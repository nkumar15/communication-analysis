# Ingestion Pipeline

## Overview

| Attribute | Details |
|-----------|---------|
| **Goal** | Efficiently ingest communication dumps and execute the multi-step risk detection pipeline |
| **Target Persona** | David Zheng (IT Admin), Dr. Priya Sharma (Risk Officer) |
| **Permission** | `surveillance:admin` |

## The Multi-Step Pipeline

In accordance with banking standards for high-volume data, the ingestion process is split into separate **Detection** and **Aggregation** phases to ensure accuracy and noise reduction.

### Step 1: Risk Identification (Potential Incidents)
Every single message ingested is immediately passed through the **[Surveillance Controls](./surveillance_controls.md)** engine.
- **Action**: The system checks if the message matches any active **Risk Indicators**.
- **Output**: Each match is recorded as a **"Risk Signal"** (Potential Incident). 
- **Retention**: All Risk Signals (including low-confidence or non-alerting ones) are retained for historical **Risk Scoring** and audit, even if they don't result in an Alert.
- **Effective Dating**: Detection only uses Surveillance Controls that are **active** for the message's timestamp. Updates to controls apply to **future data only** (no retroactive signal generation).

### Step 2: Alert Aggregation (End-of-Day Batch)
After the daily data dump is fully processed, an aggregation job runs to generate actionable Alerts.
- **Constraint**: **1 Alert per [Sender] per [Day] per [Risk Indicator]**. 
- **Example**: If a sender triggers "Load Shifting" 5 times in a day, only **one** alert is created for that specific indicator.
- **Context**: Although the alert is sender-based, the Alert Details view will show the **entire conversation thread** for all flagged messages to provide full context.

### Idempotency & Re-Ingestion
To handle data corrections or duplicate uploads:
- **Identifier Hash**: Every message is hashed (content + timestamp + sender) to prevent duplicate Step 1 processing.
- **Daily Flush & Replace**: If Step 2 (Aggregation) is re-run for a specific date, existing "Open" alerts for that date/sender/indicator are updated/refreshed, while "Addressed" alerts are preserved to maintain the audit trail.
- **Job Locking**: Only one aggregation job can run per tenant per day.

## Features/Widgets

| Feature | Description | Data Source |
|---------|-------------|-------------|
| **Pipeline Monitor** | Visual track of Step 1 (Processing) vs Step 2 (Aggregation). | `ingestion_logs` |
| **Signal Tally** | Counter showing "Signals Detected" vs "Alerts Created" (Noise filter ratio). | `risk_signals` / `alerts` |
| **Re-process Control** | Force re-run of Alert Aggregation without re-ingesting raw data. | `tasks/aggregation` |

## User Stories

1. **As a Surveillance Risk Officer**, I want to see how many "Potential Incidents" were identified before aggregation so I can tune my control thresholds.
2. **As an Analyst**, I want the aggregated alert to contain all related messages so I can see the full evidence path in one view.
3. **As an IT Admin**, I want Step 1 (Ingestion) to be fast, while Step 2 (AI Analysis) runs asynchronously.

## UX Rules

- **Status Separation**: Distinctly show if a job failed at the Ingestion step or the Aggregating step.
- **Volume Indicators**: Display a "Fan-in" chart showing how thousands of messages result in hundreds of signals and ultimately tens of alerts.

## Technical Implementation

- **Step 1 Worker**: High-speed parallel scanning (Keyword/Regex).
- **Step 2 Worker**: Enrichment and Aggregation (GenAI/Semantic/Metadata clustering).

See [Architecture Diagram](../technical/architecture.md) for data flow.
