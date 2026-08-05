# PROMPT — Agent Replit N1 (lvx--supermicro20238.replit.app)
> Ce prompt est **dédié à l'agent Replit du nœud N1**. Copie-colle-le entier dans l'agent Replit de la Replit `Supermicro2026368` (N1).

---

## IDENTITÉ DE CE NŒUD

- **node_id :** `node_57ee00fe2d5b`
- **URL publique :** `https://lvx--supermicro20238.replit.app`
- **Rôle :** Nœud N1 — source de blocs, testeur P2P vers N2
- **Pair connu :** `https://lvx--supermicro20239.replit.app` (N2)

---

## ÉTAPE 0 — PULL DERNIER CODE

```bash
cd /home/user/artcb  # ou le répertoire du repo
git pull origin main
echo "Commit actuel : $(git rev-parse --short HEAD)"
# Attendu : bb3d2dc ou plus récent
```

---

## ÉTAPE 1 — VÉRIFIER LE DÉMARRAGE

```bash
# L'API doit déjà tourner (replit_start.sh la démarre automatiquement)
curl -s https://lvx--supermicro20238.replit.app/api/v1/health | python3 -m json.tool
# Attendu : {"status":"ok","debug":true,...}
```

---

## ÉTAPE 2 — TESTS LOCAUX N1 (tous les endpoints)

Lance ces tests depuis N1 sur lui-même :

```bash
# Santé de base
curl -s https://lvx--supermicro20238.replit.app/health | python3 -m json.tool
curl -s https://lvx--supermicro20238.replit.app/api/v1/health | python3 -m json.tool

# Chaîne
curl -s https://lvx--supermicro20238.replit.app/api/v1/chain | python3 -m json.tool
curl -s https://lvx--supermicro20238.replit.app/api/v1/chain/status | python3 -m json.tool
curl -s https://lvx--supermicro20238.replit.app/api/v1/chain/blocks | python3 -m json.tool

# Nœud
curl -s https://lvx--supermicro20238.replit.app/api/v1/node/status | python3 -m json.tool
# Attendu : {"node_id":"node_57ee00fe2d5b","version":"0.3.0","debug":true,"status":"running"}

# P2P
curl -s https://lvx--supermicro20238.replit.app/api/v1/p2p/status | python3 -m json.tool
curl -s https://lvx--supermicro20238.replit.app/api/v1/p2p/peers | python3 -m json.tool

# Wallets
curl -s https://lvx--supermicro20238.replit.app/api/v1/wallet/list | python3 -m json.tool
curl -s -X POST https://lvx--supermicro20238.replit.app/api/v1/wallet/create \
  -H "Content-Type: application/json" \
  -d '{"name":"n1_test_agent_$(date +%s)"}' | python3 -m json.tool

# PoL + Dashboard
curl -s https://lvx--supermicro20238.replit.app/api/v1/pol/score | python3 -m json.tool
curl -s https://lvx--supermicro20238.replit.app/api/v1/dashboard/mining/status | python3 -m json.tool
curl -s https://lvx--supermicro20238.replit.app/api/v1/dashboard/logs/demo-live | python3 -m json.tool
```

---

## ÉTAPE 3 — MINAGE (apprendre + graver un bloc public)

```bash
# Créer un wallet frais pour le test
WALLET=$(curl -s -X POST https://lvx--supermicro20238.replit.app/api/v1/wallet/create \
  -H "Content-Type: application/json" \
  -d '{"name":"n1_mine_test"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['address'])")
echo "Wallet N1 test : $WALLET"

# Encoder + graver un bloc public via /ir/learn
curl -s -X POST https://lvx--supermicro20238.replit.app/api/v1/ir/learn \
  -H "Content-Type: application/json" \
  -d "{\"wallet_address\":\"$WALLET\",\"content\":\"Test N1 agent $(date -u +%Y%m%dT%H%M%SZ)\",\"visibility\":\"public\"}" \
  | python3 -m json.tool
# Attendu : {"status":"ok","block_index":N,"pol_score":>0,"visibility":"public"}
```

---

## ÉTAPE 4 — TEST P2P N1 → N2

```bash
# Ajouter N2 comme pair
curl -s -X POST https://lvx--supermicro20238.replit.app/api/v1/p2p/peers \
  -H "Content-Type: application/json" \
  -d '{"host":"lvx--supermicro20239.replit.app","port":443,"protocol":"https"}' \
  | python3 -m json.tool

# Vérifier la connexion
curl -s https://lvx--supermicro20238.replit.app/api/v1/p2p/peers | python3 -m json.tool
# Attendu : peers=[{peer_id: "peer_lvx--supermicro20239_replit_app_443",...}]

# Synchroniser N2 depuis N1 (depuis N2's perspective)
curl -s -X POST https://lvx--supermicro20239.replit.app/api/v1/p2p/sync \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool
```

---

## ÉTAPE 5 — ROTATION DE CLÉ (test sécurité)

```bash
# Test : rotation sans signature → DOIT être refusée (HTTP 422)
curl -s -X POST https://lvx--supermicro20238.replit.app/api/v1/governance/user-key-rotation \
  -H "Content-Type: application/json" \
  -d '{"old_address":"artcb1test","new_address":"artcb1test2","signature_hex":""}' | python3 -m json.tool
# Attendu : HTTP 422 Unprocessable Entity (pas 200 — jamais en mode dev ou non)
```

---

## ÉTAPE 6 — RAPPORT À REMONTER

Crée un fichier `n1_test_report_YYYYMMDD_HHMMSS.txt` avec :

```
=== RAPPORT AGENT N1 ===
Timestamp : <date -u>
Commit    : <git rev-parse --short HEAD>
node_id   : node_57ee00fe2d5b
Endpoints : <N>/13 OK
Mining    : OK | bloc_index=<N> | pol_score=<X>
P2P N2    : connected=<true/false> | peers=<N>
Sécurité  : rotation-sans-sig → HTTP <code> (attendu: 422)
Anomalies : <liste ou AUCUNE>
```

---

## RÈGLES ABSOLUES

1. **Toujours en mode DEBUG** (`debug=true` dans les réponses)
2. **Jamais de mock** — tous les tests appellent l'API réelle
3. **Rotation sans signature → HTTP 422** obligatoirement
4. **8 skipped bridges live** dans pytest = NORMAL (nécessitent `ARTCB_LIVE_TESTS=1`)
5. Si un endpoint retourne 404, le signaler — ce n'est pas normal pour la liste ci-dessus

---

*ARTCB — Nœud N1 — commit bb3d2dc — 2026-08-05*
