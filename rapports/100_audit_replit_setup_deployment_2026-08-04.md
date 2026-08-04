# Rapport 100 — Audit Setup Replit + Déploiement Production + Guide Tests Multi-Nœuds

**Date :** 2026-08-04T12:00:00Z  
**Agent :** Replit Agent (agent cloud, session autonome)  
**Contexte :** Import GitHub → `https://github.com/vgac2025/lvx` → Replit  
**Avancement global :** ✅ Déploiement Replit réussi | ⚠️ Tests multi-nœuds : étapes préparées, non lancés  
**Rapport précédent :** 099_audit_smoke_hardcoding_placeholder_stub_2026_07_31.md  

---

## 🔬 Expertises mobilisées

| Domaine | Raison |
|---|---|
| DevOps / CI-CD Replit | Configuration workflow, autoscale, port mapping |
| NixOS / PEP 668 | Conflit pip.conf global `user=yes` dans venv |
| Compilateur C / GCC / OpenSSL | Compilation libartcb_chain.so (architecture 64-bit) |
| Cryptographie post-quantique | liboqs-python cmake auto-build (ML-DSA-65 / ML-KEM-768) |
| Python / FastAPI / uvicorn | Démarrage API, imports, fallback gracieux |
| React / TypeScript / Vite | Build frontend → dist/ statique servi par FastAPI |
| Analyse logs HTTP | Logs access uvicorn + deployment Replit autoscale |
| Blockchain P2P | Analyse état nœud, peers, sync, gossip |
| Sécurité | eval Doppler, PIP_USER, mode debug production |

---

## 1. Contexte — État AVANT l'intervention

Le projet a été importé depuis GitHub. Le `.replit` existant avait été généré par l'import automatique.

### 1.1 Problèmes bloquants au premier démarrage

| # | Fichier | Ligne(s) AVANT | Problème |
|---|---|---|---|
| A | `scripts/replit_start.sh` | `$PIP install -r requirements.txt -q` | Replit pip.conf force `user=yes` → ERREUR dans venv |
| B | `scripts/replit_start.sh` | `find /nix/store -name 'cc' ...` | find sur tout le store Nix = hang 5+ minutes |
| C | `requirements.txt` | `liboqs-python>=0.14.0` | pip install déclenche cmake build >10min + self-install auto lors de l'import |
| D | `.replit [deployment].run` | `pip install -r requirements.txt -q` (sans `--no-user`) | Même erreur PIP_USER sur déploiement autoscale |
| E | `.replit [deployment].run` | commande inline séparée du workflow | Déploiement ≠ workflow → drift de configuration |
| F | `.replit [nix]` | `channel = "stable-23_11"` | Canal Nix obsolète |
| G | `scripts/replit_start.sh` | `DOPPLER_TOKEN` seulement | Secret Replit nommé `DOPPLER_TOKEN_REPLIT`, non détecté |

### 1.2 Résultat AVANT corrections
```
[2/6] Installation des dépendances Python...
ERROR: Can not perform a '--user' install. User site-packages are not visible in this virtualenv.
[5/6] Compilation libartcb_chain.so...   ← HANG ici (find /nix/store ~5min)
```
→ Workflow timeout, port 5000 jamais ouvert.

---

## 2. Corrections appliquées — AVANT / APRÈS exhaustif

### 2.1 `scripts/replit_start.sh`

**AVANT :**
```bash
export PATH="$VENV/bin:$PATH"
PIP="$VENV/bin/pip"
PYTHON="$VENV/bin/python3"

$PIP install -r requirements.txt -q 2>&1 | grep -v "^Requirement already" | tail -5 || true
$PIP show litellm-ibm-bob &>/dev/null || $PIP install "litellm>=1.0.0" -q 2>/dev/null || true
```

**APRÈS :**
```bash
export PATH="$VENV/bin:$PATH"
PIP="$VENV/bin/pip"
PYTHON="$VENV/bin/python3"
# Override Replit global pip.conf (user = yes) which breaks venv installs
export PIP_USER=false

$PIP install --no-user -r requirements.txt -q 2>&1 | grep -v "^Requirement already" | tail -5 || true
$PIP show litellm-ibm-bob &>/dev/null || $PIP install --no-user "litellm>=1.0.0" -q 2>/dev/null || true
```
**Raison :** `/nix/store/z0d7kvaycmw342xmz4xwwybm6p3p0zcs-pip.conf` contient `user = yes` globalement.

