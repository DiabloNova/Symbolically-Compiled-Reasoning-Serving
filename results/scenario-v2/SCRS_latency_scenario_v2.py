#!/usr/bin/env python3
"""SCRS latency scenario v2: source-informed interrupt/call accounting.

IMPORTANT: Synthetic Monte Carlo, NOT implementation telemetry. The manuscript's
reference implementation is stated to be withheld until acceptance; no runtime
logs or executable implementation were available for this run.

Run: python SCRS_latency_scenario_v2.py
Requires: numpy, pandas, openpyxl, matplotlib
"""
from __future__ import annotations
import math, csv
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

OUT = Path(__file__).parent
N = 100_000
SEED = 20261022
rng = np.random.default_rng(SEED)

# Distributions specified as median/P95. These are scenario assumptions unless
# the provenance explicitly says manuscript value. Queue is separated from TTFT.
PARAMS = {
    'ingress': (0.012, 0.030),
    'lookup': (0.004, 0.012),
    'gate': (0.008, 0.020),
    'slm_ttft': (0.024, 0.048),
    'slm_tpot': (0.005, 0.008),
    'api_queue': (0.080, 0.400),
    'oracle_ttft_service': (1.316, 1.850),
    'oracle_tpot': (0.0178, 0.0248),
    'bailout_transition': (0.120, 0.350),
}
RHO_ORACLE = 0.5
RHO_SLM = 0.5
RHO_QUEUE_TTFT = 0.5
ALPHA = 0.62
P_HIT = 0.72 # assumption; paper doesn't provide p_hit
P_BAIL = P_HIT - ALPHA # 0.10 under the source-derived alpha
P_MISS = 1 - P_HIT
NAIVE_ALPHA = 0.78
RENDER_TOKENS = 900 # explicit assumption, not measured
PARTIAL_TOKENS = 300 # explicit assumption, not measured
ANCHOR_K = 5 # manuscript parameter
UNIFIED_INTERRUPTS_PER_SUCCESS = 1.4 # manuscript's reported projected mean per answer
TIER3_INTERRUPTS_PER_ANSWER = 9.6 # manuscript's reported projected mean per answer


def sigma(m,p95): return math.log(p95/m)/1.6448536269514722

def lnorm(m,p95,z): return m*np.exp(sigma(m,p95)*z)

def draw(params,n,z=None):
    if z is None: z=rng.standard_normal(n)
    return lnorm(params[0],params[1],z)

def draw_correlated_pair(p1,p2,rho,n,z_shared=None):
    if z_shared is None: z_shared=rng.standard_normal(n)
    e1=rng.standard_normal(n); e2=rng.standard_normal(n)
    z1=np.sqrt(rho)*z_shared+np.sqrt(1-rho)*e1
    z2=np.sqrt(rho)*z_shared+np.sqrt(1-rho)*e2
    return draw(p1,n,z1),draw(p2,n,z2),z_shared

def api_call_duration(n_tokens, n, shared_load=None):
    # A single Oracle.generateAnchors/solve call is modelled as one blocking API
    # round-trip: queue + service TTFT + n_tokens*TPOT. This is an inference from
    # the manuscript pseudocode, not verified client implementation behavior.
    if shared_load is None: shared_load=rng.standard_normal(n)
    queue, ttft, z = draw_correlated_pair(PARAMS['api_queue'], PARAMS['oracle_ttft_service'], RHO_QUEUE_TTFT, n, shared_load)
    tpot, _, _ = draw_correlated_pair(PARAMS['oracle_tpot'], PARAMS['oracle_tpot'], RHO_ORACLE, n, z)
    return queue + ttft + n_tokens*tpot, queue, ttft, tpot

