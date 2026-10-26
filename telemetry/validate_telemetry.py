#!/usr/bin/env python3
"""Offline checker for SCRS request/event telemetry; not runtime instrumentation."""
from __future__ import annotations
import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("telemetry-schema.json")
with SCHEMA_PATH.open("r", encoding="utf-8") as schema_file:
    SCHEMA = json.load(schema_file)
REQUEST_FIELDS = set(SCHEMA["request_level_fields"])
EVENT_FIELDS = set(SCHEMA["required_event_level_fields"])
EVENT_TYPES = {
    "anchor_interrupt", "anchor_transport_attempt", "anchor_provider_response",
    "full_oracle_fallback", "full_oracle_transport_attempt",
    "full_oracle_provider_response", "gate_decision", "render_lifecycle",
}
PROVIDER_EVIDENCE = {"CONFIRMED", "UNKNOWN", "UNAVAILABLE"}
UNKNOWN_REASON_CODES = {
    "TIMEOUT_OUTCOME_UNKNOWN", "TRANSPORT_ERROR",
    "PROVIDER_RESPONSE_MALFORMED", "BILLING_FEED_MISSING",
}
BOOKKEEPING_FIELDS = {"ingest_replay_mark", "ingest_conflict_flag"}


def _s(value):
    return "" if value is None else str(value).strip()


def _integer(value):
    value = _s(value)
    if not value:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 and str(parsed) == value else None


