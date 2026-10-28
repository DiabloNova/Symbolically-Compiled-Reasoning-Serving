# SCRS five-arm live pilot — jarvis-zai-5arm-one-row-20261027-causality

**Evidence class:** exploratory live-model observation; not confirmatory evidence.  
**Task:** legal_reasoning_causality; one deterministic test row, sample seed 20261027.  
**Requested model route:** `zai/glm-4-flash`; provider-reported model: `glm-4-flash`.  
**Provider endpoint:** `https://api.jarvisclaw.ai/v1`; no API key used.  
**Pacing:** 5 seconds minimum between transport attempt starts.  
**Physical calls:** 8 attempts / 8 confirmed generations.  
**Reported usage:** 4237 input tokens, 308 output tokens.  
**Observed pattern:** baseline and capsule-only were correct; graph-only and Anchor-only ablations and the composed path were incorrect on this one selected row. This is a single-case observation, not a general claim that composition harms performance.  
**Limitations:** n=1; descriptive only. It does not establish statistical significance, semantic preservation, production latency, or production cost.