# SCRS Repository — PR Review, Fixes, and Merge Package

**Date:** 2026-10-23
**Repository:** https://github.com/DiabloNova/Symbolically-Compiled-Reasoning-Serving

## What was done

### 1. Cubic (cubic-dev-ai) review findings — all resolved

**PR #2 (`research/p0-r2-counter-fix`) — 6 findings, all fixed:**
| # | Severity | Finding | Fix |
|---|----------|---------|-----|
| 1 | P2 | `anchor_provider_generation_count` is a plain int, cannot hold "unknown" | Tri-state `anchor_provider_generation_evidence` ∈ {CONFIRMED, UNKNOWN+reason, UNAVAILABLE+reason}; count advances only on CONFIRMED |
| 2 | P2 | Confirmed-response branch does not tie to named counters | Branch now names every update: generation count, evidence state, returned tokens, billed tokens (per-generation UNAVAILABLE/BILLING_FEED_MISSING instead of zero) |
| 3 | P1 | No mid-render fallback path; `terminal_regime = FAST_PATH` unconditional | Explicit mid-render halt/fallback branch inside the render loop; FAST_PATH assigned only on clean EOS; case 7a added |
| 4 | P2 | Event IDs alone do not prevent duplicate counting | Mandatory ingestion dedup rule: stable `event_id = (request_id_hash, causal_interrupt_seq, attempt_number, event_type)`; identical replays marked, conflicts flagged; counters advanced only by the runtime state machine |
| 5 | P2 | Telemetry schema/CSV still use old aggregate fields | `telemetry-schema.json` → schema_version 2 (contract fields, tri-state semantics, dedup, derived-metric rules) + new request-level and event-level CSV templates |
| 6 | P2 | Counter boundaries not named in next-steps.md | Both boundaries named: runtime-event boundary vs transport boundary, with explicit ownership list |

**PR #3 (`research/p0-r3-cross-domain-safety`) — 8 findings, all fixed:**
| # | Severity | Finding | Fix |
|---|----------|---------|-----|
| 1 | P3 | section-5 spec missing from README Contents | Added spec + `experiments/cross_domain_safety/` to Contents |
| 2 | P2 | "known incompatible" labels derived from the same policy the gate enforces | Independence requirement added: end-to-end rates require human-adjudicated/externally labelled sources; policy-derived fixture results labelled **conformance results, not end-to-end error rates** |
| 3 | P2 | Predicate cannot detect canonicalization collisions | New `C_inj` conjunct: certified injective versioned mapping OR explicit collision/ambiguity rejection (`CANONICALIZATION_AMBIGUOUS`, `CANONICALIZATION_MAPPING_UNSUPPORTED/UNCERTIFIED`); collision test cases added |
| 4 | P2 | `N_known_incompatible_cases` lacks operational definition | Authoritative independent domain oracle defined; multi-domain/mislabelled case rules; upstream-extraction errors reported separately from gate conformance |
| 5 | P2 | `decide` not fail-closed for truthy non-boolean statuses | All status checks now use `is not True` semantics; `test_truthy_non_boolean_statuses_fail_closed` covers every boolean field |
| 6 | P1 | Gate accepts equal-but-stale contract versions | Per-side `request_contract_current` / `capsule_contract_current` inputs; `REQUEST_CONTRACT_NOT_CURRENT` / `CAPSULE_CONTRACT_NOT_CURRENT` reason codes; stale-version tests |
| 7 | P2 | Fail-closed coverage one-sided | Capsule-side `None` coverage for domain and contract versions; empty-string coverage both sides |
| 8 | P2 | `fixtures.json` never loaded by tests | `fixtures.json` → schema v2 with complete `candidate_fields`; `ManifestConformanceTests` loads and drives every case |

**PR #4 (`research/free-public-evidence-pipeline-v1`)** — no cubic findings; merged as-is.

### 2. Verification

- Executable reference model test suite: **26/26 passed** (24 unit + 2 manifest-driven) on merged `main`.
- `telemetry-schema.json` validated as JSON.
- Merge performed with `--no-ff` to preserve PR topology.

### 3. Merge state

All three PR branches are merged into a local `main` that is a strict descendant of `origin/main` (fast-forwardable push). Merge commits carry full evidence descriptions.

## How to publish (no push credentials were available in this environment)

**Option A — one-command push from the bundle (recommended):**
```bash
# from a machine with push access to the repo:
git clone https://github.com/DiabloNova/Symbolically-Compiled-Reasoning-Serving.git
cd Symbolically-Compiled-Reasoning-Serving
git fetch /path/to/SCRS_repo_merged.bundle main:merged-main
git push origin merged-main:main        # fast-forwards; PRs #2/#3/#4 auto-mark merged
```

**Option B — apply the patch series:**
```bash
git am /path/to/patches/*.patch
git push origin main
```

**Option C — GitHub web UI:** merge PR #2, then PR #3, then PR #4 (order irrelevant; no conflicts), then apply the three fix patches manually from `patches/0017…0019`.

Option A is preferred: after `git push origin merged-main:main`, GitHub automatically detects the merged PR branches and marks PRs #2, #3, #4 as **Merged**.

## File inventory

- `SCRS_repo_merged.bundle` — git bundle of the merged `main` (all commits + all branches).
- `patches/` — 19-commit patch series `origin/main..merged-main` (branch work + cubic fixes + README status).
- `SCRS_merged_main_vs_origin.patch` — the same series concatenated in one file.