---

**AVANT (step 4 — Doppler) :**
```bash
if ! command -v doppler &>/dev/null; then
  curl -Ls ... https://cli.doppler.com/install.sh | sh ...
fi
if [ -n "$DOPPLER_TOKEN" ]; then
  doppler configure set token "$DOPPLER_TOKEN" ...
else
  echo "DOPPLER_TOKEN absent"
fi
```

**APRÈS :**
```bash
_DTOKEN="${DOPPLER_TOKEN:-${DOPPLER_TOKEN_REPLIT:-}}"
if [ -n "$_DTOKEN" ] && command -v doppler &>/dev/null; then
  doppler configure set token "$_DTOKEN" ...
else
  echo "[4/6] Doppler ignoré — variables Replit utilisées"
fi
```
**Raison :** Le secret Replit est nommé `DOPPLER_TOKEN_REPLIT`, pas `DOPPLER_TOKEN`.

---

**AVANT (step 5 — compilation C) :**
```bash
for candidate in cc gcc "$(find /nix/store -name 'cc' -path '*/bin/cc' 2>/dev/null | grep runtime | head -1)"; do
  ...
done
OPENSSL_LIB="$(find /nix/store -name 'libcrypto.so' -not -name '*.drv' 2>/dev/null | head -1)"
```

**APRÈS :**
```bash
NIX_CC="/nix/store/a0d7m3zn9p2dfa1h7ag9h2wzzr2w25sn-gcc-wrapper-14.2.1.20250322/bin/cc"
NIX_SSL="/nix/store/2cwpdm6fcc53f8jgxmagransrfp0igbl-openssl-3.4.1/lib/libcrypto.so"
NIX_INC="/nix/store/2cwpdm6fcc53f8jgxmagransrfp0igbl-openssl-3.4.1/include"
```
**Raison :** `find /nix/store` scanne >500K fichiers = hang. Paths hardcodés pour startup immédiat.  
**Attention :** Si le store Nix change (mise à jour canal), ces paths devront être mis à jour.  
**Note :** OpenSSL à l'adresse `0w2cdbrgm5gr8vyl5sik40zqh84ic13f` était 32-bit (i386). Le bon path 64-bit est `2cwpdm6fcc53f8jgxmagransrfp0igbl`.

---

**AJOUT (step 6/7 — build frontend) :**
```bash
# NOUVEAU
FRONTEND_DIST="$REPL_DIR/frontend/dist/index.html"
FRONTEND_SRC="$REPL_DIR/frontend/src"
if [ ! -f "$FRONTEND_DIST" ] || [ -n "$(find "$FRONTEND_SRC" -newer "$FRONTEND_DIST" 2>/dev/null | head -1)" ]; then
  echo "  Build frontend (npm install + vite build)..."
  (cd "$REPL_DIR/frontend" && npm install -q && npm run build 2>&1 | tail -5) \
    && echo "  Frontend buildé ✅" \
    || echo "  ⚠️ Build frontend échoué — API seule disponible"
else
  echo "  dist/ à jour ✅"
fi
```
**Raison :** `frontend/dist/` est dans `.gitignore` → absent en déploiement propre. FastAPI sert le SPA uniquement si `dist/` existe.

---

### 2.2 `requirements.txt`

**AVANT :**
```
# liboqs-python : ML-DSA-65 + ML-KEM-768 (NIST PQC 2024)
# Fallback automatique X25519/Ed25519 si absent (kem.py + pqc.py)
# ⚠️ Nécessite cmake + ninja pour compiler le .so natif
# Sur Replit/NixOS : le script replit_start.sh compile liboqs automatiquement
liboqs-python>=0.14.0
```

