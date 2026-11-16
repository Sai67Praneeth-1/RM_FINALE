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
  Building2,
  Users,
  Network,
  Layers,
} from "lucide-react";

// Squad metadata library defining distinct federated squads
export const SQUAD_METADATA = {
  squad_command: {
    id: "squad_command",
    name: "Command & Governance Squad",
    shortName: "Command Squad",
    icon: "👑",
    color: "#3b82f6",
    fillColor: "rgba(59, 130, 246, 0.12)",
    borderColor: "#60a5fa",
    mission: "Root Task Orchestration, Scoped Token Delegation & W3C PROV Report Synthesis",
    defaultPos: { x: 350, y: 95 },
  },
  squad_complaints: {
    id: "squad_complaints",
    name: "Complaints & Experience Squad",
    shortName: "Complaints Squad",
    icon: "🏢",
    color: "#10b981",
    fillColor: "rgba(16, 185, 129, 0.12)",
    borderColor: "#34d399",
    mission: "CFPB Complaint Ingestion, Consumer Dispute Extraction & Sentiment Polarity NLP",
    defaultPos: { x: 175, y: 315 },
  },
  squad_secops: {
    id: "squad_secops",
    name: "SecOps Forensics Squad",
    shortName: "SecOps Squad",
    icon: "🛡️",
    color: "#ef4444",
    fillColor: "rgba(239, 68, 68, 0.12)",
    borderColor: "#f87171",
    mission: "System Access Log Scanning, Privilege Escalation Hunting & FedRAMP / NIST Policy Auditing",
    defaultPos: { x: 525, y: 315 },
  },
  squad_analytics: {
    id: "squad_analytics",
    name: "Statistical Analytics Squad",
    shortName: "Analytics Squad",
    icon: "📊",
    color: "#f59e0b",
    fillColor: "rgba(245, 158, 11, 0.12)",
    borderColor: "#fbbf24",
    mission: "Quantitative Metric Inversion, Anomaly Rate Computation & Variance Benchmarking",
    defaultPos: { x: 230, y: 400 },
  },
  squad_critic: {
    id: "squad_critic",
    name: "Adversarial Debate Squad",
    shortName: "Critic Squad",
    icon: "🎯",
    color: "#f97316",
    fillColor: "rgba(249, 115, 22, 0.12)",
    borderColor: "#fb923c",
    mission: "Adversarial Logic Verification, Counterfactual Challenge & Hallucination Elimination",
    defaultPos: { x: 470, y: 400 },
  },
};

// Map individual agents to their respective squads
export const AGENT_SQUAD_MAP = {
  agent_coordinator: "squad_command",
  Coordinator_Agent: "squad_command",
  agent_reporter: "squad_command",
  Synthesizer_Agent: "squad_command",
  agent_researcher: "squad_complaints",
  Executor_Agent: "squad_complaints",
  agent_sentiment: "squad_complaints",
  agent_forensics: "squad_secops",
  agent_threat_hunter: "squad_secops",
  agent_compliance: "squad_secops",
  agent_analyst: "squad_analytics",
  agent_critic: "squad_critic",
  Critic_Agent: "squad_critic",
};

export const getAgentSquadId = (agentId) => {
  if (!agentId) return "squad_command";
  if (AGENT_SQUAD_MAP[agentId]) return AGENT_SQUAD_MAP[agentId];
  const lower = agentId.toLowerCase();
  if (lower.includes("forensic") || lower.includes("threat") || lower.includes("compliance") || lower.includes("sec")) {
    return "squad_secops";
  }
  if (lower.includes("research") || lower.includes("sentiment") || lower.includes("complaint") || lower.includes("execut")) {
    return "squad_complaints";
  }
  if (lower.includes("analyst") || lower.includes("stat")) {
    return "squad_analytics";
  }
  if (lower.includes("critic") || lower.includes("debate")) {
    return "squad_critic";
  }
  return "squad_command";
};

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
    squadId: "squad_command",
  },
  Coordinator_Agent: {
    label: "Coordinator",
    role: "Lead Orchestrator & Task Delegator",
    model: "Google Gemini 3.5 Flash",
    tools: ["mint_delegation", "verify_invariants"],
    color: "#3b82f6",
    fillColor: "rgba(59, 130, 246, 0.15)",
    borderColor: "#60a5fa",
    squadId: "squad_command",
  },
  agent_researcher: {
    label: "Researcher",
    role: "CFPB Complaint Extraction",
    model: "Google Gemini 3.5 Flash",
    tools: ["read_sample_dataset", "query_cfpb_records"],
    color: "#10b981",
    fillColor: "rgba(16, 185, 129, 0.15)",
    borderColor: "#34d399",
    squadId: "squad_complaints",
  },
  Executor_Agent: {
    label: "Executor",
    role: "CIM Data Ingestion & Extraction",
    model: "Google Gemini 3.5 Flash",
    tools: ["read_sample_dataset", "query_cfpb_records"],
    color: "#10b981",
    fillColor: "rgba(16, 185, 129, 0.15)",
    borderColor: "#34d399",
    squadId: "squad_complaints",
  },
  agent_analyst: {
    label: "Analyst",
    role: "Statistical Anomaly Evaluator",
    model: "Google Gemini 3.5 Flash",
    tools: ["calculate_anomaly_rates", "compute_aggregates"],
    color: "#f59e0b",
    fillColor: "rgba(245, 158, 11, 0.15)",
    borderColor: "#fbbf24",
    squadId: "squad_analytics",
  },
  agent_reporter: {
    label: "Reporter",
    role: "W3C PROV & Synthesis",
    model: "Google Gemini 3.5 Flash",
    tools: ["export_w3c_prov", "generate_markdown_report"],
    color: "#ec4899",
    fillColor: "rgba(236, 72, 153, 0.15)",
    borderColor: "#f472b6",
    squadId: "squad_command",
  },
  Synthesizer_Agent: {
    label: "Synthesizer",
    role: "Executive Resolution Formulator",
    model: "Google Gemini 3.5 Flash",
    tools: ["export_w3c_prov", "generate_markdown_report"],
    color: "#ec4899",
    fillColor: "rgba(236, 72, 153, 0.15)",
    borderColor: "#f472b6",
    squadId: "squad_command",
  },
  agent_forensics: {
    label: "Forensics Scanner",
    role: "Access Log & Security Forensics",
    model: "Google Gemini 3.5 Flash",
    tools: ["scan_system_access_logs", "inspect_auth_events"],
    color: "#06b6d4",
    fillColor: "rgba(6, 182, 212, 0.15)",
    borderColor: "#22d3ee",
    squadId: "squad_secops",
  },
  agent_threat_hunter: {
    label: "Threat Hunter",
    role: "Privilege Escalation Detector",
    model: "Google Gemini 3.5 Flash",
    tools: ["detect_unauthorized_root", "verify_ip_anomalies"],
    color: "#ef4444",
    fillColor: "rgba(239, 68, 68, 0.15)",
    borderColor: "#f87171",
    squadId: "squad_secops",
  },
  agent_compliance: {
    label: "Compliance Auditor",
    role: "FedRAMP & NIST Policy Auditor",
    model: "Google Gemini 3.5 Flash",
    tools: ["audit_nist_sp_800_53", "validate_cim_invariants"],
    color: "#8b5cf6",
    fillColor: "rgba(139, 92, 246, 0.15)",
    borderColor: "#a78bfa",
    squadId: "squad_secops",
  },
  agent_sentiment: {
    label: "Sentiment Specialist",
    role: "Consumer Experience & NLP",
    model: "Google Gemini 3.5 Flash",
    tools: ["analyze_sentiment_polarity", "extract_customer_intents"],
    color: "#14b8a6",
    fillColor: "rgba(20, 184, 166, 0.15)",
    borderColor: "#2dd4bf",
    squadId: "squad_complaints",
  },
  agent_critic: {
    label: "Adversarial Critic",
    role: "Reasoning & Invariant Auditor",
    model: "Google Gemini 3.5 Flash",
    tools: ["verify_causality", "detect_inconsistencies"],
    color: "#f97316",
    fillColor: "rgba(249, 115, 22, 0.15)",
    borderColor: "#fb923c",
    squadId: "squad_critic",
  },
  Critic_Agent: {
    label: "Adversarial Critic",
    role: "Reasoning & Invariant Auditor",
    model: "Google Gemini 3.5 Flash",
    tools: ["verify_causality", "detect_inconsistencies"],
    color: "#f97316",
    fillColor: "rgba(249, 115, 22, 0.15)",
    borderColor: "#fb923c",
    squadId: "squad_critic",
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
  squadId: "squad_command",
};

