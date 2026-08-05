#!/usr/bin/env python3
"""
Test rapide endpoints N1+N2 + LoopQA status (sans pytest long).
Usage : python3 scripts/test_endpoints_loopqa.py
"""
from __future__ import annotations
import json, sys, time, urllib.error, urllib.request
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.replay_qa_platform import (
    LOOPQA_PROJECT, REPLIT_N1_URL, REPLIT_N2_URL,
    banner, test_replit_endpoints,
    get_loopqa_project_status, get_loopqa_bugs,
    launch_loopqa_exploration, get_loopqa_test_runs,
    save_report,
)

if __name__ == "__main__":
    banner()

    print("\n\033[94m=== TESTS ENDPOINTS N2 ===\033[0m")
    ep_n2 = test_replit_endpoints(REPLIT_N2_URL)

    print("\n\033[94m=== TESTS ENDPOINTS N1 ===\033[0m")
    ep_n1 = test_replit_endpoints(REPLIT_N1_URL)

    print("\n\033[94m=== LOOPQA STATUS ===\033[0m")
    loopqa_status = get_loopqa_project_status()
    bugs_list     = get_loopqa_bugs()
    expl_data     = launch_loopqa_exploration()
    runs_list     = get_loopqa_test_runs()

    summary = {
        "endpoints_n2": ep_n2,
        "endpoints_n1": ep_n1,
        "loopqa": loopqa_status,
        "loopqa_expl": expl_data,
        "bugs_open_count": len([b for b in bugs_list if b.get("status") == "open"]),
        "runs": runs_list[:5],
        "timestamp": datetime.now(UTC).isoformat(),
        "loopqa_project": LOOPQA_PROJECT,
        "target_n2": REPLIT_N2_URL,
        "target_n1": REPLIT_N1_URL,
        "loopqa_ui": f"https://qa.replay.io/p/{LOOPQA_PROJECT}/overview",
    }
    path = save_report(summary)

    n2_ok = ep_n2["ok"]
    n1_ok = ep_n1["ok"]
    n2_total = ep_n2["total"]
    n1_total = ep_n1["total"]

    G = "\033[92m"; R = "\033[91m"; E = "\033[0m"; BOLD = "\033[1m"
    print(f"\n{BOLD}{'─'*68}")
    print(f"  N2 Endpoints : {G if ep_n2['status']=='pass' else R}{n2_ok}/{n2_total} OK{E}")
    print(f"  N1 Endpoints : {G if ep_n1['status']=='pass' else R}{n1_ok}/{n1_total} OK{E}")
    print(f"  LoopQA projet : {LOOPQA_PROJECT}")
    print(f"  LoopQA UI     : https://qa.replay.io/p/{LOOPQA_PROJECT}/overview")
    print(f"  Rapport       : {path}")
    print(f"{'─'*68}{E}\n")

    sys.exit(0)