**APRÈS :**
```
# liboqs-python : ML-DSA-65 + ML-KEM-768 (NIST PQC 2024)
# NOTE Replit : cmake build takes >10 min — excluded here; app uses Ed25519/X25519 fallback.
# Install manually if full post-quantum crypto is needed: pip install liboqs-python
# liboqs-python>=0.14.0
```
**Raison :** `liboqs-python 0.16.0` (déjà installé dans le venv) déclenche un cmake build complet de liboqs lors du premier `import oqs` (auto-install dans `~/_oqs`). Ce build prend >10 minutes sur Replit et bloque le démarrage. Le fallback Ed25519/X25519 est fonctionnel (`kem.py` + `pqc.py`).

---

### 2.3 `.replit`

**AVANT `[nix]` :**
```toml
channel = "stable-23_11"
```
**APRÈS :**
```toml
channel = "stable-25_05"
modules = ["python-3.11", "nodejs-20", "bash", "web"]
```

**AVANT `[deployment].run` :**
```toml
run = ["sh", "-c", "python3 -m venv $HOME/venv && $HOME/venv/bin/pip install -r requirements.txt -q && PYTHONPATH=... uvicorn ..."]
```
**APRÈS :**
```toml
run = ["bash", "scripts/replit_start.sh"]
```
**Raison :** Commande inline ≠ workflow → PIP_USER absent, frontend non buildé, C lib non compilée, drift de config.

---

### 2.4 Fichier ajouté — `replit.md`

Documentation complète pour les agents futurs :
- Stack technique, commandes de démarrage
- Variables d'environnement expliquées
- Notes Replit spécifiques (pip.conf, liboqs, chemins Nix)

---

## 3. Analyse des logs fournis (access log déploiement)

**Fichier :** `attached_assets/Pasted-2026-08-04T11-45-53-275Z-...txt`  
**Période :** 2026-08-04T11:45:53Z → 11:47:30Z (≈2 minutes)

### 3.1 IPs observées

| IP | Géolocalisation | Rôle réel |
|---|---|---|
| `35.195.213.250` | GCP `europe-west1` (Belgique) | Instance autoscale Replit (health check) |
| `35.233.29.19` | GCP `europe-west1` (Belgique) | Instance autoscale Replit (health check) |
| `34.77.42.93` | GCP `europe-west1` (Belgique) | Instance autoscale Replit (health check) |

⚠️ **IMPORTANT pour l'agent local :** Ces 3 IPs sont des instances Replit Autoscale (load balancer / health checker GCP), **PAS des nœuds blockchain P2P réels**. Elles interrogent l'API toutes les ~5 secondes.

### 3.2 Endpoints appelés et fréquence

| Endpoint | Fréq. | Statut | Rôle |
|---|---|---|---|
| `GET /api/v1/health` | ~5s | ✅ 200 | Healthcheck Replit autoscale |
| `GET /api/v1/pol/score` | ~5s | ✅ 200 | Monitoring PoL |
| `GET /api/v1/chain` | ~5s | ✅ 200 | Monitoring chaîne |
| `GET /api/v1/chain/verify` | ~5s | ✅ 200 | Vérification intégrité |
| `GET /api/v1/metrics` | ~30s | ✅ 200 | Métriques système |
| `GET /api/v1/rtleg/events` | ~30s | ✅ 200 | Événements RT-LEG |
| `GET /api/v1/dashboard/logs/demo-live` | sporadique | ✅ 200 | Dashboard demo |
| `GET /api/v1/dashboard/mining/status` | sporadique | ✅ 200 | Status mining |
| `GET /api/v1/dashboard/logs/mining-latest` | sporadique | ✅ 200 | Derniers logs mining |
| `GET /api/v1/wallet/list` | sporadique | ✅ 200 | Liste wallets |
| `GET /api/v1/demo/wailly-excerpt?max_pages=2` | 1x | ✅ 200 | Demo PDF IR |
| `GET /api/v1/ai/status` | 1x | ✅ 200 | Status agent AI |

### 3.3 Problèmes détectés dans les logs

**Aucune erreur HTTP dans les logs fournis.** ✅ Toutes les réponses sont 200 OK.

**Patterns suspects :**
- Port `:0` côté client = normal (Replit proxy masque les ports source)
- Polling identique depuis 3 IPs simultanément = autoscale multi-instances  
- Aucune requête POST/PUT/DELETE = pas d'écriture depuis l'extérieur → **0 blocs créés**

---

## 4. État actuel du nœud Replit (2026-08-04)

