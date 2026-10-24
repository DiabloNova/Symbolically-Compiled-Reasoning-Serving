"""Adversarial and conformance tests for the executable reference contract.

Two layers:
  1. Hand-written unit tests covering every fail-closed branch, including
     capsule-side missing values, truthy non-boolean statuses, stale-but-equal
     contract versions, and canonicalization collisions.
  2. A manifest-driven conformance suite loaded from fixtures.json, so the
     checked-in manifest actually drives and verifies the advertised cases.
"""
import json
import os
import unittest
from gate import Candidate, decide


def valid(**overrides):
    fields = dict(
        request_domain="law.contracts",
        capsule_domain="law.contracts",
        request_contract_version="v1",
        capsule_contract_version="v1",
        request_contract_current=True,
        capsule_contract_current=True,
        canonical_mapping_version="cm-1",
        canonical_mapping_supported=True,
        canonicalization_ambiguous=False,
        preconditions_compatible=True,
        exceptions_compatible=True,
        request_validated=True,
        capsule_validated=True,
        provenance_valid=True,
    )
    fields.update(overrides)
    return Candidate(**fields)


class GateTests(unittest.TestCase):
    # -- acceptance and basic rejection classes
    def test_compatible_candidate_is_accepted(self):
        self.assertEqual(decide(valid()).reason, "ACCEPTED")
        self.assertTrue(decide(valid()).accepted)

    def test_domain_mismatch_is_rejected(self):
        self.assertEqual(decide(valid(capsule_domain="finance.tax")).reason, "DOMAIN_MISMATCH")

    def test_missing_domain_fails_closed_request_side(self):
        self.assertEqual(decide(valid(request_domain=None)).reason, "DOMAIN_MISSING")

    def test_missing_domain_fails_closed_capsule_side(self):
        self.assertEqual(decide(valid(capsule_domain=None)).reason, "DOMAIN_MISSING")

    def test_empty_domain_fails_closed_both_sides(self):
        self.assertEqual(decide(valid(request_domain="")).reason, "DOMAIN_MISSING")
        self.assertEqual(decide(valid(capsule_domain="")).reason, "DOMAIN_MISSING")

    def test_contract_version_mismatch_is_rejected(self):
        self.assertEqual(decide(valid(capsule_contract_version="v0")).reason, "CONTRACT_VERSION_MISMATCH")

    def test_missing_contract_version_fails_closed_request_side(self):
        self.assertEqual(decide(valid(request_contract_version="")).reason, "CONTRACT_VERSION_MISSING")

    def test_missing_contract_version_fails_closed_capsule_side(self):
        self.assertEqual(decide(valid(capsule_contract_version=None)).reason, "CONTRACT_VERSION_MISSING")

    # -- version currency: equal but stale versions must still be rejected
    def test_equal_but_stale_request_version_is_rejected(self):
        self.assertEqual(decide(valid(request_contract_current=False)).reason,
                         "REQUEST_CONTRACT_NOT_CURRENT")

    def test_equal_but_stale_capsule_version_is_rejected(self):
        self.assertEqual(decide(valid(capsule_contract_current=False)).reason,
                         "CAPSULE_CONTRACT_NOT_CURRENT")

    def test_equal_but_unknown_currency_fails_closed(self):
        self.assertEqual(decide(valid(request_contract_current=None)).reason,
                         "REQUEST_CONTRACT_NOT_CURRENT")

    # -- explicit-affirmative semantics for every boolean status
    def test_truthy_non_boolean_statuses_fail_closed(self):
        # Python does not enforce bool annotations: a truthy string such as
        # "unknown" must NOT pass any of the status checks.
        for field in ("request_validated", "capsule_validated", "provenance_valid",
                      "preconditions_compatible", "exceptions_compatible",
                      "request_contract_current", "capsule_contract_current",
                      "canonical_mapping_supported"):
            with self.subTest(field=field):
                self.assertFalse(decide(valid(**{field: "unknown"})).accepted)

    def test_unknown_precondition_fails_closed(self):
        self.assertEqual(decide(valid(preconditions_compatible=None)).reason,
                         "PRECONDITIONS_NOT_CONFIRMED_COMPATIBLE")

    def test_incompatible_exception_policy_is_rejected(self):
        self.assertEqual(decide(valid(exceptions_compatible=False)).reason,
                         "EXCEPTIONS_NOT_CONFIRMED_COMPATIBLE")

    def test_unknown_exception_policy_fails_closed(self):
        self.assertEqual(decide(valid(exceptions_compatible=None)).reason,
                         "EXCEPTIONS_NOT_CONFIRMED_COMPATIBLE")

    def test_unvalidated_request_is_rejected(self):
        self.assertEqual(decide(valid(request_validated=False)).reason, "REQUEST_NOT_VALIDATED")

    def test_unvalidated_capsule_is_rejected(self):
        self.assertEqual(decide(valid(capsule_validated=False)).reason, "CAPSULE_NOT_VALIDATED")

    def test_invalid_provenance_is_rejected(self):
        self.assertEqual(decide(valid(provenance_valid=False)).reason, "PROVENANCE_INVALID")

    # -- canonicalization preconditions
    def test_unsupported_canonical_mapping_is_rejected(self):
        self.assertEqual(decide(valid(canonical_mapping_version="cm-0")).reason,
                         "CANONICALIZATION_MAPPING_UNSUPPORTED")

    def test_missing_canonical_mapping_is_rejected(self):
        self.assertEqual(decide(valid(canonical_mapping_version=None)).reason,
                         "CANONICALIZATION_MAPPING_UNSUPPORTED")

    def test_uncertified_canonical_mapping_is_rejected(self):
        self.assertEqual(decide(valid(canonical_mapping_supported=False)).reason,
                         "CANONICALIZATION_MAPPING_UNCERTIFIED")

    def test_canonicalization_collision_is_rejected(self):
        # Two distinct domains that normalize to the same identifier must be
        # rejected by the collision conjunct, not accepted via equality.
        self.assertEqual(decide(valid(canonicalization_ambiguous=True)).reason,
                         "CANONICALIZATION_AMBIGUOUS")

    def test_unknown_ambiguity_status_fails_closed(self):
        self.assertEqual(decide(valid(canonicalization_ambiguous=None)).reason,
                         "CANONICALIZATION_AMBIGUOUS")

    # -- necessity of each required condition
    def test_each_required_condition_is_necessary(self):
        failures = [
            dict(request_domain="law.contracts", capsule_domain="finance.tax"),
            dict(request_contract_version="v1", capsule_contract_version="v2"),
            dict(request_contract_current=False),
            dict(capsule_contract_current=False),
            dict(canonical_mapping_supported=False),
            dict(canonicalization_ambiguous=True),
            dict(preconditions_compatible=False),
            dict(exceptions_compatible=False),
            dict(request_validated=False),
            dict(capsule_validated=False),
            dict(provenance_valid=False),
        ]
        for override in failures:
            with self.subTest(override=override):
                self.assertFalse(decide(valid(**override)).accepted)


class ManifestConformanceTests(unittest.TestCase):
    """Drive the advertised fixture manifest from fixtures.json."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures.json")
        with open(path, "r", encoding="utf-8") as fh:
            cls.manifest = json.load(fh)
        cls.base = valid()

    def test_manifest_has_expected_shape(self):
        self.assertEqual(self.manifest["schema_version"], 2)
        self.assertTrue(self.manifest["cases"])

    def test_manifest_cases_match_expected_reason(self):
        for case in self.manifest["cases"]:
            with self.subTest(case=case["id"]):
                candidate = Candidate(**{**self.base.__dict__, **case["candidate_fields"]})
                decision = decide(candidate)
                self.assertEqual(decision.reason, case["expected"],
                                 msg=f"case {case['id']}: got {decision.reason}")
                self.assertEqual(decision.accepted, decision.reason == "ACCEPTED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
