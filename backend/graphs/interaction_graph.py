"""
Interaction Graph Reconstructor (Pillar 3 - Our Proposed Research Extension).
Builds G_interact = (A, I, E_comm) from persistent inter-agent interaction records.
Answers: "Who communicated with whom, what information was exchanged, in which context, and what happened next?"
"""

import networkx as nx
from typing import List, Dict, Any, Optional
from backend.storage.event_store import EventStore

AGENT_ROLES = {
    "agent_coordinator": {"role": "Lead Orchestrator & Task Delegator", "model": "Google Gemini 3.5 Flash", "tools": ["mint_delegation", "verify_invariants"]},
    "agent_researcher": {"role": "CIM Data Ingestion & Extraction", "model": "Google Gemini 3.5 Flash", "tools": ["query_cfpb_records", "read_sample_dataset"]},
    "agent_analyst": {"role": "Statistical Anomaly Evaluator", "model": "Google Gemini 3.5 Flash", "tools": ["calculate_anomaly_rates", "compute_aggregates"]},
    "agent_reporter": {"role": "W3C PROV & Synthesis Reporter", "model": "Google Gemini 3.5 Flash", "tools": ["export_w3c_prov", "generate_markdown_report"]},
    "agent_forensics": {"role": "Security Forensics Scanner", "model": "Google Gemini 3.5 Flash", "tools": ["scan_system_access_logs", "extract_auth_tokens"]},
    "agent_threat_hunter": {"role": "Privilege Escalation Hunter", "model": "Google Gemini 3.5 Flash", "tools": ["detect_root_escalation", "trace_unauthorized_sharing"]},
    "agent_compliance": {"role": "Compliance & Policy Auditor", "model": "Google Gemini 3.5 Flash", "tools": ["audit_rbac_policies", "verify_temporal_invariants"]},
    "agent_sentiment": {"role": "Consumer Sentiment Specialist", "model": "Google Gemini 3.5 Flash", "tools": ["analyze_sentiment_distribution", "extract_topic_clusters"]},
    "agent_critic": {"role": "Adversarial Reasoning Critic", "model": "Google Gemini 3.5 Flash", "tools": ["verify_causality", "detect_inconsistencies"]},
}

class InteractionGraphBuilder:
    def __init__(self, event_store: EventStore):
        self.store = event_store

    def build_graph(
        self,
        conversation_id: Optional[str] = None,
        delegation_id: Optional[str] = None,
        workflow_id: Optional[str] = None
    ) -> nx.MultiDiGraph:
        """
        Constructs a NetworkX MultiDiGraph preserving per-message identity.
        Multiple messages between the same agents are retained as separate directed edges.
        """
        records = self.store.list_interactions(
            conversation_id=conversation_id,
            delegation_id=delegation_id,
            workflow_id=workflow_id,
            limit=200
        )
        G = nx.MultiDiGraph()

        # Add agent nodes with rich metadata
        for r in records:
            for ag_id in [r.sender_agent_id, r.receiver_agent_id]:
                if ag_id not in G:
                    meta = AGENT_ROLES.get(ag_id, {
                        "role": "Autonomous Specialized Agent",
                        "model": "Google Gemini 3.5 Flash",
                        "tools": ["standard_cim_tool"]
                    })
                    clean_label = ag_id.replace("agent_", "").replace("_", " ").title()
                    G.add_node(
                        ag_id,
                        label=clean_label,
                        node_type="agent",
                        agent_id=ag_id,
                        role=meta["role"],
                        model=meta["model"],
                        tools=meta["tools"]
                    )

            # Add directed communication edge
            summary_disp = r.semantic_summary or r.interaction_type.value
            if len(summary_disp) > 40:
                summary_disp = summary_disp[:37] + "..."

            edge_key = r.interaction_id
            G.add_edge(
                r.sender_agent_id,
                r.receiver_agent_id,
                key=edge_key,
                interaction_id=r.interaction_id,
                message_id=r.message_id,
                interaction_type=r.interaction_type.value if hasattr(r.interaction_type, "value") else str(r.interaction_type),
                label=f"[{r.interaction_type.value}] {summary_disp}",
                timestamp=r.timestamp,
                delegation_id=r.delegation_id,
                conversation_id=r.conversation_id,
                task_id=r.task_id,
                semantic_summary=r.semantic_summary,
                content=r.content,
                resource_refs=r.resource_refs,
                sensitivity_label=r.sensitivity_label.value if hasattr(r.sensitivity_label, "value") else str(r.sensitivity_label),
                status=r.status,
                retry_count=r.retry_count,
                reply_to_message_id=r.reply_to_message_id,
                downstream_action_ids=r.downstream_action_ids,
                provenance_refs=r.provenance_refs,
                capture_level=r.capture_level.value if hasattr(r.capture_level, "value") else int(r.capture_level)
            )

        return G

    def get_interaction_details(self, interaction_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves an interaction record along with its downstream tool execution consequence."""
        rec = self.store.get_interaction(interaction_id)
        if not rec:
            return None
        
        downstream_events = []
        for action_id in rec.downstream_action_ids:
            ev = self.store.get_execution_event(action_id)
            if ev:
                downstream_events.append({
                    "event_id": ev.event_id,
                    "time": ev.time,
                    "tool_name": ev.tool_name,
                    "action_semantic": ev.action_semantic.value,
                    "outcome": ev.action_outcome.value,
                    "resource_id": ev.resource_id,
                    "sensitivity": ev.sensitivity_label.value
                })

        d = rec.model_dump()
        d["downstream_execution_events"] = downstream_events
        return d