```json
{
  "health": {
    "status": "ok",
    "debug": true,
    "llm_enabled": false,
    "chain": {
      "available": true,
      "valid": true,
      "block_count": 0,
      "public_key": "lVw51ARiiWwhSFEt/oBx1G1+1fdyAWxYd/jnhXUBKLk=",
      "hybrid_signatures": false,
      "pqc_algorithm": null
    }
  },
  "p2p_status": {
    "network_id": "artcb-devnet-1",
    "node_id": "node_57ee00fe2d5b",
    "kem_public_key_hex": "f4f9707d9e58ce3ab854cfa5e45acaf7b9c55f6b8654d106b0d17f74aa88eb48",
    "kem_algorithm": "ML-KEM-768",
    "p2p_port": 18444,
    "api_port": 8000,
    "peer_count": 0,
    "pool_e2e_available": true
  },
  "chain": {
    "blocks": [],
    "count": 0
  },
  "peers": [],
  "ai": {
    "agent_ready": true,
    "pol_score": 0.6,
    "capabilities": ["ai/memo", "ai/think", "chain/search", "chain/export"]
  }
}
```

---

## 5. Problèmes identifiés — Audit complet

### P1 — [CRITIQUE] Données blockchain éphémères (RAM/JSON local)
**Symptôme :** `block_count: 0` à chaque démarrage.  
**Cause :** En autoscale Replit, chaque instance repart de zéro. La chaîne est stockée en JSON local (`data/`), non persistent entre instances.  
**Impact :** Production multi-instance = chaînes désynchronisées.  
**Fix requis :** PostgreSQL Replit ou stockage partagé (S3/GCS) pour la chaîne.

### P2 — [CRITIQUE] liboqs absent → Crypto PQ désactivée sur Replit
**Symptôme :** `"pqc_algorithm": null`, `"hybrid_signatures": false`  
**Cause :** `liboqs-python` retiré de `requirements.txt` pour éviter le hang cmake.  
**Impact :** ML-DSA-65 et ML-KEM-768 désactivés. Seulement Ed25519 + X25519.  
**Fix Replit :** Tâche #2 — installer liboqs avec cache pre-compilé.  
**Fix PC local :** `pip install liboqs-python` (cmake disponible localement).

### P3 — [MAJEUR] Startup lent au premier déploiement (~8 minutes)
**Symptôme :** Logs déploiement → healthchecks 500 de `11:44:22` à `11:52:xx` (~8 min).
```
[2026-08-04T11:44:22.288Z ERROR] healthcheck failed error=healthcheck /: connection refused
[2026-08-04T11:44:22.299Z ERROR] healthcheck failed error=healthcheck / returned status 500
```
**Cause :** pip install toutes les dépendances depuis PyPI (litellm, faiss, etc.) au premier démarrage.  
**Impact :** Si Replit impose un timeout <8min, le déploiement échoue.  
**Fix :** Pre-builder une image ou utiliser `--find-links` avec cache pip.

### P4 — [MAJEUR] LLM non connecté
**Symptôme :** `"llm_enabled": false`, `"bob_configured": false`  
**Cause :** `ARTCB_LLM_ENABLED=false` dans `.replit [env]`, aucune clé API configurée.  
**Impact :** `/ai/think`, `/ai/memo`, dual-agent pipeline = non fonctionnel. PoL incomplet.  
**Fix :** Tâche #3 — configurer une clé LLM (OpenRouter recommandé).

### P5 — [MAJEUR] TenSEAL absent → chiffrement homomorphique désactivé
**Symptôme au démarrage :** `TenSEAL non installé — mode simulé (TESTS UNIQUEMENT)`  
**Cause :** `tenseal` absent de `requirements.txt` (dépendance lourde avec build C).  
**Impact :** Calculs homomorphiques = simulés, pas réels.  
**Fix :** `pip install tenseal` + ajouter à requirements.txt si stable sur Replit.

### P6 — [MAJEUR] Tests multi-nœuds impossibles en l'état actuel
**Symptôme :** `"peer_count": 0`, 0 blocs.  
**Cause :** Aucun nœud pair configuré, ARTCB_PUBLIC_HOST non défini.  
**Impact :** Pas de sync P2P possible.  
**Fix :** Voir §6 — Guide tests multi-nœuds.

