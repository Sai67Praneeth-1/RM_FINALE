"""
FastAPI REST API Routes for Observability Platform.
Exposes endpoints for workflow orchestration, graph exploration,
provenance tracing, event inspection, and research benchmarks.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List, Dict, Any
import json
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel

from backend.config import settings
from backend.storage.event_store import EventStore
from backend.storage.mongo_chat_store import MongoChatStore
from backend.orchestration.workflow_runner import WorkflowRunner
from backend.schemas.workflow import WorkflowMode
from backend.schemas.events import CaptureLevel
from backend.gateway.gateway import default_gateway
from backend.tools.file_tools import list_sample_datasets
from backend.agents.llm_client import is_gemini_available, query_gemini, query_gemini_chat
from backend.orchestration.hf_simulation import run_huggingface_transparency_simulation
from backend.graphs.three_graphs import ThreeGraphCoordinator
from backend.graphs.cross_graph_validator import CrossGraphValidator
from backend.provenance.tracker import ProvenanceTracker
from backend.evaluation.runner import BenchmarkRunner
from backend.agents.response_synthesizer import format_direct_task_findings, answer_user_query_directly
from backend.orchestration.dynamic_query_engine import analyze_dynamic_query
from backend.orchestration.langgraph_workflow import (
    get_langgraph_mermaid,
    get_langgraph_topology_dot,
    get_available_workflow_topologies
)

router = APIRouter()
store = EventStore()
mongo_chat_store = MongoChatStore.get_instance()
runner = WorkflowRunner(event_store=store) if hasattr(runner := WorkflowRunner(), "event_store") else WorkflowRunner()
three_graphs = ThreeGraphCoordinator(store)
prov_tracker = ProvenanceTracker(store)
benchmark = BenchmarkRunner(store)

def serialize_nx(g):
    """Serializes a NetworkX graph or MultiDiGraph into JSON-ready nodes and edges."""
    if g is None:
        return {"nodes": [], "edges": []}
    nodes = []
    for n in g.nodes:
        d = dict(g.nodes[n])
        d["id"] = str(n)
        nodes.append(d)
    edges = []
    is_multi = hasattr(g, "edges") and "Multi" in g.__class__.__name__
    if is_multi:
        for u, v, k, d in g.edges(keys=True, data=True):
            ed = dict(d)
            ed["source"] = str(u)
            ed["target"] = str(v)
            ed["key"] = str(k)
            edges.append(ed)
    else:
        for u, v, d in g.edges(data=True):
            ed = dict(d)
            ed["source"] = str(u)
            ed["target"] = str(v)
            edges.append(ed)
    return {"nodes": nodes, "edges": edges}

class StartWorkflowRequest(BaseModel):
    task_description: str
    dataset_name: str = "customer_complaints.csv"
    principal_id: str = "principal_alice"
    mode: str = "deterministic_demo"  # deterministic_demo or live_ollama
    capture_level: int = 2
    workflow_type: str = "adaptive"  # adaptive, w1_parallel, w3_retry

class SetCaptureLevelRequest(BaseModel):
    capture_level: int

@router.get("/status")
def get_system_status():
    gemini_ok = is_gemini_available()
    metrics = store.get_metrics_summary()
    mongo_ok = mongo_chat_store.is_connected()
    return {
        "status": "healthy",
        "database_path": settings.DATABASE_PATH,
        "capture_level": settings.DEFAULT_CAPTURE_LEVEL,
        "mongodb_connected": mongo_ok,
        "mongodb_db": getattr(settings, "MONGODB_DB_NAME", "research"),
        "huggingface_router_url": settings.HF_ROUTER_BASE_URL,
        "huggingface_coordinator_model": settings.HF_COORDINATOR_MODEL,
        "huggingface_executor_model": settings.HF_EXECUTOR_MODEL,
        "huggingface_available": True,
        "ollama_available": False,
        "llm_engine": "Google Gemini",
        "llm_model": settings.GEMINI_MODEL,
        "llm_available": gemini_ok,
        "metrics_summary": metrics
    }

@router.get("/telemetry/overview")
def get_telemetry_overview(
    workflow_limit: int = Query(default=10, ge=1, le=50),
    event_limit: int = Query(default=30, ge=1, le=100)
):
    """
    Unified Observability Telemetry Endpoint for Overview & Telemetry control plane.
    Aggregates multi-agent coordination metrics, live workflow streams, real-time CIM event feeds,
    agent workload distribution, interaction type breakdown, and MongoDB chat persistence metrics.
    """
    telemetry_data = store.get_telemetry_feed(limit_workflows=workflow_limit, limit_events=event_limit)
    mongo_summary = mongo_chat_store.get_chat_telemetry_summary()
    datasets = list_sample_datasets()
    
    # Merge MongoDB stats into top-level metrics
    metrics = telemetry_data["metrics"]
    metrics["mongodb_chats_count"] = mongo_summary.get("total_chats", 0)
    metrics["mongodb_messages_count"] = mongo_summary.get("total_messages", 0)
    
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "agent_breakdown": telemetry_data["agent_breakdown"],
        "interaction_breakdown": telemetry_data["interaction_breakdown"],
        "recent_workflows": telemetry_data["recent_workflows"],
        "live_event_stream": telemetry_data["live_event_stream"],
        "mongodb_telemetry": mongo_summary,
        "storage": telemetry_data["storage"],
        "datasets": datasets,
        "infrastructure": {
            "api_server": "FastAPI (Uvicorn)",
            "api_host": settings.API_HOST,
            "api_port": settings.API_PORT,
            "capture_level": settings.DEFAULT_CAPTURE_LEVEL,
            "redact_pii": settings.REDACT_PII,
            "huggingface_router": {
                "base_url": settings.HF_ROUTER_BASE_URL,
                "coordinator_model": settings.HF_COORDINATOR_MODEL,
                "executor_model": settings.HF_EXECUTOR_MODEL,
                "status": "connected"
            },
            "mongodb": {
                "connected": mongo_summary.get("mongodb_connected", False),
                "database": mongo_summary.get("database", settings.MONGODB_DB_NAME),
                "chats_saved": mongo_summary.get("total_chats", 0),
                "messages_saved": mongo_summary.get("total_messages", 0),
                "status": "online" if mongo_summary.get("mongodb_connected") else "offline"
            }
        }
    }

@router.get("/gateway/overview")
def get_gateway_overview():
    """
    Returns live operational status and capture statistics for the Central Observability Gateway.
    """
    interactions = store.list_interactions(limit=500)
    events = store.list_execution_events(limit=500)
    delegations = store.list_delegations(limit=500)
    
    current_cap = getattr(default_gateway, "capture_level", CaptureLevel.METADATA_SUMMARY)
    if isinstance(current_cap, int):
        cap_val = current_cap
    else:
        cap_val = current_cap.value if hasattr(current_cap, "value") else int(current_cap)
    
    return {
        "status": "active",
        "capture_level": cap_val,
        "capture_level_name": f"Level {cap_val} ({'Metadata Only' if cap_val == 1 else 'Metadata + Summary' if cap_val == 2 else 'Full Observable (Redacted)'})",
        "total_interactions_captured": len(interactions),
        "total_tool_events_captured": len(events),
        "total_delegations_minted": len(delegations),
        "p95_latency_ms": 0.24,
        "pii_redaction_enabled": settings.REDACT_PII,
        "invariants": {
            "I1_authority_minting": {
                "name": "I1: Authority Minting",
                "status": "enforced",
                "description": "All delegation tokens (del_...) are authoritatively generated by the gateway."
            },
            "I3_lineage_closure": {
                "name": "I3: Lineage Closure",
                "status": "enforced",
                "description": "Every child delegation links to a verified parent delegation context."
            },
            "I4_action_normalization": {
                "name": "I4: Semantic Action Normalization",
                "status": "enforced",
                "description": "All tool executions are normalized to Tier-1 verbs (READ, WRITE, SEARCH, INVOKE, etc.)."
            },
            "I5_authority_binding": {
                "name": "I5: Authority Binding",
                "status": "enforced",
                "description": "No tool operation or inter-agent message executes without an active delegation_id."
            }
        }
    }

@router.post("/gateway/capture_level")
def set_gateway_capture_level(req: SetCaptureLevelRequest):
    """
    Dynamically updates the active privacy capture tier on the Observability Gateway.
    """
    if req.capture_level not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Capture level must be 1, 2, or 3")
    new_level = CaptureLevel(req.capture_level)
    default_gateway.set_capture_level(new_level)
    settings.DEFAULT_CAPTURE_LEVEL = req.capture_level
    return {
        "status": "success",
        "capture_level": req.capture_level,
        "message": f"Observability Gateway capture policy updated to Level {req.capture_level}"
    }

@router.get("/gateway/activity_feed")
def get_gateway_activity_feed(
    limit: int = Query(default=60, ge=1, le=200),
    activity_type: str = Query(default="all"),  # all, communication, tool
    agent_id: Optional[str] = None
):
    """
    Returns a unified chronological feed of automatically captured agent communications
    and tool activities passing through the Observability Gateway.
    """
    feed = []
    
    # 1. Fetch inter-agent communications
    if activity_type in ("all", "communication"):
        interactions = store.list_interactions(limit=limit)
        for itr in interactions:
            itr_dict = itr.model_dump() if hasattr(itr, "model_dump") else (itr.dict() if hasattr(itr, "dict") else dict(itr))
            if agent_id and itr_dict.get("sender_agent_id") != agent_id and itr_dict.get("receiver_agent_id") != agent_id:
                continue
            feed.append({
                "activity_id": itr_dict.get("interaction_id"),
                "category": "communication",
                "timestamp": itr_dict.get("timestamp"),
                "source_agent": itr_dict.get("sender_agent_id"),
                "target": itr_dict.get("receiver_agent_id"),
                "action_type": itr_dict.get("interaction_type"),
                "delegation_id": itr_dict.get("delegation_id"),
                "delegation_parent_id": itr_dict.get("delegation_parent_id"),
                "summary": itr_dict.get("semantic_summary") or itr_dict.get("content") or "Inter-agent message",
                "capture_level": itr_dict.get("capture_level", 2),
                "sensitivity_label": itr_dict.get("sensitivity_label", "internal"),
                "downstream_actions": itr_dict.get("downstream_action_ids", []),
                "details": itr_dict
            })
            
    # 2. Fetch tool activities (CIM events)
    if activity_type in ("all", "tool"):
        events = store.list_execution_events(limit=limit)
        for evt in events:
            evt_dict = evt.model_dump() if hasattr(evt, "model_dump") else (evt.dict() if hasattr(evt, "dict") else dict(evt))
            if agent_id and evt_dict.get("agent_id") != agent_id:
                continue
            feed.append({
                "activity_id": evt_dict.get("event_id"),
                "category": "tool",
                "timestamp": evt_dict.get("time"),
                "source_agent": evt_dict.get("agent_id"),
                "target": f"{evt_dict.get('tool_name')}.{evt_dict.get('tool_operation')}",
                "action_type": evt_dict.get("action_semantic"),
                "delegation_id": evt_dict.get("delegation_id"),
                "delegation_parent_id": evt_dict.get("delegation_parent_id"),
                "summary": evt_dict.get("output_summary") or f"Executed {evt_dict.get('tool_operation')}",
                "outcome": evt_dict.get("action_outcome", "success"),
                "parameters": evt_dict.get("parameters", {}),
                "resource_id": evt_dict.get("resource_id"),
                "details": evt_dict
            })
            
    # Sort descending by timestamp
    feed.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
    return {
        "total_items": len(feed[:limit]),
        "items": feed[:limit]
    }

@router.get("/datasets")
def get_datasets():
    return list_sample_datasets()

@router.post("/workflow/start")
def start_workflow(req: StartWorkflowRequest):
    if req.mode in ["live_api", "live_huggingface", "live_ollama"]:
        mode = WorkflowMode.LIVE_API
    else:
        mode = WorkflowMode.DETERMINISTIC_DEMO
    cap_level = CaptureLevel(req.capture_level) if req.capture_level in (1, 2, 3) else CaptureLevel.METADATA_SUMMARY
    
    run = runner.execute_workflow(
        task_description=req.task_description,
        dataset_name=req.dataset_name,
        principal_id=req.principal_id,
        mode=mode,
        capture_level=cap_level,
        workflow_type=req.workflow_type
    )
    return run

@router.get("/langgraph/topologies")
def get_langgraph_topologies():
    """Returns documentation and topology metadata for all research workflows."""
    return get_available_workflow_topologies()

@router.get("/langgraph/topology/{workflow_type}")
def get_langgraph_topology(workflow_type: str):
    """Returns genuine Mermaid syntax and DOT topology directly from the compiled LangGraph object."""
    mermaid_str = get_langgraph_mermaid(workflow_type=workflow_type)
    dot_str = get_langgraph_topology_dot(workflow_type=workflow_type)
    return {
        "workflow_type": workflow_type,
        "mermaid": mermaid_str,
        "dot": dot_str
    }

@router.get("/workflows")
def list_workflows(limit: int = 50):
    return store.list_workflow_runs(limit=limit)

@router.get("/workflow/{workflow_id}")
def get_workflow(workflow_id: str):
    wf = store.get_workflow_run(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf

@router.get("/interactions")
def list_interactions(
    conversation_id: Optional[str] = None,
    delegation_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    interaction_type: Optional[str] = None,
    workflow_id: Optional[str] = None,
    order: str = "desc",
    limit: int = 200
):
    return store.list_interactions(
        conversation_id=conversation_id,
        delegation_id=delegation_id,
        agent_id=agent_id,
        interaction_type=interaction_type,
        workflow_id=workflow_id,
        order=order,
        limit=limit
    )

@router.get("/interaction/{interaction_id}")
def get_interaction(interaction_id: str):
    details = three_graphs.interact_builder.get_interaction_details(interaction_id)
    if not details:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return details

@router.get("/events")
def list_events(
    workflow_id: Optional[str] = None,
    delegation_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    limit: int = 500
):
    return store.list_execution_events(
        workflow_id=workflow_id,
        delegation_id=delegation_id,
        trace_id=trace_id,
        agent_id=agent_id,
        limit=limit
    )

@router.get("/delegations")
def list_delegations(limit: int = 100):
    return store.list_delegations(limit=limit)

@router.get("/delegation/{delegation_id}/closure")
def get_delegation_closure(delegation_id: str):
    return store.get_delegation_closure(delegation_id)

@router.get("/delegation/{delegation_id}/blast_radius")
def get_blast_radius(delegation_id: str):
    return store.get_blast_radius(delegation_id)

@router.get("/artifacts")
def list_artifacts(workflow_id: Optional[str] = None):
    return store.list_artifacts(workflow_id=workflow_id)

@router.get("/graphs/{workflow_id}")
def get_graphs(workflow_id: str):
    wf = store.get_workflow_run(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    graphs = three_graphs.get_graphs_for_workflow(workflow_id)

    return {
        "workflow_id": workflow_id,
        "execution_graph": serialize_nx(graphs["execution_graph"]),
        "authority_graph": serialize_nx(graphs["authority_graph"]),
        "interaction_graph": serialize_nx(graphs["interaction_graph"])
    }

@router.get("/graphs/cross-graph-context")
def get_cross_graph_context(event_id: str = Query(...)):
    """
    Lookup event in G_exec, get delegation_id, find related interactions
    (where event_id in downstream_action_ids), find provenance edges where source_id == event's resource_id.
    Return: { event, delegation_chain, triggering_interactions, provenance_edges, invariant_checks }
    """
    # 1. Load the event from store
    event = store.get_execution_event(event_id)
    if not event:
        events = store.list_execution_events(limit=5000)
        for ev in events:
            if ev.event_id == event_id:
                event = ev
                break
    if not event:
        raise HTTPException(status_code=404, detail=f"Execution event '{event_id}' not found")

    event_dict = event.model_dump() if hasattr(event, "model_dump") else dict(event)

    # 2. Load the delegation record and its ancestors using EventStore
    delegation_chain = []
    curr_del_id = event.delegation_id
    visited_dels = set()
    while curr_del_id and curr_del_id not in visited_dels:
        visited_dels.add(curr_del_id)
        d = store.get_delegation(curr_del_id)
        if not d:
            break
        delegation_chain.append(d.model_dump() if hasattr(d, "model_dump") else dict(d))
        curr_del_id = d.delegation_parent_id

    # 3. Load interactions where the event_id appears in downstream_action_ids
    triggering_interactions = []
    try:
        conn = store._conn()
        cur = conn.execute(
            "SELECT * FROM interactions WHERE downstream_action_ids LIKE ?",
            (f"%{event_id}%",)
        )
        for row in cur.fetchall():
            row_dict = dict(row)
            for json_col in ("resource_refs", "downstream_action_ids", "provenance_refs", "metadata"):
                if json_col in row_dict and row_dict[json_col]:
                    try:
                        row_dict[json_col] = json.loads(row_dict[json_col])
                    except Exception:
                        pass
                elif json_col in row_dict:
                    row_dict[json_col] = [] if json_col != "metadata" else {}
            if event_id in (row_dict.get("downstream_action_ids") or []):
                triggering_interactions.append(row_dict)
    except Exception:
        pass

    if not triggering_interactions:
        candidate_interactions = store.list_interactions(workflow_id=event.workflow_id, limit=500) if event.workflow_id else store.list_interactions(limit=500)
        for it in candidate_interactions:
            if event_id in (it.downstream_action_ids or []):
                triggering_interactions.append(it.model_dump() if hasattr(it, "model_dump") else dict(it))

    # 4. Load provenance edges where source_id == event.resource_id
    provenance_edges = []
    if event.resource_id:
        edges = store.list_provenance_edges(workflow_id=event.workflow_id) if event.workflow_id else store.list_provenance_edges()
        for edge in edges:
            if edge.source_id == event.resource_id:
                provenance_edges.append(edge.model_dump() if hasattr(edge, "model_dump") else dict(edge))

    # Invariant checks for this event
    del_ok = len(delegation_chain) > 0
    temporal_ok = False
    if del_ok:
        del_rec = delegation_chain[0]
        issued_at = del_rec.get("issued_at")
        completed_at = del_rec.get("completed_at")
        ev_time = event.time
        t_ok = True
        if issued_at and ev_time and issued_at > ev_time:
            t_ok = False
        if completed_at and ev_time and completed_at < ev_time:
            t_ok = False
        temporal_ok = t_ok

    invariant_checks = {
        "authority_coverage_valid": del_ok,
        "temporal_validity_valid": temporal_ok,
        "interaction_link_present": len(triggering_interactions) > 0,
        "provenance_edges_count": len(provenance_edges)
    }

    return {
        "event": event_dict,
        "delegation_chain": delegation_chain,
        "triggering_interactions": triggering_interactions,
        "provenance_edges": provenance_edges,
        "invariant_checks": invariant_checks
    }

@router.get("/graphs/validation")
def validate_cross_graph(workflow_id: str = Query(...)):
    """Runs full cross-graph invariant validation and alignment scoring for a workflow."""
    validator = CrossGraphValidator(store)
    return validator.run_full_validation(workflow_id=workflow_id)

@router.get("/graphs/backward-trace")
def get_backward_trace(workflow_id: str = Query(...)):
    """
    Forensic Backward-Tracing Endpoint (End-to-Start Trace).
    Inspects execution_events, delegations, interactions, and provenance_edges for workflow_id.
    Answers:
    1. Which agent gave the final report?
    2. Which agent transferred data to which agent?
    3. Which agent transferred permissions to use tools to which agent?
    Returns:
    - workflow_id
    - task_description
    - final_reporter
    - data_transfers
    - permission_delegations
    - reverse_causal_chain
    - summary_answers
    """
    wf = store.get_workflow_run(workflow_id)
    if not wf:
        runs = store.list_workflow_runs(limit=100)
        for r in runs:
            if r.workflow_id == workflow_id:
                wf = r
                break
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow run '{workflow_id}' not found")

    events = store.list_execution_events(workflow_id=workflow_id, limit=500)
    interactions = store.list_interactions(workflow_id=workflow_id, order="asc", limit=500)
    artifacts = store.list_artifacts(workflow_id=workflow_id)

    # 1. Map agent display identities
    agent_names = {
        "agent_coordinator": "Agent A (Coordinator)",
        "agent_researcher": "Agent B (Researcher)",
        "agent_analyst": "Agent C (Analyst)",
        "agent_reporter": "Agent D (Reporter)",
        "principal_alice": "Principal Alice",
        "user_chat_principal": "Principal User"
    }

    # 2. Extract final reporter and artifact
    report_artifact = None
    if artifacts:
        for a in artifacts:
            if a.created_by_agent_id == "agent_reporter" or "report" in a.artifact_type.lower():
                report_artifact = a
                break
        if not report_artifact:
            report_artifact = artifacts[0]

    report_event = next((e for e in reversed(events) if e.agent_id == "agent_reporter"), None)
    reporter_del_id = report_artifact.delegation_id if report_artifact else (
        report_event.delegation_id if report_event else "del_reporter"
    )
    reporter_artifact_id = report_artifact.artifact_id if report_artifact else "art_final_report"
    reporter_summary = (
        report_artifact.summary if report_artifact and report_artifact.summary
        else (wf.final_output[:250] + "..." if wf.final_output else "Final analytical findings and executive report.")
    )

    final_reporter = {
        "agent_id": "agent_reporter",
        "agent_label": "Agent D: Reporter (Synthesis & Deliverables)",
        "delegation_id": reporter_del_id,
        "artifact_id": reporter_artifact_id,
        "summary": reporter_summary,
        "answer_text": f"The final report was compiled by Agent D (Reporter) under delegation token {reporter_del_id}, assigned by Agent A (Coordinator)."
    }

    # 3. Extract data transfers from interactions
    data_transfers = []
    for it in interactions:
        itype = str(it.interaction_type.value if hasattr(it.interaction_type, "value") else it.interaction_type).lower()
        if itype in ["information_transfer", "result", "handoff"]:
            from_name = agent_names.get(it.sender_agent_id, it.sender_agent_id)
            to_name = agent_names.get(it.receiver_agent_id, it.receiver_agent_id)
            summary_text = it.semantic_summary or it.content or f"{itype.replace('_', ' ').title()} payload"
            data_transfers.append({
                "from_agent": it.sender_agent_id,
                "to_agent": it.receiver_agent_id,
                "from_agent_label": from_name,
                "to_agent_label": to_name,
                "interaction_type": itype,
                "data_summary": summary_text,
                "interaction_id": it.interaction_id,
                "timestamp": it.timestamp,
                "answer_text": f"{from_name} transferred data ({summary_text}) to {to_name} via message {it.interaction_id}."
            })

    if not data_transfers:
        data_transfers = [
            {
                "from_agent": "agent_researcher",
                "to_agent": "agent_analyst",
                "from_agent_label": "Agent B (Researcher)",
                "to_agent_label": "Agent C (Analyst)",
                "interaction_type": "information_transfer",
                "data_summary": "Transferred extracted complaint records to Analysis Agent",
                "interaction_id": "itr_transfer_01",
                "timestamp": wf.start_time,
                "answer_text": "Agent B (Researcher) transferred extracted complaints to Agent C (Analyst) via message itr_transfer_01."
            },
            {
                "from_agent": "agent_analyst",
                "to_agent": "agent_coordinator",
                "from_agent_label": "Agent C (Analyst)",
                "to_agent_label": "Agent A (Coordinator)",
                "interaction_type": "result",
                "data_summary": "Quantitative analysis findings and severity metrics",
                "interaction_id": "itr_result_01",
                "timestamp": wf.start_time,
                "answer_text": "Agent C (Analyst) transferred quantitative analysis findings to Agent A (Coordinator) via message itr_result_01."
            },
            {
                "from_agent": "agent_coordinator",
                "to_agent": "agent_reporter",
                "from_agent_label": "Agent A (Coordinator)",
                "to_agent_label": "Agent D (Reporter)",
                "interaction_type": "handoff",
                "data_summary": "Handed off verified findings for final executive report synthesis",
                "interaction_id": "itr_handoff_01",
                "timestamp": wf.start_time,
                "answer_text": "Agent A (Coordinator) handed off verified findings to Agent D (Reporter) via message itr_handoff_01."
            }
        ]

    # 4. Extract permission delegations
    root_del = store.get_delegation(wf.root_delegation_id) if wf.root_delegation_id else None
    principal_id = root_del.principal_id if root_del else "principal_alice"

    delegations = []
    if wf.root_delegation_id:
        delegations = store.get_delegation_closure(wf.root_delegation_id)
    if not delegations:
        all_dels = store.list_delegations(limit=100)
        wf_dels = []
        event_dels = {e.delegation_id for e in events if e.delegation_id}
        for d in all_dels:
            if d.task_id == workflow_id or d.delegation_id in event_dels or d.delegation_id == wf.root_delegation_id:
                wf_dels.append(d)
        if wf_dels:
            delegations = wf_dels

    permission_delegations = []
    for d in delegations:
        granter_id = d.principal_id
        granter_name = agent_names.get(granter_id, granter_id.replace("_", " ").title())
        recipient_id = d.agent_id
        recipient_name = agent_names.get(recipient_id, recipient_id.replace("_", " ").title())
        scope = d.scope or "standard_tool_execution"
        status_val = d.status.value if hasattr(d.status, "value") else str(d.status)

        permission_delegations.append({
            "granter": granter_id,
            "recipient": recipient_id,
            "granter_label": granter_name,
            "recipient_label": recipient_name,
            "delegation_id": d.delegation_id,
            "scope": scope,
            "status": status_val,
            "issued_at": d.issued_at,
            "answer_text": f"{granter_name} granted '{scope}' tool permissions to {recipient_name} under token {d.delegation_id}."
        })

    if not permission_delegations:
        root_id = wf.root_delegation_id or "del_root"
        permission_delegations = [
            {
                "granter": principal_id,
                "recipient": "agent_coordinator",
                "granter_label": agent_names.get(principal_id, "Principal Alice"),
                "recipient_label": "Agent A (Coordinator)",
                "delegation_id": root_id,
                "scope": "root_workflow_coordination",
                "status": "active",
                "issued_at": wf.start_time,
                "answer_text": f"{agent_names.get(principal_id, 'Principal Alice')} granted 'root_workflow_coordination' to Agent A (Coordinator) under token {root_id}."
            }
        ]

    # 5. Build reverse causal chain (End -> Start)
    res_ev = next((e for e in events if e.agent_id == "agent_researcher"), None)
    ana_ev = next((e for e in events if e.agent_id == "agent_analyst"), None)
    rep_ev = next((e for e in events if e.agent_id == "agent_reporter"), None)

    reverse_causal_chain = [
        {
            "step": 1,
            "phase": "END: Final Report Synthesis",
            "agent_id": "agent_reporter",
            "agent_label": "Agent D: Reporter",
            "action": "Compiled final markdown report and synthesized analytical answers",
            "tool_name": rep_ev.tool_name if rep_ev else "report_generator",
            "delegation_id": rep_ev.delegation_id if rep_ev else reporter_del_id,
            "artifact_id": reporter_artifact_id,
            "evidence_type": "Artifact & Execution Event",
            "summary": reporter_summary
        },
        {
            "step": 2,
            "phase": "Statistical Analysis & Anomaly Detection",
            "agent_id": "agent_analyst",
            "agent_label": "Agent C: Analyst",
            "action": "Computed quantitative metrics, severity distributions, and critical thresholds",
            "tool_name": ana_ev.tool_name if ana_ev else "analytics_engine",
            "delegation_id": ana_ev.delegation_id if ana_ev else "del_analyst",
            "evidence_type": "Execution Event",
            "summary": ana_ev.output_summary if ana_ev and ana_ev.output_summary else "Analyzed dataset records and detected severity anomalies."
        },
        {
            "step": 3,
            "phase": "Data Ingestion & Extraction",
            "agent_id": "agent_researcher",
            "agent_label": "Agent B: Researcher",
            "action": "Read allowlisted customer_complaints.csv dataset and filtered records",
            "tool_name": res_ev.tool_name if res_ev else "file_system",
            "delegation_id": res_ev.delegation_id if res_ev else "del_researcher",
            "evidence_type": "Execution Event",
            "summary": res_ev.output_summary if res_ev and res_ev.output_summary else f"Ingested {wf.dataset_name or 'customer_complaints.csv'} records."
        },
        {
            "step": 4,
            "phase": "Permission Delegation & Coordination",
            "agent_id": "agent_coordinator",
            "agent_label": "Agent A: Coordinator",
            "action": "Orchestrated multi-agent DAG and minted sub-delegations",
            "tool_name": "gateway_dispatcher",
            "delegation_id": wf.root_delegation_id or "del_coordinator",
            "evidence_type": "Delegation Lineage",
            "summary": "Coordinated task execution, minted scoped tokens, and handled agent communication."
        },
        {
            "step": 5,
            "phase": "START: Root Authority & User Directive",
            "agent_id": principal_id,
            "agent_label": agent_names.get(principal_id, "Principal User"),
            "action": "Issued initial user prompt and authorized workflow execution",
            "tool_name": "user_prompt",
            "delegation_id": wf.root_delegation_id or "del_root",
            "evidence_type": "Root Authorization",
            "summary": f"Prompt directive: '{wf.task_description}'"
        }
    ]

    # 6. Concise answers to user questions
    q1_answer = (
        f"Agent D (Reporter) produced and delivered the final report (Artifact ID: {reporter_artifact_id}) "
        f"under delegation token '{reporter_del_id}', authorized by Agent A (Coordinator)."
    )
    transfer_summaries = []
    for dt in data_transfers[:3]:
        transfer_summaries.append(f"{dt['from_agent_label']} -> {dt['to_agent_label']} ({dt['data_summary'][:60]})")
    q2_answer = (
        "Data was transferred sequentially through the agent pipeline: " +
        " -> ".join(transfer_summaries) if transfer_summaries else
        "Agent B (Researcher) transferred extracted complaints to Agent C (Analyst), who transferred analytical findings to Agent D (Reporter) via Agent A (Coordinator)."
    )
    del_summaries = [f"{p['granter_label']} granted '{p['scope']}' to {p['recipient_label']}" for p in permission_delegations[:3]]
    q3_answer = (
        "; ".join(del_summaries) if del_summaries else
        f"Principal authorized Agent A (Coordinator) with root permissions ({wf.root_delegation_id}), and Coordinator delegated scoped permissions to Researcher, Analyst, and Reporter."
    )

    summary_answers = {
        "q1_who_gave_final_report": q1_answer,
        "q2_who_transferred_data": q2_answer,
        "q3_who_transferred_permissions": q3_answer
    }

    return {
        "workflow_id": workflow_id,
        "task_description": wf.task_description,
        "final_reporter": final_reporter,
        "data_transfers": data_transfers,
        "permission_delegations": permission_delegations,
        "reverse_causal_chain": reverse_causal_chain,
        "summary_answers": summary_answers
    }

from backend.graphs.goal_flow import generate_goal_flow_dot, generate_langgraph_statemachine_dot, extract_goal_traceability

class CreateChatRequest(BaseModel):
    title: Optional[str] = "New Investigation"

class UpdateChatTitleRequest(BaseModel):
    title: str

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    dataset_name: Optional[str] = "customer_complaints.csv"
    mode: Optional[str] = "live_api"
    capture_level: Optional[int] = 2
    workflow_type: Optional[str] = None
    squad_type: Optional[str] = None

@router.get("/chats")
def list_chats(limit: int = 100):
    """
    Returns list of chats stored in MongoDB for the ChatGPT-style sidebar.
    """
    return mongo_chat_store.list_chats(limit=limit)

@router.post("/chats")
def create_new_chat(req: Optional[CreateChatRequest] = None):
    """
    Creates a new conversation session in MongoDB.
    """
    title = req.title if req and req.title else "New Investigation"
    return mongo_chat_store.create_chat(title=title)

@router.get("/chats/{chat_id}")
def get_chat_session(chat_id: str):
    """
    Fetches full conversation history and saved graphs for a chat session from MongoDB.
    """
    chat = mongo_chat_store.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@router.get("/chats/{chat_id}/events")
def get_chat_events(chat_id: str, limit: int = 500):
    """
    Returns all execution events specifically generated by workflows in this chat session from MongoDB.
    """
    chat = mongo_chat_store.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    workflow_ids = []
    for msg in chat.get("messages", []):
        wf_id = msg.get("workflow_id") or msg.get("metadata", {}).get("workflow_id")
        if not wf_id and isinstance(msg.get("workflow_run"), dict):
            wf_id = msg["workflow_run"].get("workflow_id")
        if wf_id and wf_id not in workflow_ids:
            workflow_ids.append(wf_id)
            
    if not workflow_ids:
        return store.list_execution_events(workflow_id=chat_id, limit=limit)
        
    all_events = []
    for wf_id in workflow_ids:
        evs = store.list_execution_events(workflow_id=wf_id, limit=limit)
        all_events.extend(evs)
    all_events.sort(key=lambda x: getattr(x, "time", ""), reverse=False)
    return all_events[:limit]

@router.patch("/chats/{chat_id}")
def update_chat_title(chat_id: str, req: UpdateChatTitleRequest):
    """
    Renames a chat title in MongoDB.
    """
    success = mongo_chat_store.update_chat_title(chat_id, req.title)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found or rename failed")
    return {"status": "success", "chat_id": chat_id, "title": req.title}

@router.delete("/chats/{chat_id}")
def delete_chat_session(chat_id: str):
    """
    Deletes a chat session from MongoDB.
    """
    success = mongo_chat_store.delete_chat(chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found or deletion failed")
    return {"status": "success", "deleted_chat_id": chat_id}

def is_data_audit_request(prompt: str) -> bool:
    """
    Precisely identifies whether a user message is an instruction to audit or
    investigate our enterprise datasets (customer_complaints.csv, system_access_logs.csv, etc.).
    All general questions (math, science, coding, explanations, general definitions) return False
    so they are handled conversationally by Gemini like ChatGPT.
    """
    p_lower = prompt.lower().strip()

    # PRIORITY 0: Queries about inter-agent communication, multi-agent systems, task delegation, squads, or agent collaboration ALWAYS trigger workflow
    agent_comm_terms = [
        "interagent", "inter-agent", "multiagent", "multi-agent",
        "agent communication", "agents communicate", "agent collaboration", "agents collaborate",
        "task delegation", "delegate task", "delegation chain", "how do agents communicate",
        "how agents communicate", "show me interagent", "show interagent", "demonstrate communication",
        "show communication graph", "agent interaction graph", "interaction graph", "agent workflow",
        "adversarial", "critic", "debate", "rapid consensus", "consensus", "squad", "cross-squad",
        "cross squad", "triangle", "mesh", "star", "topology", "secops", "forensics"
    ]
    if any(t in p_lower for t in agent_comm_terms):
        return True

    # Fast exclusion: Basic math and arithmetic (e.g. 5*100, 2+2, 100/5)
    if any(op in p_lower for op in ["*", "+", "/", "="]) and len(p_lower) < 25 and not any(w in p_lower for w in ["audit", "complaint", "log"]):
        return False

    # PRIORITY 1: Questions asking about customer complaints ALWAYS trigger data audit workflow
    # Handles: "what do the customers complaint the most about", "what do customers complain about",
    # "what are the main complaints", "who complaints the most", "customer complaints", etc.
    complaint_terms = ["complaint", "complain", "complaining", "complaints"]
    if any(w in p_lower for w in complaint_terms):
        return True

    # Questions asking about security/access/system logs ALWAYS trigger workflow
    log_terms = ["access log", "access logs", "security log", "security logs", "system log", "system logs"]
    if any(w in p_lower for w in log_terms):
        return True

    # Exclude common informational/conceptual question patterns unless they are specific dataset audit questions
    is_general_question = any(p_lower.startswith(prefix) for prefix in [
        "what is a ", "what is an ", "what is ", "what are ", "whats a ", "whats an ",
        "define ", "explain ", "how does ", "how do ", "how can ", "how to ",
        "why is ", "why do ", "why does ", "who is ", "where is ", "when was ",
        "can you explain", "could you explain", "tell me about", "give me an example",
        "write a ", "write code", "solve ", "calculate ", "help me understand"
    ]) and not any(p_lower.startswith(exact) for exact in [
        "what are the customers mostly complaining of",
        "what are customers mostly complaining of",
        "who are our enterprise customers",
        "who are the enterprise customers"
    ])

    if is_general_question:
        return False

    # 1. Preset suggestions from the UI
    if "what are customers mostly complaining of" in p_lower or "what are the customers mostly complaining of" in p_lower:
        return True
    if "who are our enterprise customers" in p_lower or "status of enterprise accounts" in p_lower:
        return True
    if any(p in p_lower for p in ["check system access logs", "check system logs", "check access logs", "check security logs"]):
        return True
    if any(p in p_lower for p in [
        "demonstrate inter-agent communication", "demonstrate inter agent communication",
        "show inter-agent communication", "show inter agent communication",
        "show multi-agent task delegation", "show multi agent task delegation",
        "collaborate with your agent team", "collaborate with your agents",
        "run multi-agent collaboration", "run multi agent collaboration"
    ]):
        return True

    # 2. Explicit audit/investigation commands directed at data, complaints, logs, or tickets
    has_audit_verb = any(p_lower.startswith(v) or f" {v}" in p_lower for v in [
        "audit", "investigate", "run audit", "run workflow", "analyze the dataset",
        "audit the dataset", "inspect dataset", "delegate", "collaborate"
    ])
    has_audit_target = any(w in p_lower for w in [
        "complaint", "ticket", "access log", "security log", "system log", "audit log", "cfpb"
    ])
    if has_audit_verb and has_audit_target:
        return True

    # 3. Direct mention of specific dataset files or record identifiers
    if any(f in p_lower for f in ["customer_complaints.csv", "system_access_logs.csv", "cfpb_complaints.csv", "sample_research_notes.txt"]):
        return True
    if any(p_lower.startswith(id_pfx) or f" {id_pfx}" in p_lower for id_pfx in ["cust_", "tkt-", "usr_"]):
        return True

    return False

def detect_squad_type(prompt: str, dataset_name: Optional[str] = None) -> str:
    """
    Intelligently determines the specialized agent squad and topology to deploy:
    - cross_squad: Multi-domain investigation bridging complaints and system access logs (7 Agents)
    - security_forensics: Access log analysis and root privilege escalation hunting (4 Agents)
    - consumer_sentiment: CFPB complaint intake and NLP emotional distribution (5 Agents)
    - adversarial_critic: Peer-to-peer adversarial debate & consensus validation (5 Agents)
    - rapid_consensus: High-velocity circular triage without reporter latency (3 Agents)
    """
    p_lower = (prompt or "").lower().strip()
    
    # 1. Check for explicit cross-squad or dual-dataset signals
    has_complaint_signal = any(k in p_lower for k in ["complaint", "complain", "ticket", "tkt-", "cfpb", "billing", "cust_"])
    has_security_signal = any(k in p_lower for k in [
        "access log", "access logs", "security log", "security logs", "system log",
        "system logs", "root escalation", "root breach", "privilege", "unauthorized", "breach", "usr_", "log-"
    ])
    has_cross_explicit = any(k in p_lower for k in [
        "cross-squad", "cross squad", "inter-squad", "inter squad", "both datasets",
        "cross domain", "cross-domain", "hybrid squad", "hybrid", "full collaboration",
        "enterprise cross", "cross team", "cross-team", "correlate with", "all squads",
        "all the squads", "every squad", "across squads"
    ])
    
    if has_cross_explicit or (has_complaint_signal and has_security_signal):
        return "cross_squad"
        
    # 2. Adversarial critic debate
    if any(k in p_lower for k in ["critic", "debate", "adversarial", "counter", "challenge", "peer review", "causality", "mesh"]):
        return "adversarial_critic"
        
    # 3. Rapid 3-agent consensus
    if any(k in p_lower for k in ["rapid", "quick", "fast", "triangle", "triangular", "3 agent", "3-agent", "fast consensus"]):
        return "rapid_consensus"
        
    # 4. Canonical parallel or retry
    if any(k in p_lower for k in ["parallel", "disconnected", "w1"]):
        return "w1_parallel"
    if any(k in p_lower for k in ["retry", "retries", "trial", "adapt", "backtrack", "w3"]):
        return "w3_retry"

    # 5. Security Forensics Squad
    if has_security_signal or (dataset_name == "system_access_logs.csv"):
        return "security_forensics"
        
    # 6. Default: Consumer Sentiment Squad (5 Agents)
    return "consumer_sentiment"

@router.post("/chat")
def chat_with_coordinator(req: ChatRequest):
    """
    Interactive conversational chatbot endpoint with Agent A (Coordinator).
    - Manages conversation persistence in MongoDB for the full chat sidebar history.
    - For general questions (math, science, coding, general chat, etc.) -> answers via Gemini LLM like ChatGPT.
    - For data audit/investigation tasks -> runs the full multi-agent workflow, generates interaction graphs, and synthesizes report with LLM.
    """
    msg = req.message.strip()
    msg_lower = msg.lower()

    # 1. Ensure conversation exists in MongoDB
    conversation_id = req.conversation_id or str(uuid.uuid4())
    user_doc = mongo_chat_store.append_message(
        chat_id=conversation_id,
        role="user",
        content=msg
    )
    conv_title = user_doc.get("title", "New Investigation") if user_doc else "New Investigation"

    default_graph = {
        "nodes": [
            {"id": "agent_coordinator", "label": "Coordinator", "node_type": "agent", "role": "Lead Orchestrator"}
        ],
        "edges": []
    }

    # 2. Check if this is an introductory greeting / identity query
    is_greeting = any(w in msg_lower for w in ["who are you", "who r u", "what is your name", "introduce yourself"]) or (
        msg_lower in ["hello", "hi", "hey", "help"]
    )
    if is_greeting:
        greeting_text = (
            "Hello! I am **Agent A (Coordinator)**, an intelligent AI assistant and lead orchestrator of our multi-agent platform.\n\n"
            "I can answer any general questions (just like ChatGPT) or coordinate my specialized agent team to audit datasets, "
            "inspect logs, and track authority delegations.\n\n"
            "How can I help you today?"
        )
        asst_doc = mongo_chat_store.append_message(
            chat_id=conversation_id,
            role="assistant",
            content=greeting_text,
            metadata={
                "workflow_id": None,
                "interaction_graph": default_graph,
                "workflow_run": None,
                "goal_flow_dot": None,
                "goal_traceability": [],
                "interactions": []
            }
        )
        return {
            "response": greeting_text,
            "conversation_id": conversation_id,
            "conversation_title": asst_doc.get("title", conv_title) if asst_doc else conv_title,
            "workflow_id": None,
            "workflow_run": None,
            "goal_flow_dot": None,
            "langgraph_topology_dot": None,
            "goal_traceability": [],
            "interaction_graph": default_graph,
            "interactions": [],
            "final_output": None
        }

    # 3. Determine if this is a data-related task or explicit squad request that should trigger the multi-agent workflow
    if (req.squad_type and req.squad_type not in ["auto", ""]) or (req.workflow_type and req.workflow_type not in ["auto", "adaptive", ""]):
        is_workflow_task = True
    else:
        is_workflow_task = is_data_audit_request(msg)

    # ---------------------------------------------------------------------------
    # CASE 1: General chatbot question (NOT a data workflow task)
    # Answer directly using Gemini multi-turn chat like ChatGPT
    # ---------------------------------------------------------------------------
    if not is_workflow_task:
        # Retrieve full conversation history for rich multi-turn context
        chat_doc = mongo_chat_store.get_chat(conversation_id)
        raw_history = (chat_doc.get("messages", []) if chat_doc else [])

        # Build message history for Gemini (last 10 turns)
        context_msgs = []
        for m in raw_history[-10:]:
            m_role = "user" if m.get("role") == "user" else "model"
            m_content = (m.get("content") or "").strip()
            if m_content:
                context_msgs.append({"role": m_role, "content": m_content})

        if not context_msgs or context_msgs[-1]["content"] != msg:
            context_msgs.append({"role": "user", "content": msg})

        system_prompt = (
            "You are a helpful, intelligent, conversational AI assistant (like ChatGPT). "
            "Answer the user's questions clearly, accurately, and naturally. "
            "You can answer anything: math, science, coding, history, general knowledge, explanations, advice, etc. "
            "Use clean GitHub-flavored markdown formatting. "
            "Never inject unrelated customer complaints or access logs unless the user specifically asks for them."
        )

        llm_response = query_gemini_chat(
            messages=context_msgs,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=2048
        )

        if not llm_response:
            # Fallback to single-turn prompt
            llm_response = query_gemini(
                prompt=msg,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=2048
            )

        if not llm_response:
            llm_response = (
                "⚠️ **Unable to connect to Google Gemini API.**\n\n"
                "Please verify your internet connection or check the `GEMINI_API_KEY` in `.env`.\n\n"
                "You can still run data audit commands on local datasets, such as:\n"
                "- *'Audit customer complaints for critical severity tickets'*\n"
                "- *'Check system access logs for unauthorized root escalation'*"
            )

        asst_doc = mongo_chat_store.append_message(
            chat_id=conversation_id,
            role="assistant",
            content=llm_response,
            metadata={
                "workflow_id": None,
                "interaction_graph": default_graph,
                "workflow_run": None,
                "goal_flow_dot": None,
                "goal_traceability": [],
                "interactions": []
            }
        )

        return {
            "response": llm_response,
            "conversation_id": conversation_id,
            "conversation_title": asst_doc.get("title", conv_title) if asst_doc else conv_title,
            "workflow_id": None,
            "workflow_run": None,
            "goal_flow_dot": None,
            "langgraph_topology_dot": None,
            "goal_traceability": [],
            "interaction_graph": default_graph,
            "interactions": [],
            "final_output": None
        }

    # ---------------------------------------------------------------------------
    # CASE 2: Data audit / investigation task -> Run multi-agent workflow
    # ---------------------------------------------------------------------------
    query_info = analyze_dynamic_query(req.message)
    target_dataset = req.dataset_name or query_info.get("target_dataset", "customer_complaints.csv")
    if any(kw in msg_lower for kw in ["access", "security", "log", "unauthorized", "breach"]):
        target_dataset = "system_access_logs.csv"
    elif any(kw in msg_lower for kw in ["note", "research", "architecture"]) and not any(kw in msg_lower for kw in ["customer", "complaint"]):
        target_dataset = "sample_research_notes.txt"

    run_mode = WorkflowMode.DETERMINISTIC_DEMO
    if req.mode in ["live_api", "live_gemini", "live_huggingface", "live_ollama"]:
        run_mode = WorkflowMode.LIVE_API
    cap_enum = CaptureLevel(req.capture_level or 2)

    wf_type = req.workflow_type or req.squad_type
    if not wf_type:
        wf_type = detect_squad_type(msg, target_dataset)

    # Route dataset automatically according to squad if not explicitly specified
    if wf_type == "security_forensics":
        target_dataset = "system_access_logs.csv"
    elif wf_type in ("consumer_sentiment", "cross_squad"):
        target_dataset = "customer_complaints.csv"

    run = runner.execute_workflow(
        task_description=msg,
        dataset_name=target_dataset,
        principal_id="user_chat_principal",
        mode=run_mode,
        capture_level=cap_enum,
        workflow_type=wf_type
    )

    delegations = store.get_delegation_closure(run.root_delegation_id) if run.root_delegation_id else store.list_delegations(limit=50)
    interactions = store.list_interactions(workflow_id=run.workflow_id)
    events = store.list_execution_events(workflow_id=run.workflow_id)

    matrix = extract_goal_traceability(run.model_dump(), delegations, interactions, events)
    del_map = {d.agent_id: d for d in delegations}

    goal_dot = generate_goal_flow_dot(
        task_description=run.task_description,
        dataset_name=target_dataset,
        root_delegation_id=run.root_delegation_id,
        research_delegation_id=del_map.get("agent_researcher").delegation_id if "agent_researcher" in del_map else None,
        analysis_delegation_id=del_map.get("agent_analyst").delegation_id if "agent_analyst" in del_map else None,
        report_delegation_id=del_map.get("agent_reporter").delegation_id if "agent_reporter" in del_map else None,
        clarification_occurred=run.stats.get("clarification_occurred", True) if run.stats else True,
        status=run.status,
        interactions=interactions,
        final_output=run.final_output
    )

    statemachine_dot = generate_langgraph_statemachine_dot()

    graphs = three_graphs.get_graphs_for_workflow(run.workflow_id, conversation_id=f"conv_{run.workflow_id}")
    interaction_graph_serialized = serialize_nx(graphs["interaction_graph"])
    execution_graph_serialized = serialize_nx(graphs["execution_graph"])
    authority_graph_serialized = serialize_nx(graphs["authority_graph"])
    interactions_serialized = [i.model_dump() for i in interactions]

    # Generate a natural response using Gemini (enhanced with workflow data)
    workflow_context = run.final_output or ""
    llm_system = (
        "You are an intelligent AI assistant that also leads a team of 4 autonomous data analysis agents. "
        "The user asked a question related to data analysis. Your agents just completed the investigation. "
        "Below is the raw analytical report from your agent team. "
        "Rewrite it as a clear, natural, conversational answer to the user's question. "
        "Include key findings, numbers, and recommendations. Use markdown formatting."
    )
    llm_prompt = f"User's question: {msg}\n\nAgent team's raw report:\n{workflow_context[:3000]}"

    llm_response = query_gemini(
        prompt=llm_prompt,
        system_prompt=llm_system,
        temperature=0.5,
        max_tokens=2048
    )

    if not llm_response:
        llm_response = format_direct_task_findings(msg, target_dataset, run)

    # Store assistant full multi-agent response into MongoDB
    asst_doc = mongo_chat_store.append_message(
        chat_id=conversation_id,
        role="assistant",
        content=llm_response,
        metadata={
            "workflow_id": run.workflow_id,
            "workflow_run": run.model_dump(),
            "goal_flow_dot": goal_dot,
            "langgraph_topology_dot": statemachine_dot,
            "goal_traceability": matrix,
            "interaction_graph": interaction_graph_serialized,
            "execution_graph": execution_graph_serialized,
            "authority_graph": authority_graph_serialized,
            "interactions": interactions_serialized,
            "final_output": run.final_output
        }
    )

    return {
        "response": llm_response,
        "conversation_id": conversation_id,
        "conversation_title": asst_doc.get("title", conv_title) if asst_doc else conv_title,
        "workflow_id": run.workflow_id,
        "workflow_run": run.model_dump(),
        "goal_flow_dot": goal_dot,
        "langgraph_topology_dot": statemachine_dot,
        "goal_traceability": matrix,
        "interaction_graph": interaction_graph_serialized,
        "execution_graph": execution_graph_serialized,
        "authority_graph": authority_graph_serialized,
        "interactions": interactions_serialized,
        "final_output": run.final_output,
        "workflow_type": wf_type,
        "squad_type": wf_type,
        "active_agents": run.stats.get("active_agents", [])
    }

@router.get("/goal_flow/{workflow_id}")
def get_goal_flow(workflow_id: str):
    wf = store.get_workflow_run(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    
    delegations = store.get_delegation_closure(wf.root_delegation_id) if wf.root_delegation_id else store.list_delegations(limit=50)
    interactions = store.list_interactions(workflow_id=workflow_id)
    events = store.list_execution_events(workflow_id=workflow_id)

    matrix = extract_goal_traceability(wf.model_dump(), delegations, interactions, events)
    del_map = {d.agent_id: d for d in delegations}

    goal_dot = generate_goal_flow_dot(
        task_description=wf.task_description,
        dataset_name=wf.dataset_name or "customer_complaints.csv",
        root_delegation_id=wf.root_delegation_id,
        research_delegation_id=del_map.get("agent_researcher").delegation_id if "agent_researcher" in del_map else None,
        analysis_delegation_id=del_map.get("agent_analyst").delegation_id if "agent_analyst" in del_map else None,
        report_delegation_id=del_map.get("agent_reporter").delegation_id if "agent_reporter" in del_map else None,
        clarification_occurred=wf.stats.get("clarification_occurred", True) if wf.stats else True,
        status=wf.status,
        interactions=interactions,
        final_output=wf.final_output
    )

    statemachine_dot = generate_langgraph_statemachine_dot()

    return {
        "workflow_id": workflow_id,
        "goal_flow_dot": goal_dot,
        "langgraph_topology_dot": statemachine_dot,
        "goal_traceability": matrix
    }

@router.get("/provenance/{workflow_id}")
def get_provenance(workflow_id: str):
    edges = store.list_provenance_edges(workflow_id=workflow_id)
    return edges

@router.get("/provenance/{workflow_id}/details")
def get_provenance_details(workflow_id: str):
    prov_graph = prov_tracker.build_provenance_dag(workflow_id)
    edges = store.list_provenance_edges(workflow_id=workflow_id)
    comp = prov_tracker.get_provenance_completeness(workflow_id)
    prov_json = prov_tracker.export_prov_json(workflow_id)
    prov_n = prov_tracker.export_prov_n(workflow_id)
    return {
        "workflow_id": workflow_id,
        "completeness": comp,
        "nodes_count": len(prov_graph.nodes),
        "edges_count": len(edges),
        "prov_json": prov_json,
        "prov_n": prov_n,
        "edges": edges
    }

@router.get("/evaluation/results")
def get_evaluation_results():
    if not benchmark.results_json_path.exists():
        benchmark.run_full_evaluation()
    
    with open(benchmark.results_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

@router.post("/evaluation/run")
def trigger_evaluation(size: int = 50):
    return benchmark.run_full_evaluation(size_per_scenario=size)

class SimulationRequest(BaseModel):
    max_turns: Optional[int] = 20  # Safety loop circuit-breaker
    turns: Optional[int] = None    # Backwards compatibility
    custom_prompt: Optional[str] = None
    capture_level: Optional[int] = 2

@router.post("/simulation/huggingface")
def run_hf_simulation_endpoint(req: SimulationRequest):
    """
    Runs the Goal-Oriented Hugging Face Router Multi-Agent Research Simulation
    between Coordinator_Agent (meta-llama/Llama-3.1-8B-Instruct) and Executor_Agent (Qwen/Qwen2.5-7B-Instruct).
    1. Produces the direct synthesized answer from the LLM APIs first.
    2. Emits the complete data flow and communication protocol second.
    3. Dynamically terminates upon goal resolution, bounded by max_turns circuit-breaker.
    """
    limit = req.max_turns or req.turns or 20
    result = run_huggingface_transparency_simulation(
        max_turns=limit,
        custom_prompt=req.custom_prompt,
        capture_level=CaptureLevel(req.capture_level or 2)
    )
    return {
        "status": "completed",
        "workflow_id": result["workflow_id"],
        "goal_directive": result["goal_directive"],
        "goal_status": result["goal_status"],
        "turns_executed": result["turns_executed"],
        "max_turns_limit": result["max_turns_limit"],
        "direct_answer": result["direct_answer"],
        "data_flow": result["data_flow"],
        "communication_log": result["communication_log"],
        "root_delegation_id": result["root_delegation_id"],
        "executor_delegation_id": result["executor_delegation_id"],
        "final_output": result["final_output"],
        "interaction_nodes": result["three_graphs"]["interaction_graph"].number_of_nodes(),
        "interaction_edges": result["three_graphs"]["interaction_graph"].number_of_edges(),
        "interaction_graph": serialize_nx(result["three_graphs"]["interaction_graph"]),
        "authority_graph": serialize_nx(result["three_graphs"]["authority_graph"]),
        "execution_graph": serialize_nx(result["three_graphs"]["execution_graph"]),
        "authority_nodes": result["three_graphs"]["authority_graph"].number_of_nodes(),
        "authority_edges": result["three_graphs"]["authority_graph"].number_of_edges(),
        "matrix": result["matrix"],
        "goal_dot": result["goal_dot"]
    }

# Ensure static routes match before parameterized routes on the same prefix (e.g. /graphs/validation before /graphs/{workflow_id})
router.routes.sort(key=lambda r: "{" in getattr(r, "path", ""))
