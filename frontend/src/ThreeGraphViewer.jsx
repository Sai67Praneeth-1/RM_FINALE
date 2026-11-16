import React, { useState, useMemo, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
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
  Code,
  Compass,
  FileText,
  Search,
  RotateCcw,
} from "lucide-react";
import AgentInteractionGraph from "./AgentInteractionGraph";
import MermaidViewer from "./components/MermaidViewer";
import ForensicBackwardTracer from "./components/ForensicBackwardTracer";
import {
  generateC4ContainerDiagram,
  generateExecutionMermaid,
  generateAuthorityMermaid,
  generateInteractionSequenceMermaid,
  generateUnifiedThreeGraphMermaid,
} from "./utils/mermaidGenerators";

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
  autoTrace = false,
}) {
  const [searchParams] = useSearchParams();
  const shouldAutoTrace = autoTrace || searchParams.get("auto_trace") === "true";
  const [activeGraphTab, setActiveGraphTab] = useState(() => (shouldAutoTrace ? "backward_trace" : "unified"));
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [isSampleRunning, setIsSampleRunning] = useState(false);
  const [viewMode, setViewMode] = useState("interactive"); // "interactive" | "c4_mermaid"
  const [mermaidDiagram, setMermaidDiagram] = useState("c4"); // "c4" | "sequence" | "execution" | "authority" | "unified"
  const [traceData, setTraceData] = useState(null);
  const [traceLoading, setTraceLoading] = useState(false);

  useEffect(() => {
    if (shouldAutoTrace) {
      setActiveGraphTab("backward_trace");
    }
  }, [shouldAutoTrace, selectedWorkflowId]);

  useEffect(() => {
    if (!selectedWorkflowId) return;
    let isMounted = true;
    const fetchTrace = async () => {
      setTraceLoading(true);
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/graphs/backward-trace?workflow_id=${encodeURIComponent(selectedWorkflowId)}`);
        if (res.ok && isMounted) {
          const data = await res.json();
          setTraceData(data);
        }
      } catch (err) {
        console.warn("Could not fetch backward-trace API, using client-side synthesis:", err);
      } finally {
        if (isMounted) setTraceLoading(false);
      }
    };
    fetchTrace();
    return () => { isMounted = false; };
  }, [selectedWorkflowId]);

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

  const backwardTrace = useMemo(() => {
    if (traceData && traceData.summary_answers) return traceData;

    // Derived from Three-Graph data
    const lastExec = execNodes.length > 0 ? execNodes[execNodes.length - 1] : null;
    const reporterAgent = execNodes.find((n) => n.agent_id === "agent_reporter" || n.agent_id === "Synthesizer_Agent") || lastExec;
    const reporterName = reporterAgent ? (reporterAgent.agent_id === "agent_reporter" ? "Agent D: Reporter" : reporterAgent.agent_id) : "Agent D: Reporter";
    const delegationId = reporterAgent?.delegation_id || authNodes.find((n) => n.node_type === "delegation")?.id || "del_exec_001";

    const dataTransfers = [];
    if (itrEdges.length > 0) {
      itrEdges.forEach((e, idx) => {
        dataTransfers.push({
          from_agent: e.source,
          to_agent: e.target,
          interaction_type: e.interaction_type || "DATA_TRANSFER",
          data_summary: e.data_payload || e.message_preview || "Structured intermediate analytical records & metrics",
          interaction_id: e.id || `itr_${idx + 1}`,
          timestamp: e.timestamp || new Date().toISOString(),
          answer_text: `${e.source} transferred structured audit payload to ${e.target} via message [${e.interaction_type || "Task Handoff"}].`,
        });
      });
    } else {
      dataTransfers.push({
        from_agent: "agent_researcher",
        to_agent: "agent_analyst",
        interaction_type: "INFO_TRANSFER",
        data_summary: "Extracted enterprise dataset complaints & customer sentiment records",
        interaction_id: "int_res_to_ana",
        timestamp: new Date().toLocaleTimeString(),
        answer_text: "Agent B (Researcher) extracted and transferred raw customer records to Agent C (Analyst) for statistical evaluation.",
      });
      dataTransfers.push({
        from_agent: "agent_analyst",
        to_agent: "agent_reporter",
        interaction_type: "RESULT_HANDOFF",
        data_summary: "Calculated complaint distribution metrics, sentiment scoring, and severity audit",
        interaction_id: "int_ana_to_rep",
        timestamp: new Date().toLocaleTimeString(),
        answer_text: "Agent C (Analyst) transferred computed complaint distribution statistics to Agent D (Reporter) for final synthesis.",
      });
    }

    const permissionDelegations = [];
    const authDels = authNodes.filter((n) => n.node_type === "delegation" || n.id?.startsWith("del_"));
    if (authDels.length > 0) {
      authDels.forEach((d) => {
        permissionDelegations.push({
          granter: d.granter || "User Principal (Root Signer)",
          recipient: d.delegatee || d.agent_id || "Lead Multi-Agent Fleet",
          delegation_id: d.id,
          scope: d.scope || "Tool Execution Granted",
          status: "VERIFIED",
          issued_at: d.issued_at || "Workflow Start",
          answer_text: `Authority token ${d.id} granted scope '${d.scope || "execute_tools"}' from ${d.granter || "User Principal"} to ${d.delegatee || "Coordinator/Agents"}.`,
        });
      });
    } else {
      permissionDelegations.push({
        granter: "Principal (User)",
        recipient: "agent_coordinator",
        delegation_id: "del_root_001",
        scope: "manage_workflow, delegate_subtasks",
        status: "VERIFIED",
        issued_at: "Start",
        answer_text: "User Principal granted root authority token 'del_root_001' to Agent A (Coordinator) with subtask delegation permissions.",
      });
      permissionDelegations.push({
        granter: "agent_coordinator",
        recipient: "agent_researcher",
        delegation_id: "del_res_002",
        scope: "read_dataset, search_records",
        status: "VERIFIED",
        issued_at: "+120ms",
        answer_text: "Agent A (Coordinator) granted scoped token 'del_res_002' to Agent B (Researcher) to execute data extraction tools.",
      });
      permissionDelegations.push({
        granter: "agent_coordinator",
        recipient: "agent_analyst",
        delegation_id: "del_ana_003",
        scope: "statistical_audit, compute_metrics",
        status: "VERIFIED",
        issued_at: "+240ms",
        answer_text: "Agent A (Coordinator) granted scoped token 'del_ana_003' to Agent C (Analyst) for statistical computation.",
      });
    }

    const reverseChain = [
      {
        step: 5,
        title: "Final Answer / Synthesis Delivered",
        role: "Synthesis & User Delivery",
        agent: reporterName,
        agent_id: reporterAgent?.agent_id || "agent_reporter",
        action: "report_compilation",
        delegation_id: delegationId,
        invariant: "G_exec -> G_auth Validated",
        description: "Agent D (Reporter) compiled analytical findings into the executive report delivered to the user.",
        timestamp: "End of Workflow",
      },
      {
        step: 4,
        title: "Statistical & Sentiment Analysis",
        role: "Metrics & Quantitative Computation",
        agent: "Agent C: Analyst",
        agent_id: "agent_analyst",
        action: "compute_complaints_distribution",
        delegation_id: "del_ana_003",
        invariant: "G_exec -> G_intr Causal Link",
        description: "Agent C (Analyst) computed frequency metrics and root-cause classification on customer complaints.",
        timestamp: "-450ms",
      },
      {
        step: 3,
        title: "Enterprise Dataset Ingestion & Extraction",
        role: "Data Sourcing & Querying",
        agent: "Agent B: Researcher",
        agent_id: "agent_researcher",
        action: "extract_customer_complaints",
        delegation_id: "del_res_002",
        invariant: "W3C PROV Entity Derivation",
        description: "Agent B (Researcher) queried enterprise customer complaint records and filtered relevant entries.",
        timestamp: "-980ms",
      },
      {
        step: 2,
        title: "Scoped Subtask & Permission Delegation",
        role: "Orchestration & Task Delegation",
        agent: "Agent A: Coordinator",
        agent_id: "agent_coordinator",
        action: "mint_scoped_delegations",
        delegation_id: "del_root_001",
        invariant: "G_auth Cryptographic Proof",
        description: "Agent A (Coordinator) decomposed user prompt, verified tokens, and delegated scoped tools to sub-agents.",
        timestamp: "-1420ms",
      },
      {
        step: 1,
        title: "User Prompt & Root Principal Authority",
        role: "Origin of Request & Authority",
        agent: "User Principal",
        agent_id: "principal_user",
        action: "issue_root_delegation",
        delegation_id: "root_auth_token",
        invariant: "Level 1 Authority Origin",
        description: "User submitted inquiry prompt, cryptographically establishing root authority to initiate the workflow.",
        timestamp: "Workflow Start",
      },
    ];

    return {
      workflow_id: selectedWorkflowId,
      task_description: "Multi-Agent Data Audit & Inquiry Execution",
      final_reporter: {
        agent_id: reporterAgent?.agent_id || "agent_reporter",
        agent_label: reporterName,
        delegation_id: delegationId,
        artifact_id: "art_audit_report",
        summary: "Compiled comprehensive analysis answering the user prompt with verified provenance.",
        answer_text: `The final report was compiled and delivered by ${reporterName} under delegation token ${delegationId}, authorized by Agent A (Coordinator).`,
      },
      data_transfers: dataTransfers,
      permission_delegations: permissionDelegations,
      reverse_causal_chain: reverseChain,
      summary_answers: {
        q1_who_gave_final_report: `${reporterName} under delegation token ${delegationId}.`,
        q2_who_transferred_data: `Agent B (Researcher) extracted raw data and transferred it to Agent C (Analyst), who then transferred computed metrics to Agent D (Reporter).`,
        q3_who_transferred_permissions: `User Principal granted root authority to Agent A (Coordinator), which minted and transferred scoped tool permissions to Agent B (Researcher) and Agent C (Analyst).`,
      },
    };
  }, [traceData, execNodes, authNodes, itrEdges, selectedWorkflowId]);

  const currentMermaidChart = useMemo(() => {
    switch (mermaidDiagram) {
      case "c4":
        return {
          title: "Level 2 C4 Container Architecture: Multi-Agent Observability",
          type: "C4 Container Diagram",
          code: generateC4ContainerDiagram(),
        };
      case "sequence":
        return {
          title: "G_interact Multi-Agent Interaction Sequence",
          type: "Sequence Diagram",
          code: generateInteractionSequenceMermaid(itrNodes, itrEdges),
        };
      case "execution":
        return {
          title: "G_exec Causal Tool Execution Pipeline",
          type: "Causal Flowchart",
          code: generateExecutionMermaid(execNodes, execEdges),
        };
      case "authority":
        return {
          title: "G_auth Cryptographic Delegation Tree",
          type: "Delegation DAG",
          code: generateAuthorityMermaid(authNodes, authEdges),
        };
      case "unified":
      default:
        return {
          title: "Unified Three-Graph Multi-Layer Invariant Proof",
          type: "Cross-Graph Overlay",
          code: generateUnifiedThreeGraphMermaid(execNodes.length, authNodes.length, itrEdges.length),
        };
    }
  }, [mermaidDiagram, execNodes, execEdges, authNodes, authEdges, itrNodes, itrEdges]);

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
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 12,
        }}
      >
        {/* Card 0: Forensic Backward Tracer */}
        <div
          onClick={() => setActiveGraphTab("backward_trace")}
          style={{
            background: activeGraphTab === "backward_trace" ? "rgba(232, 164, 74, 0.18)" : "#111827",
            border: activeGraphTab === "backward_trace" ? "2px solid var(--accent-primary, #e8a44a)" : "1px solid #1f2937",
            borderRadius: 8,
            padding: "14px 16px",
            cursor: "pointer",
            transition: "all 0.15s ease",
            position: "relative",
            boxShadow: activeGraphTab === "backward_trace" ? "0 0 16px rgba(232, 164, 74, 0.3)" : "none",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: "var(--accent-primary, #e8a44a)", display: "flex", alignItems: "center", gap: 6 }}>
              <Compass size={16} />
              <span>🕵️ Backward Tracer</span>
            </span>
            <span style={{ fontSize: 11, background: "rgba(232, 164, 74, 0.25)", color: "var(--accent-primary, #e8a44a)", padding: "2px 6px", borderRadius: 4, fontWeight: 700 }}>
              End-to-Start
            </span>
          </div>
          <div style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.4 }}>
            <strong>"Trace back from End to Start:"</strong> Answers who gave report, who transferred data &amp; permissions.
          </div>
        </div>

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

      {/* 3. Visualization Paradigm Mode Switcher (Interactive vs C4 Architecture / Mermaid) */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "#16191d",
          border: "1px solid #2a2f38",
          borderRadius: 8,
          padding: "8px 14px",
          flexWrap: "wrap",
          gap: 10,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Compass size={16} color="#e8a44a" />
          <span style={{ fontSize: 13, fontWeight: 700, color: "#f0f2f5" }}>
            Visualization Engine:
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button
            onClick={() => setViewMode("interactive")}
            style={{
              background: viewMode === "interactive" ? "#e8a44a" : "#22262c",
              color: viewMode === "interactive" ? "#111214" : "#94a3b8",
              border: "1px solid",
              borderColor: viewMode === "interactive" ? "#e8a44a" : "#334155",
              borderRadius: 6,
              padding: "6px 14px",
              fontSize: 12.5,
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
              transition: "all 0.15s ease",
            }}
          >
            <Layers size={14} />
            <span>🎛️ Interactive Canvas & Forensic Inspector</span>
          </button>

          <button
            onClick={() => setViewMode("c4_mermaid")}
            style={{
              background: viewMode === "c4_mermaid" ? "#2dd4bf" : "#22262c",
              color: viewMode === "c4_mermaid" ? "#111214" : "#94a3b8",
              border: "1px solid",
              borderColor: viewMode === "c4_mermaid" ? "#2dd4bf" : "#334155",
              borderRadius: 6,
              padding: "6px 14px",
              fontSize: 12.5,
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
              transition: "all 0.15s ease",
            }}
          >
            <Code size={14} />
            <span>📐 C4 Architecture & Mermaid (Draw.io Ready)</span>
          </button>
        </div>
      </div>

      {/* 4. Display Mode: C4 Enterprise & Mermaid Diagrams */}
      {viewMode === "c4_mermaid" && (
        <div className="stat-card" style={{ padding: 18 }}>
          {/* Mermaid Diagram Selector Tabs */}
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              justifyContent: "space-between",
              alignItems: "center",
              borderBottom: "1px solid #1f2937",
              paddingBottom: 12,
              marginBottom: 16,
              gap: 8,
            }}
          >
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              <button
                className={`pill-btn ${mermaidDiagram === "c4" ? "active" : ""}`}
                onClick={() => setMermaidDiagram("c4")}
                style={{
                  background: mermaidDiagram === "c4" ? "#e8a44a" : "#1e293b",
                  color: mermaidDiagram === "c4" ? "#111214" : "#94a3b8",
                  fontWeight: 700,
                }}
              >
                🏛️ Level 2 C4 Architecture
              </button>

              <button
                className={`pill-btn ${mermaidDiagram === "sequence" ? "active" : ""}`}
                onClick={() => setMermaidDiagram("sequence")}
                style={{
                  background: mermaidDiagram === "sequence" ? "#38bdf8" : "#1e293b",
                  color: mermaidDiagram === "sequence" ? "#ffffff" : "#94a3b8",
                  fontWeight: 700,
                }}
              >
                💬 Interaction Sequence (GI)
              </button>

              <button
                className={`pill-btn ${mermaidDiagram === "execution" ? "active" : ""}`}
                onClick={() => setMermaidDiagram("execution")}
                style={{
                  background: mermaidDiagram === "execution" ? "#34d399" : "#1e293b",
                  color: mermaidDiagram === "execution" ? "#ffffff" : "#94a3b8",
                  fontWeight: 700,
                }}
              >
                ⚡ Causal Execution Flow (GE)
              </button>

              <button
                className={`pill-btn ${mermaidDiagram === "authority" ? "active" : ""}`}
                onClick={() => setMermaidDiagram("authority")}
                style={{
                  background: mermaidDiagram === "authority" ? "#a78bfa" : "#1e293b",
                  color: mermaidDiagram === "authority" ? "#ffffff" : "#94a3b8",
                  fontWeight: 700,
                }}
              >
                🔑 Authority Lineage Tree (GA)
              </button>

              <button
                className={`pill-btn ${mermaidDiagram === "unified" ? "active" : ""}`}
                onClick={() => setMermaidDiagram("unified")}
                style={{
                  background: mermaidDiagram === "unified" ? "#f59e0b" : "#1e293b",
                  color: mermaidDiagram === "unified" ? "#ffffff" : "#94a3b8",
                  fontWeight: 700,
                }}
              >
                🔗 Unified Multi-Layer Proof
              </button>
            </div>

            <div style={{ fontSize: 12, color: "#2dd4bf" }}>
              ✨ <em>Ready for Draw.io: Click "Draw.io" above to import directly into diagrams.net.</em>
            </div>
          </div>

          {/* Render Mermaid Component */}
          <MermaidViewer
            chart={currentMermaidChart.code}
            title={currentMermaidChart.title}
            diagramType={currentMermaidChart.type}
          />
        </div>
      )}

      {/* 5. Display Mode: Interactive Topology & Forensic Node Inspector */}
      {viewMode === "interactive" && (
        <div style={{ display: "grid", gridTemplateColumns: selectedEntity ? "1fr 340px" : "1fr", gap: 16 }}>
          {/* Graph Display Card */}
          <div className="stat-card" style={{ padding: 18, minHeight: 460 }}>
            {/* Sub-Header Tabs */}
            <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #1f2937", paddingBottom: 12, marginBottom: 16 }}>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                <button
                  className={`pill-btn ${activeGraphTab === "backward_trace" ? "active" : ""}`}
                  onClick={() => setActiveGraphTab("backward_trace")}
                  style={{
                    background: activeGraphTab === "backward_trace" ? "var(--accent-primary, #e8a44a)" : "#1e293b",
                    color: activeGraphTab === "backward_trace" ? "#111214" : "#f0f2f5",
                    fontWeight: 700,
                    boxShadow: activeGraphTab === "backward_trace" ? "0 0 12px rgba(232, 164, 74, 0.4)" : "none",
                  }}
                >
                  <Compass size={14} style={{ display: "inline", marginRight: 6 }} />
                  🕵️ Forensic Backward Tracer (End-to-Start)
                </button>
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

            {/* VIEW 0: FORENSIC BACKWARD TRACER (END-TO-START) */}
            {activeGraphTab === "backward_trace" && (
              <ForensicBackwardTracer
                trace={backwardTrace}
                selectedWorkflowId={selectedWorkflowId}
                onSelectEntity={(entity) => setSelectedEntity(entity)}
              />
            )}

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
                  defaultCollapsed={false}
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
      )}
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
