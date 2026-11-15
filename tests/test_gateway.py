"""
Unit tests for Central Observability Gateway and Tool Client.
Verifies authoritative delegation minting, tool wrapping, and semantic normalization.
"""

import pytest
import os
import tempfile
from backend.gateway.gateway import ObservabilityGateway
from backend.gateway.tool_wrapper import InstrumentedToolClient
from backend.storage.event_store import EventStore
from backend.schemas.events import ActionSemantic, ActionOutcome, ResourceClass, InteractionType

@pytest.fixture
def temp_gateway():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = EventStore(db_path=path)
    gw = ObservabilityGateway(event_store=store)
    yield gw, store, path
    store.close()
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

def test_delegation_minting_and_verification(temp_gateway):
    gw, _, _ = temp_gateway
    root_del = gw.mint_delegation(
        principal_id="user_alice",
        agent_id="agent_coordinator",
        task_id="task_root_10",
        scope="root_coordination"
    )
    assert root_del.delegation_id.startswith("del_")
    assert root_del.principal_id == "user_alice"
    assert root_del.delegation_parent_id is None

    # Child delegation
    child_del = gw.mint_delegation(
        principal_id="user_alice",
        agent_id="agent_researcher",
        task_id="task_child_11",
        parent_delegation_id=root_del.delegation_id,
        scope="data_collection"
    )
    assert child_del.delegation_parent_id == root_del.delegation_id
    
    # Verification
    verified = gw.verify_delegation(child_del.delegation_id)
    assert verified is not None
    assert verified.delegation_id == child_del.delegation_id

def test_instrumented_tool_execution(temp_gateway):
    gw, _, _ = temp_gateway
    tool_client = InstrumentedToolClient(gateway=gw)
    
    # Execute allowlisted dataset read
    res, cim_evt = tool_client.read_dataset(
        file_name="customer_complaints.csv",
        agent_id="agent_researcher",
        delegation_id="del_test_tool",
        principal_id="user_alice",
        workflow_id="wf_tool_test",
        task_id="task_tool_test"
    )
    
    assert res is not None
    assert "data" in res
    assert cim_evt is not None
    assert cim_evt.action_semantic == ActionSemantic.READ
    assert cim_evt.action_outcome == ActionOutcome.SUCCESS
    assert cim_evt.resource_type == ResourceClass.DATASET
    assert cim_evt.resource_id == "customer_complaints.csv"
    assert "elapsed_ms" in cim_evt.labels

def test_inter_agent_interaction_recording(temp_gateway):
    gw, _, _ = temp_gateway
    itr = gw.record_interaction(
        sender_agent_id="agent_coordinator",
        receiver_agent_id="agent_analyst",
        interaction_type=InteractionType.DELEGATION,
        conversation_id="conv_test_99",
        task_id="task_sub_1",
        delegation_id="del_sub_1",
        semantic_summary="Analyze top 5 complaints.",
        raw_content="Perform statistical breakdown on top 5 complaints."
    )
    assert itr.interaction_id.startswith("itr_")
    assert itr.sender_agent_id == "agent_coordinator"
    assert itr.receiver_agent_id == "agent_analyst"
    assert itr.interaction_type == InteractionType.DELEGATION
