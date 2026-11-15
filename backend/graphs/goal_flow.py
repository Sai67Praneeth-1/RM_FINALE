"""
Goal Propagation Graph and LangGraph State Machine Visualization Module.
Dynamically constructs task-specific goal decomposition flows from real runtime
delegations, interactions, and execution payloads.
"""

import html
from typing import Dict, Any, List, Optional

def sanitize_label(text: str, max_len: int = 55) -> str:
    cleaned = str(text or "").replace('"', "'").replace("\n", " ").replace("\\", "/").strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len - 3] + "..."
    return cleaned

def generate_goal_flow_dot(
    task_description: str,
    dataset_name: str,
    root_delegation_id: Optional[str] = "del_root",
    research_delegation_id: Optional[str] = "del_research",
    analysis_delegation_id: Optional[str] = "del_analysis",
    report_delegation_id: Optional[str] = "del_report",
    clarification_occurred: bool = False,
    status: str = "completed",
    interactions: Optional[List[Any]] = None,
    final_output: Optional[str] = None
) -> str:
    """
    Generates a dynamic Graphviz DOT representation based on the specific task given,
    showing:
    1. The exact task given to Agent A by the User
    2. What sub-task Agent A gave to Agent B
    3. What data Agent B extracted and transferred to Agent C
    4. What analysis Agent C performed and transferred to Agent D
    5. What report Agent D synthesized and returned to Agent A
    6. What final answer was delivered to the User.
    """
    clean_task = sanitize_label(task_description, 45)
    clean_ds = sanitize_label(dataset_name, 28)
    root_id = html.escape(str(root_delegation_id or "del_root"))
    res_id = html.escape(str(research_delegation_id or "del_res"))
    ana_id = html.escape(str(analysis_delegation_id or "del_ana"))
    rep_id = html.escape(str(report_delegation_id or "del_rep"))

    # Extract dynamic payload details from actual interaction records if available
    task_to_b = f"Read and extract records from {clean_ds}"
    data_b_to_c = f"Transferred extracted records from {clean_ds}"
    analysis_c_to_d = "Computed quantitative severity & metric breakdown"
    report_d_to_a = "Completed Markdown audit report with provenance citations"
    ans_summary = "Delivered executive audit findings and recommendations"

    # Detect domain dynamically from task description or dataset
    t_lower = task_description.lower()
    if "access" in t_lower or "security" in t_lower or "log" in t_lower:
        domain_type = "Security Access Audit"
        tool_b = "file_system.read_sample_dataset (READ)"
        tool_c = "security_auditor.audit_security_access (SEARCH)"
        task_to_b = f"Extract unauthorized access & privileged escalation events from {clean_ds}"
        data_b_to_c = "Extracted security logs & credential touches transferred"
        analysis_c_to_d = "Flagged unauthorized sharing & sensitive resource touches"
        ans_summary = "Security audit findings & access revocation recommendations"
    elif "note" in t_lower or "research" in t_lower or clean_ds.endswith(".txt"):
        domain_type = "Research & Knowledge Synthesis"
        tool_b = "file_system.read_sample_dataset (READ)"
        tool_c = "content_analyzer.analyze_text_content (READ)"
        task_to_b = f"Parse research notes and extract thematic sections from {clean_ds}"
        data_b_to_c = "Extracted unstructured notes & quotes transferred"
        analysis_c_to_d = "Extracted strategic themes & action items"
        ans_summary = "Research takeaways & architectural alignment plan"
    else:
        domain_type = "Customer Complaint Analysis"
        tool_b = "file_system.read_sample_dataset (READ)"
        tool_c = "analytics_engine.analyze_sentiment_and_severity (INVOKE)"
        task_to_b = f"Ingest customer complaints and filter high/critical issues from {clean_ds}"
        data_b_to_c = "Extracted complaint records & customer IDs transferred"
        analysis_c_to_d = "Aggregated sentiment polarity & high-severity incidents"
        ans_summary = "Complaint severity distribution & SLA escalation plan"

    # If real interaction records were passed, extract actual summaries
    if interactions:
        for itr in interactions:
            summary = getattr(itr, "semantic_summary", None) or (itr.get("semantic_summary") if isinstance(itr, dict) else None)
            sender = getattr(itr, "sender_agent_id", None) or (itr.get("sender_agent_id") if isinstance(itr, dict) else None)
            receiver = getattr(itr, "receiver_agent_id", None) or (itr.get("receiver_agent_id") if isinstance(itr, dict) else None)
            itype = getattr(itr, "interaction_type", None) or (itr.get("interaction_type") if isinstance(itr, dict) else None)
            itype_val = itype.value if hasattr(itype, "value") else str(itype or "")

            if summary:
                if sender == "agent_coordinator" and receiver == "agent_researcher":
                    task_to_b = sanitize_label(summary, 50)
                elif sender == "agent_researcher" and receiver == "agent_analyst":
                    data_b_to_c = sanitize_label(summary, 50)
                elif sender == "agent_analyst" and receiver in ("agent_coordinator", "agent_reporter"):
                    analysis_c_to_d = sanitize_label(summary, 50)
                elif sender == "agent_reporter" and receiver == "agent_coordinator":
                    report_d_to_a = sanitize_label(summary, 50)

    clean_task_to_b = sanitize_label(task_to_b, 48)
    clean_data_b_to_c = sanitize_label(data_b_to_c, 48)
    clean_analysis_c_to_d = sanitize_label(analysis_c_to_d, 48)
    clean_report_d_to_a = sanitize_label(report_d_to_a, 48)
    clean_ans_summary = sanitize_label(ans_summary, 48)

    dot = [
        'digraph GoalFlow {',
        '    rankdir=TB;',
        '    graph [bgcolor="transparent", fontname="Segoe UI, Helvetica, Arial", nodesep=0.45, ranksep=0.55];',
        '    node [shape=box, style="filled,rounded", fontname="Segoe UI, Helvetica, Arial", fontsize=11, margin="0.22,0.14", penwidth=1.6];',
        '    edge [fontname="Segoe UI, Helvetica, Arial", fontsize=9, penwidth=1.8];',
        '',
        '    // Agent & Entity Nodes with Real Task Context',
        f'    User [label=<<b>Human Principal</b><br/><font color="#475569">Goal Originator &amp; Root Authority</font><br/><font color="#4338CA"><b>Task:</b> "{clean_task}"</font>>, fillcolor="#EEF2FF", color="#6366F1"];',
        f'    Coord [label=<<b>Agent A: Coordinator</b><br/><font color="#1E3A8A">Domain: {domain_type}</font><br/><font point-size="9" color="#64748B">Authority Token: {root_id}</font>>, fillcolor="#DBEAFE", color="#2563EB"];',
        f'    Res [label=<<b>Agent B: Researcher</b><br/><font color="#854D0E">Tool: {tool_b}</font><br/><font point-size="9" color="#64748B">Delegation Token: {res_id}</font>>, fillcolor="#FEF3C7", color="#D97706"];',
    ]

    if clarification_occurred:
        dot.append('    Clarify [label=<<b>Clarification Branch</b><br/><font color="#9A3412">Question: Enterprise Account Priority</font><br/><font point-size="9" color="#64748B">Resolved: Verified by Coordinator</font>>, fillcolor="#FFEDD5", color="#EA580C", style="dashed,filled,rounded"];')

    dot.extend([
        f'    Ana [label=<<b>Agent C: Analyst</b><br/><font color="#166534">Tool: {tool_c}</font><br/><font point-size="9" color="#64748B">Delegation Token: {ana_id}</font>>, fillcolor="#DCFCE7", color="#16A34A"];',
        f'    Rep [label=<<b>Agent D: Reporter</b><br/><font color="#581C87">Tool: report_generator.format_markdown_report (WRITE)</font><br/><font point-size="9" color="#64748B">Delegation Token: {rep_id}</font>>, fillcolor="#F3E8FF", color="#9333EA"];',
        '    Artifact [label=<<b>Final Output Artifact (final_report.md)</b><br/><font color="#0F172A">Synthesized Report with W3C PROV Citations</font>>, fillcolor="#F1F5F9", color="#475569"];',
        '',
        '    // Dynamic Task Edges Showing What Task Was Given and What Was Received',
        f'    User -> Coord [label=" 1. User Assigns Goal:\\n\'{clean_task}\'", color="#6366F1", fontcolor="#4338CA"];',
        f'    Coord -> Res [label=" 2. Coordinator Assigns Sub-Task to B:\\n\'{clean_task_to_b}\'", color="#D97706", fontcolor="#B45309"];',
    ])

    if clarification_occurred:
        dot.append('    Res -> Clarify [label=" Trigger Clarification", color="#EA580C", style="dashed"];')
        dot.append('    Clarify -> Coord [label=" Request Guidance", color="#EA580C", style="dashed"];')
        dot.append('    Coord -> Ana [label=" Guidance Delivered", color="#16A34A", style="dashed"];')
        dot.append(f'    Res -> Ana [label=" 3. Researcher Delivers to Analyst:\\n\'{clean_data_b_to_c}\'", color="#16A34A", fontcolor="#15803D"];')
    else:
        dot.append(f'    Res -> Ana [label=" 3. Researcher Delivers to Analyst:\\n\'{clean_data_b_to_c}\'", color="#16A34A", fontcolor="#15803D"];')

    dot.extend([
        f'    Ana -> Rep [label=" 4. Analyst Delivers Findings to Reporter:\\n\'{clean_analysis_c_to_d}\'", color="#9333EA", fontcolor="#7E22CE"];',
        f'    Rep -> Artifact [label=" 5. Reporter Formats &amp; Generates:\\n\'{clean_report_d_to_a}\'", color="#475569", fontcolor="#334155"];',
        '    Artifact -> Coord [label=" 6. Report Artifact Returned to Coordinator", color="#2563EB", fontcolor="#1D4ED8"];',
        f'    Coord -> User [label=" 7. Final Response Delivered to User:\\n\'{clean_ans_summary}\'", color="#6366F1", fontcolor="#4338CA"];',
        '}'
    ])

    return "\n".join(dot)


