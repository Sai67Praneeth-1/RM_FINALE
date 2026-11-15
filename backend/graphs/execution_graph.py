"""
Execution Graph Reconstructor (Pillar 1).
Builds G_exec = (E, R_causal) from recorded CIM execution events.
Answers: "What happened causally across tools and execution spans?"
"""

import networkx as nx
from typing import List, Dict, Any, Optional
from backend.schemas.events import CIMEvent
from backend.storage.event_store import EventStore

class ExecutionGraphBuilder:
    def __init__(self, event_store: EventStore):
        self.store = event_store

    def build_graph(self, workflow_id: Optional[str] = None, delegation_id: Optional[str] = None) -> nx.DiGraph:
        """
        Constructs a NetworkX DiGraph representing causal execution events and tool operations.
        Nodes are execution events (spans/actions), edges represent parent_span -> child_span or temporal sequence.
        """
        events = self.store.list_execution_events(workflow_id=workflow_id, delegation_id=delegation_id)
        G = nx.DiGraph()

        span_map: Dict[str, str] = {}
        for ev in events:
            node_id = ev.event_id
            G.add_node(
                node_id,
                label=f"{ev.agent_id}\n{ev.action_semantic.value}:{ev.tool_name}",
                event_id=ev.event_id,
                time=ev.time,
                agent_id=ev.agent_id,
                tool_name=ev.tool_name,
                tool_operation=ev.tool_operation,
                action_semantic=ev.action_semantic.value,
                outcome=ev.action_outcome.value,
                resource_id=ev.resource_id,
                sensitivity=ev.sensitivity_label.value,
                delegation_id=ev.delegation_id,
                trace_id=ev.trace_id,
                span_id=ev.span_id,
                parent_span_id=ev.parent_span_id,
                node_type="execution_event"
            )
            if ev.span_id:
                span_map[ev.span_id] = node_id

        # Connect edges based on explicit causal parent_span_id links
        prev_node = None
        for ev in events:
            curr_node = ev.event_id
            if ev.parent_span_id and ev.parent_span_id in span_map:
                parent_node = span_map[ev.parent_span_id]
                G.add_edge(parent_node, curr_node, relation="causal_child", edge_type="causal")
            elif prev_node and ev.trace_id and G.nodes[prev_node].get("trace_id") == ev.trace_id:
                # Same trace sequence fallback
                G.add_edge(prev_node, curr_node, relation="temporal_sequence", edge_type="sequence")
            prev_node = curr_node

        return G

    def get_connected_components(self, G: nx.DiGraph) -> List[List[str]]:
        """Returns causal connected components for authority-causality divergence analysis."""
        return [list(c) for c in nx.weakly_connected_components(G)]