### P7 — [MOYEN] ARTCB_DEBUG=true actif en production
**Symptôme :** `"debug": true` dans `/api/v1/health`  
**Cause :** `ARTCB_DEBUG = "true"` dans `.replit [env]` (requis par PROTOCOLE_ARTCB).  
**Impact :** Logs verbeux, potentielle exposition d'infos techniques.  
**Fix :** Désactiver uniquement sur ordre explicite utilisateur (conforme PROTOCOLE).

### P8 — [MOYEN] eval Doppler — risque injection de code
**Fichier :** `scripts/replit_start.sh`  
**Ligne :** `eval "$(doppler secrets download --no-file --format env ...)"`  
**Risque :** Si Doppler est compromis ou si un secret contient du code shell, exécution arbitraire.  
**Fix recommandé :** Parser les variables manuellement sans `eval`, ou utiliser l'API JSON de Doppler.

### P9 — [MOYEN] Chemins Nix hardcodés — fragiles sur mise à jour
**Fichier :** `scripts/replit_start.sh`  
**Lignes :**
```bash
NIX_CC="/nix/store/a0d7m3zn9p2dfa1h7ag9h2wzzr2w25sn-gcc-wrapper-14.2.1.20250322/bin/cc"
NIX_SSL="/nix/store/2cwpdm6fcc53f8jgxmagransrfp0igbl-openssl-3.4.1/lib/libcrypto.so"
```
**Risque :** Si Replit met à jour le canal NixOS (`stable-25_05` → `stable-26_xx`), les hash changent et la compilation échoue.  
**Fix :** Ajouter un fallback `find /nix/store -maxdepth 4 ...` avec timeout, ou vérifier l'existence avant d'utiliser.

### P10 — [MINEUR] git pull au démarrage — risque déploiement
**Ligne :** `git pull origin "${GITHUB_BRANCH:-main}" 2>/dev/null || true`  
**Risque :** En autoscale Replit, le conteneur déploiement n'a pas d'accès SSH GitHub. Le pull échoue silencieusement (grâce à `|| true`).  
**Impact :** Non-critique (|| true), mais peut causer confusion.

### P11 — [INFO] 3 instances autoscale ≠ 3 nœuds blockchain
**Observation :** Les 3 IPs dans les logs (35.195.213.250, 35.233.29.19, 34.77.42.93) sont du load balancer Replit, pas des nœuds P2P indépendants.  
**Impact :** Illusion de multi-nœuds. Chaque instance a sa propre chaîne locale vide.

---

## 6. Guide — Tests multi-nœuds réels (pour l'agent local PC)

### 6.1 Architecture cible pour tests

```
[PC Local — Nœud A]           [Replit — Nœud B]
  port API: 8000          ←→   port API: 5000 (proxy public)
  port P2P: 18444              port P2P: 18444 (non exposé extérieur)
  node_id: <local>             node_id: node_57ee00fe2d5b
```

⚠️ **Contrainte Replit :** Le port P2P `18444` n'est PAS exposé publiquement. Seul le port 5000 (HTTP) l'est. La sync P2P se fait donc via les endpoints REST `/api/v1/p2p/*`, pas via connexion TCP directe.

### 6.2 Étapes pour lancer les tests multi-nœuds

#### Pré-requis agent local PC

```bash
# 1. Depuis la racine du projet (après git pull origin main)
git pull origin main

# 2. Installer les dépendances (avec liboqs-python cette fois !)
pip install -r requirements.txt
pip install liboqs-python  # Pour ML-DSA-65 + ML-KEM-768 complets

# 3. Démarrer le nœud local (port différent pour éviter conflit)
export ARTCB_DEBUG=true
export ARTCB_LLM_ENABLED=false  # ou true si clé disponible
export ARTCB_DATA_DIR=./data_local   # dossier data séparé !
uvicorn src.api.main:app --host 0.0.0.0 --port 8001 --reload
```

#### Récupérer les infos du nœud Replit

