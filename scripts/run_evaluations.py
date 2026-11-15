"""
Executable Evaluation Script.
Runs all 8 research scenarios and 5 comparative baselines.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.evaluation.runner import BenchmarkRunner

def main():
    print("================================================================================")
    print(" RESEARCH EVALUATION: TRANSPARENCY & OPENNESS IN AGENTIC AI SYSTEMS")
    print("================================================================================")
    runner = BenchmarkRunner()
    res = runner.run_full_evaluation(size_per_scenario=50)
    print("\nBenchmark successfully executed!")
    print(f"Total benchmark data points: {res['total_evaluations']}")
    print(f"JSON Output: {res['json_path']}")
    print(f"CSV Summary: {res['csv_path']}")
    print("================================================================================")

if __name__ == "__main__":
    main()

