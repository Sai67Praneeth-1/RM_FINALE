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
    """Standardized envelope for inter-agent communication carrying actual task payloads (Issue 1)."""
    def __init__(
        self,
        sender: str,
        recipient: str,
        interaction_type: InteractionType,
        delegation_id: str,
        conversation_id: str,
        task_id: str,
        body: str,
        payload: Optional[Dict[str, Any]] = None,
        summary: Optional[str] = None,
        resource_refs: Optional[List[str]] = None,
        sensitivity_label: SensitivityLabel = SensitivityLabel.INTERNAL,
        reply_to_message_id: Optional[str] = None,
        provenance_refs: Optional[List[str]] = None,
        workflow_id: Optional[str] = None
    ):
        self.sender = sender
        self.recipient = recipient
        self.interaction_type = interaction_type
        self.delegation_id = delegation_id
        self.conversation_id = conversation_id
        self.task_id = task_id
        self.body = body
        self.payload = payload or {}
        self.summary = summary
        self.resource_refs = resource_refs or []
        self.sensitivity_label = sensitivity_label
        self.reply_to_message_id = reply_to_message_id
        self.provenance_refs = provenance_refs or []
        self.workflow_id = workflow_id

class InstrumentedChannel:
    """
    Instrumented communication transport.
    Intercepts messages between sender and receiver and logs them via the gateway.
    Shares a shared in-memory mailbox hub across channel instances unless isolated=True.
    """
    _shared_mailboxes: Dict[str, List[Dict[str, Any]]] = {}

    def __init__(self, gateway: Optional[ObservabilityGateway] = None, isolated: bool = False):
        self.gateway = gateway or default_gateway
        self.isolated = isolated
        self._local_mailboxes: Dict[str, List[Dict[str, Any]]] = {}

    @property
    def _mailboxes(self) -> Dict[str, List[Dict[str, Any]]]:
        if self.isolated:
            return self._local_mailboxes
        return InstrumentedChannel._shared_mailboxes

    @classmethod
    def reset_shared_mailboxes(cls):
        """Clears all shared mailboxes across instances."""
        cls._shared_mailboxes.clear()

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
            span_id=span_id,
            workflow_id=envelope.workflow_id
        )

        # Deliver to in-memory mailbox for downstream consumption
        mailboxes = self._mailboxes
        if envelope.recipient not in mailboxes:
            mailboxes[envelope.recipient] = []
        
        mailboxes[envelope.recipient].append({
            "message_id": record.message_id,
            "interaction_id": record.interaction_id,
            "sender": envelope.sender,
            "recipient": envelope.recipient,
            "type": envelope.interaction_type.value if hasattr(envelope.interaction_type, "value") else str(envelope.interaction_type),
            "body": envelope.body,
            "payload": envelope.payload,
            "summary": record.semantic_summary or envelope.summary,
            "resource_refs": envelope.resource_refs,
            "timestamp": record.timestamp,
            "delegation_id": envelope.delegation_id,
            "conversation_id": envelope.conversation_id,
            "task_id": envelope.task_id,
            "workflow_id": envelope.workflow_id,
            "reply_to_message_id": envelope.reply_to_message_id,
            "acknowledged": False,
            "consumed": False
        })

        return record

    def get_inbox(self, agent_id: str, clear: bool = True) -> List[Dict[str, Any]]:
        """Retrieves and optionally clears incoming messages for an agent."""
        mailboxes = self._mailboxes
        inbox = list(mailboxes.get(agent_id, []))
        if clear:
            mailboxes[agent_id] = []
        return inbox

    def peek_inbox(self, agent_id: str) -> List[Dict[str, Any]]:
        """Retrieves incoming messages without clearing them."""
        return list(self._mailboxes.get(agent_id, []))

    def acknowledge_message(
        self,
        agent_id: str,
        message_id: str,
        downstream_action_ids: Optional[List[str]] = None
    ) -> bool:
        """
        Marks a message in agent's inbox as acknowledged and consumed,
        linking any downstream consequences to the triggering message (Issue 1).
        """
        mailboxes = self._mailboxes
        found = False
        for msg in mailboxes.get(agent_id, []):
            if msg.get("message_id") == message_id or msg.get("interaction_id") == message_id:
                msg["acknowledged"] = True
                msg["consumed"] = True
                if downstream_action_ids:
                    msg.setdefault("downstream_action_ids", []).extend(downstream_action_ids)
                found = True
                break
        
        # Persist acknowledgment and downstream consequences in SQLite
        try:
            self.gateway.store.update_interaction_acknowledgment(
                interaction_id=message_id,
                status="acknowledged",
                downstream_action_ids=downstream_action_ids
            )
        except Exception:
            pass
        return found

# Default singleton channel instance
default_channel = InstrumentedChannel(default_gateway)

