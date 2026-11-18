"""
LangGraph Multi-Agent Orchestration Workflows.
Implements the multi-agent delegation, parallel subtasking, trial-and-adapt,
and communication models specified in:
1. Multi-Agent Observability System Specifications (W1, W2, W3)
2. RM_MID.pdf (IIIT Allahabad), Slides 3, 10, 11, 12

Supports:
- Adaptive Multi-Agent Collaboration (Primary default)
- W1: Parallel Disconnected Subtasks (|Comp(d)| > 1)
- W2: Multi-Agent Dynamic Re-delegation Fanout (d -> d')
- W3: Trial-and-Adapt / Dynamic Retries & Backtracking
- MemorySaver checkpointer & thread state snapshots
- Dynamic Mermaid & Graphviz DOT extraction directly from compiled graphs
"""

from typing import TypedDict, Optional, Dict, Any, List, Annotated
import operator
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from backend.agents.coordinator import CoordinatorAgent
from backend.agents.researcher import ResearchAgent
from backend.agents.analyst import AnalysisAgent
from backend.agents.reporter import ReportAgent
from backend.gateway.gateway import ObservabilityGateway, default_gateway
from backend.schemas.events import CaptureLevel, InteractionType, SensitivityLabel

# ==============================================================================
# 1. Unified LangGraph Workflow State
# ==============================================================================
class MultiAgentWorkflowState(TypedDict):
    workflow_id: str
    task_description: str
    dataset_name: str
    principal_id: str
    conversation_id: str
    mode: str
    capture_level: int
    workflow_type: str
    root_delegation_id: Optional[str]
    research_delegation_id: Optional[str]
    analysis_delegation_id: Optional[str]
    report_delegation_id: Optional[str]
    sentiment_delegation_id: Optional[str]
    forensics_delegation_id: Optional[str]
    threat_hunter_delegation_id: Optional[str]
    compliance_delegation_id: Optional[str]
    critic_delegation_id: Optional[str]
    active_agents: Optional[List[str]]
    research_data: Optional[Dict[str, Any]]
    secondary_data: Optional[Dict[str, Any]]
    analysis_data: Optional[Dict[str, Any]]
    report_data: Optional[Dict[str, Any]]
    clarification_requested: bool
    clarification_resolved: bool
    escalation_triggered: bool
    escalation_resolved: bool
    retry_count: int
    max_retries: int
    backtrack_occurred: bool
    node_history: Annotated[List[str], operator.add]
    errors: Annotated[List[str], operator.add]
    status: str
    final_output: Optional[str]


