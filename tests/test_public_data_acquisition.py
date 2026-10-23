"""Network-free tests for the public evidence acquisition gate and serializer."""

import hashlib
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "data"))

from acquire_public_evidence import (  # noqa: E402
    AcquisitionError,
    approved_task_info,
    jsonl_bytes,
    load_manifest,
)


class PublicDataAcquisitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest_path = REPO_ROOT / "data" / "manifests" / "legalbench.json"
        cls.manifest = load_manifest(cls.manifest_path)

    def test_manifest_approves_only_reviewed_abercrombie_task(self):
        info = approved_task_info(self.manifest, "abercrombie")
        self.assertEqual(info["license_spdx"], "CC-BY-4.0")
        self.assertTrue(info["redistribution_allowed_with_attribution"])

    def test_unreviewed_task_fails_closed(self):
        with self.assertRaises(AcquisitionError):
            approved_task_info(self.manifest, "contract_nli_confidentiality_of_agreement")

    def test_task_without_explicit_redistribution_permission_is_rejected(self):
        manifest = {
            "task_allowlist": {
                "unsafe": {
                    "status": "approved",
                    "task_page": "https://example.invalid/task",
                    "task_license": "unknown",
                    "license_url": "https://example.invalid/license",
                    "attribution": "missing evidence",
                    "redistribution_allowed_with_attribution": False,
                }
            }
        }
        with self.assertRaises(AcquisitionError):
            approved_task_info(manifest, "unsafe")

    def test_jsonl_serialization_is_deterministic_and_unicode_safe(self):
        rows = [
            {
                "index": 0,
                "task": "sample",
                "split": "test",
                "fields": {"text": "deadline — excepción", "label": "preserved"},
            }
        ]
        first = jsonl_bytes(rows)
        second = jsonl_bytes(rows)
        self.assertEqual(first, second)
        self.assertIn("excepción".encode("utf-8"), first)
        self.assertEqual(len(first.splitlines()), 1)
        self.assertEqual(json.loads(first), rows[0])

    def test_sha256_expectation_for_stable_jsonl_bytes(self):
        body = jsonl_bytes([{"index": 0, "fields": {"answer": "Yes"}, "split": "test", "task": "x"}])
        self.assertEqual(hashlib.sha256(body).hexdigest(), hashlib.sha256(body).hexdigest())


if __name__ == "__main__":
    unittest.main()
