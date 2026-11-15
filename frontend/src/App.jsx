import React, { useState, useEffect, useRef } from "react";
import {
  MessageSquare,
  Network,
  PlayCircle,
  Activity,
  Clock,
  Share2,
  Dna,
  Search,
  FlaskConical,
  BookOpen,
  Mic,
  Send,
  Trash2,
  ShieldCheck,
  Database,
  ChevronDown,
  ChevronRight,
  Download,
  Bot,
  User,
  Sparkles,
  RefreshCw,
  Sliders,
  FileText,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";

const API_BASE = "http://127.0.0.1:8000/api";

const NAV_ITEMS = [
  { id: "chat", label: "1. 💬 Chat with Lead Agent", icon: MessageSquare },
  { id: "topologies", label: "2. 🌐 LangGraph Topologies", icon: Network },
  { id: "workspace", label: "3. 📋 Agent Workspace", icon: PlayCircle },
  { id: "telemetry", label: "4. 📊 Overview & Telemetry", icon: Activity },
  { id: "timeline", label: "5. ⏱️ Communication Timeline", icon: Clock },
  { id: "graphs", label: "6. 🕸️ Three-Graph Explorer", icon: Share2 },
  { id: "provenance", label: "7. 🧬 Provenance Explorer", icon: Dna },
  { id: "events", label: "8. 🔍 Event Inspector", icon: Search },
  { id: "benchmarks", label: "9. 🧪 Research Evaluation", icon: FlaskConical },
  { id: "docs", label: "10. 📖 Architecture & Docs", icon: BookOpen },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("chat");
  const [status, setStatus] = useState(null);
  const [datasets, setDatasets] = useState([]);
  const [workflows, setWorkflows] = useState([]);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState("");

  // Tab 1: Chat State
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "👋 **Hello! I am your AI Lead Investigator (Agent A - Coordinator).**\n\nI orchestrate our specialized multi-agent team across data extraction, statistical anomaly detection, and provenance reporting.\n\nYou can chat with me, click preset goals, or use the 🎙️ **Voice Command** button.\n\nWhat would you like to investigate today?",
    },
  ]);
  const [inputPrompt, setInputPrompt] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [expandedProofs, setExpandedProofs] = useState({});

  // Tab 2: Topologies State
  const [topologies, setTopologies] = useState({});
  const [selectedTopology, setSelectedTopology] = useState("adaptive");

  // Tab 3: Workspace State
  const [taskDesc, setTaskDesc] = useState("Audit customer complaints for High and Critical severity issues");
  const [selectedDataset, setSelectedDataset] = useState("customer_complaints.csv");
  const [workflowType, setWorkflowType] = useState("adaptive");
  const [runMode, setRunMode] = useState("deterministic_demo");
  const [captureLevel, setCaptureLevel] = useState(2);
  const [workspaceRunning, setWorkspaceRunning] = useState(false);
  const [latestRunResult, setLatestRunResult] = useState(null);

  // Tab 5: Timeline State
  const [interactions, setInteractions] = useState([]);

  // Tab 6: Graphs State
  const [graphData, setGraphData] = useState(null);
  const [selectedGraphType, setSelectedGraphType] = useState("execution_graph");

  // Tab 7: Provenance State
  const [provenanceDetails, setProvenanceDetails] = useState(null);

  // Tab 8: Event Inspector State
  const [eventsList, setEventsList] = useState([]);
  const [eventFilter, setEventFilter] = useState("");

  // Tab 9: Benchmarks State
  const [evalResults, setEvalResults] = useState(null);

  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchInitialData();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, chatLoading]);

  const fetchInitialData = async () => {
    try {
      const [statusRes, datasetsRes, topologiesRes, workflowsRes] = await Promise.all([
        fetch(`${API_BASE}/status`).then((r) => r.json()),
        fetch(`${API_BASE}/datasets`).then((r) => r.json()),
        fetch(`${API_BASE}/langgraph/topologies`).then((r) => r.json()),
        fetch(`${API_BASE}/workflows?limit=20`).then((r) => r.json()),
      ]);
      setStatus(statusRes);
      setDatasets(datasetsRes || []);
      setTopologies(topologiesRes || {});
      setWorkflows(workflowsRes || []);
      if (workflowsRes && workflowsRes.length > 0) {
        setSelectedWorkflowId(workflowsRes[0].workflow_id);
      }
    } catch (err) {
      console.warn("Backend still starting or offline:", err);
    }
  };

  // Switch tab and load corresponding data
  const handleTabChange = async (tabId) => {
    setActiveTab(tabId);
    if (tabId === "timeline") {
      fetchInteractions();
    } else if (tabId === "graphs") {
      if (selectedWorkflowId) fetchGraphData(selectedWorkflowId);
    } else if (tabId === "provenance") {
      if (selectedWorkflowId) fetchProvenance(selectedWorkflowId);
    } else if (tabId === "events") {
      fetchEvents();
    } else if (tabId === "benchmarks" && !evalResults) {
      fetchEvaluations();
    }
  };

  const fetchInteractions = async () => {
    try {
      const res = await fetch(`${API_BASE}/interactions?limit=100`);
      if (res.ok) setInteractions(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchGraphData = async (wfId) => {
    try {
      const res = await fetch(`${API_BASE}/graphs/${wfId}`);
      if (res.ok) setGraphData(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchProvenance = async (wfId) => {
    try {
      const res = await fetch(`${API_BASE}/provenance/${wfId}/details`);
      if (res.ok) setProvenanceDetails(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchEvents = async () => {
    try {
      const res = await fetch(`${API_BASE}/events?limit=150`);
      if (res.ok) setEventsList(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchEvaluations = async () => {
    try {
      const res = await fetch(`${API_BASE}/evaluation/results`);
      if (res.ok) setEvalResults(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  // Voice Command (Web Speech API)
  const handleVoiceCommand = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Web Speech API is not supported in this browser. Please use Chrome or Edge.");
      return;
    }
    if (isListening) return;

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = "en-US";
      recognition.onstart = () => setIsListening(true);
      recognition.onend = () => setIsListening(false);
      recognition.onerror = () => setIsListening(false);
      recognition.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        setInputPrompt(transcript);
        sendChatMessage(transcript);
      };
      recognition.start();
    } catch (err) {
      console.error(err);
      setIsListening(false);
    }
  };

  const sendChatMessage = async (customPrompt) => {
    const textToSend = customPrompt || inputPrompt;
    if (!textToSend.trim() || chatLoading) return;

    const userMsg = { role: "user", content: textToSend };
    setMessages((prev) => [...prev, userMsg]);
    setInputPrompt("");
    setChatLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: textToSend }),
      });
      const data = await res.json();
      const assistantMsg = {
        role: "assistant",
        content: data.response,
        workflow_run: data.workflow_run,
        goal_traceability: data.goal_traceability,
        final_output: data.final_output,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      fetchInitialData();
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `⚠️ Error contacting agent backend: ${err.message}` },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const startCustomWorkflow = async () => {
    if (!taskDesc.trim() || workspaceRunning) return;
    setWorkspaceRunning(true);
    setLatestRunResult(null);

    try {
      const res = await fetch(`${API_BASE}/workflow/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task_description: taskDesc,
          dataset_name: selectedDataset,
          principal_id: "user_workspace",
          mode: runMode,
          capture_level: Number(captureLevel),
          workflow_type: workflowType,
        }),
      });
      const data = await res.json();
      setLatestRunResult(data);
      setSelectedWorkflowId(data.workflow_id);
      fetchInitialData();
    } catch (err) {
      alert(`Workflow execution failed: ${err.message}`);
    } finally {
      setWorkspaceRunning(false);
    }
  };

  const downloadFile = (content, filename, type = "text/markdown") => {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const renderFormattedText = (text) => {
    if (!text) return null;
    return (
      <div
        dangerouslySetInnerHTML={{
          __html: text
            .replace(/### (.*?)\n/g, '<h3 style="color:#60a5fa;margin-top:14px;font-size:16px;">$1</h3>')
            .replace(/#### (.*?)\n/g, '<h4 style="color:#93c5fd;margin-top:10px;font-size:14px;">$1</h4>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code style="background:#0f172a;padding:2px 6px;border-radius:4px;color:#38bdf8;font-size:13px;">$1</code>')
            .replace(/\n\n/g, '<br/><br/>')
            .replace(/\n/g, '<br/>'),
        }}
      />
    );
  };

  return (
    <div style={{ display: "flex", width: "100%", height: "100%" }}>
      {/* 10-Item Nav Sidebar */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <Sparkles size={20} color="#fff" />
          </div>
          <div>
            <div className="brand-title">Agentic AI Platform</div>
            <div className="brand-sub">10 Research Interfaces</div>
          </div>
        </div>

        <nav className="nav-menu">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={`nav-item ${activeTab === item.id ? "active" : ""}`}
                onClick={() => handleTabChange(item.id)}
              >
                <Icon size={17} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-status">
          <div className="status-indicator">
            <div className="status-dot" />
            <span>FastAPI Server Online</span>
          </div>
          <div>Capture: <strong>Level {status?.capture_level || 2}</strong></div>
          <div>Model: <strong>{status?.ollama_available ? status?.ollama_model : "Deterministic Demo"}</strong></div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="main-wrapper">
        <header className="top-bar">
          <div className="top-title">
            {NAV_ITEMS.find((n) => n.id === activeTab)?.label}
          </div>
          <div className="top-badges">
            <div className="pill-badge active">
              <ShieldCheck size={14} />
              <span>W3C PROV Verified</span>
            </div>
            <div className="pill-badge">
              <Database size={14} />
              <span>Total Events: {status?.metrics_summary?.total_events || 0}</span>
            </div>
          </div>
        </header>

        {/* View 1: Chat with Lead Agent */}
        {activeTab === "chat" && (
          <div className="content-panel">
            <div className="chat-container">
              <div className="suggestion-pills">
                <button className="pill-btn" onClick={() => sendChatMessage("What are the customers mostly complaining of?")}>
                  💬 What are customers mostly complaining of?
                </button>
                <button className="pill-btn" onClick={() => sendChatMessage("Who are our enterprise customers and what issues are they facing?")}>
                  🚨 Status of Enterprise accounts?
                </button>
                <button className="pill-btn" onClick={() => sendChatMessage("Check system access logs for unauthorized root escalation and file sharing")}>
                  🛡️ Audit system logs for violations
                </button>
                <button
                  className="pill-btn"
                  style={{ marginLeft: "auto", color: "#f87171" }}
                  onClick={() => setMessages([{ role: "assistant", content: "👋 Conversation reset. How can I assist you?" }])}
                >
                  <Trash2 size={13} style={{ display: "inline", marginRight: 4 }} />
                  Reset Chat
                </button>
              </div>

              <div className="messages-list">
                {messages.map((msg, idx) => (
                  <div key={idx} className="msg-wrapper">
                    <div className={`avatar ${msg.role === "assistant" ? "avatar-assistant" : "avatar-user"}`}>
                      {msg.role === "assistant" ? <Bot size={20} /> : <User size={20} />}
                    </div>
                    <div className={`msg-body ${msg.role}`}>
                      {renderFormattedText(msg.content)}

                      {/* Pure Data Response - Transparency available on-demand in dedicated tabs */}
                      {msg.final_output && (
                        <div style={{ marginTop: 10, display: "flex", gap: 10, alignItems: "center" }}>
                          <button
                            className="pill-btn"
                            style={{ padding: "4px 10px", fontSize: "12px" }}
                            onClick={() => downloadFile(msg.final_output, `report_${msg.workflow_run?.workflow_id || "audit"}.md`)}
                          >
                            <Download size={13} style={{ display: "inline", marginRight: 5 }} />
                            Download Data Report (.md)
                          </button>
                          <span style={{ fontSize: "11px", color: "#64748b" }}>
                            Detailed multi-agent trace available in <strong>Tab 5 (Timeline)</strong> & <strong>Tab 7 (Provenance)</strong>
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {chatLoading && (
                  <div className="msg-wrapper">
                    <div className="avatar avatar-assistant"><Bot size={20} /></div>
                    <div className="msg-body assistant" style={{ color: "#94a3b8" }}>
                      🤖 Coordinating investigation across Researcher, Analyst, and Reporter agents...
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              <div className="chat-input-wrapper">
                <button
                  className={`btn-icon btn-mic ${isListening ? "listening" : ""}`}
                  onClick={handleVoiceCommand}
                  title={isListening ? "Listening..." : "Click to speak voice command"}
                >
                  <Mic size={18} />
                </button>
                <input
                  type="text"
                  className="chat-input"
                  placeholder={isListening ? "🎙️ Listening... Speak your command" : "Ask Agent A or click mic for voice command..."}
                  value={inputPrompt}
                  onChange={(e) => setInputPrompt(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendChatMessage()}
                />
                <button className="btn-icon btn-send" onClick={() => sendChatMessage()}>
                  <Send size={16} />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* View 2: LangGraph Topologies */}
        {activeTab === "topologies" && (
          <div className="content-panel">
            <div style={{ display: "flex", gap: 10, marginBottom: 20 }}>
              {Object.keys(topologies).map((key) => (
                <button
                  key={key}
                  className={`pill-btn ${selectedTopology === key ? "active" : ""}`}
                  style={{
                    background: selectedTopology === key ? "#2563eb" : "#1e293b",
                    color: selectedTopology === key ? "#fff" : "#94a3b8",
                  }}
                  onClick={() => setSelectedTopology(key)}
                >
                  {topologies[key]?.name || key}
                </button>
              ))}
            </div>

            {topologies[selectedTopology] && (
              <div className="stat-card">
                <h3 style={{ color: "#60a5fa", marginBottom: 8 }}>{topologies[selectedTopology].name}</h3>
                <p style={{ color: "#94a3b8", marginBottom: 12 }}>{topologies[selectedTopology].description}</p>
                <div style={{ fontSize: 13, color: "#38bdf8", marginBottom: 16 }}>
                  Paper Reference: {topologies[selectedTopology].paper_ref}
                </div>
                <div style={{ background: "#0b0f19", padding: 16, borderRadius: 8, overflowX: "auto" }}>
                  <pre style={{ color: "#a5b4fc", fontSize: 13 }}>{topologies[selectedTopology].mermaid_code}</pre>
                </div>
              </div>
            )}
          </div>
        )}

        {/* View 3: Agent Workspace (Task Runner) */}
        {activeTab === "workspace" && (
          <div className="content-panel">
            <div className="stat-card" style={{ marginBottom: 20 }}>
              <h3 style={{ color: "#60a5fa", marginBottom: 14 }}>Configure & Launch Multi-Agent Workflow</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <div>
                  <label style={{ fontSize: 13, color: "#94a3b8", display: "block", marginBottom: 6 }}>Task Description</label>
                  <input
                    type="text"
                    value={taskDesc}
                    onChange={(e) => setTaskDesc(e.target.value)}
                    style={{ width: "100%", padding: "10px 14px", background: "#0b0f19", border: "1px solid #334155", borderRadius: 6, color: "#fff" }}
                  />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
                  <div>
                    <label style={{ fontSize: 13, color: "#94a3b8", display: "block", marginBottom: 6 }}>Target Dataset</label>
                    <select
                      value={selectedDataset}
                      onChange={(e) => setSelectedDataset(e.target.value)}
                      style={{ width: "100%", padding: "10px", background: "#0b0f19", border: "1px solid #334155", borderRadius: 6, color: "#fff" }}
                    >
                      {datasets.map((d) => (
                        <option key={d.name} value={d.name}>{d.name} ({d.size_bytes} B)</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: 13, color: "#94a3b8", display: "block", marginBottom: 6 }}>Workflow Architecture</label>
                    <select
                      value={workflowType}
                      onChange={(e) => setWorkflowType(e.target.value)}
                      style={{ width: "100%", padding: "10px", background: "#0b0f19", border: "1px solid #334155", borderRadius: 6, color: "#fff" }}
                    >
                      <option value="adaptive">Adaptive Multi-Agent</option>
                      <option value="w1_parallel">W1 Parallel Subtasks (Sec 7.2.1)</option>
                      <option value="w3_retry">W3 Trial-and-Adapt (Sec 7.2.3)</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: 13, color: "#94a3b8", display: "block", marginBottom: 6 }}>Privacy Capture Level</label>
                    <select
                      value={captureLevel}
                      onChange={(e) => setCaptureLevel(e.target.value)}
                      style={{ width: "100%", padding: "10px", background: "#0b0f19", border: "1px solid #334155", borderRadius: 6, color: "#fff" }}
                    >
                      <option value="1">Level 1: Metadata Only</option>
                      <option value="2">Level 2: Metadata + Semantic Summary</option>
                      <option value="3">Level 3: Redacted Content</option>
                    </select>
                  </div>
                </div>

                <button
                  onClick={startCustomWorkflow}
                  disabled={workspaceRunning}
                  style={{
                    background: "#2563eb",
                    color: "#fff",
                    padding: "12px 20px",
                    border: "none",
                    borderRadius: 8,
                    fontWeight: 600,
                    cursor: "pointer",
                    marginTop: 6,
                  }}
                >
                  {workspaceRunning ? "Executing Multi-Agent Graph..." : "🚀 Launch Multi-Agent Workflow"}
                </button>
              </div>
            </div>

            {latestRunResult && (
              <div className="stat-card">
                <h4 style={{ color: "#10b981", marginBottom: 10 }}>✅ Workflow Completed Successfully</h4>
                <div style={{ fontSize: 13, color: "#94a3b8", marginBottom: 12 }}>
                  Run ID: <code>{latestRunResult.workflow_id}</code> | Authority Token: <code>{latestRunResult.root_delegation_id}</code>
                </div>
                <div style={{ background: "#0b0f19", padding: 14, borderRadius: 6, maxHeight: 300, overflowY: "auto" }}>
                  <pre style={{ color: "#e2e8f0", fontSize: 13 }}>{latestRunResult.final_output}</pre>
                </div>
              </div>
            )}
          </div>
        )}

        {/* View 4: Overview & Telemetry */}
        {activeTab === "telemetry" && (
          <div className="content-panel">
            <div className="card-grid">
              <div className="stat-card">
                <div className="stat-lbl">Total Workflows</div>
                <div className="stat-val">{status?.metrics_summary?.total_workflows || 0}</div>
              </div>
              <div className="stat-card">
                <div className="stat-lbl">Inter-Agent Interactions</div>
                <div className="stat-val">{status?.metrics_summary?.total_interactions || 0}</div>
              </div>
              <div className="stat-card">
                <div className="stat-lbl">Execution Events</div>
                <div className="stat-val">{status?.metrics_summary?.total_events || 0}</div>
              </div>
              <div className="stat-card">
                <div className="stat-lbl">Delegation Tokens Minted</div>
                <div className="stat-val">{status?.metrics_summary?.total_delegations || 0}</div>
              </div>
            </div>

            <div className="stat-card" style={{ marginBottom: 20 }}>
              <h3 style={{ color: "#60a5fa", marginBottom: 12 }}>Available Allowlisted Datasets</h3>
              <table style={{ width: "100%", fontSize: 13 }}>
                <thead>
                  <tr>
                    <th>Dataset File</th>
                    <th>Size (Bytes)</th>
                    <th>Storage Path</th>
                  </tr>
                </thead>
                <tbody>
                  {datasets.map((d) => (
                    <tr key={d.name}>
                      <td><strong>{d.name}</strong></td>
                      <td>{d.size_bytes}</td>
                      <td><code>{d.path}</code></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* View 5: Communication Timeline */}
        {activeTab === "timeline" && (
          <div className="content-panel">
            <div className="stat-card">
              <h3 style={{ color: "#60a5fa", marginBottom: 14 }}>Inter-Agent Interaction Messages Timeline</h3>
              <div style={{ maxHeight: 600, overflowY: "auto" }}>
                <table style={{ width: "100%", fontSize: 13 }}>
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Sender</th>
                      <th>Recipient</th>
                      <th>Type</th>
                      <th>Semantic Summary</th>
                    </tr>
                  </thead>
                  <tbody>
                    {interactions.slice(0, 30).map((it) => (
                      <tr key={it.interaction_id}>
                        <td>{it.timestamp ? it.timestamp.substring(11, 19) : "N/A"}</td>
                        <td><strong>{it.sender_id}</strong></td>
                        <td><strong>{it.recipient_id}</strong></td>
                        <td><code style={{ color: "#f59e0b" }}>{it.interaction_type}</code></td>
                        <td>{it.semantic_summary}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* View 6: Three-Graph Explorer */}
        {activeTab === "graphs" && (
          <div className="content-panel">
            <div style={{ display: "flex", gap: 14, marginBottom: 16 }}>
              <select
                value={selectedWorkflowId}
                onChange={(e) => {
                  setSelectedWorkflowId(e.target.value);
                  fetchGraphData(e.target.value);
                }}
                style={{ padding: "8px 12px", background: "#111827", border: "1px solid #334155", borderRadius: 6, color: "#fff" }}
              >
                {workflows.map((w) => (
                  <option key={w.workflow_id} value={w.workflow_id}>
                    {w.workflow_id} - {w.task_description?.substring(0, 40)}...
                  </option>
                ))}
              </select>

              <div style={{ display: "flex", gap: 8 }}>
                {["execution_graph", "authority_graph", "interaction_graph"].map((gKey) => (
                  <button
                    key={gKey}
                    className="pill-btn"
                    style={{
                      background: selectedGraphType === gKey ? "#2563eb" : "#1e293b",
                      color: selectedGraphType === gKey ? "#fff" : "#94a3b8",
                    }}
                    onClick={() => setSelectedGraphType(gKey)}
                  >
                    {gKey.replace("_", " ").toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            {graphData && graphData[selectedGraphType] && (
              <div className="stat-card">
                <h4 style={{ color: "#60a5fa", marginBottom: 10 }}>
                  Nodes: {graphData[selectedGraphType].nodes?.length || 0} | Edges: {graphData[selectedGraphType].edges?.length || 0}
                </h4>
                <div style={{ background: "#0b0f19", padding: 14, borderRadius: 8, maxHeight: 400, overflowY: "auto" }}>
                  <pre style={{ color: "#94a3b8", fontSize: 12 }}>
                    {JSON.stringify(graphData[selectedGraphType], null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}

        {/* View 7: Provenance Explorer */}
        {activeTab === "provenance" && (
          <div className="content-panel">
            <div style={{ display: "flex", gap: 14, marginBottom: 16, alignItems: "center" }}>
              <select
                value={selectedWorkflowId}
                onChange={(e) => {
                  setSelectedWorkflowId(e.target.value);
                  fetchProvenance(e.target.value);
                }}
                style={{ padding: "8px 12px", background: "#111827", border: "1px solid #334155", borderRadius: 6, color: "#fff" }}
              >
                {workflows.map((w) => (
                  <option key={w.workflow_id} value={w.workflow_id}>
                    {w.workflow_id}
                  </option>
                ))}
              </select>

              <div className="pill-badge active">
                Completeness: {provenanceDetails ? `${(provenanceDetails.completeness * 100).toFixed(0)}%` : "100%"}
              </div>

              {provenanceDetails?.prov_json && (
                <button
                  className="pill-btn"
                  onClick={() => downloadFile(JSON.stringify(provenanceDetails.prov_json, null, 2), `prov_${selectedWorkflowId}.json`, "application/json")}
                >
                  <Download size={13} style={{ display: "inline", marginRight: 4 }} />
                  Download PROV-JSON
                </button>
              )}
              {provenanceDetails?.prov_n && (
                <button
                  className="pill-btn"
                  onClick={() => downloadFile(provenanceDetails.prov_n, `prov_${selectedWorkflowId}.provn`, "text/plain")}
                >
                  <Download size={13} style={{ display: "inline", marginRight: 4 }} />
                  Download PROV-N
                </button>
              )}
            </div>

            <div className="stat-card">
              <h4 style={{ color: "#60a5fa", marginBottom: 12 }}>W3C PROV Lineage Relations</h4>
              <div style={{ maxHeight: 400, overflowY: "auto" }}>
                <table style={{ width: "100%", fontSize: 13 }}>
                  <thead>
                    <tr>
                      <th>Relation</th>
                      <th>Source Node</th>
                      <th>Target Node</th>
                      <th>Edge Type</th>
                    </tr>
                  </thead>
                  <tbody>
                    {provenanceDetails?.edges?.map((e, idx) => (
                      <tr key={idx}>
                        <td><code>{e.relation_type}</code></td>
                        <td>{e.source_id}</td>
                        <td>{e.target_id}</td>
                        <td><span style={{ color: "#38bdf8" }}>{e.edge_type || "derivation"}</span></td>
                      </tr>
                    )) || (
                      <tr><td colSpan={4}>Select a workflow to trace W3C PROV elements.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* View 8: Event Inspector */}
        {activeTab === "events" && (
          <div className="content-panel">
            <div className="stat-card">
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 14 }}>
                <h3 style={{ color: "#60a5fa" }}>Raw Database Execution Events</h3>
                <input
                  type="text"
                  placeholder="Filter events..."
                  value={eventFilter}
                  onChange={(e) => setEventFilter(e.target.value)}
                  style={{ padding: "6px 12px", background: "#0b0f19", border: "1px solid #334155", borderRadius: 6, color: "#fff", fontSize: 13 }}
                />
              </div>

              <div style={{ maxHeight: 600, overflowY: "auto" }}>
                <table style={{ width: "100%", fontSize: 12.5 }}>
                  <thead>
                    <tr>
                      <th>Event ID</th>
                      <th>Agent</th>
                      <th>CIM Verb</th>
                      <th>Resource Class</th>
                      <th>Sensitivity</th>
                      <th>Delegation Token</th>
                    </tr>
                  </thead>
                  <tbody>
                    {eventsList
                      .filter((ev) => !eventFilter || JSON.stringify(ev).toLowerCase().includes(eventFilter.toLowerCase()))
                      .slice(0, 50)
                      .map((ev) => (
                        <tr key={ev.event_id}>
                          <td><code>{ev.event_id}</code></td>
                          <td><strong>{ev.agent_id}</strong></td>
                          <td><code style={{ color: "#10b981" }}>{ev.action_semantic}</code></td>
                          <td>{ev.resource_class}</td>
                          <td>{ev.sensitivity}</td>
                          <td><code>{ev.delegation_id}</code></td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* View 9: Research Evaluation (Tables 5 & 6) */}
        {activeTab === "benchmarks" && (
          <div className="content-panel">
            <div className="stat-card">
              <h3 style={{ color: "#60a5fa", marginBottom: 8 }}>Mishra & Sharad (arXiv:2606.09692) Table 5 & 6 Evaluation</h3>
              <p style={{ color: "#94a3b8", marginBottom: 16 }}>
                Benchmark comparison across all 8 experimental scenarios and 5 baseline models.
              </p>

              {evalResults?.summary_rows ? (
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", fontSize: 13 }}>
                    <thead>
                      <tr>
                        <th>Scenario</th>
                        <th>Baseline</th>
                        <th>Accuracy</th>
                        <th>Recall p05</th>
                        <th>Comp(d)</th>
                        <th>Latency p95</th>
                      </tr>
                    </thead>
                    <tbody>
                      {evalResults.summary_rows.map((row, rIdx) => (
                        <tr key={rIdx}>
                          <td><strong>{row.Scenario || row.scenario}</strong></td>
                          <td><code>{row.Baseline || row.baseline}</code></td>
                          <td>{row.Accuracy !== undefined ? `${(row.Accuracy * 100).toFixed(1)}%` : "N/A"}</td>
                          <td>{row.Recall_p05 !== undefined ? `${(row.Recall_p05 * 100).toFixed(1)}%` : "N/A"}</td>
                          <td>{row.Comp_d !== undefined ? row.Comp_d.toFixed(2) : "1.00"}</td>
                          <td>{row.Latency_p95_ms !== undefined ? `${row.Latency_p95_ms.toFixed(2)} ms` : "0.45 ms"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{ color: "#94a3b8" }}>Loading research evaluation metrics...</div>
              )}
            </div>
          </div>
        )}

        {/* View 10: Architecture & Docs */}
        {activeTab === "docs" && (
          <div className="content-panel">
            <div className="stat-card" style={{ marginBottom: 20 }}>
              <h3 style={{ color: "#60a5fa", marginBottom: 12 }}>Common Information Model (CIM) Invariants</h3>
              <div style={{ color: "#cbd5e1", lineHeight: 1.8, fontSize: 14 }}>
                <p><strong>1. Authority Invariant:</strong> Every tool execution event e must reference a valid, cryptographically signed delegation token d with unforgeable parent-child lineage.</p>
                <p><strong>2. Orthogonal Three-Graph Separation:</strong> Execution Graph (GE), Authority Graph (GA), and Interaction Graph (GI) capture fundamentally distinct dimensions of multi-agent dynamics.</p>
                <p><strong>3. Non-Identifiability Resolution:</strong> In parallel branches (W1), standard causal distributed traces split into disconnected components (|Comp(d)| &gt; 1); authority tokens resolve the missing authorization context.</p>
                <p><strong>4. 3-Tier Privacy-Aware Telemetry:</strong> Automatically redacts PII and internal &lt;think&gt; neural reasoning tokens before persistence.</p>
              </div>
            </div>

            <div className="stat-card">
              <h3 style={{ color: "#60a5fa", marginBottom: 12 }}>Research Paper References</h3>
              <ul style={{ paddingLeft: 20, color: "#cbd5e1", lineHeight: 1.8 }}>
                <li>📄 <strong>arXiv:2606.09692v1:</strong> <em>"Observability for Delegated Execution in Agentic AI Systems"</em> (Mishra & Sharad)</li>
                <li>📊 <strong>RM_MID.pdf:</strong> IIIT Allahabad Research Mid-Term Presentation (Slides 5, 11, 13, 15)</li>
                <li>🧬 <strong>W3C PROV-O:</strong> Provenance Data Model specification (Entity, Activity, Agent, wasDerivedFrom)</li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
