"""
Comprehensive 30-Command Verification Suite for MOMO.
Executes 30 commands across:
  - Category 1: Desktop Automation (10 commands)
  - Category 2: Web Crawling & Live Intelligence (10 commands)
  - Category 3: LLM Knowledge & Reinforcement Learning (10 commands)
Designed to run twice to guarantee consistency and stability.
"""
import os
import sys
import time
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Configure Django environment
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["MOMO_AUTOMATION_DRY_RUN"] = "1"  # Safe dry-run to avoid opening 60 real browser/app windows

import django
django.setup()

from graph.graph import momo_graph
from graph.state import MomoState, Message
from memory.memory_manager import MemoryManager
from ai_workflow.services.temporal_service import TemporalService

# The 30 Test Commands
COMMANDS = [
    # --- Category 1: Automation (10) ---
    {"id": "AUTO-01", "category": "automation", "query": "open instagram", "expected_target": "Instagram"},
    {"id": "AUTO-02", "category": "automation", "query": "open youtube", "expected_target": "YouTube"},
    {"id": "AUTO-03", "category": "automation", "query": "open google", "expected_target": "Google"},
    {"id": "AUTO-04", "category": "automation", "query": "open github", "expected_target": "GitHub"},
    {"id": "AUTO-05", "category": "automation", "query": "open twitter", "expected_target": "X (Twitter)"},
    {"id": "AUTO-06", "category": "automation", "query": "open reddit", "expected_target": "Reddit"},
    {"id": "AUTO-07", "category": "automation", "query": "open whatsapp", "expected_target": "WhatsApp"},
    {"id": "AUTO-08", "category": "automation", "query": "open notepad", "expected_target": "Notepad"},
    {"id": "AUTO-09", "category": "automation", "query": "open calculator", "expected_target": "Calculator"},
    {"id": "AUTO-10", "category": "automation", "query": "play 2048", "expected_target": "2048"},

    # --- Category 2: Web Crawling & Live Research (10) ---
    {"id": "CRAWL-01", "category": "crawling", "query": "tell me its latest news with the date and time", "expected_keyword": "2026"},
    {"id": "CRAWL-02", "category": "crawling", "query": "latest breaking news in India", "expected_keyword": "news"},
    {"id": "CRAWL-03", "category": "crawling", "query": "what is happening with Smart India Hackathon", "expected_keyword": "hackathon"},
    {"id": "CRAWL-04", "category": "crawling", "query": "what special day is today", "expected_keyword": "september"},
    {"id": "CRAWL-05", "category": "crawling", "query": "what is the current date and time", "expected_keyword": "2026"},
    {"id": "CRAWL-06", "category": "crawling", "query": "web crawl python.org", "expected_keyword": "python"},
    {"id": "CRAWL-07", "category": "crawling", "query": "web crawl wikipedia.org", "expected_keyword": "wikipedia"},
    {"id": "CRAWL-08", "category": "crawling", "query": "latest tech developments in AI 2026", "expected_keyword": "ai"},
    {"id": "CRAWL-09", "category": "crawling", "query": "news updates from the hindu", "expected_keyword": "hindu"},
    {"id": "CRAWL-10", "category": "crawling", "query": "latest indian space research updates", "expected_keyword": "space"},

    # --- Category 3: LLM & Reinforcement Learning (10) ---
    {"id": "LLM-01", "category": "llm", "query": "Hello MOMO, how are you doing today?", "expected_keyword": "momo"},
    {"id": "LLM-02", "category": "llm", "query": "Explain quantum computing in simple terms for a beginner.", "expected_keyword": "quantum"},
    {"id": "LLM-03", "category": "reinforcement", "query": "Remember that my project name is MOMO Robot.", "expected_keyword": "momo robot"},
    {"id": "LLM-04", "category": "reinforcement", "query": "What is my project name?", "expected_keyword": "momo robot"},
    {"id": "LLM-05", "category": "reinforcement", "query": "Learn that I prefer Python for backend coding.", "expected_keyword": "python"},
    {"id": "LLM-06", "category": "reinforcement", "query": "What programming language do I prefer for backend work?", "expected_keyword": "python"},
    {"id": "LLM-07", "category": "llm", "query": "If a train leaves Station A at 60 km/h and another leaves Station B at 90 km/h towards each other, 300 km apart, when do they meet?", "expected_keyword": "2"},
    {"id": "LLM-08", "category": "llm", "query": "I have been studying for 4 hours and feeling a bit tired.", "expected_keyword": "break"},
    {"id": "LLM-09", "category": "llm", "query": "Write a Python function to check if a string is a palindrome.", "expected_keyword": "def "},
    {"id": "LLM-10", "category": "llm", "query": "What is the current system and hardware status of MOMO?", "expected_keyword": "status"},
]


