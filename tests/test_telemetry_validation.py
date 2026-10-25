"""Request-linked telemetry contract tests (reference fixtures, not live traces)."""
import unittest
from telemetry.validate_telemetry import EVENT_FIELDS, REQUEST_FIELDS, validate_records


def request(rid="req-1", **overrides):
    row = {field: "" for field in REQUEST_FIELDS}
    row.update({
        "request_id_hash": rid, "terminal_regime": "FAST_PATH",
        "anchor_interrupt_count": "0", "anchor_transport_attempt_count": "0",
        "anchor_provider_generation_count": "0", "anchor_provider_generation_evidence": "CONFIRMED",
        "anchor_provider_generation_unknown_reasons": "", "anchor_tokens_billed": "0",
        "anchor_tokens_billed_evidence": "CONFIRMED", "full_oracle_fallback_count": "0",
        "full_oracle_transport_attempt_count": "0", "full_oracle_provider_generation_count": "0",
        "full_oracle_fallback_avoided": "TRUE", "full_oracle_fallback_avoided_evidence": "KNOWN_TERMINAL_REGIME",
    })
    row.update(overrides)
    return row


def event(rid="req-1", eid="e1", etype="anchor_interrupt", **overrides):
    row = {field: "" for field in EVENT_FIELDS}
    row.update({
        "request_id_hash": rid, "event_id": eid, "event_type": etype,
        "parent_event_id": "", "causal_interrupt_seq": "1", "attempt_number": "1",
        "evidence_status": "observed", "provider_generation_evidence": "",
        "provider_generation_unknown_reason": "", "status": "success",
        "ingest_replay_mark": "false", "ingest_conflict_flag": "false",
    })
    row.update(overrides)
    return row


