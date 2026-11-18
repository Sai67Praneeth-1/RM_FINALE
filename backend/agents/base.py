"""
Base Agent Interface with explicit Gateway-mediated communications and tool operations.
"""

from typing import Dict, Any, List, Optional
from backend.schemas.events import InteractionType, SensitivityLabel
from backend.gateway.gateway import ObservabilityGateway, default_gateway
from backend.gateway.interceptor import InstrumentedChannel, AgentMessageEnvelope, default_channel
from backend.gateway.tool_wrapper import InstrumentedToolClient

class BaseAgent:
    def __init__(
        self,
        agent_id: str,
        name: str,
        role: str,
        system_prompt: str,
        gateway: Optional[ObservabilityGateway] = None,
        channel: Optional[InstrumentedChannel] = None
    ):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.gateway = gateway or default_gateway
        self.channel = channel or (default_channel if (gateway is None or gateway is default_gateway) else InstrumentedChannel(self.gateway))
        self.tools = InstrumentedToolClient(self.gateway)

    def send_message(
        self,
        recipient: str,
        interaction_type: InteractionType,
        delegation_id: str,
        conversation_id: str,
        task_id: str,
        body: str,
        summary: Optional[str] = None,
        resource_refs: Optional[List[str]] = None,
        sensitivity_label: SensitivityLabel = SensitivityLabel.INTERNAL,
        reply_to_message_id: Optional[str] = None,
        provenance_refs: Optional[List[str]] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        retry_count: int = 0,
        downstream_action_ids: Optional[List[str]] = None,
        workflow_id: Optional[str] = None
    ):
        """Sends an instrumented message to another agent through the Gateway."""
        envelope = AgentMessageEnvelope(
            sender=self.agent_id,
            recipient=recipient,
            interaction_type=interaction_type,
            delegation_id=delegation_id,
            conversation_id=conversation_id,
            task_id=task_id,
            body=body,
            summary=summary,
            resource_refs=resource_refs,
            sensitivity_label=sensitivity_label,
            reply_to_message_id=reply_to_message_id,
            provenance_refs=provenance_refs,
            workflow_id=workflow_id
        )
        return self.channel.send_message(
            envelope=envelope,
            trace_id=trace_id,
            span_id=span_id,
            retry_count=retry_count,
            downstream_action_ids=downstream_action_ids
        )

    def read_inbox(self) -> List[Dict[str, Any]]:
        """Reads and clears incoming messages delivered through the channel."""
        return self.channel.get_inbox(self.agent_id)

    def peek_inbox(self) -> List[Dict[str, Any]]:
        """Inspects incoming messages without clearing."""
        return self.channel.peek_inbox(self.agent_id)

    def acknowledge_message(self, message_id: str) -> bool:
        """Acknowledges a received message envelope."""
        return self.channel.acknowledge_message(self.agent_id, message_id)

