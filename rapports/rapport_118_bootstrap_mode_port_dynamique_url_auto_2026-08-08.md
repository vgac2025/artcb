# Rapport 118 — Mode bootstrap automatique, port dynamique, URL Replit auto-détectée
**Conforme au protocole ARTCB — Traçabilité complète**

**Date :** 2026-08-08  
**Auteur :** Agent Bob  
**Statut :** ✅ Implémenté — 519/519 tests PASS  
**Rapport précédent :** rapport 117  
**Commit :** à pousser

---

## PROBLÈME IDENTIFIÉ

Le log de déploiement Replit montrait :

```
OSError:
╔══════════════════════════════════════════════════════════════╗
║  ERREUR — Variable d'environnement manquante                ║
║  ARTCB_NODE_WALLET_ADDRESS est OBLIGATOIRE...               ║
╚══════════════════════════════════════════════════════════════╝

[step=uvicorn] ERROR command='wait "$UVICORN_PID"' status=1
[step=uvicorn] FOREGROUND end name=uvicorn status=1
```

**Cause :** `ARTCB_NODE_WALLET_ADDRESS` ne peut pas être défini dans les secrets
Replit **avant** le premier déploiement — on ne peut les modifier qu'**après** que
le nœud est en ligne. Cercle vicieux : le nœud doit tourner pour créer le wallet,
mais le wallet est requis pour que le nœud tourne.

**Deuxième problème identifié :** Si le port 5000 est déjà occupé (redémarrage
rapide, autre processus), uvicorn crash sans message clair.

---

## SOLUTION — Architecture en deux phases

```
PHASE 1 — BOOTSTRAP (premier déploiement, pas de wallet configuré)
──────────────────────────────────────────────────────────────────
Script démarre → détecte URL Replit auto → trouve port libre
nœud démarre → mode bootstrap activé
API expose UNIQUEMENT :
  GET  /health          → {"status": "bootstrap", "setup_url": "/setup/init-node"}
  GET  /setup/status    → état du bootstrap + URL détectée
  POST /setup/init-node → crée wallet + persiste .node_config
Toutes les autres routes → HTTP 503 avec message explicite

Opérateur appelle POST /setup/init-node {node_name, password}
→ wallet créé, seed_hex retournée UNE SEULE FOIS
→ .node_config écrit dans data/
→ redémarrage demandé

PHASE 2 — NORMAL (nœud configuré)
──────────────────────────────────
Script démarre → lit .node_config OU ARTCB_NODE_WALLET_ADDRESS
nœud démarre → mode normal, toutes les routes accessibles
```

---

## PARTIE 1 — Résolution de l'identité du nœud (ordre de priorité)

Le `NodeIdentityStore` résout maintenant `wallet_address` dans cet ordre :

```python
# src/artcb/p2p/node_identity.py

# Priorité 1 : variable d'environnement (secrets Replit, .env)
wallet_address = os.getenv("ARTCB_NODE_WALLET_ADDRESS", "").strip() or None

# Priorité 2 : fichier .node_config local (écrit par /setup/init-node)
if not wallet_address:
    node_cfg = _read_node_config(self._data_dir)
    wallet_address = node_cfg.get("wallet_address", "").strip() or None

# Priorité 3 : MODE BOOTSTRAP — node_id temporaire "bootstrap_<hostname>"
if not wallet_address:
    return NodeIdentity(
        node_id=f"bootstrap_{hostname[:20]}",
        bootstrap_mode=True,     # ← flag lu par main.py
        kem_public_key_hex="",   # pas de clé KEM — pas de P2P
        ...
    )
```

Le `NodeIdentity` gagne un champ `bootstrap_mode: bool = False`.

**Fichier modifié :** [`src/artcb/p2p/node_identity.py`](../src/artcb/p2p/node_identity.py)

---

## PARTIE 2 — Persistance dans `.node_config`

Nouveau fichier local (non committé) dans `data/.node_config` :

