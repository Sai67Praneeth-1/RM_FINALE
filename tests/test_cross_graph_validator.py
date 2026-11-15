"""
Unit and Integration tests for CrossGraphValidator and Cross-Graph API endpoints (Topics 5, 6, 7).
Validates:
1. Invariant 1: Authority Coverage
2. Invariant 2: Interaction-Execution Links
3. Invariant 3: Temporal Validity
4. Alignment Score: Comp(d)
5. Full Report Generation & ThreeGraphCoordinator integration
6. API Endpoints: /api/graphs/cross-graph-context and /api/graphs/validation
"""

import pytest
import os
import tempfile
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.storage.event_store import EventStore
from backend.schemas.events import CIMEvent, ActionSemantic, ActionOutcome
from backend.schemas.workflow import DelegationRecord, DelegationStatus
from backend.schemas.interaction import InteractionRecord, InteractionType
from backend.graphs.cross_graph_validator import CrossGraphValidator
from backend.graphs.three_graphs import ThreeGraphCoordinator
from backend.api.main import app


@pytest.fixture
def fresh_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = EventStore(db_path=path)
    yield store
    store.close()
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def test_cross_graph_validator_invariants(fresh_store):
    store = fresh_store
    now = datetime.now(timezone.utc)
    t0 = (now - timedelta(minutes=5)).isoformat()
    t1 = (now - timedelta(minutes=3)).isoformat()
    t2 = (now - timedelta(minutes=1)).isoformat()

    # 1. Setup valid delegation
    del1 = DelegationRecord(
        delegation_id="del_valid_01",
        principal_id="principal_alice",
        agent_id="agent_analyst",
        task_id="task_01",
        scope="execute_analysis",
        status=DelegationStatus.ACTIVE,
        issued_at=t0,
        completed_at=t2
    )
    store.save_delegation(del1)

    # 2. Setup execution events
    ev1 = CIMEvent(
        event_id="ev_valid_01",
        workflow_id="wf_test_01",
        time=t1,
        delegation_id="del_valid_01",
        principal_user_id="principal_alice",
        agent_id="agent_analyst",
        tool_name="sentiment_analyzer",
        tool_operation="analyze",
        action_semantic=ActionSemantic.INVOKE,
        action_outcome=ActionOutcome.SUCCESS,
        resource_id="res_doc_101"
    )
    store.save_execution_event(ev1)

    # Event with missing delegation
    ev_invalid_del = CIMEvent(
        event_id="ev_orphan_02",
        workflow_id="wf_test_01",
        time=t1,
        delegation_id="del_nonexistent_99",
        principal_user_id="principal_alice",
        agent_id="agent_analyst",
        tool_name="file_writer",
        tool_operation="write",
        action_semantic=ActionSemantic.WRITE,
        action_outcome=ActionOutcome.SUCCESS
    )
    store.save_execution_event(ev_invalid_del)

    # Event with temporal violation (occurred before delegation issued_at)
    t_early = (now - timedelta(minutes=10)).isoformat()
    ev_temporal_bad = CIMEvent(
        event_id="ev_time_bad_03",
        workflow_id="wf_test_01",
        time=t_early,
        delegation_id="del_valid_01",
        principal_user_id="principal_alice",
        agent_id="agent_analyst",
        tool_name="data_cleaner",
        tool_operation="clean",
        action_semantic=ActionSemantic.READ,
        action_outcome=ActionOutcome.SUCCESS
    )
    store.save_execution_event(ev_temporal_bad)

    # 3. Setup interaction with downstream actions
    interact1 = InteractionRecord(
        interaction_id="interact_01",
        timestamp=t0,
        sender_agent_id="agent_coordinator",
        receiver_agent_id="agent_analyst",
        interaction_type=InteractionType.DELEGATION,
        conversation_id="conv_test_01",
        task_id="wf_test_01",
        delegation_id="del_valid_01",
        message_id="msg_01",
        downstream_action_ids=["ev_valid_01", "ev_orphan_02"]
    )
    store.save_interaction(interact1)

    # Interaction with a missing downstream action link
    interact_bad = InteractionRecord(
        interaction_id="interact_02",
        timestamp=t0,
        sender_agent_id="agent_coordinator",
        receiver_agent_id="agent_analyst",
        interaction_type=InteractionType.CLARIFICATION,
        conversation_id="conv_test_01",
        task_id="wf_test_01",
        delegation_id="del_valid_01",
        message_id="msg_02",
        downstream_action_ids=["ev_ghost_999"]
    )
    store.save_interaction(interact_bad)

    validator = CrossGraphValidator(store)

    # Invariant 1: Authority Coverage
    cov = validator.validate_authority_coverage("wf_test_01")
    assert cov["passed"] == 2  # ev1 and ev_temporal_bad have valid delegation_id
    assert cov["failed"] == 1  # ev_invalid_del has nonexistent delegation
    assert cov["score"] == round(2 / 3, 4)
    assert any(v["event_id"] == "ev_orphan_02" for v in cov["violations"])

    # Invariant 2: Interaction-Execution Links
    links = validator.validate_interaction_execution_links("wf_test_01")
    assert links["passed"] == 2  # ev_valid_01 and ev_orphan_02 exist
    assert links["failed"] == 1  # ev_ghost_999 does not exist
    assert links["score"] == round(2 / 3, 4)
    assert any(v["event_id"] == "ev_ghost_999" for v in links["violations"])

    # Invariant 3: Temporal Validity
    temp = validator.validate_temporal_validity("wf_test_01")
    assert temp["passed"] == 1  # ev1 is within [t0, t2]
    assert temp["failed"] == 2  # ev_invalid_del (no valid del) and ev_temporal_bad (issued_at > event.time)
    assert temp["score"] == round(1 / 3, 4)

    # Comp(d)
    comp_d = validator.compute_comp_d("wf_test_01")
    assert comp_d == round(2 / 3, 4)

    # Full report
    report = validator.run_full_validation("wf_test_01")
    assert report["workflow_id"] == "wf_test_01"
    assert report["total_events"] == 3
    assert report["overall_status"] == "PARTIAL_VIOLATIONS"
    assert "invariant_1_authority_coverage" in report
    assert "invariant_2_interaction_execution_links" in report
    assert "invariant_3_temporal_validity" in report
    assert "comp_d" in report


