# Requirements Traceability Matrix

This document maps system and observability requirements from foundational multi-agent specifications and our presentation (*RM_MID.pdf*) to their concrete implementations, modules, and automated tests.

---

## 1. Traceability: Core Observability Architecture

| Paper Reference | Concept / Requirement | Implementation Module | Automated Test | Status |
|---|---|---|---|---|
| **Section 1 & 2.1** | Non-Identifiability of Delegated Execution | `backend/evaluation/baselines.py` (B0, B1, B2) | `tests/test_baselines_evaluation.py` | Implemented |
| **Section 2.2** | Orthogonality of Authority vs. Causal Flows | `backend/graphs/execution_graph.py`, `backend/graphs/authority_graph.py` | `tests/test_graphs_reconstruction.py` | Implemented |
| **Section 2.3 (R1)** | Persistent Delegation Context | `backend/schemas/events.py` (`delegation_id`), `backend/gateway/gateway.py` | `tests/test_gateway.py` | Implemented |
| **Section 2.3 (R2)** | Authority-Causality Separation | `backend/schemas/events.py` (`trace_id` vs `delegation_id`) | `tests/test_gateway.py` | Implemented |
| **Section 2.3 (R3)** | Delegation Lineage Closure | `backend/storage/event_store.py` (`get_delegation_closure`) | `tests/test_storage.py` | Implemented |
| **Section 2.3 (R4)** | Cross-System Action Normalization | `backend/schemas/events.py` (`ActionSemantic`), `backend/gateway/tool_wrapper.py` | `tests/test_gateway.py` | Implemented |
| **Section 4.1 & App. B** | Common Information Model (CIM) Envelope | `backend/schemas/events.py` (`CIMEvent`) | `tests/test_gateway.py` | Implemented |
| **Section 4.3 (I1-I5)** | Invariants (Consistency, Separation, Closure, Normalization, Binding) | `backend/gateway/gateway.py` (`mint_delegation`, `verify_delegation`) | `tests/test_gateway.py`, `tests/test_storage.py` | Implemented |
| **Section 5.1 & Table 2** | Blast Radius Query Calculation | `backend/storage/event_store.py` (`get_blast_radius`) | `tests/test_storage.py` | Implemented |
| **Section 6 & App. C** | Observability Gateway Boundary | `backend/gateway/gateway.py`, `backend/gateway/tool_wrapper.py` | `tests/test_gateway.py` | Implemented |
| **Section 7.2 (W1-W3)** | Disconnected Subtasks, Spawning, Retries | `backend/evaluation/synthetic_generator.py` (Scenarios 3, 4, 5) | `tests/test_baselines_evaluation.py` | Implemented |

---

## 2. Traceability: Presentation & Research Extension (RM_MID.pdf)

| Slide Reference | Proposed Feature / Requirement | Implementation Module | Automated Test | Status |
|---|---|---|---|---|
| **Slide 5** | Core Concept: Transparency without Chain-of-Thought | `backend/gateway/privacy.py` | `tests/test_privacy_capture.py` | Implemented |
| **Slide 6** | Challenge Mitigation: Ephemeral Communication | `backend/schemas/interaction.py`, `backend/storage/event_store.py` | `tests/test_storage.py` | Implemented |
| **Slide 8 (RQ1-4)** | Four Core Research Questions | `backend/evaluation/metrics.py`, `backend/evaluation/runner.py` | `tests/test_baselines_evaluation.py` | Implemented |
| **Slide 10** | Three-Graph Transparency Model (Pillars 1, 2, 3) | `backend/graphs/three_graphs.py`, `backend/graphs/interaction_graph.py` | `tests/test_graphs_reconstruction.py` | Implemented |
| **Slide 11** | 9-Layer System Architecture | `backend/` full hierarchical stack | Full Test Suite | Implemented |
| **Slide 12** | Formatted Interaction Record Schema | `backend/schemas/interaction.py` (`InteractionRecord`) | `tests/test_storage.py` | Implemented |
| **Slide 12** | 9 Interaction Types | `backend/schemas/events.py` (`InteractionType`) | `tests/test_storage.py` | Implemented |
| **Slide 12** | Three Capture Tiers (Level 1, 2, 3) | `backend/gateway/privacy.py`, `backend/gateway/gateway.py` | `tests/test_privacy_capture.py` | Implemented |
| **Slide 13** | 8 Experimental Scenarios | `backend/evaluation/synthetic_generator.py` (Scenarios 1-8) | `tests/test_baselines_evaluation.py` | Implemented |
| **Slide 14** | Provenance Layer & W3C PROV Integration | `backend/provenance/tracker.py`, `backend/schemas/workflow.py` | `tests/test_provenance.py` | Implemented |
| **Slide 15** | Comparative Baselines (B0, B1, B2, B3, B4) | `backend/evaluation/baselines.py` | `tests/test_baselines_evaluation.py` | Implemented |
| **Slide 16** | Limitations, Blindspots, and Risk Accounting | `docs/LIMITATIONS.md` | Documented | Implemented |

---

## 3. Implementation Status Summary

- **Fully Implemented Features:**
  - Common Information Model (CIM) schema and SQLite persistence.
  - Central Observability Gateway with authoritative delegation minting and action normalization.
  - Persistent Inter-Agent Interaction Graph with per-message identity and downstream consequence tracking.
  - Three-Graph Transparency Model ($G_{exec}$, $G_{auth}$, $G_{interact}$).
  - Provenance DAG with backward lineage tracing.
  - Three-tier privacy-aware capture engine with automated PII regex redaction.
  - LangGraph 4-agent orchestration with conditional routing and clarification branching.
  - 8 benchmark experimental scenarios and 5 comparative baseline models.
  - Full-stack interactive Streamlit research dashboard with Plotly visualization.
  - FastAPI backend with complete OpenAPI specification.

- **Partial Support / Graceful Fallback:**
  - Local LLM inference: Fully supported when Ollama is available; deterministic fallback when unavailable.

- **Future Research Directions:**
  - Cryptographic hardware-enforced TPM / SGX attestation of gateway delegation tokens.
  - Automated continuous drift anomaly detection models on production SIEM streams.