def sum_serial_anchor_calls(counts, n, request_load):
    total=np.zeros(n); total_queue=np.zeros(n); total_ttft=np.zeros(n)
    total_tpot=np.zeros(n); max_n=int(counts.max()) if n else 0
    # Each interrupt invokes generateAnchors once; k tokens returned per call.
    for j in range(max_n):
        mask=counts>j
        if not mask.any(): continue
        dur,q,t,tp=api_call_duration(ANCHOR_K,int(mask.sum()),request_load[mask])
        total[mask]+=dur; total_queue[mask]+=q; total_ttft[mask]+=t; total_tpot[mask]+=tp
    return total,total_queue,total_ttft,total_tpot

def sim_config(name, tier, alpha=0.0, anchors='none', oracle_tokens=2380):
    n=N
    ingress=draw(PARAMS['ingress'],n)
    lookup=draw(PARAMS['lookup'],n)
    gated = tier in ('jit','unified')
    gate=draw(PARAMS['gate'],n) if gated else np.zeros(n)
    common=ingress+lookup+gate
    slm_ttft, slm_tpot, zslm=draw_correlated_pair(PARAMS['slm_ttft'],PARAMS['slm_tpot'],RHO_SLM,n)
    local_render=slm_ttft+RENDER_TOKENS*slm_tpot
    u=rng.random(n)
    if tier in ('jit','unified'):
        success=u<alpha
        bailout=(u>=alpha)&(u<alpha+P_BAIL)
        miss=~(success|bailout)
    elif tier=='naive':
        success=u<alpha; bailout=np.zeros(n,dtype=bool); miss=~success
    else:
        success=np.zeros(n,dtype=bool); bailout=np.zeros(n,dtype=bool); miss=np.ones(n,dtype=bool)

    counts=np.zeros(n,dtype=int)
    if anchors=='unified':
        # Reported 1.4 interrupts per successful answer, conditional on R1.
        counts[success]=rng.poisson(UNIFIED_INTERRUPTS_PER_SUCCESS,int(success.sum()))
    elif anchors=='tier3':
        # Reported 9.6 interrupts per answer, no JIT admission.
        counts=rng.poisson(TIER3_INTERRUPTS_PER_ANSWER,n)
    api_load=rng.standard_normal(n)  # shared request-level provider-load factor across its API calls
    anchor_dur, anchor_q, anchor_ttft, anchor_tpot=sum_serial_anchor_calls(counts,n,api_load)

    total=np.zeros(n); first_token=np.zeros(n); halt_elapsed=np.zeros(n)
    queue_total=np.zeros(n); oracle_ttft_total=np.zeros(n); oracle_tpot_total=np.zeros(n)
    slm_render_elapsed=np.zeros(n); fallback_elapsed=np.zeros(n)
    api_calls=counts.copy()
    # Full-oracle path call is drawn once per request then selected by path.
    oracle_dur, q, ttft, tpot=api_call_duration(oracle_tokens,n,api_load)
    oracle_first=q+ttft
    if tier in ('baseline','tier1'):
        total=common+oracle_dur
        first_token=common+oracle_first
        queue_total=q; oracle_ttft_total=ttft; oracle_tpot_total=tpot
        api_calls += 1
    elif tier in ('tier3','tier1plus3'):
        # No JIT/fallback in these configurations: SLM renders the answer and
        # each entropy interrupt pauses for one serial anchor API call.
        total=common+local_render+anchor_dur
        first_token=common+slm_ttft
        queue_total=anchor_q; oracle_ttft_total=anchor_ttft; oracle_tpot_total=anchor_tpot
        slm_render_elapsed=local_render
    elif tier=='naive':
        total[success]=common[success]+local_render[success]
        total[miss]=common[miss]+oracle_dur[miss]
        first_token[success]=common[success]+slm_ttft[success]
        first_token[miss]=common[miss]+oracle_first[miss]
        slm_render_elapsed[success]=local_render[success]
        queue_total[miss]=q[miss]; oracle_ttft_total[miss]=ttft[miss]; oracle_tpot_total[miss]=tpot[miss]
        api_calls[miss]+=1
    elif tier in ('jit','unified'):
        total[success]=common[success]+local_render[success]+anchor_dur[success]
        first_token[success]=common[success]+slm_ttft[success]
        slm_render_elapsed[success]=local_render[success]
        queue_total[success]=anchor_q[success]; oracle_ttft_total[success]=anchor_ttft[success]; oracle_tpot_total[success]=anchor_tpot[success]
        # Bail-out: local partial generation and stop first, then incremental transition, then full Oracle.
        bailout_time=draw(PARAMS['bailout_transition'],n)
        halt_elapsed[bailout]=common[bailout]+slm_ttft[bailout]+PARTIAL_TOKENS*slm_tpot[bailout]
        total[bailout]=halt_elapsed[bailout]+bailout_time[bailout]+oracle_dur[bailout]
        first_token[bailout]=common[bailout]+slm_ttft[bailout]
        slm_render_elapsed[bailout]=slm_ttft[bailout]+PARTIAL_TOKENS*slm_tpot[bailout]
        fallback_elapsed[bailout]=bailout_time[bailout]+oracle_dur[bailout]
        queue_total[bailout]=q[bailout]; oracle_ttft_total[bailout]=ttft[bailout]; oracle_tpot_total[bailout]=tpot[bailout]
        # Miss: no partial local rendering; direct full Oracle fallback.
        total[miss]=common[miss]+oracle_dur[miss]
        first_token[miss]=common[miss]+oracle_first[miss]
        fallback_elapsed[miss]=oracle_dur[miss]
        queue_total[miss]=q[miss]; oracle_ttft_total[miss]=ttft[miss]; oracle_tpot_total[miss]=tpot[miss]
        api_calls[bailout]+=1; api_calls[miss]+=1
    else: raise ValueError(tier)

    path=np.full(n,'R3_miss_or_direct_oracle',dtype=object)
    path[success]='R1_fast_success'; path[bailout]='R2_bailout'
    if tier in ('baseline','tier1','tier3','tier1plus3'): path[:]='direct_oracle_or_tier3'
    return {
      'Configuration':name,'Requests simulated':n,'R1 share':float(success.mean()),'R2 bailout share':float(bailout.mean()),'R3/direct share':float(miss.mean()),
      'Mean API calls/request':float(api_calls.mean()),'Mean anchor calls/request':float(counts.mean()),'P95 anchor calls/answer':float(np.quantile(counts,.95)),
      'Mean queue time/request (s)':float(queue_total.mean()),'Median queue time/request (s)':float(np.median(queue_total)),
      'Median summed Oracle TTFT across calls/request (s)':float(np.median(oracle_ttft_total)),
      'Mean Oracle TPOT per API call (s/token)':float(np.mean(np.divide(oracle_tpot_total, api_calls, out=np.zeros_like(oracle_tpot_total), where=api_calls>0))),
      'Mean SLM render component/request (s)':float(slm_render_elapsed.mean()),
      'Mean stop elapsed on bailouts (s)':float(halt_elapsed[bailout].mean()) if bailout.any() else 0.0,
      'Mean fallback component/request (s)':float(fallback_elapsed.mean()),
      'Mean E2E (s)':float(total.mean()),'P50 E2E (s)':float(np.quantile(total,.50)),'P95 E2E (s)':float(np.quantile(total,.95)),
      'P50 TTFT (ms)':float(np.quantile(first_token,.50)*1000),'P95 TTFT (ms)':float(np.quantile(first_token,.95)*1000),
      '_total':total,'_ttft':first_token,'_path':path
    }

