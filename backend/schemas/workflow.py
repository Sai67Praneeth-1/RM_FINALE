"""
Workflow, Delegation, Task, Artifact, and Provenance data models.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field

from backend.schemas.events import SensitivityLabel, CaptureLevel


class WorkflowMode(str, Enum):
    LIVE_OLLAMA = "live_ollama"
    DETERMINISTIC_DEMO = "deterministic_demo"


class DelegationStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    REVOKED = "revoked"
    FAILED = "failed"


class DelegationRecord(BaseModel):
    """
    Authority context record.
    Represents nodes in the Authority / Lineage Graph (G_auth).
    """
    delegation_id: str = Field(default_factory=lambda: f"del_{uuid.uuid4().hex[:12]}")
    delegation_parent_id: Optional[str] = Field(None, description="Parent delegation for lineage DAG")
    principal_id: str = Field(..., description="Principal who granted this authority")
    agent_id: str = Field(..., description="Agent receiving the authority")
    task_id: str = Field(..., description="Root task or subtask identifier")
    scope: str = Field(default="standard_execution", description="Permitted execution scope")
    status: DelegationStatus = Field(default=DelegationStatus.ACTIVE)
    issued_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = Field(None)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskRecord(BaseModel):
    """Specific task or subtask assigned within a workflow."""
    task_id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:10]}")
    workflow_id: str
    parent_task_id: Optional[str] = None
    title: str
    description: str
    assigned_agent_id: str
    status: str = Field(default="pending")  # pending, in_progress, completed, failed
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    result_summary: Optional[str] = None


class ArtifactRecord(BaseModel):
    """Generated report, dataset, or intermediate artifact."""
    artifact_id: str = Field(default_factory=lambda: f"art_{uuid.uuid4().hex[:10]}")
    workflow_id: str
    title: str
    artifact_type: str = Field(default="report")  # report, findings, chart, summary
    format: str = Field(default="markdown")
    content: Optional[str] = None
    summary: Optional[str] = None
    created_by_agent_id: str
    delegation_id: str
    sensitivity_label: SensitivityLabel = Field(default=SensitivityLabel.INTERNAL)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_resource_refs: List[str] = Field(default_factory=list)


class ProvenanceEdge(BaseModel):
    """
    Explicit provenance link connecting sources, interactions, actions, and outputs.
    Follows W3C PROV concepts (used, wasGeneratedBy, wasDerivedFrom, informedBy).
    """
    edge_id: str = Field(default_factory=lambda: f"prv_{uuid.uuid4().hex[:12]}")
    workflow_id: str
    source_id: str = Field(..., description="Origin node (e.g., resource, tool_event, interaction)")
    source_type: str = Field(..., description="resource | message | tool_output | finding")
    target_id: str = Field(..., description="Derived node (e.g., finding, artifact, report)")
    target_type: str = Field(..., description="finding | report_section | artifact | interaction")
    relation: str = Field(default="wasDerivedFrom", description="used | wasGeneratedBy | wasDerivedFrom | informedBy")
    confidence: float = Field(default=1.0, description="1.0 for explicitly instrumented relationships")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowRun(BaseModel):
    """A complete workflow execution run."""
    workflow_id: str = Field(default_factory=lambda: f"wf_{uuid.uuid4().hex[:12]}")
    name: str = Field(default="Multi-Agent Analysis Workflow")
    task_description: str
    dataset_name: Optional[str] = None
    mode: WorkflowMode = Field(default=WorkflowMode.DETERMINISTIC_DEMO)
    capture_level: CaptureLevel = Field(default=CaptureLevel.METADATA_SUMMARY)
    status: str = Field(default="running")  # running, completed, failed
    start_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time: Optional[str] = None
    root_delegation_id: Optional[str] = None
    final_output: Optional[str] = None
    error_message: Optional[str] = None
    stats: Dict[str, Any] = Field(default_factory=dict)

