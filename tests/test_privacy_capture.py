"""
Unit tests for Privacy-Aware Capture and Redaction.
Verifies Level 1, Level 2, and Level 3 persistence behavior,
PII redaction, and confirms private chain-of-thought is never stored.
"""

import pytest
import os
import tempfile
from backend.gateway.privacy import redact_sensitive_content, apply_capture_policy
from backend.schemas.events import CaptureLevel, InteractionType
from backend.gateway.gateway import ObservabilityGateway
from backend.storage.event_store import EventStore

def test_redact_sensitive_content():
    raw_text = "Contact admin at john.doe@enterprise.com or call 555-123-4567. SSN: 123-45-6789. Card: 4111-2222-3333-4444."
    redacted = redact_sensitive_content(raw_text)
    
    assert "john.doe@enterprise.com" not in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "555-123-4567" not in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "123-45-6789" not in redacted
    assert "[REDACTED_SSN]" in redacted
    assert "4111-2222-3333-4444" not in redacted
    assert "[REDACTED_CREDIT_CARD]" in redacted

def test_capture_level_1_metadata_only():
    raw_content = "Confidential customer statement with raw text."
    summary, content = apply_capture_policy(
        capture_level=CaptureLevel.METADATA_ONLY,
        raw_content=raw_content,
        provided_summary="Customer summary"
    )
    # Level 1 MUST NOT store raw content or summary
    assert summary is None
    assert content is None

def test_capture_level_2_metadata_and_summary():
    raw_content = "Raw detailed message with account details."
    summary, content = apply_capture_policy(
        capture_level=CaptureLevel.METADATA_SUMMARY,
        raw_content=raw_content,
        provided_summary="Summary of account details"
    )
    # Level 2 stores summary, but NO raw message body
    assert summary == "Summary of account details"
    assert content is None

def test_capture_level_3_full_content_redacted():
    raw_content = "Please email test@example.com for authorization."
    summary, content = apply_capture_policy(
        capture_level=CaptureLevel.FULL_CONTENT,
        raw_content=raw_content,
        provided_summary="Email request"
    )
    # Level 3 stores both summary and redacted raw content
    assert summary == "Email request"
    assert content is not None
    assert "test@example.com" not in content
    assert "[REDACTED_EMAIL]" in content

def test_gateway_enforces_capture_level_in_storage():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = EventStore(db_path=path)
    try:
        gw = ObservabilityGateway(event_store=store, capture_level=CaptureLevel.METADATA_ONLY)
        
        # Record interaction in Level 1 mode
        itr = gw.record_interaction(
            sender_agent_id="agent_a",
            receiver_agent_id="agent_b",
            interaction_type=InteractionType.REQUEST,
            conversation_id="conv_1",
            task_id="task_1",
            delegation_id="del_1",
            raw_content="Secret secret secret message"
        )
        
        stored = store.get_interaction(itr.interaction_id)
        assert stored.content is None
        assert stored.semantic_summary is None
    finally:
        store.close()
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

def test_strip_chain_of_thought_invariant():
    from backend.gateway.privacy import strip_chain_of_thought
    raw_with_cot = "<think>Internal deliberation about user intent and agent weights.</think>Final executive recommendation."
    cleaned = strip_chain_of_thought(raw_with_cot)
    assert "<think>" not in cleaned
    assert "Internal deliberation" not in cleaned
    assert cleaned == "Final executive recommendation."

def test_tool_parameter_sanitization():
    from backend.gateway.privacy import sanitize_parameters
    raw_params = {
        "user_email": "admin@company.com",
        "api_key": "api_key: abc123def456xyz789",
        "row_limit": 50
    }
    # Level 1 masks values
    sanitized_l1 = sanitize_parameters(raw_params, CaptureLevel.METADATA_ONLY)
    assert sanitized_l1["user_email"] == "[MASKED_METADATA_ONLY]"
    
    # Level 3 redacts secrets
    sanitized_l3 = sanitize_parameters(raw_params, CaptureLevel.FULL_CONTENT)
    assert "admin@company.com" not in sanitized_l3["user_email"]
    assert "[REDACTED_EMAIL]" in sanitized_l3["user_email"]
