import React, { useState, useMemo } from "react";
import {
  Share2,
  Activity,
  Key,
  Shield,
  Bot,
  Database,
  Layers,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Sparkles,
  RefreshCw,
  Info,
  X,
  ExternalLink,
  Play,
  Zap,
} from "lucide-react";
import AgentInteractionGraph from "./AgentInteractionGraph";

// Obsidian Research Palette Node Colors
export const OBSIDIAN_NODE_COLORS = {
  agent: { color: "#60a5fa", border: "#60a5fa", bg: "rgba(96, 165, 250, 0.15)", text: "#93c5fd" },
  principal: { color: "#e8a44a", border: "#e8a44a", bg: "rgba(232, 164, 74, 0.15)", text: "#fde68a" },
  delegation: { color: "#34d399", border: "#34d399", bg: "rgba(52, 211, 153, 0.15)", text: "#a7f3d0" },
  execution_event: { color: "#f59e0b", border: "#f59e0b", bg: "rgba(245, 158, 11, 0.15)", text: "#fde68a" },
  resource: { color: "#2dd4bf", border: "#2dd4bf", bg: "rgba(45, 212, 191, 0.15)", text: "#99f6e4" },
  artifact: { color: "#a78bfa", border: "#a78bfa", bg: "rgba(167, 139, 250, 0.15)", text: "#ddd6fe" },
};

// Known Agent Styles (Mapped to Obsidian Research Palette: Agent #60a5fa)
const AGENT_COLORS = {
  agent_coordinator: { border: "#60a5fa", bg: "rgba(96, 165, 250, 0.15)", text: "#93c5fd", label: "Agent A: Coordinator" },
  Coordinator_Agent: { border: "#60a5fa", bg: "rgba(96, 165, 250, 0.15)", text: "#93c5fd", label: "Coordinator Agent" },
  agent_researcher: { border: "#60a5fa", bg: "rgba(96, 165, 250, 0.15)", text: "#93c5fd", label: "Agent B: Researcher" },
  Executor_Agent: { border: "#60a5fa", bg: "rgba(96, 165, 250, 0.15)", text: "#93c5fd", label: "Executor Agent" },
  agent_analyst: { border: "#60a5fa", bg: "rgba(96, 165, 250, 0.15)", text: "#93c5fd", label: "Agent C: Analyst" },
  Critic_Agent: { border: "#60a5fa", bg: "rgba(96, 165, 250, 0.15)", text: "#93c5fd", label: "Critic Agent" },
  agent_reporter: { border: "#60a5fa", bg: "rgba(96, 165, 250, 0.15)", text: "#93c5fd", label: "Agent D: Reporter" },
  Synthesizer_Agent: { border: "#60a5fa", bg: "rgba(96, 165, 250, 0.15)", text: "#93c5fd", label: "Synthesizer Agent" },
};

