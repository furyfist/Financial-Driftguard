"""
Connection smoke test — run this before starting the server.
Checks: DB, Groq API, Phoenix endpoint reachability.

Usage:
    python scripts/check_connections.py
"""

import os
import sys

from dotenv import load_dotenv
load_dotenv()

PASS = "[ OK ]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"


def check_db():
    url = os.getenv("DATABASE_URL", "")
    if not url:
        print(f"{SKIP} DATABASE_URL not set — will use SQLite fallback")
        return True
    if url.startswith("sqlite"):
        print(f"{PASS} DATABASE_URL is SQLite (local dev)")
        return True
    try:
        import sqlalchemy
        engine = sqlalchemy.create_engine(url, connect_args={} if "sqlite" not in url else {"check_same_thread": False})
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        print(f"{PASS} Database connected: {url.split('@')[-1]}")
        return True
    except Exception as exc:
        print(f"{FAIL} Database: {exc}")
        print("       Fix: update DATABASE_URL in .env with the Supabase pooler URL")
        print("       Supabase dashboard → Project Settings → Database → URI tab")
        return False


def check_groq():
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        print(f"{FAIL} GROQ_API_KEY not set")
        return False
    try:
        from groq import Groq
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "Reply with the single word: OK"}],
            max_tokens=5,
        )
        reply = resp.choices[0].message.content.strip()
        print(f"{PASS} Groq API responded: {reply!r}")
        return True
    except Exception as exc:
        print(f"{FAIL} Groq API: {exc}")
        return False


def check_phoenix():
    endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "")
    api_key = os.getenv("PHOENIX_API_KEY", "")
    if not endpoint:
        print(f"{SKIP} PHOENIX_COLLECTOR_ENDPOINT not set")
        return True
    if "arize.com" in endpoint and not api_key:
        print(f"{SKIP} Phoenix Arize cloud endpoint set but PHOENIX_API_KEY missing — tracing will fail")
        return True
    try:
        import httpx
        base = endpoint.replace("/v1/traces", "")
        headers = {"api_key": api_key} if api_key else {}
        r = httpx.get(base, headers=headers, timeout=8)
        print(f"{PASS} Phoenix reachable: {base} (HTTP {r.status_code})")
        return True
    except Exception as exc:
        print(f"{FAIL} Phoenix: {exc}")
        return False


def check_fred():
    key = os.getenv("FRED_API_KEY", "")
    if not key:
        print(f"{FAIL} FRED_API_KEY not set — macro signals will be degraded")
        return False
    try:
        from fredapi import Fred
        fred = Fred(api_key=key)
        val = fred.get_series("FEDFUNDS", observation_start="2024-01-01").iloc[-1]
        print(f"{PASS} FRED API connected — latest fed funds rate: {val:.2f}%")
        return True
    except Exception as exc:
        print(f"{FAIL} FRED API: {exc}")
        return False


def main():
    print("=" * 50)
    print("FinSight AI — connection checks")
    print("=" * 50)
    results = {
        "db":     check_db(),
        "groq":   check_groq(),
        "phoenix": check_phoenix(),
        "fred":   check_fred(),
    }
    print("=" * 50)
    failed = [k for k, v in results.items() if not v]
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("All checks passed.")


if __name__ == "__main__":
    main()
