# Experiment Version Registry

## Versioning Scheme
`experiment_{dataset_version}_{number}_{config_name}`

Example: `experiment_v1_004_top_k_10`

---

## Completed Experiments

### Dataset v0 (Legacy - Archived)
| Exp # | ID | Config Change | F | R | CR | Date | Status |
|-------|-------|---------------|---|---|----|------|--------|
| 0 | baseline_v0 | Naive (top_k=5, vector only) | 100% | 100% | 66.7% | 2025-12-26 | 🗄️ Archived |
| 1 | expr1_v0_table_parser | Table markdown extraction | 100% | 100% | 100% | 2025-12-26 | 🗄️ Archived |
| 2 | expr2_v0_hybrid_search | BM25+Vector RRF | 100% | 100% | 100% | 2025-12-26 | 🗄️ Archived |
| 3 | expr3_v0_reranking | Cross-encoder (MiniLM) | 100% | 100% | 100% | 2025-12-26 | 🗄️ Archived |

**Files**: `backend/scripts/nse/data/experiments/v0_legacy/deepeval-*.txt`

---

### Dataset v1 (Current - Active)
| Exp # | ID | Config Change | F | R | CR | Cost | Date | Status |
|-------|-------|---------------|---|---|----|------|------|--------|
| 4 | baseline_v1 | Baseline (top_k=5, vector, gpt-5-nano) | 90% | 100% | 24% | $0.33 | 2025-12-27 | ✅ Complete |
| 5 | expr5_v1_top_k_10 | top_k: 5 → 10 (Judge: gpt-4o-mini) | 63% | 100% | 85% | $0.05 | 2025-12-27 | ✅ Complete |
| 6 | expr6_v1_top_k_15 | top_k: 10 → 15 (Judge: gpt-4o-mini) | 48% | 100% | 85% | $0.05 | 2025-12-27 | ✅ Regression |
| 7 | expr7_v1_hybrid_search | Re-run BM25+Vector on v1 | - | - | - | $0.33 | Queued | ⏸️ |
| 8 | expr8_v1_table_chunking | Table markdown preservation | - | - | - | $0.33 | Queued | ⏸️ |
| 9 | expr9_v1_reranking | Rerank top 20→10 (Cross-Encoder) | 47% | 96% | 90% | $0.05 | 2025-12-27 | ⚠️ Mixed |

---

## Experiment Naming Convention

**Format**: `experiment_v{dataset_version}_{sequential_number}_{config_description}`

**Sequential Numbers**:
- v0: 0-3 (archived)
- v1: 4+ (active)
- Future versions continue sequence

**Examples**:
- ✅ `experiment_v1_005_top_k_10`
- ✅ `expr5_v1_top_k_10` (shorthand)
- ❌ `top_k_10_v1_001` (old format - don't use)

---

## Next Experiment

**Experiment #10: Generator Upgrade? / Prompt Tuning?**
- **Analysis**: recall is high (90%) but Faithfulness low (47%). Generator (gpt-5-nano) might be hallucinating.
- **Hypothesis**: Better prompt or stronger model (gpt-4o-mini) for generation will fix Faithfulness.
- **ID**: `expr10_v1_generator_tuning`

---

## Update Protocol

After each experiment:
1. Run evaluation
2. Extract metrics from `experiment_logs.json`
3. Update this registry table
4. Commit results with message: `experiment #X: {description} - CR: {score}%`
5. Decide: continue if improvement, revert if regression

---

## Notes

- v0 experiments used simple 20-question dataset
- v1 experiments use comprehensive 10-question dataset  
- **Results NOT comparable across versions!**
- Continuous numbering maintains experiment history