```bash
# URL publique Replit (remplacer par l'URL réelle du déploiement)
REPLIT_URL="https://<votre-repl>.replit.app"

# Infos nœud Replit
curl $REPLIT_URL/api/v1/p2p/status
# Réponse attendue :
# {
#   "node_id": "node_57ee00fe2d5b",
#   "kem_public_key_hex": "f4f9707d9e58ce3ab854cfa5e45acaf7b9c55f6b8654d106b0d17f74aa88eb48",
#   "p2p_port": 18444,
#   "peer_count": 0
# }
```

#### Enregistrement mutuel des nœuds

```bash
# --- Sur le PC LOCAL (enregistrer Replit comme pair) ---
curl -X POST http://localhost:8001/api/v1/p2p/peers \
  -H "Content-Type: application/json" \
  -d '{
    "host": "<votre-repl>.replit.app",
    "port": 443,
    "kem_public_key_hex": "f4f9707d9e58ce3ab854cfa5e45acaf7b9c55f6b8654d106b0d17f74aa88eb48",
    "label": "replit-node-B"
  }'

# --- Sur REPLIT (enregistrer le PC local comme pair) ---
# Votre PC doit être accessible publiquement (ngrok ou IP publique)
# Si ngrok : ngrok http 8001 → obtenir URL publique
curl -X POST $REPLIT_URL/api/v1/p2p/peers \
  -H "Content-Type: application/json" \
  -d '{
    "host": "<ngrok-ou-ip-publique>",
    "port": 8001,
    "kem_public_key_hex": "<votre-kem-public-key-depuis-localhost:8001/api/v1/p2p/status>",
    "label": "local-node-A"
  }'
```

#### Créer des blocs publics et vérifier la sync

```bash
# Nœud A (local) : créer un bloc public
curl -X POST http://localhost:8001/api/v1/store \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Test multi-nœud : bloc 1 depuis nœud local",
    "visibility": "public",
    "wallet_address": "<votre-wallet-local>"
  }'

# Déclencher la sync depuis nœud A vers nœud B (Replit)
curl -X POST http://localhost:8001/api/v1/p2p/sync

# Vérifier que Replit a reçu le bloc
curl $REPLIT_URL/api/v1/p2p/archive

# Sur Replit : créer un bloc public  
curl -X POST $REPLIT_URL/api/v1/store \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Test multi-nœud : bloc 1 depuis nœud Replit",
    "visibility": "public",
    "wallet_address": "<wallet-replit>"
  }'

# Sync Replit → Local
curl -X POST $REPLIT_URL/api/v1/p2p/sync

# Vérifier propagation
curl http://localhost:8001/api/v1/p2p/archive
```

#### Vérification de la blockchain distribuée

```bash
# Les deux nœuds doivent voir les mêmes blocs publics archivés
curl http://localhost:8001/api/v1/p2p/archive | jq '.count'
curl $REPLIT_URL/api/v1/p2p/archive | jq '.count'
# Les deux doivent retourner le même nombre de blocs

# Vérifier intégrité sur les deux nœuds
curl http://localhost:8001/api/v1/chain/verify
curl $REPLIT_URL/api/v1/chain/verify
```

### 6.3 Variables d'environnement importantes pour nœud local

```bash
# Dans .env local (copier .env.example)
ARTCB_DEBUG=true
ARTCB_NETWORK=devnet
ARTCB_PUBLIC_HOST=<votre-ip-publique-ou-ngrok>  # OBLIGATOIRE pour P2P entrant
ARTCB_DATA_DIR=./data_local                      # Dossier distinct du nœud Replit
ARTCB_LLM_ENABLED=false                          # ou true avec clé API

# Pour crypto PQ complète (optionnel mais recommandé en local) :
# pip install liboqs-python DOIT être fait AVANT de démarrer
```

