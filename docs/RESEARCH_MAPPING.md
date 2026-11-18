# Research Mapping: Baselines vs. Our Proposed Architecture

This document provides a rigorous academic distinction between classical observability baselines and our proposed Three-Graph transparency architecture.

---

## 1. Classical Delegation Baselines: Common Information Model (CIM-Only)

### Foundational Principles:
1. **The Non-Identifiability Proof:**
   Demonstrates that standard distributed tracing (e.g., OpenTelemetry) and enterprise SIEM audit logs cannot uniquely identify which actions occurred under which delegated authority because authority context is structurally orthogonal to causal control-flow traces.
2. **Common Information Model (CIM):**
   A structured event model binding a durable `delegation_id` to every execution event at runtime capture, accompanied by normalized action verbs (`read`, `write`, `share`, `invoke`).
3. **Dual Graphs:**
   Models execution as two distinct structures:
   - **Execution Graph ($G_{exec}$):** Causal trace/span hierarchy describing what code ran.
   - **Authority Graph ($G_{auth}$):** Delegation DAG describing who authorized what.
4. **Observability Gateway:**
   A capture boundary intercepting tool operations, minting delegation tokens, and enforcing lineage closure.

### Limitations of CIM-Only Baselines:
CIM baselines restrict focus to single-agent and multi-tool execution events. They do **not** capture or model inter-agent communication, semantic message payloads, multi-hop conversational handoffs, or evidence provenance layers.

---

## 2. Our Proposed Research Architecture: The Three-Graph Transparency Model

**Source Document:** *RM_MID.pdf* (IIIT Allahabad Research Methodology Presentation)  
**Authors:** BB Kasi Ram, Sai Praneeth, Raghunath

### What Our Architecture Contributes Beyond Prior Baselines:

```
[Standard CIM Baseline]             [Our Proposed Architecture]
+---------------------------+        +-----------------------------------+
| CIM Execution Events      |        | Persistent Inter-Agent Messages   |
| Tool-Action Normalization |   +    | Interaction Graph (G_interact)    |
| Dual Graphs (G_exec/auth) |        | Three-Graph Transparency Model    |
| Delegation Minting        |        | W3C PROV Evidence Lineage Layer   |
+---------------------------+        | 3-Tier Privacy-Aware Capture      |
                                     +-----------------------------------+
```

### Detailed Structural Innovations:
1. **Persistent Inter-Agent Interaction Graph ($G_{interact}$ - Pillar 3):**
   - While the paper treated multi-agent composition primarily as spawned child traces, our extension makes inter-agent communication a first-class observable structure.
   - Captures verified senders and receivers, 9 distinct interaction types (`request`, `response`, `delegation`, `result`, `information_transfer`, `escalation`, `handoff`, `clarification`, `warning`).
   - Preserves per-message identity rather than collapsing all exchanges into a single edge.
   - Correlates each interaction with its downstream execution consequences (`downstream_action_ids`).

2. **The Three-Graph Transparency Model:**
   Integrates all three orthogonal views:
   - **Execution Graph:** Causal execution.
   - **Authority Graph:** Delegation authority.
   - **Interaction Graph:** Inter-agent communication.

3. **Provenance Layer (W3C PROV Alignment):**
   Connects source resources (datasets, files), tool outputs, inter-agent messages, derived findings, and final reports into an inspectable evidence DAG. Answers: *"Where did this finding originate, which message transferred it, and what source data backed it?"*

4. **Three-Tier Privacy-Aware Capture:**
   Provides an explicit solution to the privacy vs. observability dilemma:
   - **Level 1 (Metadata Only):** Structural visibility without storing payloads.
   - **Level 2 (Metadata + Summary):** Permitted semantic summaries and resource labels (default).
   - **Level 3 (Full Observable Content):** Full observable message bodies with automated regex-based PII redaction.
   - **Critical Scope Boundary:** Strictly forbids capturing private neural chain-of-thought or internal model weights.

---

## 3. Comparative Summary

| Capability | Standard Tracing (B0) | SIEM / Heuristic (B2) | CIM-Only (B3) | Our Proposed Extension (B4) |
|---|---|---|---|---|
| **Delegation Attribution** | Not possible | Heuristic / ambiguous | Direct ($Amb=1$) | Direct ($Amb=1$) |
| **Tool Action Normalization** | No | Partial | Yes (Tier-1 & Tier-2) | Yes (Tier-1 & Tier-2) |
| **Inter-Agent Message Capture** | None | None | None | **Persistent & Structured** |
| **Interaction Graph** | None | None | None | **Dedicated Graph ($G_{interact}$)** |
| **Downstream Consequence Linking**| Causal only | Causal only | Causal only | **Interaction $\rightarrow$ Action Binding** |
| **Multi-Hop Provenance DAG** | None | None | None | **Full W3C PROV Lineage** |
| **Configurable Privacy Tiers** | N/A | N/A | None (metadata only)| **3 Configurable Tiers** |
| **Query Operations Burden** | 8 ops | 9 ops | 2 ops | **1 op** |

