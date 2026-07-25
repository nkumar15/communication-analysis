# Dataset Changelog

## Version History

### v1 (Current - Active) - 2025-12-27
**File**: `gold_dataset.json`  
**Size**: 10 test cases  
**Status**: ✅ Active

**Question Types**:
- Financial calculations (QoQ/YoY growth rates)
- Segment analysis with comparisons
- Multi-step reasoning
- Balance sheet queries
- Cash flow analysis
- Complex numerical extraction from tables

**Purpose**: Production-grade evaluation with comprehensive question coverage

**Baseline Results**:
- Faithfulness: 90%
- Answer Relevancy: 100%
- Contextual Recall: 24.3%
- Cost: $0.33 per run

---

### v0 (Legacy - Archived) - 2025-12-26
**File**: `gold_dataset_legacy.json`  
**Size**: 20 test cases  
**Status**: 🗄️ Archived (reference only)

**Question Types**:
- Simple lookup queries ("What was X?")
- Single-number extractions
- Basic comparisons

**Purpose**: Initial proof-of-concept testing

**Historical Results**:
- Baseline: F=100%, R=100%, CR=66.7%
- Table Parser: F=100%, R=100%, CR=100%
- Hybrid Search: F=100%, R=100%, CR=100%

**Why Archived**: Questions too simple, not representative of production complexity. v1 provides better evaluation rigor.

**Location**: `data/experiments/v0_legacy/`

---

## Version Upgrade Policy

Create a new dataset version when:
- ✅ Adding new question types not covered in current version
- ✅ Discovering production edge cases
- ✅ Quarterly document refresh (new financial reports)

Do NOT create a new version for:
- ❌ Just improving existing question wording
- ❌ Fixing typos or formatting
- ❌ Minor corrections (update in-place)

## Experiment Comparison Rules

**✅ Valid Comparisons**:
- Any experiments on the SAME dataset version
- Example: baseline_v1 vs top_k_10_v1

**❌ Invalid Comparisons**:
- Experiments across DIFFERENT dataset versions
- Example: baseline_v0 vs baseline_v1 (different difficulty)

**Note**: When upgrading dataset version, re-run baseline with new version to establish new comparison point.
