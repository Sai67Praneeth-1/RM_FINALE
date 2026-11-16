import React, { useState, useEffect } from "react";
import {
  FileText,
  Share2,
  Key,
  Bot,
  RotateCcw,
  Play,
  Search,
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
      <div style={{ textAlign: "center", padding: "48px 20px", color: "#5f6368" }}>
        <Zap size={36} color="#1a73e8" style={{ marginBottom: 12 }} />
        <div style={{ fontSize: 15, color: "#202124", fontWeight: 600 }}>
          Synthesizing Forensic Backward Lineage...
        </div>
        <div style={{ fontSize: 12.5, color: "#5f6368", marginTop: 4 }}>
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
          background: "#f8f9fa",
          border: "1px solid #dadce0",
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
                borderRadius: 16,
                background: "#e8f0fe",
                color: "#1a73e8",
                fontWeight: 700,
                letterSpacing: "0.04em",
                textTransform: "uppercase",
                border: "1px solid #d2e3fc",
              }}
            >
              Forensic Audit
            </span>
            <span style={{ fontSize: 15, fontWeight: 600, color: "#202124" }}>
              End-to-Start Reverse Lineage Reconstruction
            </span>
          </div>
          <div style={{ fontSize: 12.5, color: "#5f6368" }}>
            Workflow: <code style={{ color: "#1a73e8", background: "#f1f3f4", padding: "1px 6px", borderRadius: 4 }}>{trace.workflow_id || selectedWorkflowId}</code> &bull; Verified across G_exec, G_auth, and G_intr
          </div>
        </div>

        <button
          onClick={isReplaying ? () => setIsReplaying(false) : handleStartReplay}
          style={{
            background: isReplaying ? "#ffffff" : "#1a73e8",
            border: isReplaying ? "1px solid #dadce0" : "1px solid #1a73e8",
            color: isReplaying ? "#1a73e8" : "#ffffff",
            padding: "8px 18px",
            borderRadius: 24,
            fontSize: 13,
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 8,
            transition: "all 0.15s ease",
            boxShadow: "0 1px 3px 1px rgba(60,64,67,0.15)",
          }}
        >
          {isReplaying ? <RotateCcw size={15} /> : <Play size={15} />}
          <span>{isReplaying ? `Replaying Step ${activeStepIndex + 1} of ${steps.length}...` : "Replay End-to-Start Causal Trace"}</span>
        </button>
      </div>

      {/* 2. Three Quick-Answer Cards for User Questions */}
      <div>
        <div style={{ fontSize: 11, fontWeight: 700, color: "#5f6368", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 10 }}>
          Forensic Answers &amp; Attribution Matrix
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 14 }}>
          {/* Card 1: Which agent gave the final report? */}
          <div
            style={{
              background: "#ffffff",
              border: "1px solid #dadce0",
              borderRadius: 8,
              padding: 16,
              display: "flex",
              flexDirection: "column",
              gap: 12,
              position: "relative",
              boxShadow: "none",
              transition: "box-shadow 0.15s ease",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: "#1a73e8", display: "flex", alignItems: "center", gap: 6 }}>
                <FileText size={15} />
                <span>1. Final Report Attribution</span>
              </span>
              <span
                style={{
                  fontSize: 10.5,
                  padding: "2px 8px",
                  borderRadius: 16,
                  background: "#e8f0fe",
                  color: "#1a73e8",
                  border: "1px solid #d2e3fc",
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
                  background: "#e8f0fe",
                  border: "1px solid #d2e3fc",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#1a73e8",
                }}
              >
                <Bot size={22} />
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: "#202124" }}>
                  {reporter.agent_label || "Agent D: Reporter"}
                </div>
                <div style={{ fontSize: 11, color: "#5f6368" }}>
                  Token: <code style={{ color: "#1a73e8", background: "#f1f3f4", padding: "1px 4px", borderRadius: 4 }}>{(reporter.delegation_id || "del_exec_001").substring(0, 16)}</code>
                </div>
              </div>
            </div>

            {/* Plain English explanation */}
            <div
              style={{
                background: "#f8f9fa",
                padding: "10px 12px",
                borderRadius: 8,
                border: "1px solid #dadce0",
                fontSize: 12,
                color: "#202124",
                lineHeight: 1.5,
              }}
            >
              <strong>Answer:</strong> {reporter.answer_text || answers.q1_who_gave_final_report}
            </div>

            <button
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
                background: "#ffffff",
                border: "1px solid #dadce0",
                color: "#1a73e8",
                borderRadius: 24,
                padding: "6px 12px",
                cursor: "pointer",
                fontWeight: 600,
                width: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 5,
                transition: "all 0.15s ease",
              }}
            >
              <Search size={12} />
              Inspect Reporting Agent Node
            </button>
          </div>

          {/* Card 2: Which agent transferred data to which agent? */}
          <div
            style={{
              background: "#ffffff",
              border: "1px solid #dadce0",
              borderRadius: 8,
              padding: 16,
              display: "flex",
              flexDirection: "column",
              gap: 12,
              position: "relative",
              boxShadow: "none",
              transition: "box-shadow 0.15s ease",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: "#1a73e8", display: "flex", alignItems: "center", gap: 6 }}>
                <Share2 size={15} />
                <span>2. Inter-Agent Data Transfers</span>
              </span>
              <span
                style={{
                  fontSize: 10.5,
                  padding: "2px 8px",
                  borderRadius: 16,
                  background: "#e8f0fe",
                  color: "#1a73e8",
                  border: "1px solid #d2e3fc",
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
                background: "#f8f9fa",
                padding: "8px 10px",
                borderRadius: 8,
                border: "1px solid #dadce0",
                fontSize: 11,
              }}
            >
              <span style={{ color: "#1a73e8", fontWeight: 600 }}>Researcher</span>
              <span style={{ color: "#5f6368" }}>&rarr; data &rarr;</span>
              <span style={{ color: "#b06000", fontWeight: 600 }}>Analyst</span>
              <span style={{ color: "#5f6368" }}>&rarr; metrics &rarr;</span>
              <span style={{ color: "#137333", fontWeight: 600 }}>Reporter</span>
            </div>

            {/* Plain English explanation */}
            <div
              style={{
                background: "#f8f9fa",
                padding: "10px 12px",
                borderRadius: 8,
                border: "1px solid #dadce0",
                fontSize: 12,
                color: "#202124",
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
                    background: "#ffffff",
                    border: "1px solid #dadce0",
                    padding: "6px 8px",
                    borderRadius: 6,
                    fontSize: 11,
                    cursor: "pointer",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    transition: "background 0.15s ease",
                  }}
                >
                  <span style={{ color: "#1a73e8", fontWeight: 600, display: "flex", alignItems: "center", gap: 5 }}>
                    {dt.is_cross_squad && <span style={{ background: "#fef7e0", color: "#b06000", border: "1px solid #feefc3", fontSize: 8.5, padding: "1px 4px", borderRadius: 4, fontWeight: 700 }}>SQUAD BRIDGE</span>}
                    <span>{dt.from_agent} &rarr; {dt.to_agent}</span>
                  </span>
                  <span style={{ color: "#5f6368", fontSize: 10 }}>{dt.interaction_type}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Card 3: Which agent transferred permissions to use tools? */}
          <div
            style={{
              background: "#ffffff",
              border: "1px solid #dadce0",
              borderRadius: 8,
              padding: 16,
              display: "flex",
              flexDirection: "column",
              gap: 12,
              position: "relative",
              boxShadow: "none",
              transition: "box-shadow 0.15s ease",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: "#137333", display: "flex", alignItems: "center", gap: 6 }}>
                <Key size={15} />
                <span>3. Permission &amp; Tool Delegations</span>
              </span>
              <span
                style={{
                  fontSize: 10.5,
                  padding: "2px 8px",
                  borderRadius: 16,
                  background: "#e6f4ea",
                  color: "#137333",
                  border: "1px solid #ceead6",
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
                background: "#f8f9fa",
                padding: "8px 10px",
                borderRadius: 8,
                border: "1px solid #dadce0",
                fontSize: 11,
              }}
            >
              <span style={{ color: "#5f6368", fontWeight: 600 }}>Principal</span>
              <span style={{ color: "#137333" }}>&rarr; root &rarr;</span>
              <span style={{ color: "#1a73e8", fontWeight: 600 }}>Coordinator</span>
              <span style={{ color: "#137333" }}>&rarr; tools &rarr;</span>
              <span style={{ color: "#137333", fontWeight: 600 }}>Sub-Agents</span>
            </div>

            {/* Plain English explanation */}
            <div
              style={{
                background: "#f8f9fa",
                padding: "10px 12px",
                borderRadius: 8,
                border: "1px solid #dadce0",
                fontSize: 12,
                color: "#202124",
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
                    background: "#ffffff",
                    border: "1px solid #dadce0",
                    padding: "6px 8px",
                    borderRadius: 6,
                    fontSize: 11,
                    cursor: "pointer",
                    display: "flex",
                    justifyContent: "space-between",
                    transition: "background 0.15s ease",
                  }}
                >
                  <span style={{ color: "#137333", fontWeight: 600 }}>
                    {pd.granter} &rarr; {pd.recipient}
                  </span>
                  <span style={{ color: "#5f6368" }}>{pd.scope}</span>
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
            <div style={{ fontSize: 13, fontWeight: 600, color: "#202124", display: "flex", alignItems: "center", gap: 8 }}>
              <RotateCcw size={15} color="#1a73e8" />
              <span>Interactive Reverse Causal Chain (End ◀─── Start)</span>
            </div>
            <div style={{ fontSize: 12, color: "#5f6368" }}>
              Step backward in time from final result compilation to original root delegation origin.
            </div>
          </div>

          <div style={{ fontSize: 11.5, color: "#1a73e8", fontWeight: 600 }}>
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
                  background: isSelected ? "#e8f0fe" : "#ffffff",
                  border: isSelected ? "2px solid #1a73e8" : "1px solid #dadce0",
                  borderRadius: 8,
                  padding: "14px 18px",
                  cursor: "pointer",
                  transition: "all 0.18s ease",
                  boxShadow: isSelected ? "0 1px 3px 1px rgba(60,64,67,0.15)" : "none",
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
                        background: isSelected ? "#1a73e8" : "#f1f3f4",
                        color: isSelected ? "#ffffff" : "#3c4043",
                        border: isSelected ? "1px solid #1a73e8" : "1px solid #dadce0",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 13,
                        fontWeight: 700,
                      }}
                    >
                      {st.step}
                    </div>

                    <div>
                      <div style={{ fontSize: 13.5, fontWeight: 600, color: isSelected ? "#1a73e8" : "#202124" }}>
                        {st.title}
                      </div>
                      <div style={{ fontSize: 11.5, color: "#5f6368" }}>
                        {st.role} &bull; <strong style={{ color: "#202124" }}>{st.agent}</strong>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span
                      style={{
                        fontSize: 10.5,
                        padding: "3px 10px",
                        borderRadius: 16,
                        background: "#f1f3f4",
                        color: "#3c4043",
                        fontWeight: 600,
                        border: "1px solid #dadce0",
                      }}
                    >
                      {st.invariant}
                    </span>
                    <span
                      style={{
                        fontSize: 10.5,
                        padding: "3px 10px",
                        borderRadius: 16,
                        background: "#e8f0fe",
                        color: "#1a73e8",
                        fontWeight: 600,
                        border: "1px solid #d2e3fc",
                      }}
                    >
                      {st.timestamp || "Phase Link"}
                    </span>
                  </div>
                </div>

                <div style={{ fontSize: 12.5, color: "#202124", lineHeight: 1.5, paddingLeft: 44 }}>
                  {st.description}
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 11, color: "#5f6368", paddingLeft: 44 }}>
                  <span>Action: <code style={{ color: "#b06000", background: "#fef7e0", padding: "1px 4px", borderRadius: 4 }}>{st.action}</code></span>
                  {st.delegation_id && (
                    <span>Delegation: <code style={{ color: "#137333", background: "#e6f4ea", padding: "1px 4px", borderRadius: 4 }}>{st.delegation_id}</code></span>
                  )}
                  <span style={{ color: "#1a73e8", fontWeight: 600, marginLeft: "auto" }}>
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
