/**
 * Mermaid.js & C4 Architecture Diagram Generators for Three-Graph Explorer.
 * Supports:
 * 1. Level 2 C4 Container Architecture Diagram (Draw.io compatible)
 * 2. Execution Graph (G_exec) Causal Sequence Flowchart
 * 3. Authority Graph (G_auth) Hierarchical Delegation DAG
 * 4. Interaction Graph (G_interact) Multi-Agent Sequence Diagram
 * 5. Unified Three-Graph Multi-Layer Correlation Diagram
 */

// Helper to sanitize labels for Mermaid syntax
function sanitize(str) {
  if (!str) return "";
  return String(str)
    .replace(/["\(\)\[\]\{\};]/g, " ")
    .replace(/\n/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * 1. Level 2 C4 Container Architecture Diagram
 * Enterprise-grade architecture of the entire Agentic AI Observability Platform.
 * Ready for Draw.io (Arrange > Insert > Advanced > Mermaid).
 */
export function generateC4ContainerDiagram() {
  return `flowchart TB
    %% Level 2 C4 Container Architecture: Agentic AI Observability
    classDef boundary fill:#f8f9fa,stroke:#dadce0,stroke-width:1.5px,color:#5f6368,stroke-dasharray: 4 4
    classDef client fill:#ffffff,stroke:#1a73e8,stroke-width:1.5px,color:#202124
    classDef gateway fill:#ffffff,stroke:#1a73e8,stroke-width:1.5px,color:#202124
    classDef agent fill:#e8f0fe,stroke:#1a73e8,stroke-width:1.5px,color:#1557b0
    classDef store fill:#ffffff,stroke:#dadce0,stroke-width:1.5px,color:#202124
    classDef llm fill:#fef7e0,stroke:#f9ab00,stroke-width:1.5px,color:#202124

    subgraph UserContext ["👤 User Context"]
        User["Principal / Human Investigator<br/>[Role: Directs Workflow & Evaluates Evidence]"]:::client
    end

    subgraph ObservabilityPlatform ["🛡️ RM_FINALE Observability Platform"]
        ReactSPA["React 19 SPA / Control Plane<br/>[Frontend: Vite, React Flow, 11 Dedicated Routes]"]:::client
        FastAPI["FastAPI Observability Server<br/>[Python 3.14: REST APIs, Async Tasks, CORS]"]:::gateway
        CIMGateway["Transparent Observability Gateway<br/>[CIM Middleware: Invariant Enforcer & Event Emitter]"]:::gateway

        subgraph MultiAgentFleet ["🤖 Specialized Multi-Agent Fleet"]
            Coordinator["Agent A: Coordinator<br/>[Decomposes tasks, issues delegation tokens]"]:::agent
            Researcher["Agent B: Researcher<br/>[Reads datasets, executes CIM tool actions]"]:::agent
            Analyst["Agent C: Analyst<br/>[Anomaly detection, statistics & metrics]"]:::agent
            Reporter["Agent D: Reporter<br/>[Compiles findings & final consensus report]"]:::agent
        end

        subgraph DualPersistence ["💾 Resilient Storage Layer"]
            SQLiteStore["SQLite Event Store (WAL)<br/>[Tables: execution_events, delegations, interactions, provenance]"]:::store
            MongoAtlas["MongoDB Atlas Chat Store<br/>[Collections: conversations, multi-turn reasoning, session memory]"]:::store
        end

        subgraph ThreeGraphs ["📊 Three-Graph System (Topics 5, 6, 7)"]
            GExec["G_exec: Execution Graph<br/>[What happened: Causal tool calls & outcomes]"]:::store
            GAuth["G_auth: Authority Graph<br/>[Who authorized: Delegation tokens & lineage DAG]"]:::store
            GItr["G_interact: Interaction Graph<br/>[Who communicated: MultiDiGraph dialogues]"]:::store
            Validator["CrossGraphValidator<br/>[Invariants 1-3 & Comp(d) Score]"]:::gateway
        end
    end

    subgraph ExternalServices ["☁️ External Foundation Models"]
        Gemini["Google Gemini 1.5 Flash / 2.0<br/>[REST API with active keepalive fallback]"]:::llm
        HFRouter["HuggingFace Model Router<br/>[Llama-3.1-8B Coordinator & Qwen2.5-7B Executor]"]:::llm
    end

    %% Interactions & Dataflows
    User -->|"1. Submits Prompt / Analysis Goal"| ReactSPA
    ReactSPA -->|"2. Dispatches API Requests"| FastAPI
    FastAPI -->|"3. Orchestrates Workflow"| Coordinator
    Coordinator -->|"4. Issues Delegation Tokens"| GAuth
    Coordinator -->|"5. Communicates with Peer Agents"| GItr
    Coordinator -.->|"Directs Subtasks"| Researcher
    Researcher -.->|"Transfers Data"| Analyst
    Analyst -.->|"Consolidates Analysis"| Reporter

    Researcher -->|"6. Invokes Tools via Gateway"| CIMGateway
    CIMGateway -->|"7. Records CIM Events"| GExec
    GExec -->|"8. Persists Raw Telemetry"| SQLiteStore
    ReactSPA -->|"9. Syncs Session Memory"| MongoAtlas

    ThreeGraphs -->|"10. Validates Structural Invariants"| Validator
    MultiAgentFleet -->|"Queries Inference"| Gemini
    MultiAgentFleet -->|"Routes Multi-Model Dialogue"| HFRouter
`;
}

/**
 * 2. Execution Graph (G_exec) Causal Sequence Flowchart
 */
export function generateExecutionMermaid(nodes = [], edges = []) {
  if (!nodes || nodes.length === 0) {
    return `flowchart TD
      NoEvents["No Execution Events Recorded"]:::empty
      classDef empty fill:#f8f9fa,stroke:#dadce0,color:#5f6368;`;
  }

  const safeNodes = nodes.slice(0, 20); // Cap at 20 for crisp rendering
  let code = `flowchart TD\n`;
  code += `    classDef success fill:#e6f4ea,stroke:#1e8e3e,stroke-width:1.5px,color:#137333;\n`;
  code += `    classDef failed fill:#fce8e6,stroke:#d93025,stroke-width:1.5px,color:#d93025;\n`;
  code += `    classDef tool fill:#fef7e0,stroke:#f9ab00,stroke-width:1.5px,color:#b06000;\n\n`;

  safeNodes.forEach((node, idx) => {
    const nid = `E${idx}`;
    const agent = sanitize(node.agent_id || "agent");
    const tool = sanitize(node.tool_name || "tool");
    const op = sanitize(node.tool_operation || node.action_semantic || "invoke");
    const outcome = node.outcome === "failure" ? "FAILED" : "SUCCESS";
    const outcomeClass = node.outcome === "failure" ? "failed" : "success";
    const res = sanitize(node.resource_id || "target");

    code += `    ${nid}["⚡ ${op}<br/><b>Tool:</b> ${tool}<br/><b>Agent:</b> ${agent}<br/><b>Target:</b> ${res}<br/>[${outcome}]"]:::${outcomeClass}\n`;
  });

  // Link in sequence or causal edges
  for (let i = 0; i < safeNodes.length - 1; i++) {
    code += `    E${i} -->|"causal_step ${i + 1}"| E${i + 1}\n`;
  }

  return code;
}

/**
 * 3. Authority Graph (G_auth) Hierarchical Delegation DAG
 */
export function generateAuthorityMermaid(nodes = [], edges = []) {
  if (!nodes || nodes.length === 0) {
    return `flowchart TD
      NoAuth["No Authority Delegations Recorded"]:::empty
      classDef empty fill:#f8f9fa,stroke:#dadce0,color:#5f6368;`;
  }

  let code = `flowchart TD\n`;
  code += `    classDef principal fill:#fef7e0,stroke:#f9ab00,stroke-width:1.5px,color:#202124;\n`;
  code += `    classDef delegation fill:#e6f4ea,stroke:#1e8e3e,stroke-width:1.5px,color:#137333;\n`;
  code += `    classDef agent fill:#e8f0fe,stroke:#1a73e8,stroke-width:1.5px,color:#1557b0;\n\n`;

  const principals = nodes.filter((n) => n.node_type === "principal" || n.id?.startsWith("prin_"));
  const delegations = nodes.filter((n) => n.node_type === "delegation" || n.id?.startsWith("del_"));
  const agents = nodes.filter((n) => n.node_type === "agent" || n.id?.startsWith("agent_"));

  // Subgraph: Principals
  code += `    subgraph RootAuthority ["👤 Root Human Authority"]\n`;
  if (principals.length > 0) {
    principals.forEach((p, idx) => {
      const pid = `P_${idx}`;
      code += `        ${pid}["👤 Principal: ${sanitize(p.entity_id || p.label || "Alice")}<br/>[Root Signer]"]:::principal\n`;
    });
  } else {
    code += `        P_0["👤 Principal: principal_alice<br/>[Root Signer]"]:::principal\n`;
  }
  code += `    end\n\n`;

  // Subgraph: Delegation Tokens
  code += `    subgraph DelegationTokens ["🔑 Cryptographic Delegation Scopes"]\n`;
  delegations.slice(0, 8).forEach((d, idx) => {
    const did = `D_${idx}`;
    const token = sanitize((d.id || d.delegation_id || "token").substring(0, 14));
    const scope = sanitize(d.scope || "standard_execution");
    code += `        ${did}["🔑 Token: ${token}...<br/><b>Scope:</b> ${scope}"]:::delegation\n`;
  });
  code += `    end\n\n`;

  // Subgraph: Authorized Agents
  code += `    subgraph AuthorizedAgents ["🤖 Authorized Delegatee Agents"]\n`;
  agents.slice(0, 6).forEach((a, idx) => {
    const aid = `A_${idx}`;
    const label = sanitize(a.label || a.id || "Agent");
    code += `        ${aid}["🤖 ${label}<br/>[Authorized Agent]"]:::agent\n`;
  });
  code += `    end\n\n`;

  // Flow links
  if (delegations.length > 0) {
    code += `    P_0 -->|"issues_root_delegation"| D_0\n`;
    for (let i = 0; i < Math.min(delegations.length, agents.length); i++) {
      code += `    D_${i} -->|"assigned_to"| A_${i}\n`;
    }
  }

  return code;
}

/**
 * 4. Interaction Graph (G_interact) Multi-Agent Sequence Diagram
 */
export function generateInteractionSequenceMermaid(nodes = [], edges = []) {
  let code = `sequenceDiagram\n`;
  code += `    autonumber\n`;
  code += `    actor User as 👤 Human Principal\n`;
  code += `    participant C as 🤖 Agent A: Coordinator\n`;
  code += `    participant R as 🔬 Agent B: Researcher\n`;
  code += `    participant A as 📊 Agent C: Analyst\n`;
  code += `    participant Rep as 📝 Agent D: Reporter\n\n`;

  if (edges && edges.length > 0) {
    edges.slice(0, 10).forEach((e) => {
      const src = mapAgentParticipant(e.source);
      const tgt = mapAgentParticipant(e.target);
      const type = sanitize(e.interaction_type || "message");
      const summary = sanitize(e.semantic_summary || e.content || "task payload").substring(0, 36);
      code += `    ${src}->>+${tgt}: [${type}] ${summary}...\n`;
      code += `    Note over ${tgt}: Validates delegation context\n`;
    });
  } else {
    // Standard demonstrative flow
    code += `    User->>+C: 1. Start Analysis Goal (customer_complaints.csv)\n`;
    code += `    Note over C: Establishes root delegation token (del_root)\n`;
    code += `    C->>+R: 2. [delegation] Ingest and extract CSV complaint records\n`;
    code += `    Note over R: Invokes file_reader tool via CIM Gateway\n`;
    code += `    R-->>-C: 3. [result] Extracted 50 complaint samples & schema\n`;
    code += `    C->>+A: 4. [delegation] Compute statistical anomalies & sentiment\n`;
    code += `    Note over A: Invokes sentiment_calc & stats_aggregator\n`;
    code += `    A-->>-C: 5. [result] Sentiment distribution & cluster metrics\n`;
    code += `    C->>+Rep: 6. [delegation] Synthesize executive markdown report\n`;
    code += `    Rep-->>-C: 7. [result] Formatted report with evidence lineage\n`;
    code += `    C-->>-User: 8. Final Verified Audit Artifact & Three-Graph Proof\n`;
  }

  return code;
}

function mapAgentParticipant(name) {
  const n = String(name || "").toLowerCase();
  if (n.includes("researcher")) return "R";
  if (n.includes("analyst")) return "A";
  if (n.includes("reporter")) return "Rep";
  if (n.includes("principal") || n.includes("user")) return "User";
  return "C";
}

/**
 * 5. Unified Three-Graph Multi-Layer Correlation Flowchart
 */
export function generateUnifiedThreeGraphMermaid(execCount = 5, authCount = 3, itrCount = 4) {
  return `flowchart LR
    %% Three-Graph Unified Cross-Graph Verification
    classDef comm fill:#e8f0fe,stroke:#1a73e8,stroke-width:1.5px,color:#1557b0;
    classDef auth fill:#e6f4ea,stroke:#1e8e3e,stroke-width:1.5px,color:#137333;
    classDef exec fill:#fef7e0,stroke:#f9ab00,stroke-width:1.5px,color:#b06000;
    classDef validator fill:#ffffff,stroke:#dadce0,stroke-width:1.5px,color:#202124;

    subgraph GItr ["1. Communication Graph (G_interact)"]
        direction TB
        Msg1["Message: Coordinator → Researcher<br/>[Type: Task Delegation]"]:::comm
        Msg2["Message: Researcher → Analyst<br/>[Type: Information Transfer]"]:::comm
        Msg3["Message: Analyst → Reporter<br/>[Type: Result Synthesis]"]:::comm
        Msg1 --> Msg2 --> Msg3
    end

    subgraph GAuth ["2. Authority Graph (G_auth)"]
        direction TB
        DelRoot["Root Token: del_root<br/>[Principal Alice]"]:::auth
        DelChild1["Delegation: del_researcher<br/>[Scope: read_dataset]"]:::auth
        DelChild2["Delegation: del_analyst<br/>[Scope: compute_metrics]"]:::auth
        DelRoot --> DelChild1
        DelRoot --> DelChild2
    end

    subgraph GExec ["3. Execution Graph (G_exec)"]
        direction TB
        Act1["Event: file_reader:read_csv<br/>[Target: complaints.csv]"]:::exec
        Act2["Event: stats:calc_sentiment<br/>[Target: records]"]:::exec
        Act3["Event: report:compile_md<br/>[Target: summary.md]"]:::exec
        Act1 --> Act2 --> Act3
    end

    subgraph InvariantProof ["🛡️ Cross-Graph Invariant Verification"]
        Inv1["Invariant 1: Authority Coverage<br/>Every execution event has valid delegation"]:::validator
        Inv2["Invariant 2: Interaction Links<br/>Every message consequence exists in execution"]:::validator
        Inv3["Invariant 3: Temporal Bounds<br/>Execution timestamps within delegation lifetime"]:::validator
        CompD["Alignment Metric Comp(d) = 1.0<br/>Full Authority-Causality Consistency Verified"]:::validator
    end

    %% Cross-Graph Alignment Edges
    Msg1 -.->|"authorizes scope"| DelChild1
    DelChild1 -.->|"permits tool call"| Act1
    Msg2 -.->|"authorizes scope"| DelChild2
    DelChild2 -.->|"permits tool call"| Act2

    GExec ==> Inv1
    GItr ==> Inv2
    GAuth ==> Inv3
    Inv1 & Inv2 & Inv3 ==> CompD
`;
}
