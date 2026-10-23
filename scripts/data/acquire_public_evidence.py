#!/usr/bin/env python3
"""Acquire an explicitly licensed public LegalBench split with provenance.

Uses only the Python standard library. The downloader fails closed unless a task
is explicitly allowlisted with task-level licence evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

SCRIPT_VERSION = "1.1.0"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "data" / "manifests" / "legalbench.json"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "public" / "legalbench"


class AcquisitionError(RuntimeError):
    """Raised when upstream data cannot be fetched or validated."""


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcquisitionError(f"Cannot load manifest {path}: {exc}") from exc
    if payload.get("schema_version") != 1:
        raise AcquisitionError("Unsupported or missing manifest schema_version.")
    if not isinstance(payload.get("task_allowlist"), dict):
        raise AcquisitionError("Manifest must contain an object named task_allowlist.")
    return payload


def approved_task_info(manifest: dict[str, Any], task: str) -> dict[str, Any]:
    """Fail closed unless explicit task-level redistribution permission is recorded."""
    info = manifest.get("task_allowlist", {}).get(task)
    if not isinstance(info, dict):
        raise AcquisitionError(
            f"Task {task!r} is not allowlisted. Review the official task page and "
            "update the manifest before acquiring it."
        )
    if info.get("status") != "approved":
        raise AcquisitionError(f"Task {task!r} is not marked approved in the manifest.")
    if info.get("redistribution_allowed_with_attribution") is not True:
        raise AcquisitionError(
            f"Task {task!r} lacks an explicit redistribution permission decision."
        )
    for field in ("task_page", "task_license", "license_url", "attribution"):
        if not info.get(field):
            raise AcquisitionError(f"Task {task!r} lacks required licence field {field!r}.")
    return info


def request_bytes(url: str, *, attempts: int = 3) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        req = Request(
            url,
            headers={
                "User-Agent": "SCRS-public-evidence-acquisition/1.1 (+research reproducibility)",
                "Accept": "*/*",
            },
        )
        try:
            with urlopen(req, timeout=30) as response:
                if response.status < 200 or response.status >= 300:
                    raise AcquisitionError(f"Unexpected HTTP status {response.status} for {url}")
                return response.read()
        except HTTPError as exc:
            if exc.code == 404:
                raise AcquisitionError(f"Upstream source file was not found: {url}") from exc
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
        except (URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise AcquisitionError(f"Could not fetch bytes from {url}: {last_error}") from last_error


def resolve_upstream_revision(dataset_id: str, endpoint: str) -> str:
    """Resolve and return the exact current dataset commit SHA."""
    payload = json.loads(request_bytes(endpoint).decode("utf-8"))
    revision = payload.get("sha")
    if not isinstance(revision, str) or len(revision) != 40:
        raise AcquisitionError(
            "Hugging Face dataset API did not return a full 40-character commit SHA; "
            "refusing an unpinned download."
        )
    if not dataset_id or "/" not in dataset_id:
        raise AcquisitionError("Manifest dataset_id must use the owner/repository form.")
    return revision


def parse_tsv(source_bytes: bytes, task: str, split: str) -> list[dict[str, Any]]:
    """Parse the pinned upstream TSV, validating its schema and preserving row values."""
    try:
        decoded = source_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AcquisitionError(f"Upstream TSV is not valid UTF-8: {exc}") from exc
    reader = csv.DictReader(io.StringIO(decoded, newline=""), delimiter="\t")
    expected = {"index", "answer", "text"}
    fieldnames = set(reader.fieldnames or [])
    if not expected.issubset(fieldnames):
        raise AcquisitionError(
            f"Unexpected TSV header {reader.fieldnames!r}; required columns: {sorted(expected)}"
        )
    records: list[dict[str, Any]] = []
    seen_indexes: set[int] = set()
    for line_number, source_row in enumerate(reader, start=2):
        if None in source_row:
            raise AcquisitionError(f"Malformed TSV row at physical line {line_number}.")
        try:
            index = int(source_row["index"])
        except (ValueError, TypeError) as exc:
            raise AcquisitionError(
                f"Non-integer index at physical line {line_number}: {source_row.get('index')!r}"
            ) from exc
        if index in seen_indexes:
            raise AcquisitionError(f"Duplicate upstream row index {index}.")
        seen_indexes.add(index)
        if source_row.get("answer") is None or source_row.get("text") is None:
            raise AcquisitionError(f"Missing answer/text at physical line {line_number}.")
        fields = {
            "index": index,
            "answer": source_row["answer"],
            "text": source_row["text"],
        }
        records.append({"index": index, "task": task, "split": split, "fields": fields})
    if not records:
        raise AcquisitionError("Upstream TSV contained no data rows.")
    return records


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )
    return text.encode("utf-8")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_bytes(content)
    temp_path.replace(path)


def acquire(
    manifest_path: Path, task: str, split: str, output_root: Path
) -> tuple[Path, Path]:
    manifest = load_manifest(manifest_path)
    task_info = approved_task_info(manifest, task)
    dataset_id = manifest.get("dataset_id")
    endpoint = manifest.get("upstream_revision_endpoint")
    pattern = manifest.get("source_file_pattern")
    if not isinstance(dataset_id, str) or not dataset_id:
        raise AcquisitionError("Manifest is missing dataset_id.")
    if not isinstance(endpoint, str) or not endpoint.startswith("https://"):
        raise AcquisitionError("Manifest is missing a valid HTTPS revision endpoint.")
    if not isinstance(pattern, str) or "{task}" not in pattern or "{split}" not in pattern:
        raise AcquisitionError("Manifest source_file_pattern must include {task} and {split}.")
    revision = resolve_upstream_revision(dataset_id, endpoint)
    source_path = pattern.format(task=task, split=split)
    # Keep the dataset ID's owner/repository slash but URL-escape each user-controlled segment.
    source_path_url = "/".join(quote(part, safe="") for part in source_path.split("/"))
    source_url = (
        f"https://huggingface.co/datasets/{quote(dataset_id, safe='/')}"
        f"/resolve/{revision}/{source_path_url}"
    )
    raw_bytes = request_bytes(source_url)
    records = parse_tsv(raw_bytes, task, split)
    normalized_bytes = jsonl_bytes(records)

    out_dir = output_root / task
    raw_path = out_dir / f"{split}.tsv"
    jsonl_path = out_dir / f"{split}.jsonl"
    run_manifest_path = out_dir / f"{split}.run-manifest.json"
    atomic_write(raw_path, raw_bytes)
    atomic_write(jsonl_path, normalized_bytes)
    provenance = {
        "schema_version": 1,
        "script_version": SCRIPT_VERSION,
        "dataset_id": dataset_id,
        "dataset_homepage": manifest.get("dataset_homepage"),
        "task": task,
        "split": split,
        "upstream_revision": revision,
        "upstream_source_path": source_path,
        "upstream_source_url": source_url,
        "rows_written": len(records),
        "columns": ["index", "answer", "text"],
        "task_license": task_info["task_license"],
        "task_license_spdx": task_info.get("license_spdx"),
        "task_license_url": task_info["license_url"],
        "official_task_page": task_info["task_page"],
        "attribution": task_info["attribution"],
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_path": str(raw_path.relative_to(ROOT)) if raw_path.is_relative_to(ROOT) else str(raw_path),
        "raw_bytes": len(raw_bytes),
        "raw_sha256": sha256_bytes(raw_bytes),
        "normalized_jsonl_path": str(jsonl_path.relative_to(ROOT)) if jsonl_path.is_relative_to(ROOT) else str(jsonl_path),
        "normalized_jsonl_bytes": len(normalized_bytes),
        "normalized_jsonl_sha256": sha256_bytes(normalized_bytes),
        "normalization": "TSV quoting removed by the CSV parser; index converted to integer; source answer/text values otherwise preserved.",
        "note": "This is source benchmark data, not model output or evidence of SCRS effectiveness."
    }
    atomic_write(
        run_manifest_path,
        (json.dumps(provenance, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )
    return jsonl_path, run_manifest_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--task", required=True, help="Exact task-licensed allowlist key")
    parser.add_argument("--split", required=True, choices=("train", "test"))
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    try:
        jsonl_path, run_manifest_path = acquire(
            args.manifest, args.task, args.split, args.output_root
        )
    except (AcquisitionError, json.JSONDecodeError) as exc:
        print(f"acquisition failed: {exc}", file=sys.stderr)
        return 2
    print(f"normalized data: {jsonl_path}")
    print(f"provenance: {run_manifest_path}")
    print(f"sha256: {sha256_file(jsonl_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
