"""
Cross-Graph Invariant Validator (Topics 5, 6, 7).
Validates structural invariants across:
1. G_exec (Execution Graph - Topic 6)
2. G_auth (Authority / Lineage Graph - Topic 7)
3. G_interact (Interaction Graph - Topic 5)

Invariants validated:
- Invariant 1 (Authority Coverage): For every execution event in G_exec, check if its delegation_id
  exists in delegation_records table.
- Invariant 2 (Interaction-Execution Links): For every interaction record with non-empty downstream_action_ids,
  check each action_id exists in execution_events.
- Invariant 3 (Temporal Validity): For every execution event, check that delegation.issued_at <= event.time
  and if delegation.completed_at is set it's >= event.time.
- Comp(d): Authority-causality alignment score (passed_count / total_events).
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.storage.event_store import EventStore


def _parse_ts(val: Any) -> Optional[datetime]:
    """Parses ISO timestamp string or numeric timestamp to timezone-aware UTC datetime."""
    if not val:
        return None
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val, tz=timezone.utc)
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val
    try:
        s = str(val).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


class CrossGraphValidator:
    def __init__(self, event_store: EventStore):
        self.store = event_store

    def validate_authority_coverage(self, workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Invariant 1: For every execution event in G_exec, check if its delegation_id
        exists in delegations (delegation_records) table.
        Return shape: {passed, failed, score, violations: [{event_id, reason}]}
        """
        events = self.store.list_execution_events(workflow_id=workflow_id, limit=2000)

        conn = self.store._conn()
        cur = conn.execute("SELECT delegation_id FROM delegations")
        valid_delegation_ids = {row[0] for row in cur.fetchall() if row[0]}

        passed = 0
        failed = 0
        violations: List[Dict[str, str]] = []

        for ev in events:
            if not ev.delegation_id:
                failed += 1
                violations.append({
                    "event_id": ev.event_id,
                    "reason": "Missing delegation_id in execution event"
                })
            elif ev.delegation_id not in valid_delegation_ids:
                failed += 1
                violations.append({
                    "event_id": ev.event_id,
                    "reason": f"delegation_id '{ev.delegation_id}' does not exist in delegations table"
                })
            else:
                passed += 1

        total = passed + failed
        score = 1.0 if total == 0 else round(passed / total, 4)

        return {
            "passed": passed,
            "failed": failed,
            "score": score,
            "violations": violations
        }

    def validate_interaction_execution_links(self, workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Invariant 2: For every interaction record with non-empty downstream_action_ids,
        check each action_id exists in execution_events and satisfies temporal causality (Finding 6).
        Return shape: {passed, failed, score, violations: [{event_id, reason}]}
        """
        interactions = self.store.list_interactions(workflow_id=workflow_id, limit=2000)

        conn = self.store._conn()
        cur = conn.execute("SELECT event_id, time FROM execution_events")
        event_time_map = {row[0]: row[1] for row in cur.fetchall() if row[0]}

        passed = 0
        failed = 0
        violations: List[Dict[str, str]] = []

        for rec in interactions:
            action_ids = rec.downstream_action_ids or []
            if not action_ids:
                continue

            for action_id in action_ids:
                if action_id not in event_time_map:
                    failed += 1
                    violations.append({
                        "event_id": action_id,
                        "interaction_id": rec.interaction_id,
                        "reason": f"Downstream action_id '{action_id}' not found in execution_events table"
                    })
                else:
                    event_time_str = event_time_map[action_id]
                    try:
                        ev_dt = datetime.fromisoformat(event_time_str.replace("Z", "+00:00"))
                        itr_dt = datetime.fromisoformat(rec.timestamp.replace("Z", "+00:00"))
                        # Temporal causality: downstream event should occur at or after triggering interaction
                        if (itr_dt - ev_dt).total_seconds() > 0.05:
                            failed += 1
                            violations.append({
                                "event_id": action_id,
                                "interaction_id": rec.interaction_id,
                                "reason": f"Temporal causality inversion: downstream event '{action_id}' ({event_time_str}) occurred before interaction '{rec.interaction_id}' ({rec.timestamp})"
                            })
                            continue
                    except Exception:
                        pass
                    passed += 1

        total = passed + failed
        score = 1.0 if total == 0 else round(passed / total, 4)

        return {
            "passed": passed,
            "failed": failed,
            "score": score,
            "violations": violations
        }

    def validate_temporal_validity(self, workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Invariant 3: For every execution event, check that delegation.issued_at <= event.time
        and if delegation.completed_at is set it's >= event.time.
        Return shape: {passed, failed, score, violations: [{event_id, reason}]}
        """
        events = self.store.list_execution_events(workflow_id=workflow_id, limit=2000)

        conn = self.store._conn()
        cur = conn.execute("SELECT delegation_id, issued_at, completed_at FROM delegations")
        del_map = {row["delegation_id"]: dict(row) for row in cur.fetchall() if row["delegation_id"]}

        passed = 0
        failed = 0
        violations: List[Dict[str, str]] = []

        for ev in events:
            if not ev.delegation_id or ev.delegation_id not in del_map:
                failed += 1
                violations.append({
                    "event_id": ev.event_id,
                    "reason": f"Authorizing delegation '{ev.delegation_id}' not found for temporal validation"
                })
                continue

            del_info = del_map[ev.delegation_id]
            ev_dt = _parse_ts(ev.time)
            issued_dt = _parse_ts(del_info.get("issued_at"))
            completed_dt = _parse_ts(del_info.get("completed_at"))

            if not ev_dt or not issued_dt:
                failed += 1
                violations.append({
                    "event_id": ev.event_id,
                    "reason": f"Unparseable timestamps: event.time='{ev.time}', delegation.issued_at='{del_info.get('issued_at')}'"
                })
                continue

            if issued_dt > ev_dt:
                failed += 1
                violations.append({
                    "event_id": ev.event_id,
                    "reason": f"Event time ({ev.time}) occurred before delegation issued_at ({del_info.get('issued_at')})"
                })
            elif completed_dt and completed_dt < ev_dt:
                failed += 1
                violations.append({
                    "event_id": ev.event_id,
                    "reason": f"Event time ({ev.time}) occurred after delegation completed_at ({del_info.get('completed_at')})"
                })
            else:
                passed += 1

        total = passed + failed
        score = 1.0 if total == 0 else round(passed / total, 4)

        return {
            "passed": passed,
            "failed": failed,
            "score": score,
            "violations": violations
        }

    def compute_comp_d(self, workflow_id: Optional[str] = None) -> float:
        """
        Authority-causality alignment score: passed_count / total_events.
        """
        cov = self.validate_authority_coverage(workflow_id)
        total = cov["passed"] + cov["failed"]
        if total == 0:
            return 1.0
        return round(cov["passed"] / total, 4)

    def run_full_validation(self, workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Runs all 3 invariants + comp_d.
        Returns full report with:
        {
            "workflow_id": workflow_id,
            "validation_timestamp": ISO-8601 string,
            "total_events": int,
            "invariant_1_authority_coverage": Dict,
            "invariant_2_interaction_execution_links": Dict,
            "invariant_3_temporal_validity": Dict,
            "comp_d": float,
            "overall_status": "PASS" | "PARTIAL_VIOLATIONS"
        }
        overall_status = "PASS" if all scores == 1.0, "PARTIAL_VIOLATIONS" if any < 1.0.
        """
        inv1 = self.validate_authority_coverage(workflow_id)
        inv2 = self.validate_interaction_execution_links(workflow_id)
        inv3 = self.validate_temporal_validity(workflow_id)
        comp_d = self.compute_comp_d(workflow_id)

        events = self.store.list_execution_events(workflow_id=workflow_id, limit=2000)
        total_events = len(events)

        scores = [inv1["score"], inv2["score"], inv3["score"]]
        overall_status = "PASS" if all(s == 1.0 for s in scores) else "PARTIAL_VIOLATIONS"

        return {
            "workflow_id": workflow_id or "",
            "validation_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_events": total_events,
            "invariant_1_authority_coverage": inv1,
            "invariant_2_interaction_execution_links": inv2,
            "invariant_3_temporal_validity": inv3,
            "comp_d": comp_d,
            "overall_status": overall_status
        }
