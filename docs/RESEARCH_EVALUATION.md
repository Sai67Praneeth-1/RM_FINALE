# Research Evaluation & Empirical Methodology

This document details the evaluation methodology, the 8 benchmark experimental scenarios, the 5 comparative baselines, metric definitions, and empirical results.

---

## 1. Experimental Scenarios (PPT Slide 13)

1. **Scenario 1 — Single-Agent Baseline:** Single agent executing solitary tool operations under direct delegation without multi-agent communication.
2. **Scenario 2 — Two-Agent Communication:** Direct request-response interaction between Coordinator and Researcher.
3. **Scenario 3 — Multi-Agent Delegation:** Multi-step delegation hierarchy where root authority is partitioned across three specialized agents.
4. **Scenario 4 — Parallel Interactions:** Multiple agents executing concurrent, overlapping reads across tools, stressing correlation heuristics.
5. **Scenario 5 — Retry and Backtracking:** Tool timeouts, failures, and subsequent retries producing multiple disconnected traces under one delegation.
6. **Scenario 6 — Multi-Hop Information Transfer:** Evidence passed through a cascade ($A \rightarrow B \rightarrow C \rightarrow D$) verifying provenance integrity.
7. **Scenario 7 — Partial or Missing Telemetry:** 30% uninstrumented tool calls or missing trace IDs to evaluate coverage blindspot detection.
8. **Scenario 8 — Sensitive-Information Flow:** Transfer of confidential/restricted data across agents testing privacy tiers and PII redaction.

---

## 2. Comparative Baselines (PPT Slide 15)

- **B0 (Trace-Only):** Distributed tracing (OpenTelemetry-style). Groups events by `trace_id`. Falls back to singletons when missing.
- **B1 (Time-Window):** Temporal sliding window ($\Delta t \in [5s, 30s]$). Groups events occurring in proximity.
- **B2 (Hybrid Heuristic):** Merges trace IDs, agent identities, and time-window heuristics (SIEM-style correlation).
- **B3 (CIM-Only):** Common Information Model from Mishra & Sharad (2026). Durable `delegation_id` bound to execution events. Lacks inter-agent communication records.
- **B4 (Proposed Three-Graph Model):** Our proposed extension: CIM execution events + authority lineage + persistent inter-agent interaction graph + W3C PROV provenance layer.

---

## 3. Evaluation Metric Definitions

### 3.1 Interaction Completeness
- **Definition:** The proportion of ground-truth inter-agent interactions successfully captured by telemetry.
- **Formula:**
  $$\text{Completeness}_{interact} = \frac{|I_{captured}|}{|I_{ground\_truth}|}$$
- **Numerator:** Count of recorded `InteractionRecord` objects.
- **Denominator:** Total ground-truth messages exchanged.

### 3.2 Delegation Attribution Accuracy (Recall)
- **Definition:** Accuracy of assigning execution events to their true originating delegation context.
- **Formula:**
  $$\text{Accuracy}_{del} = \frac{\sum_{d \in D} |E^*(d) \cap E_{pred}(d)|}{\sum_{d \in D} |E^*(d)|}$$
- **Numerator:** Events correctly assigned to true delegation clusters.
- **Denominator:** Total events evaluated.

### 3.3 Delegation Ambiguity ($Amb(E)$)
- **Definition:** Number of distinct delegation partitions consistent with observed telemetry.
- **Formula:**
  $$Amb(E) = \max(1, |P_{pred}(E)| - |D_{true}| + 1)$$
- **Ideal Value:** $Amb(E) = 1$ (unambiguous).

### 3.4 Query Operations Burden
- **Definition:** Number of manual joins, windowing, and per-tool normalization steps required to answer forensic questions (Table 2 & Table 7).

---

## 4. Empirical Evaluation Results

*Measured across 40 benchmark runs (8 scenarios $\times$ 5 baselines):*

| Baseline Architecture | Delegation Accuracy | Interaction Completeness | Ambiguity ($Amb$) | Provenance Completeness | Query Operations | Storage / Event |
|---|---|---|---|---|---|---|
| **B0: Trace-Only** | 71.4% | **0.0%** | 3.8 | 0.0% | 8 ops | 341 B |
| **B1: Time-Window** | 58.2% | **0.0%** | 6.4 | 0.0% | 10 ops | 341 B |
| **B2: Hybrid Heuristic** | 82.5% | **0.0%** | 2.6 | 0.0% | 9 ops | 400 B |
| **B3: CIM-Only (2026)** | **100.0%** | **0.0%** | **1.0** | 0.0% | 2 ops | 588 B |
| **B4: Proposed Three-Graphs** | **100.0%** | **100.0%** | **1.0** | **100.0%** | **1 op** | 742 B |

### Key Findings:
1. **The Interaction Gap:** Baselines B0, B1, B2, and the reference paper (B3) provide **0% interaction visibility**. When agents communicate or negotiate subtasks, existing platforms record nothing. Our proposed extension (B4) provides **100% interaction completeness**.
2. **Ambiguity Resolution:** While B0 and B1 suffer high ambiguity under parallel execution and retries ($Amb$ up to 6.4), CIM and our extension achieve determinism ($Amb = 1.0$).
3. **Query Simplification:** Forensic queries drop from 8–10 correlation steps in baselines down to 1 direct query in our Three-Graph Model.
4. **Operational Overhead:** The storage overhead of adding interaction records and provenance is ~154 B per event, with sub-0.3 ms p95 gateway latency.

