# PROMPT — Agent Replit N2 (lvx--supermicro20239.replit.app)
> Ce prompt est **dédié à l'agent Replit du nœud N2**. Copie-colle-le entier dans l'agent Replit de la Replit `Supermicro20239` (N2).
> **Mis à jour : 2026-08-06 — v0.3.1 — rapport 107 (authentification, seed_hex)**

---

## IDENTITÉ DE CE NŒUD

- **node_id :** `node_1eb8e5ca44e4`
- **URL publique :** `https://lvx--supermicro20239.replit.app`
- **Rôle :** Nœud N2 — récepteur de sync P2P, validateur depuis N1
- **Pair connu :** `https://lvx--supermicro20238.replit.app` (N1)
- **Projet LoopQA :** `proj-artcb-replit-n2-live-tests-msgawasn`
- **URL LoopQA :** `https://qa.replay.io/p/proj-artcb-replit-n2-live-tests-msgawasn/overview`

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
curl -s https://lvx--supermicro20239.replit.app/api/v1/health | python3 -m json.tool
# Attendu : {"status":"ok","debug":true,...}
```

---

## ÉTAPE 2 — TESTS LOCAUX N2 (tous les endpoints)

Lance ces tests depuis N2 sur lui-même :

```bash
# Santé
curl -s https://lvx--supermicro20239.replit.app/health | python3 -m json.tool
curl -s https://lvx--supermicro20239.replit.app/api/v1/health | python3 -m json.tool

# Chaîne + nouveaux endpoints
curl -s https://lvx--supermicro20239.replit.app/api/v1/chain | python3 -m json.tool
curl -s https://lvx--supermicro20239.replit.app/api/v1/chain/status | python3 -m json.tool
curl -s https://lvx--supermicro20239.replit.app/api/v1/chain/blocks | python3 -m json.tool

# Nœud — CRITIQUE : doit retourner node_1eb8e5ca44e4 et PAS matcher /node/{id}
curl -s https://lvx--supermicro20239.replit.app/api/v1/node/status | python3 -m json.tool
# Attendu : {"node_id":"node_1eb8e5ca44e4","version":"0.3.0","debug":true,"status":"running"}

# P2P
curl -s https://lvx--supermicro20239.replit.app/api/v1/p2p/status | python3 -m json.tool
curl -s https://lvx--supermicro20239.replit.app/api/v1/p2p/peers | python3 -m json.tool

# Wallets
curl -s https://lvx--supermicro20239.replit.app/api/v1/wallet/list | python3 -m json.tool
curl -s -X POST https://lvx--supermicro20239.replit.app/api/v1/wallet/create \
  -H "Content-Type: application/json" \
  -d '{"name":"n2_test_agent"}' | python3 -m json.tool

