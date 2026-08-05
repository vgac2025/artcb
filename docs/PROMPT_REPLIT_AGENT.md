# PROMPT — Agent Replit ARTCB
> Copie-colle ce prompt entier dans l'agent Replit. Il contient tout ce dont il a besoin.

---

## CONTEXTE DU PROJET

Tu es l'agent Replit chargé de travailler en **parallèle** avec l'agent Bob (local) sur le projet **ARTCB** — une blockchain post-quantique Proof-of-Link (PoL) écrite en Python/FastAPI.

- Repo GitHub : `https://github.com/vgac2025/lvx`
- Branche : `main`
- Dernière version stable : commit `c3db48e` — 478/478 tests PASS (8 skipped bridges live intentionnels)

---

## ÉTAPE 1 — INSTALLATION DOPPLER (récupérer les secrets)

```bash
# 1. Installer Doppler CLI
curl -Ls --tlsv1.2 --proto "=https" --retry 3 https://cli.doppler.com/install.sh | sh

# 2. Configurer avec le token dédié Replit
doppler configure set token <DOPPLER_TOKEN_REPLIT>
doppler configure set project artcb-blockchain
doppler configure set config dev

# 3. Vérifier que Doppler répond
doppler secrets download --no-file --format env | head -5
```

> **Important :** Dans les **Secrets Replit** (panneau verrou 🔒), ajouter :
> - `DOPPLER_TOKEN` = le token fourni séparément
> - `SSH_PRIVATE_KEY` = la clé privée (récupérée depuis Doppler automatiquement)

---

## ÉTAPE 1bis — SETUP SSH GIT PERSISTANT

> Ce script règle le problème de la clé SSH qui change à chaque nouvelle session Replit.

```bash
# Clone d'abord sans SSH (HTTPS)
git clone https://github.com/vgac2025/lvx.git artcb
cd artcb

# Setup SSH persistant (récupère la clé depuis Doppler automatiquement)
bash scripts/setup_ssh_git.sh

# Vérifier que git push fonctionne
git remote -v   # doit afficher git@github.com:vgac2025/lvx.git
ssh -T git@github.com   # doit répondre "Hi vgac2025!"
```

**Si tu changes de compte Replit :** relance juste `bash scripts/setup_ssh_git.sh`
→ La clé est récupérée depuis Doppler, pas régénérée. GitHub ne la perd pas.

---

## ÉTAPE 2 — CLONER ET INSTALLER

```bash
# Cloner le repo
git clone https://github.com/vgac2025/lvx.git artcb
cd artcb

# Injecter les secrets dans l'environnement et installer les dépendances
doppler run -- pip install -r requirements.txt

# Vérifier que liboqs est disponible (PQC ML-DSA-65 + ML-KEM-768)
python3 -c "import oqs; print('liboqs OK:', oqs.get_enabled_sig_mechanisms()[:3])" || echo "liboqs absent — fallback X25519 actif"
```

---

## ÉTAPE 3 — LANCER TOUS LES TESTS

```bash
# Lancer les 478 tests avec les secrets Doppler injectés
doppler run -- python3 -m pytest tests/ -x -q --tb=short 2>&1 | tee replit_test_results.txt

# Résultat attendu : 478 passed, 8 skipped (bridges live intentionnels)
tail -3 replit_test_results.txt
```

---

## ÉTAPE 4 — CE QUE TU DOIS FAIRE EN CONTINU

### Ton rôle : CI/QA côté Replit

À chaque nouveau commit sur `main` (Bob pousse régulièrement), tu dois :

```bash
# 1. Pull la dernière version
git pull origin main

# 2. Relancer les tests
doppler run -- python3 -m pytest tests/ -x -q --tb=short 2>&1 | tee replit_test_results.txt

# 3. Rapporter les résultats en créant un fichier
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) | $(tail -1 replit_test_results.txt)" >> replit_ci_log.txt

# 4. Si des tests échouent, créer un rapport d'échec
python3 -m pytest tests/ -q --tb=long 2>&1 | grep -A 20 "FAILED\|ERROR" > replit_failures.txt
# NOTE : 8 skips pour tests/test_bridges_live.py sont NORMAUX (nécessitent ARTCB_LIVE_TESTS=1 ou --live)
```

---

## ÉTAPE 5 — TESTS SPÉCIFIQUES À VALIDER SUR REPLIT

Ces tests sont **prioritaires** car ils testent des comportements critiques qui peuvent varier selon l'environnement :

```bash
# Test PQC (cryptographie post-quantique) — dépend de liboqs
doppler run -- python3 -m pytest tests/test_pqc_crypto.py -v --tb=short

# Test wallets
doppler run -- python3 -m pytest tests/test_wallet_encryption.py -v --tb=short

# Test API complète (encode + store + chain)
doppler run -- python3 -m pytest tests/test_api.py -v --tb=short

# Test mining pipeline (BUG-P0-1 corrigé : async)
doppler run -- python3 -m pytest tests/test_mining_pipeline.py -v --tb=short

# Test pool E2E distribué
doppler run -- python3 -m pytest tests/test_pool_e2e.py -v --tb=short
```

---

## ÉTAPE 6 — BENCHMARK RAPIDE (optionnel mais utile)

