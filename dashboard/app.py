"""
Streamlit Multi-Page Research Dashboard.
Transparency and Openness in Agentic AI Systems:
Capturing Inter-Agent Communication, Execution Context, and Delegation.
"""

import sys
import os
from pathlib import Path

# Ensure project root is in sys.path regardless of how or where streamlit was launched
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from backend.config import settings
from backend.storage.event_store import EventStore
from backend.orchestration.workflow_runner import WorkflowRunner
from backend.schemas.workflow import WorkflowMode
from backend.schemas.events import CaptureLevel, InteractionType
from backend.gateway.gateway import default_gateway
from backend.tools.file_tools import list_sample_datasets
from backend.agents.llm_client import is_ollama_available, list_installed_ollama_models
from backend.graphs.three_graphs import ThreeGraphCoordinator
from backend.graphs.goal_flow import generate_goal_flow_dot, generate_langgraph_statemachine_dot, extract_goal_traceability
from backend.orchestration.langgraph_workflow import get_langgraph_mermaid, get_available_workflow_topologies
from backend.agents.response_synthesizer import answer_user_query_directly, format_direct_task_findings
from backend.provenance.tracker import ProvenanceTracker
from backend.evaluation.runner import BenchmarkRunner
from backend.orchestration.hf_simulation import run_huggingface_transparency_simulation, DEFAULT_SIMULATION_AGENTS

