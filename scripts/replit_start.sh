#!/bin/bash
# ARTCB — Script de démarrage Replit
# Installe Doppler, injecte les secrets, configure SSH Git, lance l'API

set -e

PYTHONPATH="${PYTHONPATH:-/home/runner/${REPL_SLUG}}"
export PYTHONPATH

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║            ARTCB Replit — Démarrage complet              ║"
echo "╚══════════════════════════════════════════════════════════╝"

# 1. Installer Doppler CLI si absent
if ! command -v doppler &>/dev/null; then
  echo "[1/4] Installation Doppler CLI..."
  curl -Ls --tlsv1.2 --proto "=https" --retry 3 \
    https://cli.doppler.com/install.sh | sh 2>/dev/null || \
  (curl -Ls https://cli.doppler.com/install.sh | DOPPLER_INSTALL_DIR=/usr/local/bin sh 2>/dev/null) || true
else
  echo "[1/4] Doppler CLI déjà installé ($(doppler --version 2>/dev/null | head -1))"
fi

# 2. Installer les dépendances Python
echo "[2/4] Installation des dépendances..."
pip install -r requirements.txt -q

# 3. Setup SSH Git persistant (avant inject secrets — SSH_PRIVATE_KEY vient de Doppler)
echo "[3/5] Setup SSH Git persistant..."
if [ -f "scripts/setup_ssh_git.sh" ]; then
    bash scripts/setup_ssh_git.sh
fi

# 4. Injecter les secrets Doppler si token disponible
if [ -n "$DOPPLER_TOKEN" ]; then
  echo "[3/4] Injection secrets Doppler (projet artcb-blockchain / config dev)..."
  doppler configure set token "$DOPPLER_TOKEN" 2>/dev/null || true
  doppler configure set project artcb-blockchain 2>/dev/null || true
  doppler configure set config dev 2>/dev/null || true
  # Exporter les secrets dans l'environnement courant
  eval "$(doppler secrets download --no-file --format env 2>/dev/null | grep -v '^#' || true)"
  echo "[3/4] Secrets Doppler injectés ($(doppler secrets download --no-file --format env 2>/dev/null | grep -c '^[A-Z]' || echo 0) variables)"
else
  echo "[4/5] DOPPLER_TOKEN absent — utilisation des variables d'environnement Replit"
fi

# 5. Pull la dernière version depuis GitHub
if [ -d .git ] && git remote -v | grep -q github; then
  echo "[5/5] Pull dernière version depuis GitHub..."
  git pull origin "${GITHUB_BRANCH:-main}" 2>/dev/null || echo "Pull ignoré (pas de SSH)"
fi

# 6. Lancer l'API
echo "[6/6] Démarrage ARTCB API sur :8000..."
python -m uvicorn src.api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --log-level info