def test_three_graph_coordinator_validate_workflow(fresh_store):
    store = fresh_store
    coordinator = ThreeGraphCoordinator(store)
    report = coordinator.validate_workflow("wf_empty")
    assert report["total_events"] == 0
    assert report["overall_status"] == "PASS"
    assert report["comp_d"] == 1.0


def test_api_cross_graph_endpoints():
    from backend.api.routes import store
    now = datetime.now(timezone.utc)
    t0 = (now - timedelta(minutes=5)).isoformat()
    t1 = (now - timedelta(minutes=3)).isoformat()

    del_root = DelegationRecord(
        delegation_id="del_root_api",
        principal_id="principal_bob",
        agent_id="agent_coordinator",
        task_id="task_root",
        scope="manage",
        status=DelegationStatus.ACTIVE,
        issued_at=t0
    )
    del_child = DelegationRecord(
        delegation_id="del_child_api",
        delegation_parent_id="del_root_api",
        principal_id="agent_coordinator",
        agent_id="agent_researcher",
        task_id="task_child",
        scope="query_data",
        status=DelegationStatus.ACTIVE,
        issued_at=t0
    )
    store.save_delegation(del_root)
    store.save_delegation(del_child)

    ev = CIMEvent(
        event_id="ev_api_01",
        workflow_id="wf_api_01",
        time=t1,
        delegation_id="del_child_api",
        principal_user_id="principal_bob",
        agent_id="agent_researcher",
        tool_name="data_loader",
        action_semantic=ActionSemantic.READ,
        action_outcome=ActionOutcome.SUCCESS,
        resource_id="res_dataset_99"
    )
    store.save_execution_event(ev)

    inter = InteractionRecord(
        interaction_id="inter_api_01",
        timestamp=t0,
        sender_agent_id="agent_coordinator",
        receiver_agent_id="agent_researcher",
        interaction_type=InteractionType.DELEGATION,
        conversation_id="conv_api_01",
        task_id="wf_api_01",
        delegation_id="del_child_api",
        message_id="msg_api_01",
        downstream_action_ids=["ev_api_01"]
    )
    store.save_interaction(inter)

    # Use client to query the endpoints
    client = TestClient(app)

    # Test /api/graphs/validation
    res_val = client.get("/api/graphs/validation", params={"workflow_id": "wf_api_01"})
    assert res_val.status_code == 200
    val_data = res_val.json()
    assert val_data["workflow_id"] == "wf_api_01"
    assert val_data["total_events"] == 1
    assert val_data["overall_status"] == "PASS"

    # Test /api/graphs/cross-graph-context
    res_ctx = client.get("/api/graphs/cross-graph-context", params={"event_id": "ev_api_01"})
    assert res_ctx.status_code == 200
    ctx_data = res_ctx.json()
    assert ctx_data["event"]["event_id"] == "ev_api_01"
    # Check delegation chain (child -> root)
    assert len(ctx_data["delegation_chain"]) == 2
    assert ctx_data["delegation_chain"][0]["delegation_id"] == "del_child_api"
    assert ctx_data["delegation_chain"][1]["delegation_id"] == "del_root_api"
    # Check triggering interactions
    assert len(ctx_data["triggering_interactions"]) >= 1
    assert ctx_data["triggering_interactions"][0]["interaction_id"] == "inter_api_01"
    # Check invariant checks
    assert ctx_data["invariant_checks"]["authority_coverage_valid"] is True
    assert ctx_data["invariant_checks"]["temporal_validity_valid"] is True

    # Test 404 on nonexistent event
    res_404 = client.get("/api/graphs/cross-graph-context", params={"event_id": "ev_nonexistent_999"})
    assert res_404.status_code == 404
