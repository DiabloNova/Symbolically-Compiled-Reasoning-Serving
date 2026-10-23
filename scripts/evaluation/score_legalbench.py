#!/usr/bin/env python3
"""Score supplied LegalBench predictions against a pinned local split.

This script does not call a model or generate predictions. It validates prediction
coverage and labels, computes exact-label metrics, and stores run provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOLD = ROOT / "data/public/legalbench/abercrombie/test.jsonl"
DEFAULT_SOURCE_MANIFEST = ROOT / "data/public/legalbench/abercrombie/test.run-manifest.json"
SCHEMA_VERSION = 1


class ScoringError(ValueError):
    """Raised for incomplete, ambiguous, or malformed benchmark predictions."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ScoringError(f"Cannot read {path}: {exc}") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ScoringError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
        if not isinstance(record, dict):
            raise ScoringError(f"Expected JSON object at {path}:{line_number}.")
        records.append(record)
    if not records:
        raise ScoringError(f"No records found in {path}.")
    return records


def normalized_label(value: Any, *, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ScoringError(f"{context} must be a non-empty string.")
    # Deliberately conservative: trim and case-fold only; no semantic aliases.
    return value.strip().casefold()


def _unique_index_map(
    records: list[dict[str, Any]], *, index_field: str, context: str
) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for row_no, row in enumerate(records, start=1):
        value = row.get(index_field)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ScoringError(f"{context} row {row_no} has a non-integer {index_field!r}.")
        if value in indexed:
            raise ScoringError(f"{context} contains duplicate index {value}.")
        indexed[value] = row
    return indexed


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> list[float] | None:
    """Two-sided 95% Wilson score interval for a binomial proportion."""
    if total <= 0:
        return None
    p = successes / total
    z2 = z * z
    denominator = 1.0 + z2 / total
    center = (p + z2 / (2.0 * total)) / denominator
    margin = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * total)) / total) / denominator
    return [max(0.0, center - margin), min(1.0, center + margin)]


def score_rows(
    gold_records: list[dict[str, Any]],
    prediction_records: list[dict[str, Any]],
) -> dict[str, Any]:
    gold_by_index = _unique_index_map(gold_records, index_field="index", context="Gold data")
    predictions_by_index = _unique_index_map(
        prediction_records, index_field="index", context="Predictions"
    )
    missing = sorted(set(gold_by_index) - set(predictions_by_index))
    extra = sorted(set(predictions_by_index) - set(gold_by_index))
    if missing or extra:
        raise ScoringError(
            f"Prediction coverage mismatch: missing={missing[:20]}, extra={extra[:20]}, "
            f"gold_count={len(gold_by_index)}, prediction_count={len(predictions_by_index)}."
        )

    gold_labels: dict[int, str] = {}
    predicted_labels: dict[int, str] = {}
    for index, row in gold_by_index.items():
        fields = row.get("fields")
        if not isinstance(fields, dict):
            raise ScoringError(f"Gold record {index} is missing object field 'fields'.")
        gold_labels[index] = normalized_label(
            fields.get("answer"), context=f"Gold answer at index {index}"
        )
    for index, row in predictions_by_index.items():
        predicted_labels[index] = normalized_label(
            row.get("prediction"), context=f"Prediction at index {index}"
        )

    labels = sorted(set(gold_labels.values()))
    unknown = sorted(set(predicted_labels.values()) - set(labels))
    if unknown:
        raise ScoringError(f"Predictions contain labels absent from gold labels: {unknown}.")

    confusion = {actual: {predicted: 0 for predicted in labels} for actual in labels}
    correct = 0
    for index in sorted(gold_by_index):
        actual, predicted = gold_labels[index], predicted_labels[index]
        confusion[actual][predicted] += 1
        correct += int(actual == predicted)

    per_class: dict[str, dict[str, float | int]] = {}
    precisions: list[float] = []
    recalls: list[float] = []
    f1_scores: list[float] = []
    for label in labels:
        tp = confusion[label][label]
        fp = sum(confusion[actual][label] for actual in labels if actual != label)
        fn = sum(confusion[label][predicted] for predicted in labels if predicted != label)
        support = sum(confusion[label].values())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {
            "support": support, "precision": precision, "recall": recall, "f1": f1
        }
        precisions.append(precision)
        recalls.append(recall)
        f1_scores.append(f1)

    total = len(gold_by_index)
    return {
        "n": total,
        "correct": correct,
        "accuracy": correct / total,
        "accuracy_ci95_wilson": wilson_interval(correct, total),
        "labels": labels,
        "label_support": dict(sorted(Counter(gold_labels.values()).items())),
        "macro_precision": sum(precisions) / len(precisions),
        "macro_recall": sum(recalls) / len(recalls),
        "macro_f1": sum(f1_scores) / len(f1_scores),
        "per_class": per_class,
        "confusion_matrix": confusion,
    }


