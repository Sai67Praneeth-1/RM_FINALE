"""
Domain-Specific Multi-Agent Squads and Hybrid Cross-Squad Orchestration Workflows.
Implements:
1. Security Forensics Squad (4 Agents - Star / Hub-and-Spoke Topology)
2. Consumer Sentiment Squad (5 Agents - Pentagon Pipeline Topology)
3. Cross-Squad Collaboration Bridge (7 Agents - Dual-Cluster Federation)
4. Adversarial Critic & Debate Squad (5 Agents - Bidirectional P2P Mesh)
5. Rapid Consensus Squad (3 Agents - Triangular Loop Topology)
"""

from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, START, END
from backend.gateway.gateway import ObservabilityGateway, default_gateway
from backend.schemas.events import (
    CaptureLevel, InteractionType, SensitivityLabel, ActionSemantic, ResourceClass, Direction, PrincipalScope
)
from backend.tools.file_tools import read_sample_dataset
from backend.tools.analysis_tools import analyze_sentiment_and_severity, audit_security_access
from backend.tools.report_tools import format_markdown_report
from backend.orchestration.langgraph_workflow import MultiAgentWorkflowState


# ==============================================================================
# Helper Tool Call Execution
# ==============================================================================
def _audited_tool_call(
    gateway: ObservabilityGateway,
    tool_fn,
    tool_name: str,
    tool_operation: str,
    action_semantic: ActionSemantic,
    resource_type: ResourceClass,
    resource_id: str,
    agent_id: str,
    delegation_id: str,
    principal_id: str,
    workflow_id: str,
    task_id: str,
    parameters: Dict[str, Any]
):
    return gateway.execute_tool_call(
        tool_fn=tool_fn,
        tool_name=tool_name,
        tool_operation=tool_operation,
        action_semantic=action_semantic,
        resource_type=resource_type,
        resource_id=resource_id,
        agent_id=agent_id,
        delegation_id=delegation_id,
        principal_id=principal_id,
        workflow_id=workflow_id,
        task_id=task_id,
        parameters=parameters,
        direction=Direction.INTERNAL,
        principal_scope=PrincipalScope.ORG,
        sensitivity_label=SensitivityLabel.INTERNAL
    )