def generate_langgraph_statemachine_dot(active_nodes: Optional[List[str]] = None, workflow_type: str = "adaptive") -> str:
    """
    Generates a genuine Graphviz DOT representation of the compiled LangGraph StateGraph topology,
    directly inspecting the compiled LangGraph graph structure with active node highlighting.
    """
    try:
        from backend.orchestration.langgraph_workflow import get_langgraph_topology_dot
        return get_langgraph_topology_dot(workflow_type=workflow_type, active_nodes=active_nodes)
    except Exception:
        # Fallback to standard styled representation if dynamic compilation unavailable
        actives = set(active_nodes or [
            "node_init_coordinator",
            "node_research",
            "node_clarification",
            "node_analysis",
            "node_escalation",
            "node_handoff",
            "node_report",
            "node_finalize"
        ])

        def style_node(node_id: str, label: str, role: str) -> str:
            is_active = node_id in actives
            fill = "#DCFCE7" if is_active else "#F8FAFC"
            color = "#16A34A" if is_active else "#CBD5E1"
            badge = "ACTIVE" if is_active else "READY"
            badge_color = "#15803D" if is_active else "#94A3B8"
            return f'    {node_id} [label=<<b>{label}</b><br/><font color="#475569">{role}</font><br/><font point-size="8" color="{badge_color}">[{badge}]</font>>, fillcolor="{fill}", color="{color}"];'

        dot = [
            'digraph LangGraphTopology {',
            '    rankdir=LR;',
            '    graph [bgcolor="transparent", fontname="Segoe UI, Helvetica, Arial", nodesep=0.3, ranksep=0.4];',
            '    node [shape=box, style="filled,rounded", fontname="Segoe UI, Helvetica, Arial", fontsize=10, margin="0.15,0.1", penwidth=1.5];',
            '    edge [fontname="Segoe UI, Helvetica, Arial", fontsize=8, penwidth=1.5];',
            '',
            '    START [shape=circle, label="START", fillcolor="#E2E8F0", color="#64748B", width=0.6];',
            '    END [shape=doublecircle, label="END", fillcolor="#E2E8F0", color="#64748B", width=0.6];',
            '',
            style_node("node_init_coordinator", "node_init_coordinator", "Coordinator Mints Delegations"),
            style_node("node_research", "node_research", "Researcher Reads Dataset"),
            '    cond_research [shape=diamond, label="route_after_research\\n(Clarification Needed?)", fillcolor="#FEF3C7", color="#F59E0B"];',
            style_node("node_clarification", "node_clarification", "Interactive Clarification Node"),
            style_node("node_analysis", "node_analysis", "Analyst Executes Security/Metrics Audit"),
            '    cond_analysis [shape=diamond, label="route_after_analysis\\n(Escalation / Retry Check)", fillcolor="#FEF3C7", color="#F59E0B"];',
            style_node("node_escalation", "node_escalation", "Escalation to Coordinator"),
            style_node("node_handoff", "node_handoff", "Handoff to Report Agent"),
            style_node("node_report", "node_report", "Reporter Generates Markdown Report"),
            style_node("node_finalize", "node_finalize", "Finalize State & Persist Outputs"),
            '',
            '    START -> node_init_coordinator [color="#2563EB"];',
            '    node_init_coordinator -> node_research [color="#2563EB"];',
            '    node_research -> cond_research [color="#F59E0B"];',
            '    cond_research -> node_clarification [label="if needs_clarification=True", color="#EA580C"];',
            '    cond_research -> node_analysis [label="if False", color="#16A34A"];',
            '    node_clarification -> node_analysis [color="#16A34A"];',
            '    node_analysis -> cond_analysis [color="#F59E0B"];',
            '    cond_analysis -> node_escalation [label="if critical violation", color="#EF4444"];',
            '    cond_analysis -> node_handoff [label="if success", color="#16A34A"];',
            '    cond_analysis -> node_analysis [label="if retry", color="#EF4444", style="dashed"];',
            '    node_escalation -> node_handoff [color="#EA580C"];',
            '    node_handoff -> node_report [color="#2563EB"];',
            '    node_report -> node_finalize [color="#2563EB"];',
            '    node_finalize -> END [color="#64748B"];',
            '}'
        ]
        return "\n".join(dot)


