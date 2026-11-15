"""
Deterministic Synthetic Workload Generator for Research Evaluation.
Generates known ground-truth events, delegations, and interactions
for all 8 experimental scenarios specified in PPT Slide 13.
Ensures evaluation is fully reproducible and independent of LLM non-determinism.
"""

import random
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta
from backend.schemas.events import (
    CIMEvent, ActionSemantic, ActionOutcome, Direction, PrincipalScope,
    ResourceClass, SensitivityLabel, InteractionType, CaptureLevel
)
from backend.schemas.interaction import InteractionRecord
from backend.schemas.workflow import DelegationRecord, ProvenanceEdge

class SyntheticWorkloadGenerator:
    """
    Generates synthetic benchmark workloads with independent ground truth.
    Scenarios:
    1. Single-agent baseline
    2. Two-agent communication
    3. Multi-agent delegation
    4. Parallel interactions
    5. Retry and backtracking
    6. Multi-hop information transfer
    7. Partial or missing telemetry
    8. Sensitive-information flow
    """
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)

    def generate_scenario(self, scenario_id: int, size: int = 50) -> Dict[str, Any]:
        """Dispatches to one of the 8 experimental scenarios."""
        handlers = {
            1: self._gen_single_agent,
            2: self._gen_two_agent,
            3: self._gen_multi_agent_delegation,
            4: self._gen_parallel_interactions,
            5: self._gen_retry_backtracking,
            6: self._gen_multi_hop_transfer,
            7: self._gen_partial_telemetry,
            8: self._gen_sensitive_flow
        }
        handler = handlers.get(scenario_id, self._gen_single_agent)
        return handler(size)

    # -------------------------------------------------------------
    # Scenario 1: Single-agent baseline
    # -------------------------------------------------------------
    def _gen_single_agent(self, size: int) -> Dict[str, Any]:
        base_time = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
        del_id = "del_synth_s1"
        prin_id = "principal_single"
        agent_id = "agent_coordinator"
        trace_id = "trc_s1"
        
        delegation = DelegationRecord(
            delegation_id=del_id,
            principal_id=prin_id,
            agent_id=agent_id,
            task_id="task_s1_single",
            scope="single_agent_workload"
        )
        
        events = []
        for i in range(size):
            t = (base_time + timedelta(seconds=i * 2)).isoformat()
            ev = CIMEvent(
                event_id=f"evt_s1_{i}",
                time=t,
                delegation_id=del_id,
                principal_user_id=prin_id,
                agent_id=agent_id,
                tool_name="local_db",
                tool_operation="fetch_row",
                action_semantic=ActionSemantic.READ,
                action_outcome=ActionOutcome.SUCCESS,
                resource_type=ResourceClass.DATASET,
                resource_id=f"table_partition_{i % 5}",
                sensitivity_label=SensitivityLabel.INTERNAL,
                trace_id=trace_id,
                span_id=f"spn_s1_{i}",
                workflow_id="wf_s1"
            )
            events.append(ev)

        return {
            "scenario_name": "1. Single-agent baseline",
            "delegations": [delegation],
            "interactions": [], # No inter-agent communication
            "events": events,
            "ground_truth": {
                "delegation_count": 1,
                "interaction_count": 0,
                "event_count": len(events),
                "event_delegation_map": {e.event_id: del_id for e in events}
            }
        }

    # -------------------------------------------------------------
    # Scenario 2: Two-agent communication
    # -------------------------------------------------------------
    def _gen_two_agent(self, size: int) -> Dict[str, Any]:
        base_time = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
        del_root = "del_synth_s2_root"
        del_child = "del_synth_s2_child"
        
        del_records = [
            DelegationRecord(delegation_id=del_root, principal_id="user_s2", agent_id="agent_coordinator", task_id="task_s2_root"),
            DelegationRecord(delegation_id=del_child, delegation_parent_id=del_root, principal_id="user_s2", agent_id="agent_researcher", task_id="task_s2_child")
        ]
        
        interactions = []
        events = []
        
        for i in range(size // 2):
            t_req = (base_time + timedelta(seconds=i * 10)).isoformat()
            t_resp = (base_time + timedelta(seconds=i * 10 + 3)).isoformat()
            
            # Interaction: Request from Coordinator to Researcher
            req = InteractionRecord(
                interaction_id=f"itr_s2_req_{i}",
                timestamp=t_req,
                sender_agent_id="agent_coordinator",
                receiver_agent_id="agent_researcher",
                interaction_type=InteractionType.REQUEST,
                conversation_id="conv_s2",
                task_id="task_s2_child",
                delegation_id=del_child,
                semantic_summary=f"Requesting data block {i}",
                content=f"Query dataset chunk {i} for review",
                capture_level=CaptureLevel.FULL_CONTENT
            )
            interactions.append(req)
            
            # Tool event by Researcher
            ev = CIMEvent(
                event_id=f"evt_s2_tool_{i}",
                time=t_resp,
                delegation_id=del_child,
                principal_user_id="user_s2",
                agent_id="agent_researcher",
                tool_name="data_store",
                tool_operation="read_block",
                action_semantic=ActionSemantic.READ,
                resource_type=ResourceClass.DATASET,
                resource_id=f"chunk_{i}",
                trace_id=f"trc_s2_{i}",
                span_id=f"spn_s2_{i}",
                workflow_id="wf_s2"
            )
            events.append(ev)
            
            # Interaction: Response from Researcher to Coordinator
            resp = InteractionRecord(
                interaction_id=f"itr_s2_resp_{i}",
                timestamp=t_resp,
                sender_agent_id="agent_researcher",
                receiver_agent_id="agent_coordinator",
                interaction_type=InteractionType.RESPONSE,
                conversation_id="conv_s2",
                task_id="task_s2_child",
                delegation_id=del_child,
                reply_to_message_id=req.message_id,
                semantic_summary=f"Delivered data block {i}",
                downstream_action_ids=[ev.event_id],
                capture_level=CaptureLevel.FULL_CONTENT
            )
            interactions.append(resp)

        return {
            "scenario_name": "2. Two-agent communication",
            "delegations": del_records,
            "interactions": interactions,
            "events": events,
            "ground_truth": {
                "delegation_count": 2,
                "interaction_count": len(interactions),
                "event_count": len(events),
                "event_delegation_map": {e.event_id: del_child for e in events}
            }
        }

    # -------------------------------------------------------------
    # Scenario 3: Multi-agent delegation
    # -------------------------------------------------------------
    def _gen_multi_agent_delegation(self, size: int) -> Dict[str, Any]:
        base_time = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
        d_root = "del_s3_root"
        d_res = "del_s3_research"
        d_ana = "del_s3_analysis"
        d_rep = "del_s3_report"
        
        delegations = [
            DelegationRecord(delegation_id=d_root, principal_id="user_s3", agent_id="agent_coordinator", task_id="task_s3_root"),
            DelegationRecord(delegation_id=d_res, delegation_parent_id=d_root, principal_id="user_s3", agent_id="agent_researcher", task_id="task_s3_res"),
            DelegationRecord(delegation_id=d_ana, delegation_parent_id=d_root, principal_id="user_s3", agent_id="agent_analyst", task_id="task_s3_ana"),
            DelegationRecord(delegation_id=d_rep, delegation_parent_id=d_root, principal_id="user_s3", agent_id="agent_reporter", task_id="task_s3_rep")
        ]
        
        interactions = []
        events = []
        
        # Coordinator delegates to each
        for i, (agent, did) in enumerate([("agent_researcher", d_res), ("agent_analyst", d_ana), ("agent_reporter", d_rep)]):
            t = (base_time + timedelta(seconds=i * 5)).isoformat()
            itr = InteractionRecord(
                interaction_id=f"itr_s3_del_{i}",
                timestamp=t,
                sender_agent_id="agent_coordinator",
                receiver_agent_id=agent,
                interaction_type=InteractionType.DELEGATION,
                conversation_id="conv_s3",
                task_id=f"task_s3_{i}",
                delegation_id=did,
                delegation_parent_id=d_root,
                semantic_summary=f"Delegated subtask {i} to {agent}"
            )
            interactions.append(itr)
            
            # Agent emits tools under their delegation
            for k in range(size // 4):
                ev = CIMEvent(
                    event_id=f"evt_s3_{agent}_{k}",
                    time=(base_time + timedelta(seconds=i * 10 + k * 2)).isoformat(),
                    delegation_id=did,
                    delegation_parent_id=d_root,
                    principal_user_id="user_s3",
                    agent_id=agent,
                    tool_name=f"tool_{agent}",
                    tool_operation="process",
                    action_semantic=ActionSemantic.INVOKE,
                    resource_type=ResourceClass.DOCUMENT,
                    resource_id=f"doc_{agent}_{k}",
                    trace_id=f"trc_s3_{agent}",
                    workflow_id="wf_s3"
                )
                events.append(ev)

        return {
            "scenario_name": "3. Multi-agent delegation",
            "delegations": delegations,
            "interactions": interactions,
            "events": events,
            "ground_truth": {
                "delegation_count": len(delegations),
                "interaction_count": len(interactions),
                "event_count": len(events),
                "event_delegation_map": {e.event_id: e.delegation_id for e in events}
            }
        }

    # -------------------------------------------------------------
    # Scenario 4: Parallel interactions (Concurrently overlapping traces)
    # -------------------------------------------------------------
    def _gen_parallel_interactions(self, size: int) -> Dict[str, Any]:
        base_time = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
        d_par1 = "del_s4_worker1"
        d_par2 = "del_s4_worker2"
        
        delegations = [
            DelegationRecord(delegation_id=d_par1, principal_id="user_p1", agent_id="agent_researcher", task_id="task_p1"),
            DelegationRecord(delegation_id=d_par2, principal_id="user_p2", agent_id="agent_analyst", task_id="task_p2")
        ]
        
        interactions = []
        events = []
        
        # Parallel interleaved execution
        for i in range(size // 2):
            t1 = (base_time + timedelta(milliseconds=i * 500)).isoformat()
            t2 = (base_time + timedelta(milliseconds=i * 500 + 50)).isoformat()
            
            # Worker 1 event
            e1 = CIMEvent(
                event_id=f"evt_p1_{i}",
                time=t1,
                delegation_id=d_par1,
                principal_user_id="user_p1",
                agent_id="agent_researcher",
                tool_name="db_search",
                tool_operation="query",
                action_semantic=ActionSemantic.SEARCH,
                resource_type=ResourceClass.DATASET,
                resource_id=f"shard_a_{i}",
                trace_id="trc_parallel_1",
                workflow_id="wf_s4"
            )
            # Worker 2 event
            e2 = CIMEvent(
                event_id=f"evt_p2_{i}",
                time=t2,
                delegation_id=d_par2,
                principal_user_id="user_p2",
                agent_id="agent_analyst",
                tool_name="cache_lookup",
                tool_operation="get",
                action_semantic=ActionSemantic.READ,
                resource_type=ResourceClass.DATASET,
                resource_id=f"shard_b_{i}",
                trace_id="trc_parallel_2",
                workflow_id="wf_s4"
            )
            events.extend([e1, e2])

        return {
            "scenario_name": "4. Parallel interactions",
            "delegations": delegations,
            "interactions": interactions,
            "events": events,
            "ground_truth": {
                "delegation_count": 2,
                "interaction_count": 0,
                "event_count": len(events),
                "event_delegation_map": {e.event_id: e.delegation_id for e in events}
            }
        }

    # -------------------------------------------------------------
    # Scenario 5: Retry and backtracking
    # -------------------------------------------------------------
    def _gen_retry_backtracking(self, size: int) -> Dict[str, Any]:
        base_time = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
        did = "del_s5_retry"
        delegations = [
            DelegationRecord(delegation_id=did, principal_id="user_s5", agent_id="agent_analyst", task_id="task_retry")
        ]
        
        interactions = []
        events = []
        
        for i in range(size // 3):
            # Attempt 1: Failed
            t1 = (base_time + timedelta(seconds=i * 15)).isoformat()
            e_fail = CIMEvent(
                event_id=f"evt_fail_{i}",
                time=t1,
                delegation_id=did,
                principal_user_id="user_s5",
                agent_id="agent_analyst",
                tool_name="remote_calculator",
                tool_operation="compute",
                action_semantic=ActionSemantic.INVOKE,
                action_outcome=ActionOutcome.FAILURE,
                resource_type=ResourceClass.DATASET,
                resource_id=f"metric_{i}",
                trace_id=f"trc_try_{i}_1",
                workflow_id="wf_s5"
            )
            events.append(e_fail)
            
            # Warning/Retry Interaction
            itr_retry = InteractionRecord(
                interaction_id=f"itr_retry_{i}",
                timestamp=t1,
                sender_agent_id="agent_analyst",
                receiver_agent_id="agent_coordinator",
                interaction_type=InteractionType.WARNING,
                conversation_id="conv_s5",
                task_id="task_retry",
                delegation_id=did,
                semantic_summary=f"Tool timeout on metric_{i}, initiating retry attempt 2.",
                status="retried",
                retry_count=1
            )
            interactions.append(itr_retry)
            
            # Attempt 2: Success (backtracked)
            t2 = (base_time + timedelta(seconds=i * 15 + 4)).isoformat()
            e_succ = CIMEvent(
                event_id=f"evt_succ_{i}",
                time=t2,
                delegation_id=did,
                principal_user_id="user_s5",
                agent_id="agent_analyst",
                tool_name="remote_calculator",
                tool_operation="compute",
                action_semantic=ActionSemantic.INVOKE,
                action_outcome=ActionOutcome.SUCCESS,
                resource_type=ResourceClass.DATASET,
                resource_id=f"metric_{i}",
                trace_id=f"trc_try_{i}_2", # Different trace!
                workflow_id="wf_s5"
            )
            events.append(e_succ)

        return {
            "scenario_name": "5. Retry and backtracking",
            "delegations": delegations,
            "interactions": interactions,
            "events": events,
            "ground_truth": {
                "delegation_count": 1,
                "interaction_count": len(interactions),
                "event_count": len(events),
                "retries": len(interactions),
                "event_delegation_map": {e.event_id: did for e in events}
            }
        }

    # -------------------------------------------------------------
    # Scenario 6: Multi-hop information transfer
    # -------------------------------------------------------------
    def _gen_multi_hop_transfer(self, size: int) -> Dict[str, Any]:
        base_time = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
        did = "del_s6_multihop"
        delegations = [
            DelegationRecord(delegation_id=did, principal_id="user_s6", agent_id="agent_coordinator", task_id="task_multihop")
        ]
        
        interactions = []
        events = []
        
        # Sequence: Coord -> Researcher -> Analyst -> Reporter
        agents = ["agent_coordinator", "agent_researcher", "agent_analyst", "agent_reporter"]
        types = [InteractionType.DELEGATION, InteractionType.INFORMATION_TRANSFER, InteractionType.RESULT]
        
        for k in range(max(1, size // 10)):
            prev_msg_id = None
            for hop in range(3):
                t = (base_time + timedelta(seconds=k * 30 + hop * 5)).isoformat()
                sender = agents[hop]
                receiver = agents[hop + 1]
                itype = types[hop]
                
                # Emit intermediate tool action
                ev = CIMEvent(
                    event_id=f"evt_hop_{k}_{hop}",
                    time=t,
                    delegation_id=did,
                    principal_user_id="user_s6",
                    agent_id=sender,
                    tool_name=f"tool_{sender}",
                    tool_operation="transform",
                    action_semantic=ActionSemantic.INVOKE,
                    resource_type=ResourceClass.DATASET,
                    resource_id=f"data_hop_{k}_{hop}",
                    trace_id=f"trc_hop_{k}_{hop}",
                    workflow_id="wf_s6"
                )
                events.append(ev)
                
                itr = InteractionRecord(
                    interaction_id=f"itr_hop_{k}_{hop}",
                    timestamp=t,
                    sender_agent_id=sender,
                    receiver_agent_id=receiver,
                    interaction_type=itype,
                    conversation_id=f"conv_s6_{k}",
                    task_id="task_multihop",
                    delegation_id=did,
                    reply_to_message_id=prev_msg_id,
                    semantic_summary=f"Hop {hop+1}: Transferred data from {sender} to {receiver}",
                    downstream_action_ids=[ev.event_id],
                    provenance_refs=[f"data_hop_{k}_{hop}"]
                )
                interactions.append(itr)
                prev_msg_id = itr.message_id

        return {
            "scenario_name": "6. Multi-hop information transfer",
            "delegations": delegations,
            "interactions": interactions,
            "events": events,
            "ground_truth": {
                "delegation_count": 1,
                "interaction_count": len(interactions),
                "event_count": len(events),
                "hop_count": 3,
                "event_delegation_map": {e.event_id: did for e in events}
            }
        }

    # -------------------------------------------------------------
    # Scenario 7: Partial or missing telemetry (Coverage blindspots)
    # -------------------------------------------------------------
    def _gen_partial_telemetry(self, size: int) -> Dict[str, Any]:
        base_time = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
        did = "del_s7_partial"
        delegations = [
            DelegationRecord(delegation_id=did, principal_id="user_s7", agent_id="agent_coordinator", task_id="task_partial")
        ]
        
        events = []
        ground_truth_map = {}
        
        # 70% instrumented, 30% uninstrumented / missing trace
        for i in range(size):
            t = (base_time + timedelta(seconds=i * 2)).isoformat()
            is_instrumented = (i % 10) < 7
            
            ev = CIMEvent(
                event_id=f"evt_s7_{i}",
                time=t,
                delegation_id=did if is_instrumented else "unbound_missing",
                principal_user_id="user_s7",
                agent_id="agent_researcher",
                tool_name="uninstrumented_api" if not is_instrumented else "audited_db",
                tool_operation="call",
                action_semantic=ActionSemantic.READ,
                resource_type=ResourceClass.DATASET,
                resource_id=f"item_{i}",
                trace_id=f"trc_s7_{i}" if is_instrumented else None, # Missing trace
                labels={"coverage": "instrumented" if is_instrumented else "uninstrumented_bypass"}
            )
            events.append(ev)
            ground_truth_map[ev.event_id] = did # Ground truth is that all belonged to did

        return {
            "scenario_name": "7. Partial or missing telemetry",
            "delegations": delegations,
            "interactions": [],
            "events": events,
            "ground_truth": {
                "delegation_count": 1,
                "event_count": len(events),
                "covered_events": int(size * 0.7),
                "uncovered_events": int(size * 0.3),
                "event_delegation_map": ground_truth_map
            }
        }

    # -------------------------------------------------------------
    # Scenario 8: Sensitive-information flow
    # -------------------------------------------------------------
    def _gen_sensitive_flow(self, size: int) -> Dict[str, Any]:
        base_time = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
        did = "del_s8_sensitive"
        delegations = [
            DelegationRecord(delegation_id=did, principal_id="compliance_officer", agent_id="agent_coordinator", task_id="task_confidential")
        ]
        
        interactions = []
        events = []
        
        # Mix of Public, Internal, Confidential, and Restricted resources
        sensitivities = [SensitivityLabel.INTERNAL, SensitivityLabel.CONFIDENTIAL, SensitivityLabel.RESTRICTED, SensitivityLabel.PUBLIC]
        
        for i in range(size // 2):
            t = (base_time + timedelta(seconds=i * 4)).isoformat()
            sens = sensitivities[i % len(sensitivities)]
            
            ev = CIMEvent(
                event_id=f"evt_s8_{i}",
                time=t,
                delegation_id=did,
                principal_user_id="compliance_officer",
                agent_id="agent_analyst",
                tool_name="vault_service",
                tool_operation="read_secret",
                action_semantic=ActionSemantic.READ,
                resource_type=ResourceClass.DOCUMENT,
                resource_id=f"sec_doc_{i}",
                sensitivity_label=sens,
                direction=Direction.INTERNAL,
                workflow_id="wf_s8"
            )
            events.append(ev)
            
            raw_payload = f"Confidential employee record: email=john.doe{i}@enterprise.com, ssn=123-45-{1000+i}, score=0.88"
            itr = InteractionRecord(
                interaction_id=f"itr_s8_{i}",
                timestamp=t,
                sender_agent_id="agent_analyst",
                receiver_agent_id="agent_reporter",
                interaction_type=InteractionType.INFORMATION_TRANSFER,
                conversation_id="conv_s8",
                task_id="task_confidential",
                delegation_id=did,
                semantic_summary=f"Transferred audit findings for record {i}",
                content=raw_payload,
                sensitivity_label=sens,
                resource_refs=[f"sec_doc_{i}"],
                capture_level=CaptureLevel.FULL_CONTENT
            )
            interactions.append(itr)

        return {
            "scenario_name": "8. Sensitive-information flow",
            "delegations": delegations,
            "interactions": interactions,
            "events": events,
            "ground_truth": {
                "delegation_count": 1,
                "interaction_count": len(interactions),
                "event_count": len(events),
                "sensitive_event_count": len([e for e in events if e.sensitivity_label in (SensitivityLabel.CONFIDENTIAL, SensitivityLabel.RESTRICTED)]),
                "event_delegation_map": {e.event_id: did for e in events}
            }
        }

