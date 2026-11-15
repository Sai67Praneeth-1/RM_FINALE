"""
Authority / Lineage Graph Reconstructor (Pillar 2).
Builds G_auth = (D, R_lineage) from persistent delegation records.
Answers: "Under whose delegated authority was each action authorized?"
"""

import networkx as nx
from typing import List, Dict, Any, Optional
from backend.storage.event_store import EventStore

class AuthorityGraphBuilder:
    def __init__(self, event_store: EventStore):
        self.store = event_store

    def build_graph(self, root_delegation_id: Optional[str] = None) -> nx.DiGraph:
        """
        Constructs a NetworkX DiGraph representing the delegation hierarchy (authority forest/DAG).
        Nodes represent Principals, Agents, and Delegations; edges represent authorization propagation.
        """
        G = nx.DiGraph()
        
        if root_delegation_id:
            delegations = self.store.get_delegation_closure(root_delegation_id)
        else:
            delegations = self.store.list_delegations(limit=100)

        for d in delegations:
            del_node = f"del_{d.delegation_id}"
            prin_node = f"prin_{d.principal_id}"
            agent_node = f"agent_{d.agent_id}"

            # Add Principal node
            if prin_node not in G:
                G.add_node(prin_node, label=f"Principal\n{d.principal_id}", node_type="principal", entity_id=d.principal_id)

            # Add Agent node
            if agent_node not in G:
                G.add_node(agent_node, label=f"Agent\n{d.agent_id}", node_type="agent", entity_id=d.agent_id)

            # Add Delegation node
            G.add_node(
                del_node,
                label=f"Delegation\n{d.delegation_id}\n({d.scope})",
                node_type="delegation",
                delegation_id=d.delegation_id,
                delegation_parent_id=d.delegation_parent_id,
                principal_id=d.principal_id,
                agent_id=d.agent_id,
                task_id=d.task_id,
                scope=d.scope,
                status=d.status.value if hasattr(d.status, "value") else str(d.status),
                issued_at=d.issued_at
            )

            # Edge 1: Principal authorizes delegation
            G.add_edge(prin_node, del_node, relation="issued_by", edge_type="authority_grant")
            # Edge 2: Delegation assigns authority to Agent
            G.add_edge(del_node, agent_node, relation="assigned_to", edge_type="authority_assignment")

            # Edge 3: Parent delegation -> Child delegation (Re-delegation lineage)
            if d.delegation_parent_id:
                parent_node = f"del_{d.delegation_parent_id}"
                if parent_node not in G:
                    G.add_node(parent_node, label=f"Delegation\n{d.delegation_parent_id}", node_type="delegation", delegation_id=d.delegation_parent_id)
                G.add_edge(parent_node, del_node, relation="re_delegated_from", edge_type="lineage_closure")

        return G

