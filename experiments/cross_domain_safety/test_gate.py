"""Adversarial and conformance tests for the executable reference contract."""
import unittest
from gate import Candidate, decide


def valid(**overrides):
    fields = dict(
        request_domain="law.contracts",
        capsule_domain="law.contracts",
        request_contract_version="v1",
        capsule_contract_version="v1",
        preconditions_compatible=True,
        exceptions_compatible=True,
        request_validated=True,
        capsule_validated=True,
        provenance_valid=True,
    )
    fields.update(overrides)
    return Candidate(**fields)


class GateTests(unittest.TestCase):
    def test_compatible_candidate_is_accepted(self):
        self.assertEqual(decide(valid()).reason, "ACCEPTED")
        self.assertTrue(decide(valid()).accepted)

    def test_domain_mismatch_is_rejected(self):
        self.assertEqual(decide(valid(capsule_domain="finance.tax")).reason, "DOMAIN_MISMATCH")

    def test_missing_domain_fails_closed(self):
        self.assertEqual(decide(valid(request_domain=None)).reason, "DOMAIN_MISSING")

    def test_contract_version_mismatch_is_rejected(self):
        self.assertEqual(decide(valid(capsule_contract_version="v0")).reason, "CONTRACT_VERSION_MISMATCH")

    def test_missing_contract_version_fails_closed(self):
        self.assertEqual(decide(valid(request_contract_version="")).reason, "CONTRACT_VERSION_MISSING")

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

    def test_each_required_condition_is_necessary(self):
        failures = [
            dict(request_domain="law.contracts", capsule_domain="finance.tax"),
            dict(request_contract_version="v1", capsule_contract_version="v2"),
            dict(preconditions_compatible=False),
            dict(exceptions_compatible=False),
            dict(request_validated=False),
            dict(capsule_validated=False),
            dict(provenance_valid=False),
        ]
        for override in failures:
            with self.subTest(override=override):
                self.assertFalse(decide(valid(**override)).accepted)

    def test_no_candidate_is_accepted_when_required_boolean_is_unknown(self):
        self.assertFalse(decide(valid(preconditions_compatible=None)).accepted)
        self.assertFalse(decide(valid(exceptions_compatible=None)).accepted)


if __name__ == "__main__":
    unittest.main(verbosity=2)
