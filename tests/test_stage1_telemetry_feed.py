"""
Stage 1 Automated Verification Test Suite:
Validates the Unified Observability Telemetry API (/api/telemetry/overview).
Tests data feed integrity, KPI metrics, agent workload breakdown,
interaction distribution, live event streams, and MongoDB chat stats.
"""

from fastapi.testclient import TestClient
from backend.api.main import app

def run_stage1_tests():
    print("================================================================================")
    print(" STAGE 1 VERIFICATION: UNIFIED TELEMETRY DATA FEED & BACKEND API")
    print("================================================================================")
    
    client = TestClient(app)

    # 1. Fetch telemetry overview endpoint
    print("\n[Step 1/5] Calling GET /api/telemetry/overview...")
    res = client.get("/api/telemetry/overview")
    assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}: {res.text}"
    data = res.json()
    print(" -> Response 200 OK received.")
    assert data.get("status") == "healthy"
    assert "timestamp" in data

    # 2. Validate Top-Level KPI Metrics
    print("\n[Step 2/5] Validating KPI Metrics Schema & Values...")
    metrics = data.get("metrics", {})
    required_kpis = [
        "total_workflows", "completed_workflows", "active_workflows", "failed_workflows",
        "success_rate_pct", "total_events", "total_interactions", "total_delegations",
        "total_retries", "active_agents", "mongodb_chats_count", "mongodb_messages_count"
    ]
    for k in required_kpis:
        assert k in metrics, f"Missing KPI metric '{k}' in response"
        print(f"    * {k}: {metrics[k]}")

    assert metrics["total_workflows"] >= 0
    assert metrics["total_events"] >= 0
    assert metrics["total_interactions"] >= 0
    assert metrics["active_agents"] >= 1
    assert metrics["mongodb_chats_count"] >= 0
    assert metrics["mongodb_messages_count"] >= 0
    assert 0.0 <= metrics["success_rate_pct"] <= 100.0
    print(" -> KPI metrics schema and values validated successfully.")

    # 3. Validate Agent Workload Breakdown
    print("\n[Step 3/5] Validating Multi-Agent Activity Breakdown...")
    agents = data.get("agent_breakdown", [])
    assert len(agents) == 4, f"Expected 4 specialized agents, got {len(agents)}"
    agent_ids = [a["agent_id"] for a in agents]
    expected_ids = ["agent_coordinator", "agent_researcher", "agent_analyst", "agent_reporter"]
    assert agent_ids == expected_ids, f"Agent list mismatch: {agent_ids}"

    for a in agents:
        print(f"    * {a['name']} ({a['role']}):")
        print(f"        Events: {a['events_count']} | Sent: {a['interactions_sent']} | Activity: {a['activity_pct']}%")
        assert "events_count" in a
        assert "interactions_sent" in a
        assert "interactions_received" in a
        assert "total_activity" in a
        assert "activity_pct" in a
        assert "color" in a
    print(" -> Multi-agent workload distribution validated.")

    # 4. Validate Interaction Breakdown & Live Feeds
    print("\n[Step 4/5] Validating Interaction Breakdown & Live Event Stream...")
    it_types = data.get("interaction_breakdown", [])
    assert len(it_types) > 0, "Expected at least 1 interaction type"
    print(f" -> Found {len(it_types)} distinct interaction categories.")
    for it in it_types:
        print(f"    * {it['label']} ({it['type']}): {it['count']} messages ({it['percentage']}%)")
        assert "type" in it
        assert "label" in it
        assert "count" in it
        assert "percentage" in it
        assert "color" in it

    # Workflows feed
    recent_wf = data.get("recent_workflows", [])
    print(f" -> Recent workflows in stream: {len(recent_wf)}")
    if recent_wf:
        first_wf = recent_wf[0]
        assert "workflow_id" in first_wf
        assert "status" in first_wf
        assert "dataset_name" in first_wf
        print(f"    * Latest Workflow: {first_wf['workflow_id']} [{first_wf['status']}] - {first_wf['name'][:40]}")

    # Event stream
    live_events = data.get("live_event_stream", [])
    print(f" -> Live CIM events in stream: {len(live_events)}")
    if live_events:
        first_ev = live_events[0]
        assert "event_id" in first_ev
        assert "agent_id" in first_ev
        assert "tool_name" in first_ev
        assert "action_outcome" in first_ev
        print(f"    * Latest CIM Event: {first_ev['event_id']} by {first_ev['agent_id']} ({first_ev['tool_name']} -> {first_ev['action_outcome']})")

    # 5. Validate Storage, MongoDB Telemetry & Query Limits
    print("\n[Step 5/5] Validating Storage, Infrastructure & Limit Parameters...")
    storage = data.get("storage", {})
    assert "database_path" in storage
    assert "file_size_formatted" in storage
    print(f" -> SQLite Database Size: {storage['file_size_formatted']}")

    mongo_tel = data.get("mongodb_telemetry", {})
    assert "mongodb_connected" in mongo_tel
    assert isinstance(mongo_tel["mongodb_connected"], bool)
    print(f" -> MongoDB Connected: {mongo_tel['mongodb_connected']}, Database: {mongo_tel.get('database')}")

    # Test limit parameters
    param_res = client.get("/api/telemetry/overview?workflow_limit=3&event_limit=5")
    assert param_res.status_code == 200
    param_data = param_res.json()
    assert len(param_data.get("recent_workflows", [])) <= 3
    assert len(param_data.get("live_event_stream", [])) <= 5
    print(" -> Custom limit parameters (workflow_limit=3, event_limit=5) verified.")

    print("\n================================================================================")
    print(" STAGE 1 VERIFICATION COMPLETE: ALL CHECKS PASSED WITH 100% SUCCESS!")
    print("================================================================================")

def test_stage1_telemetry_feed():
    run_stage1_tests()

if __name__ == "__main__":
    run_stage1_tests()
