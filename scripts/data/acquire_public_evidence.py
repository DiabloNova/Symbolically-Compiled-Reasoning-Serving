#!/usr/bin/env python3
"""Acquire a task-approved public LegalBench split with provenance and a checksum.

Only standard-library dependencies are used. The downloader fails closed when a
task is not explicitly allowlisted with task-level licence evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SCRIPT_VERSION = "1.0.0"
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


def request_json(url: str, *, attempts: int = 3) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(attempts):
        req = Request(
            url,
            headers={
                "User-Agent": "SCRS-public-evidence-acquisition/1.0 (+research reproducibility)",
                "Accept": "application/json",
            },
        )
        try:
            with urlopen(req, timeout=30) as response:
                if response.status < 200 or response.status >= 300:
                    raise AcquisitionError(f"Unexpected HTTP status {response.status} for {url}")
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise AcquisitionError(f"Could not fetch JSON from {url}: {last_error}") from last_error


def resolve_upstream_revision(dataset_id: str) -> str:
    """Resolve and return the exact current upstream commit SHA."""
    from urllib.parse import quote

    url = f"https://huggingface.co/api/datasets/{quote(dataset_id, safe='/')}"
    metadata = request_json(url)
    revision = metadata.get("sha")
    if not isinstance(revision, str) or len(revision) != 40:
        raise AcquisitionError(
            "Hugging Face dataset API did not return a full 40-character commit SHA; "
            "refusing an unpinned download."
        )
    return revision


def locate_split(
    dataset_id: str, revision: str, task: str, split: str
) -> dict[str, Any]:
    params = urlencode({"dataset": dataset_id, "revision": revision})
    payload = request_json(f"https://datasets-server.huggingface.co/splits?{params}")
    for item in payload.get("splits", []):
        if item.get("config") == task and item.get("split") == split:
            return item
    available = sorted(
        {
            f"{item.get('config')}/{item.get('split')}"
            for item in payload.get("splits", [])
            if isinstance(item, dict)
        }
    )
    raise AcquisitionError(
        f"Split {task}/{split} was not found at revision {revision}. "
        f"Available configs/splits returned: {available[:30]}"
    )


def fetch_split_rows(
    dataset_id: str, revision: str, task: str, split: str, num_rows: int
) -> list[dict[str, Any]]:
    """Fetch a complete split with bounded pages, preserving original field values."""
    from urllib.parse import quote

    rows: list[dict[str, Any]] = []
    page_size = 100
    offset = 0
    while offset < num_rows:
        length = min(page_size, num_rows - offset)
        params = urlencode(
            {
                "dataset": dataset_id,
                "config": task,
                "split": split,
                "offset": offset,
                "length": length,
                "revision": revision,
            }
        )
        url = f"https://datasets-server.huggingface.co/rows?{params}"
        payload = request_json(url)
        page = payload.get("rows")
        if not isinstance(page, list) or not page:
            raise AcquisitionError(
                f"Upstream returned no rows at offset {offset}, expected {num_rows} total."
            )
        for item in page:
            row = item.get("row") if isinstance(item, dict) else None
            if not isinstance(row, dict):
                raise AcquisitionError(f"Malformed row returned at offset {offset}.")
            upstream_idx = item.get("row_idx", offset + len(rows))
            rows.append({"index": upstream_idx, "task": task, "split": split, "fields": row})
        offset += len(page)
        if offset < num_rows and len(page) < length:
            raise AcquisitionError(
                f"Upstream returned a short page ({len(page)} rows) before the declared "
                f"split end ({num_rows} rows)."
            )
    if len(rows) != num_rows:
        raise AcquisitionError(f"Expected {num_rows} rows but received {len(rows)}.")
    return rows


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )
    return text.encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def acquire(
    manifest_path: Path, task: str, split: str, output_root: Path
) -> tuple[Path, Path]:
    manifest = load_manifest(manifest_path)
    task_info = approved_task_info(manifest, task)
    dataset_id = manifest.get("dataset_id")
    if not isinstance(dataset_id, str) or not dataset_id:
        raise AcquisitionError("Manifest is missing dataset_id.")
    revision = resolve_upstream_revision(dataset_id)
    split_info = locate_split(dataset_id, revision, task, split)
    num_rows = split_info.get("num_rows")
    if not isinstance(num_rows, int) or num_rows < 0:
        raise AcquisitionError("Upstream split metadata does not declare a valid num_rows.")
    records = fetch_split_rows(dataset_id, revision, task, split, num_rows)
    out_dir = output_root / task
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{split}.jsonl"
    run_manifest_path = out_dir / f"{split}.run-manifest.json"
    content = jsonl_bytes(records)
    # Write a temporary file and replace atomically to avoid partial output on interruption.
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temp_path.write_bytes(content)
    temp_path.replace(output_path)
    provenance = {
        "schema_version": 1,
        "script_version": SCRIPT_VERSION,
        "dataset_id": dataset_id,
        "dataset_homepage": manifest.get("dataset_homepage"),
        "task": task,
        "split": split,
        "upstream_revision": revision,
        "upstream_split_rows_declared": num_rows,
        "rows_written": len(records),
        "task_license": task_info["task_license"],
        "task_license_url": task_info["license_url"],
        "official_task_page": task_info["task_page"],
        "attribution": task_info["attribution"],
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "output_path": str(output_path.relative_to(ROOT)) if output_path.is_relative_to(ROOT) else str(output_path),
        "output_bytes": len(content),
        "output_sha256": hashlib.sha256(content).hexdigest(),
        "note": "Upstream field values were preserved; no model predictions or preprocessing were applied."
    }
    run_manifest_path.write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path, run_manifest_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--task", required=True, help="Exact, task-licensed allowlist key")
    parser.add_argument("--split", required=True, choices=("train", "test"))
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    try:
        output_path, run_manifest_path = acquire(
            args.manifest, args.task, args.split, args.output_root
        )
    except AcquisitionError as exc:
        print(f"acquisition failed: {exc}", file=sys.stderr)
        return 2
    print(f"data: {output_path}")
    print(f"provenance: {run_manifest_path}")
    print(f"sha256: {sha256_file(output_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
