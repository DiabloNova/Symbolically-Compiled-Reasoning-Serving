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
    parse_tsv,
    sha256_bytes,
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
                    "attribution": "not sufficient by itself",
                    "redistribution_allowed_with_attribution": False,
                }
            }
        }
        with self.assertRaises(AcquisitionError):
            approved_task_info(manifest, "unsafe")

    def test_tsv_parser_preserves_text_and_converts_index(self):
        source = (
            'index\tanswer\ttext\n'
            '0\tYes\t"The deadline is 30 days after service."\n'
            '1\tNo\t"Do not waive the exception: \"\"emergency\"\" applies."\n'
        ).encode("utf-8")
        rows = parse_tsv(source, "sample", "test")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["index"], 0)
        self.assertEqual(rows[0]["fields"]["text"], "The deadline is 30 days after service.")
        self.assertEqual(rows[1]["fields"]["text"], 'Do not waive the exception: "emergency" applies.')

    def test_tsv_parser_rejects_bad_header_and_duplicate_index(self):
        with self.assertRaises(AcquisitionError):
            parse_tsv(b"id\tlabel\n0\tYes\n", "sample", "test")
        with self.assertRaises(AcquisitionError):
            parse_tsv(b"index\tanswer\ttext\n0\tYes\tA\n0\tNo\tB\n", "sample", "test")

    def test_jsonl_serialization_is_deterministic_and_unicode_safe(self):
        rows = [
            {
                "index": 0,
                "task": "sample",
                "split": "test",
                "fields": {"text": "deadline — excepción", "answer": "preserved", "index": 0},
            }
        ]
        first = jsonl_bytes(rows)
        self.assertEqual(first, jsonl_bytes(rows))
        self.assertIn("excepción".encode("utf-8"), first)
        self.assertEqual(len(first.splitlines()), 1)
        self.assertEqual(json.loads(first), rows[0])

    def test_sha256_is_stable_for_known_canonical_jsonl(self):
        body = jsonl_bytes([
            {"index": 0, "fields": {"answer": "Yes"}, "split": "test", "task": "x"}
        ])
        self.assertEqual(
            sha256_bytes(body),
            "2214d45c6328196a5fbbcf186d64894c215f37276668b6b8aa86c3145fab5ce9",
        )


if __name__ == "__main__":
    unittest.main()
