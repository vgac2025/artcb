#!/usr/bin/env bash
# ARTCB — Script setup Codespaces / Gitpod
# Appelé automatiquement par devcontainer.json → postCreateCommand
# Compatible : GitHub Codespaces, Gitpod, DevPod

set -euo pipefail

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ARTCB — Setup Codespaces/Gitpod"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Dépendances système ────────────────────────
echo "📦 Dépendances système..."
sudo apt-get update -qq
sudo apt-get install -y -qq gcc cmake make libssl-dev curl git

# ── 2. Environnement Python ───────────────────────
echo "🐍 Installation des dépendances Python..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo "✅ Dépendances Python installées"

# ── 3. Données & répertoires ──────────────────────
mkdir -p data logs rapports
touch data/.gitkeep

# ── 4. Fichier .env si absent ─────────────────────
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📋 .env créé depuis .env.example — adapter si besoin"
fi

# ── 5. Vérification PYTHONPATH ────────────────────
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"

# ── 6. Smoke test rapide ──────────────────────────
echo "🧪 Smoke test..."
python3 -c "from src.artcb.ir.encoder import IREncoder; print('  IR Engine ✅')"
python3 -c "from src.artcb.chain.manager import ChainManager; print('  Chain ✅')"
python3 -c "from src.artcb.mcp.server import ArtcbMCPServer; print('  MCP Server ✅')"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ ARTCB prêt !"
echo ""
echo "  Lancer l'API  : python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
echo "  Lancer MCP    : python -m src.artcb.mcp.server --http 8001"
echo "  Lancer tests  : python3 -m pytest tests/ -q"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
