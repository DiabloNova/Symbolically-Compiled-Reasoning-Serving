#!/usr/bin/env python3
"""Generate SCRS recalculation-v1 CSV and manifest. Latencies are synthetic, not measured."""
from __future__ import annotations
import csv, json, math
from pathlib import Path
import numpy as np
from scenario_core import *

def exact_token_cost(input_tokens, output_tokens, local_host=False):
    if input_tokens is None or output_tokens is None:
        return None
    cost=(input_tokens*ORACLE_IN_PRICE_PER_M + output_tokens*ORACLE_OUT_PRICE_PER_M)*REQUESTS_PER_COST_BLOCK/1_000_000
    if local_host:
        cost += LOCAL_HOST_MONTHLY_USD/(MONTHLY_REQUESTS/REQUESTS_PER_COST_BLOCK)
    return round(cost, 2)

def validate_exact_invariants():
    assert math.isclose(ALPHA + P_BAIL + P_MISS, 1.0, abs_tol=1e-12)
    assert math.isclose(ALPHA, 0.6201, abs_tol=1e-12)
    assert math.isclose(P_BAIL, 0.1599, abs_tol=1e-12)
    assert math.isclose(P_MISS, 0.22, abs_tol=1e-12)
    assert math.isclose(expected_billed_output_tokens('unified'), 881.9097, abs_tol=1e-9)
    assert math.isclose(expected_billed_output_tokens('naive'), 513.66, abs_tol=1e-9)
    assert math.isclose(expected_billed_output_tokens('jit_oracle_raw'), 1462.252, abs_tol=1e-9)
    assert math.isclose(expected_billed_output_tokens('jit_oracle_capsule'), 1435.659, abs_tol=1e-9)
    assert math.isclose(exact_token_cost(BASELINE_INPUT_TOKENS, BASELINE_OUTPUT_TOKENS), 398.50, abs_tol=1e-9)
    assert math.isclose(exact_token_cost(TIER1_INPUT_TOKENS, TIER1_OUTPUT_TOKENS), 260.50, abs_tol=1e-9)

def exact_token_cost(input_tokens, output_tokens, local_host=False):
    if input_tokens is None or output_tokens is None:
        return None
    cost=(input_tokens*ORACLE_IN_PRICE_PER_M + output_tokens*ORACLE_OUT_PRICE_PER_M)*REQUESTS_PER_COST_BLOCK/1_000_000
    if local_host:
        cost += LOCAL_HOST_MONTHLY_USD/(MONTHLY_REQUESTS/REQUESTS_PER_COST_BLOCK)
    return round(cost, 2)

configs=[
 ('Baseline (raw RAG + full Oracle)','baseline'),
 ('Tier I only (capsules)','tier1'),
 ('Tier II only (hardened JIT, Oracle-rendered)','jit_oracle_raw'),
 ('Tier III only (entropy interrupt, raw context)','tier3_raw'),
 ('Tier I + III (no JIT)','tier1_tier3'),
 ('Tier I + II (no entropy interrupts)','jit_oracle_capsule'),
 ('SCRS without transfer gate (similarity-only)','naive'),
 ('Unified SCRS (I + II + III)','unified'),
]
validate_exact_invariants()
rows=[]
for idx,(name,mode) in enumerate(configs):
    sim=simulate_config(name,mode,idx)
    sim['Mode']=mode
    if mode in ('baseline','tier1'): sim['share_without_full_fallback']=0.0
    elif mode in ('tier3_raw','tier1_tier3'): sim['share_without_full_fallback']=1.0
    elif mode=='naive': sim['share_without_full_fallback']=NAIVE_ALPHA
    else: sim['share_without_full_fallback']=ALPHA
    sim['Expected_billed_Oracle_output_tokens_per_request']=round(expected_billed_output_tokens(mode),3)
    sim['Expected_billed_Oracle_input_tokens_per_request']=BASELINE_INPUT_TOKENS if mode=='baseline' else (TIER1_INPUT_TOKENS if mode=='tier1' else None)
    local=mode in ('tier3_raw','tier1_tier3','naive','unified')
    sim['Cost_USD_per_10000_requests']=exact_token_cost(sim['Expected_billed_Oracle_input_tokens_per_request'],sim['Expected_billed_Oracle_output_tokens_per_request'],local_host=local)
    sim['Cost_status']='Calculated from declared token means' if sim['Cost_USD_per_10000_requests'] is not None else 'NOT CALCULABLE: route-specific billed Oracle input tokens / cached-vs-uncached Anchor split not fully specified'
    rows.append(sim)
