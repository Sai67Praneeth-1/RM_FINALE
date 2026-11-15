"""
Inter-Agent Interaction schema for our Proposed Research Extension.
Represents observable, structured agent-to-agent communication records.
Based on PPT Slides 10, 11, 12, 14.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field

from backend.schemas.events import InteractionType, SensitivityLabel, CaptureLevel


class InteractionRecord(BaseModel):
    """
    Structured inter-agent communication record.
    Forms the foundation for the persistent Interaction Graph.
    """
    interaction_id: str = Field(default_factory=lambda: f"itr_{uuid.uuid4().hex[:12]}")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # Communicating Agents
    sender_agent_id: str = Field(..., description="Verified sender agent identifier")
    receiver_agent_id: str = Field(..., description="Verified recipient agent identifier")
    interaction_type: InteractionType = Field(..., description="Semantic classification of the message")
    
    # Context Identifiers
    conversation_id: str = Field(..., description="Conversation or workflow session context")
    task_id: str = Field(..., description="Scoped task or subtask identifier")
    delegation_id: str = Field(..., description="Durable delegation authorization context")
    delegation_parent_id: Optional[str] = Field(None, description="Parent delegation ID for lineage closure")
    
    # Causal Execution Links
    trace_id: Optional[str] = Field(None, description="Execution trace identifier")
    span_id: Optional[str] = Field(None, description="Execution span identifier")
    
    # Message Envelope Identifiers
    message_id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    reply_to_message_id: Optional[str] = Field(None, description="Explicit reference to previous message")
    
    # Payload Representation according to Privacy-Aware Capture Level
    semantic_summary: Optional[str] = Field(
        None,
        description="Concise semantic summary (Level 2 & 3). None in Level 1."
    )
    content: Optional[str] = Field(
        None,
        description="Observable message content (persisted only in Level 3 with redaction). None in Level 1 & 2."
    )
    
    # Resources and Sensitivity
    resource_refs: List[str] = Field(
        default_factory=list,
        description="Identifiers or URIs of resources referenced or transferred"
    )
    sensitivity_label: SensitivityLabel = Field(
        default=SensitivityLabel.INTERNAL,
        description="Highest sensitivity classification of the exchanged data"
    )
    
    # Status and Consequence
    status: str = Field(default="delivered", description="Delivery status: sent, delivered, failed, retried")
    retry_count: int = Field(default=0, description="Retry attempt count if applicable")
    downstream_action_ids: List[str] = Field(
        default_factory=list,
        description="Explicit downstream tool invocations or execution events triggered by this interaction"
    )
    provenance_refs: List[str] = Field(
        default_factory=list,
        description="Explicit provenance links (data sources, findings, or artifacts)"
    )
    
    # Capture Metadata
    capture_level: CaptureLevel = Field(
        default=CaptureLevel.METADATA_SUMMARY,
        description="Capture level active when this record was persisted"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