configs=[
 ('Baseline','baseline',0,'none',2380),
 ('Tier I only','tier1',0,'none',2310),
 ('Tier II only (no entropy interrupts)','jit',.62,'none',2380),
 ('Tier III only (9.6 interrupts/answer)','tier3',0,'tier3',480),
 ('Tier I + III (9.6 interrupts/answer)','tier1plus3',0,'tier3',360),
 ('Tier I + II (no entropy interrupts)','jit',.62,'none',2310),
 ('Naive unhardened JIT (no gate)','naive',.78,'none',2380),
 ('Unified SCRS (1.4 interrupts per successful answer)','unified',.62,'unified',2310),
]
results=[sim_config(*c) for c in configs]
summary=pd.DataFrame([{k:v for k,v in r.items() if not k.startswith('_')} for r in results])
summary.to_csv(OUT/'SCRS_latency_scenario_v2_results.csv',index=False)

# Synthetic telemetry contract/example, explicitly marked synthetic. One row per config is aggregate, not request-level real logs.
telemetry_fields=[
 ('request_id','Unique ID for each request','Required'),('route','FAST_PATH / HALTED / FALLBACK','Required'),
 ('queue_wait_ms','Queue wait before each API/model execution; record per span','Required'),
 ('oracle_ttft_ms','Oracle request start to first token, excluding queue','Required'),
 ('oracle_tpot_ms_per_token','Oracle generation duration divided by generated tokens','Required'),
 ('anchor_interrupt_count','Number of calls to Oracle.generateAnchors','Required'),
 ('anchor_tokens_total','Total returned anchor tokens','Required'),
 ('anchor_api_round_trips','Actual HTTP/API request count for anchor calls','Required'),
 ('halt_detected_at_ms','Elapsed request time when HALTED_* / entropy halt detected','Required'),
 ('slm_ttft_ms','Local model start to first token','Required'),
 ('slm_render_ms','Total local generation time, excluding pauses for Oracle anchors','Required'),
 ('fallback_started_at_ms','Elapsed time fallback starts','Required'),
 ('fallback_duration_ms','Fallback elapsed duration, excluding prior partial SLM and shared queue if separately logged','Required'),
 ('request_e2e_ms','Request start to final answer completion','Required'),
 ('gate_result','admitted/rejected/halted and reason code','Required'),
 ('provider_request_id','Provider-side request identifier for reconciliation','Recommended'),
 ('cancelled_or_orphaned_calls','Calls not awaited / canceled / timed out','Required'),
]
telemetry_df=pd.DataFrame(telemetry_fields,columns=['Field','Definition','Status'])

