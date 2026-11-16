import React, { useState, useEffect, useMemo } from "react";
import {
  X,
  Compass,
  Sparkles,
  Maximize2,
} from "lucide-react";
import ForensicBackwardTracer from "./ForensicBackwardTracer";
import MermaidViewer from "./MermaidViewer";

const API_BASE = "http://127.0.0.1:8000/api";

export default function CommandGraphInspector({
  workflowId,
  chatId,
  onClose,
  onExpandFullScreen,
}) {
  const [activeTab, setActiveTab] = useState("stream"); // "stream" | "graphs" | "trace"
  const [loading, setLoading] = useState(true);
  const [commandData, setCommandData] = useState(null);
  const [selectedItem, setSelectedItem] = useState(null);
  const [graphSubTab, setGraphSubTab] = useState("sequence"); // "sequence" | "execution" | "authority"

  // Fetch command-level telemetry
  useEffect(() => {
    if (!workflowId) return;
    let isMounted = true;

    const fetchCommandTelemetry = async () => {
      setLoading(true);
      try {
        // 1. Try dedicated command endpoint
        if (chatId) {
          try {
            const res = await fetch(`${API_BASE}/chats/${chatId}/command/${workflowId}`);
            if (res.ok) {
              const data = await res.json();
              if (isMounted && data) {
                // Synthesize execution_stream from tool_calls and data_transfers if not explicitly provided
                let st = data.execution_stream || [];
                if (!st.length) {
                  (data.data_transfers || []).forEach((itr, idx) => {
                    st.push({
                      id: itr.interaction_id || `itr_${idx}`,
                      type: "interaction",
                      time: itr.timestamp || idx * 100,
                      from_agent: itr.from_agent_label || itr.from_agent || "Coordinator",
                      to_agent: itr.to_agent_label || itr.to_agent || "Agent",
                      semantic: itr.interaction_type || "Data Handoff",
                      preview: itr.data_summary || itr.answer_text || "Inter-agent data transfer",
                      is_cross_squad: itr.is_cross_squad,
                      raw: itr,
                    });
                  });
                  (data.tool_calls || []).forEach((ev, idx) => {
                    st.push({
                      id: ev.event_id || `ev_${idx}`,
                      type: "tool_execution",
                      time: ev.time || (idx + 1) * 150,
                      agent: ev.agent_id || "Executor",
                      tool_name: ev.tool_name || "Tool",
                      operation: ev.tool_operation || "execute",
                      resource_id: ev.resource_id,
                      delegation_id: ev.delegation_id,
                      outcome: ev.outcome || "success",
                      raw: ev,
                    });
                  });
                }
                data.execution_stream = st;
                setCommandData(data);
                setLoading(false);
                return;
              }
            }
          } catch (e1) {
            console.warn("Primary /chats/command endpoint failed, falling back to parallel fetch:", e1);
          }
        }

        // 2. Parallel fallback: fetch graphs, backward-trace, events, interactions
        const [graphsRes, traceRes, eventsRes, interactionsRes] = await Promise.allSettled([
          fetch(`${API_BASE}/graphs/${workflowId}`).then((r) => (r.ok ? r.json() : null)),
          fetch(`${API_BASE}/graphs/backward-trace?workflow_id=${workflowId}`).then((r) => (r.ok ? r.json() : null)),
          fetch(`${API_BASE}/events?workflow_id=${workflowId}&limit=100`).then((r) => (r.ok ? r.json() : [])),
          fetch(`${API_BASE}/interactions?workflow_id=${workflowId}`).then((r) => (r.ok ? r.json() : [])),
        ]);

        const graphs = graphsRes.status === "fulfilled" ? graphsRes.value : null;
        const trace = traceRes.status === "fulfilled" ? traceRes.value : null;
        const events = eventsRes.status === "fulfilled" ? eventsRes.value || [] : [];
        const interactions = interactionsRes.status === "fulfilled" ? interactionsRes.value || [] : [];

        // Synthesize chronological stream
        const stream = [];
        (interactions || []).forEach((itr, idx) => {
          stream.push({
            id: itr.id || `itr_${idx}`,
            type: "interaction",
            time: itr.timestamp || idx * 100,
            from_agent: itr.source || itr.from_agent || "Coordinator",
            to_agent: itr.target || itr.to_agent || "Agent",
            semantic: itr.interaction_type || "Task Delegation",
            preview: itr.data_payload || itr.message_preview || "Dispatched scoped analytical subtask",
            raw: itr,
          });
        });

        (events || []).forEach((ev, idx) => {
          stream.push({
            id: ev.event_id || ev.id || `ev_${idx}`,
            type: "tool_execution",
            time: ev.time || ev.timestamp || (idx + 1) * 150,
            agent: ev.agent_id || "Executor",
            tool_name: ev.tool_name || "Tool",
            operation: ev.tool_operation || ev.action_semantic || "execute",
            resource_id: ev.resource_id,
            delegation_id: ev.delegation_id,
            outcome: ev.outcome || "success",
            raw: ev,
          });
        });

        // Sort chronologically
        stream.sort((a, b) => (a.time > b.time ? 1 : -1));

        if (isMounted) {
          setCommandData({
            workflow_id: workflowId,
            chat_id: chatId,
            command_prompt: `Command Investigation (${workflowId})`,
            execution_stream: stream,
            three_graphs: graphs || { execution_graph: { nodes: events, edges: [] }, authority_graph: { nodes: [], edges: [] }, interaction_graph: { nodes: [], edges: interactions } },
            backward_trace: trace,
          });
        }
      } catch (err) {
        console.error("Failed to load command telemetry:", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchCommandTelemetry();
    return () => {
      isMounted = false;
    };
  }, [workflowId, chatId]);

  const stream = commandData?.execution_stream || [];
  const trace = useMemo(() => {
    if (commandData?.backward_trace) return commandData.backward_trace;
    if (commandData?.forensic_backward_trace || commandData?.answers) {
      return {
        workflow_id: commandData.workflow_id,
        task_description: commandData.task_description,
        final_reporter: commandData.answers?.final_reporter,
        data_transfers: commandData.answers?.data_transfers || commandData.data_transfers || [],
        permission_delegations: commandData.answers?.permission_delegations || commandData.permission_delegations || [],
        reverse_causal_chain: commandData.forensic_backward_trace || [],
        summary_answers: {
          q1_final_reporter: commandData.answers?.final_reporter?.answer_text,
          q2_data_transfers: (commandData.answers?.data_transfers || []).map((d) => d.answer_text),
          q3_permission_delegations: (commandData.answers?.permission_delegations || []).map((p) => p.answer_text),
        },
      };
    }
    return null;
  }, [commandData]);

  // Generate dynamic Mermaid sequence diagram for this command
  const mermaidSequenceChart = useMemo(() => {
    if (commandData?.mermaid_charts?.sequence) return commandData.mermaid_charts.sequence;
    const lines = ["sequenceDiagram", "  autonumber"];
    lines.push("  actor User as Principal (User)");
    lines.push("  participant Coord as Coordinator (Agent A)");
    lines.push("  participant Res as Researcher (Agent B)");
    lines.push("  participant Ana as Analyst (Agent C)");
    lines.push("  participant Rep as Reporter (Agent D)");
    lines.push("  User->>Coord: Submit Prompt & Mint Root Delegation");
    lines.push("  Coord->>Res: Delegate Extraction Task & Tool Token");
    lines.push("  Res->>Res: Query Datasets (execute_tool)");
    lines.push("  Res->>Ana: Transfer Extracted Records (Data Handoff)");
    lines.push("  Ana->>Ana: Compute Statistics & Anomaly Audit");
    lines.push("  Ana->>Rep: Transfer Analytical Metrics & Scores");
    lines.push("  Rep->>Rep: Compile Final Report & Synthesize Answer");
    lines.push("  Rep-->>User: Deliver Answer with Provenance Chain");
    return lines.join("\n");
  }, [commandData]);

  const mermaidExecutionChart = useMemo(() => {
    if (commandData?.mermaid_charts?.execution) return commandData.mermaid_charts.execution;
    const lines = ["graph TD"];
    lines.push("  Start([User Prompt]) --> D1[Root Authority Token: del_root]");
    lines.push("  D1 --> E1[Extract Customer Complaints: Researcher]");
    lines.push("  E1 --> E2[Compute Distribution Metrics: Analyst]");
    lines.push("  E2 --> E3[Synthesize Final Executive Report: Reporter]");
    lines.push("  E3 --> Output([Final Answer Delivered to Chat])");
    lines.push("  style Start fill:#e8f0fe,stroke:#1a73e8,stroke-width:2px;");
    lines.push("  style Output fill:#e6f4ea,stroke:#137333,stroke-width:2px;");
    lines.push("  style E1 fill:#ffffff,stroke:#dadce0,stroke-width:1px;");
    lines.push("  style E2 fill:#ffffff,stroke:#dadce0,stroke-width:1px;");
    lines.push("  style E3 fill:#ffffff,stroke:#dadce0,stroke-width:1px;");
    return lines.join("\n");
  }, [commandData]);

  const mermaidAuthorityChart = useMemo(() => {
    if (commandData?.mermaid_charts?.authority) return commandData.mermaid_charts.authority;
    const lines = ["graph TD"];
    lines.push("  P[Principal / Root Signer] -->|Root Delegation| C[Coordinator Agent]");
    lines.push("  C -->|Scoped Token: del_res| R[Researcher: read_dataset]");
    lines.push("  C -->|Scoped Token: del_ana| A[Analyst: compute_metrics]");
    lines.push("  C -->|Scoped Token: del_rep| S[Reporter: compile_report]");
    lines.push("  style P fill:#f1f3f4,stroke:#1a73e8,stroke-width:2px;");
    lines.push("  style C fill:#ffffff,stroke:#dadce0,stroke-width:1.5px;");
    lines.push("  style R fill:#ffffff,stroke:#dadce0,stroke-width:1px;");
    lines.push("  style A fill:#ffffff,stroke:#dadce0,stroke-width:1px;");
    lines.push("  style S fill:#ffffff,stroke:#dadce0,stroke-width:1px;");
    return lines.join("\n");
  }, [commandData]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: "#ffffff",
        border: "1px solid #dadce0",
        borderRadius: 8,
        overflow: "hidden",
        boxShadow: "0 1px 3px 1px rgba(60,64,67,0.15)",
      }}
    >
      {/* 1. Header with Command Context & Actions */}
      <div
        style={{
          padding: "14px 18px",
          background: "#ffffff",
          borderBottom: "1px solid #dadce0",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: "#e8f0fe",
              border: "1px solid #d2e3fc",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#1a73e8",
              flexShrink: 0,
            }}
          >
            <Compass size={17} />
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 13.5, fontWeight: 600, color: "#202124", whiteSpace: "nowrap" }}>
                Command Inspector
              </span>
              <span
                style={{
                  fontSize: 10,
                  padding: "2px 8px",
                  borderRadius: 16,
                  background: "#e6f4ea",
                  color: "#137333",
                  border: "1px solid #ceead6",
                  fontWeight: 700,
                  letterSpacing: "0.04em",
                }}
              >
                LIVE TELEMETRY
              </span>
            </div>
            <div style={{ fontSize: 11, color: "#5f6368", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              Workflow: <code style={{ color: "#1a73e8", background: "#f1f3f4", padding: "1px 6px", borderRadius: 4 }}>{workflowId}</code>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
          {onExpandFullScreen && (
            <button
              onClick={() => onExpandFullScreen(workflowId)}
              style={{
                fontSize: 11,
                padding: "5px 12px",
                display: "flex",
                alignItems: "center",
                gap: 4,
                background: "#e8f0fe",
                color: "#1a73e8",
                border: "1px solid #d2e3fc",
                borderRadius: 24,
                cursor: "pointer",
                fontWeight: 600,
                transition: "all 0.15s ease",
              }}
              title="Expand to Full-Page Three-Graph Explorer"
            >
              <Maximize2 size={12} />
              <span>Full Page</span>
            </button>
          )}

          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "#5f6368",
              cursor: "pointer",
              padding: 6,
              borderRadius: 20,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "background 0.15s ease, color 0.15s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "#202124";
              e.currentTarget.style.background = "#f1f3f4";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = "#5f6368";
              e.currentTarget.style.background = "transparent";
            }}
            title="Close Inspector"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* 2. Top Nav Tabs for the Inspector */}
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid #dadce0",
          background: "#f8f9fa",
          padding: "0 12px",
          gap: 6,
        }}
      >
        {[
          { id: "stream", label: "⚡ Execution Stream", count: stream.length },
          { id: "graphs", label: "📊 Command Graphs & Mermaid" },
          { id: "trace", label: "🕵️ Backward Trace (End-to-Start)" },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            style={{
              padding: "10px 14px",
              background: "transparent",
              border: "none",
              borderBottom: activeTab === t.id ? "2px solid #1a73e8" : "2px solid transparent",
              color: activeTab === t.id ? "#1a73e8" : "#5f6368",
              fontSize: 12,
              fontWeight: activeTab === t.id ? 600 : 500,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
              transition: "all 0.15s ease",
            }}
          >
            <span>{t.label}</span>
            {t.count !== undefined && (
              <span
                style={{
                  fontSize: 10,
                  padding: "1px 6px",
                  borderRadius: 12,
                  background: activeTab === t.id ? "#e8f0fe" : "#f1f3f4",
                  color: activeTab === t.id ? "#1a73e8" : "#5f6368",
                  fontWeight: 600,
                }}
              >
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* 3. Content Body (Scrollable) */}
      <div style={{ flex: 1, overflowY: "auto", padding: 16, background: "#ffffff" }}>
        {loading ? (
          <div style={{ textAlign: "center", padding: "40px 20px", color: "#5f6368" }}>
            <Sparkles size={28} color="#1a73e8" style={{ marginBottom: 10, animation: "spin 2s linear infinite" }} />
            <div style={{ fontSize: 13, color: "#202124", fontWeight: 600 }}>Loading Command Telemetry...</div>
          </div>
        ) : (
          <>
            {/* TAB 1: EXECUTION STREAM */}
            {activeTab === "stream" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 11.5, color: "#5f6368" }}>
                  <span>Chronological Multi-Agent Actions &bull; {stream.length} Events</span>
                  <span style={{ color: "#1a73e8", fontWeight: 600 }}>Command: {workflowId}</span>
                </div>

                {stream.length === 0 ? (
                  <div style={{ textAlign: "center", padding: "36px 16px", color: "#5f6368", fontSize: 13 }}>
                    No tool executions or inter-agent interactions recorded for this turn.
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {stream.map((item, idx) => {
                      const isInteraction = item.type === "interaction";
                      const isSelected = selectedItem?.id === item.id;

                      return (
                        <div
                          key={item.id || idx}
                          onClick={() => setSelectedItem(item)}
                          style={{
                            background: isSelected ? "#e8f0fe" : "#ffffff",
                            border: isSelected ? "1px solid #1a73e8" : "1px solid #dadce0",
                            borderRadius: 8,
                            padding: "10px 12px",
                            cursor: "pointer",
                            transition: "all 0.15s ease",
                            display: "flex",
                            flexDirection: "column",
                            gap: 6,
                            boxShadow: isSelected ? "0 1px 3px 1px rgba(60,64,67,0.15)" : "none",
                          }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                              <span
                                style={{
                                  fontSize: 10,
                                  padding: "2px 8px",
                                  borderRadius: 16,
                                  background: isInteraction ? "#e8f0fe" : "#fef7e0",
                                  color: isInteraction ? "#1a73e8" : "#b06000",
                                  border: isInteraction ? "1px solid #d2e3fc" : "1px solid #feefc3",
                                  fontWeight: 700,
                                  letterSpacing: "0.03em",
                                }}
                              >
                                {isInteraction ? "INTERACTION" : "TOOL CALL"}
                              </span>
                              <span style={{ fontSize: 12.5, fontWeight: 600, color: "#202124" }}>
                                {isInteraction ? `${item.from_agent} → ${item.to_agent}` : `${item.agent}: ${item.tool_name}`}
                              </span>
                            </div>

                            <span style={{ fontSize: 10.5, color: "#5f6368" }}>
                              Step {idx + 1}
                            </span>
                          </div>

                          <div style={{ fontSize: 11.5, color: "#3c4043", lineHeight: 1.4 }}>
                            {isInteraction ? item.preview : `Operation: ${item.operation}`}
                          </div>

                          {!isInteraction && item.resource_id && (
                            <div style={{ fontSize: 10.5, color: "#5f6368", display: "flex", gap: 12 }}>
                              <span>Target: <code style={{ color: "#1a73e8", background: "#f1f3f4", padding: "1px 4px", borderRadius: 4 }}>{item.resource_id}</code></span>
                              {item.delegation_id && (
                                <span>Token: <code style={{ color: "#137333", background: "#f1f3f4", padding: "1px 4px", borderRadius: 4 }}>{item.delegation_id.substring(0, 14)}...</code></span>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Selected Item Detail Inspector */}
                {selectedItem && (
                  <div
                    style={{
                      marginTop: 10,
                      padding: 12,
                      background: "#f8f9fa",
                      borderRadius: 8,
                      border: "1px solid #dadce0",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                      <span style={{ fontSize: 11, fontWeight: 700, color: "#1a73e8" }}>
                        Payload &amp; Invariant Proof
                      </span>
                      <button
                        onClick={() => setSelectedItem(null)}
                        style={{ background: "transparent", border: "none", color: "#5f6368", cursor: "pointer", padding: 2 }}
                      >
                        <X size={14} />
                      </button>
                    </div>
                    <pre style={{ margin: 0, fontSize: 10.5, color: "#202124", overflowX: "auto", fontFamily: "Roboto Mono, monospace" }}>
                      {JSON.stringify(selectedItem.raw || selectedItem, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: COMMAND THREE-GRAPHS & MERMAID */}
            {activeTab === "graphs" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                {/* Sub-selector */}
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap", borderBottom: "1px solid #dadce0", paddingBottom: 10 }}>
                  {[
                    { id: "sequence", label: "Sequence Diagram" },
                    { id: "execution", label: "Causal Execution" },
                    { id: "authority", label: "Authority Tree" },
                  ].map((sub) => (
                    <button
                      key={sub.id}
                      onClick={() => setGraphSubTab(sub.id)}
                      style={{
                        padding: "6px 14px",
                        borderRadius: 24,
                        fontSize: 11.5,
                        fontWeight: graphSubTab === sub.id ? 600 : 500,
                        background: graphSubTab === sub.id ? "#1a73e8" : "#ffffff",
                        color: graphSubTab === sub.id ? "#ffffff" : "#3c4043",
                        border: graphSubTab === sub.id ? "1px solid #1a73e8" : "1px solid #dadce0",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                    >
                      {sub.label}
                    </button>
                  ))}
                </div>

                {/* Render Mermaid Chart */}
                <div style={{ background: "#ffffff", borderRadius: 8, border: "1px solid #dadce0", padding: 10 }}>
                  {graphSubTab === "sequence" && (
                    <MermaidViewer
                      chart={mermaidSequenceChart}
                      title={`Command Sequence: ${workflowId}`}
                      diagramType="Sequence Diagram"
                    />
                  )}
                  {graphSubTab === "execution" && (
                    <MermaidViewer
                      chart={mermaidExecutionChart}
                      title={`Execution Flow: ${workflowId}`}
                      diagramType="Flowchart"
                    />
                  )}
                  {graphSubTab === "authority" && (
                    <MermaidViewer
                      chart={mermaidAuthorityChart}
                      title={`Authority Tree: ${workflowId}`}
                      diagramType="Delegation Tree"
                    />
                  )}
                </div>
              </div>
            )}

            {/* TAB 3: FORENSIC BACKWARD TRACE */}
            {activeTab === "trace" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <ForensicBackwardTracer
                  trace={trace}
                  selectedWorkflowId={workflowId}
                  onSelectEntity={(entity) => setSelectedItem(entity)}
                />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
