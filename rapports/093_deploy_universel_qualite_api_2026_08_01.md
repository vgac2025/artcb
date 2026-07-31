# Rapport 093 — Phase 12.3 déploiement universel + 12.5 qualité API
**Date :** 2026-08-01  
**Statut :** ✅ 371/371 PASS  
**Phase :** 12.3 + 12.5

---

## Résumé

Session dédiée à deux axes en parallèle :
1. **Qualité API (Phase 12.5)** — 3 jalons supplémentaires complétés
2. **Déploiement universel (Phase 12.3)** — 4 fichiers créés/mis à jour

---

## Phase 12.5 — Qualité API

### 12.5.3 ✅ `wallet_create` retourne hybrid + address_v2

Avant, `POST /api/v1/wallet/create` retournait seulement `address` (Ed25519). Maintenant :
```json
{
  "name": "mon_wallet",
  "address": "artcb1...",
  "public_key_hex": "...",
  "public_key_b64": "...",
  "hybrid": true,
  "address_v2": "artcb1pqc..."
}
```
- `hybrid: true` → clés ML-DSA-65 générées
- `address_v2` → adresse dérivée de la clé PQC ML-DSA-65

### 12.5.5 ✅ Cache IR encode (déjà implémenté)
Le cache est déjà présent dans [`src/artcb/ir/encoder.py:39`](src/artcb/ir/encoder.py:39) — `enable_cache=True` par défaut. Hash SHA-256 du texte → graph réutilisé avec nouveau `graph_id`. Tâche marquée terminée.

---

## Phase 12.3 — Déploiement universel

### 12.3.2 ✅ Replit ready

**[`.replit`](.replit)** mis à jour :
- Lance `scripts/replit_start.sh` au démarrage
- Variables d'environnement ARTCB injectées dans Replit
- Port 8000 exposé sur port externe 80

**[`scripts/replit_start.sh`](scripts/replit_start.sh)** créé :
1. Installe Doppler CLI si absent
2. Configure Doppler avec `$DOPPLER_TOKEN` (variable secrète Replit)
3. `pip install -r requirements.txt`
4. Lance `uvicorn` avec les secrets injectés

**[`replit.nix`](replit.nix)** mis à jour :
- Ajout `liboqs` (PQC natif), `ninja`, `git`
- Suppression dépendances inutiles

### 12.3.3 ✅ Codespaces / Gitpod

**[`.devcontainer/devcontainer.json`](.devcontainer/devcontainer.json)** mis à jour :
- Image Python 3.12 Bullseye
- `postCreateCommand` → `bash .devcontainer/setup.sh`
- Extensions VSCode : python, pylance, debugpy
- Tests pytest configurés automatiquement
- Variables ARTCB pré-configurées

**[`.devcontainer/setup.sh`](.devcontainer/setup.sh)** créé :
- Installe Doppler + configure avec `$DOPPLER_TOKEN`
- `pip install -r requirements.txt`

### 12.3.4 ✅ Dockerfile officiel

**[`Dockerfile`](Dockerfile)** refactorisé :
- Base : `python:3.12-slim-bullseye`
- Dépendances système : cmake, ninja, gcc, openssl pour liboqs
- Cache layer Docker optimisé (requirements avant code)
- `HEALTHCHECK` sur `/api/v1/health` (correction de l'ancien `/health`)
- Variables env par défaut propres (debug=false en prod)

### 12.3.5 ✅ docker-compose.yml

**[`docker-compose.yml`](docker-compose.yml)** refactorisé :
- Service `artcb-api` principal (port 8000)
- Service `artcb-node2` en profil `multinode` (port 8001)
- `healthcheck` correct sur `/api/v1/health`
- Volumes nommés pour persistance chaîne + logs + rapports
- Variables d'env proprement passées depuis `.env`

---

## Infrastrucure Replit — Token Doppler dédié

Token créé pour l'agent Replit (lecture seule, projet artcb-blockchain/dev) :
```
dp.st.dev.******* (fourni séparément — ne pas committer)
```
→ À configurer dans les **Secrets Replit** sous le nom `DOPPLER_TOKEN`

---

## État Phase 12 après cette session

| Phase | Jalon | Statut |
|-------|-------|--------|
| 12.5.1 | `/store` async (BUG-P0-1) | ✅ |
| 12.5.2 | Auto-encode dans `/store` (BUG-P0-2) | ✅ |
| 12.5.3 | `wallet_create` → hybrid + address_v2 | ✅ |
| 12.5.5 | Cache IR encode | ✅ |
| 12.3.2 | Replit ready | ✅ |
| 12.3.3 | Codespaces/Gitpod | ✅ |
| 12.3.4 | Dockerfile officiel | ✅ |
| 12.3.5 | docker-compose.yml | ✅ |

**Tests :** 371/371 PASS — commit `ee3fc12` → `main`

---

## Prochains jalons P1

| Phase | Jalon | Priorité |
|-------|-------|---------|
| 12.5.6 | Documenter graph_id dans API_REFERENCE_ARTCB | P1 |
| 12.3.1 | `flake.nix` environnement Nix | P1 |
| 12.3.6 | `render.yaml` / `railway.toml` deploy 1-clic | P2 |
| 12.1.1 | Serveur MCP ARTCB | P1 |
| 13.1 | libp2p natif | P2 |

---

*ARTCB v0.3.0 — 2026-08-01*