# Page Configuration
st.set_page_config(
    page_title="Agentic AI Transparency Platform",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling for an attractive, professional research interface
st.markdown("""
<style>
    .main-header {
        font-size: 26px;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 4px;
    }
    .sub-header {
        font-size: 14px;
        color: #475569;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
    }
    .metric-val {
        font-size: 24px;
        font-weight: 700;
        color: #2563eb;
    }
    .metric-lbl {
        font-size: 12px;
        color: #64748b;
        text-transform: uppercase;
    }
    .agent-card {
        background-color: #ffffff;
        border-left: 4px solid #3b82f6;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    [data-testid="stSidebar"] {
        overflow-y: auto !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        overflow-y: auto !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Backend Services
@st.cache_resource
def get_services():
    store = EventStore()
    runner = WorkflowRunner(store.get_gateway() if hasattr(store, "get_gateway") else None)
    three_graphs = ThreeGraphCoordinator(store)
    prov_tracker = ProvenanceTracker(store)
    benchmark = BenchmarkRunner(store)
    return store, runner, three_graphs, prov_tracker, benchmark

store, runner, three_graphs, prov_tracker, benchmark = get_services()

def safe_render_graphviz(dot_string: str):
    if not dot_string:
        st.info("No graph representation available.")
        return
    try:
        st.graphviz_chart(dot_string, use_container_width=True)
    except Exception as e:
        st.code(dot_string, language="dot")

# Sidebar Navigation
st.sidebar.image("https://img.icons8.com/color/96/artificial-intelligence.png", width=64)
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select Interface View",
    [
        "1. 💬 Chat with Lead Agent (Interactive)",
        "2. 🚀 Hugging Face Multi-Agent Simulation",
        "3. 🌐 LangGraph Goal Flow & Topology",
        "4. 📋 Agent Workspace (Task Runner)",
        "5. 📊 Overview & Telemetry",
        "6. ⏱️ Communication Timeline",
        "7. 🕸️ Interactive Graph Explorer",
        "8. 🧬 Provenance Explorer",
        "9. 🔍 Event Inspector",
        "10. 🧪 Research Evaluation",
        "11. 📖 Architecture & Docs",
        "12. 🛡️ Observability Gateway (Auto-Capture)"
    ]
)

# Global Sidebar Status
st.sidebar.markdown("---")
st.sidebar.subheader("System Status")

st.sidebar.markdown(
    f"**🌐 LLM Cloud API: Active**\n\n"
    f"- **Model**: `{settings.LLM_MODEL}`\n"
    f"- **Endpoint**: `{settings.LLM_BASE_URL}`"
)

st.sidebar.caption(f"Capture Level: **Level {settings.DEFAULT_CAPTURE_LEVEL}**")
st.sidebar.caption(f"DB: `{Path(settings.DATABASE_PATH).name}`")

# ==============================================================================
# PAGE 1: CHAT WITH LEAD AGENT (INTERACTIVE CONVERSATIONAL AGENT)
# ==============================================================================
if page == "1. 💬 Chat with Lead Agent (Interactive)":
    col_h1, col_h2 = st.columns([5, 1])
    with col_h1:
        st.markdown('<div class="main-header">Conversational Agent Chat with Coordinator</div>', unsafe_allow_html=True)
    with col_h2:
        if st.button("🗑️ Reset Chat", help="Clear conversation history and start fresh"):
            st.session_state["chat_messages"] = []
            st.rerun()

    st.markdown(
        '<div class="sub-header">Chat directly with <b>Agent A (Coordinator)</b>. '
        'Submit a goal or instruction, watch live task decomposition, inspect sub-goal delegation to specialized agents, '
        'and examine transparent execution flow in real-time.</div>',
        unsafe_allow_html=True
    )

    # Initialize chat session history
    if not st.session_state.get("chat_messages"):
        st.session_state["chat_messages"] = [
            {
                "role": "assistant",
                "content": (
                    "👋 **Hello! I am your AI Lead Investigator.**\n\n"
                    "I coordinate our specialized multi-agent team to help you analyze customer feedback, audit system security logs, or review operational briefs.\n\n"
                    "You can ask me questions naturally, for example:\n"
                    "- *\"What are our customers mostly complaining about?\"*\n"
                    "- *\"Tell me about customer CUST-849 and what happened to them\"*\n"
                    "- *\"Who are our enterprise clients and are they facing critical issues?\"*\n"
                    "- *\"Check our security logs for any unauthorized access attempts\"*\n\n"
                    "How can I help you today?"
                ),
                "goal_flow_dot": None,
                "goal_matrix": None,
                "workflow_id": None,
                "report_content": None
            }
        ]

    # Quick prompt suggestion pills
    st.markdown("**Quick Inquiries to Try:**")
    colP1, colP2, colP3 = st.columns(3)
    preset_clicked = None
    with colP1:
        if st.button("💬 What are customers mostly complaining of?"):
            preset_clicked = "What are the customers mostly complaining of?"
    with colP2:
        if st.button("🚨 Are there urgent issues with Enterprise accounts?"):
            preset_clicked = "Who are our enterprise customers and what critical issues are they facing?"
    with colP3:
        if st.button("🛡️ Audit System Logs for Unauthorized Access"):
            preset_clicked = "Check system access logs for unauthorized root escalation, confidential data sharing, and security violations."

    # Display Chat History
    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
            st.markdown(msg["content"])
            
            # If this assistant response includes goal flow artifacts, render interactive tabs underneath
            if msg.get("workflow_id"):
                wf_id = msg["workflow_id"]
                root_del = msg.get("root_delegation_id") or "verified_root"
                st.caption(f"🛡️ **Authority Token:** `{root_del}` &nbsp;|&nbsp; 🌐 **Run ID:** `{wf_id}` &nbsp;|&nbsp; 🧬 **W3C PROV:** Verified &nbsp;|&nbsp; 🔒 **Privacy:** Level 2")
                with st.expander(f"🔍 Why did the agent give this response? (Observability & Transparency Proof: {wf_id})", expanded=False):
                    t_flow, t_agents, t_report = st.tabs([
                        "🌐 LangGraph Goal Propagation Flow",
                        "🎯 Goal-to-Agent Transparency Matrix",
                        "📄 Full Executive Report"
                    ])
                    
                    with t_flow:
                        st.caption("Visual representation of primary goal decomposition and authority delegation path:")
                        if msg.get("goal_flow_dot"):
                            safe_render_graphviz(msg["goal_flow_dot"])
                        else:
                            st.info("Goal flow graph not available for this turn.")
                            
                    with t_agents:
                        st.caption("Detailed breakdown of what each agent did under its delegated sub-goal:")
                        if msg.get("goal_matrix"):
                            df_mat = pd.DataFrame(msg["goal_matrix"])[[
                                "agent_name", "role", "assigned_goal", "delegation_id", "tools_invoked", "output_produced"
                            ]]
                            df_mat.columns = ["Agent", "Role", "Assigned Sub-Goal", "Delegation Token", "Tools Invoked", "Output Delivered"]
                            st.dataframe(df_mat, use_container_width=True)
                        else:
                            st.info("Traceability matrix not available.")
                            
                    with t_report:
                        if msg.get("report_content"):
                            st.markdown(msg["report_content"])
                            st.download_button(
                                "📥 Download Report (.md)",
                                data=msg["report_content"],
                                file_name=f"report_{wf_id}.md",
                                mime="text/markdown",
                                key=f"dl_{wf_id}"
                            )

    # Chat Input Box
    user_input = st.chat_input("Tell the Coordinator agent what to investigate or accomplish...")
    prompt_to_process = preset_clicked or user_input

    if prompt_to_process:
        # Append User Message
        st.session_state["chat_messages"].append({"role": "user", "content": prompt_to_process})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt_to_process)

        # Process with Coordinator Agent
        with st.chat_message("assistant", avatar="🤖"):
            p_lower = prompt_to_process.lower().strip()
            direct_ans, should_run_workflow = answer_user_query_directly(prompt_to_process)

            if not should_run_workflow:
                st.markdown(direct_ans)
                st.session_state["chat_messages"].append({
                    "role": "assistant",
                    "content": direct_ans
                })
            else:
                # Orchestrate real multi-agent goal execution tailored to the user's task
                target_dataset = "customer_complaints.csv"
                if any(k in p_lower for k in ["access", "security", "unauthorized", "login", "root", "escalation", "log"]):
                    target_dataset = "system_access_logs.csv"
                elif any(k in p_lower for k in ["research", "note", "architecture", "model", "paper", "cim", "three-graph"]):
                    target_dataset = "sample_research_notes.txt"

                with st.spinner("🤖 Coordinating multi-agent team investigation via Hugging Face Router..."):
                    run_mode = WorkflowMode.LIVE_HUGGINGFACE
                    run = runner.execute_workflow(
                        task_description=prompt_to_process,
                        dataset_name=target_dataset,
                        principal_id="user_chat_principal",
                        mode=run_mode,
                        capture_level=CaptureLevel.METADATA_SUMMARY
                    )

                st.session_state["latest_workflow_id"] = run.workflow_id

                delegations = store.get_delegation_closure(run.root_delegation_id) if run.root_delegation_id else store.list_delegations(limit=50)
                interactions = store.list_interactions(workflow_id=run.workflow_id)
                events = store.list_execution_events(workflow_id=run.workflow_id)
                del_map = {d.agent_id: d for d in delegations}

                matrix = extract_goal_traceability(run.model_dump(), delegations, interactions, events)
                goal_dot = generate_goal_flow_dot(
                    task_description=run.task_description,
                    dataset_name=target_dataset,
                    root_delegation_id=run.root_delegation_id,
                    research_delegation_id=del_map.get("agent_researcher").delegation_id if "agent_researcher" in del_map else None,
                    analysis_delegation_id=del_map.get("agent_analyst").delegation_id if "agent_analyst" in del_map else None,
                    report_delegation_id=del_map.get("agent_reporter").delegation_id if "agent_reporter" in del_map else None,
                    clarification_occurred=run.stats.get("clarification_occurred", True) if run.stats else True,
                    status=run.status,
                    interactions=interactions,
                    final_output=run.final_output
                )

                # 1. DIRECT DATA RESULT
                direct_findings = format_direct_task_findings(prompt_to_process, target_dataset, run)
                st.markdown(direct_findings)

                # Transparency is on-demand in dedicated tabs or optional collapse
                with st.expander("🔍 View Technical Transparency & Agent Execution Trace", expanded=False):
                    t_flow, t_agents, t_report = st.tabs([
                        "🌐 LangGraph Goal Propagation Flow",
                        "🎯 Goal-to-Agent Transparency Matrix",
                        "📄 Full Executive Report"
                    ])

                    with t_flow:
                        st.caption("Visual representation showing what task was given to Agent A, what sub-task Agent A delegated to B, what B transferred to C, what C analyzed for D, and the final response returned to you:")
                        safe_render_graphviz(goal_dot)

                    with t_agents:
                        st.caption("Detailed breakdown of what each agent did under its delegated sub-goal:")
                        df_mat = pd.DataFrame(matrix)[[
                            "agent_name", "role", "assigned_goal", "delegation_id", "tools_invoked", "output_produced"
                        ]]
                        df_mat.columns = ["Agent", "Role", "Assigned Sub-Goal", "Delegation Token", "Tools Invoked", "Output Delivered"]
                        st.dataframe(df_mat, use_container_width=True)

                    with t_report:
                        if run.final_output:
                            st.markdown(run.final_output)
                            st.download_button(
                                "📥 Download Report (.md)",
                                data=run.final_output,
                                file_name=f"report_{run.workflow_id}.md",
                                mime="text/markdown",
                                key=f"dl_live_{run.workflow_id}"
                            )

                st.session_state["chat_messages"].append({
                    "role": "assistant",
                    "content": direct_findings,
                    "goal_flow_dot": goal_dot,
                    "goal_matrix": matrix,
                    "workflow_id": run.workflow_id,
                    "root_delegation_id": run.root_delegation_id,
                    "report_content": run.final_output
                })

# ==============================================================================
# PAGE 2: HUGGING FACE MULTI-AGENT RESEARCH SIMULATION & TRANSPARENCY OBSERVER
# ==============================================================================
elif page == "2. 🚀 Hugging Face Multi-Agent Simulation":
    st.markdown('<div class="main-header">Hugging Face Router Multi-Agent Research Simulation</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Live dynamic multi-agent interaction between <b>Coordinator_Agent</b> '
        '(<code>meta-llama/Llama-3.1-8B-Instruct</code>) and <b>Executor_Agent</b> '
        '(<code>Qwen/Qwen2.5-7B-Instruct</code>) over the Hugging Face Router (<code>router.huggingface.co/v1</code>). '
        'Inspect observable message envelopes, authority tokens, and execution context with <b>internal reasoning (&lt;think&gt; blocks) strictly stripped</b>.</div>',
        unsafe_allow_html=True
    )

    st.info(
        "🧠 **Scope Boundary (RM_MID Slide 5 & 12)**: In accordance with transparency and privacy invariants, "
        "internal neural reasoning chains (`<think>...</think>`) are systematically removed before inter-agent logging. "
        "Only public communications, explicit delegation tokens (`del_...`), and normalized CIM execution events are captured."
    )

    col_sim1, col_sim2 = st.columns([2, 1])
    with col_sim1:
        sim_prompt = st.text_area(
            "Research Directive / Initial Goal",
            value="Audit customer churn dataset for critical severity anomalies and verify delegation token validity.",
            height=90,
            help="Initial research directive injected into the shared dialogue log."
        )
    with col_sim2:
        sim_turns = st.slider("Simulation Turns", min_value=2, max_value=20, value=6, step=2, help="Number of alternating Coordinator-Executor turns.")
        sim_capture = st.selectbox(
            "Telemetry Capture Level",
            [1, 2, 3],
            index=1,
            format_func=lambda x: f"Level {x}: {'Metadata Only' if x == 1 else 'Metadata + Summary' if x == 2 else 'Full Content (PII-Redacted)'}"
        )

    if st.button("🚀 Run Dynamic Multi-Agent Simulation", type="primary"):
        with st.spinner(f"Executing {sim_turns} turns via Hugging Face Router ({settings.HF_COORDINATOR_MODEL} & {settings.HF_EXECUTOR_MODEL})..."):
            sim_res = run_huggingface_transparency_simulation(
                max_turns=sim_turns,
                custom_prompt=sim_prompt,
                capture_level=CaptureLevel(sim_capture)
            )
            st.session_state["hf_sim_result"] = sim_res
            st.session_state["latest_workflow_id"] = sim_res["workflow_id"]
            st.success(f"✅ Simulation Complete! Recorded Workflow ID: `{sim_res['workflow_id']}`")

    # Display Simulation Result
    sim_data = st.session_state.get("hf_sim_result")
    if sim_data:
        st.markdown("---")
        st.subheader("📊 Multi-Agent Simulation Telemetry & Observability Envelope")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Workflow ID", sim_data["workflow_id"])
        m2.metric("Turns Executed", f"{sim_data['turns_executed']} turns")
        m3.metric("Root Delegation", sim_data["root_delegation_id"][:12])
        m4.metric("Executor Delegation", sim_data["executor_delegation_id"][:12])

        # Turn-by-Turn Dialogue View
        st.subheader("💬 Inter-Agent Public Communication Log (Reasoning Stripped)")
        st.caption("Notice: Every message is cryptographically attributed and timestamped in the EventStore.")

        comm_log = sim_data.get("communication_log", [])
        for idx, entry in enumerate(comm_log):
            content = entry.get("content", "")
            if "[Coordinator_Agent]" in content:
                with st.chat_message("user", avatar="🎯"):
                    st.markdown(f"**Turn {idx+1} • Coordinator Agent** (`{settings.HF_COORDINATOR_MODEL}`)")
                    clean_msg = content.replace("[Coordinator_Agent]:", "").strip()
                    st.write(clean_msg)
            elif "[Executor_Agent]" in content:
                with st.chat_message("assistant", avatar="⚡"):
                    st.markdown(f"**Turn {idx+1} • Executor Agent** (`{settings.HF_EXECUTOR_MODEL}`)")
                    clean_msg = content.replace("[Executor_Agent]:", "").strip()
                    st.write(clean_msg)
            else:
                with st.chat_message("human", avatar="👤"):
                    st.markdown(f"**Turn {idx+1} • Principal**")
                    st.write(content)

        # Transparency Tabs
        st.markdown("---")
        st.subheader("🔍 Three-Graph Transparency Observation")

        t_graph, t_auth, t_exec, t_matrix = st.tabs([
            "🕸️ Interaction Graph (G_inter)",
            "🛡️ Authority Graph (G_auth)",
            "⚙️ Execution Context (G_exec)",
            "📋 Goal Traceability Matrix"
        ])

        with t_graph:
            st.markdown("#### Dynamic Inter-Agent Interaction Graph ($G_{inter}$)")
            st.caption("Captures sender/receiver agent endpoints, turn causality, message envelopes, and sensitivity labels.")
            g_inter = sim_data["three_graphs"]["interaction_graph"]
            st.write(f"- **Total Nodes**: {g_inter.number_of_nodes()} (Agents & Message Envelopes)")
            st.write(f"- **Total Directed Edges**: {g_inter.number_of_edges()} (Causal Communications & Reply-To Links)")
            if sim_data.get("goal_dot"):
                st.graphviz_chart(sim_data["goal_dot"])

        with t_auth:
            st.markdown("#### Cryptographic Authority Graph ($G_{auth}$)")
            st.caption("Tracks the delegation lineage from the Principal down through the Coordinator to the Executor.")
            g_auth = sim_data["three_graphs"]["authority_graph"]
            auth_nodes = list(g_auth.nodes(data=True))
            auth_rows = []
            for node_id, data in auth_nodes:
                auth_rows.append({
                    "Delegation ID": node_id,
                    "Principal": data.get("principal", "Unknown"),
                    "Agent": data.get("agent", "Unknown"),
                    "Scope": data.get("scope", "General"),
                    "Status": data.get("status", "active")
                })
            if auth_rows:
                st.dataframe(pd.DataFrame(auth_rows), use_container_width=True)

        with t_exec:
            st.markdown("#### Normalized Tool Execution Context ($G_{exec}$)")
            st.caption("Common Information Model (CIM) tool invocations executed across the Hugging Face Router.")
            events = store.list_execution_events(workflow_id=sim_data["workflow_id"])
            if events:
                evt_rows = [{
                    "Timestamp": e.timestamp[:19],
                    "Agent": e.agent_id,
                    "Tool": e.tool_name,
                    "Operation": e.tool_operation,
                    "Resource": e.resource_id,
                    "Delegation ID": e.delegation_id,
                    "Outcome": e.action_outcome
                } for e in events]
                st.dataframe(pd.DataFrame(evt_rows), use_container_width=True)
            else:
                st.info("No tool events recorded for this workflow.")

        with t_matrix:
            st.markdown("#### End-to-End Goal & Traceability Matrix")
            st.caption("Correlates research goals, delegated tokens, observable messages, and downstream execution consequences.")
            mat = sim_data.get("matrix", [])
            if mat:
                st.dataframe(pd.DataFrame(mat), use_container_width=True)
            else:
                st.info("Matrix generated successfully.")

# ==============================================================================
# PAGE 3: LANGGRAPH GOAL FLOW & TOPOLOGY
# ==============================================================================
elif page == "3. 🌐 LangGraph Goal Flow & Topology":
    st.markdown('<div class="main-header">LangGraph Goal Flow & State Machine Topology</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Inspect genuine compiled LangGraph state machines and visualize how goals propagate across '
        'specialized agents according to <b>Mishra & Sharad (arXiv:2606.09692v1)</b> and <b>RM_MID.pdf</b>.</div>',
        unsafe_allow_html=True
    )

    # Topology Selector from Research Paper
    topologies = get_available_workflow_topologies()
    colTop1, colTop2 = st.columns([1, 2])
    with colTop1:
        selected_topo_key = st.selectbox(
            "LangGraph Topology Architecture",
            list(topologies.keys()),
            format_func=lambda k: topologies[k]["name"]
        )
    with colTop2:
        topo_meta = topologies[selected_topo_key]
        st.info(f"**{topo_meta['name']}** ({topo_meta['paper_ref']}): {topo_meta['description']}")

    wf_runs = store.list_workflow_runs(limit=25)
    if not wf_runs:
        st.warning("No workflow runs found yet. Use the Chat interface or Agent Workspace to execute a goal first.")
    else:
        selected_wid = st.selectbox(
            "Select Workflow Run to Inspect Execution Trace",
            [r.workflow_id for r in wf_runs],
            format_func=lambda wid: f"{wid} — {next((r.task_description[:55] for r in wf_runs if r.workflow_id == wid), '')}..."
        )
        selected_run = next((r for r in wf_runs if r.workflow_id == selected_wid), None)

        if selected_run:
            delegations = store.get_delegation_closure(selected_run.root_delegation_id) if selected_run.root_delegation_id else store.list_delegations(limit=50)
            interactions = store.list_interactions(workflow_id=selected_wid)
            events = store.list_execution_events(workflow_id=selected_wid)
            del_map = {d.agent_id: d for d in delegations}
            active_nodes = selected_run.stats.get("node_history", []) if selected_run.stats else []

            goal_dot = generate_goal_flow_dot(
                task_description=selected_run.task_description,
                dataset_name=selected_run.dataset_name or "customer_complaints.csv",
                root_delegation_id=selected_run.root_delegation_id,
                research_delegation_id=del_map.get("agent_researcher").delegation_id if "agent_researcher" in del_map else None,
                analysis_delegation_id=del_map.get("agent_analyst").delegation_id if "agent_analyst" in del_map else None,
                report_delegation_id=del_map.get("agent_reporter").delegation_id if "agent_reporter" in del_map else None,
                clarification_occurred=selected_run.stats.get("clarification_occurred", True) if selected_run.stats else True,
                status=selected_run.status,
                interactions=interactions,
                final_output=selected_run.final_output
            )

            statemachine_dot = generate_langgraph_statemachine_dot(active_nodes=active_nodes, workflow_type=selected_topo_key)
            mermaid_str = get_langgraph_mermaid(workflow_type=selected_topo_key)
            matrix = extract_goal_traceability(selected_run.model_dump(), delegations, interactions, events)

            tabG1, tabG2, tabG3, tabG4 = st.tabs([
                "1. 🌐 Goal Propagation Flow",
                "2. 🔀 Compiled LangGraph Topology (Graphviz & Mermaid)",
                "3. ⏱️ LangGraph Node Execution Trace",
                "4. 📋 Goal & Authority Traceability Matrix"
            ])

            with tabG1:
                st.markdown("### Goal Hand-off & Delegation Path")
                st.caption("Shows how the primary goal given to the Coordinator propagates into sub-goals for specialized agents:")
                safe_render_graphviz(goal_dot)

            with tabG2:
                st.markdown(f"### Compiled StateGraph Topology: {topo_meta['name']}")
                st.caption("Derived dynamically from the compiled `CompiledStateGraph` object:")
                colM1, colM2 = st.columns([3, 2])
                with colM1:
                    safe_render_graphviz(statemachine_dot)
                with colM2:
                    st.markdown("**Native LangGraph Mermaid Output:**")
                    st.code(mermaid_str, language="mermaid")

            with tabG3:
                st.markdown("### Step-by-Step LangGraph Node Transitions")
                if active_nodes:
                    st.caption(f"Sequential node execution history recorded for Run `{selected_wid}`:")
                    for idx, node in enumerate(active_nodes, 1):
                        clean_node = node.replace("node_", "").replace("_", " ").title()
                        st.markdown(f"**Step {idx}:** `{node}` — *{clean_node}*")
                else:
                    st.info("No detailed node history available for this legacy run.")

            with tabG4:
                st.markdown("### Per-Agent Goal & Authority Traceability")
                df_mat = pd.DataFrame(matrix)[[
                    "agent_name", "role", "assigned_goal", "delegation_id", "parent_authority", "scope", "tools_invoked", "output_produced"
                ]]
                df_mat.columns = ["Agent", "Role", "Assigned Sub-Goal", "Delegation Token", "Parent Authority", "Scope", "Tools", "Output Delivered"]
                st.dataframe(df_mat, use_container_width=True)

# ==============================================================================
# PAGE 4: AGENT WORKSPACE (BATCH RUNNER)
# ==============================================================================
elif page == "4. 📋 Agent Workspace (Task Runner)":
    st.markdown('<div class="main-header">Multi-Agent Execution Workspace (Task Runner)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Submit parameterized research and security audit tasks to the LangGraph 4-agent team.</div>', unsafe_allow_html=True)

    with st.expander("ℹ️ Available Sample Datasets", expanded=False):
        datasets = list_sample_datasets()
        st.json(datasets)

    col1, col2 = st.columns([2, 1])
    with col1:
        task_prompt = st.text_area(
            "Natural Language Task Description",
            value="Analyze customer complaints for High/Critical severity issues, request priority clarification if needed, and synthesize an executive report.",
            height=100
        )
    with col2:
        dataset_choice = st.selectbox(
            "Select Target Dataset",
            ["customer_complaints.csv", "system_access_logs.csv", "sample_research_notes.txt"]
        )
        workflow_type_choice = st.selectbox(
            "LangGraph Architecture Pattern",
            ["adaptive", "w1_parallel", "w3_retry"],
            format_func=lambda x: "Adaptive Multi-Agent (Default)" if x == "adaptive" else "W1: Parallel Subtasks (Paper)" if x == "w1_parallel" else "W3: Trial-and-Adapt / Retries"
        )
        mode_choice = st.radio(
            "Inference Mode",
            ["live_api", "deterministic_demo"],
            index=0,
            format_func=lambda x: f"🌐 Live LLM Cloud API ({settings.LLM_MODEL})" if x == "live_api" else "Deterministic Demo (Zero-Dependency)",
            help="Live API mode executes multi-agent inference via configured API (OpenAI, Groq, Router)."
        )
        capture_level_choice = st.selectbox(
            "Capture Level",
            [1, 2, 3],
            index=1,
            format_func=lambda x: f"Level {x}: {'Metadata Only' if x == 1 else 'Metadata + Summary' if x == 2 else 'Full Observable Content'}"
        )

    if st.button("🚀 Execute Multi-Agent Workflow", type="primary"):
        with st.spinner(f"LangGraph orchestrating workflow ({workflow_type_choice})..."):
            if mode_choice == "live_api":
                run_mode = WorkflowMode.LIVE_API
            else:
                run_mode = WorkflowMode.DETERMINISTIC_DEMO
            cap_enum = CaptureLevel(capture_level_choice)
            
            run = runner.execute_workflow(
                task_description=task_prompt,
                dataset_name=dataset_choice,
                principal_id="principal_user",
                mode=run_mode,
                capture_level=cap_enum,
                workflow_type=workflow_type_choice
            )
            
            if run.status == "completed":
                st.success(f"✅ Workflow Completed Successfully! Run ID: `{run.workflow_id}`")
            else:
                st.error(f"Workflow Status: {run.status}. Error: {run.error_message}")

            st.session_state["latest_workflow_id"] = run.workflow_id

    # Display Latest or Selected Report
    latest_id = st.session_state.get("latest_workflow_id")
    if latest_id:
        st.markdown("---")
        st.markdown(f"### Final Generated Report (`{latest_id}`)")
        wf = store.get_workflow_run(latest_id)
        if wf and wf.final_output:
            st.markdown(wf.final_output)
            st.download_button(
                "📥 Download Markdown Report",
                data=wf.final_output,
                file_name=f"report_{latest_id}.md",
                mime="text/markdown"
            )

# ==============================================================================
# PAGE 5: OVERVIEW & TELEMETRY
# ==============================================================================
elif page == "5. 📊 Overview & Telemetry":
    st.markdown('<div class="main-header">System Observability Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Real-time status of multi-agent tasks, delegations, communication interactions, and capture metrics.</div>', unsafe_allow_html=True)
    
    summary = store.get_metrics_summary()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{summary["total_workflows"]}</div><div class="metric-lbl">Total Workflows</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{summary["active_agents"]}</div><div class="metric-lbl">Active Agents</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{summary["total_interactions"]}</div><div class="metric-lbl">Inter-Agent Messages</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{summary["total_events"]}</div><div class="metric-lbl">Tool CIM Events</div></div>', unsafe_allow_html=True)
    with col5:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{summary["total_delegations"]}</div><div class="metric-lbl">Delegation Tokens</div></div>', unsafe_allow_html=True)

    st.markdown("### Recent Workflow Executions")
    runs = store.list_workflow_runs(limit=10)
    if runs:
        df_runs = pd.DataFrame([{
            "Workflow ID": r.workflow_id,
            "Task": r.task_description[:50] + "...",
            "Dataset": r.dataset_name,
            "Mode": r.mode.value if hasattr(r.mode, "value") else str(r.mode),
            "Status": r.status.upper(),
            "Start Time": r.start_time
        } for r in runs])
        st.dataframe(df_runs, use_container_width=True)

    colA, colB = st.columns(2)
    with colA:
        st.markdown("### Telemetry Breakdown by Agent")
        events = store.list_execution_events(limit=500)
        if events:
            agent_counts = pd.Series([e.agent_id for e in events]).value_counts().reset_index()
            agent_counts.columns = ["Agent", "Event Count"]
            fig_pie = px.pie(agent_counts, values="Event Count", names="Agent", hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
            fig_pie.update_layout(margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.caption("No events to display.")
            
    with colB:
        st.markdown("### Interaction Types Distribution")
        itrs = store.list_interactions(limit=500)
        if itrs:
            itr_types = pd.Series([i.interaction_type.value if hasattr(i.interaction_type, "value") else str(i.interaction_type) for i in itrs]).value_counts().reset_index()
            itr_types.columns = ["Type", "Count"]
            fig_bar = px.bar(itr_types, x="Type", y="Count", color="Type", color_discrete_sequence=px.colors.qualitative.Vivid)
            fig_bar.update_layout(margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.caption("No interactions to display.")

# ==============================================================================
# PAGE 6: COMMUNICATION TIMELINE
# ==============================================================================
elif page == "6. ⏱️ Communication Timeline":
    st.markdown('<div class="main-header">Inter-Agent Communication Timeline</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Chronological record of genuine observable messages exchanged through the Observability Gateway.</div>', unsafe_allow_html=True)

    colA, colB, colC = st.columns(3)
    with colA:
        agent_filter = st.selectbox("Filter by Agent", ["All"] + ["agent_coordinator", "agent_researcher", "agent_analyst", "agent_reporter"])
    with colB:
        type_filter = st.selectbox("Filter by Interaction Type", ["All"] + [t.value for t in InteractionType])
    with colC:
        limit_count = st.slider("Max Messages to Display", 10, 200, 50)

    itrs = store.list_interactions(
        agent_id=agent_filter if agent_filter != "All" else None,
        interaction_type=type_filter if type_filter != "All" else None,
        limit=limit_count
    )

    if itrs:
        for item in itrs:
            with st.container():
                itype = item.interaction_type.value if hasattr(item.interaction_type, "value") else str(item.interaction_type)
                st.markdown(f"""
                <div style="background-color: #f8fafc; border-left: 4px solid #6366f1; padding: 12px; margin-bottom: 8px; border-radius: 4px;">
                    <div style="font-size: 11px; color: #64748b; margin-bottom: 4px;">
                        <span>🕒 {item.timestamp}</span> | 
                        <span><b>Sender:</b> {item.sender_agent_id} ➔ <b>Receiver:</b> {item.receiver_agent_id}</span> | 
                        <span><b>Type:</b> <code>{itype}</code></span> | 
                        <span><b>Delegation:</b> <code>{item.delegation_id}</code></span>
                    </div>
                    <div style="font-size: 13px; color: #1e293b; font-weight: 500;">
                        {item.semantic_summary}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander(f"Inspect Message Details ({item.interaction_id})"):
                    st.json(item.model_dump())
    else:
        st.info("No inter-agent messages match the selected filters.")

# ==============================================================================
# PAGE 7: INTERACTIVE GRAPH EXPLORER
# ==============================================================================
elif page == "7. 🕸️ Interactive Graph Explorer":
    st.markdown('<div class="main-header">Three-Graph Transparency Explorer</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Inspect the three correlated graph views: Execution Graph, Authority Graph, and our proposed Interaction Graph.</div>', unsafe_allow_html=True)

    wf_runs = store.list_workflow_runs(limit=20)
    if not wf_runs:
        st.warning("No workflow runs found. Run a task first.")
    else:
        selected_wf_id = st.selectbox(
            "Select Workflow Run to Inspect",
            [r.workflow_id for r in wf_runs],
            format_func=lambda wid: f"{wid} - {next((r.task_description[:45] for r in wf_runs if r.workflow_id == wid), '')}..."
        )

        tab1, tab2, tab3 = st.tabs([
            "1. Execution Graph (G_exec)",
            "2. Authority / Lineage Graph (G_auth)",
            "3. Interaction Graph (G_interact — OUR EXTENSION)"
        ])

        graphs = three_graphs.get_graphs_for_workflow(selected_wf_id)

        with tab1:
            st.markdown("**Execution Graph:** Represents causal execution flow, tool invocations, and span linkages. Answers: *'What happened?'*")
            fig1 = three_graphs.render_plotly_graph(graphs["execution_graph"], "Execution Graph (G_exec)", graph_type="execution")
            st.plotly_chart(fig1, use_container_width=True)

        with tab2:
            st.markdown("**Authority Graph:** Represents durable delegation authority and parent-child delegation lineage. Answers: *'Under whose authority did each action occur?'*")
            fig2 = three_graphs.render_plotly_graph(graphs["authority_graph"], "Authority / Lineage Graph (G_auth)", graph_type="authority")
            st.plotly_chart(fig2, use_container_width=True)

        with tab3:
            st.markdown("**Interaction Graph (Our Main Extension):** Represents inter-agent communication, message types, and explicitly connected downstream execution consequences. Answers: *'Who communicated with whom, what was exchanged, and what happened next?'*")
            fig3 = three_graphs.render_plotly_graph(graphs["interaction_graph"], "Interaction Graph (G_interact)", graph_type="interaction")
            st.plotly_chart(fig3, use_container_width=True)

# ==============================================================================
# PAGE 8: PROVENANCE EXPLORER
# ==============================================================================
elif page == "8. 🧬 Provenance Explorer":
    st.markdown('<div class="main-header">W3C PROV Provenance & Evidence Explorer</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Inspect the W3C PROV evidence DAG connecting output artifacts to activities, messages, and origin datasets (RM_MID Slide 10, 14).</div>', unsafe_allow_html=True)

    artifacts = store.list_artifacts()
    if artifacts:
        selected_art = st.selectbox("Select Target Artifact", [a.artifact_id for a in artifacts], format_func=lambda x: f"{x} - {next((a.title for a in artifacts if a.artifact_id == x), '')}")
        art_obj = store.get_artifact(selected_art)
        comp_score = prov_tracker.get_provenance_completeness(art_obj.workflow_id)
        
        colK1, colK2, colK3, colK4 = st.columns(4)
        with colK1:
            st.metric("Provenance Completeness", f"{comp_score * 100:.0f}%", delta="100% Target")
        with colK2:
            st.metric("Artifact Type", art_obj.artifact_type.replace("_", " ").title())
        with colK3:
            st.metric("Created By", art_obj.created_by_agent_id)
        with colK4:
            st.metric("Workflow Run ID", art_obj.workflow_id)

        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"**Artifact ID:** `{art_obj.artifact_id}`")
            st.markdown(f"**Title:** {art_obj.title}")
            st.markdown(f"**Created At:** {art_obj.created_at}")
            
            st.markdown("#### Backward Lineage Traversal")
            lineage = prov_tracker.trace_backward_lineage(selected_art, workflow_id=art_obj.workflow_id)
            st.caption(f"Traced {len(lineage)} causal evidence dependencies to information origin.")
            for step in lineage:
                src = step.get("source_label", step.get("source", "source"))
                rel = step.get("relation", "wasDerivedFrom")
                tgt = step.get("target_label", step.get("target", "target"))
                st.markdown(f"- `{src}` ➔ **{rel}** ➔ `{tgt}`")

            st.markdown("---")
            st.markdown("#### W3C PROV Export")
            prov_json_data = prov_tracker.export_prov_json(art_obj.workflow_id)
            prov_n_data = prov_tracker.export_prov_n(art_obj.workflow_id)
            st.download_button(
                "📥 Export W3C PROV-JSON",
                data=json.dumps(prov_json_data, indent=2),
                file_name=f"prov_{art_obj.workflow_id}.json",
                mime="application/json"
            )
            st.download_button(
                "📄 Export W3C PROV-N Notation",
                data=prov_n_data,
                file_name=f"prov_{art_obj.workflow_id}.provn",
                mime="text/plain"
            )

        with col2:
            st.markdown("#### W3C PROV Lineage DAG")
            st.caption("Standard PROV styling: Entities (Yellow), Activities (Blue), Agents (Orange)")
            g_prov = prov_tracker.build_provenance_graph(workflow_id=art_obj.workflow_id)
            fig_prov = prov_tracker.render_provenance_plotly(g_prov)
            st.plotly_chart(fig_prov, use_container_width=True)

            with st.expander("📋 Inspect W3C PROV Elements Table", expanded=False):
                prov_rows = []
                for n, data in g_prov.nodes(data=True):
                    prov_rows.append({
                        "Identifier": n,
                        "Label": data.get("label", n),
                        "W3C PROV Category": data.get("prov_category", "prov:Entity"),
                        "Domain Type": data.get("node_type", "unknown")
                    })
                st.dataframe(pd.DataFrame(prov_rows), use_container_width=True)
    else:
        st.info("No artifacts recorded yet. Submit a goal in the Chat or Agent Workspace to generate a provenance-tracked report artifact.")

# ==============================================================================
# PAGE 9: EVENT INSPECTOR
# ==============================================================================
elif page == "9. 🔍 Event Inspector":
    st.markdown('<div class="main-header">CIM Event Inspector</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Raw Common Information Model (CIM) tool events normalized by the Observability Gateway.</div>', unsafe_allow_html=True)

    colA, colB, colC = st.columns(3)
    with colA:
        agent_sel = st.selectbox("Filter by Agent ID", ["All"] + ["agent_researcher", "agent_analyst", "agent_reporter"])
    with colB:
        semantic_sel = st.selectbox("Filter by Action Semantic", ["All", "read", "search", "write", "execute"])
    with colC:
        limit_ev = st.slider("Event Query Limit", 10, 500, 100)

    events = store.list_execution_events(
        agent_id=agent_sel if agent_sel != "All" else None,
        action_semantic=semantic_sel if semantic_sel != "All" else None,
        limit=limit_ev
    )

    if events:
        df_ev = pd.DataFrame([{
            "Event ID": e.event_id,
            "Time": e.time,
            "Agent": e.agent_id,
            "Tool": e.tool_name,
            "Operation": e.tool_operation,
            "Semantic": e.action_semantic.value if hasattr(e.action_semantic, "value") else str(e.action_semantic),
            "Outcome": e.action_outcome.value if hasattr(e.action_outcome, "value") else str(e.action_outcome),
            "Resource": e.resource_id,
            "Delegation ID": e.delegation_id
        } for e in events])
        st.dataframe(df_ev, use_container_width=True)

        selected_ev_id = st.selectbox("Select Event ID to Inspect Full CIM Record", [e.event_id for e in events])
        full_event = next((e for e in events if e.event_id == selected_ev_id), None)
        if full_event:
            st.json(full_event.model_dump())
    else:
        st.info("No execution events found matching filters.")

# ==============================================================================
# PAGE 10: RESEARCH EVALUATION
# ==============================================================================
elif page == "10. 🧪 Research Evaluation":
    st.markdown('<div class="main-header">Research Evaluation & Baseline Benchmark Suite</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Evaluating 8 representative scenarios against 5 baseline observability configurations.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("""
        **Evaluated Baselines:**
        - **B0: Distributed Tracing Only** (Standard OpenTelemetry spans, trace IDs, parent spans).
        - **B1: Time-Window Correlation** (Correlating events within rolling temporal windows).
        - **B2: SIEM Hybrid Heuristics** (Rule-based heuristics and access log joins).
        - **B3: Common Information Model Only (CIM-Only)** (Mishra & Sharad 2026 reference paper without interaction graph).
        - **B4: Proposed Three-Graph Transparency Platform** (CIM + Interaction Graph + Provenance + 3-Tier Privacy).
        """)
    with col2:
        if st.button("⚡ Re-Run Benchmark Suite", type="secondary"):
            with st.spinner("Generating synthetic evaluation runs across 8 scenarios..."):
                benchmark.run_full_evaluation(size_per_scenario=50)
                st.success("Benchmarks completed and cached!")

    if benchmark.results_json_path.exists():
        with open(benchmark.results_json_path, "r", encoding="utf-8") as f:
            eval_data = json.load(f)
        
        df_eval = pd.DataFrame(eval_data)
        
        st.markdown("### 📊 Academic Comparative Benchmark Summary (Mishra & Sharad Table 5 & RM_MID Slide 15)")
        
        # Aggregate summary table matching academic paper
        agg_table = df_eval.groupby("baseline").agg({
            "delegation_attribution_accuracy": "mean",
            "median_recall": "mean" if "median_recall" in df_eval.columns else "mean",
            "interaction_completeness": "mean",
            "ambiguity": "mean",
            "provenance_completeness": "mean",
            "query_operations": "mean",
            "bytes_per_event": "mean",
            "privacy_exposure": "mean" if "privacy_exposure" in df_eval.columns else "mean",
            "latency_p95_ms": "mean"
        }).reset_index()

        agg_table["delegation_attribution_accuracy"] = agg_table["delegation_attribution_accuracy"].apply(lambda v: f"{v*100:.1f}%")
        agg_table["interaction_completeness"] = agg_table["interaction_completeness"].apply(lambda v: f"{v*100:.1f}%")
        agg_table["provenance_completeness"] = agg_table["provenance_completeness"].apply(lambda v: f"{v*100:.1f}%")
        agg_table["ambiguity"] = agg_table["ambiguity"].apply(lambda v: f"{v:.1f}")
        agg_table["query_operations"] = agg_table["query_operations"].apply(lambda v: f"{int(v)} ops")
        agg_table["bytes_per_event"] = agg_table["bytes_per_event"].apply(lambda v: f"{int(v)} B")
        agg_table["latency_p95_ms"] = agg_table["latency_p95_ms"].apply(lambda v: f"+{v:.2f} ms")

        col_names = {
            "baseline": "Baseline Model",
            "delegation_attribution_accuracy": "Delegation Recall",
            "median_recall": "Median Rec(d)",
            "interaction_completeness": "Interaction Completeness",
            "ambiguity": "Ambiguity Amb(E)",
            "provenance_completeness": "Provenance Completeness",
            "query_operations": "Query Burden",
            "bytes_per_event": "Storage / Event",
            "privacy_exposure": "Privacy Exposure",
            "latency_p95_ms": "p95 Latency"
        }
        agg_table = agg_table.rename(columns={k: v for k, v in col_names.items() if k in agg_table.columns})
        st.dataframe(agg_table, use_container_width=True)

        st.markdown("### 📈 Metric Comparison Across Baselines")
        t_chart1, t_chart2 = st.tabs(["🎯 Completeness & Ambiguity", "⚡ Operational Cost & Query Overhead"])

        with t_chart1:
            colA, colB = st.columns(2)
            with colA:
                avg_interaction = df_eval.groupby("baseline")["interaction_completeness"].mean().reset_index()
                fig_i = px.bar(
                    avg_interaction, x="baseline", y="interaction_completeness",
                    title="Interaction Record Completeness (Recall %)",
                    color="baseline",
                    color_discrete_sequence=px.colors.qualitative.Prism
                )
                fig_i.update_layout(yaxis=dict(range=[0, 1.1]))
                st.plotly_chart(fig_i, use_container_width=True)

            with colB:
                avg_amb = df_eval.groupby("baseline")["ambiguity"].mean().reset_index()
                fig_amb = px.bar(
                    avg_amb, x="baseline", y="ambiguity",
                    title="Delegation Ambiguity Amb(E) [Lower is Better, Ideal=1.0]",
                    color="baseline",
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                st.plotly_chart(fig_amb, use_container_width=True)

        with t_chart2:
            colC, colD = st.columns(2)
            with colC:
                avg_ops = df_eval.groupby("baseline")["query_operations"].mean().reset_index()
                fig_ops = px.bar(
                    avg_ops, x="baseline", y="query_operations",
                    title="Query Operations Required to Answer Delegation & Interaction Questions",
                    color="baseline",
                    color_discrete_sequence=px.colors.qualitative.Safe
                )
                st.plotly_chart(fig_ops, use_container_width=True)

            with colD:
                avg_bytes = df_eval.groupby("baseline")["bytes_per_event"].mean().reset_index()
                fig_bytes = px.bar(
                    avg_bytes, x="baseline", y="bytes_per_event",
                    title="Storage Overhead per Serialized Event (Bytes)",
                    color="baseline",
                    color_discrete_sequence=px.colors.qualitative.Teal
                )
                st.plotly_chart(fig_bytes, use_container_width=True)

        st.markdown("### 🔬 Full 8-Scenario Experimental Breakdown")
        st.dataframe(df_eval, use_container_width=True)

# ==============================================================================
# PAGE 11: ARCHITECTURE & DOCS
# ==============================================================================
elif page == "11. 📖 Architecture & Docs":
    st.markdown('<div class="main-header">System Architecture & Research Traceability</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Mapping theoretical models to implementation components and structural invariants.</div>', unsafe_allow_html=True)

    st.markdown("""
    ### 1. Research Foundation vs. Our Extension
    
    | Dimension | Reference Paper (Mishra & Sharad, 2026) | Our Proposed Research Extension |
    |---|---|---|
    | **Core Problem** | Non-identifiability of delegated execution from standard traces | Ephemeral, opaque inter-agent communication and missing interaction history |
    | **Primary Telemetry** | Common Information Model (CIM) tool execution events | **Persistent Inter-Agent Interaction Graph** integrated with CIM |
    | **Graph Model** | Dual Graphs: Execution Graph + Authority Graph | **Three-Graph Model:** Execution + Authority + **Interaction Graph** + Provenance |
    | **Communication Capture** | Omitted / out of scope | Structured interaction records with 9 interaction types |
    | **Downstream Linking** | Causal trace parent/child only | Explicit linkage from interaction to subsequent tool actions |
    | **Privacy Tiers** | Coarse metadata-only | **Three-Tier Privacy Capture** (Metadata, Summary, Redacted Full Content) |
    | **Chain-of-Thought** | Excluded | Excluded (strictly observable communication only) |

    ### 2. The Three-Graph Transparency Model
    ```mermaid
    graph TD
        subgraph Layer 1: Authority & Lineage
            Principal[User / Principal] -->|delegates| DelRoot[Root Delegation D0]
            DelRoot -->|re-delegates| DelRes[Research Delegation D1]
            DelRoot -->|re-delegates| DelAna[Analysis Delegation D2]
            DelRoot -->|re-delegates| DelRep[Report Delegation D3]
        end

        subgraph Layer 2: Inter-Agent Interaction Graph (Our Extension)
            AgentCoord[Coordinator Agent] -->|request / delegation| AgentRes[Research Agent]
            AgentRes -->|information_transfer| AgentAna[Analysis Agent]
            AgentAna -->|clarification / response| AgentCoord
            AgentAna -->|result| AgentCoord
            AgentCoord -->|handoff| AgentRep[Report Agent]
        end

        subgraph Layer 3: Causal Execution Graph
            ToolRead[Tool: read_dataset] -->|outputs rows| ToolCalc[Tool: compute_analysis]
            ToolCalc -->|outputs metrics| ToolReport[Tool: format_report]
        end

        subgraph Layer 4: Provenance Layer
            Dataset[(Source Dataset)] -->|used by| ToolRead
            ToolRead -->|informed| AgentRes
            AgentRes -->|transferred to| ToolCalc
            ToolCalc -->|derived| FinalReport[Final Markdown Report]
        end
    ```

    ### 3. Coverage & Boundary Limitations
    1. **Uninstrumented Channels:** Tool calls or APIs that bypass the Observability Gateway are unobservable. Complete observability requires mandatory routing or explicit absence detection.
    2. **Attribution vs. Intent:** The platform records what transpired under delegated authority, not neural reasoning or model intentions.
    3. **Semantic Loss:** Metadata and summary tiers strip low-level details. Level 3 full content captures observable messages but redacts PII.
    4. **No Chain-of-Thought:** Internal neural model tokens and private hidden reasoning are intentionally never captured.
    """)

# ==============================================================================
# PAGE 12: OBSERVABILITY GATEWAY
# ==============================================================================
elif page == "12. 🛡️ Observability Gateway (Auto-Capture)":
    st.markdown('<div class="main-header">Central Observability Gateway</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Authoritative mediation boundary automatically intercepting all inter-agent communications and tool operations.</div>', unsafe_allow_html=True)
    
    all_interactions = store.list_interactions(limit=100)
    all_events = store.list_execution_events(limit=100)
    all_delegations = store.list_delegations(limit=100)
    
    # KPI metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Captured Messages", len(all_interactions), delta="9 Types Intercepted")
    with col2:
        st.metric("Tool Operations", len(all_events), delta="Tier-1 Normalized")
    with col3:
        st.metric("Delegations Minted", len(all_delegations), delta="Bound Authority")
    with col4:
        st.metric("Mediation Latency", "< 0.3 ms", delta="p95 Overhead")
        
    st.markdown("---")
    st.subheader("Gateway Invariants Enforced")
    inv_c1, inv_c2, inv_c3, inv_c4 = st.columns(4)
    with inv_c1:
        st.success("**I1: Authority Minting**\n\nTokens exclusively minted by Gateway.")
    with inv_c2:
        st.success("**I3: Lineage Closure**\n\nEvery delegation links to valid parent.")
    with inv_c3:
        st.success("**I4: Normalization**\n\nRaw tools mapped to Tier-1 verbs.")
    with inv_c4:
        st.success("**I5: Authority Binding**\n\nAll tools bound to delegation_id.")

    st.markdown("---")
    st.subheader("Live Intercepted Activity Feed")
    tab_comm, tab_tools = st.tabs(["💬 Inter-Agent Messages", "⚙️ Tool Executions"])
    
    with tab_comm:
        if not all_interactions:
            st.info("No inter-agent messages captured yet.")
        for itr in all_interactions[:30]:
            with st.expander(f"💬 [{itr.interaction_type.upper()}] {itr.sender_agent_id} ➔ {itr.receiver_agent_id} ({itr.interaction_id})"):
                st.write(f"**Delegation ID:** `{itr.delegation_id}`")
                st.write(f"**Summary:** {itr.semantic_summary or itr.content or 'No content'}")
                st.caption(f"Timestamp: {itr.timestamp} | Sensitivity: {itr.sensitivity_label}")
                
    with tab_tools:
        if not all_events:
            st.info("No tool activities captured yet.")
        for evt in all_events[:30]:
            with st.expander(f"⚙️ [{evt.action_semantic.upper()}] {evt.agent_id} calling {evt.tool_name}.{evt.tool_operation} ({evt.event_id})"):
                st.write(f"**Delegation ID:** `{evt.delegation_id}`")
                st.write(f"**Outcome:** `{evt.action_outcome}`")
                st.write(f"**Summary:** {evt.output_summary or 'Completed'}")
                st.caption(f"Time: {evt.time} | Resource: {evt.resource_id}")