```bash
# Démarrer l'API
doppler run -- python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &
sleep 15

# Benchmark 20 requêtes parallèles sur /store (BUG-P0 corrigé)
python3 -c "
import requests, time, threading, json

base = 'http://127.0.0.1:8000/api/v1'
results = []

def do_store(i):
    t0 = time.time()
    r = requests.post(f'{base}/store', json={'text': f'Replit bench #{i} ARTCB PoL'}, timeout=30)
    results.append({'i': i, 'status': r.status_code, 'ms': round((time.time()-t0)*1000)})

threads = [threading.Thread(target=do_store, args=(i,)) for i in range(20)]
t_start = time.time()
for t in threads: t.start()
for t in threads: t.join()
t_total = round((time.time()-t_start)*1000)

ok = sum(1 for r in results if r['status']==200)
print(f'Replit benchmark: {ok}/20 OK | total={t_total}ms | TPS={round(ok/t_total*1000,1)}')
print(json.dumps(results, indent=2))
" 2>&1 | tee replit_benchmark.txt

kill %1 2>/dev/null
```

---

## CE QUE BOB (agent local) FAIT DE SON CÔTÉ

| Bob fait | Replit valide |
|----------|---------------|
| Développe le code, corrige les bugs | Relance les tests après chaque push |
| Pousse sur `main` avec `git push` | `git pull` + `pytest` |
| Rédige les rapports `.md` dans `rapports/` | Vérifie que les tests passent |
| Déploie sur OVH (Phase 13) | Teste l'API depuis Replit vers OVH |
| Fix BUG-P0 (async, auto-encode) | Confirme que les fixes passent en CI |

---

## CE QUE TU DOIS RAPPORTER À BOB

Après chaque run, crée un fichier `replit_report_YYYYMMDD_HHMMSS.txt` avec :

```
=== RAPPORT REPLIT ===
Date : <timestamp>
Commit testé : <git rev-parse HEAD>
Tests : <N>/478 PASS | <M> FAIL | <S> SKIP (8 bridges live = NORMAL)
Environnement : Python <version> | liboqs <present/absent>
Echecs :
  - <test_name> : <erreur courte>
Actions requises de Bob :
  - <description du fix nécessaire si tests échouent>
```

---

## VARIABLES D'ENVIRONNEMENT CLÉS (via Doppler)

Doppler injecte tout automatiquement. Les variables critiques sont :

| Variable | Rôle |
|----------|------|
| `ARTCB_DEBUG` | `true` — logs détaillés |
| `ARTCB_ENCODE_MODE` | `rule-based` — pas de LLM requis pour les tests |
| `ARTCB_LLM_ENABLED` | `false` — tests tournent sans clé LLM |
| `ARTCB_ANTI_SYBIL_AI_BYPASS` | `true` — bypass rate-limit anti-Sybil (tests rapides) |
| `ARTCB_WALLET_PASSPHRASE` | Passphrase wallets de test |
| `ARTCB_MIN_BLOCK_INTERVAL_SEC` | `60` — délai anti-Sybil entre blocs |
| `BOB_API_KEY` | Clé IBM Bob (LLM optionnel) |
| `GITHUB_TOKEN` | Pour `git pull` si repo privé |

---

## EXPLICATION — CE QU'EST `/store` MAINTENANT

**Avant (cassé) :**
```python
# Nécessitait 2 appels séparés
POST /api/v1/encode  {"text": "mon texte"}  → graph_id
POST /api/v1/store   {"graph_id": "g_xxx"}  → bloc gravé
```

**Après (corrigé — BUG-P0-2) :**
```python
# 1 seul appel suffit
POST /api/v1/store   {"text": "mon texte"}  → encode + grave en chaîne automatiquement
# OU toujours compatible avec l'ancien flux :
POST /api/v1/store   {"graph_id": "g_xxx"}  → grave le graphe existant
```

**Et non-bloquant (BUG-P0-1) :**
```python
# 20 requêtes simultanées → toutes traitées en parallèle, l'API ne gèle plus
```

---

## CE QU'IL RESTE À FAIRE (Phase 13+)

Ces tâches sont planifiées — **ne pas les implémenter sans instruction de Bob** :

1. **Déploiement OVH** — VPS `137.74.133.147` (nouvelle IP) avec Terraform/image custom
2. **Tests inter-nœuds P2P** — valider `POST /api/v1/p2p/sync` entre Replit et OVH
3. **TPS production** — benchmark sur VPS 4vCPU/8GB (attendu > 50 TPS vs 22 local)
4. **Monitoring** — alertes si tests échouent sur CI Replit
5. **ngrok sur Replit** — exposer l'API Replit pour tests P2P avec Bob

---

*Projet ARTCB — v0.3.1 — commit c3db48e — 2026-08-05*
*Token Doppler Replit : fourni séparément par le propriétaire du projet (ne pas committer)*

---

## ENDPOINTS NOUVEAUX (ajoutés 2026-08-05)

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/v1/chain/status` | GET | État de la chaîne (hauteur, validité, PQC) |
| `/api/v1/chain/blocks` | GET | Liste paginée des blocs |
| `/api/v1/node/status` | GET | État du nœud courant (node_id, version, debug) |
| `/api/v1/ir/learn` | POST | Encode + grave un bloc public (wallet_address + content) |
| `/api/v1/governance/creator-key-rotation` | POST | Rotation clé créateur — signature OBLIGATOIRE |
| `/api/v1/governance/user-key-rotation` | POST | Rotation clé utilisateur — signature OBLIGATOIRE |

## RÈGLE DE SÉCURITÉ ABSOLUE (rapport 115)

> **Toute rotation de clé sans signature valide est REJETÉE — dans TOUS les environnements.**
> Il n'existe PAS de mode dev / debug qui accepterait une rotation non signée.
> `GovernanceError` immédiat si `signature_hex` absente ou invalide.
