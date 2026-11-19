"""
Provenance Layer & Lineage Tracker (W3C PROV Aligned).
Implements the 7th Layer of the Architecture (RM_MID Slide 10, 11, 14):
Connects source datasets, tool execution activities, intermediate messages,
and final report artifacts into an inspectable W3C PROV evidence DAG.

W3C PROV Data Model:
- prov:Entity: Source datasets, extracted records, metrics, report artifacts
- prov:Activity: Ingestion, statistical analysis, report compilation
- prov:Agent: Coordinator, Researcher, Analyst, Reporter, Principal
- prov:Relations: wasDerivedFrom, wasGeneratedBy, used, wasAssociatedWith, actedOnBehalfOf, wasAttributedTo
"""

import json
import networkx as nx
import plotly.graph_objects as go
from typing import List, Dict, Any, Optional
from backend.storage.event_store import EventStore
from backend.schemas.workflow import ProvenanceEdge

class ProvenanceTracker:
    def __init__(self, event_store: EventStore):
        self.store = event_store

    def build_provenance_graph(self, workflow_id: Optional[str] = None) -> nx.DiGraph:
        """
        Constructs a NetworkX DiGraph representing the full W3C PROV evidence DAG.
        Nodes represent prov:Entity, prov:Activity, or prov:Agent.
        Edges represent explicit evidence dependencies.
        """
        edges = self.store.list_provenance_edges(workflow_id=workflow_id)
        G = nx.DiGraph()

        for e in edges:
            src_type = self._classify_prov_type(e.source_type, e.source_id)
            tgt_type = self._classify_prov_type(e.target_type, e.target_id)

            if e.source_id not in G:
                G.add_node(
                    e.source_id,
                    label=self._format_node_label(e.source_id),
                    node_type=e.source_type,
                    prov_category=src_type,
                    entity_id=e.source_id
                )
            if e.target_id not in G:
                G.add_node(
                    e.target_id,
                    label=self._format_node_label(e.target_id),
                    node_type=e.target_type,
                    prov_category=tgt_type,
                    entity_id=e.target_id
                )
            G.add_edge(
                e.source_id,
                e.target_id,
                relation=e.relation,
                confidence=e.confidence,
                timestamp=e.timestamp,
                label=f"{e.relation} ({e.confidence * 100:.0f}%)"
            )

        return G

    # Alias build_provenance_dag to build_provenance_graph for backwards/API compatibility
    build_provenance_dag = build_provenance_graph

    def _classify_prov_type(self, raw_type: str, node_id: str) -> str:
        """Categorizes nodes into W3C PROV standard classes: Entity, Activity, Agent."""
        nid = str(node_id).lower()
        rtype = str(raw_type).lower()
        if "agent" in rtype or "agent" in nid or "principal" in nid:
            return "prov:Agent"
        elif "tool" in rtype or "act" in rtype or "evt" in nid or "activity" in rtype:
            return "prov:Activity"
        else:
            return "prov:Entity"

    def _format_node_label(self, node_id: str) -> str:
        clean = str(node_id).replace("file://", "").replace("tool://", "").replace("msg://", "")
        if "/" in clean:
            clean = clean.split("/")[-1]
        if len(clean) > 28:
            clean = clean[:25] + "..."
        return clean

    def trace_backward_lineage(self, target_id: str, workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Performs backward provenance traversal from an output artifact or finding
        back through intermediate activities and messages to the origin datasets.
        """
        G = self.build_provenance_graph(workflow_id=workflow_id)
        if target_id not in G:
            return []

        ancestors = nx.ancestors(G, target_id)
        ancestors.add(target_id)
        subG = G.subgraph(ancestors)

        path_elements = []
        for u, v, data in subG.edges(data=True):
            path_elements.append({
                "source": u,
                "source_label": subG.nodes[u].get("label", u),
                "source_prov": subG.nodes[u].get("prov_category", "prov:Entity"),
                "relation": data.get("relation", "wasDerivedFrom"),
                "confidence": data.get("confidence", 1.0),
                "target": v,
                "target_label": subG.nodes[v].get("label", v),
                "target_prov": subG.nodes[v].get("prov_category", "prov:Entity"),
                "node_id": v,
                "label": f"{u} --[{data.get('relation', 'wasDerivedFrom')}]--> {v}"
            })
            
        if not path_elements:
            for node in subG.nodes:
                path_elements.append({
                    "source": node,
                    "source_label": subG.nodes[node].get("label", node),
                    "source_prov": subG.nodes[node].get("prov_category", "prov:Entity"),
                    "relation": "identity",
                    "confidence": 1.0,
                    "target": node,
                    "target_label": subG.nodes[node].get("label", node),
                    "target_prov": subG.nodes[node].get("prov_category", "prov:Entity"),
                    "label": f"{node} (Root Entity)"
                })
        return path_elements

    def get_provenance_completeness(self, workflow_id: str) -> float:
        """
        Computes the Provenance Completeness metric (RM_MID Slide 14):
        Fraction of generated report artifacts whose backward lineage successfully connects
        to an origin dataset (source_type == 'resource').
        """
        artifacts = self.store.list_artifacts(workflow_id=workflow_id)
        if not artifacts:
            return 0.0
        
        covered = 0
        for art in artifacts:
            lineage = self.trace_backward_lineage(art.artifact_id, workflow_id=workflow_id)
            has_origin = any(
                "file://" in str(elem["source"]) or elem.get("source_prov") == "prov:Entity"
                for elem in lineage
            )
            if has_origin:
                covered += 1
        return round(covered / len(artifacts), 4)

    def export_prov_json(self, workflow_id: str) -> Dict[str, Any]:
        """
        Exports the provenance graph in standardized W3C PROV-JSON format.
        https://www.w3.org/Submission/2013/SUBM-prov-json-20130424/
        """
        G = self.build_provenance_graph(workflow_id=workflow_id)
        prov_json = {
            "prefix": {
                "prov": "http://www.w3.org/ns/prov#",
                "sec": "https://agentic-transparency.org/schema#",
                "default": f"https://agentic-transparency.org/run/{workflow_id}#"
            },
            "entity": {},
            "activity": {},
            "agent": {},
            "wasDerivedFrom": {},
            "used": {},
            "wasGeneratedBy": {},
            "wasAssociatedWith": {},
            "actedOnBehalfOf": {}
        }

        for n, data in G.nodes(data=True):
            pcat = data.get("prov_category", "prov:Entity")
            entry = {"sec:label": data.get("label", n), "sec:type": data.get("node_type", "unknown")}
            if pcat == "prov:Agent":
                prov_json["agent"][n] = entry
            elif pcat == "prov:Activity":
                prov_json["activity"][n] = entry
            else:
                prov_json["entity"][n] = entry

        edge_counter = 1
        for u, v, data in G.edges(data=True):
            rel = data.get("relation", "wasDerivedFrom")
            edge_id = f"_:wdf_{edge_counter}"
            record = {
                "prov:generatedEntity": v,
                "prov:usedEntity": u,
                "sec:confidence": data.get("confidence", 1.0)
            }
            if rel in prov_json:
                prov_json[rel][edge_id] = record
            else:
                prov_json["wasDerivedFrom"][edge_id] = record
            edge_counter += 1

        return prov_json

    def export_prov_n(self, workflow_id: str) -> str:
        """Exports the graph in W3C PROV-N notation."""
        G = self.build_provenance_graph(workflow_id=workflow_id)
        lines = [
            f"document",
            f"  prefix prov <http://www.w3.org/ns/prov#>",
            f"  prefix sec <https://agentic-transparency.org/schema#>",
            ""
        ]
        for n, data in G.nodes(data=True):
            pcat = data.get("prov_category", "prov:Entity").replace("prov:", "")
            lines.append(f"  {pcat.lower()}({n}, [sec:label=\"{data.get('label', n)}\"])")
        lines.append("")
        for u, v, data in G.edges(data=True):
            rel = data.get("relation", "wasDerivedFrom")
            lines.append(f"  {rel}({v}, {u})")
        lines.append("endDocument")
        return "\n".join(lines)

    def render_provenance_plotly(self, G: Any, title: str = "W3C PROV Provenance Lineage DAG") -> go.Figure:
        """
        Renders an interactive 2D diagram representing the W3C PROV DAG with standard PROV styling:
        - Entities: Yellow (#F59E0B)
        - Activities: Blue (#3B82F6)
        - Agents: Orange (#EA580C)
        """
        if isinstance(G, str):
            G = self.build_provenance_graph(workflow_id=G)

        if not hasattr(G, "nodes") or len(G.nodes) == 0:
            fig = go.Figure()
            fig.update_layout(
                title=f"{title} (No recorded provenance edges)",
                annotations=[dict(text="No provenance links recorded for this selection.", showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5)]
            )
            return fig

        pos = nx.spring_layout(G, seed=123, k=1.1)
        
        edge_x = []
        edge_y = []
        for u, v in G.edges:
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=2, color="#94A3B8"),
            hoverinfo="none",
            mode="lines"
        )

        node_x = []
        node_y = []
        node_text = []
        node_hover = []
        node_color = []

        # W3C PROV Standard Colors
        prov_colors = {
            "prov:Entity": "#F59E0B",     # Gold / Yellow (Entities)
            "prov:Activity": "#3B82F6",   # Blue (Activities)
            "prov:Agent": "#EA580C"       # Orange / Rust (Agents)
        }

        for n in G.nodes:
            x, y = pos[n]
            node_x.append(x)
            node_y.append(y)
            pcat = G.nodes[n].get("prov_category", "prov:Entity")
            lbl = G.nodes[n].get("label", n)
            node_color.append(prov_colors.get(pcat, "#64748B"))
            node_text.append(f"[{pcat.replace('prov:', '')}]<br>{lbl}")
            node_hover.append(f"<b>{n}</b><br>PROV Category: {pcat}<br>Type: {G.nodes[n].get('node_type')}")

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode="markers+text",
            hoverinfo="text",
            hovertext=node_hover,
            text=node_text,
            textposition="top center",
            textfont=dict(size=10, color="#0F172A", family="Segoe UI, sans-serif"),
            marker=dict(
                size=26,
                color=node_color,
                line=dict(width=2.5, color="#FFFFFF")
            )
        )

        return go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                title=dict(text=title, font=dict(size=16, color="#0F172A")),
                showlegend=False,
                margin=dict(b=20, l=20, r=20, t=40),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                plot_bgcolor="#F8FAFC"
            )
        )
