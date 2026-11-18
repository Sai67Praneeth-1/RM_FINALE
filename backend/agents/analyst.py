"""
Agent C: Analysis Agent
Responsible for performing quantitative calculations, statistical aggregation,
and security auditing through permitted tools, requesting clarification when necessary,
and delivering structured analytical findings.
"""

from typing import Dict, Any, List, Optional
from backend.agents.base import BaseAgent
from backend.schemas.events import InteractionType, SensitivityLabel
from backend.agents.llm_client import query_agent_llm, query_local_llm
from backend.config import settings

ANALYST_SYSTEM_PROMPT = """You are Agent C (Analysis Agent).
You receive extracted records from the Research Agent and execute statistical, sentiment,
or audit calculations using allowlisted tools.
Highlight key risk areas, enterprise account exposures, and actionable metrics."""

class AnalysisAgent(BaseAgent):
    def __init__(self, gateway=None, channel=None):
        super().__init__(
            agent_id="agent_analyst",
            name="Analysis Agent",
            role="Statistical & Quantitative Analytics",
            system_prompt=ANALYST_SYSTEM_PROMPT,
            gateway=gateway,
            channel=channel
        )

    def analyze_dataset(
        self,
        raw_records: Any,
        dataset_name: str,
        delegation_id: str,
        principal_id: str,
        workflow_id: str,
        task_id: str,
        conversation_id: str,
        upstream_interaction_id: Optional[str] = None,
        mode: str = "deterministic_demo"
    ) -> Dict[str, Any]:
        """
        Executes analytical computations through Gateway, consumes inbox messages,
        handles clarification if needed, and returns structured findings.
        """
        # Consume incoming messages delivered to analyst's inbox (Finding 1)
        inbox = self.read_inbox()
        if not upstream_interaction_id and inbox:
            upstream_interaction_id = inbox[-1].get("interaction_id")

        # Check domain: security logs vs. customer complaints vs. general text/notes
        is_security_audit = "access" in dataset_name.lower() or "log" in dataset_name.lower()
        is_text_content = isinstance(raw_records, str) or dataset_name.endswith(".txt") or not isinstance(raw_records, list)

        if is_security_audit:
            records = raw_records if isinstance(raw_records, list) else []
            analysis_output, cim_event = self.tools.audit_security(
                access_logs=records,
                agent_id=self.agent_id,
                delegation_id=delegation_id,
                principal_id=principal_id,
                workflow_id=workflow_id,
                task_id=task_id
            )
            key_takeaway = (
                f"Audited {analysis_output.get('total_access_events', 0)} access events. "
                f"Detected {analysis_output.get('violations_detected', 0)} unauthorized access attempts "
                f"and {analysis_output.get('sensitive_access_count', 0)} confidential touches."
            )
        elif is_text_content:
            analysis_output, cim_event = self.tools.analyze_text(
                content=raw_records,
                agent_id=self.agent_id,
                delegation_id=delegation_id,
                principal_id=principal_id,
                workflow_id=workflow_id,
                task_id=task_id
            )
            key_takeaway = (
                f"Analyzed research text ({analysis_output.get('total_words', 0)} words, {analysis_output.get('total_paragraphs', 0)} sections). "
                f"Identified core topics: {', '.join(analysis_output.get('topics_identified', []))}."
            )
        else:
            records = raw_records if isinstance(raw_records, list) else []
            analysis_output, cim_event = self.tools.compute_analysis(
                records=records,
                agent_id=self.agent_id,
                delegation_id=delegation_id,
                principal_id=principal_id,
                workflow_id=workflow_id,
                task_id=task_id
            )
            avg_sent = analysis_output.get("average_sentiment", 0.0)
            high_sev = analysis_output.get("high_priority_count", 0)
            key_takeaway = (
                f"Analyzed {analysis_output.get('total_tickets', 0)} tickets: "
                f"Average sentiment score = {avg_sent} ({analysis_output.get('sentiment_polarity', 'neutral')}). "
                f"{high_sev} tickets classified as High/Critical severity."
            )

        if mode in ["live_api", "live_gemini", "live_huggingface", "live_ollama"]:
            llm_insight = query_agent_llm(
                prompt=f"Provide an analytical takeaway for executive decision makers from these metrics: {analysis_output}",
                system_prompt=self.system_prompt,
                model_name=settings.HF_EXECUTOR_MODEL,
                mode=mode
            )
            if llm_insight:
                key_takeaway += f"\nAnalytical Insight: {llm_insight}"

        # Send result back to Coordinator
        if is_security_audit:
            summary = f"Security audit findings ({analysis_output.get('violations_detected', 0)} violations flagged)"
        elif is_text_content:
            summary = f"Text analysis findings ({len(analysis_output.get('topics_identified', []))} topics extracted)"
        else:
            summary = f"Quantitative analysis findings ({analysis_output.get('high_priority_count', 0)} critical issues)"
        # Send result back to Coordinator (Finding 6: cim_event is prior calculation provenance)
        prov_refs = [cim_event.event_id]
        if upstream_interaction_id:
            prov_refs.append(upstream_interaction_id)

        msg_to_coord = self.send_message(
            recipient="agent_coordinator",
            interaction_type=InteractionType.RESULT,
            delegation_id=delegation_id,
            conversation_id=conversation_id,
            task_id=task_id,
            workflow_id=workflow_id,
            body=key_takeaway,
            summary=summary,
            resource_refs=[f"file://{dataset_name}", "tool://analytics_engine"],
            sensitivity_label=SensitivityLabel.INTERNAL,
            downstream_action_ids=[],
            provenance_refs=prov_refs
        )

        # Record explicit provenance edge: Upstream message -> Analysis Calculation
        if upstream_interaction_id:
            self.gateway.record_provenance(
                workflow_id=workflow_id,
                source_id=upstream_interaction_id,
                source_type="message",
                target_id=cim_event.event_id,
                target_type="tool_output",
                relation="wasDerivedFrom",
                confidence=1.0
            )

        return {
            "analysis_output": analysis_output,
            "cim_event": cim_event,
            "key_takeaway": key_takeaway,
            "message_to_coordinator": msg_to_coord
        }

    def request_clarification(
        self,
        question: str,
        delegation_id: str,
        conversation_id: str,
        task_id: str
    ):
        """Sends an explicit clarification request to the Coordinator."""
        return self.send_message(
            recipient="agent_coordinator",
            interaction_type=InteractionType.CLARIFICATION,
            delegation_id=delegation_id,
            conversation_id=conversation_id,
            task_id=task_id,
            body=question,
            summary="Requested clarification from Coordinator on threshold criteria.",
            sensitivity_label=SensitivityLabel.INTERNAL
        )

    def escalate_issue(
        self,
        reason: str,
        delegation_id: str,
        conversation_id: str,
        task_id: str
    ):
        """Sends an escalation alert to Coordinator when critical risks or anomalies are detected."""
        return self.send_message(
            recipient="agent_coordinator",
            interaction_type=InteractionType.ESCALATION,
            delegation_id=delegation_id,
            conversation_id=conversation_id,
            task_id=task_id,
            body=f"ESCALATION ALERT: {reason}",
            summary=f"Escalated critical security/anomaly finding to Coordinator: {reason[:45]}...",
            sensitivity_label=SensitivityLabel.RESTRICTED
        )

