import React, { useState, useEffect, useRef } from "react";
import {
  Bot,
  ArrowRight,
  Play,
  Pause,
  RotateCcw,
  Shield,
  Zap,
  CheckCircle2,
  MessageSquare,
  Share2,
  Key,
  Clock,
  Sparkles,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

// Known agent visual metadata & coordinate anchors for intuitive topology
const AGENT_META = {
  agent_coordinator: {
    label: "Agent A: Coordinator",
    role: "Lead Orchestrator & Delegator",
    model: "meta-llama/Llama-3.1-8B",
    color: "#3b82f6",
    fillColor: "rgba(59, 130, 246, 0.15)",
    borderColor: "#60a5fa",
    x: 350,
    y: 75,
  },
  Coordinator_Agent: {
    label: "Coordinator Agent",
    role: "Lead Orchestrator & Delegator",
    model: "meta-llama/Llama-3.1-8B",
    color: "#3b82f6",
    fillColor: "rgba(59, 130, 246, 0.15)",
    borderColor: "#60a5fa",
    x: 350,
    y: 75,
  },
  agent_researcher: {
    label: "Agent B: Researcher",
    role: "Dataset Extraction & CIM Tools",
    model: "Qwen/Qwen2.5-7B",
    color: "#10b981",
    fillColor: "rgba(16, 185, 129, 0.15)",
    borderColor: "#34d399",
    x: 130,
    y: 240,
  },
  Executor_Agent: {
    label: "Executor Agent",
    role: "Technical Execution & Tools",
    model: "Qwen/Qwen2.5-7B",
    color: "#10b981",
    fillColor: "rgba(16, 185, 129, 0.15)",
    borderColor: "#34d399",
    x: 130,
    y: 240,
  },
  agent_analyst: {
    label: "Agent C: Analyst",
    role: "Anomaly & Statistical Evaluation",
    model: "mistralai/Mistral-7B",
    color: "#f59e0b",
    fillColor: "rgba(245, 158, 11, 0.15)",
    borderColor: "#fbbf24",
    x: 570,
    y: 240,
  },
  Critic_Agent: {
    label: "Critic Agent",
    role: "Vulnerability & Reasoning Audit",
    model: "mistralai/Mistral-7B",
    color: "#f59e0b",
    fillColor: "rgba(245, 158, 11, 0.15)",
    borderColor: "#fbbf24",
    x: 570,
    y: 240,
  },
  agent_reporter: {
    label: "Agent D: Reporter",
    role: "Consensus Formulation & Output",
    model: "google/gemma-2-9b",
    color: "#ec4899",
    fillColor: "rgba(236, 72, 153, 0.15)",
    borderColor: "#f472b6",
    x: 350,
    y: 395,
  },
  Synthesizer_Agent: {
    label: "Synthesizer Agent",
    role: "Consensus Formulation & Output",
    model: "google/gemma-2-9b",
    color: "#ec4899",
    fillColor: "rgba(236, 72, 153, 0.15)",
    borderColor: "#f472b6",
    x: 350,
    y: 395,
  },
};

const DEFAULT_META = {
  label: "Agent Node",
  role: "Autonomous Agent",
  model: "Neural LLM",
  color: "#8b5cf6",
  fillColor: "rgba(139, 92, 246, 0.15)",
  borderColor: "#a78bfa",
};

export default function AgentInteractionGraph({
  graph,
  interactions = [],
  workflowId,
  title = "Agent Interaction Graph (How Agents Communicated)",
  compact = false,
}) {
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [activeStepIdx, setActiveStepIdx] = useState(null);
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Parse nodes & edges safely
  const nodes = graph?.nodes || [];
  const edges = graph?.edges || [];

  // Compute positions dynamically if not in AGENT_META
  const nodePositions = React.useMemo(() => {
    const pos = {};
    const unanchored = [];

    nodes.forEach((n) => {
      const id = n.id || n.agent_id || n.name;
      if (AGENT_META[id]) {
        pos[id] = { ...AGENT_META[id], ...n };
      } else {
        unanchored.push({ ...n, id });
      }
    });

    if (unanchored.length > 0) {
      const count = unanchored.length;
      const cx = 350;
      const cy = 240;
      const rx = 240;
      const ry = 160;

      unanchored.forEach((n, idx) => {
        const angle = (idx / count) * 2 * Math.PI - Math.PI / 2;
        pos[n.id] = {
          ...DEFAULT_META,
          ...n,
          label: n.label || n.id,
          x: cx + rx * Math.cos(angle),
          y: cy + ry * Math.sin(angle),
        };
      });
    }

    return pos;
  }, [nodes]);

  // Order interactions sequentially for step-by-step playback
  const chronologicalSteps = React.useMemo(() => {
    if (edges.length > 0) {
      return [...edges].sort((a, b) => {
        const tA = a.timestamp || "";
        const tB = b.timestamp || "";
        return tA.localeCompare(tB);
      });
    }
    return [];
  }, [edges]);

  // Auto-play replay animation loop
  useEffect(() => {
    let timer;
    if (isPlaying && chronologicalSteps.length > 0) {
      timer = setInterval(() => {
        setActiveStepIdx((prev) => {
          if (prev === null || prev >= chronologicalSteps.length - 1) {
            return 0;
          }
          return prev + 1;
        });
      }, 1500);
    }
    return () => clearInterval(timer);
  }, [isPlaying, chronologicalSteps.length]);

  // Automatically select the active step edge when activeStepIdx changes
  useEffect(() => {
    if (activeStepIdx !== null && chronologicalSteps[activeStepIdx]) {
      setSelectedEdge(chronologicalSteps[activeStepIdx]);
    }
  }, [activeStepIdx, chronologicalSteps]);

  if (!nodes || nodes.length === 0) {
    return null;
  }

  // Calculate curved SVG path with directional curvature
  const calculatePath = (srcId, tgtId, edgeIdx = 0, totalParallel = 1) => {
    const src = nodePositions[srcId] || { x: 200, y: 200 };
    const tgt = nodePositions[tgtId] || { x: 500, y: 200 };

    const dx = tgt.x - src.x;
    const dy = tgt.y - src.y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;

    // Normal vector for curve offset
    const nx = -dy / dist;
    const ny = dx / dist;

    // Arc curvature: offset depends on edge direction to separate opposing flows
    const curvature = 36 * (edgeIdx % 2 === 0 ? 1 : -1) * (1 + Math.floor(edgeIdx / 2) * 0.4);

    const midX = (src.x + tgt.x) / 2 + nx * curvature;
    const midY = (src.y + tgt.y) / 2 + ny * curvature;

    return {
      d: `M ${src.x} ${src.y} Q ${midX} ${midY} ${tgt.x} ${tgt.y}`,
      midX,
      midY,
    };
  };

  const getEdgeColor = (type, isHighlighted) => {
    if (isHighlighted) return "#38bdf8";
    const t = (type || "").toLowerCase();
    if (t.includes("delegat")) return "#60a5fa"; // blue
    if (t.includes("finding") || t.includes("data") || t.includes("response")) return "#10b981"; // emerald
    if (t.includes("analys") || t.includes("audit") || t.includes("critic")) return "#f59e0b"; // amber
    if (t.includes("report") || t.includes("synth")) return "#ec4899"; // pink
    return "#94a3b8";
  };

  return (
    <div
      style={{
        marginTop: 14,
        background: "#080c14",
        border: "1px solid rgba(59, 130, 246, 0.35)",
        borderRadius: 12,
        padding: compact ? "12px 14px" : "18px 20px",
        boxShadow: "0 8px 30px rgba(0, 0, 0, 0.5)",
      }}
    >
      {/* Header bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: isCollapsed ? 0 : 12,
          paddingBottom: isCollapsed ? 0 : 10,
          borderBottom: isCollapsed ? "none" : "1px solid #1e293b",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: "50%",
              background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
            }}
          >
            <Share2 size={16} />
          </div>
          <div>
            <h4
              style={{
                margin: 0,
                fontSize: compact ? 13.5 : 15,
                fontWeight: 700,
                color: "#60a5fa",
                letterSpacing: "0.2px",
              }}
            >
              {title}
            </h4>
            <span style={{ fontSize: 11, color: "#94a3b8" }}>
              {nodes.length} Agent Nodes &bull; {edges.length} Observed Communication Messages &bull; Verified CIM Invariants
            </span>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {edges.length > 0 && (
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                padding: "4px 10px",
                background: isPlaying ? "#059669" : "#1e293b",
                border: "1px solid rgba(255,255,255,0.15)",
                borderRadius: 6,
                color: "#fff",
                fontSize: 11,
                fontWeight: 600,
                cursor: "pointer",
              }}
              title={isPlaying ? "Pause Flow Replay" : "Replay Agent-to-Agent Communication Flow"}
            >
              {isPlaying ? <Pause size={12} /> : <Play size={12} />}
              <span>{isPlaying ? "Pause Flow" : "Replay Flow"}</span>
            </button>
          )}

          <button
            onClick={() => {
              setActiveStepIdx(null);
              setSelectedEdge(null);
              setSelectedNode(null);
              setIsPlaying(false);
            }}
            style={{
              padding: "4px 8px",
              background: "#1e293b",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 6,
              color: "#94a3b8",
              fontSize: 11,
              cursor: "pointer",
            }}
            title="Reset Graph Selection"
          >
            <RotateCcw size={12} />
          </button>

          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            style={{
              padding: "4px 8px",
              background: "#1e293b",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 6,
              color: "#94a3b8",
              cursor: "pointer",
            }}
          >
            {isCollapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <>
          {/* Chronological Step Sequence Ribbon */}
          {chronologicalSteps.length > 0 && (
            <div
              style={{
                display: "flex",
                gap: 6,
                overflowX: "auto",
                paddingBottom: 8,
                marginBottom: 10,
                alignItems: "center",
              }}
            >
              <span style={{ fontSize: 10, textTransform: "uppercase", color: "#64748b", fontWeight: 700, minWidth: 42 }}>
                Steps:
              </span>
              {chronologicalSteps.map((step, idx) => {
                const isActive = activeStepIdx === idx || selectedEdge?.key === step.key;
                const src = nodePositions[step.source]?.label?.split(":")[0] || step.source?.replace("agent_", "");
                const tgt = nodePositions[step.target]?.label?.split(":")[0] || step.target?.replace("agent_", "");
                return (
                  <button
                    key={step.key || idx}
                    onClick={() => {
                      setActiveStepIdx(idx);
                      setSelectedEdge(step);
                      setSelectedNode(null);
                    }}
                    style={{
                      flexShrink: 0,
                      padding: "3px 8px",
                      borderRadius: 14,
                      fontSize: 10.5,
                      fontWeight: 600,
                      background: isActive ? "linear-gradient(135deg, #2563eb, #3b82f6)" : "#131b2e",
                      border: isActive ? "1px solid #60a5fa" : "1px solid #1e293b",
                      color: isActive ? "#fff" : "#94a3b8",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: 4,
                      boxShadow: isActive ? "0 0 10px rgba(59, 130, 246, 0.5)" : "none",
                    }}
                  >
                    <span>#{idx + 1}</span>
                    <span>{src} &rarr; {tgt}</span>
                  </button>
                );
              })}
            </div>
          )}

          {/* SVG Canvas */}
          <div
            style={{
              position: "relative",
              width: "100%",
              height: compact ? 340 : 460,
              background: "radial-gradient(ellipse at 50% 50%, #0e1726 0%, #06090f 100%)",
              borderRadius: 10,
              border: "1px solid #1e293b",
              overflow: "hidden",
            }}
          >
            <svg
              viewBox="0 0 700 480"
              style={{ width: "100%", height: "100%", display: "block" }}
            >
              <defs>
                {/* Glow filter */}
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>

                {/* Arrow markers for edges */}
                <marker
                  id="arrow-default"
                  viewBox="0 0 10 10"
                  refX="38"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#60a5fa" />
                </marker>
                <marker
                  id="arrow-active"
                  viewBox="0 0 10 10"
                  refX="38"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#38bdf8" />
                </marker>
                <marker
                  id="arrow-emerald"
                  viewBox="0 0 10 10"
                  refX="38"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#10b981" />
                </marker>
                <marker
                  id="arrow-amber"
                  viewBox="0 0 10 10"
                  refX="38"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#f59e0b" />
                </marker>
              </defs>

              {/* Grid Background lines */}
              <g stroke="rgba(255, 255, 255, 0.03)" strokeWidth="1">
                {Array.from({ length: 14 }).map((_, i) => (
                  <line key={`v-${i}`} x1={i * 50} y1="0" x2={i * 50} y2="480" />
                ))}
                {Array.from({ length: 10 }).map((_, i) => (
                  <line key={`h-${i}`} x1="0" y1={i * 50} x2="700" y2={i * 50} />
                ))}
              </g>

              {/* Interaction Edges (Drawn First behind Nodes) */}
              {edges.map((edge, idx) => {
                const isSelected = selectedEdge?.key === edge.key || activeStepIdx === idx;
                const pathData = calculatePath(edge.source, edge.target, idx, edges.length);
                const edgeColor = getEdgeColor(edge.interaction_type, isSelected);

                return (
                  <g
                    key={edge.key || idx}
                    onClick={() => {
                      setSelectedEdge(edge);
                      setActiveStepIdx(idx);
                      setSelectedNode(null);
                    }}
                    style={{ cursor: "pointer" }}
                  >
                    {/* Invisible fat hit area for easy hover/clicking */}
                    <path
                      d={pathData.d}
                      fill="none"
                      stroke="transparent"
                      strokeWidth="20"
                    />

                    {/* Edge shadow / outer glow */}
                    {isSelected && (
                      <path
                        d={pathData.d}
                        fill="none"
                        stroke={edgeColor}
                        strokeWidth="7"
                        opacity="0.3"
                        filter="url(#glow)"
                      />
                    )}

                    {/* Base Edge Line */}
                    <path
                      d={pathData.d}
                      fill="none"
                      stroke={edgeColor}
                      strokeWidth={isSelected ? "3" : "1.8"}
                      strokeOpacity={isSelected ? 1 : 0.65}
                      strokeDasharray={isSelected ? "8 4" : "5 5"}
                      markerEnd="url(#arrow-default)"
                    />

                    {/* Step sequence badge on the midpoint */}
                    <g transform={`translate(${pathData.midX}, ${pathData.midY})`}>
                      <circle
                        r={isSelected ? 11 : 9}
                        fill={isSelected ? "#38bdf8" : "#0f172a"}
                        stroke={edgeColor}
                        strokeWidth="1.5"
                      />
                      <text
                        textAnchor="middle"
                        dy="3.5"
                        fill={isSelected ? "#000" : "#fff"}
                        fontSize="9.5"
                        fontWeight="bold"
                        fontFamily="sans-serif"
                      >
                        {idx + 1}
                      </text>
                    </g>
                  </g>
                );
              })}

              {/* Agent Nodes */}
              {Object.entries(nodePositions).map(([id, node]) => {
                const isSelected = selectedNode?.id === id;
                const isConnected =
                  selectedEdge?.source === id || selectedEdge?.target === id;

                return (
                  <g
                    key={id}
                    transform={`translate(${node.x}, ${node.y})`}
                    onClick={() => {
                      setSelectedNode(node);
                      setSelectedEdge(null);
                    }}
                    style={{ cursor: "pointer" }}
                  >
                    {/* Node glow when active or selected */}
                    {(isSelected || isConnected) && (
                      <rect
                        x="-88"
                        y="-40"
                        width="176"
                        height="80"
                        rx="14"
                        fill="none"
                        stroke={node.color || "#3b82f6"}
                        strokeWidth="5"
                        opacity="0.4"
                        filter="url(#glow)"
                      />
                    )}

                    {/* Main Node Box */}
                    <rect
                      x="-84"
                      y="-36"
                      width="168"
                      height="72"
                      rx="12"
                      fill="#0f172a"
                      stroke={isSelected || isConnected ? "#38bdf8" : node.borderColor || "#334155"}
                      strokeWidth={isSelected || isConnected ? "2.5" : "1.5"}
                    />

                    {/* Header gradient banner */}
                    <rect
                      x="-83"
                      y="-35"
                      width="166"
                      height="26"
                      rx="10"
                      fill={node.fillColor || "rgba(59, 130, 246, 0.15)"}
                    />

                    {/* Pulse status indicator */}
                    <circle cx="-66" cy="-22" r="4" fill="#10b981" />
                    <circle cx="-66" cy="-22" r="7" fill="#10b981" opacity="0.25" />

                    {/* Agent Name */}
                    <text
                      x="-54"
                      y="-18"
                      fill="#f8fafc"
                      fontSize="11"
                      fontWeight="700"
                      fontFamily="system-ui, sans-serif"
                    >
                      {node.label?.split(":")[0] || node.id?.replace("agent_", "")}
                    </text>

                    {/* Role Description */}
                    <text
                      x="0"
                      y="6"
                      textAnchor="middle"
                      fill="#94a3b8"
                      fontSize="9.5"
                      fontFamily="system-ui, sans-serif"
                    >
                      {node.role?.length > 25 ? node.role.substring(0, 23) + "..." : node.role}
                    </text>

                    {/* Model Pill Badge */}
                    <g transform="translate(0, 22)">
                      <rect
                        x="-60"
                        y="-8"
                        width="120"
                        height="16"
                        rx="8"
                        fill="#1e293b"
                        stroke="rgba(255, 255, 255, 0.1)"
                        strokeWidth="1"
                      />
                      <text
                        x="0"
                        y="4"
                        textAnchor="middle"
                        fill="#cbd5e1"
                        fontSize="8.5"
                        fontFamily="monospace"
                        fontWeight="600"
                      >
                        {node.model?.split("/")[1] || node.model?.substring(0, 16) || "Agent"}
                      </text>
                    </g>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Bottom Interactive Inspector for Selected Edge or Node */}
          {(selectedEdge || selectedNode) && (
            <div
              style={{
                marginTop: 10,
                background: "#0c1322",
                border: "1px solid #1e3a5f",
                borderRadius: 8,
                padding: "10px 14px",
                display: "grid",
                gridTemplateColumns: "1.4fr 1fr",
                gap: 12,
                fontSize: 12,
              }}
            >
              {selectedEdge ? (
                <>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                      <span
                        style={{
                          background: "#1e3a8a",
                          color: "#93c5fd",
                          padding: "2px 6px",
                          borderRadius: 4,
                          fontSize: 10,
                          fontWeight: 700,
                          textTransform: "uppercase",
                        }}
                      >
                        {selectedEdge.interaction_type || "Inter-Agent Message"}
                      </span>
                      <strong style={{ color: "#f8fafc" }}>
                        {selectedEdge.source?.replace("agent_", "")} &rarr; {selectedEdge.target?.replace("agent_", "")}
                      </strong>
                    </div>
                    <div style={{ color: "#cbd5e1", lineHeight: 1.4 }}>
                      {selectedEdge.semantic_summary || selectedEdge.label || "Communication payload delivered across the Observability Gateway."}
                    </div>
                  </div>
                  <div style={{ fontSize: 11, color: "#94a3b8", display: "flex", flexDirection: "column", gap: 2 }}>
                    <div>
                      <strong>Token:</strong> <code>{selectedEdge.delegation_id || "del_root"}</code>
                    </div>
                    <div>
                      <strong>Privacy:</strong> <span>Capture Level 2 (Summary &bull; Redacted)</span>
                    </div>
                    <div>
                      <strong>Timestamp:</strong> <span>{selectedEdge.timestamp?.split("T")[1]?.substring(0, 8) || "Recorded"}</span>
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <div style={{ color: "#60a5fa", fontWeight: 700, fontSize: 13, marginBottom: 2 }}>
                      {selectedNode.label || selectedNode.id}
                    </div>
                    <div style={{ color: "#cbd5e1" }}>
                      Role: <strong>{selectedNode.role}</strong>
                    </div>
                  </div>
                  <div style={{ fontSize: 11, color: "#94a3b8" }}>
                    <div>Model: <code>{selectedNode.model}</code></div>
                    <div>Authority: <span>Cryptographically Delegated</span></div>
                  </div>
                </>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
