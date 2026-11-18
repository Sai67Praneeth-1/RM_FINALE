# RM_FINALE — Independent Code and Research Audit

**Audit basis:** the user-supplied `RM_FINALE.zip` as received November 18, 2026. Read-only review, isolated tests, and examination of a temporary copy of its SQLite database.

## Executive verdict

**Promising functional prototype; not yet research-ready.** The archive contains meaningful implementation of structured events, delegation records, graph reconstruction, provenance tracking, workflow topologies, a React frontend, and evaluation scripts. But the most important scientific claims are not adequately substantiated. Several benchmark numbers are constants or derived from baseline labels; interaction capture does not consistently mediate agent-to-agent data flow; live-model identity/fallback is misreported; and authority/privacy controls accept invalid inputs.


## Verification performed

| Check | Finding |
|---|---|
| Python syntax compilation | Passed for extracted backend/tests/scripts/dashboard Python files |
| Selected isolated pytest suite | 24 passed (storage, gateway, privacy, dataset manager, baseline evaluation) |
| Full test suite | Not verified: test collection fails in the auditing environment without `langgraph` installed |
| Deterministic research runner | Executed, creating 40 records (8 scenarios x 5 baselines); does **not** establish scientific validity |
| Archived SQLite DB | `PRAGMA quick_check`: `ok` |
| Saved DB row counts | 124 workflow runs, 557 delegations, 886 interactions, 296 execution events, 69 artifacts, 414 provenance edges |
| Graph reconstruction from one saved run | Execution: 3 nodes/0 edges; Authority: 9/11; Interaction: 4/6; Provenance: 6/6. Functionality exists, but relational validity still needs testing |
| Frontend | React source and built `dist` are present. Rebuild not verified under Linux: bundled Windows-oriented `node_modules` lacked required Linux native build binding. Test with `npm ci && npm run build` on the intended Windows system. |
| Live Gemini or Hugging Face execution | Not verified: no remote service calls were made during audit |
| README test claim | States 26/26. There are 48 explicitly named `test_*` functions in test modules (some additional tests may be generated differently); claim should be checked against a clean complete suite. |

## Findings by severity

### CRITICAL — 1. Communication is logged, but not necessarily delivered and consumed
**Evidence:** `backend/agents/base.py:25-27,70-72`, `backend/gateway/interceptor.py:42-105`, `backend/orchestration/langgraph_workflow.py:96-189`, and the absence of calls to `read_inbox()` elsewhere.
- By default every `BaseAgent` creates its own `InstrumentedChannel`, each with a separate in-memory mailbox.
- The sender's channel stores a message for a recipient, but the recipient's separate channel has no such message.
- The LangGraph workflow mostly supplies `research_data` and `analysis_data` to the next node through shared workflow state instead of receiving actual message envelopes.
- **Reproduced:** a message was persisted, but `recipient.read_inbox()` returned no message when both agents were constructed using default channels.
**Repair:** provide one shared runtime-owned channel/transport per workflow, explicitly receive message envelopes in nodes, preserve delivery/acknowledgment status, and correlate message IDs with the task-state values actually used by receiving agents.

### CRITICAL — 2. Benchmark results are not properly measured
**Evidence:** `backend/evaluation/runner.py:50,68-77`; `backend/evaluation/metrics.py:26-35,38-62,102-110,141-148,151-219`; `docs/RESEARCH_EVALUATION.md` and README benchmark claims.
- B4 is constructed with an empty provenance-edge list but its completeness is labeled `1.0` based on the baseline name.
- Latency p50 and p95 are fixed values, not measured around gateway operations.
- Query operation counts are dictionary constants, not instrumentation of actual reconstruction queries.
- Privacy exposure scores are fixed assumptions, not measured retained sensitive-field rates.
- `compute_storage_metrics` largely serializes the same event record for all baselines, not the different actual telemetry the baseline would retain; its `total_kb` uses a fixed multiplier of 50.
- The delegation-accuracy function chooses a majority ground-truth label separately for each predicted cluster. **Reproduced:** it returns 1.0 even if all events are wrongly split into singleton clusters. This makes some reported perfect scores uninformative.
- The ambiguity proxy `max(1,partition_count-true_delegation_count+1)` does not compute the number of candidate authority mappings consistent with observations.
- `compute_interaction_completeness(0,0)` returns 1.0, which is defensible as a vacuous convention but should be excluded or marked N/A in cross-scenario means instead of presenting it as observed communication capture.
**Repair:** build separate baseline-visible telemetry datasets; independently capture ground truth; use proper clustering/attribution metrics (pairwise precision/recall, adjusted Rand index, and authority-assignment accuracy), evaluate actual event/provenance matching, measure latency around execution with many repetitions, and measure bytes written by each configuration.

### CRITICAL — 3. Live-model simulation misidentifies execution
**Evidence:** `backend/orchestration/hf_simulation.py:294-352`; `backend/agents/llm_client.py:237-258,284-326`.
- The feature is labeled **Hugging Face Router**, but `run_agent_turn()` calls Gemini. `init_hf_client()` returns `None`; the model names in the UI are not proof those models were invoked.
- If Gemini fails, code silently generates a deterministic fallback dialogue, then a `CIMEvent` is recorded with `tool_name='huggingface_router'` and `ActionOutcome.SUCCESS`.
- The simulation uses a fixed round-robin loop (`agents[turn % len(agents)]`) rather than LangGraph agent choice.
- The recorded interaction may therefore look like successful external multi-agent communication even when the external call failed.
**Repair:** model-provider adapter with explicit `provider`, `requested_model`, `actual_model`, `mode=live|fallback`, actual success/failure, and native request IDs. Never call synthetic output a successful real provider operation. Keep simulation visibly labeled.