```json
{
  "wallet_address": "artcb1q3r5m6kz9p2wxy4n7jvdf8sg0tu1lhcae",
  "public_url": "https://lvx--supermicro20238.repl.co"
}
```

- Écrit par `POST /setup/init-node` après la création du wallet.
- Lu au démarrage suivant par `_read_node_config()`.
- Permissions `0o600` — lisible uniquement par l'utilisateur du processus.
- Ajouté dans `.gitignore` — ne sera jamais committé.
- Résiste à un redémarrage du nœud sans modification des secrets.

---

## PARTIE 3 — `POST /setup/init-node`

Nouveau fichier : [`src/api/setup_routes.py`](../src/api/setup_routes.py)

```
POST /setup/init-node
Body: {node_name: string, password: string (min 8 chars), public_url?: string}

Comportement :
  1. Vérifie qu'aucun wallet n'est déjà configuré (protection anti-écrasement)
  2. Détecte l'URL publique automatiquement si non fournie
  3. Crée le wallet Ed25519 + ML-DSA-65 hybride
  4. Retourne seed_hex UNE SEULE FOIS
  5. Écrit .node_config dans data/
  6. Indique le prochain step : redémarrer le nœud

Réponse :
{
  "status": "configured",
  "node_name": "mon_noeud",
  "address": "artcb1...",
  "seed_hex": "a1b2c3...",   ← à sauvegarder immédiatement
  "public_url": "https://lvx--supermicro20238.repl.co",
  "WARNING": "SAUVEGARDEZ votre seed_hex MAINTENANT...",
  "next_step": "Redémarrez le nœud...",
  "hybrid": true
}
```

**Sécurité :**
- Refusé avec HTTP 409 si déjà configuré.
- La seed_hex ne transite qu'une seule fois, en HTTPS.
- Le fichier `.node_config` n'est jamais committé.
- L'opérateur peut optionnellement copier l'adresse dans les secrets Replit
  pour une durabilité maximale (réinstallation, reset hébergeur).

**Endpoint GET /setup/status :**
Toujours accessible, indique l'état du bootstrap et l'URL auto-détectée.

---

## PARTIE 4 — Mode bootstrap dans `main.py`

```python
# src/api/main.py
state = build_app_state()
app.state.artcb = state

# /setup/* monté en premier — toujours accessible
app.include_router(setup_router)

if state.p2p_identity.bootstrap_mode:
    # API limitée : /health + /setup/*
    # Toutes les autres routes → HTTP 503 avec message explicite
    ...
    return app

# Mode normal — toutes les routes montées
app.include_router(auth_router)
...
```

En mode bootstrap :
- `GET /health` → `{"status": "bootstrap", "setup_url": "/setup/init-node"}`
- Routes inconnues → HTTP 503 avec instruction claire
- Healthcheck Replit passe toujours (HTTP 200 sur `/health`)

---

## PARTIE 5 — URL publique Replit auto-détectée

Dans `scripts/replit_start.sh` (v5), **avant** tout le reste :

```bash
# Replit injecte ces variables automatiquement dans l'environnement
if [ -z "${ARTCB_NODE_PUBLIC_URL:-}" ]; then
  if [ -n "${REPLIT_DOMAINS:-}" ]; then
    # "lvx--supermicro20238.repl.co" → "https://lvx--supermicro20238.repl.co"
    _FIRST_DOMAIN="$(echo "$REPLIT_DOMAINS" | cut -d',' -f1 | tr -d ' ')"
    export ARTCB_NODE_PUBLIC_URL="https://${_FIRST_DOMAIN}"
  elif [ -n "${REPL_SLUG:-}" ] && [ -n "${REPL_OWNER:-}" ]; then
    export ARTCB_NODE_PUBLIC_URL="https://${REPL_OWNER}--${REPL_SLUG}.repl.co"
  fi
fi
```

