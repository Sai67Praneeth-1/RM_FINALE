"""
Agent B: Research Agent
Responsible for safe information collection from allowlisted files/datasets,
extracting relevant records, and transferring structured findings to peer agents.
"""

from typing import Dict, Any, List
from backend.agents.base import BaseAgent
from backend.schemas.events import InteractionType, SensitivityLabel
from backend.agents.llm_client import query_agent_llm, query_local_llm
from backend.config import settings

RESEARCHER_SYSTEM_PROMPT = """You are Agent B (Research Agent).
Your mandate is to inspect approved local datasets, extract relevant fields and rows,
and transfer structured findings to the Analysis Agent and Coordinator.
Never access unapproved paths or files outside the designated samples directory."""

class ResearchAgent(BaseAgent):
    def __init__(self, gateway=None, channel=None):
        super().__init__(
            agent_id="agent_researcher",
            name="Research Agent",
            role="Data Collection & Evidence Extraction",
            system_prompt=RESEARCHER_SYSTEM_PROMPT,
            gateway=gateway,
            channel=channel
        )

    def execute_research(
        self,
        dataset_name: str,
        delegation_id: str,
        principal_id: str,
        workflow_id: str,
        task_id: str,
        conversation_id: str,
        mode: str = "deterministic_demo"
    ) -> Dict[str, Any]:
        """
        Executes allowlisted file read via Gateway and transfers structured findings.
        Consumes delegation envelope as source of truth and acknowledges triggering message (Issue 1).
        """
        # Consume incoming delegation envelope from coordinator (Issue 1)
        inbox = self.read_inbox()
        triggering_msg_id = None
        for env in inbox:
            if env.get("sender") == "agent_coordinator":
                triggering_msg_id = env.get("message_id")
                payload = env.get("payload", {})
                if payload.get("dataset_name"):
                    dataset_name = payload["dataset_name"]
                break

        # Execute tool call via Gateway
        read_result, cim_event = self.tools.read_dataset(
            file_name=dataset_name,
            agent_id=self.agent_id,
            delegation_id=delegation_id,
            principal_id=principal_id,
            workflow_id=workflow_id,
            task_id=task_id
        )

        # Acknowledge triggering delegation message and record downstream consequence (Issue 1)
        if triggering_msg_id:
            self.acknowledge_message(triggering_msg_id, downstream_action_ids=[cim_event.event_id])

        extracted_data = read_result.get("data", [])
        row_count = read_result.get("row_count", len(extracted_data) if isinstance(extracted_data, list) else 1)

        # Formulate transfer message
        transfer_body = (
            f"Extracted {row_count} records from '{dataset_name}'. "
            f"Dataset format: {read_result.get('format')}. Ready for quantitative analysis."
        )
        summary = f"Transferred {row_count} extracted records from {dataset_name} to Analysis Agent."

        if mode in ["live_api", "live_gemini", "live_huggingface", "live_ollama"] and isinstance(extracted_data, list):
            sample_slice = str(extracted_data[:3])
            llm_summary = query_agent_llm(
                prompt=f"Summarize these initial sample records for an analyst: {sample_slice}",
                system_prompt=self.system_prompt,
                model_name=settings.GEMINI_MODEL or "gemini-3.5-flash-lite",
                mode=mode
            )
            if llm_summary:
                transfer_body += f"\nInitial Research Notes: {llm_summary}"

        # 1. Multi-hop transfer: Send findings to Analysis Agent with actual payload (Issue 1)
        msg_to_analyst = self.send_message(
            recipient="agent_analyst",
            interaction_type=InteractionType.INFORMATION_TRANSFER,
            delegation_id=delegation_id,
            conversation_id=conversation_id,
            task_id=task_id,
            workflow_id=workflow_id,
            body=transfer_body,
            payload={"extracted_data": extracted_data, "row_count": row_count, "format": read_result.get("format"), "dataset_name": dataset_name},
            summary=summary,
            resource_refs=[f"file://{dataset_name}"],
            sensitivity_label=SensitivityLabel.INTERNAL,
            reply_to_message_id=triggering_msg_id,
            downstream_action_ids=[],
            provenance_refs=[cim_event.event_id, f"file://{dataset_name}"]
        )

        # 2. Inform Coordinator of task completion
        msg_to_coord = self.send_message(
            recipient="agent_coordinator",
            interaction_type=InteractionType.RESULT,
            delegation_id=delegation_id,
            conversation_id=conversation_id,
            task_id=task_id,
            workflow_id=workflow_id,
            body=f"Data extraction for '{dataset_name}' completed ({row_count} items). Transferred to Analyst.",
            summary=f"Reported extraction success for {dataset_name} to Coordinator.",
            resource_refs=[f"file://{dataset_name}"],
            sensitivity_label=SensitivityLabel.INTERNAL,
            downstream_action_ids=[],
            provenance_refs=[cim_event.event_id]
        )

        # Record explicit provenance edges:
        # 1. Dataset -> Ingestion Tool Event (prov:used)
        self.gateway.record_provenance(
            workflow_id=workflow_id,
            source_id=f"file://{dataset_name}",
            source_type="resource",
            target_id=cim_event.event_id,
            target_type="tool_output",
            relation="used",
            confidence=1.0
        )
        # 2. Ingestion Tool Event -> Transferred Record Message (prov:wasDerivedFrom)
        self.gateway.record_provenance(
            workflow_id=workflow_id,
            source_id=cim_event.event_id,
            source_type="tool_output",
            target_id=msg_to_analyst.interaction_id,
            target_type="message",
            relation="wasDerivedFrom",
            confidence=1.0
        )

        return {
            "dataset_name": dataset_name,
            "read_result": read_result,
            "cim_event": cim_event,
            "message_to_analyst": msg_to_analyst,
            "message_to_coordinator": msg_to_coord
        }

