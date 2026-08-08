# ARTCB — Guide de déploiement

Version 0.3.0 — 7 environnements supportés

---

## Prérequis communs

- Python 3.12+
- `pip install -r requirements.txt`
- [Doppler CLI](https://docs.doppler.com/docs/install-cli) + token projet `artcb-blockchain`
- `liboqs-python` pour la cryptographie PQC (ML-DSA-65 + ML-KEM-768) — facultatif, fallback X25519 si absent

Vérifier l'installation :
```bash
make deploy-check
```

---

## 1. Local (dev)

```bash
# Cloner
git clone https://github.com/vgactech/artcb.git && cd lvx

# Installer les dépendances
pip install -r requirements.txt

# Configurer Doppler
doppler configure set token <TON_TOKEN>
doppler configure set project artcb-blockchain
doppler configure set config dev

# Lancer l'API
make api
# → http://localhost:8000/api/v1/health

# Lancer les tests
make test
```

---

## 2. Docker

```bash
# Build + lancement
make env-docker
# → http://localhost:8000/api/v1/health

# 2 nœuds P2P (port 8000 + 8001)
make docker-multinode

# Arrêter
make docker-down

# Logs
make docker-logs
```

Variables d'environnement via fichier `.env` (copier depuis `.env.example`) :
```bash
cp .env.example .env
# Éditer .env avec vos clés
```

---

## 3. Replit

**Démarrage automatique :** le fichier [`.replit`](.replit) lance `scripts/replit_start.sh` qui :
1. Installe Doppler CLI
2. Configure Doppler avec `$DOPPLER_TOKEN` (secret Replit)
3. Configure SSH Git persistant
4. `pip install -r requirements.txt`
5. Lance l'API sur le port 8000

**Configuration :** dans les **Secrets Replit** (🔒), ajouter :
| Secret | Valeur |
|--------|--------|
| `DOPPLER_TOKEN` | Token Doppler fourni séparément |

**Changement de compte Replit :**
```bash
bash scripts/setup_ssh_git.sh
# Récupère la clé SSH depuis Doppler — git push fonctionne immédiatement
```

---

## 4. GitHub Codespaces / Gitpod

```bash
# Dans Codespaces, tout est automatique via .devcontainer/
# postCreateCommand exécute .devcontainer/setup.sh

# Puis lancer l'API :
make api
```

Variables à configurer dans les **Secrets Codespaces** :
- `DOPPLER_TOKEN`

---

## 5. Render.com

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

Fichier [`render.yaml`](render.yaml) pré-configuré.

Variables d'environnement Render :
| Variable | Valeur |
|----------|--------|
| `DOPPLER_TOKEN` | Token Doppler projet artcb-blockchain |
| `ARTCB_DEBUG` | `false` |
| `ARTCB_ENCODE_MODE` | `rule-based` |

---

## 6. Railway.app

Fichier [`railway.toml`](railway.toml) pré-configuré.

```bash
railway up
```

---

## 7. VPS / Serveur dédié

```bash
# Sur le serveur (Ubuntu 22.04+)
git clone https://github.com/vgactech/artcb.git && cd lvx

# Installer les dépendances système
sudo apt-get install -y cmake ninja-build gcc g++ libssl-dev python3.12 python3-pip

# Installer Doppler
curl -Ls https://cli.doppler.com/install.sh | sudo sh

# Configurer Doppler
doppler configure set token <TOKEN_PROD>
doppler configure set project artcb-blockchain
doppler configure set config prd

# Installer les dépendances Python
pip install -r requirements.txt

# Lancer en production
make api-prod
```

**Avec systemd :**
```ini
# /etc/systemd/system/artcb.service
[Unit]
Description=ARTCB Blockchain Node
After=network.target

[Service]
WorkingDirectory=/opt/artcb/lvx
ExecStart=/usr/bin/doppler run -- python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
User=artcb

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable artcb && sudo systemctl start artcb
```

---

## Variables d'environnement clés

| Variable | Défaut | Description |
|----------|--------|-------------|
| `ARTCB_DEBUG` | `true` | Logs détaillés |
| `ARTCB_ENCODE_MODE` | `rule-based` | `rule-based` ou `llm` |
| `ARTCB_LLM_ENABLED` | `false` | Activer les LLM |
| `ARTCB_MIN_BLOCK_INTERVAL_SEC` | `60` | Rate-limit anti-Sybil |
| `ARTCB_ANTI_SYBIL_AI_BYPASS` | `false` | Bypass en mode étude |
| `ARTCB_WALLET_PASSPHRASE` | — | Passphrase des wallets |
| `BOB_API_KEY` | — | Clé IBM Bob (LLM) |
| `DOPPLER_TOKEN` | — | Token Doppler (secrets) |

---

## Vérification santé API

```bash
curl http://localhost:8000/api/v1/health
# {"status":"ok","chain":{"block_count":N,"valid":true,"pqc_algorithm":"ML-DSA-65"}}
```

## Résumé des commandes Makefile

```bash
make help          # Afficher toutes les commandes
make api           # API locale (dev)
make test          # 371 tests
make env-docker    # Docker Compose
make env-replit    # Replit
make ssh-setup     # SSH persistant (Replit)
make deploy-check  # Vérification installation
```
