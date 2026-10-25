#!/usr/bin/env python3
"""Core model definitions for SCRS recalculation-v1; importing this module does not run the simulation."""
from __future__ import annotations
import csv, json, math
from pathlib import Path
import numpy as np

OUT = Path(__file__).parent
N = 100_000
SEED = 20261025
PARAMS = {
    "ingress": (0.012, 0.030), "lookup": (0.004, 0.012), "gate": (0.008, 0.020),
    "slm_ttft": (0.024, 0.048), "slm_tpot": (0.005, 0.008),
    "api_queue": (0.080, 0.400), "oracle_ttft_service": (1.316, 1.850),
    "oracle_tpot": (0.0178, 0.0248), "bailout_transition": (0.120, 0.350),
}
RHO_ORACLE = RHO_SLM = RHO_QUEUE_TTFT = 0.5
P_HIT, P_HALT_COND = 0.78, 0.205
ALPHA = P_HIT * (1.0 - P_HALT_COND)
P_BAIL = P_HIT * P_HALT_COND
P_MISS = 1.0 - P_HIT
NAIVE_ALPHA = P_HIT
ORACLE_FAST_RENDER_TOKENS = 900
ORACLE_BASE_INPUT_TOKENS = 6420
ORACLE_FIXED_TTFT_FLOOR_S = 0.30
RAW_ANCHOR_INPUT_TOKENS, CAPSULE_ANCHOR_INPUT_TOKENS = 6900, 1400
LOCAL_RENDER_TOKENS, PARTIAL_LOCAL_TOKENS = 900, 300
ANCHOR_K = 5
N_ANCHOR_CONDITIONAL = 1.4
N_TIER3_RAW, N_TIER1_TIER3 = 11.5, 9.6
ORACLE_IN_PRICE_PER_M, ORACLE_OUT_PRICE_PER_M = 2.50, 10.00
LOCAL_HOST_MONTHLY_USD, MONTHLY_REQUESTS = 766.0, 300_000
REQUESTS_PER_COST_BLOCK = 10_000
BASELINE_INPUT_TOKENS, BASELINE_OUTPUT_TOKENS = 6420, 2380
TIER1_INPUT_TOKENS, TIER1_OUTPUT_TOKENS = 1180, 2310


def sigma(median: float, p95: float) -> float:
    return math.log(p95 / median) / 1.6448536269514722


def draw_lognormal(pair: tuple[float, float], n: int, rng: np.random.Generator, z=None):
    if z is None:
        z = rng.standard_normal(n)
    return pair[0] * np.exp(sigma(*pair) * z)


def draw_correlated_pair(p1, p2, rho, n, rng, z_shared=None):
    if z_shared is None:
        z_shared = rng.standard_normal(n)
    e1, e2 = rng.standard_normal(n), rng.standard_normal(n)
    z1 = np.sqrt(rho) * z_shared + np.sqrt(1-rho) * e1
    z2 = np.sqrt(rho) * z_shared + np.sqrt(1-rho) * e2
    return draw_lognormal(p1, n, rng, z1), draw_lognormal(p2, n, rng, z2), z_shared


def api_call_duration(n_tokens: int, input_tokens: int, n: int, rng: np.random.Generator, request_load=None):
    # One serial Oracle round-trip per logical call is a scenario assumption.
    if request_load is None:
        request_load = rng.standard_normal(n)
    # A shared request-load factor plus independent residuals avoids the accidental
    # perfect rank correlation in the first recalculation attempt.
    eps_queue, eps_ttft, eps_tpot = (rng.standard_normal(n) for _ in range(3))
    z_queue = np.sqrt(RHO_QUEUE_TTFT)*request_load + np.sqrt(1-RHO_QUEUE_TTFT)*eps_queue
    z_ttft = np.sqrt(RHO_QUEUE_TTFT)*request_load + np.sqrt(1-RHO_QUEUE_TTFT)*eps_ttft
    z_tpot = np.sqrt(RHO_ORACLE)*request_load + np.sqrt(1-RHO_ORACLE)*eps_tpot
    queue = draw_lognormal(PARAMS['api_queue'], n, rng, z_queue)
    ratio = max(0.0, input_tokens / ORACLE_BASE_INPUT_TOKENS)
    m0, p950 = PARAMS['oracle_ttft_service']
    fixed = ORACLE_FIXED_TTFT_FLOOR_S
    pttft = (fixed + (m0-fixed)*ratio, fixed + (p950-fixed)*ratio)
    ttft = draw_lognormal(pttft, n, rng, z_ttft)
    tpot = draw_lognormal(PARAMS['oracle_tpot'], n, rng, z_tpot)
    return queue + ttft + n_tokens*tpot, queue, ttft, tpot