def _payload(row):
    payload = {k: _s(v) for k, v in row.items() if k not in BOOKKEEPING_FIELDS}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def validate_records(request_rows, event_rows, request_headers=None, event_headers=None):
    """Validate request/event records; return a JSON-serializable report."""
    requests = [dict(r) for r in request_rows]
    raw_events = [dict(r) for r in event_rows]
    errors, warnings = [], []

    def err(code, message, rid=""):
        errors.append({"code": code, "request_id_hash": rid, "message": message})

    def warn(code, message, rid=""):
        warnings.append({"code": code, "request_id_hash": rid, "message": message})

    req_cols = set(request_headers) if request_headers is not None else (set(requests[0]) if requests else set())
    event_cols = set(event_headers) if event_headers is not None else (set(raw_events[0]) if raw_events else set())
    if req_cols:
        missing = sorted(REQUEST_FIELDS - req_cols)
        if missing:
            err("REQUEST_COLUMNS_MISSING", ", ".join(missing))
    else:
        err("REQUEST_HEADER_MISSING", "Request CSV has no readable header.")
    if event_cols:
        missing = sorted(EVENT_FIELDS - event_cols)
        if missing:
            err("EVENT_COLUMNS_MISSING", ", ".join(missing))
    else:
        err("EVENT_HEADER_MISSING", "Event CSV must have a readable header even when there are no events.")

    by_request = {}
    for row in requests:
        rid = _s(row.get("request_id_hash"))
        if not rid:
            err("REQUEST_ID_MISSING", "Request row has no request_id_hash.")
        elif rid in by_request:
            err("DUPLICATE_REQUEST_ROW", "Expected one request row per request_id_hash.", rid)
        else:
            by_request[rid] = row

    grouped = defaultdict(list)
    for row in raw_events:
        eid = _s(row.get("event_id"))
        if not eid:
            err("EVENT_ID_MISSING", "Event row has no event_id.", _s(row.get("request_id_hash")))
        else:
            grouped[eid].append(row)

    unique_events, replay_count, conflict_ids = [], 0, []
    for eid, copies in grouped.items():
        payloads = {_payload(row) for row in copies}
        if len(payloads) > 1:
            conflict_ids.append(eid)
            err("EVENT_ID_CONFLICT", f"event_id {eid!r} has conflicting payloads; all copies are excluded.",
                _s(copies[0].get("request_id_hash")))
            continue
        unique_events.append(copies[0])
        if len(copies) > 1:
            replay_count += len(copies) - 1
            warn("IDENTICAL_EVENT_REPLAY", f"event_id {eid!r} was repeated; counted once.",
                 _s(copies[0].get("request_id_hash")))

    events_by_request = defaultdict(list)
    confirmed_generations = 0
    unknown_provider_events = 0
    missing_billing_feed_events = 0
    for row in unique_events:
        rid, etype = _s(row.get("request_id_hash")), _s(row.get("event_type"))
        if not rid:
            err("EVENT_REQUEST_ID_MISSING", "Event has no request_id_hash.")
            continue
        if rid not in by_request:
            err("ORPHAN_EVENT", "Event references a request with no request-level row.", rid)
        events_by_request[rid].append(row)
        if etype not in EVENT_TYPES:
            err("EVENT_TYPE_UNKNOWN", f"Unsupported event_type {etype!r}.", rid)

        evidence = _s(row.get("provider_generation_evidence")).upper()
        reason = _s(row.get("provider_generation_unknown_reason"))
        if evidence and evidence not in PROVIDER_EVIDENCE:
            err("PROVIDER_EVIDENCE_UNKNOWN", f"Unsupported provider evidence {evidence!r}.", rid)
        if evidence in {"UNKNOWN", "UNAVAILABLE"}:
            unknown_provider_events += 1
            if not reason:
                err("PROVIDER_UNKNOWN_REASON_MISSING", f"{evidence} provider outcome requires a reason code.", rid)
            elif reason not in UNKNOWN_REASON_CODES:
                err("PROVIDER_UNKNOWN_REASON_INVALID", f"Unsupported provider reason {reason!r}.", rid)
        if reason == "BILLING_FEED_MISSING":
            missing_billing_feed_events += 1
        if etype in {"anchor_provider_response", "full_oracle_provider_response"} and evidence == "CONFIRMED":
            confirmed_generations += 1
        if etype in {"anchor_transport_attempt", "full_oracle_transport_attempt"}:
            status = _s(row.get("status")).lower()
            if status in {"timeout", "timed_out", "timeout_unknown"} and evidence != "CONFIRMED":
                if evidence != "UNKNOWN" or reason != "TIMEOUT_OUTCOME_UNKNOWN":
                    err("TIMEOUT_EVIDENCE_MISMATCH",
                        "Unconfirmed timed-out attempt must be UNKNOWN / TIMEOUT_OUTCOME_UNKNOWN.", rid)

    simple_counters = {
        "anchor_interrupt_count": "anchor_interrupt",
        "anchor_transport_attempt_count": "anchor_transport_attempt",
        "full_oracle_fallback_count": "full_oracle_fallback",
        "full_oracle_transport_attempt_count": "full_oracle_transport_attempt",
    }
    for rid, req in by_request.items():
        rows = events_by_request.get(rid, [])
        for field, etype in simple_counters.items():
            actual = _integer(req.get(field))
            expected = sum(1 for ev in rows if _s(ev.get("event_type")) == etype)
            if actual is None:
                err("COUNTER_NOT_KNOWN_INTEGER", f"{field} must be an explicit non-negative integer; blank is not zero.", rid)
            elif actual != expected:
                err("COUNTER_EVENT_MISMATCH", f"{field}={actual}; found {expected} distinct {etype} events.", rid)

        for field, etype in [
            ("anchor_provider_generation_count", "anchor_provider_response"),
            ("full_oracle_provider_generation_count", "full_oracle_provider_response"),
        ]:
            actual = _integer(req.get(field))
            expected = sum(1 for ev in rows if _s(ev.get("event_type")) == etype
                           and _s(ev.get("provider_generation_evidence")).upper() == "CONFIRMED")
            if actual is None:
                err("COUNTER_NOT_KNOWN_INTEGER", f"{field} must be an explicit count of confirmed generations.", rid)
            elif actual != expected:
                err("GENERATION_COUNTER_MISMATCH", f"{field}={actual}; found {expected} CONFIRMED {etype} events.", rid)

        terminal = _s(req.get("terminal_regime")).upper()
        fallback_count = _integer(req.get("full_oracle_fallback_count"))
        avoided = _s(req.get("full_oracle_fallback_avoided")).upper()
        avoided_evidence = _s(req.get("full_oracle_fallback_avoided_evidence")).upper()
        if avoided not in {"TRUE", "FALSE", "UNKNOWN"}:
            err("FALLBACK_AVOIDED_VALUE_INVALID", "fallback_avoided must be TRUE, FALSE, or UNKNOWN.", rid)
        elif terminal == "FAST_PATH":
            if fallback_count != 0 or avoided != "TRUE":
                err("FALLBACK_AVOIDED_INCONSISTENT", "FAST_PATH requires zero full fallback operations and fallback_avoided=TRUE.", rid)
        elif terminal == "FALLBACK":
            if fallback_count is None or fallback_count < 1 or avoided != "FALSE":
                err("FALLBACK_AVOIDED_INCONSISTENT", "FALLBACK requires at least one full fallback operation and fallback_avoided=FALSE.", rid)
        elif avoided != "UNKNOWN" or avoided_evidence not in {"UNKNOWN_TERMINAL_REGIME", "UNRESOLVED_FALLBACK_OUTCOME"}:
            err("FALLBACK_UNKNOWN_EVIDENCE_MISSING", "An unknown terminal regime/outcome requires fallback_avoided=UNKNOWN and explicit unknown evidence.", rid)
        if avoided in {"TRUE", "FALSE"} and avoided_evidence not in {"KNOWN_TERMINAL_REGIME", ""}:
            err("FALLBACK_EVIDENCE_MISMATCH", "Known TRUE/FALSE requires KNOWN_TERMINAL_REGIME evidence.", rid)

        billing_evidence = _s(req.get("anchor_tokens_billed_evidence")).upper()
        billed = _s(req.get("anchor_tokens_billed"))
        if billing_evidence.startswith("UNAVAILABLE") and billed:
            if _integer(billed) is not None:
                err("UNAVAILABLE_BILLING_AS_NUMBER", "Unavailable billed tokens must not be represented by a numeric value.", rid)
        elif billing_evidence in {"UNKNOWN", ""} and billed == "0":
            err("UNKNOWN_BILLING_COERCED_TO_ZERO", "Unknown/missing billing evidence must not be represented as zero.", rid)
        elif billing_evidence == "CONFIRMED" and _integer(billed) is None:
            err("CONFIRMED_BILLING_VALUE_MISSING", "Confirmed billing requires an explicit non-negative token count.", rid)

        generation_evidence = _s(req.get("anchor_provider_generation_evidence")).upper()
        generation_reason = _s(req.get("anchor_provider_generation_unknown_reasons"))
        if generation_evidence in {"UNKNOWN", "UNAVAILABLE"} and not generation_reason:
            err("REQUEST_PROVIDER_UNKNOWN_REASON_MISSING", "Unknown/unavailable request provider evidence requires a reason.", rid)
        if generation_evidence and generation_evidence not in PROVIDER_EVIDENCE:
            err("REQUEST_PROVIDER_EVIDENCE_INVALID", f"Unsupported request provider evidence {generation_evidence!r}.", rid)

    return {
        "schema_contract": "SCRS telemetry schema v2 (offline contract validation)",
        "status": "PASS" if not errors else "FAIL",
        "request_rows": len(requests),
        "raw_event_rows": len(raw_events),
        "distinct_event_ids": len(grouped),
        "counted_distinct_event_rows": len(unique_events),
        "identical_replay_rows_excluded": replay_count,
        "conflicting_event_ids_excluded": len(conflict_ids),
        "confirmed_provider_response_events": confirmed_generations,
        "events_with_unknown_or_unavailable_provider_evidence": unknown_provider_events,
        "events_citing_missing_billing_feed": missing_billing_feed_events,
        "errors": errors,
        "warnings": warnings,
    }


def read_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        return list(reader.fieldnames), [dict(row) for row in reader]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", required=True, help="Request-level CSV path")
    parser.add_argument("--events", required=True, help="Event-level CSV path")
    parser.add_argument("--report", help="Optional JSON report output path")
    args = parser.parse_args(argv)
    try:
        req_headers, req_rows = read_csv(args.requests)
        event_headers, event_rows = read_csv(args.events)
        report = validate_records(req_rows, event_rows, req_headers, event_headers)
    except (OSError, csv.Error, ValueError) as exc:
        print(f"telemetry input error: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.report:
        try:
            Path(args.report).write_text(rendered, encoding="utf-8")
        except OSError as exc:
            print(f"cannot write report: {exc}", file=sys.stderr)
            return 2
    print(rendered, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
