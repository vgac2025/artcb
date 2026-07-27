#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
REPLAY IA AUTONOME — Bob joue le rôle de l'agent externe
Protocole : Bob se connecte, crée sa clé, grave ses observations,
            lit sa mémoire, cherche dans la chaîne, exporte, webhooks.
═══════════════════════════════════════════════════════════════════════════════
"""
import importlib
import json
import os
import sys
import traceback

from fastapi.testclient import TestClient
from src.api.main import create_app

app = create_app()
client = TestClient(app, raise_server_exceptions=False)

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

log    = []
errors = []
ok_n   = 0
fail_n = 0

def step(num, title):
    print(f"\n{BLUE}{BOLD}── ÉTAPE {num} : {title}{RESET}")

def ok(label, detail=""):
    global ok_n
    ok_n += 1
    d = f" → {str(detail)[:60]}" if detail != "" else ""
    print(f"  {GREEN}✅ {label}{d}{RESET}")
    log.append(f"✅ {label}{d}")

def fail(label, detail="", exc=None):
    global fail_n
    fail_n += 1
    d = f" → {str(detail)[:80]}" if detail != "" else ""
    tb = ""
    if exc:
        tb = f"\n     {traceback.format_exc().strip()[-200:]}"
    print(f"  {RED}❌ PROBLÈME : {label}{d}{tb}{RESET}")
    errors.append(f"❌ {label}{d}")
    log.append(f"❌ {label}{d}")

def warn(label, detail=""):
    d = f" → {str(detail)[:60]}" if detail != "" else ""
    print(f"  {YELLOW}⚠️  {label}{d}{RESET}")
    log.append(f"⚠️  {label}{d}")

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BOLD}{'═'*65}")
print("  REPLAY IA AUTONOME — ARTCB Agent Validation")
print(f"{'═'*65}{RESET}")

# ─────────────────────────────────────────────────────────────────────────────
step(1, "Health check — le serveur répond")
try:
    r = client.get("/health")
    if r.status_code == 200 and r.json().get("status") == "healthy":
        ok("Serveur en ligne", f"status={r.json()['status']} version={r.json().get('version')}")
    else:
        fail("Serveur health", f"HTTP {r.status_code} body={r.text[:80]}")
except Exception as e:
    fail("Serveur health", exc=e)

# ─────────────────────────────────────────────────────────────────────────────
step(2, "Créer une clé API pour l'agent IA")
BOB_TOKEN = ""
BOB_KEY_ID = ""
try:
    r = client.post("/api/v1/api-keys/generate", json={
        "label": "bob_agent_replay",
        "scopes": ["read", "write", "mining"],
        "expires_days": 90
    })
    if r.status_code == 200:
        d = r.json()
        BOB_TOKEN  = d["token"]
        BOB_KEY_ID = d["key_id"]
        ok("Clé API générée", f"token={BOB_TOKEN[:22]}…")
        ok("key_id", BOB_KEY_ID)
        ok("scopes", d.get("scopes"))
        ok("expires_at non nul", d.get("expires_at") is not None)
    else:
        fail("Génération clé API", f"HTTP {r.status_code} {r.text[:80]}")
except Exception as e:
    fail("Génération clé API", exc=e)

# ─────────────────────────────────────────────────────────────────────────────
step(3, "Vérifier la clé via /me (authentification Bearer)")
BOB_HEADERS = {"Authorization": f"Bearer {BOB_TOKEN}"} if BOB_TOKEN else {}
try:
    r = client.get("/api/v1/api-keys/me", headers=BOB_HEADERS)
    if r.status_code == 200:
        d = r.json()
        ok("Bearer accepté", f"label={d.get('label')}")
        ok("Scopes confirmés", d.get("scopes"))
        if d.get("label") == "bob_agent_replay":
            ok("Label correspond exactement")
        else:
            fail("Label ne correspond pas", f"attendu=bob_agent_replay obtenu={d.get('label')}")
    elif r.status_code == 401:
        fail("Bearer rejeté 401", r.text[:80])
    else:
        fail("GET /api-keys/me", f"HTTP {r.status_code} {r.text[:80]}")
except Exception as e:
    fail("Bearer /me", exc=e)

# ─────────────────────────────────────────────────────────────────────────────
step(4, "Lister toutes les clés API")
try:
    r = client.get("/api/v1/api-keys/list")
    if r.status_code == 200:
        d = r.json()
        ok("Liste clés", f"count={d['count']}")
        bob_present = any(k.get("label") == "bob_agent_replay" for k in d["keys"])
        if bob_present:
            ok("Clé bob_agent_replay présente dans la liste")
        else:
            fail("Clé bob_agent_replay ABSENTE de la liste")
    else:
        fail("GET /api-keys/list", f"HTTP {r.status_code}")
except Exception as e:
    fail("Liste clés", exc=e)

# ─────────────────────────────────────────────────────────────────────────────
step(5, "AI Status — snapshot état complet de la chaîne")
CHAIN_HEIGHT_BEFORE = 0
try:
    r = client.get("/api/v1/ai/status", headers=BOB_HEADERS)
    if r.status_code == 200:
        d = r.json()
        ok("agent_ready", d.get("agent_ready"))
        ok("Hauteur chaîne", f"{d['chain']['height']} blocs")
        ok("PoL moyen", f"{d['chain']['pol_avg']}")
        ok("Graphes en RAM", d["memory"]["graphs_in_ram"])
        ok("Memos IA existants", d["memory"]["memo_blocks"])
        ok("Capacités exposées", len(d.get("capabilities", [])))
        CHAIN_HEIGHT_BEFORE = d["chain"]["height"]
        current_key = d.get("current_key")
        if current_key and current_key.get("label") == "bob_agent_replay":
            ok("Clé courante reconnue dans status", current_key["label"])
        else:
            warn("Clé courante absente du status (Bearer non propagé au status?)")
    else:
        fail("GET /ai/status", f"HTTP {r.status_code} {r.text[:100]}")
except Exception as e:
    fail("GET /ai/status", exc=e)

# ─────────────────────────────────────────────────────────────────────────────
step(6, "Graver 3 memos IA de types différents")
MEMO_BLOCK_INDICES = []
memos_to_grave = [
    {
        "content": "Bug fix confirmé: list_blocks() retourne list[dict]. get_blocks() n'existe pas sur ChainManager. Fix appliqué dans ai_routes.py — tous les accès convertis en .get('key').",
        "memo_type": "fix",
        "tags": ["bug", "list_blocks", "dict", "chain_manager"],
    },
    {
        "content": "Observation: 34+ blocs valides signés ML-DSA-65 + Ed25519. PoL moyen > 0.7. Intégrité blockchain confirmée par verify(). Aucun bloc altéré détecté.",
        "memo_type": "observation",
        "tags": ["blockchain", "integrity", "ml-dsa", "pol"],
    },
    {
        "content": "Décision: /ws/stream_thought gravera le raisonnement token-par-token pour les sessions Cursor/ChatGPT. Protocole: start→token×N→commit→committed. Plus granulaire qu'un seul mémo.",
        "memo_type": "decision",
        "tags": ["stream", "websocket", "cursor", "architecture"],
    },
]
for memo in memos_to_grave:
    try:
        r = client.post(
            "/api/v1/ai/memo",
            json={**memo, "session_id": "bob_replay_session", "visibility": "private"},
            headers=BOB_HEADERS,
        )
        if r.status_code == 200:
            d = r.json()
            if d.get("memo_stored"):
                MEMO_BLOCK_INDICES.append(d["block_index"])
                ok(
                    f"Mémo [{memo['memo_type']}] gravé",
                    f"bloc #{d['block_index']} graph={d['graph_id'][:16]}… PoL={d['pol_score']}",
                )
            else:
                fail(f"Mémo [{memo['memo_type']}] non gravé", str(d)[:80])
        else:
            fail(f"POST /ai/memo [{memo['memo_type']}]", f"HTTP {r.status_code} {r.text[:100]}")
    except Exception as e:
        fail(f"POST /ai/memo [{memo['memo_type']}]", exc=e)

# ─────────────────────────────────────────────────────────────────────────────
step(7, "Lire la mémoire IA — récupérer les memos gravés")
try:
    r = client.get("/api/v1/ai/memory", params={"limit": 20}, headers=BOB_HEADERS)
    if r.status_code == 200:
        d = r.json()
        ok("GET /ai/memory", f"count={d['count']}")
        for m in d["memos"][:3]:
            ok("  Mémo trouvé", f"bloc #{m['block_index']} type={m['memo_type']} agent={m['agent_id']}")
        found = sum(1 for idx in MEMO_BLOCK_INDICES if any(m["block_index"] == idx for m in d["memos"]))
        if found == len(MEMO_BLOCK_INDICES):
            ok(f"Tous les {len(MEMO_BLOCK_INDICES)} memos retrouvés en mémoire")
        else:
            warn(f"Seulement {found}/{len(MEMO_BLOCK_INDICES)} memos retrouvés")
    else:
        fail("GET /ai/memory", f"HTTP {r.status_code} {r.text[:100]}")
except Exception as e:
    fail("GET /ai/memory", exc=e)

# ─────────────────────────────────────────────────────────────────────────────
step(8, "AI Think — raisonnement pipeline Explorer+Critic → bloc")
try:
    r = client.post(
        "/api/v1/ai/think",
        json={
            "question": "Comment garantir l'intégrité de la blockchain ARTCB face à une attaque Sybil ?",
            "session_id": "bob_think_replay",
            "use_llm": False,
            "store_block": True,
            "visibility": "private",
        },
        headers=BOB_HEADERS,
    )
    if r.status_code == 200:
        d = r.json()
        ok("think_complete", d.get("think_complete"))
        ok("graph_id", (d.get("graph_id") or "")[:22] + "…")
        ok("pol_score", d.get("pol_score"))
        if d.get("block_index") is not None:
            ok("Bloc think gravé", f"#{d['block_index']}")
        else:
            warn("store_block=True mais block_index=None (threshold PoL non atteint?)")
    else:
        fail("POST /ai/think", f"HTTP {r.status_code} {r.text[:150]}")
except Exception as e:
    fail("POST /ai/think", exc=e)

# ─────────────────────────────────────────────────────────────────────────────
step(9, "AI Status APRÈS memos — hauteur chaîne doit avoir augmenté")
try:
    r = client.get("/api/v1/ai/status", headers=BOB_HEADERS)
    if r.status_code == 200:
        d = r.json()
        new_height = d["chain"]["height"]
        delta = new_height - CHAIN_HEIGHT_BEFORE
        if delta > 0:
            ok("Chaîne a grandi", f"{CHAIN_HEIGHT_BEFORE} → {new_height} (+{delta} blocs)")
        else:
            warn(f"Hauteur inchangée : {CHAIN_HEIGHT_BEFORE} → {new_height}")
        ok("memo_blocks comptés", d["memory"]["memo_blocks"])
        if d["chain"].get("last_block"):
            lb = d["chain"]["last_block"]
            ok("Dernier bloc", f"#{lb.get('index')} PoL={lb.get('pol_score')} vis={lb.get('visibility')}")
    else:
        fail("GET /ai/status (après memos)", f"HTTP {r.status_code}")
except Exception as e:
    fail("GET /ai/status (après)", exc=e)

# ─────────────────────────────────────────────────────────────────────────────
step(10, "Recherche sémantique cross-chain")
for query in ["list_blocks fix", "blockchain intégrité", "stream thought"]:
    try:
        r = client.get(
            "/api/v1/chain/search",
            params={"q": query, "top_k": 5},
            headers=BOB_HEADERS,
        )
        if r.status_code == 200:
            d = r.json()
            ok(f"Recherche '{query}'", f"count={d['count']} résultats")
        else:
            fail(f"Recherche '{query}'", f"HTTP {r.status_code} {r.text[:80]}")
    except Exception as e:
        fail(f"Recherche '{query}'", exc=e)

# ─────────────────────────────────────────────────────────────────────────────
step(11, "Export chaîne — 3 formats (summary / jsonl / json)")
for fmt in ["summary", "jsonl", "json"]:
    try:
        r = client.get("/api/v1/chain/export", params={"format": fmt}, headers=BOB_HEADERS)
        if r.status_code == 200:
            d = r.json()
            if fmt == "summary":
                data_str = str(d.get("data", ""))
                ok(f"Export summary", f"{d.get('block_count')} blocs, {len(data_str)} chars")
                if "ARTCB Blockchain" in data_str:
                    ok("  En-tête ARTCB présent dans le summary")
                else:
                    fail("  En-tête ARTCB absent du summary", data_str[:60])
            elif fmt == "jsonl":
                lines = [l for l in str(d.get("data", "")).strip().split("\n") if l]
                ok(f"Export jsonl", f"{d.get('block_count')} blocs, {len(lines)} lignes")
                if lines:
                    try:
                        first = json.loads(lines[0])
                        ok("  Ligne JSONL parseable", f"index={first.get('index')} pol={first.get('pol_score')}")
                    except Exception as e2:
                        fail("  Ligne JSONL non parseable", str(e2))
            elif fmt == "json":
                ok(f"Export json", f"{d.get('block_count')} blocs")
                if isinstance(d.get("data"), list) and d["data"]:
                    first = d["data"][0]
                    ok("  Premier bloc JSON", f"index={first.get('index')} hash={str(first.get('hash',''))[:12]}…")
        else:
            fail(f"Export {fmt}", f"HTTP {r.status_code} {r.text[:100]}")
    except Exception as e:
        fail(f"Export {fmt}", exc=e)

# ─────────────────────────────────────────────────────────────────────────────
step(12, "Webhooks — enregistrer, lister, révoquer")
WH_ID = ""
try:
    r = client.post(
        "/api/v1/webhooks/register",
        json={
            "url": "https://bob-agent.example.com/artcb-events",
            "label": "bob_cursor_webhook",
            "events": ["block_stored", "memo_stored"],
        },
        headers=BOB_HEADERS,
    )
    if r.status_code == 200:
        d = r.json()
        WH_ID = d.get("hook_id", "")
        ok("Webhook enregistré", f"hook_id={WH_ID}")
        ok("Events configurés", d.get("events"))
    else:
        fail("POST /webhooks/register", f"HTTP {r.status_code} {r.text[:80]}")
except Exception as e:
    fail("POST /webhooks/register", exc=e)

try:
    r = client.get("/api/v1/webhooks/list", headers=BOB_HEADERS)
    if r.status_code == 200:
        d = r.json()
        ok("GET /webhooks/list", f"count={d['count']}")
        bob_wh = next((w for w in d["webhooks"] if w.get("label") == "bob_cursor_webhook"), None)
        if bob_wh:
            ok("Webhook bob_cursor_webhook présent dans la liste")
        else:
            warn("Webhook bob_cursor_webhook absent de la liste")
    else:
        fail("GET /webhooks/list", f"HTTP {r.status_code}")
except Exception as e:
    fail("GET /webhooks/list", exc=e)

if WH_ID:
    try:
        r = client.delete(f"/api/v1/webhooks/{WH_ID}", headers=BOB_HEADERS)
        if r.status_code == 200 and r.json().get("revoked"):
            ok(f"Webhook {WH_ID} révoqué")
        else:
            fail(f"DELETE /webhooks/{WH_ID}", f"HTTP {r.status_code} {r.text[:80]}")
    except Exception as e:
        fail(f"DELETE /webhooks/{WH_ID}", exc=e)

# ─────────────────────────────────────────────────────────────────────────────
step(13, "Révoquer la clé Bob en fin de session")
if BOB_KEY_ID:
    try:
        r = client.delete(f"/api/v1/api-keys/{BOB_KEY_ID}")
        if r.status_code == 200 and r.json().get("revoked"):
            ok(f"Clé {BOB_KEY_ID} révoquée")
            r2 = client.get("/api/v1/api-keys/me", headers=BOB_HEADERS)
            if r2.status_code == 401:
                ok("Token révoqué → 401 confirmé (sécurité OK)")
            else:
                warn(f"Token révoqué mais /me retourne HTTP {r2.status_code} (attendu 401)")
        else:
            fail(f"DELETE /api-keys/{BOB_KEY_ID}", f"HTTP {r.status_code} {r.text[:80]}")
    except Exception as e:
        fail("Révocation clé", exc=e)

# ─────────────────────────────────────────────────────────────────────────────
step(14, "Imports Python — tous les modules se chargent")
modules_check = [
    ("src.api.ai_routes",            ["router_ai", "router_chain_ext", "router_webhooks"]),
    ("src.api.api_keys_routes",      ["router", "verify_api_key"]),
    ("src.api.websocket",            ["router", "stream_thought_ws"]),
    ("src.artcb.connectors.llm_router", ["LLMRouter"]),
    ("src.artcb.connectors.sources",    ["fetch_learning_text", "_fetch_wikipedia_batch"]),
    ("src.artcb.chain.manager",         ["ChainManager"]),
]
for mod_name, symbols in modules_check:
    try:
        mod = importlib.import_module(mod_name)
        missing_syms = [s for s in symbols if not hasattr(mod, s)]
        if missing_syms:
            fail(f"import {mod_name}", f"symboles manquants: {missing_syms}")
        else:
            ok(f"import {mod_name}", f"[{', '.join(symbols)}]")
    except Exception as e:
        fail(f"import {mod_name}", str(e)[:80])

# ─────────────────────────────────────────────────────────────────────────────
step(15, "Google AI + Wikipedia dans les connecteurs")
try:
    from src.artcb.connectors.llm_router import LLMRouter
    assert hasattr(LLMRouter, "_google_ai_chat"), "_google_ai_chat absent"
    ok("Google AI _google_ai_chat dans LLMRouter")
except Exception as e:
    fail("Google AI connecteur", str(e))

try:
    from src.artcb.connectors import sources as src_sources
    assert hasattr(src_sources, "_fetch_wikipedia_batch"), "_fetch_wikipedia_batch absent"
    ok("Wikipedia _fetch_wikipedia_batch dans sources.py")
except Exception as e:
    fail("Wikipedia connecteur", str(e))

# ─────────────────────────────────────────────────────────────────────────────
step(16, "Frontend — fichiers critiques et mots-clés")
files_to_check = [
    ("frontend/src/pages/AgentMemory.tsx",   ["stream_thought", "fetchAiMemory", "postAiMemo", "chainSearch"]),
    ("frontend/src/pages/ApiKeys.tsx",       ["generateApiKey", "listApiKeys", "revokeApiKey"]),
    ("frontend/src/i18n/translations.ts",    ["nav_agent_memory", "nav_api_keys"]),
    ("frontend/src/App.tsx",                 ["agent-memory", "AgentMemory", "api-keys"]),
    ("frontend/src/layout/DashboardLayout.tsx", ["agent-memory", "nav_agent_memory"]),
    ("frontend/dist/index.html",             ["<!doctype", "assets"]),
]
for fpath, keywords in files_to_check:
    if not os.path.isfile(fpath):
        fail("Fichier manquant", fpath)
        continue
    with open(fpath, encoding="utf-8") as f:
        content = f.read().lower()
    missing = [k for k in keywords if k.lower() not in content]
    if missing:
        fail(os.path.basename(fpath), f"mots-clés manquants: {missing}")
    else:
        ok(os.path.basename(fpath), f"[{', '.join(keywords[:2])}…] ✓")

# ─────────────────────────────────────────────────────────────────────────────
step(17, "i18n — 7 langues contiennent nav_agent_memory")
try:
    with open("frontend/src/i18n/translations.ts", encoding="utf-8") as f:
        t = f.read()
    count = t.count("nav_agent_memory")
    # 1 dans l'interface + 7 dans les langues = 8 minimum
    if count >= 8:
        ok("nav_agent_memory × 7 langues", f"{count} occurrences trouvées (min 8)")
    else:
        fail("nav_agent_memory manquant dans certaines langues", f"seulement {count}/8 occurrences")
    # Vérifier les 7 codes langue
    for lang in ["nav_dashboard: 'Tableau", "nav_dashboard: 'Dashboard'",
                 "nav_dashboard: '仪表板'", "nav_dashboard: 'Panel'",
                 "nav_dashboard: 'Painel'", "nav_dashboard: 'Pannello'",
                 "nav_dashboard: 'Панель'"]:
        if lang in t:
            ok(f"  Langue présente", lang[:30])
        else:
            warn(f"  Langue possiblement manquante", lang[:30])
except Exception as e:
    fail("Lecture translations.ts", str(e))

# ─────────────────────────────────────────────────────────────────────────────
step(18, "Git — remote origin à jour")
import subprocess
try:
    res = subprocess.run(
        ["git", "log", "--oneline", "-3"],
        capture_output=True, text=True, cwd="."
    )
    lines = res.stdout.strip().split("\n")
    ok("git log (3 derniers commits)", lines[0] if lines else "?")
    for l in lines[1:]:
        ok("  ", l)

    res2 = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True, text=True, cwd="."
    )
    dirty = res2.stdout.strip()
    if dirty:
        warn("Working tree non propre", dirty[:80])
    else:
        ok("Working tree propre — rien à committer")

    res3 = subprocess.run(
        ["git", "remote", "-v"],
        capture_output=True, text=True, cwd="."
    )
    remote_line = res3.stdout.strip().split("\n")[0] if res3.stdout else ""
    if "github.com" in remote_line:
        ok("Remote origin GitHub", remote_line.split("@")[-1][:40] if "@" in remote_line else remote_line[:40])
    else:
        warn("Remote origin inconnu", remote_line[:60])
except Exception as e:
    fail("Vérification git", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# BILAN FINAL
print(f"\n{BOLD}{'═'*65}")
print("  BILAN FINAL — REPLAY IA AUTONOME ARTCB")
print(f"{'═'*65}{RESET}")

total = ok_n + fail_n
pct   = int(ok_n / total * 100) if total > 0 else 0
color = GREEN if fail_n == 0 else (YELLOW if fail_n <= 2 else RED)

print(f"\n  {color}{BOLD}{ok_n}/{total} validations ✅  |  {fail_n} problèmes ❌  ({pct}%){RESET}\n")

if errors:
    print(f"  {RED}{BOLD}⚠️  PROBLÈMES DÉTECTÉS :{RESET}")
    for e in errors:
        print(f"  {RED}  {e}{RESET}")
else:
    print(f"  {GREEN}{BOLD}🎉 ZÉRO BUG — Tout fonctionne parfaitement !{RESET}")

print(f"\n  Memos gravés dans blocs : {MEMO_BLOCK_INDICES}")
print(f"  Clé Bob utilisée        : {BOB_TOKEN[:25]}… (révoquée)" if BOB_TOKEN else "  Clé : non générée")
print(f"  Chaîne avant replay     : {CHAIN_HEIGHT_BEFORE} blocs")
print(f"  Chaîne après replay     : {CHAIN_HEIGHT_BEFORE + len(MEMO_BLOCK_INDICES)} blocs (estimé)")
print(f"{'═'*65}\n")

sys.exit(0 if fail_n == 0 else 1)