def serial_anchor_calls(counts, input_tokens, n, rng, request_load):
    total = np.zeros(n); queue_total = np.zeros(n); ttft_total = np.zeros(n); tpot_total = np.zeros(n)
    for j in range(int(counts.max()) if n else 0):
        mask = counts > j
        if not mask.any():
            continue
        dur, q, t, tp = api_call_duration(ANCHOR_K, input_tokens, int(mask.sum()), rng, request_load[mask])
        total[mask] += dur; queue_total[mask] += q; ttft_total[mask] += t; tpot_total[mask] += tp
    return total, queue_total, ttft_total, tpot_total


def simulate_config(name: str, mode: str, index: int):
    rng = np.random.default_rng(SEED + index)
    n = N
    ingress = draw_lognormal(PARAMS['ingress'], n, rng)
    lookup = draw_lognormal(PARAMS['lookup'], n, rng)
    gated = mode in ('jit_oracle_raw', 'jit_oracle_capsule', 'unified')
    gate = draw_lognormal(PARAMS['gate'], n, rng) if gated else np.zeros(n)
    common = ingress + lookup + gate
    slm_ttft, slm_tpot, _ = draw_correlated_pair(PARAMS['slm_ttft'], PARAMS['slm_tpot'], RHO_SLM, n, rng)
    local_render = slm_ttft + LOCAL_RENDER_TOKENS*slm_tpot
    u = rng.random(n)
    if mode in ('jit_oracle_raw', 'jit_oracle_capsule', 'unified'):
        success = u < ALPHA
        bailout = (u >= ALPHA) & (u < ALPHA + P_BAIL)
        miss = ~(success | bailout)
    elif mode == 'naive':
        success = u < NAIVE_ALPHA; bailout = np.zeros(n, dtype=bool); miss = ~success
    else:
        success = np.zeros(n, dtype=bool); bailout = np.zeros(n, dtype=bool); miss = np.ones(n, dtype=bool)

    counts = np.zeros(n, dtype=int)
    if mode == 'tier3_raw':
        counts = rng.poisson(N_TIER3_RAW, n)
    elif mode == 'tier1_tier3':
        counts = rng.poisson(N_TIER1_TIER3, n)
    elif mode in ('unified', 'naive'):
        counts[success] = rng.poisson(N_ANCHOR_CONDITIONAL, int(success.sum()))

    request_load = rng.standard_normal(n)
    anchor_input_tokens = RAW_ANCHOR_INPUT_TOKENS if mode == 'tier3_raw' else CAPSULE_ANCHOR_INPUT_TOKENS
    anchor_dur, anchor_q, anchor_ttft, anchor_tpot = serial_anchor_calls(counts, anchor_input_tokens, n, rng, request_load)
    total = np.zeros(n); first_token = np.zeros(n); queue_total = np.zeros(n); oracle_ttft_total = np.zeros(n)
    api_calls = counts.copy()
    fallback_duration = np.zeros(n); slm_active = np.zeros(n)

    if mode in ('baseline', 'tier1'):
        out_tokens = BASELINE_OUTPUT_TOKENS if mode == 'baseline' else TIER1_OUTPUT_TOKENS
        oracle_dur, q, ttft, _ = api_call_duration(out_tokens, BASELINE_INPUT_TOKENS if mode == 'baseline' else TIER1_INPUT_TOKENS, n, rng, request_load)
        first_oracle = q + ttft
        total = common + oracle_dur; first_token = common + first_oracle
        queue_total = q; oracle_ttft_total = ttft; api_calls += 1
    elif mode in ('tier3_raw', 'tier1_tier3'):
        total = common + local_render + anchor_dur
        first_token = common + slm_ttft
        queue_total = anchor_q; oracle_ttft_total = anchor_ttft
        slm_active = local_render
    elif mode in ('jit_oracle_raw', 'jit_oracle_capsule'):
        full_out = BASELINE_OUTPUT_TOKENS if mode == 'jit_oracle_raw' else TIER1_OUTPUT_TOKENS
        in_tokens = BASELINE_INPUT_TOKENS if mode == 'jit_oracle_raw' else TIER1_INPUT_TOKENS
        fast_dur, qfast, ttfast, _ = api_call_duration(ORACLE_FAST_RENDER_TOKENS, in_tokens, n, rng, request_load)
        full_dur, qfull, ttfull, _ = api_call_duration(full_out, in_tokens, n, rng, request_load)
        total[success] = common[success] + fast_dur[success]
        first_token[success] = common[success] + qfast[success] + ttfast[success]
        queue_total[success] = qfast[success]; oracle_ttft_total[success] = ttfast[success]
        transition = draw_lognormal(PARAMS['bailout_transition'], n, rng)
        total[bailout] = common[bailout] + transition[bailout] + full_dur[bailout]
        first_token[bailout] = common[bailout] + qfull[bailout] + ttfull[bailout]
        fallback_duration[bailout] = transition[bailout] + full_dur[bailout]
        total[miss] = common[miss] + full_dur[miss]
        first_token[miss] = common[miss] + qfull[miss] + ttfull[miss]
        fallback_duration[miss] = full_dur[miss]
        queue_total[bailout|miss] = qfull[bailout|miss]; oracle_ttft_total[bailout|miss] = ttfull[bailout|miss]
        api_calls[success] += 1; api_calls[bailout] += 1; api_calls[miss] += 1
    elif mode in ('naive', 'unified'):
        full_out = TIER1_OUTPUT_TOKENS
        full_dur, q, ttft, _ = api_call_duration(full_out, TIER1_INPUT_TOKENS, n, rng, request_load)
        first_oracle = q + ttft
        total[success] = common[success] + local_render[success] + anchor_dur[success]
        first_token[success] = common[success] + slm_ttft[success]
        queue_total[success] = anchor_q[success]; oracle_ttft_total[success] = anchor_ttft[success]
        slm_active[success] = local_render[success]
        if mode == 'unified':
            transition = draw_lognormal(PARAMS['bailout_transition'], n, rng)
            halt_elapsed = common + slm_ttft + PARTIAL_LOCAL_TOKENS*slm_tpot
            total[bailout] = halt_elapsed[bailout] + transition[bailout] + full_dur[bailout]
            first_token[bailout] = common[bailout] + slm_ttft[bailout]
            slm_active[bailout] = slm_ttft[bailout] + PARTIAL_LOCAL_TOKENS*slm_tpot[bailout]
            fallback_duration[bailout] = transition[bailout] + full_dur[bailout]
            api_calls[bailout] += 1
        total[miss] = common[miss] + full_dur[miss]
        first_token[miss] = common[miss] + first_oracle[miss]
        fallback_duration[miss] = full_dur[miss]
        queue_total[miss] = q[miss]; oracle_ttft_total[miss] = ttft[miss]
        api_calls[miss] += 1
    else:
        raise ValueError(mode)

    path = np.full(n, 'R3_miss_or_direct_oracle', dtype=object)
    path[success] = 'R1_fast_success'; path[bailout] = 'R2_bailout'
    if mode in ('baseline', 'tier1', 'tier3_raw', 'tier1_tier3'):
        path[:] = 'direct_oracle_or_tier3'
    if mode in ('jit_oracle_raw', 'jit_oracle_capsule', 'unified'):
        theoretical = (ALPHA, P_BAIL, P_MISS)
    elif mode == 'naive':
        theoretical = (NAIVE_ALPHA, 0, 1-NAIVE_ALPHA)
    else:
        theoretical = (0, 0, 1)
    return {
        'Configuration': name, 'N': n, 'p_R1_sim': float(success.mean()), 'p_R2_sim': float(bailout.mean()), 'p_R3_sim': float(miss.mean()),
        'p_R1_model': theoretical[0], 'p_R2_model': theoretical[1], 'p_R3_model': theoretical[2],
        'Mean_API_calls_per_request': float(api_calls.mean()), 'Mean_anchor_calls_per_request': float(counts.mean()), 'P95_anchor_calls_per_request': float(np.quantile(counts, .95)),
        'Mean_fallback_component_s': float(fallback_duration.mean()), 'Mean_SLM_active_s': float(slm_active.mean()),
        'Mean_E2E_s': float(total.mean()), 'P50_E2E_s': float(np.quantile(total, .50)), 'P95_E2E_s': float(np.quantile(total, .95)),
        'P50_TTFT_s': float(np.quantile(first_token, .50)), 'P95_TTFT_s': float(np.quantile(first_token, .95)),
    }


def expected_billed_output_tokens(mode: str) -> float:
    if mode == 'baseline': return float(BASELINE_OUTPUT_TOKENS)
    if mode == 'tier1': return float(TIER1_OUTPUT_TOKENS)
    if mode == 'jit_oracle_raw': return ALPHA*ORACLE_FAST_RENDER_TOKENS + (P_BAIL+P_MISS)*BASELINE_OUTPUT_TOKENS
    if mode == 'jit_oracle_capsule': return ALPHA*ORACLE_FAST_RENDER_TOKENS + (P_BAIL+P_MISS)*TIER1_OUTPUT_TOKENS
    if mode == 'tier3_raw': return N_TIER3_RAW*ANCHOR_K
    if mode == 'tier1_tier3': return N_TIER1_TIER3*ANCHOR_K
    if mode == 'naive': return (1-NAIVE_ALPHA)*TIER1_OUTPUT_TOKENS+NAIVE_ALPHA*N_ANCHOR_CONDITIONAL*ANCHOR_K
    if mode == 'unified': return (P_BAIL+P_MISS)*TIER1_OUTPUT_TOKENS+ALPHA*N_ANCHOR_CONDITIONAL*ANCHOR_K
    raise ValueError(mode)
