# User Personas

## Overview

Three core personas represent the primary users of the Bank Surveillance platform. Each has distinct needs, workflows, and success metrics.

---

## Persona 1: Sarah Chen – Head of Compliance

### Profile
| Attribute | Value |
|-----------|-------|
| **Title** | Head of Compliance, APAC Region |
| **Experience** | 18 years in financial compliance |
| **Daily Focus** | Strategic oversight, regulatory relationships |
| **Tech Comfort** | Executive-level (dashboard consumer) |

### Goals
- Prove surveillance program effectiveness to regulators
- Reduce regulatory risk and avoid enforcement actions
- Demonstrate ROI of compliance technology investments
- Maintain pre-audit readiness at all times

### Pain Points Addressed
| Pain Point | How Platform Solves It |
|------------|------------------------|
| Spreadsheet-based case tracking | Case Management with full lifecycle |
| Ad-hoc reporting to regulators | Audit & Reports with exportable evidence |
| Blind spots in communication patterns | Dashboard with risk themes |
| Lack of AI explainability | Alert Detail with documented reasoning |

### Key Pages
1. **Dashboard** – Morning risk overview
2. **Audit & Reports** – Regulator evidence generation
3. **Cases** – High-priority case monitoring
4. **Policies** – Policy effectiveness review

### Success Metrics
- Mean time to case closure < 5 days
- Zero regulator findings on surveillance gaps
- 100% audit trail completeness

### Typical Workflow
```
Morning Check-in (Dashboard)
    ↓
Review High-Priority Cases (Cases)
    ↓
Prepare Weekly Board Report (Audit & Reports)
    ↓
Quarterly Policy Review (Policies)
```

---

## Persona 2: Marcus Johnson – Surveillance Analyst

### Profile
| Attribute | Value |
|-----------|-------|
| **Title** | Senior Surveillance Analyst |
| **Experience** | 5 years in trade surveillance |
| **Daily Focus** | Alert triage, investigation, case building |
| **Tech Comfort** | Power user, keyboard shortcuts |

### Goals
- Efficiently process daily alert queue
- Build watertight investigation evidence
- Minimize false positive fatigue
- Leverage AI to accelerate investigations

### Pain Points Addressed
| Pain Point | How Platform Solves It |
|------------|------------------------|
| Manual email review across systems | Investigation Workspace unified view |
| Missing context on alerts | AI-generated conversation summaries |
| Repetitive documentation tasks | Auto-generated investigation notes |
| No similar case reference | Historical pattern matching |

### Key Pages
1. **Alerts** – Daily queue management
2. **Investigation Workspace** – Deep dive analysis
3. **Search & RAG** – Ad-hoc research
4. **Cases** – Evidence documentation

### Success Metrics
- Alerts reviewed per day > 50
- False positive rate < 30%
- Average investigation time < 45 minutes
- Case quality score > 4.5/5

### Typical Workflow
```
Morning: Review assigned alerts (Alerts)
    ↓
Investigate high-confidence alerts (Alert Detail → Investigation)
    ↓
Research patterns using RAG (Search & RAG)
    ↓
Document findings and escalate (Cases)
    ↓
End of day: Bulk close low-risk items (Alerts)
```

---

## Persona 3: Dr. Priya Sharma – Risk Officer

### Profile
| Attribute | Value |
|-----------|-------|
| **Title** | Head of Market Conduct Risk |
| **Experience** | 12 years in risk management, PhD in Financial Economics |
| **Daily Focus** | Risk pattern detection, policy calibration |
| **Tech Comfort** | Analytical, data-driven |

### Goals
- Detect emerging risk patterns before they materialize
- Calibrate surveillance policies to reduce noise
- Ensure consistent risk appetite across regions
- Build predictive risk models

### Pain Points Addressed
| Pain Point | How Platform Solves It |
|------------|------------------------|
| Static, unconfigurable rules | Policy & Risk Typology Builder |
| Regional policy inconsistency | Region-specific policy activation |
| No visibility into model behavior | Policy impact preview |
| Delayed risk signal detection | Dashboard emerging themes |

### Key Pages
1. **Policies** – Rule configuration and tuning
2. **Dashboard** – Emerging risk patterns
3. **Teams & Access** – Regional access review
4. **Search & RAG** – Pattern exploration

### Success Metrics
- Policy false positive rate < 25%
- Emerging risk detection lead time > 7 days
- Regional policy consistency score > 90%
- Zero missed true positives

### Typical Workflow
```
Weekly: Review emerging risk themes (Dashboard)
    ↓
Analyze alert patterns (Policies → Impact Preview)
    ↓
Tune policy thresholds (Policies)
    ↓
Monthly: Cross-region policy alignment (Teams & Access)
    ↓
Quarterly: Backtest policies on historical data (Policies)
```

---

## Persona Comparison Matrix

| Attribute | Sarah (Executive) | Marcus (Analyst) | Priya (Risk) |
|-----------|-------------------|------------------|--------------|
| **Page Depth** | Surface (dashboards) | Deep (workspaces) | Medium (config) |
| **Frequency** | Daily check-in | All-day | Weekly deep-dive |
| **Primary Action** | Review & approve | Investigate & document | Configure & analyze |
| **Success Measure** | Regulator readiness | Case throughput | Risk accuracy |
| **AI Usage** | Consume summaries | Interactive analysis | Policy tuning |

---

## Persona-Based Feature Prioritization

| Feature | Sarah | Marcus | Priya |
|---------|-------|--------|-------|
| Dashboard widgets | ⭐⭐⭐ | ⭐ | ⭐⭐ |
| Alert bulk actions | ⭐ | ⭐⭐⭐ | ⭐ |
| Investigation workspace | ⭐ | ⭐⭐⭐ | ⭐⭐ |
| AI explainability | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Policy builder | ⭐ | ⭐ | ⭐⭐⭐ |
| Audit exports | ⭐⭐⭐ | ⭐ | ⭐ |
| Region selector | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ |
