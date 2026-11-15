"""
Integration tests for FastAPI REST API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from backend.api.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_api_status(client):
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "metrics_summary" in data

def test_api_datasets(client):
    resp = client.get("/api/datasets")
    assert resp.status_code == 200
    datasets = resp.json()
    assert isinstance(datasets, list)
    names = [d["name"] for d in datasets]
    assert "customer_complaints.csv" in names

def test_api_start_workflow_and_get_details(client):
    payload = {
        "task_description": "API integration test for complaint audit",
        "dataset_name": "customer_complaints.csv",
        "principal_id": "api_test_principal",
        "mode": "deterministic_demo",
        "capture_level": 2
    }
    resp = client.post("/api/workflow/start", json=payload)
    assert resp.status_code == 200
    run_data = resp.json()
    assert run_data["status"] == "completed"
    wf_id = run_data["workflow_id"]

    # Get workflow details
    resp_get = client.get(f"/api/workflow/{wf_id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["workflow_id"] == wf_id

    # Get graphs
    resp_graphs = client.get(f"/api/graphs/{wf_id}")
    assert resp_graphs.status_code == 200
    g_data = resp_graphs.json()
    assert "execution_graph" in g_data
    assert "authority_graph" in g_data
    assert "interaction_graph" in g_data

def test_api_evaluation_results(client):
    resp = client.get("/api/evaluation/results")
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, list)
    assert len(results) > 0

def test_api_chat_and_goal_flow(client):
    # Test chat greeting
    resp_greet = client.post("/api/chat", json={"message": "Hello, who are you?"})
    assert resp_greet.status_code == 200
    assert "Agent A (Coordinator)" in resp_greet.json()["response"]

    # Test chat task execution
    resp_task = client.post("/api/chat", json={
        "message": "Audit customer complaints for critical tickets",
        "dataset_name": "customer_complaints.csv",
        "mode": "deterministic_demo"
    })
    assert resp_task.status_code == 200
    data = resp_task.json()
    assert "goal_flow_dot" in data
    assert "goal_traceability" in data
    assert len(data["goal_traceability"]) == 4
    wf_id = data["workflow_run"]["workflow_id"]

    # Test goal flow endpoint
    resp_flow = client.get(f"/api/goal_flow/{wf_id}")
    assert resp_flow.status_code == 200
    flow_data = resp_flow.json()
    assert "goal_flow_dot" in flow_data
    assert "langgraph_topology_dot" in flow_data
    assert len(flow_data["goal_traceability"]) == 4

