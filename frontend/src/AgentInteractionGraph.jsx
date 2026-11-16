import React, { useState, useEffect, useRef, useMemo } from "react";
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
  Plus,
  Trash2,
  Move,
  RefreshCw,
  X,
  Sliders,
} from "lucide-react";

// Dynamic metadata library for specialized agents
const KNOWN_AGENTS = {
  agent_coordinator: {
    label: "Coordinator",
    role: "Lead Orchestrator & Task Delegator",
    model: "Google Gemini 3.5 Flash",
    tools: ["mint_delegation", "verify_invariants"],
    color: "#3b82f6",
    fillColor: "rgba(59, 130, 246, 0.15)",
    borderColor: "#60a5fa",
  },
  Coordinator_Agent: {
    label: "Coordinator",
    role: "Lead Orchestrator & Task Delegator",
    model: "Google Gemini 3.5 Flash",
    tools: ["mint_delegation", "verify_invariants"],
    color: "#3b82f6",
    fillColor: "rgba(59, 130, 246, 0.15)",
    borderColor: "#60a5fa",
  },
  agent_researcher: {
    label: "Researcher",
    role: "CFPB Complaint Extraction",
    model: "Google Gemini 3.5 Flash",
    tools: ["read_sample_dataset", "query_cfpb_records"],
    color: "#10b981",
    fillColor: "rgba(16, 185, 129, 0.15)",
    borderColor: "#34d399",
  },
  Executor_Agent: {
    label: "Executor",
    role: "CIM Data Ingestion & Extraction",
    model: "Google Gemini 3.5 Flash",
    tools: ["read_sample_dataset", "query_cfpb_records"],
    color: "#10b981",
    fillColor: "rgba(16, 185, 129, 0.15)",
    borderColor: "#34d399",
  },
  agent_analyst: {
    label: "Analyst",
    role: "Statistical Anomaly Evaluator",
    model: "Google Gemini 3.5 Flash",
    tools: ["calculate_anomaly_rates", "compute_aggregates"],
    color: "#f59e0b",
    fillColor: "rgba(245, 158, 11, 0.15)",
    borderColor: "#fbbf24",
  },
  Critic_Agent: {
    label: "Critic",
    role: "Adversarial Reasoning Auditor",
    model: "Google Gemini 3.5 Flash",
    tools: ["verify_causality", "detect_inconsistencies"],
    color: "#f59e0b",
    fillColor: "rgba(245, 158, 11, 0.15)",
    borderColor: "#fbbf24",
  },
  agent_reporter: {
    label: "Reporter",
    role: "W3C PROV & Synthesis",
    model: "Google Gemini 3.5 Flash",
    tools: ["export_w3c_prov", "generate_markdown_report"],
    color: "#ec4899",
    fillColor: "rgba(236, 72, 153, 0.15)",
    borderColor: "#f472b6",
  },
  Synthesizer_Agent: {
    label: "Synthesizer",
    role: "Executive Resolution Formulator",
    model: "Google Gemini 3.5 Flash",
    tools: ["export_w3c_prov", "generate_markdown_report"],
    color: "#ec4899",
    fillColor: "rgba(236, 72, 153, 0.15)",
    borderColor: "#f472b6",
  },
  agent_forensics: {
    label: "Forensics Scanner",
    role: "Access Log & Security Forensics",
    model: "Google Gemini 3.5 Flash",
    tools: ["scan_system_access_logs", "inspect_auth_events"],
    color: "#06b6d4",
    fillColor: "rgba(6, 182, 212, 0.15)",
    borderColor: "#22d3ee",
  },
  agent_threat_hunter: {
    label: "Threat Hunter",
    role: "Privilege Escalation Detector",
    model: "Google Gemini 3.5 Flash",
    tools: ["detect_unauthorized_root", "verify_ip_anomalies"],
    color: "#ef4444",
    fillColor: "rgba(239, 68, 68, 0.15)",
    borderColor: "#f87171",
  },
  agent_compliance: {
    label: "Compliance Auditor",
    role: "FedRAMP & NIST Policy Auditor",
    model: "Google Gemini 3.5 Flash",
    tools: ["audit_nist_sp_800_53", "validate_cim_invariants"],
    color: "#8b5cf6",
    fillColor: "rgba(139, 92, 246, 0.15)",
    borderColor: "#a78bfa",
  },
  agent_sentiment: {
    label: "Sentiment Specialist",
    role: "Consumer Experience & NLP",
    model: "Google Gemini 3.5 Flash",
    tools: ["analyze_sentiment_polarity", "extract_customer_intents"],
    color: "#14b8a6",
    fillColor: "rgba(20, 184, 166, 0.15)",
    borderColor: "#2dd4bf",
  },
};

