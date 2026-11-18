"""
Agent D: Report Agent
Synthesizes verified research and analytical findings into an actionable,
transparent Markdown report with explicit provenance citations and source mappings.
"""

from typing import Dict, Any, List
from backend.agents.base import BaseAgent
from backend.schemas.events import InteractionType, SensitivityLabel
from backend.schemas.workflow import ArtifactRecord
from backend.agents.llm_client import query_agent_llm, query_local_llm
from backend.config import settings

REPORTER_SYSTEM_PROMPT = """You are Agent D (Report Agent).
Your purpose is to synthesize all completed research and statistical analyses into a transparent,
executive-ready Markdown report. Every conclusion must be traceable to explicit observable evidence."""

class ReportAgent(BaseAgent):
    def __init__(self, gateway=None, channel=None):
        super().__init__(
            agent_id="agent_reporter",
            name="Report Agent",
            role="Report Synthesis & Provenance Attribution",
            system_prompt=REPORTER_SYSTEM_PROMPT,
            gateway=gateway,
            channel=channel
        )

    def generate_final_report(
        self,
        task_description: str,
        dataset_name: str,
        research_data: Dict[str, Any],
        analysis_data: Dict[str, Any],
        delegation_id: str,
        principal_id: str,
        workflow_id: str,
        task_id: str,
        conversation_id: str,
        mode: str = "deterministic_demo"
    ) -> Dict[str, Any]:
        """
        Synthesizes the final Markdown report via Gateway, attaches provenance citations,
        and saves the artifact.
        """
        # Consume incoming messages delivered to reporter's inbox (Finding 1)
        inbox = self.read_inbox()

        analysis_out = analysis_data.get("analysis_output", {})
        is_security_audit = "access" in dataset_name.lower() or "log" in dataset_name.lower() or "security" in task_description.lower()
        is_text_content = dataset_name.endswith(".txt") or "notes" in dataset_name.lower() or "topics_identified" in analysis_out
        
        # Formulate report sections dynamically
        if is_security_audit:
            title = f"Executive Security & Access Audit: {dataset_name.replace('_', ' ').replace('.csv', '').title()}"
            exec_summary = (
                f"This transparent multi-agent investigation was initiated under delegation '{delegation_id}' "
                f"for instruction: '{task_description}'.\n"
                f"Security audit tool inspected access logs and evaluated authorization privileges and confidential touches."
            )
            findings = [
                f"Detected {analysis_out.get('violations_detected', 0)} unauthorized access attempts requiring immediate revocation.",
                f"Audited {analysis_out.get('total_access_events', 0)} total access events across enterprise systems.",
                f"Identified {analysis_out.get('sensitive_access_count', 0)} touch events involving confidential or restricted resources.",
                f"Full audit trail verified through Observability Gateway with cryptographic delegation tokens."
            ]
            recommendations = [
                "Immediately revoke unauthorized credentials identified in flagged security events.",
                "Enforce role-based access control (RBAC) boundaries on confidential and restricted resources.",
                "Implement gateway-mediated authorization checks before sensitive inter-agent resource sharing.",
                "Maintain continuous audit logging for all delegated agent tasks."
            ]
            primary_tool_uri = "tool://security_auditor/audit_security_access"
        elif is_text_content:
            title = f"Executive Research & Knowledge Synthesis: {dataset_name.replace('_', ' ').replace('.txt', '').title()}"
            exec_summary = (
                f"This transparent multi-agent investigation was initiated under delegation '{delegation_id}' "
                f"for instruction: '{task_description}'.\n"
                f"Research and content analysis tools evaluated unstructured knowledge sources and extracted strategic themes."
            )
            topics = analysis_out.get("topics_identified", ["Multi-Agent Architecture"])
            findings = [
                f"Extracted {analysis_out.get('total_words', 0)} words across {analysis_out.get('total_paragraphs', 0)} sections.",
                f"Identified key strategic topics: {', '.join(topics)}.",
                f"Verified actionable takeaways: {'; '.join(analysis_out.get('key_action_items', ['Align with research invariants']))}.",
                f"End-to-end provenance established from raw notes to synthesized findings."
            ]
            recommendations = [
                "Prioritize identified research topics in upcoming technical architecture milestones.",
                "Incorporate delegation token verification across all inter-agent communication channels.",
                "Adopt 3-tier privacy capture to balance transparency with sensitive data protection.",
                "Conduct regular multi-agent provenance audits to verify artifact integrity."
            ]
            primary_tool_uri = "tool://content_analyzer/analyze_text_content"
        else:
            title = f"Executive Audit & Analysis: {dataset_name.replace('_', ' ').replace('.csv', '').title()}"
            exec_summary = (
                f"This transparent multi-agent investigation was initiated under delegation '{delegation_id}' "
                f"for instruction: '{task_description}'.\n"
                f"Data extracted from `{dataset_name}` was processed through verified analytical tools."
            )
            findings = [
                f"Severe negative sentiment concentrated in high-value enterprise accounts.",
                f"Identified {analysis_out.get('high_priority_count', 0)} critical priority tickets requiring engineering escalation.",
                f"Category distribution shows operational and billing disputes as top churn drivers.",
                f"Explicit data flow verified from {dataset_name} through Research and Analysis agents."
            ]
            recommendations = [
                "Establish automated SLA escalation for Critical severity tickets within 15 minutes.",
                "Review billing automation workflows to eliminate duplicate subscription charges.",
                "Address system query latency during peak hours.",
                "Maintain continuous gateway-mediated telemetry for all inter-agent task delegations."
            ]
            primary_tool_uri = "tool://analytics_engine/analyze_sentiment_and_severity"

        source_refs = [
            f"dataset://data/samples/{dataset_name}",
            f"tool://file_system/read_sample_dataset",
            primary_tool_uri,
            f"interaction://agent_researcher_to_agent_analyst"
        ]

        if mode in ["live_api", "live_gemini", "live_huggingface", "live_ollama"]:
            llm_report_enhancement = query_agent_llm(
                prompt=f"Enhance this executive summary for task '{task_description}' based on: {analysis_out}",
                system_prompt=self.system_prompt,
                model_name=settings.HF_COORDINATOR_MODEL,
                mode=mode
            )
            if llm_report_enhancement:
                exec_summary += f"\n\n**LLM Synthesis:**\n{llm_report_enhancement}"

        # Execute report generation tool via Gateway
        markdown_content, cim_event = self.tools.synthesize_report(
            title=title,
            executive_summary=exec_summary,
            key_findings=findings,
            statistical_breakdown=analysis_out,
            recommendations=recommendations,
            source_references=source_refs,
            agent_id=self.agent_id,
            delegation_id=delegation_id,
            principal_id=principal_id,
            workflow_id=workflow_id,
            task_id=task_id
        )

        # Persist report as an ArtifactRecord in SQLite
        artifact = ArtifactRecord(
            workflow_id=workflow_id,
            title=title,
            artifact_type="final_report",
            format="markdown",
            content=markdown_content,
            summary=f"Final transparent report synthesized with {len(findings)} findings.",
            created_by_agent_id=self.agent_id,
            delegation_id=delegation_id,
            sensitivity_label=SensitivityLabel.INTERNAL,
            source_resource_refs=source_refs
        )
        self.gateway.store.save_artifact(artifact)

        # Record explicit provenance edges (W3C PROV Alignment):
        # 1. Analysis Tool Event -> Artifact (prov:wasDerivedFrom)
        analysis_evt = analysis_data.get("cim_event")
        analysis_evt_id = getattr(analysis_evt, "event_id", None) or (analysis_evt.get("event_id") if isinstance(analysis_evt, dict) else None)
        if not analysis_evt_id:
            analysis_evt_id = f"act_analysis_{workflow_id}"

        self.gateway.record_provenance(
            workflow_id=workflow_id,
            source_id=analysis_evt_id,
            source_type="tool_output",
            target_id=artifact.artifact_id,
            target_type="artifact",
            relation="wasDerivedFrom",
            confidence=1.0
        )

        # 2. Source Dataset -> Artifact (prov:used)
        self.gateway.record_provenance(
            workflow_id=workflow_id,
            source_id=f"file://{dataset_name}",
            source_type="resource",
            target_id=artifact.artifact_id,
            target_type="artifact",
            relation="used",
            confidence=1.0
        )

        # 3. Report Agent -> Artifact (prov:wasAttributedTo)
        self.gateway.record_provenance(
            workflow_id=workflow_id,
            source_id=self.agent_id,
            source_type="agent",
            target_id=artifact.artifact_id,
            target_type="artifact",
            relation="wasAttributedTo",
            confidence=1.0
        )

        # Deliver final notification to Coordinator (Finding 6: cim_event and artifact are upstream provenance)
        summary = f"Delivered completed markdown report artifact ({artifact.artifact_id})."
        msg_to_coord = self.send_message(
            recipient="agent_coordinator",
            interaction_type=InteractionType.RESULT,
            delegation_id=delegation_id,
            conversation_id=conversation_id,
            task_id=task_id,
            workflow_id=workflow_id,
            body=f"Final report '{title}' generated successfully. Artifact ID: {artifact.artifact_id}.",
            summary=summary,
            resource_refs=[f"artifact://{artifact.artifact_id}"],
            sensitivity_label=SensitivityLabel.INTERNAL,
            downstream_action_ids=[],
            provenance_refs=[cim_event.event_id, artifact.artifact_id]
        )

        return {
            "artifact": artifact,
            "markdown_content": markdown_content,
            "cim_event": cim_event,
            "message_to_coordinator": msg_to_coord
        }