def current_git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True, timeout=5
        )
    except (OSError, subprocess.SubprocessError):
        return None
    commit = result.stdout.strip()
    return commit or None


def evaluate_files(
    gold_path: Path,
    predictions_path: Path,
    source_manifest_path: Path,
    *,
    condition: str,
    model_id: str,
    method_description: str,
    seed: int | None,
) -> dict[str, Any]:
    if not condition.strip() or not model_id.strip():
        raise ScoringError("Both condition and model_id must be non-empty.")
    gold = read_jsonl(gold_path)
    predictions = read_jsonl(predictions_path)
    try:
        source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScoringError(f"Cannot read source run manifest {source_manifest_path}: {exc}") from exc
    if source_manifest.get("normalized_jsonl_sha256") != sha256_file(gold_path):
        raise ScoringError("Gold data SHA-256 does not match its source run manifest.")
    metrics = score_rows(gold, predictions)
    return {
        "schema_version": SCHEMA_VERSION,
        "evaluation_type": "public-benchmark-scoring-of-supplied-predictions",
        "dataset": {
            "dataset_id": source_manifest.get("dataset_id"),
            "task": source_manifest.get("task"),
            "split": source_manifest.get("split"),
            "upstream_revision": source_manifest.get("upstream_revision"),
            "gold_path": str(gold_path),
            "gold_sha256": sha256_file(gold_path),
            "upstream_source_sha256": source_manifest.get("raw_sha256"),
            "upstream_source_url": source_manifest.get("upstream_source_url"),
            "task_license": source_manifest.get("task_license"),
            "task_license_url": source_manifest.get("task_license_url"),
        },
        "method": {
            "condition": condition,
            "model_id": model_id,
            "description": method_description,
            "seed": seed,
            "implementation_commit": current_git_commit(),
        },
        "predictions": {
            "path": str(predictions_path),
            "sha256": sha256_file(predictions_path),
            "record_count": len(predictions),
            "schema": {"index": "integer from gold split", "prediction": "exact task label"},
            "normalization": "strip surrounding whitespace and case-fold; no alias mapping",
        },
        "metrics": metrics,
        "scored_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "This script scores predictions; it does not generate model predictions.",
            "Accuracy is task-specific and must not be generalized to SCRS's overall semantic preservation.",
            "Wilson interval treats examples as independent binomial trials; it does not account for task or prompt dependence.",
            "Any claimed comparison requires the same task/split and documented model, prompt, extractor, graph, and compatibility-gate versions."
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--condition", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--method-description", default="")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = evaluate_files(
            args.gold, args.predictions, args.source_manifest,
            condition=args.condition, model_id=args.model_id,
            method_description=args.method_description, seed=args.seed
        )
    except ScoringError as exc:
        print(f"scoring failed: {exc}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    metrics = report["metrics"]
    print(f"n: {metrics['n']}")
    print(f"accuracy: {metrics['accuracy']:.6f}")
    print(f"95% Wilson CI: {metrics['accuracy_ci95_wilson']}")
    print(f"macro F1: {metrics['macro_f1']:.6f}")
    print(f"report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
