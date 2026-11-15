import React, { useState, useEffect } from "react";
import {
  FileText,
  Share2,
  Key,
  Shield,
  Bot,
  User,
  ArrowLeft,
  ChevronRight,
  CheckCircle2,
  Play,
  RotateCcw,
  Sparkles,
  Layers,
  Search,
  ExternalLink,
  ShieldCheck,
  Zap,
} from "lucide-react";

export default function ForensicBackwardTracer({
  trace,
  onSelectEntity,
  selectedWorkflowId,
}) {
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [isReplaying, setIsReplaying] = useState(false);

  const steps = trace?.reverse_causal_chain || [];

  // Auto-replay effect
  useEffect(() => {
    let timer = null;
    if (isReplaying) {
      timer = setInterval(() => {
        setActiveStepIndex((prev) => {
          const next = prev + 1;
          if (next >= steps.length) {
            setIsReplaying(false);
            return prev;
          }
          if (onSelectEntity && steps[next]) {
            onSelectEntity({
              ...steps[next],
              id: steps[next].delegation_id || steps[next].action || steps[next].agent_id,
              label: `${steps[next].title} (${steps[next].agent})`,
              entityCategory: "Backward Trace Step",
            });
          }
          return next;
        });
      }, 1500);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isReplaying, steps, onSelectEntity]);

  const handleStartReplay = () => {
    setActiveStepIndex(0);
    setIsReplaying(true);
    if (steps.length > 0 && onSelectEntity) {
      onSelectEntity({
        ...steps[0],
        id: steps[0].delegation_id || steps[0].action || steps[0].agent_id,
        label: `${steps[0].title} (${steps[0].agent})`,
        entityCategory: "Backward Trace Step",
      });
    }
  };

  const handleStepClick = (step, idx) => {
    setIsReplaying(false);
    setActiveStepIndex(idx);
    if (onSelectEntity) {
      onSelectEntity({
        ...step,
        id: step.delegation_id || step.action || step.agent_id,
        label: `${step.title} (${step.agent})`,
        entityCategory: "Backward Trace Step",
      });
    }
  };

  if (!trace) {
    return (
      <div style={{ textAlign: "center", padding: "48px 20px", color: "var(--text-muted, #5c6472)" }}>
        <Zap size={36} color="var(--accent-primary, #e8a44a)" style={{ marginBottom: 12 }} />
        <div style={{ fontSize: 15, color: "var(--text-secondary, #9ba3b0)", fontWeight: 600 }}>
          Synthesizing Forensic Backward Lineage...
        </div>
        <div style={{ fontSize: 12.5, color: "var(--text-muted, #5c6472)", marginTop: 4 }}>
          Inspecting cross-graph causal records across Interaction, Execution & Authority graphs.
        </div>
      </div>
    );
  }

  const reporter = trace.final_reporter || {};
  const dataTransfers = trace.data_transfers || [];
  const permissionDelegations = trace.permission_delegations || [];
  const answers = trace.summary_answers || {};

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* 1. Forensic Header & Replay Action Bar */}
      <div
        style={{
          background: "linear-gradient(135deg, rgba(232, 164, 74, 0.12) 0%, rgba(45, 212, 191, 0.08) 100%)",
          border: "1px solid rgba(232, 164, 74, 0.4)",
          borderRadius: 8,
          padding: "16px 20px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 16,
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span
              style={{
                fontSize: 11,
                padding: "2px 8px",
                borderRadius: 4,
                background: "var(--accent-primary, #e8a44a)",
                color: "#111214",
                fontWeight: 800,
                letterSpacing: "0.05em",
                textTransform: "uppercase",
              }}
            >
              Forensic Audit
            </span>
            <span style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary, #f0f2f5)" }}>
              End-to-Start Reverse Lineage Reconstruction
            </span>
          </div>
          <div style={{ fontSize: 12.5, color: "var(--text-secondary, #9ba3b0)" }}>
            Workflow: <code style={{ color: "var(--accent-primary, #e8a44a)" }}>{trace.workflow_id || selectedWorkflowId}</code> &bull; Verified across G_exec, G_auth, and G_intr
          </div>
        </div>

        <button
          onClick={isReplaying ? () => setIsReplaying(false) : handleStartReplay}
          style={{
            background: isReplaying ? "rgba(232, 164, 74, 0.2)" : "var(--accent-primary, #e8a44a)",
            border: "1px solid var(--accent-primary, #e8a44a)",
            color: isReplaying ? "var(--accent-primary, #e8a44a)" : "#111214",
            padding: "8px 16px",
            borderRadius: 6,
            fontSize: 13,
            fontWeight: 700,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 8,
            transition: "all 0.15s ease",
            boxShadow: "0 2px 10px rgba(232, 164, 74, 0.3)",
          }}
        >
          {isReplaying ? <RotateCcw size={15} /> : <Play size={15} />}
          <span>{isReplaying ? `Replaying Step ${activeStepIndex + 1} of ${steps.length}...` : "⚡ Replay End-to-Start Causal Trace"}</span>
        </button>
      </div>

      {/* 2. Three Quick-Answer Cards for User Questions */}
      <div>
        <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted, #5c6472)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 10 }}>
          Forensic Answers &amp; Attribution Matrix
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 14 }}>
          {/* Card 1: Which agent gave the final report? */}
          <div
            style={{
              background: "var(--bg-surface, #1a1d21)",
              border: "1px solid rgba(232, 164, 74, 0.4)",
              borderRadius: 8,
              padding: 16,
              display: "flex",
              flexDirection: "column",
              gap: 12,
              position: "relative",
              boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: "var(--accent-primary, #e8a44a)", display: "flex", alignItems: "center", gap: 6 }}>
                <FileText size={15} />
                <span>1. Final Report Attribution</span>
              </span>
              <span
                style={{
                  fontSize: 10.5,
                  padding: "2px 6px",
                  borderRadius: 4,
                  background: "rgba(232, 164, 74, 0.18)",
                  color: "var(--accent-primary, #e8a44a)",
                  fontWeight: 600,
                }}
              >
                Synthesizer
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div
                style={{
                  width: 38,
                  height: 38,
                  borderRadius: 8,
                  background: "rgba(232, 164, 74, 0.15)",
                  border: "1px solid var(--accent-primary, #e8a44a)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--accent-primary, #e8a44a)",
                }}
              >
                <Bot size={22} />
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary, #f0f2f5)" }}>
                  {reporter.agent_label || "Agent D: Reporter"}
                </div>
                <div style={{ fontSize: 11, color: "var(--text-secondary, #9ba3b0)" }}>
                  Token: <code style={{ color: "var(--accent-primary, #e8a44a)" }}>{(reporter.delegation_id || "del_exec_001").substring(0, 16)}</code>
                </div>
              </div>
            </div>

            {/* Plain English explanation */}
            <div
              style={{
                background: "var(--bg-base, #111214)",
                padding: "10px 12px",
                borderRadius: 6,
                border: "1px solid var(--border-subtle, #2a2f38)",
                fontSize: 12,
                color: "var(--text-primary, #f0f2f5)",
                lineHeight: 1.5,
              }}
            >
              <strong>Answer:</strong> {reporter.answer_text || answers.q1_who_gave_final_report}
            </div>

            <button
              className="pill-btn"
              onClick={() =>
                onSelectEntity &&
                onSelectEntity({
                  ...reporter,
                  id: reporter.agent_id || "agent_reporter",
                  label: reporter.agent_label || "Agent D: Reporter",
                  entityCategory: "Final Reporting Agent",
                })
              }
              style={{
                fontSize: 11.5,
                background: "rgba(232, 164, 74, 0.1)",
                borderColor: "var(--accent-primary, #e8a44a)",
                color: "var(--accent-primary, #e8a44a)",
                width: "100%",
                justifyContent: "center",
              }}
            >
              <Search size={12} style={{ display: "inline", marginRight: 5 }} />
              Inspect Reporting Agent Node
            </button>
          </div>

          {/* Card 2: Which agent transferred data to which agent? */}
          <div
            style={{
              background: "var(--bg-surface, #1a1d21)",
              border: "1px solid rgba(45, 212, 191, 0.4)",
              borderRadius: 8,
              padding: 16,
              display: "flex",
              flexDirection: "column",
              gap: 12,
              position: "relative",
              boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: "var(--accent-secondary, #2dd4bf)", display: "flex", alignItems: "center", gap: 6 }}>
                <Share2 size={15} />
                <span>2. Inter-Agent Data Transfers</span>
              </span>
              <span
                style={{
                  fontSize: 10.5,
                  padding: "2px 6px",
                  borderRadius: 4,
                  background: "rgba(45, 212, 191, 0.18)",
                  color: "var(--accent-secondary, #2dd4bf)",
                  fontWeight: 600,
                }}
              >
                {dataTransfers.length} Transfers
              </span>
            </div>

            {/* Visual Mini Pipeline */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                background: "var(--bg-base, #111214)",
                padding: "8px 10px",
                borderRadius: 6,
                border: "1px solid var(--border-subtle, #2a2f38)",
                fontSize: 11,
              }}
            >
              <span style={{ color: "#60a5fa", fontWeight: 600 }}>Researcher</span>
              <span style={{ color: "var(--accent-secondary, #2dd4bf)" }}>&rarr; data &rarr;</span>
              <span style={{ color: "#fbbf24", fontWeight: 600 }}>Analyst</span>
              <span style={{ color: "var(--accent-secondary, #2dd4bf)" }}>&rarr; metrics &rarr;</span>
              <span style={{ color: "#a78bfa", fontWeight: 600 }}>Reporter</span>
            </div>

            {/* Plain English explanation */}
            <div
              style={{
                background: "var(--bg-base, #111214)",
                padding: "10px 12px",
                borderRadius: 6,
                border: "1px solid var(--border-subtle, #2a2f38)",
                fontSize: 12,
                color: "var(--text-primary, #f0f2f5)",
                lineHeight: 1.5,
              }}
            >
              <strong>Answer:</strong> {answers.q2_who_transferred_data || dataTransfers[0]?.answer_text}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 90, overflowY: "auto" }}>
              {dataTransfers.map((dt, idx) => (
                <div
                  key={idx}
                  onClick={() => onSelectEntity && onSelectEntity({ ...dt, entityCategory: "Data Transfer Message" })}
                  style={{
                    background: "#111214",
                    border: "1px solid #2a2f38",
                    padding: "6px 8px",
                    borderRadius: 4,
                    fontSize: 11,
                    cursor: "pointer",
                    display: "flex",
                    justifyContent: "space-between",
                  }}
                >
                  <span style={{ color: "var(--accent-secondary, #2dd4bf)", fontWeight: 600 }}>
                    {dt.from_agent} &rarr; {dt.to_agent}
                  </span>
                  <span style={{ color: "var(--text-muted, #5c6472)" }}>{dt.interaction_type}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Card 3: Which agent transferred permissions to use tools? */}
          <div
            style={{
              background: "var(--bg-surface, #1a1d21)",
              border: "1px solid rgba(52, 211, 153, 0.4)",
              borderRadius: 8,
              padding: 16,
              display: "flex",
              flexDirection: "column",
              gap: 12,
              position: "relative",
              boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: "var(--color-success, #34d399)", display: "flex", alignItems: "center", gap: 6 }}>
                <Key size={15} />
                <span>3. Permission &amp; Tool Delegations</span>
              </span>
              <span
                style={{
                  fontSize: 10.5,
                  padding: "2px 6px",
                  borderRadius: 4,
                  background: "rgba(52, 211, 153, 0.18)",
                  color: "var(--color-success, #34d399)",
                  fontWeight: 600,
                }}
              >
                {permissionDelegations.length} Verified Tokens
              </span>
            </div>

            {/* Visual Mini Hierarchy */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                background: "var(--bg-base, #111214)",
                padding: "8px 10px",
                borderRadius: 6,
                border: "1px solid var(--border-subtle, #2a2f38)",
                fontSize: 11,
              }}
            >
              <span style={{ color: "#e8a44a", fontWeight: 600 }}>Principal</span>
              <span style={{ color: "var(--color-success, #34d399)" }}>&rarr; root &rarr;</span>
              <span style={{ color: "#60a5fa", fontWeight: 600 }}>Coordinator</span>
              <span style={{ color: "var(--color-success, #34d399)" }}>&rarr; tools &rarr;</span>
              <span style={{ color: "#34d399", fontWeight: 600 }}>Sub-Agents</span>
            </div>

            {/* Plain English explanation */}
            <div
              style={{
                background: "var(--bg-base, #111214)",
                padding: "10px 12px",
                borderRadius: 6,
                border: "1px solid var(--border-subtle, #2a2f38)",
                fontSize: 12,
                color: "var(--text-primary, #f0f2f5)",
                lineHeight: 1.5,
              }}
            >
              <strong>Answer:</strong> {answers.q3_who_transferred_permissions || permissionDelegations[0]?.answer_text}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 90, overflowY: "auto" }}>
              {permissionDelegations.map((pd, idx) => (
                <div
                  key={idx}
                  onClick={() => onSelectEntity && onSelectEntity({ ...pd, entityCategory: "Authority Delegation Grant" })}
                  style={{
                    background: "#111214",
                    border: "1px solid #2a2f38",
                    padding: "6px 8px",
                    borderRadius: 4,
                    fontSize: 11,
                    cursor: "pointer",
                    display: "flex",
                    justifyContent: "space-between",
                  }}
                >
                  <span style={{ color: "var(--color-success, #34d399)", fontWeight: 600 }}>
                    {pd.granter} &rarr; {pd.recipient}
                  </span>
                  <span style={{ color: "var(--text-muted, #5c6472)" }}>{pd.scope}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 3. Interactive Reverse Causal Stepper (End-to-Start) */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary, #f0f2f5)", display: "flex", alignItems: "center", gap: 8 }}>
              <RotateCcw size={15} color="var(--accent-primary, #e8a44a)" />
              <span>Interactive Reverse Causal Chain (End ◀─── Start)</span>
            </div>
            <div style={{ fontSize: 12, color: "var(--text-secondary, #9ba3b0)" }}>
              Step backward in time from final result compilation to original root delegation origin.
            </div>
          </div>

          <div style={{ fontSize: 11.5, color: "var(--accent-primary, #e8a44a)", fontWeight: 600 }}>
            Active: Step {steps[activeStepIndex]?.step || activeStepIndex + 1}
          </div>
        </div>

        {/* Step Cards List */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {steps.map((st, idx) => {
            const isSelected = activeStepIndex === idx;

            return (
              <div
                key={idx}
                onClick={() => handleStepClick(st, idx)}
                style={{
                  background: isSelected ? "rgba(232, 164, 74, 0.12)" : "var(--bg-base, #111214)",
                  border: isSelected ? "2px solid var(--accent-primary, #e8a44a)" : "1px solid var(--border-subtle, #2a2f38)",
                  borderRadius: 8,
                  padding: "14px 18px",
                  cursor: "pointer",
                  transition: "all 0.18s ease",
                  boxShadow: isSelected ? "0 0 16px rgba(232, 164, 74, 0.3)" : "none",
                  display: "flex",
                  flexDirection: "column",
                  gap: 10,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div
                      style={{
                        width: 32,
                        height: 32,
                        borderRadius: "50%",
                        background: isSelected ? "var(--accent-primary, #e8a44a)" : "#22262c",
                        color: isSelected ? "#111214" : "#f0f2f5",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 13,
                        fontWeight: 800,
                      }}
                    >
                      {st.step}
                    </div>

                    <div>
                      <div style={{ fontSize: 13.5, fontWeight: 700, color: isSelected ? "var(--accent-primary, #e8a44a)" : "var(--text-primary, #f0f2f5)" }}>
                        {st.title}
                      </div>
                      <div style={{ fontSize: 11.5, color: "var(--text-secondary, #9ba3b0)" }}>
                        {st.role} &bull; <strong style={{ color: "#f0f2f5" }}>{st.agent}</strong>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span
                      style={{
                        fontSize: 10.5,
                        padding: "3px 8px",
                        borderRadius: 4,
                        background: "rgba(45, 212, 191, 0.15)",
                        color: "var(--accent-secondary, #2dd4bf)",
                        fontWeight: 600,
                        border: "1px solid rgba(45, 212, 191, 0.3)",
                      }}
                    >
                      {st.invariant}
                    </span>
                    <span
                      style={{
                        fontSize: 10.5,
                        padding: "3px 8px",
                        borderRadius: 4,
                        background: "rgba(167, 139, 250, 0.15)",
                        color: "var(--accent-tertiary, #a78bfa)",
                        fontWeight: 600,
                      }}
                    >
                      {st.timestamp || "Phase Link"}
                    </span>
                  </div>
                </div>

                <div style={{ fontSize: 12.5, color: "var(--text-primary, #f0f2f5)", lineHeight: 1.5, paddingLeft: 44 }}>
                  {st.description}
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 11, color: "var(--text-muted, #5c6472)", paddingLeft: 44 }}>
                  <span>Action: <code style={{ color: "#fbbf24" }}>{st.action}</code></span>
                  {st.delegation_id && (
                    <span>Delegation: <code style={{ color: "#34d399" }}>{st.delegation_id}</code></span>
                  )}
                  <span style={{ color: "var(--accent-primary, #e8a44a)", fontWeight: 600, marginLeft: "auto" }}>
                    Click to Inspect in Drawer &rarr;
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
