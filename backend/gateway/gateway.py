"""
Central Observability Gateway.
Core research component acting as an authoritative mediation boundary
between agents, and between agents and external tools.
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable, Tuple
from backend.schemas.events import (
    CIMEvent, ActionSemantic, ActionOutcome, Direction,
    PrincipalScope, ResourceClass, SensitivityLabel,
    InteractionType, CaptureLevel
)
from backend.schemas.interaction import InteractionRecord
from backend.schemas.workflow import DelegationRecord, ProvenanceEdge, ArtifactRecord, TaskRecord
from backend.storage.event_store import EventStore
from backend.gateway.privacy import (
    apply_capture_policy,
    sanitize_parameters,
    redact_sensitive_content,
    sanitize_resource_refs,
    sanitize_metadata
)

class ObservabilityGateway:
    """
    Authoritative Observability Gateway enforcing CIM invariants,
    minting delegation credentials, and recording inter-agent communication.
    """
    def __init__(
        self,
        event_store: Optional[EventStore] = None,
        capture_level: CaptureLevel = CaptureLevel.METADATA_SUMMARY,
        strict_authority_enforcement: bool = False
    ):
        self.store = event_store or EventStore()
        self.capture_level = capture_level
        self.strict_authority_enforcement = strict_authority_enforcement
        self._delegation_registry: Dict[str, DelegationRecord] = {}

    def set_capture_level(self, level: CaptureLevel):
        """Dynamically reconfigures the capture tier."""
        self.capture_level = level

    # -------------------------------------------------------------
    # Delegation Authority Minting and Binding (Invariants I1, I3, I5)
    # -------------------------------------------------------------
    def mint_delegation(
        self,
        principal_id: str,
        agent_id: str,
        task_id: str,
        parent_delegation_id: Optional[str] = None,
        scope: str = "standard_execution",
        metadata: Optional[Dict[str, Any]] = None,
        strict: bool = False
    ) -> DelegationRecord:
        """
        Cryptographically or authoritatively mints a durable delegation identifier.
        Ensures authority context cannot be forged by untrusted agent runtime code.
        """
        del_id = f"del_{uuid.uuid4().hex[:12]}"
        meta = dict(metadata or {})
        
        # Verify parent delegation exists if specified (Lineage consistency & Finding 4)
        if parent_delegation_id:
            parent = self.store.get_delegation(parent_delegation_id)
            if not parent:
                if strict:
                    raise ValueError(f"Invalid delegation lineage: parent delegation '{parent_delegation_id}' does not exist.")
                meta["parent_unverified"] = True
                meta["authority_quarantined"] = True
            else:
                meta["parent_verified"] = True
                if parent.agent_id != principal_id and parent.principal_id != principal_id:
                    meta["principal_binding_warning"] = "sub_delegating_principal_differs_from_parent_delegate"
                
        rec = DelegationRecord(
            delegation_id=del_id,
            delegation_parent_id=parent_delegation_id,
            principal_id=principal_id,
            agent_id=agent_id,
            task_id=task_id,
            scope=scope,
            metadata=meta
        )
        self._delegation_registry[del_id] = rec
        self.store.save_delegation(rec)
        return rec

    def verify_delegation(self, delegation_id: str) -> Optional[DelegationRecord]:
        """Validates that a delegation ID was legitimately minted by the gateway."""
        if delegation_id in self._delegation_registry:
            return self._delegation_registry[delegation_id]
        rec = self.store.get_delegation(delegation_id)
        if rec:
            self._delegation_registry[delegation_id] = rec
        return rec

    def validate_authority(
        self,
        delegation_id: str,
        agent_id: str,
        task_id: Optional[str] = None,
        required_scope: Optional[str] = None
    ) -> Tuple[bool, str, Optional[DelegationRecord]]:
        """
        Validates delegation authority binding (Issue 2):
        1. Confirms delegation was minted by gateway and is active.
        2. Binds agent identity: agent executing operation must match delegation.agent_id or delegation.principal_id.
        3. Validates task scope: ensures operation does not exceed granted delegation scope.
        Returns (is_valid: bool, reason: str, delegation: Optional[DelegationRecord]).
        """
        if not delegation_id:
            return False, "Missing delegation ID: authority cannot be verified", None

        delegation = self.verify_delegation(delegation_id)
        if not delegation:
            return False, f"Unverified authority: delegation '{delegation_id}' not found in registry", None

        status_val = delegation.status.value if hasattr(delegation.status, "value") else str(delegation.status)
        if status_val.lower() in ("revoked", "failed"):
            return False, f"Authority inactive: delegation '{delegation_id}' has status '{status_val}'", delegation

        # Bind agent identity
        if agent_id and delegation.agent_id != agent_id and delegation.principal_id != agent_id:
            return False, f"Identity binding mismatch: agent '{agent_id}' is not authorized under delegation '{delegation_id}' (bound to '{delegation.agent_id}')", delegation

        # Bind task scope if specified
        if required_scope and delegation.scope and delegation.scope != "standard_execution":
            if required_scope != delegation.scope and required_scope not in delegation.scope:
                return False, f"Scope mismatch: operation requires '{required_scope}' but delegation granted '{delegation.scope}'", delegation

        return True, "Authority verified and bound successfully", delegation

    # -------------------------------------------------------------
    # Inter-Agent Interaction Capture (Pillar 3 - Our Extension)
    # -------------------------------------------------------------
    def record_interaction(
        self,
        sender_agent_id: str,
        receiver_agent_id: str,
        interaction_type: InteractionType,
        conversation_id: str,
        task_id: str,
        delegation_id: str,
        semantic_summary: Optional[str] = None,
        raw_content: Optional[str] = None,
        resource_refs: Optional[List[str]] = None,
        sensitivity_label: SensitivityLabel = SensitivityLabel.INTERNAL,
        reply_to_message_id: Optional[str] = None,
        status: str = "delivered",
        retry_count: int = 0,
        downstream_action_ids: Optional[List[str]] = None,
        provenance_refs: Optional[List[str]] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None,
        capture_level: Optional[CaptureLevel] = None
    ) -> InteractionRecord:
        """
        Intercepts and persists an inter-agent message with privacy-aware filtering and authority validation.
        """
        # Look up and verify delegation context & authority binding (Issue 2)
        is_auth, auth_reason, delegation = self.validate_authority(
            delegation_id=delegation_id,
            agent_id=sender_agent_id
        )
        parent_del_id = delegation.delegation_parent_id if delegation else None
        meta = dict(metadata or {})

        if is_auth:
            meta["delegation_verified"] = True
            meta["authority_status"] = "verified"
            if receiver_agent_id and delegation and delegation.agent_id not in (sender_agent_id, receiver_agent_id) and delegation.principal_id not in (sender_agent_id, receiver_agent_id):
                meta["authority_binding_mismatch"] = True
                meta["binding_warning"] = f"Receiver agent '{receiver_agent_id}' differs from delegation agent '{delegation.agent_id}'"
        else:
            meta["delegation_verified"] = False
            meta["authority_status"] = "isolated"
            meta["authority_quarantined"] = True
            meta["isolation_reason"] = auth_reason
            status = "isolated_quarantine"
            if self.strict_authority_enforcement:
                raise PermissionError(f"Gateway rejected unverified authority for interaction: {auth_reason}")

        # Immutable per-request capture tier support (Finding 5)
        effective_capture_level = capture_level if capture_level is not None else self.capture_level

        # Apply configured capture tier (Level 1, 2, or 3) with PII redaction
        summary, content = apply_capture_policy(
            capture_level=effective_capture_level,
            raw_content=raw_content,
            provided_summary=semantic_summary
        )

        # Sanitize resource_refs and metadata for privacy integrity (Finding 5)
        sanitized_refs = sanitize_resource_refs(resource_refs)
        sanitized_meta = sanitize_metadata(meta)

        # Resolve workflow_id if not directly passed (Finding 7)
        eff_workflow_id = workflow_id
        if not eff_workflow_id:
            if conversation_id and ("wf_" in conversation_id or "workflow_" in conversation_id):
                eff_workflow_id = conversation_id
            elif task_id and "wf_" in task_id:
                parts = task_id.split("wf_")
                if len(parts) > 1:
                    eff_workflow_id = "wf_" + parts[-1].split("_")[0]

        interaction = InteractionRecord(
            sender_agent_id=sender_agent_id,
            receiver_agent_id=receiver_agent_id,
            interaction_type=interaction_type,
            conversation_id=conversation_id,
            task_id=task_id,
            workflow_id=eff_workflow_id,
            delegation_id=delegation_id,
            delegation_parent_id=parent_del_id,
            trace_id=trace_id or f"trc_{uuid.uuid4().hex[:8]}",
            span_id=span_id or f"spn_{uuid.uuid4().hex[:8]}",
            reply_to_message_id=reply_to_message_id,
            semantic_summary=summary,
            content=content,
            resource_refs=sanitized_refs,
            sensitivity_label=sensitivity_label,
            status=status,
            retry_count=retry_count,
            downstream_action_ids=downstream_action_ids or [],
            provenance_refs=provenance_refs or [],
            capture_level=effective_capture_level,
            metadata=sanitized_meta
        )

        self.store.save_interaction(interaction)
        return interaction

    # -------------------------------------------------------------
    # Instrumented Tool Execution & Semantic Normalization
    # -------------------------------------------------------------
    def execute_tool_call(
        self,
        tool_fn: Callable[..., Any],
        tool_name: str,
        tool_operation: str,
        action_semantic: ActionSemantic,
        resource_type: ResourceClass,
        resource_id: str,
        agent_id: str,
        delegation_id: str,
        principal_id: str,
        workflow_id: str,
        task_id: str,
        parameters: Dict[str, Any],
        direction: Direction = Direction.INTERNAL,
        principal_scope: PrincipalScope = PrincipalScope.ORG,
        sensitivity_label: SensitivityLabel = SensitivityLabel.INTERNAL,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None
    ) -> Tuple[Any, CIMEvent]:
        """
        Mediates tool invocation: attaches delegation context, normalizes semantics,
        measures execution, and records before/after CIM telemetry.
        """
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        span_id = f"spn_{uuid.uuid4().hex[:8]}"
        t_start = time.perf_counter()
        
        # Verify delegation and authority binding (Issue 2)
        is_auth, auth_reason, delegation = self.validate_authority(
            delegation_id=delegation_id,
            agent_id=agent_id,
            task_id=task_id
        )
        parent_del_id = delegation.delegation_parent_id if delegation else None
        labels = {"elapsed_ms": "0.00"}
        if not is_auth:
            labels["delegation_verified"] = "false"
            labels["authority_status"] = "isolated"
            labels["authority_quarantined"] = "true"
            labels["isolation_reason"] = auth_reason
            if self.strict_authority_enforcement:
                raise PermissionError(f"Gateway rejected unverified authority for tool execution: {auth_reason}")
        else:
            labels["delegation_verified"] = "true"
            labels["authority_status"] = "verified"

        outcome = ActionOutcome.SUCCESS
        result = None
        error_msg = None

        try:
            result = tool_fn(**parameters)
        except Exception as e:
            outcome = ActionOutcome.FAILURE
            error_msg = str(e)
            raise e
        finally:
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            labels["elapsed_ms"] = f"{elapsed_ms:.2f}"
            
            # Format output summary
            out_summary = f"Completed {action_semantic.value} on {resource_id} in {elapsed_ms:.2f}ms"
            if outcome == ActionOutcome.FAILURE:
                out_summary = f"Failed {action_semantic.value} on {resource_id}: {error_msg}"

            cim_event = CIMEvent(
                event_id=event_id,
                delegation_id=delegation_id,
                delegation_parent_id=parent_del_id,
                principal_user_id=principal_id,
                agent_id=agent_id,
                tool_name=tool_name,
                tool_operation=tool_operation,
                action_semantic=action_semantic,
                action_outcome=outcome,
                direction=direction,
                principal_scope=principal_scope,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_uri=f"{tool_name}://{resource_id}",
                sensitivity_label=sensitivity_label,
                trace_id=trace_id or f"trc_{uuid.uuid4().hex[:8]}",
                span_id=span_id,
                parent_span_id=parent_span_id,
                workflow_id=workflow_id,
                task_id=task_id,
                parameters=sanitize_parameters(parameters, self.capture_level),
                output_summary=redact_sensitive_content(out_summary),
                labels=labels
            )
            self.store.save_execution_event(cim_event)

        return result, cim_event

        return result, cim_event

    # -------------------------------------------------------------
    # Provenance Tracking (W3C PROV Alignment)
    # -------------------------------------------------------------
    def record_provenance(
        self,
        workflow_id: str,
        source_id: str,
        source_type: str,
        target_id: str,
        target_type: str,
        relation: str = "wasDerivedFrom",
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProvenanceEdge:
        """Explicitly records evidence linkages between resources, messages, and artifacts."""
        edge = ProvenanceEdge(
            workflow_id=workflow_id,
            source_id=source_id,
            source_type=source_type,
            target_id=target_id,
            target_type=target_type,
            relation=relation,
            confidence=confidence,
            metadata=metadata or {}
        )
        self.store.save_provenance_edge(edge)
        return edge

# Global gateway singleton instance
default_gateway = ObservabilityGateway()