### 6.4 Endpoints P2P disponibles

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/p2p/status` | Identité + stats du nœud |
| `GET` | `/api/v1/p2p/peers` | Liste des pairs enregistrés |
| `POST` | `/api/v1/p2p/peers` | Ajouter un pair (host, port, kem_key) |
| `DELETE` | `/api/v1/p2p/peers/{peer_id}` | Supprimer un pair |
| `POST` | `/api/v1/p2p/sync` | Déclencher sync avec tous les pairs |
| `POST` | `/api/v1/p2p/sync/{peer_id}` | Sync avec un pair spécifique |
| `GET` | `/api/v1/p2p/archive` | Blocs publics reçus des pairs |
| `POST` | `/api/v1/p2p/receive` | Recevoir blocs d'un pair (appelé par les pairs) |
| `GET` | `/api/v1/p2p/gossip/announce` | Annonce gossip du nœud |

---

## 7. Commits appliqués sur `main`

| Commit | Description |
|---|---|
| `8065606` | Update Replit configuration (import auto) |
| `dd7a190` | Fix PIP_USER, chemins Nix, exclusion liboqs-python, build frontend, fix déploiement |
| `3041043` | Fix déploiement : `[deployment].run` → `scripts/replit_start.sh` |
| `HEAD` | Rapport 100 + mise à jour AUTO_PROMPT_ARTCB |

**Statut push :** `origin/main` à jour ✅

---

## 8. État du déploiement Replit Production

| Composant | État | Notes |
|---|---|---|
| API FastAPI | ✅ RUNNING | Port 5000, toutes routes 200 OK |
| Frontend React | ✅ SERVING | `/` sert `frontend/dist/index.html` |
| libartcb_chain.so | ✅ COMPILÉ | Ed25519 SHA-256 fonctionnel |
| liboqs (ML-DSA-65) | ⚠️ FALLBACK | Ed25519 actif, PQ désactivé |
| LLM | ⚠️ DÉSACTIVÉ | ARTCB_LLM_ENABLED=false |
| TenSEAL | ⚠️ SIMULÉ | Mode test uniquement |
| P2P peers | ⚠️ 0 pairs | En attente enregistrement pairs |
| Wallet | ✅ GÉNÉRÉ | `lVw51ARiiWwhSFEt/oBx1G1+...` |
| PoL score | ✅ 0.60 | Seuil OK (≥0.6) |
| Blockchain | ✅ VALIDE | 0 blocs (vide, attend transactions) |

---

## 9. Ce que l'agent local PC doit faire maintenant

```
Priorité 1 (immédiat) :
  □ git pull origin main  ← récupérer toutes les corrections Replit
  □ pip install liboqs-python  ← PQ crypto complète en local
  □ Vérifier ARTCB_PUBLIC_HOST dans .env (ngrok ou IP publique)
  □ Démarrer nœud local sur port 8001 (ou 8000 si Replit pas en local)

Priorité 2 (tests multi-nœuds) :
  □ Récupérer l'URL publique du déploiement Replit
  □ Enregistrement mutuel des pairs (§6.2)
  □ Créer blocs publics sur chaque nœud
  □ Déclencher sync P2P
  □ Vérifier propagation des blocs

Priorité 3 (blockchain complète) :
  □ Activer LLM (ARTCB_LLM_ENABLED=true + clé API)
  □ Lancer pipeline ai/think → bloc PoL complet
  □ Vérifier PoL score > 0.6 sur les deux nœuds
  □ Lancer les 303 tests pytest : pytest tests/ -v

Priorité 4 (à planifier) :
  □ Tâche #2 Replit : liboqs pré-compilé + cache
  □ Tâche #3 Replit : connecter LLM provider
  □ Tâche #4 Replit : frontend build auto (déjà implémenté)
```

---

## 10. Éléments non précisés par l'utilisateur — ajoutés par l'agent

Les points suivants ont été identifiés comme nécessaires et ajoutés sans demande explicite :

1. **`replit.md`** — Documentation technique créée (absente du projet original)
2. **Numéro du rapport** — 100 (suite logique des 097-099 existants)
3. **Analyse des IPs des logs** — Les 3 IPs sont Replit autoscale, pas des nœuds P2P
4. **Guide ngrok** — Nécessaire pour exposer le nœud local au P2P entrant
5. **Port séparé pour nœud local** — `8001` recommandé si Replit tourne en local aussi
6. **Variable ARTCB_DATA_DIR séparée** — Évite que les deux nœuds partagent les mêmes données
7. **Problème éphémérité Replit autoscale** — Données JSON locales perdues entre instances

---

*Rapport généré par Replit Agent — 2026-08-04T12:00:00Z*  
*Conforme PROTOCOLE_ARTCB + AUTO_PROMPT_ARTCB*  
*À ne pas écraser. Prochain rapport : 101_xxx.md*
