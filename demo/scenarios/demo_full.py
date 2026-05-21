"""
FinSight AI — Full Hackathon Demo

Runs all three demonstration scenarios in sequence:

  1. Fed Rate Hike 2017   → credit_stress → DON'T retrain
  2. COVID Crash 2020     → black_swan    → HALT
  3. Normal Model Decay   → stable        → RETRAIN

Each scenario pauses so you can walk judges through the output before
moving to the next. Pass --auto to skip the pauses and run continuously.

Usage:
  python scripts/demo_full.py           # interactive (pauses between scenarios)
  python scripts/demo_full.py --auto    # fully automated (CI / recording mode)
"""

import sys
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SCENARIOS = [
    {
        "name":   "Scenario 1 — Fed Rate Hike Cycle 2017-2018",
        "script": ROOT / "demo" / "scenarios" / "rate_hike_2017.py",
        "expect": "credit_stress regime → Monitor, do NOT retrain",
    },
    {
        "name":   "Scenario 2 — COVID-19 Black Swan March 2020",
        "script": ROOT / "demo" / "scenarios" / "covid_crash.py",
        "expect": "black_swan regime → HALT, freeze automated decisions",
    },
    {
        "name":   "Scenario 3 — Normal Model Decay (stable macro)",
        "script": ROOT / "demo" / "scenarios" / "normal_decay.py",
        "expect": "stable regime + drift → Investigate + RETRAIN",
    },
]

SEPARATOR = "═" * 65


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FinSight AI full demo runner")
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run all scenarios without pausing",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Seconds between scenarios in auto mode (default: 3.0)",
    )
    return parser.parse_args()


def print_header() -> None:
    print(f"\n{SEPARATOR}")
    print("  FinSight AI — Full Demo")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(SEPARATOR)
    print()
    print("  This demo runs 3 scenarios showing the same drift metric")
    print("  producing three different regime-aware recommendations.")
    print()
    print("  The core thesis: same drift score, different regimes →")
    print("  opposite actions. No other tool makes this distinction.")
    print()
    print("  Prerequisites:")
    print("    ✓ Backend running  (uvicorn driftguard.api.main:app --reload)")
    print("    ✓ Lending Club demo seeded  (python demo/lending_club.py)")
    print("    ✓ Optionally: Phoenix running  (docker compose up phoenix)")
    print()


def print_scenario_preview(idx: int, scenario: dict) -> None:
    print(f"\n{'─' * 65}")
    print(f"  [{idx}/3] {scenario['name']}")
    print(f"  Expected: {scenario['expect']}")
    print(f"{'─' * 65}\n")


def wait_for_user(auto: bool, delay: float, scenario_name: str) -> None:
    if auto:
        print(f"\n  (auto mode: continuing in {delay:.0f}s...)")
        time.sleep(delay)
    else:
        print(f"\n  Press Enter to continue to the next scenario...")
        input("  > ")


def run_scenario(scenario: dict) -> tuple[bool, float]:
    """Run a scenario script. Returns (success, elapsed_seconds)."""
    start = time.perf_counter()
    result = subprocess.run(
        [sys.executable, str(scenario["script"])],
        check=False,
    )
    elapsed = time.perf_counter() - start
    return result.returncode == 0, elapsed


def print_summary(results: list[dict]) -> None:
    print(f"\n{SEPARATOR}")
    print("  DEMO COMPLETE — SUMMARY")
    print(SEPARATOR)
    print()

    all_passed = True
    for r in results:
        status  = "✅  PASSED" if r["success"] else "❌  FAILED"
        elapsed = f"{r['elapsed']:.1f}s"
        print(f"  {status}  {r['name']:<42}  {elapsed}")
        if not r["success"]:
            all_passed = False

    total = sum(r["elapsed"] for r in results)
    print()
    print(f"  Total runtime  : {total:.1f}s")
    print()

    if all_passed:
        print("  ✅  All scenarios passed.")
        print()
        print("  What to show judges:")
        print("    1. Phoenix at http://localhost:6006 — all 3 traces visible")
        print("    2. Dashboard at http://localhost:5173 — regime badges + action cards")
        print("    3. /agent — ask 'Is my lending model safe right now?'")
        print("    4. /agent — 'Generate compliance report' → PDF downloads")
        print("    5. curl http://localhost:8000/trust/lending_club_v1 — trust score JSON")
    else:
        print("  ⚠️   Some scenarios failed. Check output above.")
        print("  Make sure the backend is running and demo data is seeded.")
    print()


def main() -> None:
    args = parse_args()
    print_header()

    if not args.auto:
        print("  Press Enter to start the demo...")
        input("  > ")

    results = []
    for i, scenario in enumerate(SCENARIOS, start=1):
        print_scenario_preview(i, scenario)

        success, elapsed = run_scenario(scenario)
        results.append({
            "name":    scenario["name"],
            "success": success,
            "elapsed": elapsed,
        })

        # Don't pause after the last scenario
        if i < len(SCENARIOS):
            wait_for_user(args.auto, args.delay, scenario["name"])

    print_summary(results)

    # Exit with error code if any scenario failed (useful for CI)
    failed = [r for r in results if not r["success"]]
    sys.exit(len(failed))


if __name__ == "__main__":
    main()
