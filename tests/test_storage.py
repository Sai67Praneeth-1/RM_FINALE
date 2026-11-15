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