export default function ThreeGraphViewer({
  graphData,
  selectedWorkflowId,
  workflows = [],
  onSelectWorkflow,
  onRefresh,
  onRunSampleWorkflow,
  loading = false,
}) {
  const [activeGraphTab, setActiveGraphTab] = useState("unified"); // "unified" | "execution_graph" | "authority_graph" | "interaction_graph" | "raw_json"
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [isSampleRunning, setIsSampleRunning] = useState(false);

  // Safe fallback if graphData is null or empty
  const execGraph = graphData?.execution_graph || { nodes: [], edges: [] };
  const authGraph = graphData?.authority_graph || { nodes: [], edges: [] };
  const itrGraph = graphData?.interaction_graph || { nodes: [], edges: [] };

  const execNodes = execGraph.nodes || [];
  const execEdges = execGraph.edges || [];
  const authNodes = authGraph.nodes || [];
  const authEdges = authGraph.edges || [];
  const itrNodes = itrGraph.nodes || [];
  const itrEdges = itrGraph.edges || [];

  const handleRunSample = async () => {
    if (onRunSampleWorkflow) {
      setIsSampleRunning(true);
      try {
        await onRunSampleWorkflow();
      } finally {
        setIsSampleRunning(false);
      }
    }
  };

  return (
    <div className="three-graph-explorer" style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      {/* 1. New-User Architectural Guidance Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: 12,
        }}
      >
        {/* Card 1: Execution Graph */}
        <div
          onClick={() => setActiveGraphTab("execution_graph")}
          style={{
            background: activeGraphTab === "execution_graph" ? "rgba(16, 185, 129, 0.12)" : "#111827",
            border: activeGraphTab === "execution_graph" ? "1px solid #10b981" : "1px solid #1f2937",
            borderRadius: 8,
            padding: "14px 16px",
            cursor: "pointer",
            transition: "all 0.15s ease",
            position: "relative",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: "#34d399", display: "flex", alignItems: "center", gap: 6 }}>
              <Activity size={16} />
              <span>1. Execution Graph (GE)</span>
            </span>
            <span style={{ fontSize: 11, background: "rgba(16, 185, 129, 0.2)", color: "#34d399", padding: "2px 6px", borderRadius: 4 }}>
              {execNodes.length} Events
            </span>
          </div>
          <div style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.4 }}>
            <strong>"What happened?"</strong> &bull; Causal sequence of tool invocations, dataset operations, and status outcomes.
          </div>
        </div>

        {/* Card 2: Authority Graph */}
        <div
          onClick={() => setActiveGraphTab("authority_graph")}
          style={{
            background: activeGraphTab === "authority_graph" ? "rgba(139, 92, 246, 0.12)" : "#111827",
            border: activeGraphTab === "authority_graph" ? "1px solid #8b5cf6" : "1px solid #1f2937",
            borderRadius: 8,
            padding: "14px 16px",
            cursor: "pointer",
            transition: "all 0.15s ease",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: "#a78bfa", display: "flex", alignItems: "center", gap: 6 }}>
              <Key size={16} />
              <span>2. Authority Graph (GA)</span>
            </span>
            <span style={{ fontSize: 11, background: "rgba(139, 92, 246, 0.2)", color: "#a78bfa", padding: "2px 6px", borderRadius: 4 }}>
              {authNodes.length} Nodes
            </span>
          </div>
          <div style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.4 }}>
            <strong>"Who authorized it?"</strong> &bull; Cryptographic delegation lineage from User Principal down to sub-agent tokens.
          </div>
        </div>

        {/* Card 3: Interaction Graph */}
        <div
          onClick={() => setActiveGraphTab("interaction_graph")}
          style={{
            background: activeGraphTab === "interaction_graph" ? "rgba(56, 189, 248, 0.12)" : "#111827",
            border: activeGraphTab === "interaction_graph" ? "1px solid #38bdf8" : "1px solid #1f2937",
            borderRadius: 8,
            padding: "14px 16px",
            cursor: "pointer",
            transition: "all 0.15s ease",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: "#38bdf8", display: "flex", alignItems: "center", gap: 6 }}>
              <Share2 size={16} />
              <span>3. Interaction Graph (GI)</span>
            </span>
            <span style={{ fontSize: 11, background: "rgba(56, 189, 248, 0.2)", color: "#38bdf8", padding: "2px 6px", borderRadius: 4 }}>
              {itrNodes.length} Agents
            </span>
          </div>
          <div style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.4 }}>
            <strong>"Who communicated?"</strong> &bull; Peer-to-peer dialogues, subtask handoffs, and consequence tool linkages.
          </div>
        </div>

        {/* Card 4: Unified Multi-Graph Overlay */}
        <div
          onClick={() => setActiveGraphTab("unified")}
          style={{
            background: activeGraphTab === "unified" ? "rgba(245, 158, 11, 0.12)" : "#111827",
            border: activeGraphTab === "unified" ? "1px solid #f59e0b" : "1px solid #1f2937",
            borderRadius: 8,
            padding: "14px 16px",
            cursor: "pointer",
            transition: "all 0.15s ease",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: "#fbbf24", display: "flex", alignItems: "center", gap: 6 }}>
              <Layers size={16} />
              <span>4. Unified "3-in-1" View</span>
            </span>
            <span style={{ fontSize: 11, background: "rgba(245, 158, 11, 0.2)", color: "#fbbf24", padding: "2px 6px", borderRadius: 4 }}>
              Full Trace
            </span>
          </div>
          <div style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.4 }}>
            <strong>End-to-End Correlation:</strong> See how an inter-agent dialogue grants authority which executes tool actions.
          </div>
        </div>
      </div>

      {/* 2. Control Toolbar & Workflow Run Selector */}
      <div
        className="stat-card"
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          padding: "12px 18px",
        }}
      >
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 12, flex: 1 }}>
          <label style={{ fontSize: 13, color: "#94a3b8", fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
            <Bot size={15} color="#60a5fa" />
            <span>Select Investigation Workflow:</span>
          </label>
          <select
            value={selectedWorkflowId}
            onChange={(e) => onSelectWorkflow && onSelectWorkflow(e.target.value)}
            style={{
              background: "#0b0f19",
              border: "1px solid #334155",
              borderRadius: 6,
              color: "#f8fafc",
              padding: "7px 12px",
              fontSize: 12.5,
              minWidth: 260,
              maxWidth: 420,
            }}
          >
            {workflows && workflows.length > 0 ? (
              workflows.map((w) => (
                <option key={w.workflow_id} value={w.workflow_id}>
                  {w.workflow_id} &bull; {(w.task_description || "Multi-Agent Investigation").substring(0, 36)}...
                </option>
              ))
            ) : (
              <option value="">No workflows recorded yet</option>
            )}
          </select>

          {onRefresh && (
            <button
              className="pill-btn"
              onClick={onRefresh}
              disabled={loading}
              title="Refresh graph data"
              style={{ display: "flex", alignItems: "center", gap: 6, padding: "6px 10px" }}
            >
              <RefreshCw size={13} className={loading ? "spin" : ""} />
              <span>Refresh</span>
            </button>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button
            className="pill-btn"
            onClick={handleRunSample}
            disabled={isSampleRunning}
            style={{
              background: "#1d4ed8",
              borderColor: "#2563eb",
              color: "#ffffff",
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "7px 14px",
            }}
          >
            <Sparkles size={14} className={isSampleRunning ? "spin" : ""} />
            <span>{isSampleRunning ? "Executing Multi-Agent Run..." : "⚡ Run Sample Multi-Agent Investigation"}</span>
          </button>
        </div>
      </div>

      {/* 3. Main Topology View & Forensic Node Inspector Split View */}
      <div style={{ display: "grid", gridTemplateColumns: selectedEntity ? "1fr 340px" : "1fr", gap: 16 }}>
        {/* Graph Display Card */}
        <div className="stat-card" style={{ padding: 18, minHeight: 460 }}>
          {/* Sub-Header Tabs */}
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #1f2937", paddingBottom: 12, marginBottom: 16 }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              <button
                className={`pill-btn ${activeGraphTab === "unified" ? "active" : ""}`}
                onClick={() => setActiveGraphTab("unified")}
                style={{
                  background: activeGraphTab === "unified" ? "#d97706" : "#1e293b",
                  color: activeGraphTab === "unified" ? "#ffffff" : "#94a3b8",
                  fontWeight: 600,
                }}
              >
                <Layers size={14} style={{ display: "inline", marginRight: 6 }} />
                Unified 3-in-1 Overlay
              </button>
              <button
                className={`pill-btn ${activeGraphTab === "execution_graph" ? "active" : ""}`}
                onClick={() => setActiveGraphTab("execution_graph")}
                style={{
                  background: activeGraphTab === "execution_graph" ? "#059669" : "#1e293b",
                  color: activeGraphTab === "execution_graph" ? "#ffffff" : "#94a3b8",
                  fontWeight: 600,
                }}
              >
                <Activity size={14} style={{ display: "inline", marginRight: 6 }} />
                Execution Graph (GE)
              </button>
              <button
                className={`pill-btn ${activeGraphTab === "authority_graph" ? "active" : ""}`}
                onClick={() => setActiveGraphTab("authority_graph")}
                style={{
                  background: activeGraphTab === "authority_graph" ? "#7c3aed" : "#1e293b",
                  color: activeGraphTab === "authority_graph" ? "#ffffff" : "#94a3b8",
                  fontWeight: 600,
                }}
              >
                <Key size={14} style={{ display: "inline", marginRight: 6 }} />
                Authority Lineage (GA)
              </button>
              <button
                className={`pill-btn ${activeGraphTab === "interaction_graph" ? "active" : ""}`}
                onClick={() => setActiveGraphTab("interaction_graph")}
                style={{
                  background: activeGraphTab === "interaction_graph" ? "#0284c7" : "#1e293b",
                  color: activeGraphTab === "interaction_graph" ? "#ffffff" : "#94a3b8",
                  fontWeight: 600,
                }}
              >
                <Share2 size={14} style={{ display: "inline", marginRight: 6 }} />
                Interaction Graph (GI)
              </button>
              <button
                className={`pill-btn ${activeGraphTab === "raw_json" ? "active" : ""}`}
                onClick={() => setActiveGraphTab("raw_json")}
                style={{ fontSize: 11 }}
              >
                Developer JSON
              </button>
            </div>

            <div style={{ fontSize: 12, color: "#64748b" }}>
              💡 <em>Click any node or connection arrow to inspect forensic attributes.</em>
            </div>
          </div>

          {/* VIEW A: UNIFIED 3-IN-1 OVERLAY */}
          {activeGraphTab === "unified" && (
            <UnifiedThreeGraphView
              execNodes={execNodes}
              authNodes={authNodes}
              itrEdges={itrEdges}
              itrNodes={itrNodes}
              onSelectNode={(node, type) => setSelectedEntity({ ...node, entityCategory: type })}
              onSelectEdge={(edge, type) => setSelectedEntity({ ...edge, entityCategory: type })}
            />
          )}

          {/* VIEW B: EXECUTION GRAPH (GE) VISUAL TOPOLOGY */}
          {activeGraphTab === "execution_graph" && (
            <ExecutionGraphTopology
              nodes={execNodes}
              edges={execEdges}
              onSelectNode={(node) => setSelectedEntity({ ...node, entityCategory: "Execution Event (CIM)" })}
              onSelectEdge={(edge) => setSelectedEntity({ ...edge, entityCategory: "Execution Causal Link" })}
            />
          )}

          {/* VIEW C: AUTHORITY GRAPH (GA) VISUAL TOPOLOGY */}
          {activeGraphTab === "authority_graph" && (
            <AuthorityGraphTopology
              nodes={authNodes}
              edges={authEdges}
              onSelectNode={(node) => setSelectedEntity({ ...node, entityCategory: "Authority / Delegation Node" })}
              onSelectEdge={(edge) => setSelectedEntity({ ...edge, entityCategory: "Delegation Grant" })}
            />
          )}

          {/* VIEW D: INTERACTION GRAPH (GI) VISUAL TOPOLOGY */}
          {activeGraphTab === "interaction_graph" && (
            <div>
              <AgentInteractionGraph
                graph={itrGraph}
                workflowId={selectedWorkflowId}
                title="Inter-Agent Communication Graph (G_interact) Topology"
              />
            </div>
          )}

          {/* VIEW E: RAW JSON (DEVELOPER VIEW) */}
          {activeGraphTab === "raw_json" && (
            <div style={{ background: "#0b0f19", border: "1px solid #1e293b", borderRadius: 8, padding: 14, maxHeight: 480, overflowY: "auto" }}>
              <pre style={{ color: "#94a3b8", fontSize: 11.5, margin: 0, fontFamily: "monospace" }}>
                {JSON.stringify(graphData || {}, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* 4. Forensic Node & Edge Inspector Slide-In Drawer */}
        {selectedEntity && (
          <div
            className="stat-card"
            style={{
              padding: 16,
              background: "#0b0f19",
              border: "1px solid #334155",
              display: "flex",
              flexDirection: "column",
              gap: 12,
              maxHeight: 640,
              overflowY: "auto",
              position: "relative",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #1f2937", paddingBottom: 10 }}>
              <div>
                <span style={{ fontSize: 10, color: "#38bdf8", textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.05em" }}>
                  {selectedEntity.entityCategory || "Entity Inspection"}
                </span>
                <h5 style={{ margin: "2px 0 0 0", color: "#f8fafc", fontSize: 14 }}>
                  {selectedEntity.label || selectedEntity.id || selectedEntity.event_id || "Forensic Inspector"}
                </h5>
              </div>
              <button
                onClick={() => setSelectedEntity(null)}
                style={{ background: "transparent", border: "none", color: "#94a3b8", cursor: "pointer", padding: 4 }}
              >
                <X size={16} />
              </button>
            </div>

            {/* Entity Attributes */}
            <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 12.5 }}>
              {selectedEntity.agent_id && (
                <div>
                  <div style={{ color: "#64748b", fontSize: 11 }}>Executing Agent:</div>
                  <div style={{ color: "#60a5fa", fontWeight: 600 }}>{selectedEntity.agent_id}</div>
                </div>
              )}

              {selectedEntity.tool_name && (
                <div>
                  <div style={{ color: "#64748b", fontSize: 11 }}>CIM Tool Invocated:</div>
                  <div style={{ color: "#f59e0b", fontWeight: 600 }}>
                    <code>{selectedEntity.tool_name}</code> &bull; <em>{selectedEntity.tool_operation || selectedEntity.action_semantic}</em>
                  </div>
                </div>
              )}

              {selectedEntity.resource_id && (
                <div>
                  <div style={{ color: "#64748b", fontSize: 11 }}>Target Resource:</div>
                  <div style={{ color: "#2dd4bf" }}><code>{selectedEntity.resource_id}</code></div>
                </div>
              )}

              {selectedEntity.delegation_id && (
                <div>
                  <div style={{ color: "#64748b", fontSize: 11 }}>Authority Delegation Token:</div>
                  <div style={{ color: "#34d399", fontWeight: 600 }}><code>{selectedEntity.delegation_id}</code></div>
                </div>
              )}

              {selectedEntity.outcome && (
                <div>
                  <div style={{ color: "#64748b", fontSize: 11 }}>Execution Outcome:</div>
                  <div style={{ color: selectedEntity.outcome === "success" ? "#34d399" : "#f87171", fontWeight: 600 }}>
                    {selectedEntity.outcome.toUpperCase()}
                  </div>
                </div>
              )}

              {selectedEntity.sensitivity && (
                <div>
                  <div style={{ color: "#64748b", fontSize: 11 }}>3-Tier Privacy Tier:</div>
                  <span style={{
                    fontSize: 11,
                    padding: "2px 6px",
                    borderRadius: 4,
                    background: selectedEntity.sensitivity === "confidential" ? "rgba(239, 68, 68, 0.2)" : "rgba(59, 130, 246, 0.2)",
                    color: selectedEntity.sensitivity === "confidential" ? "#f87171" : "#60a5fa"
                  }}>
                    {selectedEntity.sensitivity}
                  </span>
                </div>
              )}

              {selectedEntity.time && (
                <div>
                  <div style={{ color: "#64748b", fontSize: 11 }}>Timestamp:</div>
                  <div style={{ color: "#94a3b8", fontSize: 11.5 }}>{selectedEntity.time}</div>
                </div>
              )}

              {selectedEntity.interaction_type && (
                <div>
                  <div style={{ color: "#64748b", fontSize: 11 }}>Interaction Type:</div>
                  <div style={{ color: "#38bdf8", fontWeight: 600 }}>{selectedEntity.interaction_type}</div>
                </div>
              )}

              {selectedEntity.message_preview && (
                <div>
                  <div style={{ color: "#64748b", fontSize: 11 }}>Message Content Preview:</div>
                  <div style={{ background: "#111827", padding: 8, borderRadius: 6, color: "#e2e8f0", fontSize: 12, marginTop: 4 }}>
                    "{selectedEntity.message_preview}"
                  </div>
                </div>
              )}

              {/* Complete JSON Attributes */}
              <div style={{ marginTop: 8, borderTop: "1px solid #1f2937", paddingTop: 8 }}>
                <div style={{ color: "#64748b", fontSize: 11, marginBottom: 4 }}>Raw Node Properties:</div>
                <div style={{ background: "#111827", padding: 8, borderRadius: 6, maxHeight: 180, overflowY: "auto" }}>
                  <pre style={{ color: "#94a3b8", fontSize: 11, margin: 0, fontFamily: "monospace" }}>
                    {JSON.stringify(selectedEntity, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ==============================================================================
// 1. EXECUTION GRAPH (GE) VISUAL TOPOLOGY COMPONENT
// ==============================================================================
function ExecutionGraphTopology({ nodes = [], edges = [], onSelectNode, onSelectEdge }) {
  if (nodes.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: "48px 20px", color: "#64748b" }}>
        <Activity size={36} color="#334155" style={{ marginBottom: 12 }} />
        <div style={{ fontSize: 15, color: "#cbd5e1", fontWeight: 600 }}>No Execution Events Recorded for this Workflow</div>
        <div style={{ fontSize: 12.5, color: "#64748b", marginTop: 4 }}>
          Click "⚡ Run Sample Multi-Agent Investigation" above to execute and stream live tool execution events.
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12.5, color: "#94a3b8" }}>
        <span>Causal Pipeline of Tool Invocations &bull; Sequence Ordered by Execution Time</span>
        <span style={{ color: "#34d399", fontWeight: 600 }}>{nodes.length} Executed Tool Calls</span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {nodes.map((node, idx) => {
          const agentKey = node.agent_id || "agent_researcher";
          const agentMeta = AGENT_COLORS[agentKey] || { border: "#60a5fa", bg: "rgba(96, 165, 250, 0.15)", text: "#93c5fd", label: agentKey };
          const isSuccess = node.outcome === "success" || !node.outcome;

          return (
            <div key={node.id || idx}>
              <div
                onClick={() => onSelectNode && onSelectNode(node)}
                style={{
                  background: "#0b0f19",
                  border: `1px solid #f59e0b`,
                  borderRadius: 8,
                  padding: "12px 16px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <div
                    style={{
                      width: 28,
                      height: 28,
                      borderRadius: "50%",
                      background: "rgba(245, 158, 11, 0.15)",
                      border: `1px solid #f59e0b`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 12,
                      fontWeight: 700,
                      color: "#fbbf24",
                    }}
                  >
                    {idx + 1}
                  </div>

                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: 13, fontWeight: 700, color: "#f8fafc" }}>
                        {node.tool_name || "Tool Call"}: <code>{node.tool_operation || node.action_semantic || "operation"}</code>
                      </span>
                      <span style={{ fontSize: 11, padding: "1px 6px", borderRadius: 4, background: agentMeta.bg, color: agentMeta.text, border: `1px solid ${agentMeta.border}` }}>
                        {agentMeta.label}
                      </span>
                    </div>

                    <div style={{ fontSize: 11.5, color: "#94a3b8", marginTop: 4, display: "flex", gap: 12 }}>
                      <span>Target: <code style={{ color: "#2dd4bf" }}>{node.resource_id || "resource"}</code></span>
                      <span>Delegation Token: <code style={{ color: "#34d399" }}>{(node.delegation_id || "").substring(0, 14)}...</code></span>
                      {node.time && <span>Time: {new Date(node.time).toLocaleTimeString()}</span>}
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                    fontSize: 12,
                    color: isSuccess ? "#34d399" : "#f87171",
                    fontWeight: 600
                  }}>
                    {isSuccess ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
                    <span>{isSuccess ? "Success" : "Failed"}</span>
                  </div>
                  <ArrowRight size={15} color="#475569" />
                </div>
              </div>

              {/* Connecting Downward Causal Arrow */}
              {idx < nodes.length - 1 && (
                <div style={{ display: "flex", justifyContent: "center", margin: "4px 0" }}>
                  <div style={{ width: 2, height: 14, background: "#334155" }} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ==============================================================================
// 2. AUTHORITY GRAPH (GA) VISUAL TOPOLOGY COMPONENT
// ==============================================================================
function AuthorityGraphTopology({ nodes = [], edges = [], onSelectNode, onSelectEdge }) {
  if (nodes.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: "48px 20px", color: "#64748b" }}>
        <Key size={36} color="#334155" style={{ marginBottom: 12 }} />
        <div style={{ fontSize: 15, color: "#cbd5e1", fontWeight: 600 }}>No Authority Lineage Recorded for this Workflow</div>
        <div style={{ fontSize: 12.5, color: "#64748b", marginTop: 4 }}>
          Click "⚡ Run Sample Multi-Agent Investigation" to generate cryptographic delegation tokens and lineage trees.
        </div>
      </div>
    );
  }

  // Group nodes by type
  const principals = nodes.filter((n) => n.node_type === "principal" || n.id?.startsWith("prin_"));
  const delegations = nodes.filter((n) => n.node_type === "delegation" || n.id?.startsWith("del_"));
  const agents = nodes.filter((n) => n.node_type === "agent" || n.id?.startsWith("agent_"));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12.5, color: "#94a3b8" }}>
        <span>Hierarchical Cryptographic Delegation Lineage &bull; Verified W3C PROV Invariant</span>
        <span style={{ color: "#a78bfa", fontWeight: 600 }}>{delegations.length} Verified Delegation Tokens</span>
      </div>

      {/* Visual Tree Levels */}
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Tier 1: User Principal (Origin of Authority) */}
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", textTransform: "uppercase", marginBottom: 8, letterSpacing: "0.05em" }}>
            Level 1: Root Authority Origin (User Principal)
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
            {principals.map((p, idx) => (
              <div
                key={p.id || idx}
                onClick={() => onSelectNode && onSelectNode(p)}
                style={{
                  background: "rgba(232, 164, 74, 0.12)",
                  border: "1px solid #e8a44a",
                  borderRadius: 8,
                  padding: "10px 16px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                }}
              >
                <Shield size={18} color="#e8a44a" />
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "#e8a44a" }}>
                    Principal: {p.entity_id || p.label || "Human User"}
                  </div>
                  <div style={{ fontSize: 11, color: "#fde68a" }}>Root Authority Signer</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Downward Hierarchy Link */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#64748b", fontSize: 12 }}>
          <div style={{ flex: 1, height: 1, background: "#1f2937" }} />
          <span>Delegates Authority to Lead Agent</span>
          <div style={{ flex: 1, height: 1, background: "#1f2937" }} />
        </div>

        {/* Tier 2: Delegation Tokens Granted */}
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", textTransform: "uppercase", marginBottom: 8, letterSpacing: "0.05em" }}>
            Level 2: Active Delegation Scopes & Tokens
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 10 }}>
            {delegations.map((d, idx) => (
              <div
                key={d.id || idx}
                onClick={() => onSelectNode && onSelectNode(d)}
                style={{
                  background: "#0b0f19",
                  border: "1px solid #34d399",
                  borderRadius: 6,
                  padding: "10px 14px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Key size={14} color="#34d399" />
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "#e2e8f0" }}>
                      <code>{(d.id || d.label || "").substring(0, 16)}</code>
                    </div>
                    <div style={{ fontSize: 11, color: "#94a3b8" }}>Scope: {d.scope || "Tool Execution Granted"}</div>
                  </div>
                </div>
                <span style={{ fontSize: 10, background: "rgba(52, 211, 153, 0.2)", color: "#34d399", padding: "2px 5px", borderRadius: 4 }}>
                  Valid
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Tier 3: Authorized Agents Hierarchy */}
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", textTransform: "uppercase", marginBottom: 8, letterSpacing: "0.05em" }}>
            Level 3: Authorized Multi-Agent Fleet
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 10 }}>
            {agents.map((a, idx) => {
              const agentKey = a.entity_id || a.agent_id || a.id?.replace("agent_", "") || "agent_coordinator";
              const meta = AGENT_COLORS[agentKey] || { border: "#60a5fa", bg: "rgba(96, 165, 250, 0.15)", text: "#93c5fd", label: a.label || agentKey };

              return (
                <div
                  key={a.id || idx}
                  onClick={() => onSelectNode && onSelectNode(a)}
                  style={{
                    background: "#0b0f19",
                    border: `1px solid #60a5fa`,
                    borderRadius: 6,
                    padding: "10px 14px",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                  }}
                >
                  <Bot size={18} color="#60a5fa" />
                  <div>
                    <div style={{ fontSize: 12.5, fontWeight: 700, color: "#f8fafc" }}>{meta.label}</div>
                    <div style={{ fontSize: 11, color: "#60a5fa" }}>Authorized Delegatee</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ==============================================================================
// 3. UNIFIED "3-IN-1" CORRELATED MULTI-GRAPH COMPONENT
// ==============================================================================
function UnifiedThreeGraphView({ execNodes = [], authNodes = [], itrEdges = [], itrNodes = [], onSelectNode, onSelectEdge }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <div style={{ background: "#0b0f19", border: "1px solid #1e293b", borderLeft: "4px solid #f59e0b", borderRadius: 6, padding: "12px 16px", fontSize: 12.5, color: "#cbd5e1" }}>
        <strong>🔗 The Three-Graph Unified Correlation Invariant:</strong> Multi-agent operations require three orthogonal perspectives. Below, observe how each <strong>Agent Communication (GI)</strong> authoritatively bounds a <strong>Delegation Token (GA)</strong>, which safely permits the downstream <strong>Tool Execution Event (GE)</strong>.
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
        {/* Column 1: Communication (GI) */}
        <div style={{ background: "#0b0f19", border: "1px solid #1f2937", borderRadius: 8, padding: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#38bdf8", fontWeight: 700, fontSize: 13, marginBottom: 12 }}>
            <Share2 size={16} />
            <span>1. Communication (GI)</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {itrEdges.length > 0 ? (
              itrEdges.slice(0, 5).map((e, idx) => (
                <div
                  key={idx}
                  onClick={() => onSelectEdge && onSelectEdge(e, "Interaction Event")}
                  style={{
                    background: "#111827",
                    border: "1px solid #334155",
                    borderRadius: 6,
                    padding: "8px 10px",
                    fontSize: 11.5,
                    cursor: "pointer",
                  }}
                >
                  <div style={{ color: "#38bdf8", fontWeight: 600 }}>{e.source} &rarr; {e.target}</div>
                  <div style={{ color: "#94a3b8", fontSize: 11, marginTop: 2 }}>{e.interaction_type || "Task Delegation"}</div>
                </div>
              ))
            ) : (
              <div style={{ color: "#64748b", fontSize: 12 }}>{itrNodes.length} Agents Registered in Communication Graph</div>
            )}
          </div>
        </div>

        {/* Column 2: Authority Lineage (GA) */}
        <div style={{ background: "#0b0f19", border: "1px solid #1f2937", borderRadius: 8, padding: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#34d399", fontWeight: 700, fontSize: 13, marginBottom: 12 }}>
            <Key size={16} />
            <span>2. Authority Scope (GA)</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {authNodes.slice(0, 5).map((n, idx) => (
              <div
                key={idx}
                onClick={() => onSelectNode && onSelectNode(n, "Authority Node")}
                style={{
                  background: "#111827",
                  border: "1px solid #34d399",
                  borderRadius: 6,
                  padding: "8px 10px",
                  fontSize: 11.5,
                  cursor: "pointer",
                }}
              >
                <div style={{ color: "#34d399", fontWeight: 600 }}><code>{(n.id || "").substring(0, 20)}</code></div>
                <div style={{ color: "#94a3b8", fontSize: 11, marginTop: 2 }}>Type: {n.node_type || "Delegation Token"}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Column 3: Tool Execution (GE) */}
        <div style={{ background: "#0b0f19", border: "1px solid #1f2937", borderRadius: 8, padding: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#f59e0b", fontWeight: 700, fontSize: 13, marginBottom: 12 }}>
            <Activity size={16} />
            <span>3. Tool Execution (GE)</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {execNodes.slice(0, 5).map((ev, idx) => (
              <div
                key={idx}
                onClick={() => onSelectNode && onSelectNode(ev, "Execution Event")}
                style={{
                  background: "#111827",
                  border: "1px solid #f59e0b",
                  borderRadius: 6,
                  padding: "8px 10px",
                  fontSize: 11.5,
                  cursor: "pointer",
                }}
              >
                <div style={{ color: "#34d399", fontWeight: 600 }}>{ev.tool_name}: {ev.tool_operation || ev.action_semantic}</div>
                <div style={{ color: "#94a3b8", fontSize: 11, marginTop: 2 }}>Agent: {ev.agent_id}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