### HIGH — 4. Delegation identity/authority is not enforced
**Evidence:** `backend/gateway/gateway.py:38-82,87-148,181-184`.
- If a parent delegation is unknown, the gateway flags metadata but still mints a child delegation.
- `record_interaction` and `execute_tool_call` look up delegation but continue if absent. Claimed sender/agent identity is accepted as input without validated binding to the delegation owner/scope.
- **Reproduced:** an interaction with an entirely unknown delegation ID was persisted.
- A UUID is not automatically a cryptographically authenticated bearer token.
**Repair:** reject or quarantine unverified delegations, validate scope and principal-agent consistency, and explicitly document the intended trust model.

### HIGH — 5. Privacy policy misses supplied summaries and metadata
**Evidence:** `backend/gateway/privacy.py:107-134`; `backend/gateway/gateway.py:124-145`.
- A supplied `semantic_summary` gets `strip_chain_of_thought` but not `redact_sensitive_content`.
- **Reproduced:** a supplied email remained in a Level-2 summary.
- `resource_refs` and arbitrary `metadata` can include sensitive identifiers and bypass message-body redaction.
- Capture level is mutable on a shared gateway singleton (`set_capture_level`) and can be overwritten by concurrent runs.
**Repair:** redact/validate all persisted fields and make capture policy immutable per run/request.

### HIGH — 6. Temporal and trace causality is inconsistent
**Evidence:** `backend/agents/researcher.py:42-85`; `backend/gateway/gateway.py:132-134,203-220`; `backend/graphs/cross_graph_validator.py:89-128`.
- The research agent puts its **prior** dataset-reading event inside `downstream_action_ids` of a **later** outgoing message. That is a source/upstream event, not a downstream consequence.
- Cross-graph validation verifies only that a downstream ID exists, not whether the cited action happened after the interaction or belonged to the proper workflow/delegation.
- Trace and span IDs may be independently generated instead of propagated from a common root. A single run's event identifiers should be consistent, not guessed afterward.
**Repair:** represent distinct `triggered_by`, `derived_from`, `responds_to`, and delegation relationships and test directionality and time constraints.

### MEDIUM — 7. Workflow filtering and graph scope
**Evidence:** `backend/storage/event_store.py:186-218`.
- The `interactions` table has no explicit `workflow_id`; filtering by workflow uses `task_id LIKE '%id%' OR conversation_id LIKE '%id%'`.
- This is fragile against accidental matches and makes relational integrity/indexing harder.
**Repair:** add `workflow_id` as an indexed foreign key and migrate existing records. Keep `conversation_id` and task references as separate exact identifiers.

### MEDIUM — 8. Dynamic autonomy claims exceed implementation
**Evidence:** `backend/orchestration/langgraph_workflow.py:278-305`; `backend/api/routes.py:1205-1340`; `backend/orchestration/squad_workflows.py`.
- LangGraph workflows exist and execute tool operations, but a large share of routing uses preset pipelines and keyword-based rules.
- General Gemini chat requests bypass multi-agent orchestration.
- This is appropriate for a controlled benchmark if labeled as such; it should not be called fully autonomous, open-domain dynamic delegation.
**Repair:** maintain reproducible deterministic workflows, and add a distinct real orchestration mode where an agent chooses constrained tool/delegation actions and each choice becomes an observable event.

### MEDIUM — 9. Local-only security and packaging
**Evidence:** `backend/api/main.py:30-36`; chat list/get/delete and gateway settings endpoints in `backend/api/routes.py`.
- Wildcard CORS and lack of API authentication would be inappropriate if deployed beyond a trusted local environment.
- Archive size is inflated by bundled Git history and `node_modules`. There is also no reliable dependency-lock workflow for Python packages using unbounded minimum versions.
**Repair:** keep services bound to localhost during research, add access control before deployment, implement least-privilege permissions, use Python lock/pinning, and distribute sanitized source.

## What deserves credit

- Actual persistent SQLite event tables and meaningful stored records.
- Functional gateway APIs, typed event schemas, distinct delegation records, graph builders, and provenance functions.
- Multiple workflow topologies, domain-specific agent roles, and actual sample datasets.
- React dashboard source and build outputs, plus a separate Streamlit dashboard.
- Automated tests for individual components and reproducible synthetic scenarios.
- Explicit intent to keep hidden model reasoning out of the captured data.

## Recommended repair sequence

2. **Fix communication semantics:** shared channel, receive/acknowledge, envelope-linked state changes, separate observable traffic from simulated traffic.
3. **Fix execution provenance:** real provider identity/outcomes, explicit trace propagation, correct upstream/downstream causality.
4. **Enforce gateway authority:** verified delegation owner, parent linkage, task/scope checks, reject unknown IDs.
5. **Fix privacy:** sanitize summaries, resource refs, event metadata; pin capture level per run.
6. **Rebuild evaluation from ground truth:** correct baselines, labels, matching, metrics, real latency/storage and query instrumentation; ensure B3 vs B4 comparison isolates Interaction Graph value.
7. **Run full verification on Windows:** clean Python environment, `pip install -r requirements.txt`, `npm ci`, backend/test/frontend build; use real Gemini calls only where needed; record pass/fail without inventing successes.
8. **Only then finalize paper/README** with appropriately qualified results and limitations.

## Research readiness judgment

This is a **meaningful engineering prototype, not yet validated research evidence**. The strongest present claim is that the app can persist structured communication records and build three related graph views. The strongest **unverified** claim is that doing so improves faithful reconstruction over a proper CIM-only baseline at acceptable measured overhead. That claim needs controlled experiments and correct metrics.

A fair subjective assessment based on source review (not a grading rubric): engineering implementation **6.5/10**; research evaluation credibility **2.5/10**; overall research-demo readiness **around 5/10**. These numbers are judgments, not objective measurements.
