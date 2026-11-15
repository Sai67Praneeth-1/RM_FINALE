"""
Interaction Graph Reconstructor (Pillar 3 - Our Proposed Research Extension).
Builds G_interact = (A, I, E_comm) from persistent inter-agent interaction records.
Answers: "Who communicated with whom, what information was exchanged, in which context, and what happened next?"
"""

import networkx as nx
from typing import List, Dict, Any, Optional
from backend.storage.event_store import EventStore

class InteractionGraphBuilder:
    def __init__(self, event_store: EventStore):
        self.store = event_store

    def build_graph(
        self,
        conversation_id: Optional[str] = None,
        delegation_id: Optional[str] = None
    ) -> nx.MultiDiGraph:
        """
        Constructs a NetworkX MultiDiGraph preserving per-message identity.
        Multiple messages between the same agents are retained as separate directed edges.
        """
        records = self.store.list_interactions(
            conversation_id=conversation_id,
            delegation_id=delegation_id,
            limit=200
        )
        G = nx.MultiDiGraph()

        # Add agent nodes
        for r in records:
            if r.sender_agent_id not in G:
                G.add_node(
                    r.sender_agent_id,
                    label=r.sender_agent_id.replace("agent_", "").title(),
                    node_type="agent",
                    agent_id=r.sender_agent_id
                )
            if r.receiver_agent_id not in G:
                G.add_node(
                    r.receiver_agent_id,
                    label=r.receiver_agent_id.replace("agent_", "").title(),
                    node_type="agent",
                    agent_id=r.receiver_agent_id
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

