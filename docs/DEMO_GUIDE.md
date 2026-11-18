# Academic Demonstration Guide

Step-by-step guide for demonstrating the research prototype to a professor, advisor, or evaluator.

---

## 1. Quick Startup

### On Windows:
1. Double-click `start_project.bat` (or open PowerShell in the project directory):
   ```powershell
   .\start_project.bat
   ```
2. The launcher will:
   - Check the Python environment and dependencies.
   - Detect local Ollama service status (or gracefully enable Deterministic Demo Mode).
   - Start the FastAPI Observability Backend on `http://127.0.0.1:8000`.
   - Start the Streamlit Research Dashboard on `http://127.0.0.1:8501`.

---

## 2. Recommended 7-Step Demonstration Flow

### Step 1: System Overview & Telemetry State
- Navigate to **"1. Overview"** in the Streamlit sidebar.
- Show the metric cards: Total Workflows, Active Agents (4), Inter-Agent Messages, and Tool CIM Events.
- Highlight the pie chart showing event distributions across the 4 specialized agents.

### Step 2: Live Multi-Agent Execution in Agent Workspace
- Navigate to **"2. Agent Workspace"**.
- Point out the target dataset dropdown (`customer_complaints.csv` or `system_access_logs.csv`).
- Show the two execution modes:
  - `deterministic_demo`: Reproducible, standalone evaluation mode.
  - `live_ollama`: Live local LLM execution if Ollama is running.
- Click **"🚀 Execute Multi-Agent Workflow"**.
- Watch the live execution progress:
  1. Agent A (Coordinator) mints delegations and assigns subtasks.
  2. Agent B (Researcher) extracts records through the Observability Gateway.
  3. Agent C (Analyst) asks clarification and computes metrics.
  4. Agent D (Reporter) synthesizes the final Markdown report.
- Inspect the generated report with executive summary, metric table, and explicit evidence citations.

### Step 3: Inspect Real Inter-Agent Communication Timeline
- Navigate to **"3. Communication Timeline"**.
- Explain that these are **genuine observable messages** captured at the gateway boundary, not simulated hardcoded UI text.
- Filter by agent (`agent_coordinator`) or interaction type (`delegation`, `clarification`, `information_transfer`).
- Open an interaction details expander to show the bound `delegation_id`, `conversation_id`, and downstream tool action IDs.

### Step 4: The Three-Graph Transparency Model Explorer
- Navigate to **"4. Interactive Graph Explorer"**.
- Explain the theoretical foundation:
  - **Tab 1: Execution Graph ($G_{exec}$)** — Shows the causal tool events and span linkages (*"What happened?"*).
  - **Tab 2: Authority Graph ($G_{auth}$)** — Shows the delegation tree from Principal $\rightarrow$ Root $\rightarrow$ Sub-delegations (*"Under whose authority?"*).
  - **Tab 3: Interaction Graph ($G_{interact}$ — OUR EXTENSION)** — Shows real inter-agent communication flows, message types, and downstream action consequences (*"Who communicated with whom and what happened next?"*).
- Show how per-message identity is preserved rather than collapsed into a single edge.

### Step 5: Provenance & Evidence Explorer
- Navigate to **"5. Provenance Explorer"**.
- Select the latest generated report artifact.
- Display the **W3C PROV Provenance DAG**: show how the final report is connected directly back to the analysis tool output, research finding, and original CSV file.
- Inspect the backward lineage table.

### Step 6: Empirical Research Evaluation
- Navigate to **"7. Research Evaluation"**.
- Click **"🔄 Re-run Benchmark Suite"** to demonstrate live computation across all 8 experimental scenarios and 5 baselines.
- Highlight the key research findings:
  - Baselines B0, B1, B2, and the reference paper (B3) have **0% interaction completeness**.
  - Our proposed model (B4) achieves **100% interaction completeness** and resolves delegation ambiguity ($Amb = 1.0$).
  - Query construction effort is reduced from 8–10 operations to 1 direct query.

### Step 7: Architecture, CIM Foundation & Boundary Limits
- Navigate to **"8. Architecture & Docs"**.
- Review the comparison table between the Common Information Model baseline and our research architecture.
- Emphasize the critical scope boundary: **we strictly avoid capturing private neural chain-of-thought or model weights, focusing purely on observable communications and actions.**

