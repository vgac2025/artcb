#!/bin/bash
# ARTCB — Setup DevContainer (GitHub Codespaces / Gitpod)
set -e

echo "=== ARTCB DevContainer Setup ==="

# Installer Doppler CLI
curl -Ls --tlsv1.2 --proto "=https" --retry 3 \
  https://cli.doppler.com/install.sh | sudo sh 2>/dev/null || true

# Dépendances Python
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Configurer Doppler si token disponible
if [ -n "$DOPPLER_TOKEN" ]; then
  doppler configure set token "$DOPPLER_TOKEN" 2>/dev/null || true
  doppler configure set project artcb-blockchain 2>/dev/null || true
  doppler configure set config dev 2>/dev/null || true
  echo "Doppler configuré"
fi

echo "Setup terminé. Lancer : python -m uvicorn src.api.main:app --reload"