assumptions=pd.DataFrame([
 ['Reference code available to inspect','No','Manuscript says code URL withheld until acceptance; no repository or logs provided.'],
 ['Anchor trigger behavior','One Oracle.generateAnchors invocation per interrupt','Source pseudocode lines 22-24; implementation still unverified.'],
 ['One anchor interrupt equals one API round-trip','Scenario assumption / code-inferred','Each interrupt invokes generateAnchors once; cannot verify whether wrapper retries/batches/caches without source.'],
 ['Unified mean interrupts','1.4 per completed fast-path answer','Manuscript projection; treated as conditional mean on R1.'],
 ['Tier I+III mean interrupts','9.6 per answer','Manuscript projection; treated as conditional mean for each answer.'],
 ['Anchor length','5 tokens/call','Manuscript pinned parameter.'],
 ['Fast path alpha','0.62','Manuscript projection, not measured.'],
 ['p_hit','0.72','Scenario assumption; manuscript does not specify it.'],
 ['Queue median/P95','80 ms / 400 ms','Scenario assumption; separate from TTFT.'],
 ['Oracle service TTFT median/P95','1.316 s / 1.850 s','Scenario assumption; chosen to pair with queue distribution near baseline timing.'],
 ['Oracle TPOT median/P95','17.8 / 24.8 ms per token','Previous scenario calibration, not implementation measurement.'],
 ['Local SLM TTFT median/P95','24 / 48 ms','Scenario assumption.'],
 ['Local SLM TPOT median/P95','5 / 8 ms per token','Scenario assumption.'],
 ['Local visible output length','900 tokens','Scenario assumption.'],
 ['Partial SLM output before bail-out','300 tokens','Scenario assumption.'],
 ['Distribution family','Lognormal','Scenario assumption; not fit to production samples.'],
 ['Monte Carlo size / seed','100,000 / 20261022','Fixed for reproducibility.'],
],columns=['Item','Value / decision','Provenance / limitation'])

