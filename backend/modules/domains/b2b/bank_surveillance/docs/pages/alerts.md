# Alerts

## Overview

| Attribute | Details |
|-----------|---------|
| **Goal** | The daily workflow hub where analysts live |
| **Target Persona** | Marcus Johnson (Surveillance Analyst) |
| **Permission** | `surveillance:read` |

## Features/Widgets

| Feature | Description |
|---------|-------------|
| Alert List | Sortable table with risk type, confidence, region, team |
| Risk Type Filter | Insider Trading, Market Abuse, Information Barrier, Evasion |
| Date Range Filter | Today, Last 7 days, Custom range |
| Region Filter | APAC, EMEA, Americas, Global |
| Bulk Actions | Close, Escalate, Convert to Case |
| Quick Stats | Open alerts count, critical count, oldest alert age |

## User Stories

1. **As a Surveillance Analyst**, I want to filter alerts by risk type so that I can focus on my assigned category.
2. **As a Surveillance Analyst**, I want to bulk-close low-confidence alerts so that I can manage my queue efficiently.
3. **As a Surveillance Manager**, I want to see alert aging metrics so that I can ensure SLA compliance.
4. **As a Surveillance Analyst**, I want to escalate alerts with one click so that I can quickly involve senior reviewers.
5. **As a Surveillance Analyst**, I want to convert an alert directly to a case so that I can begin formal investigation.

## UX Rules

- Alerts are business objects, not raw emails
- Never show a simple "email list" – always contextualize
- Color-coded risk levels (Red/Amber/Green)

## Demo Hook

> Alert examples: "Potential earnings leakage – High confidence", "Abnormal secrecy spike in Executive communications"

## Wireframe

![Alerts Wireframe](../wireframes/alerts.png)

## Technical Implementation

See [API Reference](../technical/api.md#alerts)
