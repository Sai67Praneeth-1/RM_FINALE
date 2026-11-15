"""
Workflow Runner providing unified execution for live LLM and deterministic modes.
Manages workflow state lifecycle, LangGraph streaming execution, and SQLite persistence.
Supports multiple research workflow topologies (Adaptive, W1 Parallel, W3 Retry).
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Iterator
from backend.schemas.workflow import WorkflowRun, WorkflowMode
from backend.schemas.events import CaptureLevel
from backend.gateway.gateway import ObservabilityGateway, default_gateway
from backend.orchestration.langgraph_workflow import (
    build_multi_agent_graph,
    get_langgraph_mermaid,
    get_langgraph_topology_dot,
    get_available_workflow_topologies
)
from backend.agents.llm_client import is_ollama_available

class WorkflowRunner:
    def __init__(self, gateway: Optional[ObservabilityGateway] = None):
        self.gateway = gateway or default_gateway
        self._compiled_graphs: Dict[str, Any] = {}

    def get_graph(self, workflow_type: str = "adaptive"):
        """Returns or lazily compiles the requested LangGraph workflow topology."""
        wt = (workflow_type or "adaptive").lower()
        if wt not in self._compiled_graphs:
            self._compiled_graphs[wt] = build_multi_agent_graph(self.gateway, workflow_type=wt)
        return self._compiled_graphs[wt]

    def execute_workflow(
        self,
        task_description: str,
        dataset_name: str = "customer_complaints.csv",
        principal_id: str = "principal_alice",
        mode: Optional[WorkflowMode] = None,
        capture_level: Optional[CaptureLevel] = None,
        workflow_type: str = "adaptive"
    ) -> WorkflowRun:
        """
        Executes the LangGraph multi-agent workflow, tracking node transitions and persisting telemetry.
        """
        workflow_id = f"wf_{uuid.uuid4().hex[:10]}"
        conv_id = f"conv_{uuid.uuid4().hex[:8]}"
        
        selected_mode = mode or WorkflowMode.DETERMINISTIC_DEMO

        active_capture_level = capture_level or self.gateway.capture_level
        self.gateway.set_capture_level(active_capture_level)

        wf_record = WorkflowRun(
            workflow_id=workflow_id,
            name=f"Investigation ({workflow_type}): {task_description[:35]}...",
            task_description=task_description,
            dataset_name=dataset_name,
            mode=selected_mode,
            capture_level=active_capture_level,
            status="running",
            start_time=datetime.now(timezone.utc).isoformat()
        )
        self.gateway.store.save_workflow_run(wf_record)

        initial_state = {
            "workflow_id": workflow_id,
            "task_description": task_description,
            "dataset_name": dataset_name,
            "principal_id": principal_id,
            "conversation_id": conv_id,
            "mode": selected_mode.value,
            "capture_level": active_capture_level.value,
            "workflow_type": workflow_type,
            "root_delegation_id": None,
            "research_delegation_id": None,
            "analysis_delegation_id": None,
            "report_delegation_id": None,
            "research_data": None,
            "secondary_data": None,
            "analysis_data": None,
            "report_data": None,
            "clarification_requested": False,
            "clarification_resolved": False,
            "escalation_triggered": False,
            "escalation_resolved": False,
            "retry_count": 0,
            "max_retries": 2,
            "backtrack_occurred": False,
            "node_history": [],
            "active_node": None,
            "errors": [],
            "status": "started",
            "final_output": None
        }

        graph = self.get_graph(workflow_type)
        thread_config = {"configurable": {"thread_id": workflow_id}}
        node_history = []
        final_state = dict(initial_state)

        try:
            # Stream execution through LangGraph so node transitions are captured step-by-step
            for step_event in graph.stream(initial_state, config=thread_config):
                for node_name, state_update in step_event.items():
                    node_history.append(node_name)
                    if isinstance(state_update, dict):
                        final_state.update(state_update)

            wf_record.status = final_state.get("status", "completed")
            wf_record.end_time = datetime.now(timezone.utc).isoformat()
            wf_record.root_delegation_id = final_state.get("root_delegation_id")
            wf_record.final_output = final_state.get("final_output")
            
            if final_state.get("errors"):
                wf_record.error_message = "; ".join(final_state.get("errors", []))

            events = self.gateway.store.list_execution_events(workflow_id=workflow_id)
            interactions = self.gateway.store.list_interactions(conversation_id=conv_id)
            
            wf_record.stats = {
                "events_count": len(events),
                "interactions_count": len(interactions),
                "clarification_occurred": final_state.get("clarification_requested", False),
                "escalation_occurred": final_state.get("escalation_triggered", False),
                "retry_count": final_state.get("retry_count", 0),
                "node_history": node_history,
                "workflow_type": workflow_type,
                "active_agents": ["agent_coordinator", "agent_researcher", "agent_analyst", "agent_reporter"]
            }

        except Exception as e:
            wf_record.status = "failed"
            wf_record.end_time = datetime.now(timezone.utc).isoformat()
            wf_record.error_message = str(e)
            
        self.gateway.store.save_workflow_run(wf_record)
        return wf_record

    def stream_workflow(
        self,
        task_description: str,
        dataset_name: str = "customer_complaints.csv",
        principal_id: str = "principal_alice",
        mode: Optional[WorkflowMode] = None,
        capture_level: Optional[CaptureLevel] = None,
        workflow_type: str = "adaptive"
    ) -> Iterator[Dict[str, Any]]:
        """
        Generator yielding real-time node transitions as LangGraph executes them.
        """
        workflow_id = f"wf_{uuid.uuid4().hex[:10]}"
        conv_id = f"conv_{uuid.uuid4().hex[:8]}"
        
        selected_mode = mode or WorkflowMode.DETERMINISTIC_DEMO
        active_capture_level = capture_level or self.gateway.capture_level
        self.gateway.set_capture_level(active_capture_level)

        initial_state = {
            "workflow_id": workflow_id,
            "task_description": task_description,
            "dataset_name": dataset_name,
            "principal_id": principal_id,
            "conversation_id": conv_id,
            "mode": selected_mode.value,
            "capture_level": active_capture_level.value,
            "workflow_type": workflow_type,
            "root_delegation_id": None,
            "research_delegation_id": None,
            "analysis_delegation_id": None,
            "report_delegation_id": None,
            "research_data": None,
            "secondary_data": None,
            "analysis_data": None,
            "report_data": None,
            "clarification_requested": False,
            "clarification_resolved": False,
            "escalation_triggered": False,
            "escalation_resolved": False,
            "retry_count": 0,
            "max_retries": 2,
            "backtrack_occurred": False,
            "node_history": [],
            "active_node": None,
            "errors": [],
            "status": "started",
            "final_output": None
        }

        graph = self.get_graph(workflow_type)
        thread_config = {"configurable": {"thread_id": workflow_id}}
        
        for step_event in graph.stream(initial_state, config=thread_config):
            yield {
                "workflow_id": workflow_id,
                "step_event": step_event
            }