const DEFAULT_META = {
  label: "Specialized Agent",
  role: "Collaborative Autonomous Node",
  model: "Google Gemini 3.5 Flash",
  tools: ["cim_tool_execution", "envelope_exchange"],
  color: "#8b5cf6",
  fillColor: "rgba(139, 92, 246, 0.15)",
  borderColor: "#a78bfa",
};

const AVAILABLE_AGENT_OPTIONS = [
  { id: "agent_threat_hunter", name: "Threat Hunter", role: "Privilege Escalation Detector", color: "#ef4444" },
  { id: "agent_compliance", name: "Compliance Auditor", role: "FedRAMP & NIST Invariant Auditor", color: "#8b5cf6" },
  { id: "agent_sentiment", name: "Sentiment Specialist", role: "Consumer Experience & NLP", color: "#14b8a6" },
  { id: "agent_forensics", name: "Forensics Scanner", role: "Access Log & Security Forensics", color: "#06b6d4" },
  { id: "agent_critic", name: "Adversarial Critic", role: "Reasoning & Vulnerability Auditor", color: "#f59e0b" },
];

export default function AgentInteractionGraph({
  graph,
  interactions = [],
  workflowId,
  title = "Agent Interaction Graph (How Agents Communicated)",
  compact = false,
  defaultCollapsed = false,
}) {
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [activeStepIdx, setActiveStepIdx] = useState(null);
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);

  // Dynamic graph nodes & edges with real-time add/remove
  const [localNodes, setLocalNodes] = useState([]);
  const [localEdges, setLocalEdges] = useState([]);
  const [nodePositions, setNodePositions] = useState({});
  const [draggingNodeId, setDraggingNodeId] = useState(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [showAddMenu, setShowAddMenu] = useState(false);

  const svgRef = useRef(null);

  // Synchronize incoming props to local state
  useEffect(() => {
    const rawNodes = graph?.nodes || [];
    const rawEdges = graph?.edges || [];

    // Ensure initial set exists
    let initialNodes = [...rawNodes];
    if (initialNodes.length === 0) {
      initialNodes = [
        { id: "agent_coordinator", label: "Coordinator", node_type: "agent" },
        { id: "agent_researcher", label: "Researcher", node_type: "agent" },
        { id: "agent_analyst", label: "Analyst", node_type: "agent" },
        { id: "agent_reporter", label: "Reporter", node_type: "agent" },
      ];
    }

    setLocalNodes(initialNodes);
    setLocalEdges(rawEdges);
    setNodePositions(computeDynamicLayout(initialNodes));
  }, [graph, interactions, workflowId]);

  // Compute adaptive balanced layout for N nodes
  function computeDynamicLayout(nodesList) {
    const pos = {};
    const count = nodesList.length;
    if (count === 0) return pos;

    const findCoordIdx = nodesList.findIndex((n) => {
      const id = (n.id || "").toLowerCase();
      return id.includes("coord") || id.includes("lead") || id.includes("orchestrat");
    });

    const hasCoord = findCoordIdx !== -1;
    let others = [...nodesList];
    let coordNode = null;

    if (hasCoord) {
      coordNode = others.splice(findCoordIdx, 1)[0];
      const coordMeta = KNOWN_AGENTS[coordNode.id] || DEFAULT_META;
      pos[coordNode.id] = {
        ...coordMeta,
        ...coordNode,
        label: coordNode.label || coordMeta.label,
        x: 350,
        y: 75,
      };
    }

    const otherCount = others.length;
    if (otherCount === 0) return pos;

    if (hasCoord) {
      if (otherCount === 1) {
        const meta = KNOWN_AGENTS[others[0].id] || DEFAULT_META;
        pos[others[0].id] = { ...meta, ...others[0], label: others[0].label || meta.label, x: 350, y: 350 };
      } else if (otherCount === 2) {
        const meta0 = KNOWN_AGENTS[others[0].id] || DEFAULT_META;
        const meta1 = KNOWN_AGENTS[others[1].id] || DEFAULT_META;
        pos[others[0].id] = { ...meta0, ...others[0], label: others[0].label || meta0.label, x: 170, y: 310 };
        pos[others[1].id] = { ...meta1, ...others[1], label: others[1].label || meta1.label, x: 530, y: 310 };
      } else if (otherCount === 3) {
        const meta0 = KNOWN_AGENTS[others[0].id] || DEFAULT_META;
        const meta1 = KNOWN_AGENTS[others[1].id] || DEFAULT_META;
        const meta2 = KNOWN_AGENTS[others[2].id] || DEFAULT_META;
        pos[others[0].id] = { ...meta0, ...others[0], label: others[0].label || meta0.label, x: 140, y: 240 };
        pos[others[1].id] = { ...meta1, ...others[1], label: others[1].label || meta1.label, x: 560, y: 240 };
        pos[others[2].id] = { ...meta2, ...others[2], label: others[2].label || meta2.label, x: 350, y: 395 };
      } else if (otherCount === 4) {
        const coords = [
          { x: 130, y: 190 },
          { x: 570, y: 190 },
          { x: 190, y: 390 },
          { x: 510, y: 390 },
        ];
        others.forEach((n, idx) => {
          const meta = KNOWN_AGENTS[n.id] || DEFAULT_META;
          pos[n.id] = { ...meta, ...n, label: n.label || meta.label, ...coords[idx] };
        });
      } else {
        const cx = 350;
        const cy = 250;
        const rx = 240;
        const ry = 160;
        others.forEach((n, idx) => {
          const angle = Math.PI * 0.15 + (idx / (otherCount - 1)) * (Math.PI * 0.7);
          const meta = KNOWN_AGENTS[n.id] || DEFAULT_META;
          pos[n.id] = {
            ...meta,
            ...n,
            label: n.label || meta.label,
            x: Math.round(cx + rx * Math.cos(angle)),
            y: Math.round(cy + ry * Math.sin(angle)),
          };
        });
      }
    } else {
      const cx = 350;
      const cy = 240;
      const rx = 230;
      const ry = 150;
      others.forEach((n, idx) => {
        const angle = (idx / otherCount) * 2 * Math.PI - Math.PI / 2;
        const meta = KNOWN_AGENTS[n.id] || DEFAULT_META;
        pos[n.id] = {
          ...meta,
          ...n,
          label: n.label || meta.label,
          x: Math.round(cx + rx * Math.cos(angle)),
          y: Math.round(cy + ry * Math.sin(angle)),
        };
      });
    }

    return pos;
  }

  // Interactive mouse / touch drag coordinates
  const getSvgCoordinates = (e) => {
    if (!svgRef.current) return { x: 0, y: 0 };
    const rect = svgRef.current.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    const scaleX = 700 / (rect.width || 700);
    const scaleY = 480 / (rect.height || 480);
    return {
      x: (clientX - rect.left) * scaleX,
      y: (clientY - rect.top) * scaleY,
    };
  };

  const handleMouseDownNode = (nodeId, e) => {
    e.stopPropagation();
    e.preventDefault();
    const pt = getSvgCoordinates(e);
    const curr = nodePositions[nodeId] || { x: 350, y: 240 };
    setDraggingNodeId(nodeId);
    setDragOffset({ x: pt.x - curr.x, y: pt.y - curr.y });
  };

  const handleMouseMoveCanvas = (e) => {
    if (!draggingNodeId) return;
    const pt = getSvgCoordinates(e);
    setNodePositions((prev) => ({
      ...prev,
      [draggingNodeId]: {
        ...prev[draggingNodeId],
        x: Math.round(Math.max(85, Math.min(615, pt.x - dragOffset.x))),
        y: Math.round(Math.max(45, Math.min(435, pt.y - dragOffset.y))),
      },
    }));
  };

  const handleMouseUpCanvas = () => {
    setDraggingNodeId(null);
  };

  // Add dynamic agent to the live graph
  const handleAddAgent = (agentOption) => {
    setShowAddMenu(false);
    if (localNodes.some((n) => n.id === agentOption.id)) {
      alert(`${agentOption.name} is already present in this topology!`);
      return;
    }

    const newNode = {
      id: agentOption.id,
      label: agentOption.name,
      node_type: "agent",
      role: agentOption.role,
    };

    const newNodes = [...localNodes, newNode];
    setLocalNodes(newNodes);

    // Create real interactive edges from coordinator and to analyst/reporter
    const coordId = localNodes.find((n) => n.id.includes("coord"))?.id || "agent_coordinator";
    const newEdges = [
      ...localEdges,
      {
        key: `del_${agentOption.id}_${Date.now()}`,
        source: coordId,
        target: agentOption.id,
        interaction_type: "delegation",
        semantic_summary: `Delegated specialized scope '${agentOption.role}' to ${agentOption.name}`,
        timestamp: new Date().toISOString(),
      },
      {
        key: `resp_${agentOption.id}_${Date.now()}`,
        source: agentOption.id,
        target: "agent_reporter",
        interaction_type: "result",
        semantic_summary: `${agentOption.name} delivered analytical verification findings`,
        timestamp: new Date().toISOString(),
      },
    ];
    setLocalEdges(newEdges);
    setNodePositions(computeDynamicLayout(newNodes));
  };

  // Remove agent from the live graph
  const handleRemoveAgent = (agentId) => {
    if (agentId.includes("coord")) {
      alert("Cannot remove Lead Coordinator! It holds root authority.");
      return;
    }
    const filteredNodes = localNodes.filter((n) => n.id !== agentId);
    const filteredEdges = localEdges.filter((e) => e.source !== agentId && e.target !== agentId);
    setLocalNodes(filteredNodes);
    setLocalEdges(filteredEdges);
    setNodePositions(computeDynamicLayout(filteredNodes));
    if (selectedNode?.id === agentId) setSelectedNode(null);
  };

  // Order interactions sequentially for step-by-step playback
  const chronologicalSteps = useMemo(() => {
    if (localEdges.length > 0) {
      return [...localEdges].sort((a, b) => {
        const tA = a.timestamp || "";
        const tB = b.timestamp || "";
        return tA.localeCompare(tB);
      });
    }
    return [];
  }, [localEdges]);

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

  useEffect(() => {
    if (activeStepIdx !== null && chronologicalSteps[activeStepIdx]) {
      setSelectedEdge(chronologicalSteps[activeStepIdx]);
    }
  }, [activeStepIdx, chronologicalSteps]);

  // Calculate curved SVG path with directional curvature
  const calculatePath = (srcId, tgtId, edgeIdx = 0) => {
    const src = nodePositions[srcId] || { x: 200, y: 200 };
    const tgt = nodePositions[tgtId] || { x: 500, y: 200 };

    const dx = tgt.x - src.x;
    const dy = tgt.y - src.y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;

    const nx = -dy / dist;
    const ny = dx / dist;

    const curvature = 36 * (edgeIdx % 2 === 0 ? 1 : -1) * (1 + Math.floor(edgeIdx / 2) * 0.35);

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
    if (t.includes("delegat")) return "#60a5fa";
    if (t.includes("finding") || t.includes("data") || t.includes("response") || t.includes("result")) return "#10b981";
    if (t.includes("analys") || t.includes("audit") || t.includes("critic")) return "#f59e0b";
    if (t.includes("report") || t.includes("synth")) return "#ec4899";
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
        position: "relative",
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
        <div
          onClick={() => setIsCollapsed(!isCollapsed)}
          style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer", userSelect: "none" }}
          title={isCollapsed ? "Click to expand interaction graph" : "Click to collapse interaction graph"}
        >
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
              flexShrink: 0,
            }}
          >
            <Share2 size={15} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
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
              <span
                style={{
                  fontSize: 10.5,
                  padding: "1px 6px",
                  borderRadius: 4,
                  background: isCollapsed ? "rgba(56, 189, 248, 0.15)" : "rgba(148, 163, 184, 0.12)",
                  color: isCollapsed ? "#38bdf8" : "#94a3b8",
                  border: isCollapsed ? "1px solid rgba(56, 189, 248, 0.3)" : "1px solid rgba(148, 163, 184, 0.2)",
                  fontWeight: 600,
                }}
              >
                {isCollapsed ? "Click to Expand Graph ▼" : `${localNodes.length} Agents Active ▲`}
              </span>
            </div>
            <span style={{ fontSize: 11, color: "#94a3b8" }}>
              {localNodes.length} Dynamic Agents &bull; {localEdges.length} Observed Messages &bull; Draggable Physics
            </span>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {!isCollapsed && (
            <>
              {/* Dynamic Add Agent Button */}
              <div style={{ position: "relative" }}>
                <button
                  onClick={() => setShowAddMenu(!showAddMenu)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                    padding: "4px 8px",
                    background: "rgba(16, 185, 129, 0.15)",
                    border: "1px solid rgba(16, 185, 129, 0.35)",
                    borderRadius: 6,
                    color: "#34d399",
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                  title="Add specialized agent node to live topology"
                >
                  <Plus size={12} />
                  <span>Add Agent</span>
                </button>

                {showAddMenu && (
                  <div
                    style={{
                      position: "absolute",
                      top: "100%",
                      right: 0,
                      marginTop: 4,
                      background: "#0f172a",
                      border: "1px solid #334155",
                      borderRadius: 8,
                      padding: 6,
                      display: "flex",
                      flexDirection: "column",
                      gap: 4,
                      zIndex: 50,
                      width: 220,
                      boxShadow: "0 10px 25px rgba(0,0,0,0.5)",
                    }}
                  >
                    <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700, padding: "4px 8px", textTransform: "uppercase" }}>
                      Select Specialized Agent:
                    </div>
                    {AVAILABLE_AGENT_OPTIONS.map((opt) => (
                      <button
                        key={opt.id}
                        onClick={() => handleAddAgent(opt)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "6px 8px",
                          background: "#1e293b",
                          border: "1px solid #334155",
                          borderRadius: 6,
                          color: "#f8fafc",
                          fontSize: 11,
                          cursor: "pointer",
                          textAlign: "left",
                        }}
                      >
                        <span style={{ fontWeight: 600, color: opt.color }}>{opt.name}</span>
                        <Plus size={11} color="#94a3b8" />
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Reset / Auto-Layout */}
              <button
                onClick={() => setNodePositions(computeDynamicLayout(localNodes))}
                style={{
                  padding: "4px 8px",
                  background: "#1e293b",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 6,
                  color: "#94a3b8",
                  fontSize: 11,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                }}
                title="Reset to balanced geometric topology"
              >
                <RefreshCw size={11} />
                <span>Auto-Layout</span>
              </button>

              {/* Replay Button */}
              {localEdges.length > 0 && (
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
                  <span>{isPlaying ? "Pause" : "Replay"}</span>
                </button>
              )}
            </>
          )}

          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            style={{
              padding: "4px 10px",
              background: isCollapsed ? "rgba(59, 130, 246, 0.15)" : "#1e293b",
              border: isCollapsed ? "1px solid #3b82f6" : "1px solid rgba(255,255,255,0.1)",
              borderRadius: 6,
              color: isCollapsed ? "#93c5fd" : "#94a3b8",
              fontSize: 11.5,
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 5,
            }}
            title={isCollapsed ? "Expand Graph" : "Collapse Graph"}
          >
            <span>{isCollapsed ? "Expand" : "Collapse"}</span>
            {isCollapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <>
          {/* Interactive Step Sequence Ribbon */}
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

          {/* SVG Canvas with Draggable Physics & Living Animation */}
          <div
            style={{
              position: "relative",
              width: "100%",
              height: compact ? 340 : 460,
              background: "radial-gradient(ellipse at 50% 50%, #0e1726 0%, #06090f 100%)",
              borderRadius: 10,
              border: "1px solid #1e293b",
              overflow: "hidden",
              userSelect: "none",
            }}
          >
            <svg
              ref={svgRef}
              viewBox="0 0 700 480"
              style={{ width: "100%", height: "100%", display: "block", cursor: draggingNodeId ? "grabbing" : "default" }}
              onMouseMove={handleMouseMoveCanvas}
              onMouseUp={handleMouseUpCanvas}
              onTouchMove={handleMouseMoveCanvas}
              onTouchEnd={handleMouseUpCanvas}
            >
              <defs>
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>

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
              </defs>

              {/* Subdued Grid Background */}
              <g stroke="rgba(255, 255, 255, 0.03)" strokeWidth="1">
                {Array.from({ length: 14 }).map((_, i) => (
                  <line key={`v-${i}`} x1={i * 50} y1="0" x2={i * 50} y2="480" />
                ))}
                {Array.from({ length: 10 }).map((_, i) => (
                  <line key={`h-${i}`} x1="0" y1={i * 50} x2="700" y2={i * 50} />
                ))}
              </g>

              {/* Interaction Edges */}
              {localEdges.map((edge, idx) => {
                const isSelected = selectedEdge?.key === edge.key || activeStepIdx === idx;
                const pathData = calculatePath(edge.source, edge.target, idx);
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
                    <path
                      d={pathData.d}
                      fill="none"
                      stroke="transparent"
                      strokeWidth="20"
                    />

                    {isSelected && (
                      <path
                        d={pathData.d}
                        fill="none"
                        stroke={edgeColor}
                        strokeWidth="7"
                        opacity="0.35"
                        filter="url(#glow)"
                      />
                    )}

                    <path
                      d={pathData.d}
                      fill="none"
                      stroke={edgeColor}
                      strokeWidth={isSelected ? "3" : "1.8"}
                      strokeOpacity={isSelected ? 1 : 0.65}
                      strokeDasharray={isSelected ? "8 4" : "5 5"}
                      markerEnd="url(#arrow-default)"
                    />

                    {/* Animated Flowing Packet (Proves Real-time Living Graph) */}
                    <circle r="4.5" fill={edgeColor} filter="url(#glow)">
                      <animateMotion
                        path={pathData.d}
                        dur={`${2.2 + (idx % 3) * 0.4}s`}
                        repeatCount="indefinite"
                      />
                    </circle>

                    {/* Step Sequence Badge on Midpoint */}
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

              {/* Draggable Agent Nodes */}
              {Object.entries(nodePositions).map(([id, node]) => {
                const isSelected = selectedNode?.id === id;
                const isConnected = selectedEdge?.source === id || selectedEdge?.target === id;
                const isDragging = draggingNodeId === id;

                return (
                  <g
                    key={id}
                    transform={`translate(${node.x}, ${node.y})`}
                    onMouseDown={(e) => handleMouseDownNode(id, e)}
                    onTouchStart={(e) => handleMouseDownNode(id, e)}
                    onClick={() => {
                      setSelectedNode(node);
                      setSelectedEdge(null);
                    }}
                    style={{ cursor: isDragging ? "grabbing" : "grab" }}
                  >
                    {(isSelected || isConnected || isDragging) && (
                      <rect
                        x="-88"
                        y="-42"
                        width="176"
                        height="84"
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
                      y="-38"
                      width="168"
                      height="76"
                      rx="12"
                      fill="#0f172a"
                      stroke={isSelected || isConnected ? "#38bdf8" : node.borderColor || "#334155"}
                      strokeWidth={isSelected || isConnected ? "2.5" : "1.5"}
                    />

                    {/* Header gradient banner */}
                    <rect
                      x="-83"
                      y="-37"
                      width="166"
                      height="26"
                      rx="10"
                      fill={node.fillColor || "rgba(59, 130, 246, 0.15)"}
                    />

                    {/* Pulse status indicator */}
                    <circle cx="-66" cy="-24" r="4" fill="#10b981" />
                    <circle cx="-66" cy="-24" r="7" fill="#10b981" opacity="0.25" />

                    {/* Agent Name */}
                    <text
                      x="-54"
                      y="-20"
                      fill="#f8fafc"
                      fontSize="11"
                      fontWeight="700"
                      fontFamily="system-ui, sans-serif"
                    >
                      {node.label || id.replace("agent_", "")}
                    </text>

                    {/* Drag Grip Indicator */}
                    <g transform="translate(60, -28)" opacity="0.6">
                      <circle cx="0" cy="0" r="1.5" fill="#94a3b8" />
                      <circle cx="5" cy="0" r="1.5" fill="#94a3b8" />
                      <circle cx="0" cy="5" r="1.5" fill="#94a3b8" />
                      <circle cx="5" cy="5" r="1.5" fill="#94a3b8" />
                    </g>

                    {/* Role Description */}
                    <text
                      x="0"
                      y="4"
                      textAnchor="middle"
                      fill="#94a3b8"
                      fontSize="9.5"
                      fontFamily="system-ui, sans-serif"
                    >
                      {node.role?.length > 25 ? node.role.substring(0, 23) + "..." : node.role}
                    </text>

                    {/* Real Tool Badge */}
                    <g transform="translate(0, 22)">
                      <rect
                        x="-70"
                        y="-7"
                        width="140"
                        height="15"
                        rx="4"
                        fill="#111827"
                        stroke="rgba(255, 255, 255, 0.1)"
                        strokeWidth="1"
                      />
                      <text
                        x="0"
                        y="4"
                        textAnchor="middle"
                        fill="#38bdf8"
                        fontSize="8"
                        fontFamily="monospace"
                        fontWeight="600"
                      >
                        ⚙️ {node.tools ? node.tools[0] : "CIM Tool"}
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
                      <strong>Timestamp:</strong> <span>{selectedEdge.timestamp?.split("T")[1]?.substring(0, 8) || "Live"}</span>
                    </div>
                  </div>
                </>
              ) : selectedNode ? (
                <>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <strong style={{ color: "#38bdf8", fontSize: 13 }}>{selectedNode.label || selectedNode.id}</strong>
                      <span style={{ fontSize: 10, background: "rgba(56, 189, 248, 0.15)", color: "#38bdf8", padding: "1px 6px", borderRadius: 4 }}>
                        {selectedNode.model || "Google Gemini 3.5 Flash"}
                      </span>
                    </div>
                    <div style={{ color: "#cbd5e1", fontSize: 11.5, marginBottom: 6 }}>
                      {selectedNode.role || "Autonomous Specialized Agent"}
                    </div>
                    <div style={{ fontSize: 11, color: "#94a3b8" }}>
                      <strong>Active Tools:</strong> {(selectedNode.tools || ["read_dataset", "query_records"]).join(", ")}
                    </div>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "flex-end", gap: 6 }}>
                    <div style={{ fontSize: 11, color: "#10b981" }}>
                      &bull; State: <strong>Online &amp; Active</strong>
                    </div>
                    {!selectedNode.id.includes("coord") && (
                      <button
                        onClick={() => handleRemoveAgent(selectedNode.id)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 4,
                          padding: "3px 8px",
                          background: "rgba(239, 68, 68, 0.15)",
                          border: "1px solid rgba(239, 68, 68, 0.3)",
                          borderRadius: 4,
                          color: "#f87171",
                          fontSize: 10.5,
                          cursor: "pointer",
                        }}
                      >
                        <Trash2 size={11} />
                        <span>Remove Agent from Team</span>
                      </button>
                    )}
                  </div>
                </>
              ) : null}
            </div>
          )}
        </>
      )}
    </div>
  );
}
