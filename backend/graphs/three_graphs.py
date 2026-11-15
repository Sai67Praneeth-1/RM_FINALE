"""
Unified Three-Graph Transparency Coordinator.
Correlates:
1. Execution Graph (Causal: what happened)
2. Authority / Lineage Graph (Lineage: who authorized it)
3. Interaction Graph (Inter-agent communication: what was exchanged and consequence)
"""

from typing import Dict, Any, Optional
import networkx as nx
import plotly.graph_objects as go
from backend.storage.event_store import EventStore
from backend.graphs.execution_graph import ExecutionGraphBuilder
from backend.graphs.authority_graph import AuthorityGraphBuilder
from backend.graphs.interaction_graph import InteractionGraphBuilder

class ThreeGraphCoordinator:
    def __init__(self, event_store: EventStore):
        self.store = event_store
        self.exec_builder = ExecutionGraphBuilder(self.store)
        self.auth_builder = AuthorityGraphBuilder(self.store)
        self.interact_builder = InteractionGraphBuilder(self.store)

    def get_graphs_for_workflow(self, workflow_id: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Builds all three graphs for a given workflow execution."""
        wf = self.store.get_workflow_run(workflow_id)
        root_del = wf.root_delegation_id if wf else None

        g_exec = self.exec_builder.build_graph(workflow_id=workflow_id)
        g_auth = self.auth_builder.build_graph(root_delegation_id=root_del)
        g_interact = self.interact_builder.build_graph(conversation_id=conversation_id, workflow_id=workflow_id)

        return {
            "execution_graph": g_exec,
            "authority_graph": g_auth,
            "interaction_graph": g_interact
        }

    def render_plotly_graph(self, G: nx.Graph, title: str, graph_type: str = "interaction") -> go.Figure:
        """
        Renders an interactive 2D graph visualization using Plotly.
        Calculates spring layout and customizes node colors and edge hover tooltips.
        """
        if len(G.nodes) == 0:
            fig = go.Figure()
            fig.update_layout(
                title=f"{title} (No nodes recorded)",
                annotations=[dict(text="No graph data available for this selection.", showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5)]
            )
            return fig

        pos = nx.spring_layout(G, seed=42, k=1.2)
        
        # Edge Traces
        edge_x = []
        edge_y = []
        edge_text = []
        
        # Collect edges (handling MultiDiGraph vs DiGraph)
        edges = G.edges(data=True, keys=True) if isinstance(G, nx.MultiDiGraph) else G.edges(data=True)
        for e in edges:
            u, v = e[0], e[1]
            data = e[-1]
            if u in pos and v in pos:
                x0, y0 = pos[u]
                x1, y1 = pos[v]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])
                edge_text.append(data.get("label", data.get("relation", "")))

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=1.5, color="#64748b"),
            hoverinfo="none",
            mode="lines"
        )

        # Node Traces
        node_x = []
        node_y = []
        node_text = []
        node_hover = []
        node_color = []

        color_palette = {
            "agent": "#3b82f6",          # Blue
            "principal": "#8b5cf6",      # Purple
            "delegation": "#10b981",     # Emerald
            "execution_event": "#f59e0b",# Amber
            "resource": "#06b6d4",       # Cyan
            "artifact": "#ec4899"        # Pink
        }

        for node in G.nodes:
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            data = G.nodes[node]
            ntype = data.get("node_type", "agent")
            node_color.append(color_palette.get(ntype, "#64748b"))
            
            lbl = data.get("label", str(node))
            node_text.append(lbl)
            
            # Hover metadata
            hover_lines = [f"<b>{k}:</b> {v}" for k, v in data.items() if k not in ("label", "node_type")]
            node_hover.append(f"<b>Type:</b> {ntype}<br>" + "<br>".join(hover_lines[:6]))

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode="markers+text",
            hoverinfo="text",
            hovertext=node_hover,
            text=node_text,
            textposition="top center",
            textfont=dict(size=10, color="#1e293b"),
            marker=dict(
                size=28,
                color=node_color,
                line=dict(width=2, color="#0f172a")
            )
        )

        fig = go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                title=dict(text=title, font=dict(size=16, color="#0f172a")),
                showlegend=False,
                hovermode="closest",
                margin=dict(b=20, l=20, r=20, t=40),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                plot_bgcolor="#f8fafc",
                paper_bgcolor="#ffffff"
            )
        )
        return fig

