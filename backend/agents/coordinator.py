"""
Agent A: Coordinator
Orchestrates multi-agent execution, decomposes user requests, mints sub-delegations,
delegates tasks to specialized agents, handles clarification, and combines completed work.
"""

from typing import Dict, Any, List, Optional
from backend.agents.base import BaseAgent
from backend.schemas.events import InteractionType, SensitivityLabel
from backend.agents.llm_client import query_local_llm

COORDINATOR_SYSTEM_PROMPT = """You are Agent A (Coordinator) in an enterprise multi-agent analytics system.
Your responsibility is to oversee task decomposition, assign sub-delegations to the Research Agent and Analysis Agent,
clarify ambiguities, and synthesize intermediate results for final reporting by the Report Agent.
Always be explicit about task scope, dataset sources, and delegated authority."""

class CoordinatorAgent(BaseAgent):
    def __init__(self, gateway=None, channel=None):
        super().__init__(
            agent_id="agent_coordinator",
            name="Coordinator Agent",
            role="Task Orchestration & Authority Delegation",
            system_prompt=COORDINATOR_SYSTEM_PROMPT,
            gateway=gateway,
            channel=channel
        )

    def initiate_delegations(
        self,
        principal_id: str,
        workflow_id: str,
        task_description: str,
        dataset_name: str,
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        Mints root and child delegations and sends the initial assignment to the Research Agent.
        """
        # Mint root delegation from principal to coordinator
        root_del = self.gateway.mint_delegation(
            principal_id=principal_id,
            agent_id=self.agent_id,
            task_id=f"root_task_{workflow_id}",
            parent_delegation_id=None,
            scope="root_workflow_coordination",
            metadata={"workflow_id": workflow_id, "dataset": dataset_name}
        )

        # Mint child delegation for Research Agent
        research_del = self.gateway.mint_delegation(
            principal_id=principal_id,
            agent_id="agent_researcher",
            task_id=f"research_task_{workflow_id}",
            parent_delegation_id=root_del.delegation_id,
            scope="data_ingestion_and_extraction",
            metadata={"workflow_id": workflow_id, "dataset": dataset_name}
        )

        # Mint child delegation for Analysis Agent
        analysis_del = self.gateway.mint_delegation(
            principal_id=principal_id,
            agent_id="agent_analyst",
            task_id=f"analysis_task_{workflow_id}",
            parent_delegation_id=root_del.delegation_id,
            scope="quantitative_analysis_and_metrics",
            metadata={"workflow_id": workflow_id}
        )

        # Mint child delegation for Report Agent
        report_del = self.gateway.mint_delegation(
            principal_id=principal_id,
            agent_id="agent_reporter",
            task_id=f"report_task_{workflow_id}",
            parent_delegation_id=root_del.delegation_id,
            scope="markdown_report_generation",
            metadata={"workflow_id": workflow_id}
        )

        # Send initial delegation message to Research Agent
        instruction_body = (
            f"Please ingest and extract relevant records from dataset '{dataset_name}' "
            f"for task: '{task_description}'. Forward structured findings to Analysis Agent and me."
        )
        clean_task_brief = task_description[:35] + ("..." if len(task_description) > 35 else "")
        summary = f"Delegated extraction from {dataset_name} for '{clean_task_brief}'"

        msg_record = self.send_message(
            recipient="agent_researcher",
            interaction_type=InteractionType.DELEGATION,
            delegation_id=research_del.delegation_id,
            conversation_id=conversation_id,
            task_id=research_del.task_id,
            body=instruction_body,
            summary=summary,
            resource_refs=[f"file://{dataset_name}"],
            sensitivity_label=SensitivityLabel.INTERNAL
        )

        return {
            "root_delegation": root_del,
            "research_delegation": research_del,
            "analysis_delegation": analysis_del,
            "report_delegation": report_del,
            "initial_message": msg_record
        }

    def respond_to_clarification(
        self,
        clarification_msg: Dict[str, Any],
        delegation_id: str,
        conversation_id: str,
        task_id: str,
        mode: str = "deterministic_demo"
    ) -> Any:
        """Handles clarification requests from peers (e.g. Analysis Agent)."""
        question = clarification_msg.get("body", "")
        reply_to = clarification_msg.get("message_id")
        
        reply_body = (
            "Guidance: Focus primary analysis on High and Critical severity categories, "
            "and compute sentiment impact across Enterprise tier accounts."
        )
        
        if mode == "live_ollama":
            llm_reply = query_local_llm(
                prompt=f"The sub-agent asked: '{question}'. Provide concise clarification for our complaint analysis task.",
                system_prompt=self.system_prompt
            )
            if llm_reply:
                reply_body = llm_reply

        summary = "Provided clarification on severity threshold and account tier priority."
        return self.send_message(
            recipient=clarification_msg.get("sender", "agent_analyst"),
            interaction_type=InteractionType.RESPONSE,
            delegation_id=delegation_id,
            conversation_id=conversation_id,
            task_id=task_id,
            body=reply_body,
            summary=summary,
            reply_to_message_id=reply_to,
            sensitivity_label=SensitivityLabel.INTERNAL
        )

    def respond_to_escalation(
        self,
        escalation_msg: Dict[str, Any],
        delegation_id: str,
        conversation_id: str,
        task_id: str
    ) -> Any:
        """Acknowledges and handles escalation alerts from Analyst or Researcher."""
        reply_to = escalation_msg.get("message_id")
        reason = escalation_msg.get("body", "Critical anomaly flagged")
        return self.send_message(
            recipient=escalation_msg.get("sender", "agent_analyst"),
            interaction_type=InteractionType.RESPONSE,
            delegation_id=delegation_id,
            conversation_id=conversation_id,
            task_id=task_id,
            body=f"Escalation acknowledged: Authorized immediate forensic synthesis and priority flagging for: {reason[:80]}",
            summary="Acknowledged escalation alert and authorized priority executive synthesis.",
            reply_to_message_id=reply_to,
            sensitivity_label=SensitivityLabel.RESTRICTED
        )

    def handoff_to_reporter(
        self,
        delegation_id: str,
        conversation_id: str,
        task_id: str,
        findings_summary: str
    ) -> Any:
        """Formally hands off verified analytical findings to Report Agent for executive Markdown compilation."""
        return self.send_message(
            recipient="agent_reporter",
            interaction_type=InteractionType.HANDOFF,
            delegation_id=delegation_id,
            conversation_id=conversation_id,
            task_id=task_id,
            body=f"Verified findings handoff: {findings_summary}",
            summary="Handed off verified findings to Report Agent for final executive report synthesis.",
            sensitivity_label=SensitivityLabel.INTERNAL
        )

