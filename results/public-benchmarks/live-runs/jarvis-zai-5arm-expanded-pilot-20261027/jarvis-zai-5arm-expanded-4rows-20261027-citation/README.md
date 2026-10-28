# Expanded live five-arm pilot — citation_prediction_classification

**Run:** `jarvis-zai-5arm-expanded-4rows-20261027-citation`  
**Evidence status:** exploratory follow-up, four new paired rows; not confirmatory or publication-ready evidence.  
**Provider:** requested `zai/glm-4-flash`, provider-reported `glm-4-flash`; no API key used.  
**Sampling:** seed `20261028`; selected test indices `[58,70,87,104]`; previously exposed index 37 explicitly excluded.  
**Rate control:** 5s minimum interval between provider attempt starts.

| Arm | Correct / n | Accuracy | Invalid outputs |
|---|---:|---:|---:|
| baseline | 0/4 | 0% | 0 |
| capsule_anchor_no_graph | 0/4 | 0% | 0 |
| capsule_graph_no_anchor | 0/4 | 0% | 0 |
| capsule_only | 0/4 | 0% | 0 |
| compiled_graph_gates | 0/4 | 0% | 0 |

Physical provider usage: 32 transport attempts, 32 confirmed generations, 11210 input tokens, 553 output tokens. Billed cost remains NR. This is one task with n=4; it is still a small descriptive sample and must not be treated as confirmatory evidence.

Raw case records, event log, full metrics, run manifest, all five predictions, and capsule/graph traces are preserved in this directory.