# Transparency and Openness in Agentic AI Systems
### Capturing Inter-Agent Communication, Execution Context, and Delegation

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-red.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A complete research implementation and observability platform addressing the **Non-Identifiability Problem** in multi-agent autonomous AI systems. Built in `C:\Users\prane\OneDrive\Desktop\RM_FINALE`.

---

## 1. Research Background & Contributions

### The Theoretical Foundation
Based on *"Observability for Delegated Execution in Agentic AI Systems"* by **Abhinav Mishra & Kumar Sharad** (Splunk, Cisco Inc., arXiv:2606.09692v1, June 2026).
- **The Non-Identifiability Problem:** Standard distributed tracing (OpenTelemetry) and audit logs cannot uniquely identify which actions occurred under which delegated authority because authority context is orthogonal to causal control-flow traces.
- **Common Information Model (CIM):** An event schema that binds durable `delegation_id` contexts to tool operations at execution capture.
- **Dual Graphs:** Execution Graph ($G_{exec}$) and Authority Graph ($G_{auth}$).

### Our Proposed Research Extension
Presented in *RM_MID.pdf* (IIIT Allahabad Research Methodology Presentation by BB Kasi Ram, Sai Praneeth, Raghunath):
1. **Persistent Inter-Agent Interaction Graph ($G_{interact}$):** Captures observable agent-to-agent communication, semantic summaries, 9 interaction types, and explicit downstream tool execution consequences.
2. **Three-Graph Transparency Model:** Correlates Execution, Authority, and Interaction graphs into a cohesive observability view.
3. **Provenance Layer (W3C PROV):** Connects final report findings back to intermediate messages, tool executions, and origin datasets.
4. **Three-Tier Privacy-Aware Capture:** Configurable capture levels (Level 1: Metadata Only, Level 2: Metadata + Summary, Level 3: Full Content with PII redaction). **Never captures hidden neural chain-of-thought.**

---

## 2. System Architecture & The 4 Specialized Agents

```
                        +---------------------------------------------+
                        |           Human Principal / User            |
                        +---------------------------------------------+
                                               |
                                     (Initiates / Delegates)
                                               v
                        +---------------------------------------------+
                        |        Layer 2: Coordinator Agent           |
                        +---------------------------------------------+
                                    /                     \
                      (Delegates) /                         \ (Handoff)
                                 v                           v
     +----------------------------------+       +----------------------------------+
     |     Layer 3: Research Agent      |       |      Layer 3: Report Agent       |
     +----------------------------------+       +----------------------------------+
                        \                                   ^
       (Transfers Info)  \                                 / (Transfers Findings)
                          v                               /
                        +----------------------------------+
                        |      Layer 3: Analysis Agent     |
                        +----------------------------------+
                                         |
     ====================================v==========================================
     |                    CENTRAL OBSERVABILITY GATEWAY                            |
     |   - Mints/Verifies Delegation Tokens (Invariants I1, I3, I5)                |
     |   - Normalizes Tool Actions (Read, Write, Search, Share, Invoke)            |
     |   - Enforces 3-Tier Privacy Capture & PII Redaction                         |
     ===============================================================================
                                         |
                                         v
                         +-------------------------------+
                         |  Persistent SQLite Event Store|
                         |  (Survives Process Restarts)  |
                         +-------------------------------+
                                         |
             +---------------------------+---------------------------+
             |                           |                           |
             v                           v                           v
     [Execution Graph]           [Authority Graph]          [Interaction Graph]
      "What happened?"        "Under whose authority?"   "Who talked to whom & next?"
```

---

## 3. Quick Start & Windows Setup

### Prerequisites
- Python 3.10, 3.11, 3.12, 3.13, or 3.14 installed and added to `PATH`.
- (Optional for live LLM inference) [Ollama](https://ollama.com/download/windows).

### 1-Click Launch (Recommended)
Double-click `start_project.bat` or run:
```powershell
.\start_project.bat
```
This automatically starts:
- **FastAPI Backend Server:** `http://127.0.0.1:8000`
- **Streamlit Research Dashboard:** `http://127.0.0.1:8501`

### Manual Startup Commands
1. **Install Dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```
2. **Start the API Server:**
   ```powershell
   python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
   ```
3. **Start the Research Dashboard:**
   ```powershell
   streamlit run dashboard/app.py --server.port 8501
   ```

---

## 4. Setting Up Ollama (Optional Local LLM)

If you wish to run genuine live local LLM inference rather than the deterministic demo mode:
1. Download Ollama for Windows from [ollama.com](https://ollama.com/download/windows) and install it.
2. Open a terminal and pull the recommended lightweight model:
   ```powershell
   ollama pull qwen2.5:3b
   ```
3. The platform autodetects Ollama at `http://127.0.0.1:11434` and enables live inference.
4. *If Ollama is not running, the platform operates seamlessly in Deterministic Demonstration Mode.*

---

## 5. Verification & Testing

### Run Complete Pytest Suite (26/26 Tests)
```powershell
pytest tests/ -v
```
All 26 automated unit and integration tests pass, covering:
- SQLite persistence and restart survival.
- Authoritative delegation minting and lineage closure.
- Privacy capture tiers and sensitive PII regex redaction.
- LangGraph 4-agent workflow orchestration with clarification branching.
- Three-Graph model reconstruction ($G_{exec}$, $G_{auth}$, $G_{interact}$).
- W3C PROV provenance DAG and backward lineage traversal.
- 5 comparative baseline reconstruction algorithms across 8 scenarios.
- FastAPI REST API endpoints.

### Run End-to-End Demonstration Script
```powershell
python scripts/run_demo.py
```

### Run Benchmark Evaluation Suite
```powershell
python scripts/run_evaluations.py
```
Executes all 8 scenarios across all 5 baselines and exports:
- `data/generated/evaluation_results.json`
- `data/generated/evaluation_summary.csv`

---

## 6. Research Documentation

Exhaustive academic documentation is available in the `docs/` folder:
- [Architecture & 9-Layer Stack](docs/ARCHITECTURE.md)
- [Research Mapping: Mishra & Sharad vs. Our Extension](docs/RESEARCH_MAPPING.md)
- [Requirements Traceability Matrix](docs/REQUIREMENTS_TRACEABILITY.md)
- [Event Schema Specification](docs/EVENT_SCHEMA.md)
- [Research Evaluation, Scenarios & Empirical Results](docs/RESEARCH_EVALUATION.md)
- [Academic Demonstration Guide](docs/DEMO_GUIDE.md)
- [System Limitations, Boundary Conditions & Risks](docs/LIMITATIONS.md)

---

## 7. Comparative Benchmark Summary

| Baseline Architecture | Delegation Accuracy | Interaction Completeness | Ambiguity ($Amb$) | Provenance Completeness | Query Operations | Storage / Event |
|---|---|---|---|---|---|---|
| **B0: Trace-Only** | 71.4% | **0.0%** | 3.8 | 0.0% | 8 ops | 341 B |
| **B1: Time-Window** | 58.2% | **0.0%** | 6.4 | 0.0% | 10 ops | 341 B |
| **B2: Hybrid Heuristic** | 82.5% | **0.0%** | 2.6 | 0.0% | 9 ops | 400 B |
| **B3: CIM-Only (2026)** | **100.0%** | **0.0%** | **1.0** | 0.0% | 2 ops | 588 B |
| **B4: Proposed Three-Graphs** | **100.0%** | **100.0%** | **1.0** | **100.0%** | **1 op** | 742 B |

*Our proposed extension resolves the 0% interaction visibility of existing platforms while maintaining sub-0.3 ms p95 gateway latency.*

