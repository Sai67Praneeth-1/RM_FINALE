"""
Unit tests for Persistent SQLite Event Store.
Verifies table creation, event insertion, query retrieval, restart survival, and lineage closure.
"""

import pytest
import os
import tempfile
from backend.storage.event_store import EventStore
from backend.schemas.workflow import WorkflowRun, DelegationRecord, ArtifactRecord
from backend.schemas.events import CIMEvent, ActionSemantic, ActionOutcome, ResourceClass, SensitivityLabel
from backend.schemas.interaction import InteractionRecord, InteractionType

@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = EventStore(db_path=path)
    yield store, path
    store.close()
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

def test_workflow_persistence(temp_db):
    store, path = temp_db
    run = WorkflowRun(
        workflow_id="wf_test_101",
        name="Test Workflow",
        task_description="Execute test pipeline",
        dataset_name="customer_complaints.csv",
        status="completed"
    )
    store.save_workflow_run(run)
    store.close()
    
    # Simulate restart by creating a new EventStore instance pointing to same file
    store2 = EventStore(db_path=path)
    fetched = store2.get_workflow_run("wf_test_101")
    store2.close()
    assert fetched is not None
    assert fetched.workflow_id == "wf_test_101"
    assert fetched.name == "Test Workflow"
    assert fetched.status == "completed"

def test_delegation_lineage_closure(temp_db):
    store, _ = temp_db
    d0 = DelegationRecord(delegation_id="del_root", principal_id="user_admin", agent_id="agent_coordinator", task_id="task_0")
    d1 = DelegationRecord(delegation_id="del_child_1", delegation_parent_id="del_root", principal_id="user_admin", agent_id="agent_researcher", task_id="task_1")
    d2 = DelegationRecord(delegation_id="del_grandchild_2", delegation_parent_id="del_child_1", principal_id="user_admin", agent_id="agent_analyst", task_id="task_2")
    
    store.save_delegation(d0)
    store.save_delegation(d1)
    store.save_delegation(d2)

    closure = store.get_delegation_closure("del_root")
    closure_ids = [d.delegation_id for d in closure]
    assert len(closure) == 3
    assert "del_root" in closure_ids
    assert "del_child_1" in closure_ids
    assert "del_grandchild_2" in closure_ids

def test_interaction_persistence(temp_db):
    store, _ = temp_db
    itr = InteractionRecord(
        interaction_id="itr_test_55",
        sender_agent_id="agent_coordinator",
        receiver_agent_id="agent_researcher",
        interaction_type=InteractionType.REQUEST,
        conversation_id="conv_10",
        task_id="task_1",
        delegation_id="del_test",
        semantic_summary="Please fetch row count."
    )
    store.save_interaction(itr)
    
    fetched = store.get_interaction("itr_test_55")
    assert fetched is not None
    assert fetched.sender_agent_id == "agent_coordinator"
    assert fetched.receiver_agent_id == "agent_researcher"
    assert fetched.interaction_type == InteractionType.REQUEST

def test_mongo_chat_store_telemetry_persistence(tmp_path):
    from backend.storage.mongo_chat_store import MongoChatStore

    store = MongoChatStore(uri="", db_name="test_db")
    store._local_file_path = str(tmp_path / "test_local_chats.json")
    chat_id = "test_chat_storage_101"
    wf_id = "wf_storage_999"

    # Create chat and append assistant message
    store.create_chat(title="Storage Test Chat", chat_id=chat_id)
    store.append_message(
        chat_id=chat_id,
        role="assistant",
        content="Workflow analytical result",
        metadata={"workflow_id": wf_id}
    )

    sample_events = [
        {"event_id": "ev_01", "event_type": "task_received", "agent_id": "agent_coordinator"},
        {"event_id": "ev_02", "event_type": "tool_call", "agent_id": "agent_researcher"}
    ]
    sample_delgs = [
        {"delegation_id": "del_01", "principal_id": "user", "agent_id": "agent_coordinator"}
    ]
    sample_ixs = [
        {"interaction_id": "ix_01", "sender_agent_id": "agent_coordinator", "receiver_agent_id": "agent_researcher"}
    ]
    sample_graphs = {
        "execution_graph": {"nodes": [{"id": "n1"}], "edges": []},
        "authority_graph": {"nodes": [{"id": "a1"}], "edges": []},
        "interaction_graph": {"nodes": [{"id": "i1"}], "edges": []}
    }

    result = store.store_workflow_telemetry(
        chat_id=chat_id,
        workflow_id=wf_id,
        events=sample_events,
        delegations=sample_delgs,
        interactions=sample_ixs,
        workflow_run={"workflow_id": wf_id, "status": "completed"},
        graphs=sample_graphs,
        provenance={"nodes": ["p1"]}
    )

    assert result["status"] == "success"
    assert result["events_stored"] == 2
    assert result["delegations_stored"] == 1
    assert result["interactions_stored"] == 1

    # Verify retrieval methods
    retrieved_events = store.get_chat_events(chat_id)
    assert len(retrieved_events) == 2
    assert retrieved_events[0]["event_id"] == "ev_01"

    retrieved_delgs = store.get_chat_delegations(chat_id)
    assert len(retrieved_delgs) == 1
    assert retrieved_delgs[0]["delegation_id"] == "del_01"

    retrieved_ixs = store.get_chat_interactions(chat_id)
    assert len(retrieved_ixs) == 1
    assert retrieved_ixs[0]["interaction_id"] == "ix_01"

    telemetry = store.get_chat_telemetry(chat_id)
    assert telemetry["chat_id"] == chat_id
    assert telemetry["workflow_id"] == wf_id
    assert len(telemetry["execution_events"]) == 2
    assert "execution_graph" in telemetry["graphs"]
    assert telemetry["provenance"] is not None

    summary = store.get_chat_telemetry_summary()
    assert summary["total_execution_events"] >= 2
    assert summary["total_delegations"] >= 1
    assert summary["total_interactions"] >= 1
    assert "execution_events" in summary["collections"]
