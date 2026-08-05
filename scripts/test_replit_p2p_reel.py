#!/usr/bin/env python3
"""Test P2P reel — 2 noeuds Replit ARTCB.
Usage : python3 scripts/test_replit_p2p_reel.py
"""
import urllib.request, urllib.error, json, time, sys

N1 = "https://lvx--supermicro20238.replit.app"
N2 = "https://lvx--supermicro20239.replit.app"  # Redeploye 2026-08-05
results = []
ts_start = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ARTCB-test"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


def post(url, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"User-Agent": "ARTCB-test", "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


def step(name, ok, detail=""):
    mark = "OK" if ok else "FAIL"
    msg = f"  [{mark}] {name}"
    if detail:
        msg += f"  |  {detail}"
    print(msg)
    results.append({"name": name, "ok": ok, "detail": str(detail)[:200]})
    return ok


print("=" * 64)
print("   TEST REEL P2P — 2 NOEUDS REPLIT ARTCB")
print(f"   Debut : {ts_start}")
print("=" * 64)

# ─── 1. ETAT INITIAL ──────────────────────────────────────────
print("\n--- [1] ETAT INITIAL ---")
s, d = get(N1 + "/api/v1/p2p/status")
n1_id = d.get("node_id", "?")
n1_kem = d.get("kem_public_key_hex", "")
step("N1 p2p/status", s == 200, f"node_id={n1_id}")

s, d = get(N2 + "/api/v1/p2p/status")
n2_id = d.get("node_id", "?")
n2_kem = d.get("kem_public_key_hex", "")
step("N2 p2p/status", s == 200, f"node_id={n2_id}")

s, d = get(N1 + "/api/v1/chain")
n1_blk0 = d.get("count", len(d.get("blocks", [])))
step("N1 chain init", s == 200, f"blocs={n1_blk0}")

s, d = get(N2 + "/api/v1/chain")
n2_blk0 = d.get("count", len(d.get("blocks", [])))
step("N2 chain init", s == 200, f"blocs={n2_blk0}")

s, d = get(N1 + "/api/v1/p2p/peers")
n1_peers0 = d.get("count", len(d.get("peers", [])))
step("N1 peers init", s == 200, f"peers={n1_peers0}")

s, d = get(N2 + "/api/v1/p2p/peers")
n2_peers0 = d.get("count", len(d.get("peers", [])))
step("N2 peers init", s == 200, f"peers={n2_peers0}")

# ─── 2. WALLETS ───────────────────────────────────────────────
print("\n--- [2] WALLETS ---")
s, d = get(N1 + "/api/v1/wallet/list")
wallets_n1 = d.get("wallets", [])
if wallets_n1:
    n1_addr = wallets_n1[0].get("address", "")
    step("N1 wallet existant", bool(n1_addr), f"address={n1_addr[:35]}...")
else:
    s, d = post(N1 + "/api/v1/wallet/create", {"name": "test_n1_p2p"})
    n1_addr = d.get("address", "") if s == 200 else ""
    step("N1 wallet cree", s == 200, f"address={n1_addr[:35]}..." if n1_addr else str(d)[:80])

ts_suffix = str(int(time.time()))
s, d = post(N2 + "/api/v1/wallet/create", {"name": f"test_n2_p2p_{ts_suffix}"})
n2_addr = d.get("address", "") if s == 200 else ""
step("N2 wallet cree", s == 200, f"address={n2_addr[:35]}..." if n2_addr else str(d)[:80])

# ─── 3. CONNEXION P2P ─────────────────────────────────────────
print("\n--- [3] CONNEXION P2P N1 <-> N2 ---")
s, d = post(N1 + "/api/v1/p2p/peers", {
    "host": "lvx--supermicro20239.replit.app",
    "port": 443,
    "kem_public_key_hex": n2_kem
})
step("N1 add N2 comme peer", s in (200, 201), str(d)[:100])

s, d = post(N2 + "/api/v1/p2p/peers", {
    "host": "lvx--supermicro20238.replit.app",
    "port": 443,
    "kem_public_key_hex": n1_kem
})
step("N2 add N1 comme peer", s in (200, 201), str(d)[:100])

time.sleep(1)
s, d = get(N1 + "/api/v1/p2p/peers")
n1_peers1 = d.get("count", len(d.get("peers", [])))
step("N1 peers apres connexion", n1_peers1 >= 1, f"peers={n1_peers1}")

s, d = get(N2 + "/api/v1/p2p/peers")
n2_peers1 = d.get("count", len(d.get("peers", [])))
step("N2 peers apres connexion", n2_peers1 >= 1, f"peers={n2_peers1}")

# ─── 4. APPRENTISSAGE + MINAGE SUR N1 ─────────────────────────
print("\n--- [4] APPRENTISSAGE + MINAGE SUR N1 ---")
graph_id = ""
bloc_ok = False
n1_blk1 = n1_blk0

if n1_addr:
    s, d = post(N1 + "/api/v1/ir/learn", {
        "wallet_address": n1_addr,
        "content": (
            "Test P2P reel ARTCB 2026-08-05. "
            "Deux noeuds Replit connectes en production. "
            "Noeud N1=supermicro20238 Noeud N2=supermicro20239. "
            "Blockchain PoL post-quantique ML-DSA-65."
        ),
        "visibility": "public"
    })
    graph_id = d.get("graph_id", "") if s == 200 else ""
    # block_index retourne directement par /ir/learn (encode+store combine)
    bloc_idx_direct = d.get("block_index", "?") if s == 200 else "?"
    step("N1 ir/learn", s == 200, f"graph_id={graph_id[:30] if graph_id else 'N/A'} block_index={bloc_idx_direct} status={s}")

    # /ir/learn grave deja le bloc — si block_index recu, on considere le bloc grave
    if graph_id and bloc_idx_direct != "?":
        bloc_ok = True
        step("N1 bloc PUBLIC grave", True, f"index={bloc_idx_direct} (via ir/learn)")
    elif graph_id:
        # Fallback : essayer /store si /ir/learn n'a pas grave (pas de block_index)
        s2, d2 = post(N1 + "/api/v1/store", {
            "wallet_address": n1_addr,
            "graph_id": graph_id,
            "visibility": "public"
        })
        bloc_ok = s2 == 200
        bloc_idx = d2.get("block_index", d2.get("index", "?"))
        step("N1 bloc PUBLIC grave", bloc_ok, f"index={bloc_idx} | {str(d2)[:80]}")
    else:
        step("N1 bloc PUBLIC grave", False, "skip — pas de graph_id")
else:
    step("N1 ir/learn", False, "skip — pas de wallet")
    step("N1 bloc PUBLIC grave", False, "skip")

# ─── 5. CHAIN N1 APRES MINAGE ─────────────────────────────────
print("\n--- [5] CHAIN N1 APRES MINAGE ---")
s, d = get(N1 + "/api/v1/chain")
n1_blk1 = d.get("count", len(d.get("blocks", [])))
step("N1 blocs apres minage", s == 200, f"blocs={n1_blk1} (init={n1_blk0}) delta={n1_blk1 - n1_blk0}")

# ─── 6. SYNC N2 DEPUIS N1 ─────────────────────────────────────
print("\n--- [6] SYNC N2 DEPUIS N1 ---")
s, d = post(N2 + "/api/v1/p2p/sync", {})
sync_ok = s == 200
sync_detail = ""
if sync_ok and "results" in d:
    for pr in d["results"]:
        pull = pr.get("pull", {})
        sync_detail = (
            f"received={pull.get('received', 0)} "
            f"imported={pull.get('imported', 0)} "
            f"ok={pr.get('ok', False)}"
        )
step("N2 p2p/sync", sync_ok, sync_detail or str(d)[:150])

time.sleep(2)
s, d = get(N2 + "/api/v1/chain")
n2_blk1 = d.get("count", len(d.get("blocks", [])))
step("N2 blocs apres sync", s == 200, f"blocs={n2_blk1} (init={n2_blk0}) delta={n2_blk1 - n2_blk0}")

# ─── 7. BLOC PRIVE SUR N1 ─────────────────────────────────────
print("\n--- [7] BLOC PRIVE N1 (ne doit PAS aller sur N2) ---")
n1_blk1_priv = n1_blk1
if n1_addr:
    # /ir/learn grave directement (encode+store combine) — visibility=private
    s, d = post(N1 + "/api/v1/ir/learn", {
        "wallet_address": n1_addr,
        "content": "Contenu prive ARTCB test. Ne pas synchroniser sur N2.",
        "visibility": "private"
    })
    priv_ok = s == 200 and d.get("block_index") is not None
    priv_idx = d.get("block_index", "?")
    step("N1 bloc PRIVE grave", priv_ok, f"index={priv_idx} visibility=private")

    # Nouvelle sync N2 — le bloc prive NE doit PAS etre recu
    time.sleep(1)
    s, d = post(N2 + "/api/v1/p2p/sync", {})
    time.sleep(2)
    s, d = get(N2 + "/api/v1/chain")
    n2_blk_after_priv = d.get("count", len(d.get("blocks", [])))
    step("N2 blocs APRES sync bloc prive", s == 200,
         f"blocs={n2_blk_after_priv} (attendu={n2_blk1} — prive non transmis)")
else:
    step("N1 bloc PRIVE grave", False, "skip — pas de wallet")
    n2_blk_after_priv = n2_blk1

# ─── 8. SANTE FINALE ──────────────────────────────────────────
print("\n--- [8] SANTE FINALE ---")
s, d = get(N1 + "/api/v1/health")
step("N1 health", s == 200, d.get("status", "?"))

s, d = get(N2 + "/api/v1/health")
step("N2 health", s == 200, d.get("status", "?"))

s, d = get(N1 + "/api/v1/p2p/peers")
n1_pf = d.get("count", len(d.get("peers", [])))
step("N1 peers final", s == 200, f"peers={n1_pf}")

s, d = get(N2 + "/api/v1/p2p/peers")
n2_pf = d.get("count", len(d.get("peers", [])))
step("N2 peers final", s == 200, f"peers={n2_pf}")

s, d = get(N1 + "/api/v1/dashboard/mining/status")
step("N1 mining/status", s == 200, f"block_count={d.get('block_count',0)} reward={d.get('current_reward_artcb',0)} ARTCB")

s, d = get(N2 + "/api/v1/dashboard/mining/status")
step("N2 mining/status", s == 200, f"block_count={d.get('block_count',0)} reward={d.get('current_reward_artcb',0)} ARTCB")

# ─── BILAN ─────────────────────────────────────────────────────
ok_count = sum(1 for r in results if r["ok"])
total = len(results)
ts_end = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
duree = int(time.time()) - int(time.mktime(time.strptime(ts_start, "%Y-%m-%dT%H:%M:%SZ")))

print()
print("=" * 64)
print(f"   BILAN FINAL : {ok_count}/{total} etapes OK")
print(f"   N1 blocs   : {n1_blk0} -> {n1_blk1}    N2 blocs : {n2_blk0} -> {n2_blk1}")
print(f"   P2P        : N1 peers={n1_pf}   N2 peers={n2_pf}")
print(f"   Sync N2    : blocs recus = {n2_blk1 - n2_blk0}")
print(f"   Bloc prive : N2 ne recoit PAS les blocs prives = {n2_blk_after_priv == n2_blk1}")
print(f"   Duree      : {duree}s")
print(f"   Fin        : {ts_end}")
print("=" * 64)

output = {
    "test": "test_reel_p2p_2noeuds_replit",
    "ts_start": ts_start,
    "ts_end": ts_end,
    "duree_secondes": duree,
    "n1": {
        "url": N1, "node_id": n1_id,
        "blocs_init": n1_blk0, "blocs_final": n1_blk1,
        "peers_final": n1_pf,
        "wallet": n1_addr[:40] + "..." if n1_addr else ""
    },
    "n2": {
        "url": N2, "node_id": n2_id,
        "blocs_init": n2_blk0, "blocs_final": n2_blk1,
        "peers_final": n2_pf,
        "wallet": n2_addr[:40] + "..." if n2_addr else ""
    },
    "conclusions": {
        "p2p_connected": n1_pf >= 1 and n2_pf >= 1,
        "bloc_mine_n1": n1_blk1 > n1_blk0,
        "sync_n2_received_public": n2_blk1 > n2_blk0,
        "private_bloc_not_synced": n2_blk_after_priv == n2_blk1
    },
    "ok_count": ok_count,
    "total": total,
    "steps": results
}
ts_log = ts_start.replace(":", "").replace("-", "").replace("T", "_")[:15]
log_file = f"logs/test_replit_p2p_reel_{ts_log}.json"
with open(log_file, "w") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
print(f"\nResultats sauvegardes : {log_file}")
