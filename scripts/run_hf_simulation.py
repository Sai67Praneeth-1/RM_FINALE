"""
Standalone Goal-Oriented Multi-Agent Research Simulation & Transparency Observer powered by Google Gemini.
Executes dynamic multi-agent interaction between specialized agents (Coordinator, Executor, Critic, Synthesizer).
"""

import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.orchestration.hf_simulation import run_huggingface_transparency_simulation
from backend.agents.llm_client import init_hf_client, run_agent_turn, strip_internal_reasoning
from backend.config import settings

def main():
    max_turns = 20
    goal = "Audit customer complaints for High and Critical severity issues and verify system SLAs."

    if len(sys.argv) > 1:
        try:
            max_turns = int(sys.argv[1])
            if len(sys.argv) > 2:
                goal = " ".join(sys.argv[2:])
        except ValueError:
            goal = " ".join(sys.argv[1:])

    result = run_huggingface_transparency_simulation(max_turns=max_turns, custom_prompt=goal)

    print("\n" + "=" * 80)
    print("===================== 1. DIRECT SYNTHESIZED ANSWER =====================")
    print("=====================  (PRODUCED FIRST FROM LLMS)   =====================")
    print("=" * 80)
    print(result["direct_answer"]["markdown"])

    print("\n" + "=" * 80)
    print("================== 2. DATA FLOW & COMMUNICATION TRACE ==================")
    print("==================   (HOW AGENTS COMMUNICATED)        ==================")
    print("=" * 80)
    print("\n[A] VISUAL DATA FLOW ARCHITECTURE:")
    print(result["data_flow"]["ascii_flow"])

    print("[B] COMMUNICATION STAGES:")
    for st in result["data_flow"]["stages"]:
        print(f"  Stage {st['stage']}: {st['name']} ({st['authority_token']})")
        print(f"    {st['description']}\n")

    print(f"Goal Status: {result['goal_status'].upper()} in {result['turns_executed']} turns (limit: max {result['max_turns_limit']}).")
    print(f"Workflow ID: {result['workflow_id']}")

if __name__ == "__main__":
    main()
