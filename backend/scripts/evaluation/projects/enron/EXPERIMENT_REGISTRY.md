# Enron Experiment Version Registry

## Versioning Scheme
`experiment_{dataset_version}_{number}_{config_name}`

Example: `experiment_v1_001_baseline`

---

## Completed Experiments

### Dataset v1 (Current - Active)
| Exp # | ID | Config | F | R | CR | Date | Status |
|-------|-------|--------|---|---|----|------|--------|
| 001 | baseline_v1 | enron_baseline_v1 | 0.70 | 0.63 | 0.76 | 2026-01-04 | Baseline. Good recall, retrieval gaps. |

---

## Experiment Naming Convention

**Format**: `experiment_v{dataset_version}_{sequential_number}_{config_description}`

**Sequential Numbers**:
- v1: 1+ (active)

## Next Experiment
- Baseline v1 (Top-k=10, Vector Only)
