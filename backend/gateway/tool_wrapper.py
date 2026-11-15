"""
Instrumented Tool Wrappers with CIM Semantic Normalization.
Enforces that every agent tool invocation is intercepted, normalized,
and attributed to an active delegation context.
"""

from typing import Dict, Any, Tuple
from backend.schemas.events import (
    ActionSemantic, ResourceClass, SensitivityLabel, Direction, PrincipalScope, CIMEvent
)
from backend.gateway.gateway import ObservabilityGateway, default_gateway
from backend.tools.file_tools import read_sample_dataset, list_sample_datasets
from backend.tools.analysis_tools import analyze_sentiment_and_severity, audit_security_access, analyze_text_content
from backend.tools.report_tools import format_markdown_report

class InstrumentedToolClient:
    """Provides audited tool execution APIs to agents."""
    def __init__(self, gateway: Optional[ObservabilityGateway] = None):
        self.gateway = gateway or default_gateway

    def read_dataset(
        self,
        file_name: str,
        agent_id: str,
        delegation_id: str,
        principal_id: str,
        workflow_id: str,
        task_id: str,
        trace_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], CIMEvent]:
        """Reads dataset with normalized ActionSemantic.READ."""
        return self.gateway.execute_tool_call(
            tool_fn=read_sample_dataset,
            tool_name="file_system",
            tool_operation="read_sample_dataset",
            action_semantic=ActionSemantic.READ,
            resource_type=ResourceClass.DATASET,
            resource_id=file_name,
            agent_id=agent_id,
            delegation_id=delegation_id,
            principal_id=principal_id,
            workflow_id=workflow_id,
            task_id=task_id,
            parameters={"file_name": file_name},
            direction=Direction.INTERNAL,
            principal_scope=PrincipalScope.ORG,
            sensitivity_label=SensitivityLabel.INTERNAL,
            trace_id=trace_id
        )

    def compute_analysis(
        self,
        records: list,
        agent_id: str,
        delegation_id: str,
        principal_id: str,
        workflow_id: str,
        task_id: str,
        trace_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], CIMEvent]:
        """Computes statistical metrics with normalized ActionSemantic.INVOKE."""
        return self.gateway.execute_tool_call(
            tool_fn=analyze_sentiment_and_severity,
            tool_name="analytics_engine",
            tool_operation="analyze_sentiment_and_severity",
            action_semantic=ActionSemantic.INVOKE,
            resource_type=ResourceClass.DATASET,
            resource_id="complaint_metrics",
            agent_id=agent_id,
            delegation_id=delegation_id,
            principal_id=principal_id,
            workflow_id=workflow_id,
            task_id=task_id,
            parameters={"records": records},
            direction=Direction.INTERNAL,
            principal_scope=PrincipalScope.ORG,
            sensitivity_label=SensitivityLabel.INTERNAL,
            trace_id=trace_id
        )

    def audit_security(
        self,
        access_logs: list,
        agent_id: str,
        delegation_id: str,
        principal_id: str,
        workflow_id: str,
        task_id: str,
        trace_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], CIMEvent]:
        """Audits access logs with normalized ActionSemantic.SEARCH."""
        return self.gateway.execute_tool_call(
            tool_fn=audit_security_access,
            tool_name="security_auditor",
            tool_operation="audit_security_access",
            action_semantic=ActionSemantic.SEARCH,
            resource_type=ResourceClass.DOCUMENT,
            resource_id="system_access_audit",
            agent_id=agent_id,
            delegation_id=delegation_id,
            principal_id=principal_id,
            workflow_id=workflow_id,
            task_id=task_id,
            parameters={"access_logs": access_logs},
            direction=Direction.INTERNAL,
            principal_scope=PrincipalScope.ORG,
            sensitivity_label=SensitivityLabel.CONFIDENTIAL,
            trace_id=trace_id
        )

    def analyze_text(
        self,
        content: Any,
        agent_id: str,
        delegation_id: str,
        principal_id: str,
        workflow_id: str,
        task_id: str,
        trace_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], CIMEvent]:
        """Analyzes unstructured research notes or text content with normalized ActionSemantic.READ."""
        return self.gateway.execute_tool_call(
            tool_fn=analyze_text_content,
            tool_name="content_analyzer",
            tool_operation="analyze_text_content",
            action_semantic=ActionSemantic.READ,
            resource_type=ResourceClass.DOCUMENT,
            resource_id="text_analysis",
            agent_id=agent_id,
            delegation_id=delegation_id,
            principal_id=principal_id,
            workflow_id=workflow_id,
            task_id=task_id,
            parameters={"content": str(content)[:200]},
            direction=Direction.INTERNAL,
            principal_scope=PrincipalScope.ORG,
            sensitivity_label=SensitivityLabel.INTERNAL,
            trace_id=trace_id
        )

    def synthesize_report(
        self,
        title: str,
        executive_summary: str,
        key_findings: list,
        statistical_breakdown: dict,
        recommendations: list,
        source_references: list,
        agent_id: str,
        delegation_id: str,
        principal_id: str,
        workflow_id: str,
        task_id: str,
        trace_id: Optional[str] = None
    ) -> Tuple[str, CIMEvent]:
        """Synthesizes markdown report with normalized ActionSemantic.WRITE."""
        params = {
            "title": title,
            "executive_summary": executive_summary,
            "key_findings": key_findings,
            "statistical_breakdown": statistical_breakdown,
            "recommendations": recommendations,
            "source_references": source_references,
            "delegation_context": {
                "delegation_id": delegation_id,
                "principal_id": principal_id,
                "workflow_id": workflow_id
            }
        }
        return self.gateway.execute_tool_call(
            tool_fn=format_markdown_report,
            tool_name="report_generator",
            tool_operation="format_markdown_report",
            action_semantic=ActionSemantic.WRITE,
            resource_type=ResourceClass.ARTIFACT,
            resource_id="final_report.md",
            agent_id=agent_id,
            delegation_id=delegation_id,
            principal_id=principal_id,
            workflow_id=workflow_id,
            task_id=task_id,
            parameters=params,
            direction=Direction.INTERNAL,
            principal_scope=PrincipalScope.ORG,
            sensitivity_label=SensitivityLabel.INTERNAL,
            trace_id=trace_id
        )

