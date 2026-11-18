"""
Unified Event Store providing thread-safe persistence and querying
for workflows, delegations, interactions, execution events, artifacts, and provenance.
"""

import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from backend.storage.database import get_connection, init_db
from backend.schemas.events import CIMEvent, ActionSemantic, ActionOutcome, Direction, PrincipalScope, ResourceClass, SensitivityLabel, InteractionType, CaptureLevel
from backend.schemas.interaction import InteractionRecord
from backend.schemas.workflow import WorkflowRun, DelegationRecord, TaskRecord, ArtifactRecord, ProvenanceEdge

class EventStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        init_db(self.db_path)

    def _conn(self) -> sqlite3.Connection:
        return get_connection(self.db_path)

    def close(self):
        from backend.storage.database import close_connection
        close_connection()

    # -------------------------------------------------------------
    # Workflow Runs
    # -------------------------------------------------------------
    def save_workflow_run(self, run: WorkflowRun):
        conn = self._conn()
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO workflow_runs (
                    workflow_id, name, task_description, dataset_name, mode,
                    capture_level, status, start_time, end_time, root_delegation_id,
                    final_output, error_message, stats
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.workflow_id, run.name, run.task_description, run.dataset_name,
                    run.mode.value if hasattr(run.mode, "value") else str(run.mode),
                    run.capture_level.value if hasattr(run.capture_level, "value") else int(run.capture_level),
                    run.status, run.start_time, run.end_time, run.root_delegation_id,
                    run.final_output, run.error_message, json.dumps(run.stats)
                )
            )

    def get_workflow_run(self, workflow_id: str) -> Optional[WorkflowRun]:
        conn = self._conn()
        cur = conn.execute("SELECT * FROM workflow_runs WHERE workflow_id = ?", (workflow_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["stats"] = json.loads(d["stats"]) if d["stats"] else {}
        return WorkflowRun(**d)

    def list_workflow_runs(self, limit: int = 50) -> List[WorkflowRun]:
        conn = self._conn()
        cur = conn.execute("SELECT * FROM workflow_runs ORDER BY start_time DESC LIMIT ?", (limit,))
        runs = []
        for row in cur.fetchall():
            d = dict(row)
            d["stats"] = json.loads(d["stats"]) if d["stats"] else {}
            runs.append(WorkflowRun(**d))
        return runs

    # -------------------------------------------------------------
    # Delegations (Authority Lineage)
    # -------------------------------------------------------------
    def save_delegation(self, delegation: DelegationRecord):
        conn = self._conn()
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO delegations (
                    delegation_id, delegation_parent_id, principal_id, agent_id,
                    task_id, scope, status, issued_at, completed_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    delegation.delegation_id, delegation.delegation_parent_id,
                    delegation.principal_id, delegation.agent_id, delegation.task_id,
                    delegation.scope, delegation.status.value if hasattr(delegation.status, "value") else str(delegation.status),
                    delegation.issued_at, delegation.completed_at, json.dumps(delegation.metadata)
                )
            )

    def get_delegation(self, delegation_id: str) -> Optional[DelegationRecord]:
        conn = self._conn()
        cur = conn.execute("SELECT * FROM delegations WHERE delegation_id = ?", (delegation_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else {}
        return DelegationRecord(**d)

    def list_delegations(self, limit: int = 100) -> List[DelegationRecord]:
        conn = self._conn()
        cur = conn.execute("SELECT * FROM delegations ORDER BY issued_at DESC LIMIT ?", (limit,))
        res = []
        for row in cur.fetchall():
            d = dict(row)
            d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else {}
            res.append(DelegationRecord(**d))
        return res

    def get_delegation_closure(self, root_delegation_id: str) -> List[DelegationRecord]:
        """
        Returns transitive descendants of root_delegation_id (Lineage Closure).
        Implements CIM Invariant I3.
        """
        conn = self._conn()
        query = """
        WITH RECURSIVE lineage(delegation_id) AS (
            SELECT delegation_id FROM delegations WHERE delegation_id = ?
            UNION ALL
            SELECT d.delegation_id FROM delegations d
            JOIN lineage l ON d.delegation_parent_id = l.delegation_id
        )
        SELECT d.* FROM delegations d
        JOIN lineage l ON d.delegation_id = l.delegation_id
        ORDER BY d.issued_at ASC;
        """
        cur = conn.execute(query, (root_delegation_id,))
        results = []
        for row in cur.fetchall():
            d = dict(row)
            d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else {}
            results.append(DelegationRecord(**d))
        return results

    # -------------------------------------------------------------
    # Inter-Agent Interactions (Our Main Extension)
    # -------------------------------------------------------------
    def save_interaction(self, record: InteractionRecord):
        conn = self._conn()
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO interactions (
                    interaction_id, timestamp, sender_agent_id, receiver_agent_id,
                    interaction_type, conversation_id, task_id, workflow_id, delegation_id,
                    delegation_parent_id, trace_id, span_id, message_id,
                    reply_to_message_id, semantic_summary, content, resource_refs,
                    sensitivity_label, status, retry_count, downstream_action_ids,
                    provenance_refs, capture_level, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.interaction_id, record.timestamp, record.sender_agent_id,
                    record.receiver_agent_id,
                    record.interaction_type.value if hasattr(record.interaction_type, "value") else str(record.interaction_type),
                    record.conversation_id, record.task_id, record.workflow_id, record.delegation_id,
                    record.delegation_parent_id, record.trace_id, record.span_id,
                    record.message_id, record.reply_to_message_id,
                    record.semantic_summary, record.content,
                    json.dumps(record.resource_refs),
                    record.sensitivity_label.value if hasattr(record.sensitivity_label, "value") else str(record.sensitivity_label),
                    record.status, record.retry_count,
                    json.dumps(record.downstream_action_ids),
                    json.dumps(record.provenance_refs),
                    record.capture_level.value if hasattr(record.capture_level, "value") else int(record.capture_level),
                    json.dumps(record.metadata)
                )
            )

    def get_interaction(self, interaction_id: str) -> Optional[InteractionRecord]:
        conn = self._conn()
        cur = conn.execute("SELECT * FROM interactions WHERE interaction_id = ?", (interaction_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["resource_refs"] = json.loads(d["resource_refs"]) if d["resource_refs"] else []
        d["downstream_action_ids"] = json.loads(d["downstream_action_ids"]) if d["downstream_action_ids"] else []
        d["provenance_refs"] = json.loads(d["provenance_refs"]) if d["provenance_refs"] else []
        d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else {}
        return InteractionRecord(**d)

    def update_interaction_acknowledgment(
        self,
        interaction_id: str,
        status: str = "acknowledged",
        downstream_action_ids: Optional[List[str]] = None
    ) -> bool:
        """
        Updates the delivery/consumption status and downstream consequences of an interaction.
        Enforces persistent message acknowledgment and causality linking (Issue 1).
        """
        conn = self._conn()
        with conn:
            if downstream_action_ids is not None:
                cur = conn.execute(
                    "SELECT downstream_action_ids FROM interactions WHERE interaction_id = ? OR message_id = ?",
                    (interaction_id, interaction_id)
                )
                row = cur.fetchone()
                existing_actions = json.loads(row[0]) if row and row[0] else []
                merged = list(dict.fromkeys(existing_actions + downstream_action_ids))
                conn.execute(
                    "UPDATE interactions SET status = ?, downstream_action_ids = ? WHERE interaction_id = ? OR message_id = ?",
                    (status, json.dumps(merged), interaction_id, interaction_id)
                )
            else:
                conn.execute(
                    "UPDATE interactions SET status = ? WHERE interaction_id = ? OR message_id = ?",
                    (status, interaction_id, interaction_id)
                )
        return True

    def list_interactions(
        self,
        conversation_id: Optional[str] = None,
        delegation_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        interaction_type: Optional[str] = None,
        workflow_id: Optional[str] = None,
        order: str = "desc",
        limit: int = 200
    ) -> List[InteractionRecord]:
        conn = self._conn()
        clauses = []
        params = []
        if workflow_id:
            clauses.append("(workflow_id = ? OR task_id LIKE ? OR conversation_id LIKE ?)")
            params.extend([workflow_id, f"%{workflow_id}%", f"%{workflow_id}%"])
        if conversation_id:
            clauses.append("conversation_id = ?")
            params.append(conversation_id)
        if delegation_id:
            clauses.append("delegation_id = ?")
            params.append(delegation_id)
        if agent_id:
            clauses.append("(sender_agent_id = ? OR receiver_agent_id = ?)")
            params.extend([agent_id, agent_id])
        if interaction_type:
            clauses.append("interaction_type = ?")
            params.append(interaction_type)
            
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        order_dir = "DESC" if str(order).lower() == "desc" else "ASC"
        query = f"SELECT * FROM interactions {where} ORDER BY timestamp {order_dir} LIMIT ?"
        params.append(limit)
        
        cur = conn.execute(query, params)
        records = []
        for row in cur.fetchall():
            d = dict(row)
            d["resource_refs"] = json.loads(d["resource_refs"]) if d["resource_refs"] else []
            d["downstream_action_ids"] = json.loads(d["downstream_action_ids"]) if d["downstream_action_ids"] else []
            d["provenance_refs"] = json.loads(d["provenance_refs"]) if d["provenance_refs"] else []
            d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else {}
            records.append(InteractionRecord(**d))
        return records

    # -------------------------------------------------------------
    # CIM Execution Events
    # -------------------------------------------------------------
    def save_execution_event(self, event: CIMEvent):
        conn = self._conn()
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO execution_events (
                    event_id, time, delegation_id, delegation_parent_id,
                    principal_user_id, agent_id, agent_instance_id,
                    tool_name, tool_operation, action_semantic, action_outcome,
                    direction, principal_scope, resource_type, resource_id,
                    resource_uri, sensitivity_label, target_principal_id,
                    trace_id, span_id, parent_span_id, workflow_id, task_id,
                    parameters, output_summary, labels
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id, event.time, event.delegation_id, event.delegation_parent_id,
                    event.principal_user_id, event.agent_id, event.agent_instance_id,
                    event.tool_name, event.tool_operation,
                    event.action_semantic.value if hasattr(event.action_semantic, "value") else str(event.action_semantic),
                    event.action_outcome.value if hasattr(event.action_outcome, "value") else str(event.action_outcome),
                    event.direction.value if hasattr(event.direction, "value") else str(event.direction),
                    event.principal_scope.value if hasattr(event.principal_scope, "value") else str(event.principal_scope),
                    event.resource_type.value if hasattr(event.resource_type, "value") else str(event.resource_type),
                    event.resource_id, event.resource_uri,
                    event.sensitivity_label.value if hasattr(event.sensitivity_label, "value") else str(event.sensitivity_label),
                    event.target_principal_id, event.trace_id, event.span_id, event.parent_span_id,
                    event.workflow_id, event.task_id, json.dumps(event.parameters),
                    event.output_summary, json.dumps(event.labels)
                )
            )

    def get_execution_event(self, event_id: str) -> Optional[CIMEvent]:
        conn = self._conn()
        cur = conn.execute("SELECT * FROM execution_events WHERE event_id = ?", (event_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["parameters"] = json.loads(d["parameters"]) if d["parameters"] else {}
        d["labels"] = json.loads(d["labels"]) if d["labels"] else {}
        return CIMEvent(**d)

    def list_execution_events(
        self,
        workflow_id: Optional[str] = None,
        delegation_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 500
    ) -> List[CIMEvent]:
        conn = self._conn()
        clauses = []
        params = []
        if workflow_id:
            clauses.append("workflow_id = ?")
            params.append(workflow_id)
        if delegation_id:
            clauses.append("delegation_id = ?")
            params.append(delegation_id)
        if trace_id:
            clauses.append("trace_id = ?")
            params.append(trace_id)
        if agent_id:
            clauses.append("agent_id = ?")
            params.append(agent_id)
            
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT * FROM execution_events {where} ORDER BY time ASC LIMIT ?"
        params.append(limit)
        
        cur = conn.execute(query, params)
        events = []
        for row in cur.fetchall():
            d = dict(row)
            d["parameters"] = json.loads(d["parameters"]) if d["parameters"] else {}
            d["labels"] = json.loads(d["labels"]) if d["labels"] else {}
            events.append(CIMEvent(**d))
        return events

    # -------------------------------------------------------------
    # Artifacts & Tasks
    # -------------------------------------------------------------
    def save_artifact(self, artifact: ArtifactRecord):
        conn = self._conn()
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO artifacts (
                    artifact_id, workflow_id, title, artifact_type, format,
                    content, summary, created_by_agent_id, delegation_id,
                    sensitivity_label, created_at, source_resource_refs
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact.artifact_id, artifact.workflow_id, artifact.title,
                    artifact.artifact_type, artifact.format, artifact.content,
                    artifact.summary, artifact.created_by_agent_id, artifact.delegation_id,
                    artifact.sensitivity_label.value if hasattr(artifact.sensitivity_label, "value") else str(artifact.sensitivity_label),
                    artifact.created_at, json.dumps(artifact.source_resource_refs)
                )
            )

    def get_artifact(self, artifact_id: str) -> Optional[ArtifactRecord]:
        conn = self._conn()
        cur = conn.execute("SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["source_resource_refs"] = json.loads(d["source_resource_refs"]) if d["source_resource_refs"] else []
        return ArtifactRecord(**d)

    def list_artifacts(self, workflow_id: Optional[str] = None) -> List[ArtifactRecord]:
        conn = self._conn()
        if workflow_id:
            cur = conn.execute("SELECT * FROM artifacts WHERE workflow_id = ? ORDER BY created_at DESC", (workflow_id,))
        else:
            cur = conn.execute("SELECT * FROM artifacts ORDER BY created_at DESC LIMIT 50")
        arts = []
        for row in cur.fetchall():
            d = dict(row)
            d["source_resource_refs"] = json.loads(d["source_resource_refs"]) if d["source_resource_refs"] else []
            arts.append(ArtifactRecord(**d))
        return arts

    # -------------------------------------------------------------
    # Provenance Edges
    # -------------------------------------------------------------
    def save_provenance_edge(self, edge: ProvenanceEdge):
        conn = self._conn()
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO provenance_edges (
                    edge_id, workflow_id, source_id, source_type,
                    target_id, target_type, relation, confidence,
                    timestamp, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    edge.edge_id, edge.workflow_id, edge.source_id, edge.source_type,
                    edge.target_id, edge.target_type, edge.relation, edge.confidence,
                    edge.timestamp, json.dumps(edge.metadata)
                )
            )

    def list_provenance_edges(self, workflow_id: Optional[str] = None) -> List[ProvenanceEdge]:
        conn = self._conn()
        if workflow_id:
            cur = conn.execute("SELECT * FROM provenance_edges WHERE workflow_id = ? ORDER BY timestamp ASC", (workflow_id,))
        else:
            cur = conn.execute("SELECT * FROM provenance_edges ORDER BY timestamp ASC LIMIT 500")
        edges = []
        for row in cur.fetchall():
            d = dict(row)
            d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else {}
            edges.append(ProvenanceEdge(**d))
        return edges

    # -------------------------------------------------------------
    # Research Query Helpers
    # -------------------------------------------------------------
    def get_blast_radius(self, delegation_id: str) -> List[Dict[str, Any]]:
        """
        Calculates the exact resource touch set under delegation d (and its descendants).
        Returns distinct (resource_id, resource_type, sensitivity_label, action_semantic).
        """
        conn = self._conn()
        query = """
        WITH RECURSIVE lineage(delegation_id) AS (
            SELECT delegation_id FROM delegations WHERE delegation_id = ?
            UNION ALL
            SELECT d.delegation_id FROM delegations d
            JOIN lineage l ON d.delegation_parent_id = l.delegation_id
        )
        SELECT DISTINCT e.resource_id, e.resource_type, e.sensitivity_label, e.action_semantic, e.tool_name
        FROM execution_events e
        JOIN lineage l ON e.delegation_id = l.delegation_id
        WHERE e.resource_id IS NOT NULL;
        """
        cur = conn.execute(query, (delegation_id,))
        return [dict(r) for r in cur.fetchall()]

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Returns overall system counts for the overview dashboard."""
        conn = self._conn()
        workflows_cnt = conn.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0]
        active_workflows = conn.execute("SELECT COUNT(*) FROM workflow_runs WHERE status = 'running'").fetchone()[0]
        interactions_cnt = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
        events_cnt = conn.execute("SELECT COUNT(*) FROM execution_events").fetchone()[0]
        delegations_cnt = conn.execute("SELECT COUNT(*) FROM delegations").fetchone()[0]
        retries_cnt = conn.execute("SELECT COALESCE(SUM(retry_count), 0) FROM interactions").fetchone()[0]
        agents_cnt = conn.execute("SELECT COUNT(DISTINCT agent_id) FROM agents").fetchone()[0]
        
        return {
            "total_workflows": workflows_cnt,
            "active_workflows": active_workflows,
            "total_interactions": interactions_cnt,
            "total_events": events_cnt,
            "total_delegations": delegations_cnt,
            "total_retries": retries_cnt,
            "active_agents": agents_cnt
        }

    def get_telemetry_feed(self, limit_workflows: int = 10, limit_events: int = 30) -> Dict[str, Any]:
        """
        Computes a rich, unified telemetry feed for the real-time Observability Overview.
        Aggregates KPI metrics, agent workload distribution, interaction breakdown,
        recent workflow streams, live CIM event feeds, and storage metrics.
        """
        conn = self._conn()
        
        # 1. Workflow KPIs
        total_wf = conn.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0]
        active_wf = conn.execute("SELECT COUNT(*) FROM workflow_runs WHERE status = 'running'").fetchone()[0]
        completed_wf = conn.execute("SELECT COUNT(*) FROM workflow_runs WHERE status = 'completed'").fetchone()[0]
        failed_wf = conn.execute("SELECT COUNT(*) FROM workflow_runs WHERE status = 'failed'").fetchone()[0]
        success_rate = round((completed_wf / total_wf) * 100, 1) if total_wf > 0 else 100.0

        interactions_cnt = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
        events_cnt = conn.execute("SELECT COUNT(*) FROM execution_events").fetchone()[0]
        delegations_cnt = conn.execute("SELECT COUNT(*) FROM delegations").fetchone()[0]
        retries_cnt = conn.execute("SELECT COALESCE(SUM(retry_count), 0) FROM interactions").fetchone()[0]
        agents_cnt = conn.execute("SELECT COUNT(DISTINCT agent_id) FROM agents").fetchone()[0]

        # 2. Agent Breakdown
        agent_colors = {
            "agent_coordinator": "#38bdf8",
            "agent_researcher": "#818cf8",
            "agent_analyst": "#f59e0b",
            "agent_reporter": "#10b981",
        }
        agent_names = {
            "agent_coordinator": "Coordinator (Agent A)",
            "agent_researcher": "Researcher (Agent B)",
            "agent_analyst": "Analyst (Agent C)",
            "agent_reporter": "Reporter (Agent D)",
        }
        agent_roles = {
            "agent_coordinator": "Lead Orchestrator & Planner",
            "agent_researcher": "Data Ingestion & Filtering",
            "agent_analyst": "Statistical & Anomaly Analysis",
            "agent_reporter": "Synthesis & Provenance Report",
        }

        # Query events per agent
        ev_cur = conn.execute("SELECT agent_id, COUNT(*) as c FROM execution_events GROUP BY agent_id")
        events_by_agent = {r[0]: r[1] for r in ev_cur.fetchall()}

        # Query interactions sent per agent
        sent_cur = conn.execute("SELECT sender_agent_id, COUNT(*) as c FROM interactions GROUP BY sender_agent_id")
        sent_by_agent = {r[0]: r[1] for r in sent_cur.fetchall()}

        # Query interactions received per agent
        recv_cur = conn.execute("SELECT receiver_agent_id, COUNT(*) as c FROM interactions GROUP BY receiver_agent_id")
        recv_by_agent = {r[0]: r[1] for r in recv_cur.fetchall()}

        total_system_activity = sum(events_by_agent.values()) + sum(sent_by_agent.values())

        agent_breakdown = []
        for aid in ["agent_coordinator", "agent_researcher", "agent_analyst", "agent_reporter"]:
            ev = events_by_agent.get(aid, 0)
            sent = sent_by_agent.get(aid, 0)
            recv = recv_by_agent.get(aid, 0)
            total_act = ev + sent
            pct = round((total_act / max(total_system_activity, 1)) * 100, 1)
            agent_breakdown.append({
                "agent_id": aid,
                "name": agent_names.get(aid, aid),
                "role": agent_roles.get(aid, "Specialized Agent"),
                "events_count": ev,
                "interactions_sent": sent,
                "interactions_received": recv,
                "total_activity": total_act,
                "activity_pct": pct,
                "color": agent_colors.get(aid, "#94a3b8")
            })

        # 3. Interaction Types Breakdown
        type_labels = {
            "delegation": ("Task Delegation", "#3b82f6"),
            "handoff": ("Context Handoff", "#10b981"),
            "clarification": ("Clarification Request", "#f59e0b"),
            "response": ("Clarification Reply", "#a855f7"),
            "information_transfer": ("Data Transfer", "#06b6d4"),
            "result": ("Task Findings", "#ec4899"),
            "escalation": ("Task Escalation", "#ef4444")
        }
        type_cur = conn.execute(
            "SELECT interaction_type, COUNT(*) as c FROM interactions GROUP BY interaction_type ORDER BY c DESC"
        )
        interaction_breakdown = []
        for r in type_cur.fetchall():
            itype = str(r[0])
            lbl, col = type_labels.get(itype, (itype.replace("_", " ").title(), "#94a3b8"))
            pct = round((r[1] / max(interactions_cnt, 1)) * 100, 1)
            interaction_breakdown.append({
                "type": itype,
                "label": lbl,
                "count": r[1],
                "percentage": pct,
                "color": col
            })

        # 4. Recent Workflows
        wf_cur = conn.execute(
            "SELECT workflow_id, name, task_description, dataset_name, mode, status, start_time, end_time, stats "
            "FROM workflow_runs ORDER BY start_time DESC LIMIT ?",
            (limit_workflows,)
        )
        recent_workflows = []
        for row in wf_cur.fetchall():
            row_dict = dict(row)
            stats_raw = row_dict.get("stats")
            stats_obj = {}
            if stats_raw:
                try:
                    stats_obj = json.loads(stats_raw) if isinstance(stats_raw, str) else stats_raw
                except Exception:
                    pass

            duration = None
            if row_dict.get("start_time") and row_dict.get("end_time"):
                try:
                    t1 = datetime.fromisoformat(row_dict["start_time"].replace("Z", "+00:00"))
                    t2 = datetime.fromisoformat(row_dict["end_time"].replace("Z", "+00:00"))
                    duration = round((t2 - t1).total_seconds(), 2)
                except Exception:
                    pass

            recent_workflows.append({
                "workflow_id": row_dict["workflow_id"],
                "name": row_dict.get("name") or row_dict.get("task_description", "")[:45],
                "task_description": row_dict.get("task_description", ""),
                "dataset_name": row_dict.get("dataset_name") or "customer_complaints.csv",
                "mode": row_dict.get("mode") or "deterministic_demo",
                "status": row_dict.get("status") or "completed",
                "start_time": row_dict.get("start_time"),
                "end_time": row_dict.get("end_time"),
                "duration_seconds": duration,
                "events_count": stats_obj.get("events_count", 0),
                "interactions_count": stats_obj.get("interactions_count", 0),
                "clarification_occurred": stats_obj.get("clarification_occurred", False),
                "escalation_occurred": stats_obj.get("escalation_occurred", False),
            })

        # 5. Live CIM Execution Event Stream
        ev_stream_cur = conn.execute(
            "SELECT event_id, time, delegation_id, principal_user_id, agent_id, tool_name, tool_operation, "
            "action_semantic, action_outcome, sensitivity_label, workflow_id "
            "FROM execution_events ORDER BY time DESC LIMIT ?",
            (limit_events,)
        )
        live_events = []
        for r in ev_stream_cur.fetchall():
            live_events.append(dict(r))

        # 6. Database Storage Stats
        from backend.config import settings
        db_file = Path(self.db_path or settings.DATABASE_PATH)
        file_size = db_file.stat().st_size if db_file.exists() else 0
        if file_size > 1024 * 1024:
            size_fmt = f"{file_size / (1024 * 1024):.2f} MB"
        else:
            size_fmt = f"{file_size / 1024:.1f} KB"

        return {
            "metrics": {
                "total_workflows": total_wf,
                "active_workflows": active_wf,
                "completed_workflows": completed_wf,
                "failed_workflows": failed_wf,
                "success_rate_pct": success_rate,
                "total_interactions": interactions_cnt,
                "total_events": events_cnt,
                "total_delegations": delegations_cnt,
                "total_retries": retries_cnt,
                "active_agents": agents_cnt,
            },
            "agent_breakdown": agent_breakdown,
            "interaction_breakdown": interaction_breakdown,
            "recent_workflows": recent_workflows,
            "live_event_stream": live_events,
            "storage": {
                "database_path": str(db_file),
                "file_size_bytes": file_size,
                "file_size_formatted": size_fmt,
                "journal_mode": "WAL",
            }
        }