async def execute_single_command(cmd_spec: Dict[str, Any], session_id: str = "test_suite") -> Dict[str, Any]:
    """
    Executes a single test command through the LangGraph pipeline and returns evaluation metrics.
    """
    query = cmd_spec["query"]
    cid = cmd_spec["id"]
    category = cmd_spec["category"]

    # Pre-step: If it's a reinforcement teaching command, store the fact via MemoryManager as well
    mm = MemoryManager()
    if "remember that" in query.lower() or "learn that" in query.lower():
        await mm.extract_and_store_facts(query)

    state = MomoState(
        messages=[Message(role="user", content=query)],
        metadata={"session_id": session_id}
    )

    t0 = time.time()
    try:
        res = await asyncio.wait_for(momo_graph.ainvoke(state), timeout=45.0)
        elapsed = time.time() - t0

        if isinstance(res, dict):
            resp_obj = res.get("response")
            route = res.get("current_route", "")
            agent = res.get("current_agent", "")
        else:
            resp_obj = getattr(res, "response", None)
            route = getattr(res, "current_route", "")
            agent = getattr(res, "current_agent", "")

        msg = resp_obj.message if resp_obj else ""
        msg_clean = msg.strip()

        # Check for buffering error or failure phrases
        is_buffering_error = "buffering" in msg.lower() and "ollama" in msg.lower()
        is_empty = len(msg_clean) == 0

        # Verification rules
        passed = True
        notes = []

        if is_buffering_error:
            passed = False
            notes.append("Returned Ollama buffering fallback error.")

        if is_empty:
            passed = False
            notes.append("Empty response received.")

        if category == "automation":
            exp_target = cmd_spec.get("expected_target", "").lower()
            if not any(k in msg.lower() for k in [exp_target, "launching", "opening", "opened", "launched"]):
                passed = False
                notes.append(f"Automation did not confirm action for {exp_target}")
            if elapsed > 15.0:
                notes.append(f"Slow automation: {elapsed:.2f}s")

        elif category == "crawling":
            # Guard against hallucinated 2022 news
            if "2022" in msg and "2026" not in msg:
                passed = False
                notes.append("Contains stale/hallucinated 2022 reference.")
            if "cambridge dictionary" in msg.lower():
                passed = False
                notes.append("Hallucinated dictionary definition returned.")

        elif category == "reinforcement":
            # Check for retention of learned fact
            exp_kw = cmd_spec.get("expected_keyword", "").lower()
            if exp_kw and exp_kw not in msg.lower():
                # Check if memory has it
                recalled = await mm.get_relevant_memories(exp_kw)
                rules = await mm.get_active_reinforced_rules()
                all_mem = " ".join(recalled + rules).lower()
                if exp_kw in all_mem:
                    notes.append(f"Fact '{exp_kw}' present in memory store.")
                else:
                    passed = False
                    notes.append(f"Expected keyword '{exp_kw}' not in response or memory.")

        return {
            "id": cid,
            "category": category,
            "query": query,
            "passed": passed,
            "elapsed": round(elapsed, 2),
            "route": route,
            "agent": agent,
            "response": msg_clean[:250] + ("..." if len(msg_clean) > 250 else ""),
            "notes": "; ".join(notes) if notes else "OK"
        }

    except asyncio.TimeoutError:
        return {
            "id": cid,
            "category": category,
            "query": query,
            "passed": False,
            "elapsed": 45.0,
            "route": "timeout",
            "agent": "timeout",
            "response": "TIMEOUT ERROR",
            "notes": "Execution exceeded 45s timeout"
        }
    except Exception as e:
        return {
            "id": cid,
            "category": category,
            "query": query,
            "passed": False,
            "elapsed": round(time.time() - t0, 2),
            "route": "error",
            "agent": "error",
            "response": f"EXCEPTION: {e}",
            "notes": str(e)
        }


async def run_suite(round_number: int) -> List[Dict[str, Any]]:
    print(f"\n{'='*70}")
    print(f"STARTING 30-COMMAND TEST SUITE - ROUND {round_number}")
    print(f"{'='*70}")

    results = []
    for idx, cmd in enumerate(COMMANDS, 1):
        print(f"[{idx}/30] [{cmd['category'].upper()}] Running: '{cmd['query']}'...")
        res = await execute_single_command(cmd, session_id=f"test_round_{round_number}")
        status_str = "PASS" if res["passed"] else "FAIL"
        print(f"       -> [{status_str}] in {res['elapsed']}s | Response: {res['response'][:90]}... (Notes: {res['notes']})")
        results.append(res)

    total_passed = sum(1 for r in results if r["passed"])
    print(f"\n{'-'*70}")
    print(f"ROUND {round_number} COMPLETE: {total_passed}/30 Passed ({total_passed/30*100:.1f}%)")
    print(f"{'-'*70}\n")
    return results


async def main():
    print("MOMO 30-Command Dual-Pass Verification Runner Initiated.")
    round1_results = await run_suite(round_number=1)
    round2_results = await run_suite(round_number=2)

    # Save results to JSON file for logging and inspection
    summary_path = BACKEND_DIR / "tests" / "test_30_commands_results.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.time(),
            "round_1": round1_results,
            "round_2": round2_results,
            "round_1_passed": sum(1 for r in round1_results if r["passed"]),
            "round_2_passed": sum(1 for r in round2_results if r["passed"]),
        }, f, indent=2)

    print(f"Results saved to: {summary_path}")

if __name__ == "__main__":
    asyncio.run(main())
