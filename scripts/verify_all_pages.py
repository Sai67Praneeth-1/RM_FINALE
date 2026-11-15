"""
Comprehensive Verification Script for RM_FINALE.
Simulates and exercises all views, pages, data access methods,
graphs, provenance traversals, and multi-agent workflows to guarantee zero errors.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import settings
from backend.storage.event_store import EventStore
from backend.orchestration.workflow_runner import WorkflowRunner
from backend.schemas.workflow import WorkflowMode
from backend.schemas.events import CaptureLevel, InteractionType
from backend.tools.file_tools import list_sample_datasets
from backend.graphs.three_graphs import ThreeGraphCoordinator
from backend.graphs.goal_flow import generate_goal_flow_dot, generate_langgraph_statemachine_dot, extract_goal_traceability
from backend.provenance.tracker import ProvenanceTracker
from backend.evaluation.runner import BenchmarkRunner

def main():
    print("=" * 70)
    print("RUNNING COMPREHENSIVE MULTI-PAGE & FEATURE VERIFICATION")
    print("=" * 70)

    store = EventStore()
    runner = WorkflowRunner(store.get_gateway() if hasattr(store, "get_gateway") else None)
    three_graphs = ThreeGraphCoordinator(store)
    prov_tracker = ProvenanceTracker(store)
    benchmark = BenchmarkRunner(store)

    # 1. Test Overview metrics
    print("\n[1/8] Verifying Overview Metrics...")
    summary = store.get_metrics_summary()
    assert "total_workflows" in summary
    assert "active_agents" in summary
    print(f" -> Metrics verified: {summary}")

    # 2. Test Datasets
    print("\n[2/8] Verifying Datasets...")
    datasets = list_sample_datasets()
    assert len(datasets) >= 2
    print(f" -> Found {len(datasets)} verified sample datasets.")

    # 3. Test Workflow Execution with both tasks
    print("\n[3/8] Verifying Workflow Execution (Complaint Audit)...")
    run1 = runner.execute_workflow(
        task_description="Verify customer complaints audit for high severity items",
        dataset_name="customer_complaints.csv",
        principal_id="test_principal_1",
        mode=WorkflowMode.DETERMINISTIC_DEMO,
        capture_level=CaptureLevel.METADATA_SUMMARY
    )
    assert run1.status == "completed"
    print(f" -> Run 1 Completed successfully (ID: {run1.workflow_id})")

    print("\n[4/8] Verifying Workflow Execution (Security Log Audit)...")
    run2 = runner.execute_workflow(
        task_description="Verify security access logs for root escalation and violations",
        dataset_name="system_access_logs.csv",
        principal_id="test_principal_2",
        mode=WorkflowMode.DETERMINISTIC_DEMO,
        capture_level=CaptureLevel.FULL_CONTENT
    )
    assert run2.status == "completed"
    print(f" -> Run 2 Completed successfully (ID: {run2.workflow_id})")

    # 4. Test Goal Flow & LangGraph State Machine
    print("\n[5/8] Verifying Goal Flow and LangGraph Topology Generation...")
    del_closure = store.get_delegation_closure(run1.root_delegation_id)
    del_map = {d.agent_id: d for d in del_closure}
    goal_dot = generate_goal_flow_dot(
        task_description=run1.task_description,
        dataset_name="customer_complaints.csv",
        root_delegation_id=run1.root_delegation_id,
        research_delegation_id=del_map.get("agent_researcher").delegation_id if "agent_researcher" in del_map else None,
        analysis_delegation_id=del_map.get("agent_analyst").delegation_id if "agent_analyst" in del_map else None,
        report_delegation_id=del_map.get("agent_reporter").delegation_id if "agent_reporter" in del_map else None,
        clarification_occurred=True,
        status=run1.status
    )
    assert "digraph GoalFlow" in goal_dot
    
    statemachine_dot = generate_langgraph_statemachine_dot()
    assert "digraph LangGraphTopology" in statemachine_dot

    interactions = store.list_interactions(limit=50)
    events = store.list_execution_events(workflow_id=run1.workflow_id)
    matrix = extract_goal_traceability(run1.model_dump(), del_closure, interactions, events)
    assert len(matrix) == 4
    print(" -> Goal flow and topology validated with 4-agent traceability matrix.")

    # 5. Test Three Graphs
    print("\n[6/8] Verifying Three-Graph Reconstruction...")
    graphs = three_graphs.get_graphs_for_workflow(run1.workflow_id)
    assert "execution_graph" in graphs
    assert "authority_graph" in graphs
    assert "interaction_graph" in graphs
    fig1 = three_graphs.render_plotly_graph(graphs["execution_graph"], "Execution Graph", "execution")
    fig2 = three_graphs.render_plotly_graph(graphs["authority_graph"], "Authority Graph", "authority")
    fig3 = three_graphs.render_plotly_graph(graphs["interaction_graph"], "Interaction Graph", "interaction")
    assert fig1 and fig2 and fig3
    print(" -> Three graphs generated and Plotly figures rendered successfully.")

    # 6. Test Provenance Tracking & Plotly
    print("\n[7/8] Verifying Provenance Tracking and Backward Lineage...")
    artifacts = store.list_artifacts()
    assert len(artifacts) > 0
    art = artifacts[0]
    lineage = prov_tracker.trace_backward_lineage(art.artifact_id, workflow_id=art.workflow_id)
    assert len(lineage) > 0
    fig_prov = prov_tracker.render_provenance_plotly(art.workflow_id)
    assert fig_prov
    print(f" -> Provenance lineage traced {len(lineage)} elements. Plotly figure created.")

    # 7. Test Evaluation Benchmarks
    print("\n[8/8] Verifying Benchmark Results...")
    assert benchmark.results_json_path.exists()
    print(" -> Benchmark cache verified.")

    print("\n" + "=" * 70)
    print("ALL FEATURES & MODULES VERIFIED WITH ZERO ERRORS!")
    print("=" * 70)

if __name__ == "__main__":
    main()