# Excel snapshots
xlsx=OUT/'SCRS_Latency_Scenario_v2_Snapshot.xlsx'
with pd.ExcelWriter(xlsx,engine='openpyxl') as w:
    assumptions.to_excel(w,sheet_name='Assumptions',index=False)
    summary.to_excel(w,sheet_name='Monte Carlo Results',index=False)
    telemetry_df.to_excel(w,sheet_name='Telemetry Contract',index=False)
    # Path-level result distributions and compact percentiles
    path_rows=[]
    for r in results:
        for label,mask in [('all',np.ones(N,dtype=bool)),('R1_fast_success',r['_path']=='R1_fast_success'),('R2_bailout',r['_path']=='R2_bailout'),('R3_miss_or_direct_oracle',np.isin(r['_path'],['R3_miss_or_direct_oracle','direct_oracle_or_tier3']))]:
            vals=r['_total'][mask]
            if len(vals): path_rows.append({'Configuration':r['Configuration'],'Path':label,'N':len(vals),'Share':len(vals)/N,'Mean E2E (s)':vals.mean(),'P50 E2E (s)':np.quantile(vals,.5),'P95 E2E (s)':np.quantile(vals,.95)})
    pd.DataFrame(path_rows).to_excel(w,sheet_name='Path Quantiles',index=False)
    for ws in w.book.worksheets:
        ws.freeze_panes='A2'; ws.auto_filter.ref=ws.dimensions
        for col in ws.columns:
            letter=col[0].column_letter
            maxlen=max(len(str(c.value or '')) for c in col[:100])
            ws.column_dimensions[letter].width=min(max(maxlen+2,12),55)

# Plot P50/P95 comparison, scenario output only
plt.figure(figsize=(12,6))
x=np.arange(len(summary)); width=.36
plt.bar(x-width/2,summary['P50 E2E (s)'],width,label='P50 scenario')
plt.bar(x+width/2,summary['P95 E2E (s)'],width,label='P95 scenario')
plt.xticks(x,summary['Configuration'],rotation=35,ha='right')
plt.ylabel('End-to-end latency (seconds)')
plt.title('SCRS v2 — Source-informed anchor-call scenario (synthetic, not measured)')
plt.legend(); plt.tight_layout()
plt.savefig(OUT/'SCRS_Latency_Scenario_v2_P50_P95.png',dpi=160); plt.close()

# Machine-readable model provenance and results snapshot
with (OUT/'SCRS_Latency_Scenario_v2_snapshot.json').open('w',encoding='utf-8') as f:
 import json
 json.dump({'status':'synthetic_monte_carlo_not_production_telemetry','seed':SEED,'n':N,'parameters':PARAMS,'alpha_eff':ALPHA,'p_hit_assumption':P_HIT,'p_bail':P_BAIL,'p_miss':P_MISS,'anchor_calls_per_interrupt':'one generateAnchors invocation per interrupt; separate HTTP round-trip inferred but unverified','results':summary.to_dict(orient='records')},f,ensure_ascii=False,indent=2)

print('Status: synthetic scenario only; no implementation telemetry was available.')
print(f'R1={ALPHA:.3f}, R2={P_BAIL:.3f}, R3={P_MISS:.3f}; N={N}, seed={SEED}')
print(summary[['Configuration','Mean API calls/request','Mean anchor calls/request','P50 E2E (s)','P95 E2E (s)','P50 TTFT (ms)']].to_string(index=False))
print('Wrote:',xlsx)
print('Wrote:',OUT/'SCRS_latency_scenario_v2_results.csv')
print('Wrote:',OUT/'SCRS_Latency_Scenario_v2_P50_P95.png')
print('Wrote:',OUT/'SCRS_Latency_Scenario_v2_snapshot.json')
