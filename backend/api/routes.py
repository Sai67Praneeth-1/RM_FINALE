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
    Precisely identifies whether a user message is an explicit instruction to audit or
    investigate our enterprise datasets (customer_complaints.csv, system_access_logs.csv, etc.).
    All general questions (math, science, coding, explanations, general definitions) return False
    so they are handled conversationally by Gemini like ChatGPT.
    """
    p_lower = prompt.lower().strip()

    # Fast exclusion: Basic math and arithmetic (e.g. 5*100, 2+2, 100/5)
    if any(op in p_lower for op in ["*", "+", "/", "="]) and len(p_lower) < 25 and not any(w in p_lower for w in ["audit", "complaint", "log"]):
        return False

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
            "workflow_run": None,
            "goal_flow_dot": None,
            "langgraph_topology_dot": None,
            "goal_traceability": [],
            "interaction_graph": default_graph,
            "interactions": [],
            "final_output": None
        }

    # 3. Determine if this is a data-related task that should trigger the multi-agent workflow
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

    run = runner.execute_workflow(
        task_description=msg,
        dataset_name=target_dataset,
        principal_id="user_chat_principal",
        mode=run_mode,
        capture_level=cap_enum
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

    graphs = three_graphs.get_graphs_for_workflow(run.workflow_id)
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
        "final_output": run.final_output
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
