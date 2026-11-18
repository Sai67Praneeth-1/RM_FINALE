"""
Event schemas and models for the Common Information Model (CIM) and Observability Gateway.
Standardized Autonomous Agent Observability Event Schema.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field


class ActionSemantic(str, Enum):
    """Tier-1 normalized action taxonomy from CIM Table 8 & Appendix B.2."""
    READ = "read"
    WRITE = "write"
    SEARCH = "search"
    SHARE = "share"
    INVOKE = "invoke"
    DELEGATE = "delegate"
    SPAWN = "spawn"
    ENUMERATE = "enumerate"
    REVOKE = "revoke"


class ActionOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    UNKNOWN = "unknown"


class Direction(str, Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class PrincipalScope(str, Enum):
    SELF = "self"
    ORG = "org"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class ResourceClass(str, Enum):
    DOCUMENT = "document"
    DATASET = "dataset"
    MESSAGE = "message"
    TICKET = "ticket"
    REPO = "repo"
    CHANNEL = "channel"
    ARTIFACT = "artifact"
    ACCOUNT = "account"
    UNKNOWN = "unknown"


class SensitivityLabel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


class InteractionType(str, Enum):
    """Supported interaction types from PPT Slide 12."""
    REQUEST = "request"
    RESPONSE = "response"
    DELEGATION = "delegation"
    RESULT = "result"
    INFORMATION_TRANSFER = "information_transfer"
    ESCALATION = "escalation"
    HANDOFF = "handoff"
    CLARIFICATION = "clarification"
    WARNING = "warning"


class CaptureLevel(int, Enum):
    """Three privacy-aware capture tiers from PPT Slide 12."""
    METADATA_ONLY = 1
    METADATA_SUMMARY = 2
    METADATA_AND_SUMMARY = 2  # Alias for backward/forward compatibility
    FULL_CONTENT = 3


class CIMEvent(BaseModel):
    """
    Standard Common Information Model (CIM) event record.
    Preserves authority-flow and control-flow independently.
    """
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    delegation_id: str = Field(..., description="Durable authorization context identifier")
    delegation_parent_id: Optional[str] = Field(None, description="Parent delegation ID for lineage closure")
    
    # Principal & Agent Identities
    principal_user_id: str = Field(default="user_default", description="Human/root principal who originated authority")
    agent_id: str = Field(..., description="Logical agent identity (e.g., coordinator, researcher)")
    agent_instance_id: Optional[str] = Field(None, description="Concrete runtime session or process instance")
    
    # Tool and Normalized Action Semantics
    tool_name: str = Field(..., description="Tool family name (e.g., file_reader, sentiment_calc)")
    tool_operation: Optional[str] = Field(None, description="Tool native operation name")
    action_semantic: ActionSemantic = Field(..., description="Tier-1 normalized action semantic")
    action_outcome: ActionOutcome = Field(default=ActionOutcome.SUCCESS)
    
    # Tier-2 Qualifiers
    direction: Direction = Field(default=Direction.INTERNAL)
    principal_scope: PrincipalScope = Field(default=PrincipalScope.ORG)
    
    # Resource Attribution
    resource_type: ResourceClass = Field(default=ResourceClass.UNKNOWN)
    resource_id: Optional[str] = Field(None, description="Tool-scoped identifier")
    resource_uri: Optional[str] = Field(None, description="Canonical URI/locator")
    sensitivity_label: SensitivityLabel = Field(default=SensitivityLabel.INTERNAL)
    target_principal_id: Optional[str] = Field(None)
    
    # Execution & Trace Context
    trace_id: Optional[str] = Field(None, description="Distributed execution trace ID")
    span_id: Optional[str] = Field(None, description="Current execution span ID")
    parent_span_id: Optional[str] = Field(None, description="Causal parent span ID")
    workflow_id: Optional[str] = Field(None, description="Workflow run ID")
    task_id: Optional[str] = Field(None, description="Current task identifier")
    
    # Optional parameters or metadata
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    output_summary: Optional[str] = Field(None)
    labels: Dict[str, str] = Field(default_factory=dict)