const AVAILABLE_AGENT_OPTIONS = [
  { id: "agent_threat_hunter", name: "Threat Hunter", role: "Privilege Escalation Detector", color: "#ef4444", squad: "squad_secops" },
  { id: "agent_compliance", name: "Compliance Auditor", role: "FedRAMP & NIST Invariant Auditor", color: "#8b5cf6", squad: "squad_secops" },
  { id: "agent_sentiment", name: "Sentiment Specialist", role: "Consumer Experience & NLP", color: "#14b8a6", squad: "squad_complaints" },
  { id: "agent_forensics", name: "Forensics Scanner", role: "Access Log & Security Forensics", color: "#06b6d4", squad: "squad_secops" },
  { id: "agent_critic", name: "Adversarial Critic", role: "Reasoning & Vulnerability Auditor", color: "#f97316", squad: "squad_critic" },
];

export default function AgentInteractionGraph({
  graph,
  interactions = [],
  workflowId,
  title = "Squad & Agent Interaction Topology",
  compact = false,
  defaultCollapsed = true,
}) {
  // View mode: "squad" (Squad-Level View) or "agent" (Granular Agent Detail View)
  const [viewMode, setViewMode] = useState("squad");

  const [selectedEdge, setSelectedEdge] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedSquad, setSelectedSquad] = useState(null);
  const [selectedSquadEdge, setSelectedSquadEdge] = useState(null);

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

    // Determine if multiple squads are active; if so, default to squad view
    const squadsPresent = new Set(initialNodes.map((n) => n.squad_id || getAgentSquadId(n.id)));
    if (squadsPresent.size > 1) {
      setViewMode("squad");
    }
  }, [graph, interactions, workflowId]);

  // Compute adaptive balanced layout for N nodes
  function computeDynamicLayout(nodesList) {
    const pos = {};
    const count = nodesList.length;
    if (count === 0) return pos;

    const idSet = new Set(nodesList.map((n) => n.id));

    // Topology 1: Cross-Squad Federation (7+ agents across Complaints & SecOps)
    if (idSet.has("agent_forensics") && idSet.has("agent_researcher")) {
      const crossPositions = {
        agent_coordinator: { x: 350, y: 70 },
        agent_researcher: { x: 135, y: 175 },
        agent_sentiment: { x: 135, y: 320 },
        agent_forensics: { x: 565, y: 175 },
        agent_threat_hunter: { x: 565, y: 320 },
        agent_compliance: { x: 260, y: 415 },
        agent_reporter: { x: 440, y: 415 },
      };
      nodesList.forEach((n) => {
        const meta = KNOWN_AGENTS[n.id] || DEFAULT_META;
        const coords = crossPositions[n.id] || { x: 350, y: 240 };
        pos[n.id] = { ...meta, ...n, label: n.label || meta.label, ...coords };
      });
      return pos;
    }

    // Topology 2: Adversarial Debate Squad (Peer-to-Peer Mesh with Critic)
    if (idSet.has("agent_critic")) {
      const criticPositions = {
        agent_coordinator: { x: 350, y: 70 },
        agent_researcher: { x: 130, y: 210 },
        agent_analyst: { x: 270, y: 330 },
        agent_critic: { x: 430, y: 330 },
        agent_reporter: { x: 570, y: 210 },
      };
      nodesList.forEach((n) => {
        const meta = KNOWN_AGENTS[n.id] || DEFAULT_META;
        const coords = criticPositions[n.id] || { x: 350, y: 240 };
        pos[n.id] = { ...meta, ...n, label: n.label || meta.label, ...coords };
      });
      return pos;
    }

    // Topology 3: SecOps Access Log & Privilege Escalation Squad (4 agents)
    if (idSet.has("agent_forensics") && idSet.has("agent_threat_hunter")) {
      const secPositions = {
        agent_coordinator: { x: 350, y: 75 },
        agent_forensics: { x: 150, y: 240 },
        agent_threat_hunter: { x: 550, y: 240 },
        agent_compliance: { x: 350, y: 395 },
      };
      nodesList.forEach((n) => {
        const meta = KNOWN_AGENTS[n.id] || DEFAULT_META;
        const coords = secPositions[n.id] || { x: 350, y: 240 };
        pos[n.id] = { ...meta, ...n, label: n.label || meta.label, ...coords };
      });
      return pos;
    }

    // Topology 4: Consumer Sentiment Squad (5 agents)
    if (idSet.has("agent_sentiment")) {
      const sentPositions = {
        agent_coordinator: { x: 350, y: 75 },
        agent_researcher: { x: 130, y: 200 },
        agent_sentiment: { x: 190, y: 390 },
        agent_analyst: { x: 510, y: 390 },
        agent_reporter: { x: 570, y: 200 },
      };
      nodesList.forEach((n) => {
        const meta = KNOWN_AGENTS[n.id] || DEFAULT_META;
        const coords = sentPositions[n.id] || { x: 350, y: 240 };
        pos[n.id] = { ...meta, ...n, label: n.label || meta.label, ...coords };
      });
      return pos;
    }

    // Default Mathematical Dynamic Geometry for generic N
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
        pos[others[0].id] = { ...meta0, ...others[0], label: others[0].label || meta0.label, x: 175, y: 330 };
        pos[others[1].id] = { ...meta1, ...others[1], label: others[1].label || meta1.label, x: 525, y: 330 };
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

  // Active Squads aggregation from localNodes
  const activeSquads = useMemo(() => {
    const squadMap = {};
    localNodes.forEach((node) => {
      const sqId = node.squad_id || getAgentSquadId(node.id);
      if (!squadMap[sqId]) {
        const meta = SQUAD_METADATA[sqId] || {
          id: sqId,
          name: `${sqId.replace("squad_", "").toUpperCase()} Squad`,
          shortName: `${sqId.replace("squad_", "")} Squad`,
          icon: "🏢",
          color: "#8b5cf6",
          fillColor: "rgba(139, 92, 246, 0.12)",
          borderColor: "#a78bfa",
          mission: "Domain-specific autonomous agent collaboration",
          defaultPos: { x: 350, y: 240 },
        };
        squadMap[sqId] = {
          ...meta,
          members: [],
          tools: new Set(),
        };
      }
      squadMap[sqId].members.push(node);
      const meta = KNOWN_AGENTS[node.id] || {};
      const agentTools = node.tools || meta.tools || [];
      agentTools.forEach((t) => squadMap[sqId].tools.add(t));
    });

    return Object.values(squadMap).map((sq) => ({
      ...sq,
      toolList: Array.from(sq.tools),
    }));
  }, [localNodes]);

  // Squad positions for the dedicated Squad View Canvas
  const squadPositions = useMemo(() => {
    const pos = {};
    const count = activeSquads.length;
    if (count === 0) return pos;

    const hasCommand = activeSquads.some((s) => s.id === "squad_command");
    const hasComplaints = activeSquads.some((s) => s.id === "squad_complaints");
    const hasSecOps = activeSquads.some((s) => s.id === "squad_secops");

    // Standard Triad: Command (Top), Complaints (Left), SecOps (Right)
    if (hasCommand && hasComplaints && hasSecOps && count === 3) {
      pos["squad_command"] = { x: 350, y: 85 };
      pos["squad_complaints"] = { x: 185, y: 310 };
      pos["squad_secops"] = { x: 515, y: 310 };
      return pos;
    }

    if (hasCommand && hasComplaints && hasSecOps && count >= 4) {
      pos["squad_command"] = { x: 350, y: 75 };
      pos["squad_complaints"] = { x: 175, y: 240 };
      pos["squad_secops"] = { x: 525, y: 240 };
      const remaining = activeSquads.filter((s) => !["squad_command", "squad_complaints", "squad_secops"].includes(s.id));
      if (remaining.length === 1) {
        pos[remaining[0].id] = { x: 350, y: 400 };
      } else if (remaining.length === 2) {
        pos[remaining[0].id] = { x: 230, y: 400 };
        pos[remaining[1].id] = { x: 470, y: 400 };
      }
      return pos;
    }

    // Dynamic Polygon Layout for arbitrary squad sets
    const cx = 350;
    const cy = 240;
    const rx = 210;
    const ry = 140;
    activeSquads.forEach((sq, i) => {
      const angle = (i / count) * 2 * Math.PI - Math.PI / 2;
      pos[sq.id] = {
        x: Math.round(cx + rx * Math.cos(angle)),
        y: Math.round(cy + ry * Math.sin(angle)),
      };
    });
    return pos;
  }, [activeSquads]);

  // Aggregate inter-squad communication conduits
  const squadEdges = useMemo(() => {
    const edgeAgg = {};
    localEdges.forEach((e) => {
      const srcSquad = e.from_squad || getAgentSquadId(e.source);
      const tgtSquad = e.to_squad || getAgentSquadId(e.target);
      const key = `${srcSquad}__${tgtSquad}`;

      if (!edgeAgg[key]) {
        const isBridge =
          (srcSquad === "squad_complaints" && tgtSquad === "squad_secops") ||
          (srcSquad === "squad_secops" && tgtSquad === "squad_complaints");
        edgeAgg[key] = {
          key,
          source: srcSquad,
          target: tgtSquad,
          isBridge,
          interactions: [],
          messageCount: 0,
          interactionTypes: new Set(),
        };
      }
      edgeAgg[key].interactions.push(e);
      edgeAgg[key].messageCount += 1;
      if (e.interaction_type) edgeAgg[key].interactionTypes.add(e.interaction_type);
    });

    return Object.values(edgeAgg).map((se) => {
      let label = `${se.messageCount} Message${se.messageCount > 1 ? "s" : ""}`;
      if (se.isBridge) {
        label = `⚡ CROSS-SQUAD BRIDGE (${se.messageCount})`;
      } else if (se.source === "squad_command") {
        label = `Delegation & Directives (${se.messageCount})`;
      } else if (se.target === "squad_command") {
        label = `Findings & Synthesis (${se.messageCount})`;
      }
      return {
        ...se,
        label,
        types: Array.from(se.interactionTypes),
      };
    });
  }, [localEdges]);

  // Visual Bounding Boxes around member agents for each squad (used in Agent Detail View)
  const squadBoundingBoxes = useMemo(() => {
    const boxes = [];
    activeSquads.forEach((squad) => {
      const memberCoords = squad.members
        .map((m) => nodePositions[m.id])
        .filter((pos) => pos && pos.x !== undefined && pos.y !== undefined);

      if (memberCoords.length === 0) return;

      const xs = memberCoords.map((c) => c.x);
      const ys = memberCoords.map((c) => c.y);

      const minX = Math.min(...xs) - 95;
      const maxX = Math.max(...xs) + 95;
      const minY = Math.min(...ys) - 55;
      const maxY = Math.max(...ys) + 55;

      boxes.push({
        squadId: squad.id,
        squadName: squad.name,
        shortName: squad.shortName,
        icon: squad.icon,
        color: squad.color,
        fillColor: squad.fillColor,
        borderColor: squad.borderColor,
        x: minX,
        y: minY,
        width: Math.max(220, maxX - minX),
        height: Math.max(130, maxY - minY),
        memberCount: squad.members.length,
      });
    });
    return boxes;
  }, [activeSquads, nodePositions]);

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
      squad_id: agentOption.squad,
    };

    const newNodes = [...localNodes, newNode];
    setLocalNodes(newNodes);

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
        from_squad: "squad_command",
        to_squad: agentOption.squad,
        is_cross_squad: agentOption.squad !== "squad_command",
      },
      {
        key: `resp_${agentOption.id}_${Date.now()}`,
        source: agentOption.id,
        target: "agent_reporter",
        interaction_type: "result",
        semantic_summary: `${agentOption.name} delivered analytical verification findings`,
        timestamp: new Date().toISOString(),
        from_squad: agentOption.squad,
        to_squad: "squad_command",
        is_cross_squad: agentOption.squad !== "squad_command",
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
      }, 1600);
    }
    return () => clearInterval(timer);
  }, [isPlaying, chronologicalSteps.length]);

  useEffect(() => {
    if (activeStepIdx !== null && chronologicalSteps[activeStepIdx]) {
      setSelectedEdge(chronologicalSteps[activeStepIdx]);
    }
  }, [activeStepIdx, chronologicalSteps]);

  // Calculate curved SVG path between squads in Squad View
  const calculateSquadPath = (srcSquadId, tgtSquadId, edgeIdx = 0) => {
    const src = squadPositions[srcSquadId] || { x: 200, y: 200 };
    const tgt = squadPositions[tgtSquadId] || { x: 500, y: 200 };

    const dx = tgt.x - src.x;
    const dy = tgt.y - src.y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;

    const nx = -dy / dist;
    const ny = dx / dist;

    const curvature = 45 * (edgeIdx % 2 === 0 ? 1 : -1);

    const midX = (src.x + tgt.x) / 2 + nx * curvature;
    const midY = (src.y + tgt.y) / 2 + ny * curvature;

    return {
      d: `M ${src.x} ${src.y} Q ${midX} ${midY} ${tgt.x} ${tgt.y}`,
      midX,
      midY,
    };
  };

  // Calculate curved SVG path between agents in Agent View
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

  const getEdgeColor = (type, isHighlighted, isCrossSquad = false) => {
    if (isCrossSquad) return "#f59e0b"; // Radiant Amber for Cross-Squad Bridge
    if (isHighlighted) return "#38bdf8";
    const t = (type || "").toLowerCase();
    if (t.includes("delegat")) return "#60a5fa";
    if (t.includes("finding") || t.includes("data") || t.includes("response") || t.includes("result")) return "#10b981";
    if (t.includes("analys") || t.includes("audit") || t.includes("critic")) return "#f59e0b";
    if (t.includes("report") || t.includes("synth")) return "#ec4899";
    return "#94a3b8";
  };

  const isCrossSquadActive = activeSquads.length > 1;

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
      {/* 1. Header Bar with View Mode Toggle */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: isCollapsed ? 0 : 12,
          paddingBottom: isCollapsed ? 0 : 10,
          borderBottom: isCollapsed ? "none" : "1px solid #1e293b",
          flexWrap: "wrap",
          gap: 10,
        }}
      >
        <div
          onClick={() => setIsCollapsed(!isCollapsed)}
          style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer", userSelect: "none" }}
          title={isCollapsed ? "Click to expand interaction graph" : "Click to collapse interaction graph"}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: "50%",
              background: "linear-gradient(135deg, #3b82f6, #10b981)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              flexShrink: 0,
              boxShadow: "0 0 12px rgba(16, 185, 129, 0.4)",
            }}
          >
            {viewMode === "squad" ? <Building2 size={17} /> : <Share2 size={17} />}
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <h4
                style={{
                  margin: 0,
                  fontSize: compact ? 14 : 15.5,
                  fontWeight: 700,
                  color: "#60a5fa",
                  letterSpacing: "0.2px",
                }}
              >
                {viewMode === "squad"
                  ? "🏢 SQUAD INTERACTION VIEW (Federated Squads & Cross-Squad Bridge)"
                  : title}
              </h4>
              <span
                style={{
                  fontSize: 10.5,
                  padding: "2px 7px",
                  borderRadius: 4,
                  background: isCrossSquadActive ? "rgba(245, 158, 11, 0.2)" : "rgba(56, 189, 248, 0.15)",
                  color: isCrossSquadActive ? "#fbbf24" : "#38bdf8",
                  border: isCrossSquadActive ? "1px solid rgba(245, 158, 11, 0.4)" : "1px solid rgba(56, 189, 248, 0.3)",
                  fontWeight: 700,
                }}
              >
                {isCrossSquadActive ? "⚡ CROSS-SQUAD COLLABORATION" : `${activeSquads.length} Squad Active`}
              </span>
            </div>
            <span style={{ fontSize: 11, color: "#94a3b8" }}>
              {activeSquads.length} Autonomous Squads &bull; {localNodes.length} Specialized Agents &bull; {localEdges.length} Messages Captured
            </span>
          </div>
        </div>

        {/* View Mode Segmented Control + Actions */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          {!isCollapsed && (
            <>
              {/* PRIMARY VIEW SWITCHER: Dropdown for Squad Interaction vs Agent Detail */}
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <select
                  value={viewMode}
                  onChange={(e) => {
                    const newMode = e.target.value;
                    setViewMode(newMode);
                    if (newMode === "squad") {
                      setSelectedNode(null);
                      setSelectedEdge(null);
                    } else {
                      setSelectedSquad(null);
                      setSelectedSquadEdge(null);
                    }
                  }}
                  style={{
                    padding: "5px 10px",
                    borderRadius: 6,
                    background: "#0b1329",
                    color: "#60a5fa",
                    border: "1px solid #1e3a8a",
                    fontSize: 11.5,
                    fontWeight: 700,
                    cursor: "pointer",
                    outline: "none",
                    boxShadow: "0 0 10px rgba(59, 130, 246, 0.2)",
                  }}
                  title="Switch between Squad-Level and Agent-Level interaction topology"
                >
                  <option value="squad">🏢 Squad View ({activeSquads.length} Squads)</option>
                  <option value="agent">👥 Agent Detail View ({localNodes.length} Agents)</option>
                </select>
              </div>

              {/* Dynamic Add Agent Button (only in Agent view) */}
              {viewMode === "agent" && (
                <div style={{ position: "relative" }}>
                  <button
                    onClick={() => setShowAddMenu(!showAddMenu)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 4,
                      padding: "5px 9px",
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
              )}

              {/* Reset / Auto-Layout */}
              <button
                onClick={() => setNodePositions(computeDynamicLayout(localNodes))}
                style={{
                  padding: "5px 9px",
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
                    padding: "5px 11px",
                    background: isPlaying ? "#059669" : "#1e293b",
                    border: "1px solid rgba(255,255,255,0.15)",
                    borderRadius: 6,
                    color: "#fff",
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                  title={isPlaying ? "Pause Flow Replay" : "Replay Communication Flow"}
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
              padding: "5px 10px",
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
            title={isCollapsed ? "Expand Squad Interaction View" : "Collapse Squad Interaction View"}
          >
            <span>{isCollapsed ? "Expand View" : "Collapse View"}</span>
            {isCollapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <>
          {/* SQUAD COLLABORATION BANNER */}
          <div
            style={{
              background: "linear-gradient(90deg, rgba(30, 58, 138, 0.25) 0%, rgba(16, 185, 129, 0.15) 50%, rgba(239, 68, 68, 0.15) 100%)",
              border: "1px solid #1e3a8a",
              borderRadius: 8,
              padding: "8px 12px",
              marginBottom: 10,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: 8,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Zap size={14} color="#f59e0b" />
              <span style={{ fontWeight: 700, color: "#f8fafc", fontSize: 12 }}>
                {viewMode === "squad" ? "🏢 SQUAD INTERACTION TOPOLOGY" : "👥 AGENT DETAIL TOPOLOGY (GROUPED BY SQUAD)"}
              </span>
              <span style={{ color: "#94a3b8", fontSize: 11.5 }}>
                {activeSquads.map((s) => `${s.icon} ${s.shortName}`).join(" ⇄ ")}
              </span>
            </div>
            {isCrossSquadActive && (
              <span
                style={{
                  background: "#f59e0b",
                  color: "#000",
                  padding: "2px 8px",
                  borderRadius: 4,
                  fontSize: 10.5,
                  fontWeight: 800,
                  letterSpacing: "0.04em",
                }}
              >
                ⚡ FEDERATED CROSS-SQUAD BRIDGE ACTIVE
              </span>
            )}
          </div>

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
                const srcSquad = SQUAD_METADATA[step.from_squad || getAgentSquadId(step.source)];
                const tgtSquad = SQUAD_METADATA[step.to_squad || getAgentSquadId(step.target)];
                const isCross = srcSquad?.id !== tgtSquad?.id;

                const srcAgent = nodePositions[step.source]?.label || step.source?.replace("agent_", "");
                const tgtAgent = nodePositions[step.target]?.label || step.target?.replace("agent_", "");

                return (
                  <button
                    key={step.key || idx}
                    onClick={() => {
                      setActiveStepIdx(idx);
                      setSelectedEdge(step);
                      setSelectedNode(null);
                      if (viewMode === "squad") {
                        const sqEdge = squadEdges.find(
                          (se) => se.source === srcSquad?.id && se.target === tgtSquad?.id
                        );
                        if (sqEdge) setSelectedSquadEdge(sqEdge);
                      }
                    }}
                    style={{
                      flexShrink: 0,
                      padding: "4px 9px",
                      borderRadius: 14,
                      fontSize: 10.5,
                      fontWeight: 600,
                      background: isActive
                        ? isCross
                          ? "linear-gradient(135deg, #b45309, #f59e0b)"
                          : "linear-gradient(135deg, #2563eb, #3b82f6)"
                        : isCross
                        ? "rgba(245, 158, 11, 0.12)"
                        : "#131b2e",
                      border: isActive
                        ? isCross
                          ? "1px solid #fbbf24"
                          : "1px solid #60a5fa"
                        : isCross
                        ? "1px solid rgba(245, 158, 11, 0.4)"
                        : "1px solid #1e293b",
                      color: isActive ? "#fff" : isCross ? "#fbbf24" : "#94a3b8",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: 4,
                      boxShadow: isActive ? "0 0 10px rgba(59, 130, 246, 0.5)" : "none",
                    }}
                  >
                    <span>#{idx + 1}</span>
                    {isCross && <span>⚡</span>}
                    <span>
                      {srcSquad?.icon} {srcAgent} &rarr; {tgtSquad?.icon} {tgtAgent}
                    </span>
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
              height: compact ? 370 : 490,
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
              style={{
                width: "100%",
                height: "100%",
                display: "block",
                cursor: draggingNodeId ? "grabbing" : "default",
              }}
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
                <filter id="gold-glow" x="-30%" y="-30%" width="160%" height="160%">
                  <feGaussianBlur stdDeviation="4" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>

                <linearGradient id="bridgeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#10b981" />
                  <stop offset="50%" stopColor="#f59e0b" />
                  <stop offset="100%" stopColor="#ef4444" />
                </linearGradient>

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
                  id="arrow-bridge"
                  viewBox="0 0 10 10"
                  refX="38"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#f59e0b" />
                </marker>
                <marker
                  id="arrow-squad"
                  viewBox="0 0 10 10"
                  refX="65"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#38bdf8" />
                </marker>
                <marker
                  id="arrow-squad-bridge"
                  viewBox="0 0 10 10"
                  refX="65"
                  refY="5"
                  markerWidth="8"
                  markerHeight="8"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#f59e0b" />
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

              {/* ========================================================= */}
              {/* MODE A: SQUAD INTERACTION VIEW (Primary Squad Nodes)     */}
              {/* ========================================================= */}
              {viewMode === "squad" && (
                <>
                  {/* High-Level Inter-Squad Conduits */}
                  {squadEdges.map((sEdge, idx) => {
                    const isSelected = selectedSquadEdge?.key === sEdge.key;
                    const pathData = calculateSquadPath(sEdge.source, sEdge.target, idx);
                    const strokeColor = sEdge.isBridge ? "#f59e0b" : "#3b82f6";

                    return (
                      <g
                        key={sEdge.key}
                        onClick={() => {
                          setSelectedSquadEdge(sEdge);
                          setSelectedSquad(null);
                        }}
                        style={{ cursor: "pointer" }}
                      >
                        {/* Wide hit area */}
                        <path d={pathData.d} fill="none" stroke="transparent" strokeWidth="32" />

                        {/* Glow halo */}
                        <path
                          d={pathData.d}
                          fill="none"
                          stroke={sEdge.isBridge ? "#f59e0b" : "#38bdf8"}
                          strokeWidth={sEdge.isBridge ? "8" : "5"}
                          opacity={isSelected ? "0.6" : sEdge.isBridge ? "0.35" : "0.2"}
                          filter={sEdge.isBridge ? "url(#gold-glow)" : "url(#glow)"}
                        />

                        {/* Main Conduit Line */}
                        <path
                          d={pathData.d}
                          fill="none"
                          stroke={sEdge.isBridge ? "url(#bridgeGradient)" : strokeColor}
                          strokeWidth={isSelected ? "4" : sEdge.isBridge ? "3.5" : "2.5"}
                          strokeDasharray={sEdge.isBridge ? "8 4" : "none"}
                          markerEnd={sEdge.isBridge ? "url(#arrow-squad-bridge)" : "url(#arrow-squad)"}
                        />

                        {/* High-energy traveling packet */}
                        <circle
                          r={sEdge.isBridge ? "6" : "5"}
                          fill={sEdge.isBridge ? "#fde047" : "#60a5fa"}
                          filter="url(#glow)"
                        >
                          <animateMotion
                            path={pathData.d}
                            dur={`${2.0 + (idx % 2) * 0.4}s`}
                            repeatCount="indefinite"
                          />
                        </circle>

                        {/* Midpoint Squad Conduit Badge */}
                        <g transform={`translate(${pathData.midX}, ${pathData.midY})`}>
                          <rect
                            x={sEdge.isBridge ? -100 : -75}
                            y="-13"
                            width={sEdge.isBridge ? 200 : 150}
                            height="26"
                            rx="13"
                            fill={isSelected ? "#1e3a8a" : "#0f172a"}
                            stroke={sEdge.isBridge ? "#f59e0b" : "#38bdf8"}
                            strokeWidth={sEdge.isBridge ? "2" : "1.5"}
                          />
                          <text
                            textAnchor="middle"
                            dy="4"
                            fill={sEdge.isBridge ? "#fef08a" : "#f8fafc"}
                            fontSize="9.5"
                            fontWeight="bold"
                            fontFamily="system-ui, sans-serif"
                          >
                            {sEdge.label}
                          </text>
                        </g>
                      </g>
                    );
                  })}

                  {/* SQUAD NODES */}
                  {activeSquads.map((squad) => {
                    const pos = squadPositions[squad.id] || { x: 350, y: 240 };
                    const isSelected = selectedSquad?.id === squad.id;

                    return (
                      <g
                        key={squad.id}
                        transform={`translate(${pos.x}, ${pos.y})`}
                        onClick={() => {
                          setSelectedSquad(squad);
                          setSelectedSquadEdge(null);
                        }}
                        style={{ cursor: "pointer" }}
                      >
                        {/* Selected / Outer Glow */}
                        <rect
                          x="-114"
                          y="-58"
                          width="228"
                          height="116"
                          rx="16"
                          fill="none"
                          stroke={squad.color}
                          strokeWidth={isSelected ? "5" : "3"}
                          opacity={isSelected ? "0.6" : "0.25"}
                          filter="url(#glow)"
                        />

                        {/* Main Squad Box */}
                        <rect
                          x="-110"
                          y="-54"
                          width="220"
                          height="108"
                          rx="14"
                          fill="#0c1322"
                          stroke={isSelected ? "#38bdf8" : squad.borderColor}
                          strokeWidth={isSelected ? "2.5" : "1.8"}
                        />

                        {/* Top Squad Banner */}
                        <rect
                          x="-109"
                          y="-53"
                          width="218"
                          height="32"
                          rx="12"
                          fill={squad.fillColor}
                        />

                        {/* Operational Status Light */}
                        <circle cx="-92" cy="-37" r="4.5" fill="#10b981" />
                        <circle cx="-92" cy="-37" r="8" fill="#10b981" opacity="0.3" />

                        {/* Squad Title */}
                        <text
                          x="-78"
                          y="-33"
                          fill="#f8fafc"
                          fontSize="11.5"
                          fontWeight="800"
                          fontFamily="system-ui, sans-serif"
                        >
                          {squad.icon} {squad.shortName}
                        </text>

                        {/* Member Count Pill */}
                        <rect
                          x="40"
                          y="-46"
                          width="60"
                          height="18"
                          rx="9"
                          fill="#1e293b"
                          stroke={squad.borderColor}
                          strokeWidth="1"
                        />
                        <text
                          x="70"
                          y="-34"
                          textAnchor="middle"
                          fill="#93c5fd"
                          fontSize="8.5"
                          fontWeight="700"
                        >
                          {squad.members.length} Agents
                        </text>

                        {/* Member Agents Chips */}
                        <g transform="translate(0, -6)">
                          <text
                            x="0"
                            y="0"
                            textAnchor="middle"
                            fill="#cbd5e1"
                            fontSize="9"
                            fontFamily="system-ui, sans-serif"
                          >
                            Members: {squad.members.map((m) => m.label || m.id.replace("agent_", "")).join(", ")}
                          </text>
                        </g>

                        {/* Squad Mission Subtitle */}
                        <text
                          x="0"
                          y="18"
                          textAnchor="middle"
                          fill="#94a3b8"
                          fontSize="8.5"
                          fontFamily="system-ui, sans-serif"
                        >
                          {squad.mission?.length > 40
                            ? squad.mission.substring(0, 38) + "..."
                            : squad.mission}
                        </text>

                        {/* Tool Badge */}
                        <g transform="translate(0, 38)">
                          <rect
                            x="-95"
                            y="-9"
                            width="190"
                            height="18"
                            rx="5"
                            fill="#111827"
                            stroke="rgba(255, 255, 255, 0.12)"
                            strokeWidth="1"
                          />
                          <text
                            x="0"
                            y="3.5"
                            textAnchor="middle"
                            fill="#38bdf8"
                            fontSize="8"
                            fontFamily="monospace"
                            fontWeight="600"
                          >
                            ⚙️ Tools: {squad.toolList.slice(0, 2).join(", ")}
                          </text>
                        </g>
                      </g>
                    );
                  })}
                </>
              )}

              {/* ========================================================= */}
              {/* MODE B: AGENT DETAIL VIEW (With Squad Bounding Hulls)     */}
              {/* ========================================================= */}
              {viewMode === "agent" && (
                <>
                  {/* Visual Squad Bounding Containers (Colored Hull Boxes) */}
                  {squadBoundingBoxes.map((hull) => (
                    <g key={`hull-${hull.squadId}`}>
                      <rect
                        x={hull.x}
                        y={hull.y}
                        width={hull.width}
                        height={hull.height}
                        rx="16"
                        fill={hull.fillColor}
                        stroke={hull.borderColor}
                        strokeWidth="1.5"
                        strokeDasharray="6 4"
                      />

                      {/* Header label on top-left of each squad hull */}
                      <g transform={`translate(${hull.x + 12}, ${hull.y - 12})`}>
                        <rect
                          x="0"
                          y="0"
                          width={Math.min(hull.width - 24, 210)}
                          height="22"
                          rx="6"
                          fill="#0f172a"
                          stroke={hull.borderColor}
                          strokeWidth="1.5"
                        />
                        <text
                          x="10"
                          y="15"
                          fill={hull.color}
                          fontSize="9.5"
                          fontWeight="800"
                          fontFamily="system-ui, sans-serif"
                        >
                          {hull.icon} {hull.shortName.toUpperCase()} ({hull.memberCount} AGENTS)
                        </text>
                      </g>
                    </g>
                  ))}

                  {/* Inter-Agent Interaction Edges */}
                  {localEdges.map((edge, idx) => {
                    const isSelected = selectedEdge?.key === edge.key || activeStepIdx === idx;
                    const srcSquad = SQUAD_METADATA[edge.from_squad || getAgentSquadId(edge.source)];
                    const tgtSquad = SQUAD_METADATA[edge.to_squad || getAgentSquadId(edge.target)];
                    const isCross = srcSquad?.id !== tgtSquad?.id;

                    const pathData = calculatePath(edge.source, edge.target, idx);
                    const edgeColor = getEdgeColor(edge.interaction_type, isSelected, isCross);

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
                        <path d={pathData.d} fill="none" stroke="transparent" strokeWidth="20" />

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
                          stroke={isCross ? "#f59e0b" : edgeColor}
                          strokeWidth={isSelected ? "3" : isCross ? "2.5" : "1.8"}
                          strokeOpacity={isSelected ? 1 : 0.75}
                          strokeDasharray={isCross ? "8 4" : isSelected ? "8 4" : "5 5"}
                          markerEnd={isCross ? "url(#arrow-bridge)" : "url(#arrow-default)"}
                        />

                        {/* Animated Flowing Packet */}
                        <circle r={isCross ? "5" : "4.5"} fill={isCross ? "#fbbf24" : edgeColor} filter="url(#glow)">
                          <animateMotion
                            path={pathData.d}
                            dur={`${2.0 + (idx % 3) * 0.4}s`}
                            repeatCount="indefinite"
                          />
                        </circle>

                        {/* Step Sequence Badge on Midpoint */}
                        <g transform={`translate(${pathData.midX}, ${pathData.midY})`}>
                          <circle
                            r={isSelected ? 11 : 9}
                            fill={isSelected ? "#38bdf8" : isCross ? "#b45309" : "#0f172a"}
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
                    const squad = SQUAD_METADATA[node.squadId || node.squad_id || getAgentSquadId(id)] || SQUAD_METADATA.squad_command;

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
                            stroke={squad.color || node.color || "#3b82f6"}
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

                        {/* Squad Badge Pill on Agent Card */}
                        <g transform="translate(0, 0)">
                          <rect
                            x="-72"
                            y="-6"
                            width="144"
                            height="14"
                            rx="4"
                            fill="rgba(0, 0, 0, 0.4)"
                            stroke={squad.borderColor}
                            strokeWidth="0.8"
                          />
                          <text
                            x="0"
                            y="4.5"
                            textAnchor="middle"
                            fill={squad.color}
                            fontSize="8"
                            fontWeight="700"
                            fontFamily="system-ui, sans-serif"
                          >
                            {squad.icon} {squad.shortName}
                          </text>
                        </g>

                        {/* Real Tool Badge */}
                        <g transform="translate(0, 24)">
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
                </>
              )}
            </svg>
          </div>

          {/* Bottom Interactive Inspector */}
          {(selectedSquad || selectedSquadEdge || selectedEdge || selectedNode) && (
            <div
              style={{
                marginTop: 10,
                background: "#0c1322",
                border: "1px solid #1e3a5f",
                borderRadius: 8,
                padding: "12px 16px",
                display: "grid",
                gridTemplateColumns: "1.4fr 1fr",
                gap: 12,
                fontSize: 12,
              }}
            >
              {/* INSPECTOR 1: Selected Squad Node in Squad View */}
              {selectedSquad ? (
                <>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <span style={{ fontSize: 18 }}>{selectedSquad.icon}</span>
                      <strong style={{ color: selectedSquad.color, fontSize: 14 }}>
                        {selectedSquad.name}
                      </strong>
                      <span
                        style={{
                          fontSize: 10,
                          background: "rgba(16, 185, 129, 0.15)",
                          color: "#34d399",
                          padding: "1px 6px",
                          borderRadius: 4,
                          fontWeight: 700,
                        }}
                      >
                        ● Active Squad
                      </span>
                    </div>
                    <div style={{ color: "#cbd5e1", fontSize: 11.5, marginBottom: 6, lineHeight: 1.4 }}>
                      <strong>Mission:</strong> {selectedSquad.mission}
                    </div>
                    <div style={{ fontSize: 11, color: "#94a3b8" }}>
                      <strong>Member Agents ({selectedSquad.members.length}):</strong>{" "}
                      {selectedSquad.members.map((m) => m.label || m.id).join(", ")}
                    </div>
                  </div>
                  <div style={{ fontSize: 11, color: "#94a3b8", display: "flex", flexDirection: "column", gap: 3 }}>
                    <div>
                      <strong>Squad ID:</strong> <code>{selectedSquad.id}</code>
                    </div>
                    <div>
                      <strong>Tool Suite:</strong>{" "}
                      <span style={{ color: "#38bdf8" }}>{selectedSquad.toolList.join(", ") || "CIM Specialized Tools"}</span>
                    </div>
                    <div>
                      <strong>Federation Status:</strong>{" "}
                      <span style={{ color: "#10b981" }}>Zero-Trust Enforced &bull; W3C Tracked</span>
                    </div>
                  </div>
                </>
              ) : selectedSquadEdge ? (
                /* INSPECTOR 2: Selected Squad Conduit in Squad View */
                <>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                      <span
                        style={{
                          background: selectedSquadEdge.isBridge ? "#b45309" : "#1e3a8a",
                          color: selectedSquadEdge.isBridge ? "#fef08a" : "#93c5fd",
                          padding: "2px 7px",
                          borderRadius: 4,
                          fontSize: 10,
                          fontWeight: 800,
                          textTransform: "uppercase",
                        }}
                      >
                        {selectedSquadEdge.isBridge ? "⚡ Cross-Squad Federation Bridge" : "Inter-Squad Conduit"}
                      </span>
                      <strong style={{ color: "#f8fafc" }}>
                        {SQUAD_METADATA[selectedSquadEdge.source]?.shortName} &rarr;{" "}
                        {SQUAD_METADATA[selectedSquadEdge.target]?.shortName}
                      </strong>
                    </div>
                    <div style={{ color: "#cbd5e1", lineHeight: 1.4 }}>
                      {selectedSquadEdge.isBridge
                        ? "Federated cross-squad bridge correlating CFPB Consumer Complaints with SecOps System Access Logs under Zero-Trust provenance tracking."
                        : `Conduit exchanging ${selectedSquadEdge.messageCount} inter-squad coordination messages.`}
                    </div>
                  </div>
                  <div style={{ fontSize: 11, color: "#94a3b8", display: "flex", flexDirection: "column", gap: 3 }}>
                    <div>
                      <strong>Messages Exchanged:</strong> {selectedSquadEdge.messageCount}
                    </div>
                    <div>
                      <strong>Protocol:</strong> <span>CIM Gateway / Envelope Exchange</span>
                    </div>
                    <div>
                      <strong>Types:</strong> <span>{selectedSquadEdge.types.join(", ") || "information_transfer"}</span>
                    </div>
                  </div>
                </>
              ) : selectedEdge ? (
                /* INSPECTOR 3: Selected Edge in Agent Detail View */
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
                /* INSPECTOR 4: Selected Agent Node in Agent Detail View */
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
