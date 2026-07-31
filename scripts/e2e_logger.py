"""
ARTCB — Logger bout-en-bout complet de toutes les fonctionnalités.
Teste 100% des endpoints API avec les vrais chemins, mesure les latences, identifie les bugs.
Usage: PYTHONPATH=/home/lvx/ARTCB/lvx python scripts/e2e_logger.py
"""
from __future__ import annotations
import json, time, os, sys
from datetime import datetime, timezone
from pathlib import Path
import requests

BASE = "http://127.0.0.1:8000/api/v1"
LOG: list[dict] = []
T0 = time.perf_counter()
VGACTECH_ADDR = "artcb1juqdyyyl3w5clp7hslkltpn4cpg8npyrc65m85"
TIMESTAMP = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
# Wallet dédié aux tests e2e (ne jamais utiliser vgactech pour les tests — anti-sybil rate-limit)
E2E_WALLET = f"e2e_run_{TIMESTAMP}"

# ── helpers ──────────────────────────────────────────────────────────────────

def _log(step: str, ok: bool, detail: str = "", latency_ms: float = 0.0, data: dict | None = None):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "step": step,
        "ok": ok,
        "latency_ms": round(latency_ms, 2),
        "detail": detail,
    }
    if data:
        entry["data"] = data
    LOG.append(entry)
    icon = "✅" if ok else "❌"
    print(f"{icon} [{latency_ms:7.1f}ms] {step:38s} {detail}")


def _get(path: str, timeout: int = 8):
    t = time.perf_counter()
    try:
        r = requests.get(BASE + path, timeout=timeout)
        return r, (time.perf_counter() - t) * 1000
    except Exception as e:
        return None, (time.perf_counter() - t) * 1000


def _post(path: str, body: dict, timeout: int = 30):
    t = time.perf_counter()
    try:
        r = requests.post(BASE + path, json=body, timeout=timeout)
        return r, (time.perf_counter() - t) * 1000
    except Exception as e:
        return None, (time.perf_counter() - t) * 1000


def _j(r) -> dict:
    try:
        return r.json() if r else {}
    except Exception:
        return {}


# ── tests ────────────────────────────────────────────────────────────────────