# PoL + Dashboard
curl -s https://lvx--supermicro20239.replit.app/api/v1/pol/score | python3 -m json.tool
curl -s https://lvx--supermicro20239.replit.app/api/v1/dashboard/mining/status | python3 -m json.tool
curl -s https://lvx--supermicro20239.replit.app/api/v1/dashboard/logs/demo-live | python3 -m json.tool
```

---

## ÉTAPE 3 — MINAGE SUR N2

```bash
# Wallet frais pour ce test
WALLET=$(curl -s -X POST https://lvx--supermicro20239.replit.app/api/v1/wallet/create \
  -H "Content-Type: application/json" \
  -d '{"name":"n2_mine_test"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['address'])")
echo "Wallet N2 test : $WALLET"

# ir/learn — encode + grave un bloc public
curl -s -X POST https://lvx--supermicro20239.replit.app/api/v1/ir/learn \
  -H "Content-Type: application/json" \
  -d "{\"wallet_address\":\"$WALLET\",\"content\":\"Test N2 agent $(date -u +%Y%m%dT%H%M%SZ)\",\"visibility\":\"public\"}" \
  | python3 -m json.tool
# Attendu : block_index=N, pol_score>0
```

---

## ÉTAPE 4 — RECEVOIR LA SYNC DEPUIS N1

```bash
# Ajouter N1 comme pair de N2
curl -s -X POST https://lvx--supermicro20239.replit.app/api/v1/p2p/peers \
  -H "Content-Type: application/json" \
  -d '{"host":"lvx--supermicro20238.replit.app","port":443,"protocol":"https"}' \
  | python3 -m json.tool

# Déclencher la sync P2P
curl -s -X POST https://lvx--supermicro20239.replit.app/api/v1/p2p/sync \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool
# Si N1 a miné des blocs publics, N2 devrait les recevoir
```

---

## ÉTAPE 5 — TESTS GOUVERNANCE (sécurité)

```bash
# Rotation utilisateur sans signature → DOIT être refusée HTTP 422
curl -s -w "\nHTTP_CODE:%{http_code}" -X POST \
  https://lvx--supermicro20239.replit.app/api/v1/governance/user-key-rotation \
  -H "Content-Type: application/json" \
  -d '{"old_address":"artcb1test","new_address":"artcb1test2","signature_hex":""}' \
  | tail -1
# Attendu : HTTP_CODE:422

# Rotation créateur sans signature → DOIT être refusée HTTP 422
curl -s -w "\nHTTP_CODE:%{http_code}" -X POST \
  https://lvx--supermicro20239.replit.app/api/v1/governance/creator-key-rotation \
  -H "Content-Type: application/json" \
  -d '{"old_address":"artcb1test","new_address":"artcb1test2","signature_hex":""}' \
  | tail -1
# Attendu : HTTP_CODE:422

# Vérifier la chaîne (intégrité)
curl -s https://lvx--supermicro20239.replit.app/api/v1/chain/verify | python3 -m json.tool
# Attendu : {"valid":true,...}
```

---

## ÉTAPE 6 — VÉRIFIER LOOPQA (tests IA sur le frontend)

LoopQA explore le dashboard de ce nœud en temps réel.

```bash
# Voir l'état de l'exploration IA sur le dashboard
curl -s -H "Authorization: Bearer lqa_e1d739fe4152328d0d7579549754972da625cde4aa6bc02b" \
  -H "Content-Type: application/json" \
  -X POST https://qa.replay.io/api/mcp \
  -d '{"jsonrpc":"2.0","method":"tools/call","id":1,"params":{"name":"get_project_status","arguments":{"project_id":"proj-artcb-replit-n2-live-tests-msgawasn"}}}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['result']['content'][0]['text'])"

# Lister les bugs détectés par LoopQA IA
curl -s -H "Authorization: Bearer lqa_e1d739fe4152328d0d7579549754972da625cde4aa6bc02b" \
  -H "Content-Type: application/json" \
  -X POST https://qa.replay.io/api/mcp \
  -d '{"jsonrpc":"2.0","method":"tools/call","id":2,"params":{"name":"list_bugs","arguments":{"project_id":"proj-artcb-replit-n2-live-tests-msgawasn","status":"open"}}}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['result']['content'][0]['text'])"
```

Interface web LoopQA : https://qa.replay.io/p/proj-artcb-replit-n2-live-tests-msgawasn/overview

---

## ÉTAPE 7 — RAPPORT À REMONTER

Crée un fichier `n2_test_report_YYYYMMDD_HHMMSS.txt` avec :

```
=== RAPPORT AGENT N2 ===
Timestamp  : <date -u>
Commit     : <git rev-parse --short HEAD>
node_id    : node_1eb8e5ca44e4
Endpoints  : <N>/13 OK
Mining     : OK | bloc_index=<N> | pol_score=<X>
P2P N1     : connected=<true/false> | peers=<N>
Sync N1→N2 : blocs_reçus=<N> | blocs_privés_propagés=<true/false>
Gouvernance: rotation-sans-sig → HTTP <code> (attendu: 422)
LoopQA     : bugs_ouverts=<N> | explorations_actives=<N>
Anomalies  : <liste ou AUCUNE>
```

---

## VARIABLES D'ENVIRONNEMENT ATTENDUES

| Variable | Valeur | Rôle |
|----------|--------|------|
| `ARTCB_DEBUG` | `true` | Logs détaillés |
| `LOOPQA_API_TOKEN` | `lqa_e1d739fe4152328d0d7579549754972da625cde4aa6bc02b` | LoopQA |
| `LOOPQA_PROJECT_N2` | `proj-artcb-replit-n2-live-tests-msgawasn` | ID projet |
| `LOOPQA_API_URL` | `https://qa.replay.io/api/mcp` | Endpoint MCP |
| `ARTCB_ANTI_SYBIL_AI_BYPASS` | `false` | Sécurité anti-Sybil active |
| `ARTCB_MIN_BLOCK_INTERVAL_SEC` | `60` | Délai entre blocs |

---

## ÉTAPE 8 — TEST PRÉ-FILTRAGE ANTI-SYBIL (rapport 109 — nouveau)

```bash
# Vérifier que le pré-filtre anti-Sybil est actif sur N2
# Un wallet qui vient de miner ne doit PAS recevoir de job — il est filtré AVANT

ADDR=$(curl -s -X POST https://lvx--supermicro20239.replit.app/api/v1/wallet/create \
  -H "Content-Type: application/json" \
  -d '{"name":"n2_prefilter_test"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('address',''))")
echo "Wallet: $ADDR"

# Premier bloc
curl -s -X POST https://lvx--supermicro20239.replit.app/api/v1/ir/learn \
  -H "Content-Type: application/json" \
  -d "{\"wallet_address\":\"$ADDR\",\"content\":\"Bloc N2 pre-filter $(date -u +%s)\"}" \
  | python3 -m json.tool

# Second bloc immédiat → wallet doit être exclu AVANT calcul, pas après
curl -s -X POST https://lvx--supermicro20239.replit.app/api/v1/ir/learn \
  -H "Content-Type: application/json" \
  -d "{\"wallet_address\":\"$ADDR\",\"content\":\"Bloc N2 pre-filter #2 $(date -u +%s)\"}" \
  | python3 -m json.tool
# Attendu : bloc gravé avec liste contributeurs vide ou autre wallet, JAMAIS d'annulation

# Métriques anti-sybil
curl -s https://lvx--supermicro20239.replit.app/api/v1/security/anti-sybil/metrics \
  | python3 -m json.tool
```

---

## RÈGLES ABSOLUES

1. **debug=true** dans toutes les réponses — le mode debug est PERMANENT
2. **Jamais de mock** — tous les appels sont réels
3. **Rotation sans signature → HTTP 422** — sans exception, jamais en mode dev
4. **8 skipped pytest** = bridges live intentionnels, NORMAL
5. **LoopQA explore vraiment le dashboard** — vérifier sur qa.replay.io que les crédits baissent
6. **`/api-keys/generate` sans session → HTTP 401** — rapport 107
7. **Wallet en cooldown → exclu AVANT attribution job** — rapport 109

---

*ARTCB — Nœud N2 — v0.3.2 — rapport 109 — commit 9a119ab — 2026-08-06*
*LoopQA projet : proj-artcb-replit-n2-live-tests-msgawasn*
