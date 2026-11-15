"""
Integration tests for LangGraph Multi-Agent Orchestration.
Verifies conditional execution, genuine inter-agent messages,
clarification handling, and end-to-end report synthesis.
"""

import pytest
import os
import tempfile
from backend.storage.event_store import EventStore
from backend.gateway.gateway import ObservabilityGateway
from backend.orchestration.workflow_runner import WorkflowRunner
from backend.schemas.workflow import WorkflowMode
from backend.schemas.events import CaptureLevel

@pytest.fixture
def workflow_env():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = EventStore(db_path=path)
    gw = ObservabilityGateway(event_store=store)
    runner = WorkflowRunner(gateway=gw)
    yield runner, store, path
    store.close()
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

def test_full_langgraph_workflow_execution(workflow_env):
    runner, store, _ = workflow_env
    
    # Run workflow with clarification trigger in prompt
    run = runner.execute_workflow(
        task_description="Analyze high severity complaints, request priority clarification from Coordinator, and generate executive report.",
        dataset_name="customer_complaints.csv",
        mode=WorkflowMode.DETERMINISTIC_DEMO,
        capture_level=CaptureLevel.METADATA_SUMMARY
    )

    assert run.status == "completed"
    assert run.final_output is not None
    assert "# Executive Audit & Analysis" in run.final_output
    assert run.stats.get("clarification_occurred") is True
    assert run.stats.get("events_count", 0) >= 3
    assert run.stats.get("interactions_count", 0) >= 6

    # Verify persistence in SQLite
    persisted_run = store.get_workflow_run(run.workflow_id)
    assert persisted_run is not None
    assert persisted_run.status == "completed"

    # Verify artifacts
    artifacts = store.list_artifacts(workflow_id=run.workflow_id)
    assert len(artifacts) >= 1
    assert artifacts[0].artifact_type == "final_report"

def test_security_audit_workflow_pattern(workflow_env):
    runner, store, _ = workflow_env
    
    # Task Pattern 2: Security Access Log Audit
    run = runner.execute_workflow(
        task_description="Audit system access logs for unauthorized actions and high-sensitivity touches.",
        dataset_name="system_access_logs.csv",
        mode=WorkflowMode.DETERMINISTIC_DEMO,
        capture_level=CaptureLevel.FULL_CONTENT
    )

    assert run.status == "completed"
    assert run.final_output is not None
    assert "System Access Logs" in run.final_output

def test_w1_parallel_subtasks_workflow(workflow_env):
    runner, store, _ = workflow_env
    
    # Executes Canonical Workload W1: Parallel tool execution
    run = runner.execute_workflow(
        task_description="Perform cross-system parallel ingestion across complaints and access logs",
        dataset_name="customer_complaints.csv",
        mode=WorkflowMode.DETERMINISTIC_DEMO,
        workflow_type="w1_parallel"
    )

    assert run.status == "completed"
    assert run.final_output is not None
    assert "W1 Parallel Subtasks Synthesis" in run.final_output
    assert "node_w1_read_primary" in run.stats.get("node_history", [])
    assert "node_w1_read_secondary" in run.stats.get("node_history", [])
    assert "node_w1_join" in run.stats.get("node_history", [])

def test_w3_trial_and_adapt_workflow(workflow_env):
    runner, store, _ = workflow_env
    
    # Executes Canonical Workload W3: Trial-and-adapt with retries
    run = runner.execute_workflow(
        task_description="Execute iterative query trial with dynamic parameter adaptation",
        dataset_name="customer_complaints.csv",
        mode=WorkflowMode.DETERMINISTIC_DEMO,
        workflow_type="w3_retry"
    )

    assert run.status == "completed"
    assert run.final_output is not None
    assert run.stats.get("retry_count", 0) >= 1
    assert "node_w3_backtrack_adapt" in run.stats.get("node_history", [])

def test_langgraph_mermaid_and_dot_export(workflow_env):
    from backend.orchestration.langgraph_workflow import (
        get_langgraph_mermaid,
        get_langgraph_topology_dot,
        get_available_workflow_topologies
    )
    
    topos = get_available_workflow_topologies()
    assert "adaptive" in topos
    assert "w1_parallel" in topos
    assert "w3_retry" in topos

    # Verify Mermaid generation directly from LangGraph object
    mermaid_adaptive = get_langgraph_mermaid("adaptive")
    assert "graph TD" in mermaid_adaptive
    assert "node_init_coordinator" in mermaid_adaptive

    mermaid_w1 = get_langgraph_mermaid("w1_parallel")
    assert "node_w1_join" in mermaid_w1

    # Verify DOT topology generation
    dot = get_langgraph_topology_dot("adaptive", active_nodes=["node_init_coordinator"])
    assert "digraph LangGraphTopology" in dot
    assert "node_init_coordinator" in dot