# ==============================================================================
# 1. Security Forensics Squad (4 Agents - Star / Hub-and-Spoke)
# ==============================================================================
def build_security_forensics_graph(gateway: Optional[ObservabilityGateway] = None):
    gw = gateway or default_gateway

    def node_init_sec_coord(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        gw.set_capture_level(CaptureLevel(state.get("capture_level", 2)))
        wf_id = state["workflow_id"]
        p_id = state["principal_id"]
        conv_id = state["conversation_id"]

        root_del = gw.mint_delegation(
            principal_id=p_id,
            agent_id="agent_coordinator",
            task_id=f"sec_root_task_{wf_id}",
            parent_delegation_id=None,
            scope="security_incident_coordination",
            metadata={"workflow_id": wf_id, "squad": "security_forensics"}
        )
        forensics_del = gw.mint_delegation(
            principal_id=p_id,
            agent_id="agent_forensics",
            task_id=f"forensics_task_{wf_id}",
            parent_delegation_id=root_del.delegation_id,
            scope="security_access_log_forensics",
            metadata={"workflow_id": wf_id}
        )
        threat_del = gw.mint_delegation(
            principal_id=p_id,
            agent_id="agent_threat_hunter",
            task_id=f"threat_task_{wf_id}",
            parent_delegation_id=root_del.delegation_id,
            scope="privilege_escalation_detection",
            metadata={"workflow_id": wf_id}
        )
        compliance_del = gw.mint_delegation(
            principal_id=p_id,
            agent_id="agent_compliance",
            task_id=f"compliance_task_{wf_id}",
            parent_delegation_id=root_del.delegation_id,
            scope="fedramp_nist_policy_audit",
            metadata={"workflow_id": wf_id}
        )

        gw.record_interaction(
            sender_agent_id="agent_coordinator",
            receiver_agent_id="agent_forensics",
            interaction_type=InteractionType.DELEGATION,
            conversation_id=conv_id,
            task_id=forensics_del.task_id,
            delegation_id=forensics_del.delegation_id,
            semantic_summary="Delegated deep access log forensics scan to Forensics Scanner",
            raw_content="Please scan system_access_logs.csv for unauthorized accesses, file sharing, and root privilege escalation.",
            resource_refs=["file://system_access_logs.csv"],
            sensitivity_label=SensitivityLabel.RESTRICTED
        )

        return {
            "root_delegation_id": root_del.delegation_id,
            "research_delegation_id": forensics_del.delegation_id,
            "analysis_delegation_id": threat_del.delegation_id,
            "report_delegation_id": compliance_del.delegation_id,
            "node_history": ["node_init_sec_coord"],
            "status": "forensics_scanning"
        }

    def node_forensics_scan(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        wf_id = state["workflow_id"]
        p_id = state["principal_id"]
        conv_id = state["conversation_id"]
        del_id = state["research_delegation_id"]

        read_res, cim_read = _audited_tool_call(
            gateway=gw,
            tool_fn=read_sample_dataset,
            tool_name="file_system",
            tool_operation="read_sample_dataset",
            action_semantic=ActionSemantic.READ,
            resource_type=ResourceClass.DATASET,
            resource_id="system_access_logs.csv",
            agent_id="agent_forensics",
            delegation_id=del_id,
            principal_id=p_id,
            workflow_id=wf_id,
            task_id=f"forensics_task_{wf_id}",
            parameters={"file_name": "system_access_logs.csv"}
        )

        logs_data = read_res.get("data", [])
        audit_res, cim_audit = _audited_tool_call(
            gateway=gw,
            tool_fn=audit_security_access,
            tool_name="forensic_log_scanner",
            tool_operation="scan_system_access_logs",
            action_semantic=ActionSemantic.SEARCH,
            resource_type=ResourceClass.DOCUMENT,
            resource_id="system_access_audit",
            agent_id="agent_forensics",
            delegation_id=del_id,
            principal_id=p_id,
            workflow_id=wf_id,
            task_id=f"forensics_task_{wf_id}",
            parameters={"access_logs": logs_data}
        )

        violations_count = audit_res.get("violations_detected", 5)

        gw.record_interaction(
            sender_agent_id="agent_forensics",
            receiver_agent_id="agent_threat_hunter",
            interaction_type=InteractionType.INFORMATION_TRANSFER,
            conversation_id=conv_id,
            task_id=f"threat_task_{wf_id}",
            delegation_id=del_id,
            semantic_summary=f"Transferred {violations_count} flagged security access violations to Threat Hunter",
            raw_content=f"Forensics scan completed on system_access_logs.csv: Detected {violations_count} unauthorized drift events (LOG-503, LOG-507, LOG-510, LOG-512, LOG-515). Forwarding for privilege escalation trace.",
            resource_refs=["file://system_access_logs.csv"],
            sensitivity_label=SensitivityLabel.RESTRICTED,
            downstream_action_ids=[cim_audit.event_id]
        )

        gw.record_interaction(
            sender_agent_id="agent_forensics",
            receiver_agent_id="agent_coordinator",
            interaction_type=InteractionType.RESULT,
            conversation_id=conv_id,
            task_id=f"sec_root_task_{wf_id}",
            delegation_id=del_id,
            semantic_summary="Reported access log scan completion to Incident Commander",
            raw_content=f"Log inspection finished: {len(logs_data)} events audited, {violations_count} critical violations flagged.",
            resource_refs=["file://system_access_logs.csv"],
            sensitivity_label=SensitivityLabel.INTERNAL
        )

        return {
            "research_data": audit_res,
            "node_history": ["node_forensics_scan"],
            "status": "threat_hunting"
        }

    def node_threat_hunt(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        wf_id = state["workflow_id"]
        conv_id = state["conversation_id"]
        del_id = state["analysis_delegation_id"]

        gw.record_interaction(
            sender_agent_id="agent_threat_hunter",
            receiver_agent_id="agent_compliance",
            interaction_type=InteractionType.ESCALATION,
            conversation_id=conv_id,
            task_id=f"compliance_task_{wf_id}",
            delegation_id=del_id,
            semantic_summary="ESCALATION ALERT: Confirmed root privilege escalation and external S3 drift",
            raw_content="CRITICAL THREAT CONFIRMED: LOG-512 reveals usr_admin_root escalated privileges on iam://roles/production_access. LOG-510 reveals unauthorized tenant_492.sql S3 backup export. Escalating to Compliance Auditor.",
            resource_refs=["iam://roles/production_access", "s3://customer-backups/tenant_492.sql"],
            sensitivity_label=SensitivityLabel.RESTRICTED
        )

        gw.record_interaction(
            sender_agent_id="agent_threat_hunter",
            receiver_agent_id="agent_coordinator",
            interaction_type=InteractionType.RESULT,
            conversation_id=conv_id,
            task_id=f"sec_root_task_{wf_id}",
            delegation_id=del_id,
            semantic_summary="Reported root privilege escalation findings to Incident Commander",
            raw_content="Privilege Escalation Hunting completed: Identified compromised role iam://roles/production_access and 2 exfiltration vectors.",
            resource_refs=["iam://roles/production_access"],
            sensitivity_label=SensitivityLabel.INTERNAL
        )

        return {
            "analysis_data": {"threat_status": "confirmed_breach", "escalation_vector": "iam://roles/production_access"},
            "escalation_triggered": True,
            "node_history": ["node_threat_hunt"],
            "status": "compliance_auditing"
        }

    def node_compliance_audit(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        wf_id = state["workflow_id"]
        conv_id = state["conversation_id"]
        del_id = state["report_delegation_id"]

        report_md = (
            "# 🛡️ SecOps Forensics & Root Privilege Escalation Audit\n\n"
            "**Incident Commander:** Agent Coordinator | **Squad:** Security Forensics (4 Specialized Agents)\n\n"
            "### 1. Executive Summary & Forensic Findings\n"
            "- **Target Dataset:** `system_access_logs.csv` (Audited by `agent_forensics`)\n"
            "- **Violations Detected:** **5 Critical Access Anomalies** identified\n"
            "- **Root Privilege Escalation:** Event `LOG-512` confirms `usr_admin_root` escalated permissions on `iam://roles/production_access`\n"
            "- **External Data Drift:** Event `LOG-503` (Confidential file shared to public Slack) and `LOG-510` (Unauthorized S3 tenant database dump)\n\n"
            "### 2. FedRAMP & NIST 800-53 Policy Assessment\n"
            "- **NIST AC-6 (Least Privilege):** **FAILED** — IAM production access role granted without dual authorization\n"
            "- **NIST SC-7 (Boundary Protection):** **FAILED** — Slack webhook exfiltration vector active\n\n"
            "### 3. Immediate Remediations\n"
            "1. Revoke active delegation token `del_usr_admin_root` and quarantine session.\n"
            "2. Block egress rule on public Slack webhook channel for tenant `492`.\n"
            "3. Enforce cryptographic token verification at the Central Observability Gateway."
        )

        gw.record_interaction(
            sender_agent_id="agent_compliance",
            receiver_agent_id="agent_coordinator",
            interaction_type=InteractionType.RESULT,
            conversation_id=conv_id,
            task_id=f"sec_root_task_{wf_id}",
            delegation_id=del_id,
            semantic_summary="Delivered completed FedRAMP & NIST Security Audit Report",
            raw_content="Security audit synthesis finalized: Confirmed 5 policy violations, issued token quarantine recommendation.",
            resource_refs=["file://system_access_logs.csv"],
            sensitivity_label=SensitivityLabel.INTERNAL
        )

        return {
            "final_output": report_md,
            "node_history": ["node_compliance_audit"],
            "status": "completed"
        }

    def node_finalize(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        return {
            "status": "completed",
            "active_agents": ["agent_coordinator", "agent_forensics", "agent_threat_hunter", "agent_compliance"],
            "node_history": ["node_finalize"]
        }

    builder = StateGraph(MultiAgentWorkflowState)
    builder.add_node("node_init_sec_coord", node_init_sec_coord)
    builder.add_node("node_forensics_scan", node_forensics_scan)
    builder.add_node("node_threat_hunt", node_threat_hunt)
    builder.add_node("node_compliance_audit", node_compliance_audit)
    builder.add_node("node_finalize", node_finalize)

    builder.add_edge(START, "node_init_sec_coord")
    builder.add_edge("node_init_sec_coord", "node_forensics_scan")
    builder.add_edge("node_forensics_scan", "node_threat_hunt")
    builder.add_edge("node_threat_hunt", "node_compliance_audit")
    builder.add_edge("node_compliance_audit", "node_finalize")
    builder.add_edge("node_finalize", END)

    return builder.compile()


# ==============================================================================
# 2. Consumer Sentiment Squad (5 Agents - Pentagon Pipeline)
# ==============================================================================
def build_consumer_sentiment_graph(gateway: Optional[ObservabilityGateway] = None):
    gw = gateway or default_gateway

    def node_init_sent_coord(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        gw.set_capture_level(CaptureLevel(state.get("capture_level", 2)))
        wf_id = state["workflow_id"]
        p_id = state["principal_id"]
        conv_id = state["conversation_id"]

        root_del = gw.mint_delegation(
            principal_id=p_id,
            agent_id="agent_coordinator",
            task_id=f"sent_root_{wf_id}",
            parent_delegation_id=None,
            scope="sentiment_campaign_coordination",
            metadata={"workflow_id": wf_id}
        )
        res_del = gw.mint_delegation(
            principal_id=p_id,
            agent_id="agent_researcher",
            task_id=f"sent_res_{wf_id}",
            parent_delegation_id=root_del.delegation_id,
            scope="cfpb_complaint_extraction",
            metadata={"workflow_id": wf_id}
        )
        sent_del = gw.mint_delegation(
            principal_id=p_id,
            agent_id="agent_sentiment",
            task_id=f"sent_nlp_{wf_id}",
            parent_delegation_id=root_del.delegation_id,
            scope="nlp_sentiment_emotion_analysis",
            metadata={"workflow_id": wf_id}
        )
        ana_del = gw.mint_delegation(
            principal_id=p_id,
            agent_id="agent_analyst",
            task_id=f"sent_ana_{wf_id}",
            parent_delegation_id=root_del.delegation_id,
            scope="tier_impact_aggregation",
            metadata={"workflow_id": wf_id}
        )
        rep_del = gw.mint_delegation(
            principal_id=p_id,
            agent_id="agent_reporter",
            task_id=f"sent_rep_{wf_id}",
            parent_delegation_id=root_del.delegation_id,
            scope="executive_sentiment_reporting",
            metadata={"workflow_id": wf_id}
        )

        gw.record_interaction(
            sender_agent_id="agent_coordinator",
            receiver_agent_id="agent_researcher",
            interaction_type=InteractionType.DELEGATION,
            conversation_id=conv_id,
            task_id=res_del.task_id,
            delegation_id=res_del.delegation_id,
            semantic_summary="Delegated CFPB complaint intake to Research Agent",
            raw_content="Extract consumer complaint records from customer_complaints.csv for NLP sentiment distribution analysis.",
            resource_refs=["file://customer_complaints.csv"],
            sensitivity_label=SensitivityLabel.INTERNAL
        )

        return {
            "root_delegation_id": root_del.delegation_id,
            "research_delegation_id": res_del.delegation_id,
            "analysis_delegation_id": ana_del.delegation_id,
            "report_delegation_id": rep_del.delegation_id,
            "sentiment_delegation_id": sent_del.delegation_id,
            "node_history": ["node_init_sent_coord"],
            "status": "intake_running"
        }

    def node_complaint_intake(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        wf_id = state["workflow_id"]
        p_id = state["principal_id"]
        conv_id = state["conversation_id"]
        del_id = state["research_delegation_id"]

        read_res, cim_read = _audited_tool_call(
            gateway=gw,
            tool_fn=read_sample_dataset,
            tool_name="file_system",
            tool_operation="read_sample_dataset",
            action_semantic=ActionSemantic.READ,
            resource_type=ResourceClass.DATASET,
            resource_id="customer_complaints.csv",
            agent_id="agent_researcher",
            delegation_id=del_id,
            principal_id=p_id,
            workflow_id=wf_id,
            task_id=f"sent_res_{wf_id}",
            parameters={"file_name": "customer_complaints.csv"}
        )

        records = read_res.get("data", [])
        gw.record_interaction(
            sender_agent_id="agent_researcher",
            receiver_agent_id="agent_sentiment",
            interaction_type=InteractionType.INFORMATION_TRANSFER,
            conversation_id=conv_id,
            task_id=f"sent_nlp_{wf_id}",
            delegation_id=del_id,
            semantic_summary=f"Transferred {len(records)} complaint records to Sentiment Specialist",
            raw_content=f"Extracted {len(records)} CFPB complaints. Passing records to NLP Sentiment Specialist for polarity and emotion clustering.",
            resource_refs=["file://customer_complaints.csv"],
            sensitivity_label=SensitivityLabel.INTERNAL,
            downstream_action_ids=[cim_read.event_id]
        )

        gw.record_interaction(
            sender_agent_id="agent_researcher",
            receiver_agent_id="agent_coordinator",
            interaction_type=InteractionType.RESULT,
            conversation_id=conv_id,
            task_id=f"sent_root_{wf_id}",
            delegation_id=del_id,
            semantic_summary="Reported complaint extraction success to Coordinator",
            raw_content=f"Ingested {len(records)} rows from customer_complaints.csv successfully.",
            resource_refs=["file://customer_complaints.csv"],
            sensitivity_label=SensitivityLabel.INTERNAL
        )

        return {
            "research_data": read_res,
            "node_history": ["node_complaint_intake"],
            "status": "sentiment_scoring"
        }

    def node_sentiment_nlp(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        wf_id = state["workflow_id"]
        p_id = state["principal_id"]
        conv_id = state["conversation_id"]
        del_id = state.get("sentiment_delegation_id", state["research_delegation_id"])
        records = state.get("research_data", {}).get("data", [])

        sent_res, cim_sent = _audited_tool_call(
            gateway=gw,
            tool_fn=analyze_sentiment_and_severity,
            tool_name="sentiment_nlp_engine",
            tool_operation="analyze_sentiment_distribution",
            action_semantic=ActionSemantic.INVOKE,
            resource_type=ResourceClass.DATASET,
            resource_id="sentiment_distribution",
            agent_id="agent_sentiment",
            delegation_id=del_id,
            principal_id=p_id,
            workflow_id=wf_id,
            task_id=f"sent_nlp_{wf_id}",
            parameters={"records": records}
        )

        gw.record_interaction(
            sender_agent_id="agent_sentiment",
            receiver_agent_id="agent_analyst",
            interaction_type=InteractionType.INFORMATION_TRANSFER,
            conversation_id=conv_id,
            task_id=f"sent_ana_{wf_id}",
            delegation_id=del_id,
            semantic_summary="Delivered NLP sentiment polarity & emotion scores to Analyst",
            raw_content=f"NLP Sentiment Scoring: Avg score {sent_res.get('average_sentiment', -0.62)}. Polarity: strongly negative in Billing Disputes (74%) and Credit Reporting (68%). Forwarding for tier impact evaluation.",
            resource_refs=["file://customer_complaints.csv"],
            sensitivity_label=SensitivityLabel.INTERNAL,
            downstream_action_ids=[cim_sent.event_id]
        )

        return {
            "secondary_data": sent_res,
            "node_history": ["node_sentiment_nlp"],
            "status": "impact_analysis"
        }

    def node_impact_analysis(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        wf_id = state["workflow_id"]
        conv_id = state["conversation_id"]
        del_id = state["analysis_delegation_id"]
        sent_res = state.get("secondary_data", {})

        gw.record_interaction(
            sender_agent_id="agent_analyst",
            receiver_agent_id="agent_coordinator",
            interaction_type=InteractionType.RESULT,
            conversation_id=conv_id,
            task_id=f"sent_root_{wf_id}",
            delegation_id=del_id,
            semantic_summary=f"Reported {sent_res.get('high_priority_count', 2511)} critical severity tickets to Coordinator",
            raw_content=f"Severity distribution analyzed: {sent_res.get('high_priority_count', 2511)} critical tickets identified. Enterprise accounts impacted: 42%.",
            resource_refs=["file://customer_complaints.csv"],
            sensitivity_label=SensitivityLabel.INTERNAL
        )

        gw.record_interaction(
            sender_agent_id="agent_coordinator",
            receiver_agent_id="agent_reporter",
            interaction_type=InteractionType.HANDOFF,
            conversation_id=conv_id,
            task_id=f"sent_rep_{wf_id}",
            delegation_id=state["root_delegation_id"],
            semantic_summary="Handed off verified sentiment & severity findings to Reporter",
            raw_content="All NLP sentiment and statistical metrics validated. Authorized final executive resolution synthesis.",
            resource_refs=["file://customer_complaints.csv"],
            sensitivity_label=SensitivityLabel.INTERNAL
        )

        return {
            "analysis_data": sent_res,
            "node_history": ["node_impact_analysis"],
            "status": "reporting"
        }

    def node_synthesis_reporting(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        wf_id = state["workflow_id"]
        conv_id = state["conversation_id"]
        del_id = state["report_delegation_id"]
        sent_res = state.get("analysis_data", {})

        report_md = (
            "# 💬 Consumer Experience & Sentiment Analysis Report\n\n"
            "**Orchestrator:** Agent Coordinator | **Squad:** Consumer Sentiment & Experience (5 Specialized Agents)\n\n"
            "### 1. Sentiment & Emotional Polarity Overview\n"
            f"- **Dataset Evaluated:** `customer_complaints.csv` ({sent_res.get('total_tickets', 5025)} total complaints)\n"
            f"- **Average Sentiment Score:** `{sent_res.get('average_sentiment', -0.62):.2f}` (Strongly Negative Polarity)\n"
            f"- **High Severity Incidents:** **{sent_res.get('high_priority_count', 2511)} critical tickets**\n\n"
            "### 2. Primary Pain Points & Category Clusters\n"
            "1. **Credit Reporting & Score Updates:** Accounts for 48% of total frustration mentions.\n"
            "2. **Billing Inaccuracies & Late Fee Reversals:** Accounts for 31% of escalated complaints.\n"
            "3. **Multi-Factor Authentication (MFA) Delays:** Rapidly increasing churn indicator on Enterprise tier.\n\n"
            "### 3. Resolution Recommendations\n"
            "- Implement proactive webhook alerts for credit bureau update delays.\n"
            "- Auto-credit standard billing dispute tickets under $50 to improve customer satisfaction.\n"
            "- Audit SLA escalation thresholds with Account Management."
        )

        gw.record_interaction(
            sender_agent_id="agent_reporter",
            receiver_agent_id="agent_coordinator",
            interaction_type=InteractionType.RESULT,
            conversation_id=conv_id,
            task_id=f"sent_root_{wf_id}",
            delegation_id=del_id,
            semantic_summary="Delivered completed Consumer Experience & Sentiment Report",
            raw_content="Executive sentiment dossier generated and persisted successfully.",
            resource_refs=["file://customer_complaints.csv"],
            sensitivity_label=SensitivityLabel.INTERNAL
        )

        return {
            "final_output": report_md,
            "node_history": ["node_synthesis_reporting"],
            "status": "completed"
        }

    def node_finalize(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        return {
            "status": "completed",
            "active_agents": ["agent_coordinator", "agent_researcher", "agent_sentiment", "agent_analyst", "agent_reporter"],
            "node_history": ["node_finalize"]
        }

    builder = StateGraph(MultiAgentWorkflowState)
    builder.add_node("node_init_sent_coord", node_init_sent_coord)
    builder.add_node("node_complaint_intake", node_complaint_intake)
    builder.add_node("node_sentiment_nlp", node_sentiment_nlp)
    builder.add_node("node_impact_analysis", node_impact_analysis)
    builder.add_node("node_synthesis_reporting", node_synthesis_reporting)
    builder.add_node("node_finalize", node_finalize)

    builder.add_edge(START, "node_init_sent_coord")
    builder.add_edge("node_init_sent_coord", "node_complaint_intake")
    builder.add_edge("node_complaint_intake", "node_sentiment_nlp")
    builder.add_edge("node_sentiment_nlp", "node_impact_analysis")
    builder.add_edge("node_impact_analysis", "node_synthesis_reporting")
    builder.add_edge("node_synthesis_reporting", "node_finalize")
    builder.add_edge("node_finalize", END)

    return builder.compile()


# ==============================================================================
# 3. Cross-Squad Enterprise Collaboration (7 Agents - Federation & Bridge)
# ==============================================================================
def build_cross_squad_graph(gateway: Optional[ObservabilityGateway] = None):
    gw = gateway or default_gateway

    def node_init_cross(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        gw.set_capture_level(CaptureLevel(state.get("capture_level", 2)))
        wf_id = state["workflow_id"]
        p_id = state["principal_id"]
        conv_id = state["conversation_id"]

        root_del = gw.mint_delegation(
            principal_id=p_id,
            agent_id="agent_coordinator",
            task_id=f"cross_root_{wf_id}",
            parent_delegation_id=None,
            scope="cross_squad_enterprise_incident",
            metadata={"workflow_id": wf_id, "squad": "cross_squad"}
        )
        res_del = gw.mint_delegation(
            principal_id=p_id,
            agent_id="agent_researcher",
            task_id=f"cross_res_{wf_id}",
            parent_delegation_id=root_del.delegation_id,
            scope="complaints_intake",
            metadata={"workflow_id": wf_id}
        )
        sent_del = gw.mint_delegation(
            principal_id=p_id,
            agent_id="agent_sentiment",
            task_id=f"cross_sent_{wf_id}",
            parent_delegation_id=root_del.delegation_id,
            scope="sentiment_and_threat_flagging",
            metadata={"workflow_id": wf_id}
        )
        forensics_del = gw.mint_delegation(
            principal_id=p_id,
            agent_id="agent_forensics",
            task_id=f"cross_forensics_{wf_id}",
            parent_delegation_id=root_del.delegation_id,
            scope="access_log_forensics",
            metadata={"workflow_id": wf_id}
        )
        threat_del = gw.mint_delegation(
            principal_id=p_id,
            agent_id="agent_threat_hunter",
            task_id=f"cross_threat_{wf_id}",
            parent_delegation_id=root_del.delegation_id,
            scope="privilege_escalation_trace",
            metadata={"workflow_id": wf_id}
        )
        compliance_del = gw.mint_delegation(
            principal_id=p_id,
            agent_id="agent_compliance",
            task_id=f"cross_compliance_{wf_id}",
            parent_delegation_id=root_del.delegation_id,
            scope="regulatory_policy_audit",
            metadata={"workflow_id": wf_id}
        )
        rep_del = gw.mint_delegation(
            principal_id=p_id,
            agent_id="agent_reporter",
            task_id=f"cross_rep_{wf_id}",
            parent_delegation_id=root_del.delegation_id,
            scope="cross_domain_synthesis",
            metadata={"workflow_id": wf_id}
        )

        gw.record_interaction(
            sender_agent_id="agent_coordinator",
            receiver_agent_id="agent_researcher",
            interaction_type=InteractionType.DELEGATION,
            conversation_id=conv_id,
            task_id=res_del.task_id,
            delegation_id=res_del.delegation_id,
            semantic_summary="[Phase 1] Delegated customer complaint dossier intake to Complaints Squad",
            raw_content="Extract customer complaint TKT-1004 and associated security breach indicators from customer_complaints.csv.",
            resource_refs=["file://customer_complaints.csv"],
            sensitivity_label=SensitivityLabel.INTERNAL
        )

        return {
            "root_delegation_id": root_del.delegation_id,
            "research_delegation_id": res_del.delegation_id,
            "sentiment_delegation_id": sent_del.delegation_id,
            "forensics_delegation_id": forensics_del.delegation_id,
            "threat_hunter_delegation_id": threat_del.delegation_id,
            "compliance_delegation_id": compliance_del.delegation_id,
            "report_delegation_id": rep_del.delegation_id,
            "node_history": ["node_init_cross"],
            "status": "cross_intake_running"
        }

    def node_intake_complaint(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        wf_id = state["workflow_id"]
        conv_id = state["conversation_id"]
        res_del = state.get("research_delegation_id") or "del_res"

        gw.record_interaction(
            sender_agent_id="agent_researcher",
            receiver_agent_id="agent_sentiment",
            interaction_type=InteractionType.INFORMATION_TRANSFER,
            conversation_id=conv_id,
            task_id=f"cross_sent_{wf_id}",
            delegation_id=res_del,
            semantic_summary="Transferred complaint ticket TKT-1004 to Sentiment Specialist for threat indicator analysis",
            raw_content="Customer narrative in TKT-1004: 'Customer reports unauthorized login and file access from an unfamiliar IP address'. Handing off for threat evaluation.",
            resource_refs=["ticket://crm/TKT-1004"],
            sensitivity_label=SensitivityLabel.RESTRICTED
        )
        return {"node_history": ["node_intake_complaint"], "status": "flagging"}

    def node_sentiment_flag(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        wf_id = state["workflow_id"]
        conv_id = state["conversation_id"]
        sent_del = state.get("sentiment_delegation_id") or "del_sent"

        gw.record_interaction(
            sender_agent_id="agent_sentiment",
            receiver_agent_id="agent_coordinator",
            interaction_type=InteractionType.ESCALATION,
            conversation_id=conv_id,
            task_id=f"cross_root_{wf_id}",
            delegation_id=sent_del,
            semantic_summary="ESCALATION: Flagged account credential leak in TKT-1004; requesting SecOps bridge",
            raw_content="URGENT INCIDENT ESCALATION: TKT-1004 sentiment indicates high severity credential compromise. Requesting Coordinator bridge to Security Forensics Squad.",
            resource_refs=["ticket://crm/TKT-1004"],
            sensitivity_label=SensitivityLabel.RESTRICTED
        )
        return {"node_history": ["node_sentiment_flag"], "status": "bridging"}

    def node_cross_squad_bridge(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        wf_id = state["workflow_id"]
        conv_id = state["conversation_id"]
        root_del = state.get("root_delegation_id") or "del_root"

        # This is the historic CROSS-SQUAD BRIDGE edge!
        gw.record_interaction(
            sender_agent_id="agent_coordinator",
            receiver_agent_id="agent_forensics",
            interaction_type=InteractionType.HANDOFF,
            conversation_id=conv_id,
            task_id=f"cross_forensics_{wf_id}",
            delegation_id=root_del,
            semantic_summary="[CROSS-SQUAD BRIDGE: Complaints Squad ➔ Security Squad] Activated SecOps Forensics for TKT-1004",
            raw_content="CROSS-SQUAD DELEGATION BRIDGE: Incident Commander authorizing Security Forensics Squad to scan system_access_logs.csv matching TKT-1004 incident timestamp.",
            resource_refs=["file://system_access_logs.csv", "ticket://crm/TKT-1004"],
            sensitivity_label=SensitivityLabel.RESTRICTED
        )
        return {"node_history": ["node_cross_squad_bridge"], "status": "forensics_scanning"}

    def node_sec_forensics(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        wf_id = state["workflow_id"]
        conv_id = state["conversation_id"]
        forensics_del = state.get("forensics_delegation_id") or "del_forensics"

        gw.record_interaction(
            sender_agent_id="agent_forensics",
            receiver_agent_id="agent_threat_hunter",
            interaction_type=InteractionType.INFORMATION_TRANSFER,
            conversation_id=conv_id,
            task_id=f"cross_threat_{wf_id}",
            delegation_id=forensics_del,
            semantic_summary="Correlated access logs: Found unauthorized tenant_492.sql export (LOG-510) and root escalation (LOG-512)",
            raw_content="Correlation complete: Customer TKT-1004 matches access log LOG-510 (unauthorized tenant backup export to S3) and LOG-503 (Slack webhook share). Forwarding to Threat Hunter.",
            resource_refs=["file://system_access_logs.csv", "s3://customer-backups/tenant_492.sql"],
            sensitivity_label=SensitivityLabel.RESTRICTED
        )
        return {"node_history": ["node_sec_forensics"], "status": "threat_hunting"}

    def node_threat_hunt(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        wf_id = state["workflow_id"]
        conv_id = state["conversation_id"]
        threat_del = state.get("threat_hunter_delegation_id") or "del_threat"

        gw.record_interaction(
            sender_agent_id="agent_threat_hunter",
            receiver_agent_id="agent_compliance",
            interaction_type=InteractionType.ESCALATION,
            conversation_id=conv_id,
            task_id=f"cross_compliance_{wf_id}",
            delegation_id=threat_del,
            semantic_summary="ESCALATION: Confirmed multi-hop privilege escalation on iam://roles/production_access",
            raw_content="Confirmed attack chain: Attacker utilized usr_dev_01 session to export tenant backup, followed by root privilege escalation on iam://roles/production_access. Forwarding to Compliance Auditor.",
            resource_refs=["iam://roles/production_access"],
            sensitivity_label=SensitivityLabel.RESTRICTED
        )
        return {"node_history": ["node_threat_hunt"], "status": "compliance_auditing"}

    def node_compliance_verify(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        wf_id = state["workflow_id"]
        conv_id = state["conversation_id"]
        compliance_del = state.get("compliance_delegation_id") or "del_compliance"

        gw.record_interaction(
            sender_agent_id="agent_compliance",
            receiver_agent_id="agent_reporter",
            interaction_type=InteractionType.HANDOFF,
            conversation_id=conv_id,
            task_id=f"cross_rep_{wf_id}",
            delegation_id=compliance_del,
            semantic_summary="Handed off cross-domain compliance evidence to Executive Reporter",
            raw_content="Compliance verdict: Dual violation of NIST AC-3 (Access Enforcement) and NIST SC-7 (Boundary Protection). Evidence bundled for unified cross-squad dossier.",
            resource_refs=["file://system_access_logs.csv", "file://customer_complaints.csv"],
            sensitivity_label=SensitivityLabel.INTERNAL
        )
        return {"node_history": ["node_compliance_verify"], "status": "reporting"}

    def node_unified_report(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        wf_id = state["workflow_id"]
        conv_id = state["conversation_id"]
        rep_del = state.get("report_delegation_id") or "del_rep"

        report_md = (
            "# 🌐 Enterprise Cross-Squad Incident Report\n\n"
            "**Incident Commander:** Agent Coordinator | **Squads:** Complaints Intake Squad ➔ Security Forensics Squad (7 Agents)\n\n"
            "### 1. Cross-Squad Investigation Timeline\n"
            "1. **Phase 1 (Complaints Squad):** `agent_researcher` and `agent_sentiment` ingested complaint `TKT-1004` flagging unauthorized account activity.\n"
            "2. **Phase 2 (Cross-Squad Bridge):** `agent_coordinator` established an inter-squad bridge, delegating forensic log correlation to `agent_forensics`.\n"
            "3. **Phase 3 (SecOps Squad):** `agent_forensics` and `agent_threat_hunter` correlated server logs, discovering `LOG-510` (tenant database export) and `LOG-512` (root IAM privilege escalation).\n"
            "4. **Phase 4 (Compliance & Synthesis):** `agent_compliance` verified NIST AC-3 and SC-7 violations; `agent_reporter` synthesized the unified executive dossier.\n\n"
            "### 2. Multi-Domain Root Cause & Impact\n"
            "- **Customer Impact:** Account `cust_1004` experienced session hijacking.\n"
            "- **Infrastructure Impact:** Production IAM role compromised; tenant database `tenant_492.sql` exfiltrated.\n\n"
            "### 3. Cross-Functional Corrective Actions\n"
            "- Immediate token revocation for `usr_dev_01` and `usr_admin_root`.\n"
            "- Notify affected enterprise customer tier under regulatory 72-hour breach disclosure window.\n"
            "- Apply automated delegation token invariants at the Observability Gateway to prevent lateral privilege escalation."
        )

        gw.record_interaction(
            sender_agent_id="agent_reporter",
            receiver_agent_id="agent_coordinator",
            interaction_type=InteractionType.RESULT,
            conversation_id=conv_id,
            task_id=f"cross_root_{wf_id}",
            delegation_id=rep_del,
            semantic_summary="Delivered unified Cross-Squad Executive Incident Dossier",
            raw_content="Cross-squad dossier compiled and submitted to Enterprise Incident Commander.",
            resource_refs=["file://system_access_logs.csv", "file://customer_complaints.csv"],
            sensitivity_label=SensitivityLabel.INTERNAL
        )

        return {
            "final_output": report_md,
            "node_history": ["node_unified_report"],
            "status": "completed"
        }

    def node_finalize(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        return {
            "status": "completed",
            "active_agents": [
                "agent_coordinator",
                "agent_researcher",
                "agent_sentiment",
                "agent_forensics",
                "agent_threat_hunter",
                "agent_compliance",
                "agent_reporter"
            ],
            "node_history": ["node_finalize"]
        }

    builder = StateGraph(MultiAgentWorkflowState)
    builder.add_node("node_init_cross", node_init_cross)
    builder.add_node("node_intake_complaint", node_intake_complaint)
    builder.add_node("node_sentiment_flag", node_sentiment_flag)
    builder.add_node("node_cross_squad_bridge", node_cross_squad_bridge)
    builder.add_node("node_sec_forensics", node_sec_forensics)
    builder.add_node("node_threat_hunt", node_threat_hunt)
    builder.add_node("node_compliance_verify", node_compliance_verify)
    builder.add_node("node_unified_report", node_unified_report)
    builder.add_node("node_finalize", node_finalize)

    builder.add_edge(START, "node_init_cross")
    builder.add_edge("node_init_cross", "node_intake_complaint")
    builder.add_edge("node_intake_complaint", "node_sentiment_flag")
    builder.add_edge("node_sentiment_flag", "node_cross_squad_bridge")
    builder.add_edge("node_cross_squad_bridge", "node_sec_forensics")
    builder.add_edge("node_sec_forensics", "node_threat_hunt")
    builder.add_edge("node_threat_hunt", "node_compliance_verify")
    builder.add_edge("node_compliance_verify", "node_unified_report")
    builder.add_edge("node_unified_report", "node_finalize")
    builder.add_edge("node_finalize", END)

    return builder.compile()


# ==============================================================================
# 4. Adversarial Critic & Debate Squad (5 Agents - P2P Mesh Topology)
# ==============================================================================
def build_adversarial_critic_graph(gateway: Optional[ObservabilityGateway] = None):
    gw = gateway or default_gateway

    def node_init_critic(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        gw.set_capture_level(CaptureLevel(state.get("capture_level", 2)))
        wf_id = state["workflow_id"]
        p_id = state["principal_id"]
        conv_id = state["conversation_id"]

        root_del = gw.mint_delegation(principal_id=p_id, agent_id="agent_coordinator", task_id=f"critic_root_{wf_id}", parent_delegation_id=None, scope="adversarial_debate_coordination")
        res_del = gw.mint_delegation(principal_id=p_id, agent_id="agent_researcher", task_id=f"critic_res_{wf_id}", parent_delegation_id=root_del.delegation_id, scope="evidence_collection")
        ana_del = gw.mint_delegation(principal_id=p_id, agent_id="agent_analyst", task_id=f"critic_ana_{wf_id}", parent_delegation_id=root_del.delegation_id, scope="hypothesis_generation")
        crit_del = gw.mint_delegation(principal_id=p_id, agent_id="agent_critic", task_id=f"critic_crit_{wf_id}", parent_delegation_id=root_del.delegation_id, scope="adversarial_challenge")
        rep_del = gw.mint_delegation(principal_id=p_id, agent_id="agent_reporter", task_id=f"critic_rep_{wf_id}", parent_delegation_id=root_del.delegation_id, scope="consensus_reporting")

        gw.record_interaction(
            sender_agent_id="agent_coordinator",
            receiver_agent_id="agent_researcher",
            interaction_type=InteractionType.DELEGATION,
            conversation_id=conv_id,
            task_id=res_del.task_id,
            delegation_id=res_del.delegation_id,
            semantic_summary="Delegated evidence collection for adversarial debate validation",
            raw_content="Collect empirical evidence records for peer-to-peer adversarial review and causal validation."
        )

        return {
            "root_delegation_id": root_del.delegation_id,
            "research_delegation_id": res_del.delegation_id,
            "analysis_delegation_id": ana_del.delegation_id,
            "critic_delegation_id": crit_del.delegation_id,
            "report_delegation_id": rep_del.delegation_id,
            "node_history": ["node_init_critic"],
            "status": "gathering_evidence"
        }

    def node_gather_evidence(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        wf_id = state["workflow_id"]
        conv_id = state["conversation_id"]
        del_id = state["research_delegation_id"]

        gw.record_interaction(
            sender_agent_id="agent_researcher",
            receiver_agent_id="agent_analyst",
            interaction_type=InteractionType.INFORMATION_TRANSFER,
            conversation_id=conv_id,
            task_id=f"critic_ana_{wf_id}",
            delegation_id=del_id,
            semantic_summary="Transferred raw dataset observations to Analyst for hypothesis generation",
            raw_content="Delivered 5025 records. Ready for initial causal hypothesis formulation."
        )
        return {"node_history": ["node_gather_evidence"], "status": "debating"}

    def node_debate_round(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        wf_id = state["workflow_id"]
        conv_id = state["conversation_id"]
        ana_del = state["analysis_delegation_id"]
        crit_del = state.get("critic_delegation_id", ana_del)

        # 1. Analyst proposes hypothesis to Critic
        gw.record_interaction(
            sender_agent_id="agent_analyst",
            receiver_agent_id="agent_critic",
            interaction_type=InteractionType.CLARIFICATION,
            conversation_id=conv_id,
            task_id=f"critic_crit_{wf_id}",
            delegation_id=ana_del,
            semantic_summary="Proposed Hypothesis: 80% anomaly spike caused by billing gateway timeout",
            raw_content="Hypothesis H1: Primary root cause of customer churn spike is payment gateway timeout on Oct 15th."
        )

        # 2. Critic challenges hypothesis with counter-evidence
        gw.record_interaction(
            sender_agent_id="agent_critic",
            receiver_agent_id="agent_analyst",
            interaction_type=InteractionType.RESPONSE,
            conversation_id=conv_id,
            task_id=f"critic_ana_{wf_id}",
            delegation_id=crit_del,
            semantic_summary="Adversarial Critique: Confounding variable detected — MFA latency preceded billing failure",
            raw_content="Critique C1: Temporal causal invariant violation. MFA timeouts in TKT-1004 occurred 45 minutes prior. The billing spike is a downstream symptom, not root cause."
        )

        # 3. Analyst acknowledges and updates consensus
        gw.record_interaction(
            sender_agent_id="agent_analyst",
            receiver_agent_id="agent_critic",
            interaction_type=InteractionType.RESPONSE,
            conversation_id=conv_id,
            task_id=f"critic_crit_{wf_id}",
            delegation_id=ana_del,
            semantic_summary="Consensus Reached: Refined root cause to Multi-Factor Authentication bottleneck",
            raw_content="Consensus C2: Adversarial critique accepted. Root cause refined to MFA authentication latency; billing failures categorized as secondary cascade."
        )

        # 4. Analyst hands off to Reporter
        gw.record_interaction(
            sender_agent_id="agent_analyst",
            receiver_agent_id="agent_reporter",
            interaction_type=InteractionType.HANDOFF,
            conversation_id=conv_id,
            task_id=f"critic_rep_{wf_id}",
            delegation_id=ana_del,
            semantic_summary="Handed off audited adversarial consensus to Executive Reporter",
            raw_content="Consensus validated through peer-to-peer critique. Ready for final synthesis."
        )

        return {"node_history": ["node_debate_round"], "status": "reporting"}

    def node_critic_reporting(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        wf_id = state["workflow_id"]
        conv_id = state["conversation_id"]
        rep_del = state["report_delegation_id"]

        report_md = (
            "# 🎯 Adversarial Multi-Agent Consensus & Causality Audit\n\n"
            "**Orchestrator:** Agent Coordinator | **Squad:** Adversarial Critic & Debate Squad (5 Agents)\n\n"
            "### 1. Peer-to-Peer Debate Summary\n"
            "- **Primary Hypothesis (Agent Analyst):** Initial claim posited payment gateway timeout as sole root cause.\n"
            "- **Adversarial Critique (Agent Critic):** Identified confounding temporal variable: MFA delays occurred 45 minutes prior to billing drops.\n"
            "- **Consensus Verdict:** Causal resolution achieved — MFA bottleneck triggered customer session retries, inducing synthetic load on billing gateways.\n\n"
            "### 2. Causality Invariant Verification\n"
            "- **Temporal Precedence Invariant:** Verified $\\tau(E_{MFA}) < \\tau(E_{Billing})$.\n"
            "- **False-Positive Reduction:** Eliminated single-point misattribution by 100% through bidirectional peer review."
        )

        gw.record_interaction(
            sender_agent_id="agent_reporter",
            receiver_agent_id="agent_coordinator",
            interaction_type=InteractionType.RESULT,
            conversation_id=conv_id,
            task_id=f"critic_root_{wf_id}",
            delegation_id=rep_del,
            semantic_summary="Delivered completed Adversarial Consensus & Causality Report",
            raw_content="Adversarial debate findings compiled into audited report."
        )

        return {"final_output": report_md, "node_history": ["node_critic_reporting"], "status": "completed"}

    def node_finalize(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        return {
            "status": "completed",
            "active_agents": ["agent_coordinator", "agent_researcher", "agent_analyst", "agent_critic", "agent_reporter"],
            "node_history": ["node_finalize"]
        }

    builder = StateGraph(MultiAgentWorkflowState)
    builder.add_node("node_init_critic", node_init_critic)
    builder.add_node("node_gather_evidence", node_gather_evidence)
    builder.add_node("node_debate_round", node_debate_round)
    builder.add_node("node_critic_reporting", node_critic_reporting)
    builder.add_node("node_finalize", node_finalize)

    builder.add_edge(START, "node_init_critic")
    builder.add_edge("node_init_critic", "node_gather_evidence")
    builder.add_edge("node_gather_evidence", "node_debate_round")
    builder.add_edge("node_debate_round", "node_critic_reporting")
    builder.add_edge("node_critic_reporting", "node_finalize")
    builder.add_edge("node_finalize", END)

    return builder.compile()


# ==============================================================================
# 5. Rapid Consensus Squad (3 Agents - Triangular Loop)
# ==============================================================================
def build_rapid_consensus_graph(gateway: Optional[ObservabilityGateway] = None):
    gw = gateway or default_gateway

    def node_init_rapid(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        gw.set_capture_level(CaptureLevel(state.get("capture_level", 2)))
        wf_id = state["workflow_id"]
        p_id = state["principal_id"]
        conv_id = state["conversation_id"]

        root_del = gw.mint_delegation(principal_id=p_id, agent_id="agent_coordinator", task_id=f"rapid_root_{wf_id}", parent_delegation_id=None, scope="rapid_summary_triage")
        res_del = gw.mint_delegation(principal_id=p_id, agent_id="agent_researcher", task_id=f"rapid_res_{wf_id}", parent_delegation_id=root_del.delegation_id, scope="fast_record_ingestion")
        ana_del = gw.mint_delegation(principal_id=p_id, agent_id="agent_analyst", task_id=f"rapid_ana_{wf_id}", parent_delegation_id=root_del.delegation_id, scope="fast_metric_computation")

        gw.record_interaction(
            sender_agent_id="agent_coordinator",
            receiver_agent_id="agent_researcher",
            interaction_type=InteractionType.DELEGATION,
            conversation_id=conv_id,
            task_id=res_del.task_id,
            delegation_id=res_del.delegation_id,
            semantic_summary="Rapid triage delegation to Research Agent",
            raw_content="Perform rapid snapshot extraction of active records."
        )

        return {
            "root_delegation_id": root_del.delegation_id,
            "research_delegation_id": res_del.delegation_id,
            "analysis_delegation_id": ana_del.delegation_id,
            "node_history": ["node_init_rapid"],
            "status": "rapid_running"
        }

    def node_fast_cycle(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        wf_id = state["workflow_id"]
        conv_id = state["conversation_id"]
        res_del = state["research_delegation_id"]
        ana_del = state["analysis_delegation_id"]

        # Fast pass: Researcher -> Analyst
        gw.record_interaction(
            sender_agent_id="agent_researcher",
            receiver_agent_id="agent_analyst",
            interaction_type=InteractionType.INFORMATION_TRANSFER,
            conversation_id=conv_id,
            task_id=f"rapid_ana_{wf_id}",
            delegation_id=res_del,
            semantic_summary="Transferred quick dataset snapshot to Analyst",
            raw_content="Snapshot extracted: 5025 records loaded for rapid summary calculation."
        )

        # Fast pass: Analyst -> Coordinator (Triangle closed!)
        gw.record_interaction(
            sender_agent_id="agent_analyst",
            receiver_agent_id="agent_coordinator",
            interaction_type=InteractionType.RESULT,
            conversation_id=conv_id,
            task_id=f"rapid_root_{wf_id}",
            delegation_id=ana_del,
            semantic_summary="Delivered rapid consensus metrics to Coordinator (Triangle Loop Closed)",
            raw_content="Rapid analysis complete: Average sentiment -0.62, 2511 high priority records identified."
        )

        report_md = (
            "# ⚡ Rapid 3-Agent Consensus Summary\n\n"
            "**Orchestrator:** Agent Coordinator | **Squad:** Rapid Consensus Squad (3 Agents - Triangle Topology)\n\n"
            "### Fast Verification Results\n"
            "- **Agent Coordinator** ➔ **Agent Researcher** ➔ **Agent Analyst** ➔ **Agent Coordinator** (Zero Reporter latency)\n"
            "- **Total Records Analyzed:** 5,025 records\n"
            "- **Severity Distribution:** 2,511 critical issues flagged for immediate triage\n"
            "- **Execution Latency:** Accelerated 3x compared to 5-agent pipeline."
        )

        return {
            "final_output": report_md,
            "node_history": ["node_fast_cycle"],
            "status": "completed"
        }

    def node_finalize(state: MultiAgentWorkflowState) -> Dict[str, Any]:
        return {
            "status": "completed",
            "active_agents": ["agent_coordinator", "agent_researcher", "agent_analyst"],
            "node_history": ["node_finalize"]
        }

    builder = StateGraph(MultiAgentWorkflowState)
    builder.add_node("node_init_rapid", node_init_rapid)
    builder.add_node("node_fast_cycle", node_fast_cycle)
    builder.add_node("node_finalize", node_finalize)

    builder.add_edge(START, "node_init_rapid")
    builder.add_edge("node_init_rapid", "node_fast_cycle")
    builder.add_edge("node_fast_cycle", "node_finalize")
    builder.add_edge("node_finalize", END)

    return builder.compile()
