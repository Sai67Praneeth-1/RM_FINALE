"""
Deterministic & Live Multi-Agent Workflow Demo Script.
Demonstrates the complete end-to-end multi-agent execution,
Observability Gateway interception, and Three-Graph reconstruction.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.orchestration.workflow_runner import WorkflowRunner
from backend.schemas.workflow import WorkflowMode
from backend.schemas.events import CaptureLevel
from backend.agents.llm_client import is_gemini_available
from backend.storage.event_store import EventStore
from backend.graphs.three_graphs import ThreeGraphCoordinator

def main():
    print("================================================================================")
    print(" MULTI-AGENT TRANSPARENCY PLATFORM: END-TO-END DEMO")
    print("================================================================================")
    
    gemini_ok = is_gemini_available()
    mode = WorkflowMode.LIVE_GEMINI if gemini_ok else WorkflowMode.DETERMINISTIC_DEMO
    print(f"Inference Mode: {mode.value} (Gemini Available: {gemini_ok})")
    print(f"Capture Level: Level 2 (Metadata + Summary)")
    
    task = "Analyze customer complaints for High/Critical severity issues, request priority clarification from Coordinator, and generate executive report."
    dataset = "customer_complaints.csv"
    
    print(f"\nSubmitting Task: '{task}'")
    print(f"Target Dataset: {dataset}\n")
    
    runner = WorkflowRunner()
    run = runner.execute_workflow(
        task_description=task,
        dataset_name=dataset,
        mode=mode,
        capture_level=CaptureLevel.METADATA_SUMMARY
    )
    
    print("================================================================================")
    print(f" WORKFLOW EXECUTION STATUS: {run.status.upper()}")
    print("================================================================================")
    print(f"Workflow ID: {run.workflow_id}")
    print(f"Root Delegation ID: {run.root_delegation_id}")
    print(f"Telemetry Summary: {run.stats}")
    
    store = EventStore()
    coordinator = ThreeGraphCoordinator(store)
    graphs = coordinator.get_graphs_for_workflow(run.workflow_id)
    
    print("\n--- THREE-GRAPH TRANSPARENCY MODEL RECONSTRUCTION ---")
    print(f"1. Execution Graph (G_exec):    {len(graphs['execution_graph'].nodes)} tool events, {len(graphs['execution_graph'].edges)} causal links")
    print(f"2. Authority Graph (G_auth):    {len(graphs['authority_graph'].nodes)} authority nodes, {len(graphs['authority_graph'].edges)} delegation links")
    print(f"3. Interaction Graph (G_inter): {len(graphs['interaction_graph'].nodes)} agent nodes, {len(graphs['interaction_graph'].edges)} genuine inter-agent messages")
    
    print("\n--- SYNTHESIZED REPORT PREVIEW ---")
    if run.final_output:
        lines = run.final_output.split("\n")
        print("\n".join(lines[:25]))
        print("...\n[Truncated for console display. Full report available in SQLite / Dashboard]")
    print("================================================================================")

if __name__ == "__main__":
    main()

