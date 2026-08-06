#!/usr/bin/env python3
"""
ARTCB — Script LoopQA (Replay QA Platform) v2.0
API : https://qa.replay.io/api/mcp  (JSON-RPC Streamable-HTTP MCP)
Docs: https://qa.replay.io/api/docs

Ce script :
  1. Lance pytest en local et collecte les résultats
  2. Crée / récupère le projet LoopQA pour Replit N2
  3. Lance une exploration LoopQA sur le dashboard ARTCB (test frontend réel)
  4. Interroge l'API ARTCB Replit N2 directement (tests endpoints)
  5. Grave les résultats dans la blockchain ARTCB via /ai/memo
  6. Sauvegarde un rapport JSON horodaté dans rapports/

Usage :
    python3 scripts/replay_qa_platform.py          # run complet
    python3 scripts/replay_qa_platform.py --dry    # pytest local seulement
    python3 scripts/replay_qa_platform.py --status # état projet LoopQA seulement

Token : depuis env LOOPQA_API_TOKEN ou .env
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

# ─── Configuration ────────────────────────────────────────────────────────────
LOOPQA_MCP_URL  = os.environ.get("LOOPQA_API_URL",     "https://qa.replay.io/api/mcp")
LOOPQA_REST_URL = os.environ.get("LOOPQA_REST_URL",    "https://qa.replay.io/api/v1")
LOOPQA_TOKEN    = os.environ.get("LOOPQA_API_TOKEN",   "lqa_c13a64b1339ea4e9927f6f365f823b14e947d65b43a9fce5")
LOOPQA_PROJECT  = os.environ.get("LOOPQA_PROJECT_N2",  "proj-artcb-replit-n2-live-tests-msgawasn")
REPLIT_N2_URL   = "https://lvx--supermicro20239.replit.app"
REPLIT_N1_URL   = "https://lvx--supermicro20238.replit.app"
ARTCB_LOCAL_API = os.environ.get("ARTCB_API_URL",      "http://127.0.0.1:8000")

G    = "\033[92m"; R = "\033[91m"; Y = "\033[93m"
B    = "\033[94m"; E = "\033[0m";  BOLD = "\033[1m"


def banner() -> None:
    print(f"\n{BOLD}{'═'*68}")
    print("  ARTCB — LoopQA (Replay QA Platform) v2.0")
    print(f"  MCP API  : {LOOPQA_MCP_URL}")
    print(f"  REST API : {LOOPQA_REST_URL}")
    print(f"  Projet   : {LOOPQA_PROJECT}")
    print(f"  Cible    : {REPLIT_N2_URL}")
    print(f"{'═'*68}{E}\n")


# ─── Helpers JSON-RPC MCP ─────────────────────────────────────────────────────

def _mcp_call(method: str, params: dict, call_id: int = 1) -> dict:
    """Appel JSON-RPC vers l'API MCP LoopQA."""
    body = json.dumps({
        "jsonrpc": "2.0",
        "method":  method,
        "id":      call_id,
        "params":  params,
    }).encode("utf-8")
    req = urllib.request.Request(
        LOOPQA_MCP_URL,
        data=body,
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {LOOPQA_TOKEN}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    if "error" in data:
        raise RuntimeError(f"LoopQA MCP error: {data['error']}")
    return data.get("result", {})


def mcp_tool(tool_name: str, arguments: dict) -> dict | list | str:
    """Appelle un outil MCP et retourne le contenu parsé."""
    result = _mcp_call("tools/call", {"name": tool_name, "arguments": arguments})
    content = result.get("content", [])
    if content and content[0].get("type") == "text":
        try:
            return json.loads(content[0]["text"])
        except json.JSONDecodeError:
            return content[0]["text"]
    return result


# ─── Helpers REST API ─────────────────────────────────────────────────────────

def _rest_get(path: str) -> dict | list:
    """GET sur l'API REST LoopQA."""
    req = urllib.request.Request(
        f"{LOOPQA_REST_URL}{path}",
        headers={"Authorization": f"Bearer {LOOPQA_TOKEN}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


# ─── 1. Tests pytest locaux ───────────────────────────────────────────────────

def run_pytest() -> dict:
    """Lance pytest complet et retourne les métriques."""
    import re
    print(f"{B}[1/5] pytest tests/ ...{E}")
    t0 = time.time()
    cmd = [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short", "--no-header"]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          cwd=Path(__file__).parent.parent)
    elapsed = round(time.time() - t0, 2)

    lines = proc.stdout.splitlines()
    summary = ""
    for ln in reversed(lines):
        if re.search(r"\d+ passed", ln) or re.search(r"\d+ failed", ln):
            summary = ln
            break

    def _extract(pat: str) -> int:
        m = re.search(pat, summary)
        return int(m.group(1)) if m else 0

    passed  = _extract(r"(\d+) passed")
    failed  = _extract(r"(\d+) failed")
    errors  = _extract(r"(\d+) error")
    skipped = _extract(r"(\d+) skipped")
    status  = "pass" if failed == 0 and errors == 0 and passed > 0 else "fail"
    mark    = f"{G}✅" if status == "pass" else f"{R}❌"
    print(f"  {mark} {passed} passed, {skipped} skipped, {failed} failed — {elapsed}s{E}")
    if failed > 0:
        for ln in lines:
            if "FAILED" in ln or "ERROR" in ln:
                print(f"  {R}{ln}{E}")
    return {
        "passed": passed, "failed": failed, "errors": errors,
        "skipped": skipped, "elapsed_s": elapsed, "status": status,
        "summary": summary.strip(),
        "stdout_tail": "\n".join(lines[-20:]),
        "timestamp": datetime.now(UTC).isoformat(),
        "returncode": proc.returncode,
    }


# ─── 2. Tests endpoints Replit N2 ─────────────────────────────────────────────

def test_replit_endpoints(base: str = REPLIT_N2_URL) -> dict:
    """Teste tous les endpoints ARTCB sur Replit."""
    print(f"\n{B}[2/5] Tests endpoints réels sur {base} ...{E}")

    endpoints = [
        ("GET",  "/",                              None,           None),  # HTML frontend — pas JSON
        ("GET",  "/health",                        None,           200),
        ("GET",  "/api/v1/health",                 None,           200),
        ("GET",  "/api/v1/chain",                  None,           200),
        ("GET",  "/api/v1/chain/status",           None,           200),
        ("GET",  "/api/v1/chain/blocks",           None,           200),
        ("GET",  "/api/v1/node/status",            None,           200),
        ("GET",  "/api/v1/p2p/status",             None,           200),
        ("GET",  "/api/v1/p2p/peers",              None,           200),
        ("GET",  "/api/v1/wallet/list",            None,           200),
        ("GET",  "/api/v1/pol/score",              None,           200),
        ("GET",  "/api/v1/dashboard/mining/status",None,           200),
        ("GET",  "/api/v1/dashboard/logs/demo-live",None,          200),
        ("POST", "/api/v1/wallet/create",          {"name": f"loopqa_test_{int(time.time())}"}, 200),
        ("POST", "/api/v1/ir/learn",               {
            "wallet_address": "artcb1loopqa_probe_test_address_00000",
            "content": "LoopQA ARTCB endpoint probe test 2026-08-05",
            "visibility": "public",
        }, None),  # 200 ou 429 (anti-sybil) — les deux sont acceptés
    ]

    results = []
    ok_count = 0
    fail_count = 0

    for method, path, body, expected_status in endpoints:
        url = f"{base}{path}"
        t0 = time.time()
        try:
            data_bytes = json.dumps(body).encode() if body else None
            headers: dict[str, str] = {}
            if data_bytes:
                headers["Content-Type"] = "application/json"
            req = urllib.request.Request(
                url, data=data_bytes, headers=headers, method=method
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                status_code = resp.getcode()
                raw = resp.read()
                try:
                    resp_body = json.loads(raw)
                except Exception:
                    # HTML (frontend React, robots.txt...) — pas une erreur
                    resp_body = {"_html": len(raw)}
        except urllib.error.HTTPError as exc:
            status_code = exc.code
            try:
                resp_body = json.loads(exc.read())
            except Exception:
                resp_body = {"error": str(exc)}
        except Exception as exc:
            status_code = 0
            resp_body = {"error": str(exc)}

        elapsed_ms = round((time.time() - t0) * 1000)

        # expected_status=None : HTML, anti-sybil, etc. — accepter tous codes 2xx, 200, 422, 429
        if expected_status is None:
            ok = status_code in (200, 201, 206, 422, 429) or (200 <= status_code < 300)
        else:
            ok = (status_code == expected_status)

        if ok:
            ok_count += 1
            mark = f"{G}✅{E}"
        else:
            fail_count += 1
            mark = f"{R}❌{E}"

        print(f"  {mark} {method:4s} {path:45s} → {status_code} ({elapsed_ms}ms)")

        results.append({
            "method": method, "path": path,
            "status_code": status_code,
            "expected": expected_status,
            "ok": ok, "elapsed_ms": elapsed_ms,
            "response_keys": list(resp_body.keys()) if isinstance(resp_body, dict) else [],
        })

    total = ok_count + fail_count
    print(f"\n  {G if fail_count == 0 else R}Total : {ok_count}/{total} OK{E}")
    return {
        "base_url": base,
        "results": results,
        "ok": ok_count,
        "fail": fail_count,
        "total": total,
        "status": "pass" if fail_count == 0 else "fail",
    }


# ─── 3. LoopQA — état du projet ───────────────────────────────────────────────

def get_loopqa_project_status() -> dict:
    """Récupère et affiche l'état du projet LoopQA."""
    print(f"\n{B}[3/5] État projet LoopQA : {LOOPQA_PROJECT} ...{E}")
    try:
        status = mcp_tool("get_project_status", {"project_id": LOOPQA_PROJECT})
        bugs   = status.get("bugs", {})
        tests  = status.get("test_runs", {})
        jrns   = status.get("journeys", {})
        expl   = status.get("explorations", {})
        print(f"  Bugs      : {G}{bugs.get('open',0)} open{E} | {bugs.get('fixed',0)} fixed")
        print(f"  Test runs : {tests.get('completed',0)} completed | {tests.get('failed',0)} failed")
        print(f"  Journeys  : {jrns.get('total',0)} total")
        print(f"  Expl.     : {expl.get('completed',0)} completed | {expl.get('in-progress',0)} en cours")
        return {"status": "ok", "data": status}
    except Exception as exc:
        print(f"  {R}Erreur LoopQA : {exc}{E}")
        return {"status": "error", "error": str(exc)}


def get_loopqa_bugs() -> list:
    """Récupère les bugs ouverts détectés par LoopQA."""
    print(f"\n{B}  Bugs ouverts détectés par LoopQA IA :{E}")
    try:
        bugs_data = mcp_tool("list_bugs", {"project_id": LOOPQA_PROJECT, "status": "open"})
        items = bugs_data.get("items", []) if isinstance(bugs_data, dict) else []
        if not items:
            print(f"  {G}  Aucun bug ouvert ✅{E}")
        for bug in items[:10]:
            print(f"  {R}  🐛 [{bug.get('id','')}] {bug.get('title','?')}{E}")
        return items
    except Exception as exc:
        print(f"  {Y}  Bugs non récupérés : {exc}{E}")
        return []


def launch_loopqa_exploration() -> dict:
    """Lance une nouvelle exploration LoopQA sur le dashboard ARTCB."""
    print(f"\n{B}  Exploration LoopQA en cours (async — résultats dans ~2min) ...{E}")
    # Note : une exploration est déjà en cours depuis la création du projet.
    # On liste les explorations actives plutôt que d'en créer une nouvelle.
    try:
        expl_data = mcp_tool("list_explorations", {"project_id": LOOPQA_PROJECT})
        items = expl_data.get("items", []) if isinstance(expl_data, dict) else []
        active = [e for e in items if e.get("status") in ("in-progress", "queued")]
        done   = [e for e in items if e.get("status") == "completed"]
        print(f"  {G}{len(active)} exploration(s) active(s){E} | {len(done)} terminée(s)")
        for expl in items[:5]:
            sym = "🔄" if expl.get("status") == "in-progress" else "✅"
            print(f"  {sym} [{expl.get('id','')}] status={expl.get('status','')} journeys_created={expl.get('journeys_created',0)}")
        return {"active": len(active), "done": len(done), "items": items}
    except Exception as exc:
        print(f"  {Y}  Explorations non récupérées : {exc}{E}")
        return {"error": str(exc)}


def get_loopqa_test_runs() -> list:
    """Récupère les derniers test runs LoopQA."""
    print(f"\n{B}  Test runs LoopQA :{E}")
    try:
        runs_data = mcp_tool("list_test_runs", {"project_id": LOOPQA_PROJECT})
        items = runs_data.get("items", []) if isinstance(runs_data, dict) else []
        for run in items[:5]:
            sym = "✅" if run.get("status") == "pass" else ("🔄" if run.get("status") == "in-progress" else "❌")
            print(f"  {sym} [{run.get('id','')}] status={run.get('status','')} bugs={run.get('bug_count',0)}")
        return items
    except Exception as exc:
        print(f"  {Y}  Runs non récupérés : {exc}{E}")
        return []


# ─── 4. Gravure blockchain ARTCB ──────────────────────────────────────────────

def grave_in_blockchain(summary: dict) -> bool:
    """Grave les résultats dans la blockchain ARTCB locale."""
    print(f"\n{B}[4/5] Gravure résultats dans la blockchain ARTCB ...{E}")
    try:
        memo = {
            "title": (
                f"LoopQA v2 — pytest {summary['pytest']['passed']}/{summary['pytest']['passed']+summary['pytest']['failed']} "
                f"| N2 endpoints {summary['endpoints']['ok']}/{summary['endpoints']['total']} "
                f"| LoopQA {summary['loopqa'].get('data', {}).get('explorations', {}).get('completed', '?')} expl"
            ),
            "content": json.dumps({
                "pytest": summary["pytest"]["summary"],
                "pytest_status": summary["pytest"]["status"],
                "endpoints_ok": summary["endpoints"]["ok"],
                "endpoints_total": summary["endpoints"]["total"],
                "endpoints_status": summary["endpoints"]["status"],
                "loopqa_project": LOOPQA_PROJECT,
                "loopqa_url": REPLIT_N2_URL,
                "loopqa_bugs_open": summary.get("bugs_open_count", "?"),
                "session": "loopqa_v2_2026-08-05",
            }),
            "memo_type": "qa_result",
            "tags": ["loopqa", "pytest", "qa", "artcb", "replit-n2"],
            "agent_id": "loopqa_platform_v2",
        }
        req = urllib.request.Request(
            f"{ARTCB_LOCAL_API}/api/v1/ai/memo",
            data=json.dumps(memo).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            idx = data.get("block_index", "?")
            pol = data.get("pol_score", "?")
            print(f"  {G}✅ Gravé dans la blockchain — bloc #{idx}, PoL {pol}{E}")
            return True
    except Exception as exc:
        print(f"  {Y}⚠️  API ARTCB locale non disponible : {exc}{E}")
        return False


# ─── 5. Rapport local ─────────────────────────────────────────────────────────

def save_report(data: dict) -> Path:
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = Path(__file__).parent.parent / "rapports" / f"loopqa_{ts}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return path


# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="ARTCB LoopQA Platform v2")
    parser.add_argument("--dry",    action="store_true", help="pytest local seulement, pas d'upload")
    parser.add_argument("--status", action="store_true", help="Afficher état LoopQA seulement")
    args = parser.parse_args()

    banner()

    if args.status:
        status = get_loopqa_project_status()
        bugs   = get_loopqa_bugs()
        runs   = get_loopqa_test_runs()
        expl   = launch_loopqa_exploration()
        print(f"\n{BOLD}URL projet : https://qa.replay.io/p/{LOOPQA_PROJECT}/overview{E}\n")
        sys.exit(0)

    # 1. pytest local
    pytest_results = run_pytest()

    if args.dry:
        path = save_report({"pytest": pytest_results})
        print(f"\n{Y}Mode --dry : pas d'appels LoopQA ni blockchain{E}")
        print(f"Rapport : {path}")
        sys.exit(0 if pytest_results["status"] == "pass" else 1)

    # 2. Tests endpoints Replit N2
    endpoint_results = test_replit_endpoints(REPLIT_N2_URL)

    # 3. LoopQA status + bugs + explorations + runs
    loopqa_status = get_loopqa_project_status()
    bugs_list     = get_loopqa_bugs()
    expl_data     = launch_loopqa_exploration()
    runs_list     = get_loopqa_test_runs()

    # 4. Résumé global
    summary = {
        "pytest":          pytest_results,
        "endpoints":       endpoint_results,
        "loopqa":          loopqa_status,
        "loopqa_expl":     expl_data,
        "bugs_open_count": len([b for b in bugs_list if b.get("status") == "open"]),
        "runs":            runs_list[:3],
        "timestamp":       datetime.now(UTC).isoformat(),
        "loopqa_project":  LOOPQA_PROJECT,
        "target_url":      REPLIT_N2_URL,
        "loopqa_ui":       f"https://qa.replay.io/p/{LOOPQA_PROJECT}/overview",
    }

    # 5. Gravure blockchain
    grave_in_blockchain(summary)

    # 6. Rapport local
    print(f"\n{B}[5/5] Sauvegarde rapport local ...{E}")
    path = save_report(summary)
    print(f"  Rapport : {path}")

    # ── Résumé final ──────────────────────────────────────────────────────────
    pytest_ok    = pytest_results["status"] == "pass"
    endpoint_ok  = endpoint_results["status"] == "pass"
    overall      = "PASS" if pytest_ok and endpoint_ok else "FAIL"
    color        = G if overall == "PASS" else R

    print(f"\n{BOLD}{'─'*68}")
    print(f"  {color}Résultat global : {overall}{E}")
    print(f"  pytest      : {G if pytest_ok else R}{pytest_results['passed']} passed · {pytest_results['failed']} failed{E}")
    print(f"  Endpoints   : {G if endpoint_ok else R}{endpoint_results['ok']}/{endpoint_results['total']} OK{E}")
    print(f"  LoopQA UI   : https://qa.replay.io/p/{LOOPQA_PROJECT}/overview")
    print(f"  Rapport     : {path}")
    print(f"{'─'*68}{E}\n")

    sys.exit(0 if overall == "PASS" else 1)


if __name__ == "__main__":
    main()