with (OUT/'recalculated_table2.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
probability={
 'p_hit':P_HIT,'p_halt_conditional_on_hit':P_HALT_COND,'p_fast_path':ALPHA,'p_bailout':P_BAIL,'p_miss':P_MISS,
 'sum':ALPHA+P_BAIL+P_MISS,'proof':'p_fast=p_hit*(1-p_halt); p_bail=p_hit*p_halt; p_miss=1-p_hit',
 'anchor_mean_conditional_on_fast_path':N_ANCHOR_CONDITIONAL,
 'unified_anchor_mean_unconditional_per_request':ALPHA*N_ANCHOR_CONDITIONAL,
 'unified_anchor_output_tokens_per_request':ALPHA*N_ANCHOR_CONDITIONAL*ANCHOR_K,
 'unified_expected_billed_output_tokens_using_capsule_fallback_mean':expected_billed_output_tokens('unified'),
 'naive_expected_billed_output_tokens_using_capsule_fallback_mean':expected_billed_output_tokens('naive'),
 'baseline_cost_per_10000':exact_token_cost(BASELINE_INPUT_TOKENS,BASELINE_OUTPUT_TOKENS),
 'tier1_cost_per_10000':exact_token_cost(TIER1_INPUT_TOKENS,TIER1_OUTPUT_TOKENS),
 'notes':[
  'P50/P95 are synthetic Monte Carlo outputs under declared latency distributions, not measurements.',
  'Latency dependence uses a shared request-load latent factor with rho_queue_ttft=0.5, rho_oracle_request_load_tpot=0.5, and rho_slm_ttft_tpot=0.5 plus independent Gaussian residuals; the earlier perfect-correlation attempt was discarded.',
  'Full Oracle output means are 2380 tokens raw and 2310 capsule; 900-token fast-path Oracle rendering is an explicit assumption.',
  'The 1.4 Anchor-call mean is conditional on successful fast-path completion; unconditional expected count is alpha_eff*1.4.',
  'share_without_full_fallback is a configuration-specific table value, not alpha_eff; it is 1.0 for no-JIT Tier III ablations.',
  'Input-token/cost values are omitted where route-specific Oracle input tokens and the stable-prefix/uncached-suffix split are unavailable.',
  'Actual client retries, batching, and provider billing remain unverified.'
 ]}
with (OUT/'recalculation_manifest.json').open('w',encoding='utf-8') as f:
    json.dump({'status':'synthetic_monte_carlo_plus_exact_analytic_subcalculations_not_empirical','seed':SEED,'n_requests_per_configuration':N,'parameters':PARAMS,'correlations':{'rho_queue_ttft':RHO_QUEUE_TTFT,'rho_oracle_request_load_tpot':RHO_ORACLE,'rho_slm_ttft_tpot':RHO_SLM},'model':probability,'results':rows},f,indent=2,ensure_ascii=False)
print(f"R1={ALPHA:.4f}; R2={P_BAIL:.4f}; R3={P_MISS:.4f}; sum={ALPHA+P_BAIL+P_MISS:.4f}")
for r in rows:
    print(f"{r['Configuration']}: P50={r['P50_E2E_s']:.3f}s P95={r['P95_E2E_s']:.3f}s output={r['Expected_billed_Oracle_output_tokens_per_request']} cost={r['Cost_USD_per_10000_requests']}")
