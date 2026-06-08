"""
Quick agent smoke test — validates the full Groq tool-calling loop.

Usage:
    python scripts/test_agent.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

PASS = "[ OK ]"
FAIL = "[FAIL]"


def test_llm_direct():
    """Sanity: LLM responds at all."""
    try:
        from finsight.llm import get_llm
        llm = get_llm(role="fast")
        resp = llm.complete([{"role": "user", "content": "Reply with a single word: READY"}], temperature=0.0)
        reply = resp.content.strip()
        print(f"{PASS} LLM direct call — model: {resp.model}, reply: {reply!r}")
        return True
    except Exception as exc:
        print(f"{FAIL} LLM direct call: {exc}")
        return False


def test_tool_call():
    """Sanity: LLM triggers a tool call when asked about macro."""
    try:
        from finsight.llm import get_llm
        from finsight.agent.tools.macro_tools import MACRO_TOOLS
        llm = get_llm(role="fast")
        messages = [
            {"role": "system", "content": "You are a financial AI. Always use tools when asked for data."},
            {"role": "user", "content": "What are the current macro signals? Use get_current_macro."},
        ]
        resp = llm.complete(messages, tools=MACRO_TOOLS, temperature=0.0)
        if resp.tool_calls:
            tc = resp.tool_calls[0]
            print(f"{PASS} Tool call triggered — name: {tc.name}, args: {tc.arguments}")
            return True
        else:
            print(f"{FAIL} No tool call in response — content: {resp.content[:100]!r}")
            return False
    except Exception as exc:
        print(f"{FAIL} Tool call test: {exc}")
        return False


def test_full_agent(model_id: str = "lending_club_v1"):
    """Full agent loop — requires model to exist in DB."""
    try:
        from finsight.agent.brain import DriftGuardAgent
        agent = DriftGuardAgent()
        result = agent.ask(query="What is the current drift status?", model_id=model_id)
        print(f"{PASS} Agent loop completed")
        print(f"       action     : {result.action}")
        print(f"       confidence : {result.confidence:.2f}")
        print(f"       regime     : {result.regime}")
        print(f"       recommendation: {result.recommendation[:100]!r}")
        return True
    except Exception as exc:
        print(f"{FAIL} Full agent loop: {exc}")
        return False


def main():
    print("=" * 50)
    print("FinSight AI — agent smoke test")
    print("=" * 50)

    results = {
        "llm_direct": test_llm_direct(),
        "tool_call":  test_tool_call(),
        "agent_loop": test_full_agent(),
    }

    print("=" * 50)
    failed = [k for k, v in results.items() if not v]
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        print("Note: agent_loop requires demo data seeded (python demo/lending_club.py)")
        sys.exit(1)
    print("All agent tests passed.")


if __name__ == "__main__":
    main()