Cette variable est ensuite lue par :
- `setup_routes.py::_detect_public_url()` → proposée dans la réponse `/setup/init-node`
- `logging_config.py::_node_suffix()` → nom de fichier log unique par nœud
- `node_identity.py` → stockée dans `.node_config`

---

## PARTIE 6 — Port dynamique

```bash
# scripts/replit_start.sh
_find_free_port() {
  local preferred="$1"
  if ! nc -z 127.0.0.1 "$preferred" 2>/dev/null; then
    echo "$preferred"   # port libre → utiliser
    return
  fi
  # Port occupé → chercher le prochain libre
  local port=$((preferred + 1))
  while [ $port -lt 65535 ]; do
    if ! nc -z 127.0.0.1 "$port" 2>/dev/null; then
      echo "$port"
      return
    fi
    port=$((port + 1))
  done
  echo "$preferred"  # fallback ultime
}
ARTCB_PORT="$(_find_free_port 5000)"
export ARTCB_PORT
```

Uvicorn démarre maintenant sur `$ARTCB_PORT` au lieu du port 5000 codé en dur.
Si le port est occupé → message d'avertissement clair dans les logs.

> **Note :** Replit webview est configuré pour le port 5000. Si uvicorn démarre sur
> un autre port, le webview ne répondra pas. Dans ce cas, redémarrer le Repl
> libère le port précédent et permet le démarrage normal sur 5000.

---

## PARTIE 7 — Workflow complet pour l'opérateur (premier déploiement)

```
1. Déployer le nœud sur Replit (push du code)
   → Le script démarre en v5
   → L'URL est détectée automatiquement (REPLIT_DOMAINS ou REPL_SLUG+REPL_OWNER)
   → Port 5000 vérifié libre

2. Le nœud démarre en MODE BOOTSTRAP
   → Logs : "BOOTSTRAP MODE: ARTCB_NODE_WALLET_ADDRESS absent"
   → /health retourne {"status": "bootstrap"}
   → Le dashboard affiche le mode bootstrap

3. L'opérateur appelle via curl ou le dashboard :
   POST https://mon-noeud.replit.app/setup/init-node
   Content-Type: application/json
   {"node_name": "n1_artcb", "password": "MonMotDePasse123!"}

4. Réponse :
   {
     "status": "configured",
     "address": "artcb1q3r5...",
     "seed_hex": "a1b2c3...",   ← SAUVEGARDER MAINTENANT
     "public_url": "https://lvx--supermicro20238.repl.co",
     "next_step": "Redémarrez le nœud..."
   }

5. L'opérateur sauvegarde seed_hex dans son gestionnaire de mots de passe

6. L'opérateur redémarre le nœud (bouton Stop + Start dans Replit)
   → .node_config est lu au démarrage
   → Nœud démarre en mode NORMAL
   → Toutes les routes sont accessibles

7. Optionnel (recommandé pour robustesse) :
   Ajouter dans les Secrets Replit :
   ARTCB_NODE_WALLET_ADDRESS = artcb1q3r5...
   (si .node_config est perdu lors d'un reset Replit, le nœud démarre quand même)
```

---

## PARTIE 8 — Résumé des fichiers modifiés

| Fichier | Action | Description |
|---------|--------|-------------|
| `src/artcb/p2p/node_identity.py` | ✅ Modifié | Mode bootstrap + lecture .node_config + write_node_config() |
| `src/api/setup_routes.py` | ✅ Créé | Routes /setup/status et /setup/init-node |
| `src/api/main.py` | ✅ Modifié | Mode bootstrap dans create_app() + setup_router monté |
| `scripts/replit_start.sh` | ✅ Modifié v5 | URL auto-détectée + port dynamique + message bootstrap |
| `.gitignore` | ✅ Modifié | .node_config exclu du tracking |

---

**Tests : 519 PASS, 0 failed, 8 skipped**  
**Avancement global : 99 % → 99.5 %**