class TelemetryContractTests(unittest.TestCase):
    def validate(self, requests, events):
        return validate_records(requests, events, request_headers=REQUEST_FIELDS, event_headers=EVENT_FIELDS)

    def assert_pass(self, requests, events):
        report = self.validate(requests, events)
        self.assertEqual(report["status"], "PASS", report["errors"])
        return report

    def assert_fail_code(self, requests, events, code):
        report = self.validate(requests, events)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn(code, {e["code"] for e in report["errors"]}, report["errors"])
        return report

    def test_no_interrupt_fast_path(self):
        self.assert_pass([request()], [])

    def test_multiple_interrupts_and_separate_transport_attempts(self):
        req = request(anchor_interrupt_count="2", anchor_transport_attempt_count="3", anchor_provider_generation_count="2")
        events = [
            event(eid="i1", etype="anchor_interrupt", causal_interrupt_seq="1"),
            event(eid="i2", etype="anchor_interrupt", causal_interrupt_seq="2"),
            event(eid="a1", etype="anchor_transport_attempt", causal_interrupt_seq="1"),
            event(eid="a2", etype="anchor_transport_attempt", causal_interrupt_seq="1", attempt_number="2", status="retry"),
            event(eid="a3", etype="anchor_transport_attempt", causal_interrupt_seq="2"),
            event(eid="g1", etype="anchor_provider_response", causal_interrupt_seq="1", provider_generation_evidence="CONFIRMED"),
            event(eid="g2", etype="anchor_provider_response", causal_interrupt_seq="2", provider_generation_evidence="CONFIRMED"),
        ]
        self.assert_pass([req], events)

    def test_retry_is_one_interrupt_but_two_attempts(self):
        req = request(anchor_interrupt_count="1", anchor_transport_attempt_count="2", anchor_provider_generation_count="1")
        events = [
            event(eid="i1", etype="anchor_interrupt"),
            event(eid="a1", etype="anchor_transport_attempt", status="transport_error",
                  provider_generation_evidence="UNKNOWN", provider_generation_unknown_reason="TRANSPORT_ERROR"),
            event(eid="a2", etype="anchor_transport_attempt", attempt_number="2"),
            event(eid="g1", etype="anchor_provider_response", attempt_number="2", provider_generation_evidence="CONFIRMED"),
        ]
        self.assert_pass([req], events)

    def test_timeout_unknown_is_not_counted_as_confirmed_generation(self):
        req = request(terminal_regime="FALLBACK", anchor_interrupt_count="1", anchor_transport_attempt_count="1",
                      anchor_provider_generation_count="0", anchor_provider_generation_evidence="UNKNOWN",
                      anchor_provider_generation_unknown_reasons="TIMEOUT_OUTCOME_UNKNOWN", anchor_tokens_billed="",
                      anchor_tokens_billed_evidence="UNKNOWN", full_oracle_fallback_count="1",
                      full_oracle_transport_attempt_count="1", full_oracle_provider_generation_count="1",
                      full_oracle_fallback_avoided="FALSE")
        events = [
            event(eid="i1", etype="anchor_interrupt"),
            event(eid="a1", etype="anchor_transport_attempt", status="timeout", provider_generation_evidence="UNKNOWN",
                  provider_generation_unknown_reason="TIMEOUT_OUTCOME_UNKNOWN"),
            event(eid="f1", etype="full_oracle_fallback"),
            event(eid="fa1", etype="full_oracle_transport_attempt"),
            event(eid="fg1", etype="full_oracle_provider_response", provider_generation_evidence="CONFIRMED"),
        ]
        report = self.assert_pass([req], events)
        self.assertEqual(report["confirmed_provider_response_events"], 1)
        self.assertEqual(report["events_with_unknown_or_unavailable_provider_evidence"], 1)

    def test_cache_miss_falls_back_without_anchor_interrupt(self):
        req = request(terminal_regime="FALLBACK", full_oracle_fallback_count="1", full_oracle_transport_attempt_count="1",
                      full_oracle_provider_generation_count="1", full_oracle_fallback_avoided="FALSE")
        events = [event(eid="f1", etype="full_oracle_fallback"),
                  event(eid="a1", etype="full_oracle_transport_attempt"),
                  event(eid="g1", etype="full_oracle_provider_response", provider_generation_evidence="CONFIRMED")]
        self.assert_pass([req], events)

    def test_halt_after_anchor_keeps_anchor_counts_and_adds_fallback(self):
        req = request(terminal_regime="FALLBACK", anchor_interrupt_count="1", anchor_transport_attempt_count="1",
                      anchor_provider_generation_count="1", full_oracle_fallback_count="1",
                      full_oracle_transport_attempt_count="1", full_oracle_provider_generation_count="1",
                      full_oracle_fallback_avoided="FALSE")
        events = [event(eid="i1", etype="anchor_interrupt"), event(eid="a1", etype="anchor_transport_attempt"),
                  event(eid="g1", etype="anchor_provider_response", provider_generation_evidence="CONFIRMED"),
                  event(eid="f1", etype="full_oracle_fallback"), event(eid="fa1", etype="full_oracle_transport_attempt"),
                  event(eid="fg1", etype="full_oracle_provider_response", provider_generation_evidence="CONFIRMED")]
        self.assert_pass([req], events)

    def test_identical_event_replay_is_counted_once(self):
        one = event(eid="i1")
        replay = dict(one, ingest_replay_mark="true")
        report = self.assert_pass([request(anchor_interrupt_count="1")], [one, replay])
        self.assertEqual(report["identical_replay_rows_excluded"], 1)
        self.assertIn("IDENTICAL_EVENT_REPLAY", {w["code"] for w in report["warnings"]})

    def test_conflicting_duplicate_event_id_is_excluded_and_flagged(self):
        one = event(eid="same", etype="gate_decision", status="accept")
        other = dict(one, status="reject")
        report = self.assert_fail_code([request()], [one, other], "EVENT_ID_CONFLICT")
        self.assertEqual(report["conflicting_event_ids_excluded"], 1)

    def test_unknown_billing_must_not_be_encoded_as_zero(self):
        self.assert_fail_code([request(anchor_tokens_billed="0", anchor_tokens_billed_evidence="UNKNOWN")], [],
                              "UNKNOWN_BILLING_COERCED_TO_ZERO")

    def test_unavailable_billing_must_not_be_encoded_as_numeric(self):
        self.assert_fail_code([request(anchor_tokens_billed="0",
                              anchor_tokens_billed_evidence="UNAVAILABLE(BILLING_FEED_MISSING)")], [],
                              "UNAVAILABLE_BILLING_AS_NUMBER")

    def test_counter_mismatch_is_rejected(self):
        self.assert_fail_code([request(anchor_interrupt_count="1")], [], "COUNTER_EVENT_MISMATCH")

    def test_unknown_provider_outcome_requires_reason(self):
        req = request(anchor_interrupt_count="1", anchor_transport_attempt_count="1",
                      anchor_provider_generation_evidence="UNKNOWN",
                      anchor_provider_generation_unknown_reasons="TIMEOUT_OUTCOME_UNKNOWN")
        events = [event(eid="i1"), event(eid="a1", etype="anchor_transport_attempt", status="timeout",
                  provider_generation_evidence="UNKNOWN", provider_generation_unknown_reason="")]
        self.assert_fail_code([req], events, "PROVIDER_UNKNOWN_REASON_MISSING")

    def test_fallback_avoided_true_requires_fast_path_and_zero_fallback(self):
        req = request(terminal_regime="FALLBACK", full_oracle_fallback_count="1")
        self.assert_fail_code([req], [], "FALLBACK_AVOIDED_INCONSISTENT")

    def test_known_fast_path_cannot_mark_fallback_avoided_unknown(self):
        req = request(full_oracle_fallback_avoided="UNKNOWN",
                      full_oracle_fallback_avoided_evidence="UNKNOWN_TERMINAL_REGIME")
        self.assert_fail_code([req], [], "FALLBACK_AVOIDED_INCONSISTENT")

    def test_fallback_terminal_requires_a_fallback_event(self):
        req = request(terminal_regime="FALLBACK", full_oracle_fallback_avoided="FALSE")
        self.assert_fail_code([req], [], "FALLBACK_AVOIDED_INCONSISTENT")

    def test_orphan_event_rejected(self):
        self.assert_fail_code([request()], [event(rid="unmatched")], "ORPHAN_EVENT")

    def test_header_contract_is_checked_even_for_empty_event_sets(self):
        report = validate_records([request()], [], request_headers=REQUEST_FIELDS, event_headers=["request_id_hash", "event_id"])
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("EVENT_COLUMNS_MISSING", {e["code"] for e in report["errors"]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