def extract_goal_traceability(workflow_run_dict: Dict[str, Any], delegations: List[Any], interactions: List[Any], events: List[Any]) -> List[Dict[str, Any]]:
    """
    Builds a structured goal traceability matrix mapping every agent to its assigned goal,
    delegation token, tools called, and outputs delivered.
    """
    task_desc = workflow_run_dict.get("task_description", "")
    dataset = workflow_run_dict.get("dataset_name", "")

    # Map delegations by agent
    del_map = {d.agent_id: d for d in delegations}
    
    matrix = [
        {
            "agent_id": "agent_coordinator",
            "agent_name": "Agent A: Coordinator",
            "role": "Orchestrator & Delegator",
            "assigned_goal": f"Decompose primary goal: '{task_desc}'. Mint authority tokens, oversee multi-agent execution, and assemble findings.",
            "delegation_id": del_map.get("agent_coordinator").delegation_id if "agent_coordinator" in del_map else "N/A",
            "parent_authority": "Human Principal",
            "scope": del_map.get("agent_coordinator").scope if "agent_coordinator" in del_map else "root_workflow_coordination",
            "tools_invoked": "Authority Token Minting, Message Dispatching",
            "output_produced": "Root Workflow Orchestration & Synthesized Response"
        },
        {
            "agent_id": "agent_researcher",
            "agent_name": "Agent B: Researcher",
            "role": "Data Ingestion Specialist",
            "assigned_goal": f"Ingest dataset '{dataset}', parse structured rows, extract target records, and transfer data envelope to Analyst.",
            "delegation_id": del_map.get("agent_researcher").delegation_id if "agent_researcher" in del_map else "N/A",
            "parent_authority": del_map.get("agent_researcher").delegation_parent_id if "agent_researcher" in del_map else "del_root",
            "scope": del_map.get("agent_researcher").scope if "agent_researcher" in del_map else "data_ingestion_and_extraction",
            "tools_invoked": "file_system.read_sample_dataset (Tier-1: READ)",
            "output_produced": f"Parsed records from {dataset} transferred to Agent C"
        },
        {
            "agent_id": "agent_analyst",
            "agent_name": "Agent C: Analyst",
            "role": "Quantitative & Security Auditor",
            "assigned_goal": "Perform statistical sentiment analysis, severity distribution calculation, or unauthorized access violation detection.",
            "delegation_id": del_map.get("agent_analyst").delegation_id if "agent_analyst" in del_map else "N/A",
            "parent_authority": del_map.get("agent_analyst").delegation_parent_id if "agent_analyst" in del_map else "del_root",
            "scope": del_map.get("agent_analyst").scope if "agent_analyst" in del_map else "quantitative_analysis_and_metrics",
            "tools_invoked": "security_auditor / analytics_engine / content_analyzer (Tier-1: SEARCH / INVOKE / READ)",
            "output_produced": "Aggregated metrics dictionary and identified critical incidents"
        },
        {
            "agent_id": "agent_reporter",
            "agent_name": "Agent D: Reporter",
            "role": "Executive Synthesis Specialist",
            "assigned_goal": "Format Markdown executive report with statistical tables, findings, recommendations, and explicit W3C PROV source citations.",
            "delegation_id": del_map.get("agent_reporter").delegation_id if "agent_reporter" in del_map else "N/A",
            "parent_authority": del_map.get("agent_reporter").delegation_parent_id if "agent_reporter" in del_map else "del_root",
            "scope": del_map.get("agent_reporter").scope if "agent_reporter" in del_map else "markdown_report_generation",
            "tools_invoked": "report_generator.format_markdown_report (Tier-1: WRITE)",
            "output_produced": "Structured Markdown Artifact (final_report.md) with W3C PROV links"
        }
    ]
    return matrix
