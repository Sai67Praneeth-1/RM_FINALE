"""
Unit tests for Provenance Layer (W3C PROV Alignment).
Verifies provenance DAG creation, backward lineage traversal, and evidence integrity.
"""

import pytest
import os
import tempfile
import networkx as nx
from backend.storage.event_store import EventStore
from backend.gateway.gateway import ObservabilityGateway
from backend.provenance.tracker import ProvenanceTracker
from backend.orchestration.workflow_runner import WorkflowRunner
from backend.schemas.workflow import WorkflowMode

@pytest.fixture
def prov_env():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = EventStore(db_path=path)
    gw = ObservabilityGateway(event_store=store)
    runner = WorkflowRunner(gateway=gw)
    run = runner.execute_workflow(
        task_description="Execute provenance pipeline test",
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

def test_provenance_dag_construction(prov_env):
    store, wf_id, _ = prov_env
    tracker = ProvenanceTracker(store)
    G = tracker.build_provenance_graph(workflow_id=wf_id)
    
    assert isinstance(G, nx.DiGraph)
    assert len(G.nodes) >= 2
    assert len(G.edges) >= 2
    
    # Check relations
    relations = [d.get("relation") for _, _, d in G.edges(data=True)]
    assert "wasDerivedFrom" in relations or "used" in relations

def test_backward_lineage_trace(prov_env):
    store, wf_id, _ = prov_env
    tracker = ProvenanceTracker(store)
    artifacts = store.list_artifacts(workflow_id=wf_id)
    assert len(artifacts) > 0
    art_id = artifacts[0].artifact_id
    
    path = tracker.trace_backward_lineage(target_id=art_id, workflow_id=wf_id)
    assert len(path) > 0
    node_ids = [p["node_id"] for p in path]
    assert art_id in node_ids

def test_w3c_prov_json_and_prov_n_export(prov_env):
    store, wf_id, _ = prov_env
    tracker = ProvenanceTracker(store)
    
    # Test W3C PROV-JSON
    p_json = tracker.export_prov_json(wf_id)
    assert "prefix" in p_json
    assert "entity" in p_json
    assert "activity" in p_json or "wasDerivedFrom" in p_json
    
    # Test W3C PROV-N notation
    p_n = tracker.export_prov_n(wf_id)
    assert "document" in p_n
    assert "endDocument" in p_n

    # Test Provenance Completeness
    comp = tracker.get_provenance_completeness(wf_id)
    assert comp > 0.0
