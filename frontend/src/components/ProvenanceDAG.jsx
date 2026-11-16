import React, { useMemo, useCallback } from "react";
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  MarkerType,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "@dagrejs/dagre";

// Edge Colors by W3C PROV Relation Type using Google MD3 palette
const RELATION_COLORS = {
  wasDerivedFrom: "#1a73e8",
  used: "#f9ab00",
  wasGeneratedBy: "#1e8e3e",
  wasAssociatedWith: "#5f6368",
  actedOnBehalfOf: "#d93025",
  wasAttributedTo: "#129eaf",
};

// 1. Entity Node Component (Google Blue card)
function EntityNode({ data, selected }) {
  return (
    <div
      style={{
        padding: "10px 14px",
        borderRadius: "8px",
        background: selected ? "#e8f0fe" : "#ffffff",
        border: `2px solid ${selected ? "#1a73e8" : "#dadce0"}`,
        boxShadow: selected
          ? "0 1px 4px 1px rgba(26, 115, 232, 0.25)"
          : "0 1px 2px rgba(60, 64, 67, 0.1)",
        color: "#202124",
        width: 180,
        boxSizing: "border-box",
        textAlign: "center",
        position: "relative",
        transition: "all 0.18s ease",
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: "#1a73e8", width: 8, height: 8 }}
      />
      <div
        style={{
          fontSize: 9.5,
          fontWeight: 700,
          color: "#1a73e8",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          marginBottom: 4,
        }}
      >
        prov:Entity
      </div>
      <div
        style={{
          fontWeight: 600,
          fontSize: 12,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          color: "#202124",
        }}
        title={data.label || data.id}
      >
        {data.label || data.id}
      </div>
      {data.subtext && (
        <div
          style={{
            fontSize: 10,
            color: "#5f6368",
            marginTop: 2,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {data.subtext}
        </div>
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: "#1a73e8", width: 8, height: 8 }}
      />
    </div>
  );
}

// 2. Activity Node Component (Google Amber card)
function ActivityNode({ data, selected }) {
  return (
    <div
      style={{
        padding: "10px 14px",
        borderRadius: "8px",
        background: selected ? "#fef7e0" : "#ffffff",
        border: `2px solid ${selected ? "#f9ab00" : "#dadce0"}`,
        boxShadow: selected
          ? "0 1px 4px 1px rgba(249, 171, 0, 0.25)"
          : "0 1px 2px rgba(60, 64, 67, 0.1)",
        color: "#202124",
        width: 180,
        boxSizing: "border-box",
        textAlign: "center",
        position: "relative",
        transition: "all 0.18s ease",
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: "#f9ab00", width: 8, height: 8 }}
      />
      <div
        style={{
          fontSize: 9.5,
          fontWeight: 700,
          color: "#b06000",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          marginBottom: 4,
        }}
      >
        prov:Activity
      </div>
      <div
        style={{
          fontWeight: 600,
          fontSize: 12,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          color: "#202124",
        }}
        title={data.label || data.id}
      >
        {data.label || data.id}
      </div>
      {data.subtext && (
        <div
          style={{
            fontSize: 10,
            color: "#5f6368",
            marginTop: 2,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {data.subtext}
        </div>
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: "#f9ab00", width: 8, height: 8 }}
      />
    </div>
  );
}

// 3. Agent Node Component (Google Green card)
function AgentNode({ data, selected }) {
  return (
    <div
      style={{
        padding: "10px 14px",
        borderRadius: "8px",
        background: selected ? "#e6f4ea" : "#ffffff",
        border: `2px solid ${selected ? "#1e8e3e" : "#dadce0"}`,
        boxShadow: selected
          ? "0 1px 4px 1px rgba(30, 142, 62, 0.25)"
          : "0 1px 2px rgba(60, 64, 67, 0.1)",
        color: "#202124",
        width: 180,
        boxSizing: "border-box",
        textAlign: "center",
        position: "relative",
        transition: "all 0.18s ease",
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: "#1e8e3e", width: 8, height: 8 }}
      />
      <div
        style={{
          fontSize: 9.5,
          fontWeight: 700,
          color: "#137333",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          marginBottom: 4,
        }}
      >
        prov:Agent
      </div>
      <div
        style={{
          fontWeight: 600,
          fontSize: 12,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          color: "#202124",
        }}
        title={data.label || data.id}
      >
        {data.label || data.id}
      </div>
      {data.subtext && (
        <div
          style={{
            fontSize: 10,
            color: "#5f6368",
            marginTop: 2,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {data.subtext}
        </div>
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: "#1e8e3e", width: 8, height: 8 }}
      />
    </div>
  );
}

const nodeTypes = {
  entity: EntityNode,
  activity: ActivityNode,
  agent: AgentNode,
};

const NODE_WIDTH = 180;
const NODE_HEIGHT = 68;

function getDagreLayout(nodes, edges) {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({
    rankdir: "TB",
    ranksep: 60,
    nodesep: 40,
    align: "UL",
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  try {
    dagre.layout(dagreGraph);
  } catch (err) {
    console.warn("Dagre layout error:", err);
  }

  const layoutedNodes = nodes.map((node, idx) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    const x = nodeWithPosition
      ? nodeWithPosition.x - NODE_WIDTH / 2
      : (idx % 4) * (NODE_WIDTH + 30);
    const y = nodeWithPosition
      ? nodeWithPosition.y - NODE_HEIGHT / 2
      : Math.floor(idx / 4) * (NODE_HEIGHT + 60);

    return {
      ...node,
      position: { x, y },
    };
  });

  return { layoutedNodes, layoutedEdges: edges };
}

export default function ProvenanceDAG({ nodes = [], edges = [], onNodeClick }) {
  const { reactFlowNodes, reactFlowEdges } = useMemo(() => {
    const rawNodes = Array.isArray(nodes) ? nodes : [];
    const rawEdges = Array.isArray(edges) ? edges : [];

    const classifyProvType = (rawType, id) => {
      const nid = String(id || "").toLowerCase();
      const rtype = String(rawType || "").toLowerCase();
      if (
        rtype.includes("agent") ||
        nid.includes("agent") ||
        nid.includes("principal") ||
        nid.includes("coordinator") ||
        nid.includes("researcher") ||
        nid.includes("analyst") ||
        nid.includes("reporter")
      ) {
        return "agent";
      }
      if (
        rtype.includes("activity") ||
        rtype.includes("tool") ||
        rtype.includes("act") ||
        nid.includes("evt") ||
        nid.includes("act") ||
        nid.includes("activity") ||
        nid.includes("tool://")
      ) {
        return "activity";
      }
      return "entity";
    };

    const nodeMap = new Map();

    // 1. Process explicit nodes
    rawNodes.forEach((n) => {
      const id = String(n.id || n.entity_id || n.node_id);
      if (!id) return;
      const type = classifyProvType(n.node_type || n.prov_category || n.type, id);
      const label = n.label || n.name || id;
      nodeMap.set(id, {
        id,
        type,
        data: {
          id,
          label,
          subtext: n.subtext || n.node_type || n.prov_category || `prov:${type.charAt(0).toUpperCase() + type.slice(1)}`,
          raw: n,
        },
      });
    });

    // 2. Discover missing nodes from edge endpoints
    rawEdges.forEach((e) => {
      const srcId = String(e.source || e.source_id);
      const tgtId = String(e.target || e.target_id);

      if (srcId && !nodeMap.has(srcId)) {
        const type = classifyProvType(e.source_type, srcId);
        const label = e.source_label || (srcId.includes("/") ? srcId.split("/").pop() : srcId);
        nodeMap.set(srcId, {
          id: srcId,
          type,
          data: {
            id: srcId,
            label,
            subtext: e.source_type || `prov:${type.charAt(0).toUpperCase() + type.slice(1)}`,
            raw: { id: srcId, node_type: e.source_type, prov_category: `prov:${type}` },
          },
        });
      }

      if (tgtId && !nodeMap.has(tgtId)) {
        const type = classifyProvType(e.target_type, tgtId);
        const label = e.target_label || (tgtId.includes("/") ? tgtId.split("/").pop() : tgtId);
        nodeMap.set(tgtId, {
          id: tgtId,
          type,
          data: {
            id: tgtId,
            label,
            subtext: e.target_type || `prov:${type.charAt(0).toUpperCase() + type.slice(1)}`,
            raw: { id: tgtId, node_type: e.target_type, prov_category: `prov:${type}` },
          },
        });
      }
    });

    const parsedNodes = Array.from(nodeMap.values());

    const parsedEdges = rawEdges
      .map((e, idx) => {
        const srcId = String(e.source || e.source_id);
        const tgtId = String(e.target || e.target_id);
        const relation = e.relation || e.relation_type || "wasDerivedFrom";
        const edgeColor = RELATION_COLORS[relation] || "#5f6368";
        const edgeId = e.id || `edge-${srcId}-${tgtId}-${idx}`;

        return {
          id: edgeId,
          source: srcId,
          target: tgtId,
          label: relation,
          type: "smoothstep",
          animated: relation === "used" || relation === "wasGeneratedBy",
          style: { stroke: edgeColor, strokeWidth: 2 },
          labelStyle: { fill: "#202124", fontSize: 11, fontWeight: 600 },
          labelBgStyle: { fill: "#ffffff", stroke: "#dadce0", strokeWidth: 1, rx: 4, ry: 4 },
          labelBgPadding: [6, 4],
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: edgeColor,
            width: 16,
            height: 16,
          },
          data: e,
        };
      })
      .filter((e) => nodeMap.has(e.source) && nodeMap.has(e.target));

    if (parsedNodes.length === 0) {
      return { reactFlowNodes: [], reactFlowEdges: [] };
    }

    return getDagreLayout(parsedNodes, parsedEdges);
  }, [nodes, edges]);

  const handleNodeClick = useCallback(
    (event, node) => {
      if (onNodeClick && node?.data) {
        onNodeClick(node.data.raw || node.data);
      }
    },
    [onNodeClick]
  );

  if (!reactFlowNodes || reactFlowNodes.length === 0) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          minHeight: 480,
          background: "#ffffff",
          border: "1px dashed #dadce0",
          borderRadius: 8,
          color: "#5f6368",
          padding: 32,
        }}
      >
        <div style={{ fontSize: 36, marginBottom: 12 }}>🧬</div>
        <div
          style={{
            fontSize: 15,
            fontWeight: 600,
            color: "#202124",
            marginBottom: 6,
          }}
        >
          No provenance data for this workflow. Run a workflow first.
        </div>
        <div style={{ fontSize: 12.5, color: "#5f6368" }}>
          Run an investigation to stream W3C PROV evidence trees and multi-agent lineage.
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        width: "100%",
        height: 540,
        background: "#f8f9fa",
        borderRadius: "8px",
        border: "1px solid #dadce0",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <ReactFlow
        nodes={reactFlowNodes}
        edges={reactFlowEdges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={1.8}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#dadce0" gap={16} size={1} />
        <Controls
          style={{
            background: "#ffffff",
            border: "1px solid #dadce0",
            borderRadius: 8,
            boxShadow: "0 1px 3px rgba(60,64,67,0.15)",
          }}
        />
        <MiniMap
          nodeStrokeColor={(n) => {
            if (n.type === "agent") return "#1e8e3e";
            if (n.type === "activity") return "#f9ab00";
            return "#1a73e8";
          }}
          nodeColor={(n) => {
            if (n.type === "agent") return "#e6f4ea";
            if (n.type === "activity") return "#fef7e0";
            return "#e8f0fe";
          }}
          style={{
            background: "#ffffff",
            border: "1px solid #dadce0",
            borderRadius: 8,
          }}
        />
      </ReactFlow>

      {/* Legend Panel (Bottom-Left) */}
      <div
        style={{
          position: "absolute",
          bottom: 14,
          left: 14,
          zIndex: 10,
          background: "rgba(255, 255, 255, 0.96)",
          backdropFilter: "blur(8px)",
          border: "1px solid #dadce0",
          borderRadius: 8,
          padding: "10px 14px",
          boxShadow: "0 1px 3px 1px rgba(60, 64, 67, 0.15)",
          fontSize: 11.5,
          pointerEvents: "auto",
        }}
      >
        <div
          style={{
            fontSize: 10,
            fontWeight: 700,
            color: "#5f6368",
            textTransform: "uppercase",
            marginBottom: 8,
            letterSpacing: "0.06em",
          }}
        >
          W3C PROV Legend
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span
              style={{
                width: 12,
                height: 12,
                borderRadius: 3,
                background: "#e8f0fe",
                display: "inline-block",
                border: "1.5px solid #1a73e8",
              }}
            />
            <span style={{ color: "#202124", fontWeight: 500 }}>
              prov:Entity (Google Blue)
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span
              style={{
                width: 12,
                height: 12,
                borderRadius: 3,
                background: "#fef7e0",
                display: "inline-block",
                border: "1.5px solid #f9ab00",
              }}
            />
            <span style={{ color: "#202124", fontWeight: 500 }}>
              prov:Activity (Google Amber)
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span
              style={{
                width: 12,
                height: 12,
                borderRadius: 3,
                background: "#e6f4ea",
                display: "inline-block",
                border: "1.5px solid #1e8e3e",
              }}
            />
            <span style={{ color: "#202124", fontWeight: 500 }}>
              prov:Agent (Google Green)
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
