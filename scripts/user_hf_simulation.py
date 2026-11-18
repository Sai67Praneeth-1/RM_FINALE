"""
Goal-Oriented Multi-Agent Research Simulation powered by Google Gemini.
Executes dynamic multi-agent interaction between specialized agents (Coordinator, Executor, Critic, Synthesizer).
"""

import os
import re
import sys
from dotenv import load_dotenv
from openai import OpenAI

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env")))

# Ensure token works directly in os.environ lookup
HF_TOKEN_VALUE = os.environ.get("HF_TOKEN") or os.environ.get("HF_API_KEY", "")

# Initialize the Hugging Face router client
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN_VALUE,
    timeout=5.0
)

from backend.orchestration.hf_simulation import run_huggingface_transparency_simulation
from backend.agents.llm_client import strip_internal_reasoning, run_agent_turn

# --- Configuration ---
# --- 4-Agent Research Team Configuration ---
agents = [
    {
        "name": "Coordinator_Agent",
        "agent_id": "agent_coordinator",
        "model": "gemini-3.5-flash",
        "prompt": "You are a Project Coordinator managing a technical research task. Keep responses focused on macro-level objectives, delegation, and structure."
    },
    {
        "name": "Executor_Agent",
        "agent_id": "agent_executor",
        "model": "gemini-3.5-flash",
        "prompt": "You are a Technical Executor. Provide concrete implementation steps, code logic, or architectural solutions based on the ongoing discussion."
    },
    {
        "name": "Critic_Agent",
        "agent_id": "agent_critic",
        "model": "gemini-3.5-flash",
        "prompt": "You are a Critical Reviewer. Analyze previous proposals for edge cases, security flaws, communication bottlenecks, or logical inconsistencies."
    },
    {
        "name": "Synthesizer_Agent",
        "agent_id": "agent_synthesizer",
        "model": "gemini-3.5-flash",
        "prompt": "You are a Research Synthesizer. Summarize insights, reconcile differing viewpoints, and unify the team's ongoing dialogue."
    }
]

def main():
    # Read goal directive from argv if supplied
    goal_directive = "Analyze the communication bottlenecks and transparency challenges in decentralized multi-agent architectures."
    max_turns = 6  # 4-agent research dialogue

    if len(sys.argv) > 1:
        # Check if first arg is numeric (max_turns) or string (goal)
        try:
            max_turns = int(sys.argv[1])
            if len(sys.argv) > 2:
                goal_directive = " ".join(sys.argv[2:])
        except ValueError:
            goal_directive = " ".join(sys.argv[1:])

    # Execute dynamic goal-oriented simulation with 4-agent team
    result = run_huggingface_transparency_simulation(
        max_turns=max_turns,
        custom_prompt=goal_directive,
        custom_agents=agents
    )

    print("\n" + "=" * 80)
    print("===================== 1. DIRECT SYNTHESIZED ANSWER =====================")
    print("=====================  (PRODUCED FIRST FROM LLMS)   =====================")
    print("=" * 80)
    print(f"\nGoal Directive: {result['goal_directive']}\n")
    print(result["direct_answer"]["markdown"])

    print("\n" + "=" * 80)
    print("================== 2. DATA FLOW & COMMUNICATION TRACE ==================")
    print("==================   (HOW AGENTS COMMUNICATED)        ==================")
    print("=" * 80)
    
    print("\n[A] VISUAL DATA FLOW ARCHITECTURE:")
    print(result["data_flow"]["ascii_flow"])

    print("[B] STEP-BY-STEP DATA FLOW STAGES:")
    for st in result["data_flow"]["stages"]:
        print(f"  Stage {st['stage']}: {st['name']}")
        print(f"    - Sender:   {st['sender']}")
        print(f"    - Receiver: {st['receiver']}")
        print(f"    - Token:    {st['authority_token']} (Scope: {st['scope']})")
        print(f"    - Detail:   {st['description']}\n")

    print("[C] DYNAMIC TERMINATION & SAFETY CIRCUIT-BREAKER:")
    print(f"  - Goal Status:              {result['goal_status'].upper()}")
    print(f"  - Dynamic Turns Taken:      {result['turns_executed']} turns (terminated upon conclusive resolution)")
    print(f"  - Safety Loop Limit:        max {result['max_turns_limit']} turns")
    print(f"  - Root Authority Token:     {result['root_delegation_id']}")
    print(f"  - Executor Authority Token: {result['executor_delegation_id']}")
    print(f"  - Total Messages Recorded:  {result['data_flow']['total_messages']}")
    print(f"  - Total CIM Tool Events:    {result['data_flow']['total_cim_events']}")

    print("\n[D] THREE-GRAPH TRANSPARENCY METRICS:")
    g_inter = result["three_graphs"]["interaction_graph"]
    g_auth = result["three_graphs"]["authority_graph"]
    print(f"  - Interaction Graph (G_inter): {g_inter.number_of_nodes()} nodes, {g_inter.number_of_edges()} causal edges")
    print(f"  - Authority Graph (G_auth):   {g_auth.number_of_nodes()} delegation tokens, {g_auth.number_of_edges()} lineage edges")
    print("  - Internal Neural Reasoning:  100% stripped (<think> blocks removed before logging)")

    print("\n" + "=" * 80)
    print("Inspect interactive React Dashboard: http://localhost:5173 (or Streamlit: http://localhost:8501)")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