def run_all():
    print("=" * 72)
    print(f"  ARTCB — LOG E2E COMPLET — {datetime.now(timezone.utc).isoformat()}")
    print("=" * 72)

    # 01 — Health (chaîne + PQC)
    r, ms = _get("/health")
    d = _j(r)
    c = d.get("chain", {})
    ok = bool(r and r.status_code == 200 and c.get("valid"))
    _log("01_health", ok,
         f"blocks={c.get('block_count')} pqc={c.get('pqc_algorithm')} hybrid={c.get('hybrid_signatures')}",
         ms, {"block_count": c.get("block_count"), "pqc": c.get("pqc_algorithm")})

    # 02 — Explorer (vue globale chaîne)
    r, ms = _get("/chain/explorer")
    d = _j(r)
    ok = bool(r and r.status_code == 200)
    _log("02_chain_explorer", ok,
         f"blocks={d.get('block_count')} public={d.get('public_block_count')} rewards={d.get('total_rewards_satoshi')} syms={d.get('symbol_registry_count')}",
         ms, {"block_count": d.get("block_count"), "public": d.get("public_block_count")})

    # 03 — Chain verify (intégrité)
    r, ms = _get("/chain/verify")
    d = _j(r)
    ok = bool(r and r.status_code == 200 and d.get("valid"))
    _log("03_chain_verify", ok,
         f"valid={d.get('valid')} blocks={d.get('block_count')} pqc={d.get('pqc_algorithm')}",
         ms, {"valid": d.get("valid"), "block_count": d.get("block_count"), "errors": d.get("errors", [])})

    # 04 — Block genesis (index 0)
    r, ms = _get("/chain/block/0")
    d = _j(r)
    b = d.get("block", {})
    ok = bool(r and r.status_code == 200 and b.get("index") == 0)
    _log("04_block_genesis", ok,
         f"hash={str(b.get('hash',''))[:16]} pol={b.get('pol_score')} sig={str(b.get('signature',''))[:20]}",
         ms)

    # 05 — Block dernier
    r, ms = _get("/chain/block/524")
    d = _j(r)
    b = d.get("block", {})
    ok = bool(r and r.status_code == 200)
    _log("05_block_latest", ok,
         f"index={b.get('index')} hash={str(b.get('hash',''))[:16]} pol={b.get('pol_score')} sig_algo={str(b.get('signature',''))[:12]}",
         ms)

    # 06 — Wallets liste (vrai chemin /wallet/list)
    r, ms = _get("/wallet/list")
    d = _j(r)
    wallets = d.get("wallets", [])
    hybrid_n = sum(1 for w in wallets if w.get("hybrid"))
    ok = bool(r and r.status_code == 200 and len(wallets) > 0)
    _log("06_wallet_list", ok,
         f"total={len(wallets)} hybrid_pqc={hybrid_n} legacy={len(wallets)-hybrid_n}",
         ms, {"total": len(wallets), "hybrid": hybrid_n, "legacy": len(wallets)-hybrid_n})

    # 07 — Wallet create (wallet dédié e2e — évite anti-sybil sur vgactech)
    r, ms = _post("/wallet/create", {"name": E2E_WALLET})
    d = _j(r)
    ok = bool(r and r.status_code in (200, 201) and d.get("address"))
    e2e_addr = d.get("address", VGACTECH_ADDR)
    _log("07_wallet_create", ok,
         f"address={d.get('address','')[:28]} hybrid={d.get('hybrid')} addr_v2={str(d.get('address_v2',''))[:20]}",
         ms)

    # 08 — Encode → graph_id (flux PoL correct)
    r, ms = _post("/encode", {
        "text": f"[E2E-LOG {TIMESTAMP}] Test complet bout-en-bout ARTCB — logging toutes fonctionnalités 100%",
        "mode": "rule-based"
    }, timeout=15)
    d = _j(r)
    graph_id = d.get("graph_id", "")
    ok = bool(r and r.status_code in (200, 201) and graph_id)
    _log("08_ir_encode", ok,
         f"graph_id={graph_id} nodes={d.get('node_count')} edges={d.get('edge_count')}",
         ms, {"graph_id": graph_id})

    # 09 — Store un bloc PoL (flux complet encode → store)
    if graph_id:
        r, ms = _post("/store", {
            "graph_id": graph_id,
            "wallet_name": E2E_WALLET,
            "visibility": "public",
            "contributors": [{"address": e2e_addr, "weight": 1.0}]
        })
        d = _j(r)
        ok = bool(r and r.status_code in (200, 201) and d.get("block_index") is not None)
        _log("09_store_bloc_pol", ok,
             f"index={d.get('block_index')} pol={d.get('pol_score')} hash={str(d.get('hash',''))[:16]}",
             ms, {"index": d.get("block_index"), "pol": d.get("pol_score"), "hash": str(d.get("hash",""))[:16]})
    else:
        _log("09_store_bloc_pol", False, "SKIP: pas de graph_id (encode échoué)", 0)

    # 10 — Mining pipeline (flux direct texte → bloc)
    r, ms = _post("/mining/pipeline", {
        "text": f"[PIPELINE {TIMESTAMP}] Raisonnement PoL via pipeline minage apprentissage ARTCB Phase 13",
        "wallet_name": E2E_WALLET,
        "visibility": "public",
    })
    d = _j(r)
    ok = bool(r and r.status_code in (200, 201) and d.get("block_index") is not None)
    _log("10_mining_pipeline", ok,
         f"index={d.get('block_index')} pol={d.get('pol_score')}",
         ms, {"index": d.get("block_index"), "pol": d.get("pol_score")})

    # 11 — P2P status
    r, ms = _get("/p2p/status")
    d = _j(r)
    ok = bool(r and r.status_code == 200)
    _log("11_p2p_status", ok,
         f"node_id={str(d.get('node_id',''))[:20]} peers={d.get('peer_count',0)}",
         ms, {"peers": d.get("peer_count", 0)})

    # 12 — P2P peers
    r, ms = _get("/p2p/peers")
    d = _j(r)
    ok = bool(r and r.status_code == 200)
    _log("12_p2p_peers", ok,
         f"peers={d.get('count', len(d.get('peers',[])))}",
         ms)

    # 13 — Bridges status (timeout réduit — réseau externe)
    r, ms = _get("/bridges/status", timeout=5)
    d = _j(r)
    ok = bool(r and r.status_code == 200)
    if ok:
        chains_ok = [c["chain"] for c in d.get("bridges", []) if c.get("status") == "ok"]
        chains_fail = [c["chain"] for c in d.get("bridges", []) if c.get("status") != "ok"]
        _log("13_bridges_status", ok,
             f"ok={chains_ok} fail={chains_fail} summary={d.get('summary','')}",
             ms, {"ok": chains_ok, "fail": chains_fail})
    else:
        _log("13_bridges_status", False, f"status={r.status_code if r else 'ERR'}", ms)

    # 14 — Interop chains
    r, ms = _get("/interop/chains")
    d = _j(r)
    ok = bool(r and r.status_code == 200)
    _log("14_interop_chains", ok, f"total={d.get('total')} chains={[c['chain'] for c in d.get('supported_chains',[])[:3]]}", ms)

    # 15 — Anti-Sybil config (vrai chemin)
    r, ms = _get("/security/anti-sybil/config")
    d = _j(r)
    ok = bool(r and r.status_code == 200)
    _log("15_antisybil_config", ok,
         f"enabled={d.get('enabled')} min_interval={d.get('min_block_interval_s')}s pol_min={d.get('min_pol_score')}",
         ms, d)

    # 16 — Anti-Sybil metrics
    r, ms = _get("/security/anti-sybil/metrics")
    d = _j(r)
    ok = bool(r and r.status_code == 200)
    _log("16_antisybil_metrics", ok,
         f"samples={d.get('sample_count')} suggested={d.get('suggested_limit_sec')}s",
         ms)

    # 17 — AI context
    r, ms = _get("/ai/context")
    d = _j(r)
    ok = bool(r and r.status_code == 200)
    _log("17_ai_context", ok,
         f"height={d.get('chain_height')} memos={d.get('total_ai_memos')} ready={d.get('prompt_ready')}",
         ms)

    # 18 — AI bugs ouverts
    r, ms = _get("/ai/bugs/open")
    d = _j(r)
    ok = bool(r and r.status_code == 200)
    _log("18_ai_bugs_open", ok,
         f"open_bugs={d.get('count')} bugs={[b.get('title','')[:20] for b in d.get('open_bugs',[])[:2]]}",
         ms)

    # 19 — PoL NFT
    r, ms = _get("/pol/nft")
    d = _j(r)
    ok = bool(r and r.status_code == 200)
    _log("19_pol_nft", ok, f"nfts={d.get('count')} minted={len(d.get('nfts',[]))}", ms)

    # 20 — IR Rules
    r, ms = _get("/ir/rules")
    d = _j(r)
    ok = bool(r and r.status_code == 200)
    _log("20_ir_rules", ok, f"rules={d.get('count')}", ms)

    # 21 — Groups (besoin d'un group_id — utiliser list via chain)
    r, ms = _get("/groups")
    ok = bool(r and r.status_code in (200, 422))  # 422 si paramètre manquant
    _log("21_groups_endpoint", ok, f"status={r.status_code if r else 'ERR'}", ms)

    # 22 — Connectors formats
    r, ms = _get("/connectors/formats")
    d = _j(r)
    ok = bool(r and r.status_code == 200)
    _log("22_connectors_formats", ok,
         f"formats={d.get('total_extensions')} types={len(d.get('formats', {}))}",
         ms)

    # 23 — Devnet faucet status
    r, ms = _get("/devnet/faucet/status")
    d = _j(r)
    ok = bool(r and r.status_code == 200)
    _log("23_devnet_faucet", ok,
         f"total_requests={d.get('total_requests')} distributed={d.get('total_distributed_satoshi')}",
         ms)

    # 24 — Chain encode (IR encode)
    r, ms = _post("/encode", {"text": "test encodage IR", "mode": "rule-based"})
    d = _j(r)
    ok = bool(r and r.status_code in (200, 201))
    _log("24_ir_encode", ok, f"status={r.status_code if r else 'ERR'} {str(d)[:60]}", ms)

    # 25 — Doppler (externe)
    try:
        import subprocess
        result = subprocess.run(
            ["doppler", "secrets", "--project", "artcb-blockchain", "--config", "dev", "--json"],
            capture_output=True, text=True, timeout=8
        )
        secrets = json.loads(result.stdout) if result.returncode == 0 else {}
        ok = len(secrets) > 10
        _log("25_doppler_secrets", ok,
             f"secrets={len(secrets)} projet=artcb-blockchain/dev",
             0, {"count": len(secrets)})
    except Exception as e:
        _log("25_doppler_secrets", False, str(e)[:60], 0)

    # ── résumé ────────────────────────────────────────────────────────────────
    total_ms = (time.perf_counter() - T0) * 1000
    ok_n = sum(1 for e in LOG if e["ok"])
    fail_n = len(LOG) - ok_n

    print()
    print("=" * 72)
    print(f"  RÉSULTAT : {ok_n}/{len(LOG)} OK | {fail_n} ÉCHEC | {total_ms/1000:.1f}s")

    if fail_n > 0:
        print("\n  ❌ ÉCHECS :")
        for e in LOG:
            if not e["ok"]:
                print(f"     {e['step']:38s} → {e['detail'][:55]}")
    print("=" * 72)

    # Sauvegarder
    Path("logs").mkdir(exist_ok=True)
    log_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_ms": round(total_ms, 2),
        "ok": ok_n, "total": len(LOG), "fail": fail_n,
        "steps": LOG,
    }
    ts_path = f"logs/e2e_{TIMESTAMP}.json"
    with open(ts_path, "w") as f:
        json.dump(log_data, f, indent=2)
    with open("logs/e2e_latest.json", "w") as f:
        json.dump(log_data, f, indent=2)
    print(f"\n  📁 Logs: {ts_path}")
    return ok_n, len(LOG), fail_n, LOG


if __name__ == "__main__":
    ok_n, total, fail_n, _ = run_all()
    sys.exit(0 if fail_n == 0 else 1)
