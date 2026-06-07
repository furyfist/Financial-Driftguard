"""
Run governance LLM-as-Judge evals and push results to Phoenix.

Usage:
    python scripts/run_evals.py
    python scripts/run_evals.py --model lending_club_v1
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Run governance evals")
    parser.add_argument("--model", default="lending_club_v1", help="Model ID to evaluate")
    args = parser.parse_args()

    print(f"Running evals for model: {args.model}")

    try:
        from finsight.evals.governance_eval import run_evals
        results = run_evals(model_id=args.model)
    except Exception as exc:
        print(f"[FAIL] Evals failed: {exc}")
        sys.exit(1)

    print(f"Total evaluated : {results['total_evaluated']}")
    print(f"Correct         : {results['correct']}")
    print(f"Accuracy        : {results['accuracy']:.1%}")
    print(f"Regime eval     : {results['regime_eval_count']}")
    print(f"Action eval     : {results['action_eval_count']}")
    print(f"Experiment name : {results['experiment_name']}")

    if results["total_evaluated"] == 0:
        print("\nNo data to evaluate. Seed demo data first: python demo/lending_club.py")
        print("Then run the agent a few times: python scripts/test_agent.py")
    else:
        print("\nCheck Phoenix Experiments tab for results:")
        import os
        base = os.getenv("PHOENIX_MCP_BASE_URL", "http://localhost:6006")
        print(f"  {base}")


if __name__ == "__main__":
    main()