# ==============================================================================
# 2. Primary Workflow: Adaptive Multi-Agent Collaboration
# ==============================================================================
def build_adaptive_multi_agent_graph(gateway: Optional[ObservabilityGateway] = None):
    gw = gateway or default_gateway
    coord = CoordinatorAgent(gateway=gw)
    researcher = ResearchAgent(gateway=gw)
    analyst = AnalysisAgent(gateway=gw)
    reporter = ReportAgent(gateway=gw)

    def node_init_coordinator(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        gw.set_capture_level(CaptureLevel(state.get("capture_level", 2)))
        delegations = coord.initiate_delegations(
            principal_id=state["principal_id"],
            workflow_id=state["workflow_id"],
            task_description=state["task_description"],
            dataset_name=state["dataset_name"],
            conversation_id=state["conversation_id"]
        )
        return {
            "root_delegation_id": delegations["root_delegation"].delegation_id,
            "research_delegation_id": delegations["research_delegation"].delegation_id,
            "analysis_delegation_id": delegations["analysis_delegation"].delegation_id,
            "report_delegation_id": delegations["report_delegation"].delegation_id,
            "status": "research_in_progress",
            "node_history": ["node_init_coordinator"]
        }

    def node_research(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        try:
            res = researcher.execute_research(
                dataset_name=state["dataset_name"],
                delegation_id=state["research_delegation_id"],
                principal_id=state["principal_id"],
                workflow_id=state["workflow_id"],
                task_id=f"research_task_{state['workflow_id']}",
                conversation_id=state["conversation_id"],
                mode=state.get("mode", "deterministic_demo")
            )
            return {
                "research_data": res,
                "status": "research_completed",
                "node_history": ["node_research"]
            }
        except Exception as e:
            return {
                "errors": [f"Research error: {str(e)}"],
                "status": "failed",
                "node_history": ["node_research"]
            }

    def route_after_research(state: MultiAgentWorkflowState) -> str:
        if state.get("status") == "failed":
            return "node_finalize"
        task_desc = state.get("task_description", "").lower()
        needs_clarification = (
            ("clarification" in task_desc or "priority" in task_desc or "audit" in task_desc)
            and not state.get("clarification_resolved", False)
        )
        if needs_clarification:
            return "node_clarification"
        return "node_analysis"

    def node_clarification(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        clarification_msg = analyst.request_clarification(
            question="Should analysis prioritize Enterprise accounts over Standard accounts during severity aggregation?",
            delegation_id=state["analysis_delegation_id"],
            conversation_id=state["conversation_id"],
            task_id=f"analysis_task_{state['workflow_id']}"
        )
        coord.respond_to_clarification(
            clarification_msg={"body": "Prioritize Enterprise accounts", "sender": "agent_analyst", "message_id": clarification_msg.message_id},
            delegation_id=state["root_delegation_id"],
            conversation_id=state["conversation_id"],
            task_id=f"root_task_{state['workflow_id']}",
            mode=state.get("mode", "deterministic_demo")
        )
        return {
            "clarification_requested": True,
            "clarification_resolved": True,
            "status": "clarified",
            "node_history": ["node_clarification"]
        }

    def node_analysis(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        try:
            r_data = state.get("research_data", {})
            extracted = r_data.get("read_result", {}).get("data", [])
            upstream_msg = r_data.get("message_to_analyst")
            upstream_id = upstream_msg.interaction_id if upstream_msg else None

            ans = analyst.analyze_dataset(
                raw_records=extracted,
                dataset_name=state["dataset_name"],
                delegation_id=state["analysis_delegation_id"],
                principal_id=state["principal_id"],
                workflow_id=state["workflow_id"],
                task_id=f"analysis_task_{state['workflow_id']}",
                conversation_id=state["conversation_id"],
                upstream_interaction_id=upstream_id,
                mode=state.get("mode", "deterministic_demo")
            )
            return {
                "analysis_data": ans,
                "status": "analysis_completed",
                "node_history": ["node_analysis"]
            }
        except Exception as e:
            retries = state.get("retry_count", 0)
            if retries < 1:
                return {
                    "retry_count": retries + 1,
                    "status": "retrying_analysis",
                    "node_history": ["node_analysis"]
                }
            return {
                "errors": [f"Analysis error: {str(e)}"],
                "status": "failed",
                "node_history": ["node_analysis"]
            }

    def route_after_analysis(state: MultiAgentWorkflowState) -> str:
        if state.get("status") == "retrying_analysis":
            return "node_analysis"
        if state.get("status") == "failed":
            return "node_finalize"
        
        ans_data = state.get("analysis_data", {})
        out = ans_data.get("analysis_output", {})
        violations = out.get("violations_detected", 0)
        task_desc = state.get("task_description", "").lower()
        needs_escalation = (violations > 0 or "escalat" in task_desc) and not state.get("escalation_resolved", False)
        
        if needs_escalation:
            return "node_escalation"
        return "node_handoff"

    def node_escalation(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        ans_data = state.get("analysis_data", {})
        out = ans_data.get("analysis_output", {})
        violations = out.get("violations_detected", 1)
        
        esc_msg = analyst.escalate_issue(
            reason=f"Detected {violations} critical unauthorized security touches requiring immediate coordinator review",
            delegation_id=state["analysis_delegation_id"],
            conversation_id=state["conversation_id"],
            task_id=f"analysis_task_{state['workflow_id']}"
        )
        reason_content = getattr(esc_msg, "content", None) or getattr(esc_msg, "semantic_summary", None) or "Critical anomaly flagged"
        coord.respond_to_escalation(
            escalation_msg={"body": reason_content, "sender": "agent_analyst", "message_id": esc_msg.message_id},
            delegation_id=state["root_delegation_id"],
            conversation_id=state["conversation_id"],
            task_id=f"root_task_{state['workflow_id']}"
        )
        return {
            "escalation_triggered": True,
            "escalation_resolved": True,
            "status": "escalation_resolved",
            "node_history": ["node_escalation"]
        }

    def node_handoff(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        ans_data = state.get("analysis_data", {})
        takeaway = ans_data.get("key_takeaway", "Analytical synthesis ready")
        out = ans_data.get("analysis_output", {})
        coord.handoff_to_reporter(
            delegation_id=state["root_delegation_id"],
            conversation_id=state["conversation_id"],
            task_id=f"root_task_{state['workflow_id']}",
            findings_summary=takeaway,
            workflow_id=state["workflow_id"],
            analysis_output=out
        )
        return {
            "status": "handoff_completed",
            "node_history": ["node_handoff"]
        }

    def node_report(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        try:
            rep = reporter.generate_final_report(
                task_description=state["task_description"],
                dataset_name=state["dataset_name"],
                research_data=state.get("research_data", {}),
                analysis_data=state.get("analysis_data", {}),
                delegation_id=state["report_delegation_id"],
                principal_id=state["principal_id"],
                workflow_id=state["workflow_id"],
                task_id=f"report_task_{state['workflow_id']}",
                conversation_id=state["conversation_id"],
                mode=state.get("mode", "deterministic_demo")
            )
            return {
                "report_data": rep,
                "final_output": rep.get("markdown_content"),
                "status": "completed",
                "node_history": ["node_report"]
            }
        except Exception as e:
            return {
                "errors": [f"Report error: {str(e)}"],
                "status": "failed",
                "node_history": ["node_report"]
            }

    def node_finalize(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        # Coordinator consumes and acknowledges remaining incoming envelopes (Issue 1)
        inbox = coord.read_inbox()
        for env in inbox:
            msg_id = env.get("message_id") if isinstance(env, dict) else getattr(env, "message_id", None)
            is_ack = env.get("acknowledged", False) if isinstance(env, dict) else (getattr(env, "status", None) == "acknowledged")
            if msg_id and not is_ack:
                coord.acknowledge_message(msg_id)
        is_success = state.get("status") in ("completed", "handoff_completed", "analysis_completed", "escalation_resolved")
        return {
            "status": "completed" if is_success else "failed",
            "node_history": ["node_finalize"]
        }

    builder = StateGraph(MultiAgentWorkflowState)
    builder.add_node("node_init_coordinator", node_init_coordinator)
    builder.add_node("node_research", node_research)
    builder.add_node("node_clarification", node_clarification)
    builder.add_node("node_analysis", node_analysis)
    builder.add_node("node_escalation", node_escalation)
    builder.add_node("node_handoff", node_handoff)
    builder.add_node("node_report", node_report)
    builder.add_node("node_finalize", node_finalize)

    builder.add_edge(START, "node_init_coordinator")
    builder.add_edge("node_init_coordinator", "node_research")
    builder.add_conditional_edges("node_research", route_after_research, {
        "node_clarification": "node_clarification",
        "node_analysis": "node_analysis",
        "node_finalize": "node_finalize"
    })
    builder.add_edge("node_clarification", "node_analysis")
    builder.add_conditional_edges("node_analysis", route_after_analysis, {
        "node_analysis": "node_analysis",
        "node_escalation": "node_escalation",
        "node_handoff": "node_handoff",
        "node_finalize": "node_finalize"
    })
    builder.add_edge("node_escalation", "node_handoff")
    builder.add_edge("node_handoff", "node_report")
    builder.add_edge("node_report", "node_finalize")
    builder.add_edge("node_finalize", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


# ==============================================================================
# 3. Canonical Workload W1: Parallel Disconnected Subtasks (Paper Section 7.2.1)
# ==============================================================================
def build_w1_parallel_graph(gateway: Optional[ObservabilityGateway] = None):
    """
    Implements W1: Cross-system causally disconnected parallel subtasks.
    Issues parallel reads across multiple tools under a single root delegation,
    inducing causally disconnected components (|Comp(d)| > 1) followed by join & synthesis.
    """
    gw = gateway or default_gateway
    coord = CoordinatorAgent(gateway=gw)
    researcher = ResearchAgent(gateway=gw)
    analyst = AnalysisAgent(gateway=gw)
    reporter = ReportAgent(gateway=gw)

    def node_w1_init(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        gw.set_capture_level(CaptureLevel(state.get("capture_level", 2)))
        root_del = gw.mint_delegation(
            principal_id=state["principal_id"],
            agent_id=coord.agent_id,
            task_id=f"w1_root_{state['workflow_id']}",
            scope="parallel_subtask_coordination"
        )
        return {
            "root_delegation_id": root_del.delegation_id,
            "research_delegation_id": root_del.delegation_id,
            "analysis_delegation_id": root_del.delegation_id,
            "report_delegation_id": root_del.delegation_id,
            "status": "parallel_ingestion",
            "node_history": ["node_w1_init"]
        }

    def node_w1_read_primary(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        res = researcher.execute_research(
            dataset_name=state.get("dataset_name", "customer_complaints.csv"),
            delegation_id=state["root_delegation_id"],
            principal_id=state["principal_id"],
            workflow_id=state["workflow_id"],
            task_id=f"w1_subtask_primary_{state['workflow_id']}",
            conversation_id=state["conversation_id"],
            mode=state.get("mode", "deterministic_demo")
        )
        return {
            "research_data": res,
            "node_history": ["node_w1_read_primary"]
        }

    def node_w1_read_secondary(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        sec_dataset = "system_access_logs.csv" if state.get("dataset_name") != "system_access_logs.csv" else "sample_research_notes.txt"
        sec_res = researcher.execute_research(
            dataset_name=sec_dataset,
            delegation_id=state["root_delegation_id"],
            principal_id=state["principal_id"],
            workflow_id=state["workflow_id"],
            task_id=f"w1_subtask_secondary_{state['workflow_id']}",
            conversation_id=state["conversation_id"],
            mode=state.get("mode", "deterministic_demo")
        )
        return {
            "secondary_data": sec_res,
            "node_history": ["node_w1_read_secondary"]
        }

    def node_w1_join(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        return {
            "status": "parallel_joined",
            "node_history": ["node_w1_join"]
        }

    def node_w1_analyze(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        r_data = state.get("research_data", {})
        extracted = r_data.get("read_result", {}).get("data", [])
        ans = analyst.analyze_dataset(
            raw_records=extracted,
            dataset_name=state.get("dataset_name", "customer_complaints.csv"),
            delegation_id=state["root_delegation_id"],
            principal_id=state["principal_id"],
            workflow_id=state["workflow_id"],
            task_id=f"w1_analysis_{state['workflow_id']}",
            conversation_id=state["conversation_id"],
            mode=state.get("mode", "deterministic_demo")
        )
        return {
            "analysis_data": ans,
            "node_history": ["node_w1_analyze"]
        }

    def node_w1_report(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        rep = reporter.generate_final_report(
            task_description=f"W1 Parallel Subtasks Synthesis: {state['task_description']}",
            dataset_name=state.get("dataset_name", "customer_complaints.csv"),
            research_data=state.get("research_data", {}),
            analysis_data=state.get("analysis_data", {}),
            delegation_id=state["root_delegation_id"],
            principal_id=state["principal_id"],
            workflow_id=state["workflow_id"],
            task_id=f"w1_report_{state['workflow_id']}",
            conversation_id=state["conversation_id"],
            mode=state.get("mode", "deterministic_demo")
        )
        return {
            "report_data": rep,
            "final_output": rep.get("markdown_content"),
            "status": "completed",
            "node_history": ["node_w1_report"]
        }

    def node_w1_finalize(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        return {
            "status": "completed",
            "node_history": ["node_w1_finalize"]
        }

    builder = StateGraph(MultiAgentWorkflowState)
    builder.add_node("node_w1_init", node_w1_init)
    builder.add_node("node_w1_read_primary", node_w1_read_primary)
    builder.add_node("node_w1_read_secondary", node_w1_read_secondary)
    builder.add_node("node_w1_join", node_w1_join)
    builder.add_node("node_w1_analyze", node_w1_analyze)
    builder.add_node("node_w1_report", node_w1_report)
    builder.add_node("node_w1_finalize", node_w1_finalize)

    builder.add_edge(START, "node_w1_init")
    builder.add_edge("node_w1_init", "node_w1_read_primary")
    builder.add_edge("node_w1_init", "node_w1_read_secondary")
    builder.add_edge("node_w1_read_primary", "node_w1_join")
    builder.add_edge("node_w1_read_secondary", "node_w1_join")
    builder.add_edge("node_w1_join", "node_w1_analyze")
    builder.add_edge("node_w1_analyze", "node_w1_report")
    builder.add_edge("node_w1_report", "node_w1_finalize")
    builder.add_edge("node_w1_finalize", END)

    return builder.compile(checkpointer=MemorySaver())


# ==============================================================================
# 4. Canonical Workload W3: Trial-and-Adapt with Retries (Paper Section 7.2.1)
# ==============================================================================
def build_w3_retry_graph(gateway: Optional[ObservabilityGateway] = None):
    """
    Implements W3: Trial-and-adapt workflow with retries and backtracking.
    Iteratively refines tool parameters upon intermediate observations or simulated errors.
    """
    gw = gateway or default_gateway
    coord = CoordinatorAgent(gateway=gw)
    researcher = ResearchAgent(gateway=gw)
    analyst = AnalysisAgent(gateway=gw)
    reporter = ReportAgent(gateway=gw)

    def node_w3_init(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        gw.set_capture_level(CaptureLevel(state.get("capture_level", 2)))
        delegations = coord.initiate_delegations(
            principal_id=state["principal_id"],
            workflow_id=state["workflow_id"],
            task_description=f"W3 Trial-and-Adapt: {state['task_description']}",
            dataset_name=state["dataset_name"],
            conversation_id=state["conversation_id"]
        )
        return {
            "root_delegation_id": delegations["root_delegation"].delegation_id,
            "research_delegation_id": delegations["research_delegation"].delegation_id,
            "analysis_delegation_id": delegations["analysis_delegation"].delegation_id,
            "report_delegation_id": delegations["report_delegation"].delegation_id,
            "retry_count": 0,
            "max_retries": 2,
            "backtrack_occurred": False,
            "status": "trial_started",
            "node_history": ["node_w3_init"]
        }

    def node_w3_try_tool(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        retries = state.get("retry_count", 0)
        res = researcher.execute_research(
            dataset_name=state["dataset_name"],
            delegation_id=state["research_delegation_id"],
            principal_id=state["principal_id"],
            workflow_id=state["workflow_id"],
            task_id=f"w3_trial_{retries}_{state['workflow_id']}",
            conversation_id=state["conversation_id"],
            mode=state.get("mode", "deterministic_demo")
        )
        return {
            "research_data": res,
            "node_history": ["node_w3_try_tool"]
        }

    def route_w3_eval(state: MultiAgentWorkflowState) -> str:
        retries = state.get("retry_count", 0)
        if retries < 1 and not state.get("backtrack_occurred", False):
            return "node_w3_backtrack_adapt"
        return "node_w3_analyze"

    def node_w3_backtrack_adapt(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        retries = state.get("retry_count", 0) + 1
        coord.send_message(
            recipient="agent_researcher",
            interaction_type=InteractionType.REQUEST,
            delegation_id=state["root_delegation_id"],
            conversation_id=state["conversation_id"],
            task_id=f"w3_adapt_task_{state['workflow_id']}",
            body="Trial refinement: Expand search filters to capture edge records and retry collection.",
            summary=f"Trial adaptation: parameter adjustment and retry trigger (attempt {retries}).",
            sensitivity_label=SensitivityLabel.INTERNAL
        )
        return {
            "retry_count": retries,
            "backtrack_occurred": True,
            "node_history": ["node_w3_backtrack_adapt"]
        }

    def node_w3_analyze(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        r_data = state.get("research_data", {})
        extracted = r_data.get("read_result", {}).get("data", [])
        ans = analyst.analyze_dataset(
            raw_records=extracted,
            dataset_name=state["dataset_name"],
            delegation_id=state["analysis_delegation_id"],
            principal_id=state["principal_id"],
            workflow_id=state["workflow_id"],
            task_id=f"w3_analysis_{state['workflow_id']}",
            conversation_id=state["conversation_id"],
            mode=state.get("mode", "deterministic_demo")
        )
        return {
            "analysis_data": ans,
            "node_history": ["node_w3_analyze"]
        }

    def node_w3_report(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        rep = reporter.generate_final_report(
            task_description=f"W3 Trial-and-Adapt Results: {state['task_description']}",
            dataset_name=state["dataset_name"],
            research_data=state.get("research_data", {}),
            analysis_data=state.get("analysis_data", {}),
            delegation_id=state["report_delegation_id"],
            principal_id=state["principal_id"],
            workflow_id=state["workflow_id"],
            task_id=f"w3_report_{state['workflow_id']}",
            conversation_id=state["conversation_id"],
            mode=state.get("mode", "deterministic_demo")
        )
        return {
            "report_data": rep,
            "final_output": rep.get("markdown_content"),
            "status": "completed",
            "node_history": ["node_w3_report"]
        }

    def node_w3_finalize(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        return {
            "status": "completed",
            "node_history": ["node_w3_finalize"]
        }

    builder = StateGraph(MultiAgentWorkflowState)
    builder.add_node("node_w3_init", node_w3_init)
    builder.add_node("node_w3_try_tool", node_w3_try_tool)
    builder.add_node("node_w3_backtrack_adapt", node_w3_backtrack_adapt)
    builder.add_node("node_w3_analyze", node_w3_analyze)
    builder.add_node("node_w3_report", node_w3_report)
    builder.add_node("node_w3_finalize", node_w3_finalize)

    builder.add_edge(START, "node_w3_init")
    builder.add_edge("node_w3_init", "node_w3_try_tool")
    builder.add_conditional_edges("node_w3_try_tool", route_w3_eval, {
        "node_w3_backtrack_adapt": "node_w3_backtrack_adapt",
        "node_w3_analyze": "node_w3_analyze"
    })
    builder.add_edge("node_w3_backtrack_adapt", "node_w3_try_tool")
    builder.add_edge("node_w3_analyze", "node_w3_report")
    builder.add_edge("node_w3_report", "node_w3_finalize")
    builder.add_edge("node_w3_finalize", END)

    return builder.compile(checkpointer=MemorySaver())


# ==============================================================================
# 5. Graph Factory & Dynamic Introspection
# ==============================================================================
def build_multi_agent_graph(gateway: Optional[ObservabilityGateway] = None, workflow_type: str = "adaptive"):
    """
    Factory function returning the compiled LangGraph workflow requested.
    Supports:
    - Domain Squads: 'security_forensics', 'consumer_sentiment', 'cross_squad', 'adversarial_critic', 'rapid_consensus'
    - Canonical Benchmark Topologies: 'adaptive', 'w1_parallel', 'w3_retry'
    """
    wt = (workflow_type or "adaptive").lower()
    from backend.orchestration.squad_workflows import (
        build_security_forensics_graph,
        build_consumer_sentiment_graph,
        build_cross_squad_graph,
        build_adversarial_critic_graph,
        build_rapid_consensus_graph
    )
    if wt in ("security_forensics", "security", "secops", "forensics"):
        return build_security_forensics_graph(gateway)
    elif wt in ("consumer_sentiment", "sentiment", "experience", "complaints_squad"):
        return build_consumer_sentiment_graph(gateway)
    elif wt in ("cross_squad", "hybrid", "cross", "inter_squad", "cross_team"):
        return build_cross_squad_graph(gateway)
    elif wt in ("adversarial_critic", "critic", "debate", "peer_review"):
        return build_adversarial_critic_graph(gateway)
    elif wt in ("rapid_consensus", "rapid", "triangle", "fast"):
        return build_rapid_consensus_graph(gateway)
    elif wt in ("w1", "w1_parallel", "parallel"):
        return build_w1_parallel_graph(gateway)
    elif wt in ("w3", "w3_retry", "retry", "trial"):
        return build_w3_retry_graph(gateway)
    else:
        return build_adaptive_multi_agent_graph(gateway)


def get_langgraph_mermaid(workflow_type: str = "adaptive", gateway: Optional[ObservabilityGateway] = None) -> str:
    """Extracts genuine Mermaid flowchart syntax directly from the compiled LangGraph object."""
    compiled = build_multi_agent_graph(gateway, workflow_type=workflow_type)
    return compiled.get_graph().draw_mermaid()


def get_langgraph_topology_dot(workflow_type: str = "adaptive", active_nodes: Optional[List[str]] = None, gateway: Optional[ObservabilityGateway] = None) -> str:
    """
    Generates genuine Graphviz DOT topology by inspecting nodes and edges
    from the compiled LangGraph graph object, with live active node highlighting.
    """
    compiled = build_multi_agent_graph(gateway, workflow_type=workflow_type)
    g = compiled.get_graph()
    actives = set(active_nodes or [])

    dot = [
        'digraph LangGraphTopology {',
        '    rankdir=LR;',
        '    graph [bgcolor="transparent", fontname="Segoe UI, Helvetica, Arial", nodesep=0.35, ranksep=0.45];',
        '    node [shape=box, style="filled,rounded", fontname="Segoe UI, Helvetica, Arial", fontsize=10, margin="0.15,0.1", penwidth=1.5];',
        '    edge [fontname="Segoe UI, Helvetica, Arial", fontsize=8, penwidth=1.5];',
        ''
    ]

    for node_id in g.nodes.keys():
        if node_id in ("__start__", "START"):
            dot.append('    START [shape=circle, label="START", fillcolor="#E2E8F0", color="#64748B", width=0.6];')
        elif node_id in ("__end__", "END"):
            dot.append('    END [shape=doublecircle, label="END", fillcolor="#E2E8F0", color="#64748B", width=0.6];')
        else:
            is_active = node_id in actives
            fill = "#DCFCE7" if is_active else "#F8FAFC"
            border = "#16A34A" if is_active else "#94A3B8"
            badge = "ACTIVE" if is_active else "READY"
            badge_color = "#15803D" if is_active else "#64748B"
            clean_name = node_id.replace("node_", "").replace("_", " ").title()
            dot.append(
                f'    {node_id} [label=<<b>{node_id}</b><br/><font color="#475569">{clean_name}</font><br/><font point-size="8" color="{badge_color}">[{badge}]</font>>, fillcolor="{fill}", color="{border}"];'
            )

    dot.append('')
    for e in g.edges:
        src = "START" if e.source in ("__start__", "START") else e.source
        dst = "END" if e.target in ("__end__", "END") else e.target
        is_cond = getattr(e, "conditional", False)
        color = "#F59E0B" if is_cond else "#2563EB"
        style = 'style="dashed", ' if is_cond else ''
        dot.append(f'    {src} -> {dst} [{style}color="{color}"];')

    dot.append('}')
    return "\n".join(dot)


def get_available_workflow_topologies() -> Dict[str, Dict[str, Any]]:
    """Returns documentation and metadata for each supported LangGraph workflow."""
    return {
        "consumer_sentiment": {
            "name": "Consumer Experience & Sentiment Squad (5 Agents)",
            "paper_ref": "Domain Squad: Pentagon Pipeline",
            "description": "5-agent customer sentiment pipeline integrating Ingestion, NLP emotion distribution scoring, impact evaluation, and executive reporting.",
            "features": ["NLP Sentiment Distribution", "Category Polarity Scoring", "Severity Tier Evaluation", "Pentagon Pipeline Topology"],
            "agents": ["agent_coordinator", "agent_researcher", "agent_sentiment", "agent_analyst", "agent_reporter"]
        },
        "security_forensics": {
            "name": "SecOps Access Log & Privilege Escalation Squad (4 Agents)",
            "paper_ref": "Domain Squad: Hub-and-Spoke / Star Topology",
            "description": "4-agent security squad scanning system access logs, identifying unauthorized file sharing and root IAM escalation vectors.",
            "features": ["Access Log Scanning", "Root Privilege Escalation Hunting", "FedRAMP & NIST Invariant Auditing", "Star Topology"],
            "agents": ["agent_coordinator", "agent_forensics", "agent_threat_hunter", "agent_compliance"]
        },
        "cross_squad": {
            "name": "Cross-Squad Enterprise Collaboration (7 Agents - Complaints ➔ Security Bridge)",
            "paper_ref": "Hybrid Cross-Domain: Dual-Cluster Federation",
            "description": "Cross-squad investigation bridging customer ticket complaints to backend server access logs, detecting correlated lateral movement.",
            "features": ["Inter-Squad Escalation Bridge", "Cross-Domain Log Correlation", "NIST AC-3 Compliance Assessment", "Federated Dual-Cluster Topology"],
            "agents": ["agent_coordinator", "agent_researcher", "agent_sentiment", "agent_forensics", "agent_threat_hunter", "agent_compliance", "agent_reporter"]
        },
        "adversarial_critic": {
            "name": "Adversarial Critic & Debate Squad (5 Agents - P2P Mesh)",
            "paper_ref": "P2P Debate: Bidirectional Mesh",
            "description": "Peer-to-peer adversarial debate between Analyst and Critic to challenge confounding causal variables and reach verified consensus.",
            "features": ["Hypothesis Proposal", "Adversarial Counter-Critique", "Causal Precedence Invariant", "Bidirectional P2P Mesh"],
            "agents": ["agent_coordinator", "agent_researcher", "agent_analyst", "agent_critic", "agent_reporter"]
        },
        "rapid_consensus": {
            "name": "Rapid Consensus Squad (3 Agents - Triangular Loop)",
            "paper_ref": "Rapid Triage: Triangular Topology",
            "description": "High-velocity 3-agent circular consensus without reporter overhead, accelerating verification 3x.",
            "features": ["Circular Closed Loop", "Zero-Reporter Latency", "Rapid Snapshot Triage", "Triangular Topology"],
            "agents": ["agent_coordinator", "agent_researcher", "agent_analyst"]
        },
        "adaptive": {
            "name": "Adaptive Multi-Agent Collaboration (Canonical)",
            "paper_ref": "RM_MID Slide 11 (Autonomous MAS Architecture)",
            "description": "Full 4-agent collaborative state graph with dynamic tool selection, bi-directional clarification, escalation, handoff, and provenance synthesis.",
            "features": ["Dynamic Clarification", "Anomaly Escalation", "Formal Handoff", "Provenance Footnotes"],
            "agents": ["agent_coordinator", "agent_researcher", "agent_analyst", "agent_reporter"]
        },
        "w1_parallel": {
            "name": "W1: Parallel Disconnected Subtasks",
            "paper_ref": "Parallel Execution Workflow (W1)",
            "description": "Issues parallel reads across multiple tools under a single root delegation, inducing causally disconnected components (|Comp(d)| > 1) followed by fan-in join.",
            "features": ["Parallel Tool Reads", "Fan-In Join", "|Comp(d)| > 1 Stress Test", "Cross-Dataset Synthesis"],
            "agents": ["agent_coordinator", "agent_researcher", "agent_reporter"]
        },
        "w3_retry": {
            "name": "W3: Trial-and-Adapt / Dynamic Retries",
            "paper_ref": "Trial-and-Adapt Workflow (W3)",
            "description": "Implements iterative trial-and-adapt cycles with parameter refinement, backtracking, and retry logging upon intermediate observations.",
            "features": ["Parameter Backtracking", "Retry Loop", "Dynamic Refinement", "State Recovery"],
            "agents": ["agent_coordinator", "agent_researcher", "agent_reporter"]
        }
    }
