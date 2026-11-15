"""
Agent-to-Agent Communication Channel and Interceptor.
Guarantees all semantic inter-agent messages pass through the
Observability Gateway and are recorded persistently.
"""

from typing import Dict, Any, List, Optional
from backend.schemas.events import InteractionType, SensitivityLabel
from backend.schemas.interaction import InteractionRecord
from backend.gateway.gateway import ObservabilityGateway, default_gateway

class AgentMessageEnvelope:
    """Standardized envelope for inter-agent communication."""
    def __init__(
        self,
        sender: str,
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
        provenance_refs: Optional[List[str]] = None
    ):
        self.sender = sender
        self.recipient = recipient
        self.interaction_type = interaction_type
        self.delegation_id = delegation_id
        self.conversation_id = conversation_id
        self.task_id = task_id
        self.body = body
        self.summary = summary
        self.resource_refs = resource_refs or []
        self.sensitivity_label = sensitivity_label
        self.reply_to_message_id = reply_to_message_id
        self.provenance_refs = provenance_refs or []

class InstrumentedChannel:
    """
    Instrumented communication transport.
    Intercepts messages between sender and receiver and logs them via the gateway.
    """
    def __init__(self, gateway: Optional[ObservabilityGateway] = None):
        self.gateway = gateway or default_gateway
        self._mailboxes: Dict[str, List[Dict[str, Any]]] = {}

    def send_message(
        self,
        envelope: AgentMessageEnvelope,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        retry_count: int = 0,
        downstream_action_ids: Optional[List[str]] = None
    ) -> InteractionRecord:
        """
        Sends a message through the observability gateway.
        Records telemetry and places payload in recipient mailbox.
        """
        # Intercept and persist via Gateway
        record = self.gateway.record_interaction(
            sender_agent_id=envelope.sender,
            receiver_agent_id=envelope.recipient,
            interaction_type=envelope.interaction_type,
            conversation_id=envelope.conversation_id,
            task_id=envelope.task_id,
            delegation_id=envelope.delegation_id,
            semantic_summary=envelope.summary,
            raw_content=envelope.body,
            resource_refs=envelope.resource_refs,
            sensitivity_label=envelope.sensitivity_label,
            reply_to_message_id=envelope.reply_to_message_id,
            retry_count=retry_count,
            downstream_action_ids=downstream_action_ids or [],
            provenance_refs=envelope.provenance_refs,
            trace_id=trace_id,
            span_id=span_id
        )

        # Deliver to local in-memory mailbox for downstream consumption
        if envelope.recipient not in self._mailboxes:
            self._mailboxes[envelope.recipient] = []
        
        self._mailboxes[envelope.recipient].append({
            "message_id": record.message_id,
            "interaction_id": record.interaction_id,
            "sender": envelope.sender,
            "type": envelope.interaction_type.value,
            "body": envelope.body,
            "summary": envelope.summary,
            "resource_refs": envelope.resource_refs,
            "timestamp": record.timestamp,
            "delegation_id": envelope.delegation_id
        })

        return record

    def get_inbox(self, agent_id: str) -> List[Dict[str, Any]]:
        """Retrieves and clears incoming messages for an agent."""
        inbox = self._mailboxes.get(agent_id, [])
        self._mailboxes[agent_id] = []
        return inbox

