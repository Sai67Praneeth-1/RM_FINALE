"""
FastAPI REST API Routes for Observability Platform.
Exposes endpoints for workflow orchestration, graph exploration,
provenance tracing, event inspection, and research benchmarks.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List, Dict, Any
import json
from pydantic import BaseModel

from backend.config import settings
from backend.storage.event_store import EventStore
from backend.orchestration.workflow_runner import WorkflowRunner
from backend.schemas.workflow import WorkflowMode
from backend.schemas.events import CaptureLevel
from backend.tools.file_tools import list_sample_datasets
from backend.agents.llm_client import is_ollama_available, list_installed_ollama_models
from backend.orchestration.hf_simulation import run_huggingface_transparency_simulation
from backend.graphs.three_graphs import ThreeGraphCoordinator
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
    ollama_ok = is_ollama_available()
    models = list_installed_ollama_models() if ollama_ok else []
    metrics = store.get_metrics_summary()
    return {
        "status": "healthy",
        "database_path": settings.DATABASE_PATH,
        "capture_level": settings.DEFAULT_CAPTURE_LEVEL,
        "huggingface_router_url": settings.HF_ROUTER_BASE_URL,
        "huggingface_coordinator_model": settings.HF_COORDINATOR_MODEL,
        "huggingface_executor_model": settings.HF_EXECUTOR_MODEL,
        "huggingface_available": True,
        "ollama_available": ollama_ok,
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "ollama_model": settings.OLLAMA_MODEL,
        "installed_models": models,
        "metrics_summary": metrics
    }

@router.get("/datasets")
def get_datasets():
    return list_sample_datasets()

@router.post("/workflow/start")
def start_workflow(req: StartWorkflowRequest):
    if req.mode == "live_huggingface":
        mode = WorkflowMode.LIVE_HUGGINGFACE
    elif req.mode == "live_ollama":
        mode = WorkflowMode.LIVE_OLLAMA
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
    limit: int = 200
):
    return store.list_interactions(
        conversation_id=conversation_id,
        delegation_id=delegation_id,
        agent_id=agent_id,
        interaction_type=interaction_type,
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

from backend.graphs.goal_flow import generate_goal_flow_dot, generate_langgraph_statemachine_dot, extract_goal_traceability

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    dataset_name: Optional[str] = "customer_complaints.csv"
    mode: Optional[str] = "deterministic_demo"
    capture_level: Optional[int] = 2

@router.post("/chat")
def chat_with_coordinator(req: ChatRequest):
    """
    Interactive conversational endpoint with Agent A (Coordinator).
    Accepts goals, tasks, or questions, coordinates with the multi-agent team,
    and returns conversational responses with full goal-based transparency.
    """
    msg_lower = req.message.lower().strip()
    
    # 1. First evaluate direct conversational answer & relevance gate
    direct_ans, should_run_workflow = answer_user_query_directly(req.message)
    if not should_run_workflow:
        return {
            "response": direct_ans,
            "workflow_run": None,
            "goal_flow_dot": None,
            "goal_traceability": [],
            "interaction_graph": {
                "nodes": [
                    {"id": "agent_coordinator", "label": "Coordinator", "node_type": "agent", "role": "Lead Orchestrator"}
                ],
                "edges": []
            },
            "interactions": []
        }

    # Automatically select dataset if mentioned in prompt or inferred dynamically
    query_info = analyze_dynamic_query(req.message)
    target_dataset = req.dataset_name or query_info.get("target_dataset", "customer_complaints.csv")

    # Execute workflow under user delegation
    if req.mode == "live_huggingface":
        run_mode = WorkflowMode.LIVE_HUGGINGFACE
    elif req.mode == "live_ollama":
        run_mode = WorkflowMode.LIVE_OLLAMA
    else:
        run_mode = WorkflowMode.DETERMINISTIC_DEMO
    cap_enum = CaptureLevel(req.capture_level or 2)
    
    run = runner.execute_workflow(
        task_description=req.message,
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

    reply = format_direct_task_findings(req.message, target_dataset, run)
    graphs = three_graphs.get_graphs_for_workflow(run.workflow_id)

    return {
        "response": reply,
        "workflow_run": run.model_dump(),
        "goal_flow_dot": goal_dot,
        "langgraph_topology_dot": statemachine_dot,
        "goal_traceability": matrix,
        "interaction_graph": serialize_nx(graphs["interaction_graph"]),
        "execution_graph": serialize_nx(graphs["execution_graph"]),
        "authority_graph": serialize_nx(graphs["authority_graph"]),
        "interactions": [i.model_dump() for i in interactions],
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
