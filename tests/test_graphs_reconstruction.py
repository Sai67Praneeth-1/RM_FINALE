"""
Unit tests for Graph Reconstruction (Three-Graph Model).
Verifies:
1. Execution Graph (causal flow)
2. Authority / Lineage Graph (delegations)
3. Interaction Graph (inter-agent communication)
"""

import pytest
import os
import tempfile
import networkx as nx
from backend.storage.event_store import EventStore
from backend.gateway.gateway import ObservabilityGateway
from backend.graphs.execution_graph import ExecutionGraphBuilder
from backend.graphs.authority_graph import AuthorityGraphBuilder
from backend.graphs.interaction_graph import InteractionGraphBuilder
from backend.graphs.three_graphs import ThreeGraphCoordinator
from backend.orchestration.workflow_runner import WorkflowRunner
from backend.schemas.workflow import WorkflowMode

@pytest.fixture
def executed_workflow_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = EventStore(db_path=path)
    gw = ObservabilityGateway(event_store=store)
    runner = WorkflowRunner(gateway=gw)
    
    # Run a quick workflow to populate all 3 graphs
    run = runner.execute_workflow(
        task_description="Execute test analysis for graph validation",
        dataset_name="customer_complaints.csv",
        mode=WorkflowMode.DETERMINISTIC_DEMO
    )
    yield store, run.workflow_id, path
    store.close()
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

def test_execution_graph_reconstruction(executed_workflow_store):
    store, wf_id, _ = executed_workflow_store
    builder = ExecutionGraphBuilder(store)
    G = builder.build_graph(workflow_id=wf_id)
    
    assert isinstance(G, nx.DiGraph)
    assert len(G.nodes) >= 3 # Read, analyze, report tool events
    for n in G.nodes:
        assert "action_semantic" in G.nodes[n]
        assert "tool_name" in G.nodes[n]

def test_authority_graph_reconstruction(executed_workflow_store):
    store, wf_id, _ = executed_workflow_store
    wf = store.get_workflow_run(wf_id)
    builder = AuthorityGraphBuilder(store)
    G = builder.build_graph(root_delegation_id=wf.root_delegation_id)
    
    assert isinstance(G, nx.DiGraph)
    assert len(G.nodes) >= 4 # Principal, Agent Coordinator, Sub-agents, Delegations
    # Verify delegation lineage edges exist
    edges = G.edges(data=True)
    edge_types = [d.get("edge_type") for _, _, d in edges]
    assert "authority_grant" in edge_types
    assert "authority_assignment" in edge_types

def test_interaction_graph_preserves_per_message_identity(executed_workflow_store):
    store, wf_id, _ = executed_workflow_store
    builder = InteractionGraphBuilder(store)
    G = builder.build_graph()
    
    assert isinstance(G, nx.MultiDiGraph)
    # Ensure there are multiple edges between agents representing distinct messages
    assert len(G.edges) >= 5
    for u, v, k, d in G.edges(keys=True, data=True):
        assert "interaction_id" in d
        assert "interaction_type" in d
        assert "delegation_id" in d

def test_three_graph_coordinator(executed_workflow_store):
    store, wf_id, _ = executed_workflow_store
    coordinator = ThreeGraphCoordinator(store)
    all_graphs = coordinator.get_graphs_for_workflow(wf_id)
    
    assert "execution_graph" in all_graphs
    assert "authority_graph" in all_graphs
    assert "interaction_graph" in all_graphs
