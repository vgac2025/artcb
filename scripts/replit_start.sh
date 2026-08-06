#!/bin/bash
# ARTCB — Script de démarrage Replit (v4 — démarrage rapide < 30s)
# Corrige automatiquement :
#   - PEP 668 (pip bloqué sur Python NixOS)  → venv isolé
#   - litellm-ibm-bob absent sur PyPI public  → litellm standard
#   - liboqs RuntimeError/SystemExit          → patch oqs.py
#   - Port 8000 vs 5000 Replit webview        → port 5000
#   - libartcb_chain.so absent                → compilation auto
#   - git pull AVANT build (v3 corrigé)
#   - liboqs cmake build EN ARRIÈRE-PLAN (v4) → démarrage < 30s garanti
# ──────────────────────────────────────────────────────────────────

set -e
REPL_DIR="$(pwd)"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║         ARTCB Replit — Démarrage complet v4              ║"
echo "╚══════════════════════════════════════════════════════════╝"

# ── 0. Pull GitHub EN PREMIER — avant tout build ─────────────────
if [ -d .git ] && git remote -v 2>/dev/null | grep -q github; then
  echo "[0/6] Pull GitHub (mise à jour code) ..."
  git config --global --add safe.directory "$REPL_DIR" 2>/dev/null || true
  git pull origin "${GITHUB_BRANCH:-main}" --ff-only 2>/dev/null \
    && echo "  Code à jour ✅" \
    || echo "  ⚠️ git pull échoué — démarrage avec code existant"
fi

# ── 1. Venv Python isolé (contourne NixOS PEP 668) ───────────────
VENV="$HOME/venv"
if [ ! -f "$VENV/bin/python3" ]; then
  echo "[1/6] Création venv Python isolé (NixOS PEP 668)..."
  python3 -m venv "$VENV"
else
  echo "[1/6] Venv existant : $VENV"
fi
export PATH="$VENV/bin:$PATH"
PIP="$VENV/bin/pip"
PYTHON="$VENV/bin/python3"
export PIP_USER=false

# ── 2. Installation des dépendances via venv ──────────────────────
echo "[2/6] Installation des dépendances Python..."
$PIP install --no-user -r requirements.txt \
    --ignore-requires-python \
    -q 2>&1 | grep -v "^Requirement already" | tail -5 || true
# Fallback litellm
$PIP show litellm-ibm-bob &>/dev/null || $PIP install --no-user "litellm>=1.0.0" -q 2>/dev/null || true

# ── 3. Patch oqs.py — évite l'auto-install bloquant ──────────────
echo "[3/6] Patch oqs.py (fallback RuntimeError)..."
$PYTHON -c "
import sys, os
for p in sys.path:
    f = os.path.join(p, 'oqs', 'oqs.py')
    if os.path.exists(f):
        with open(f) as fh: content = fh.read()
        if 'raise SystemExit(msg) from None' in content:
            patched = content.replace('raise SystemExit(msg) from None', 'raise RuntimeError(msg) from None')
            with open(f, 'w') as fh: fh.write(patched)
            print('  oqs.py patché (SystemExit → RuntimeError)')
        else:
            print('  oqs.py déjà patché ou absent')
        break
" 2>/dev/null || echo "  (patch oqs.py ignoré)"

# ── 4. Injecter secrets Doppler (si token disponible) ────────────
_DTOKEN="${DOPPLER_TOKEN:-${DOPPLER_TOKEN_REPLIT:-}}"
if [ -n "$_DTOKEN" ] && command -v doppler &>/dev/null; then
  echo "[4/6] Injection secrets Doppler..."
  doppler configure set token "$_DTOKEN" 2>/dev/null || true
  doppler configure set project artcb-blockchain 2>/dev/null || true
  doppler configure set config dev 2>/dev/null || true
  eval "$(doppler secrets download --no-file --format env 2>/dev/null | grep -v '^#' || true)"
  echo "      Secrets Doppler injectés"
else
  echo "[4/6] Doppler ignoré — variables Replit utilisées"
fi

# ── 5. Compiler libartcb_chain.so si absent ───────────────────────
echo "[5/6] Compilation libartcb_chain.so..."
if [ ! -f "src/c/libartcb_chain.so" ]; then
  NIX_CC="/nix/store/a0d7m3zn9p2dfa1h7ag9h2wzzr2w25sn-gcc-wrapper-14.2.1.20250322/bin/cc"
  NIX_SSL="/nix/store/2cwpdm6fcc53f8jgxmagransrfp0igbl-openssl-3.4.1/lib/libcrypto.so"
  NIX_INC="/nix/store/2cwpdm6fcc53f8jgxmagransrfp0igbl-openssl-3.4.1/include"
  CC_CMD=""; OPENSSL_LIB=""; OPENSSL_INC=""
  if [ -x "$NIX_CC" ] && [ -f "$NIX_SSL" ]; then
    CC_CMD="$NIX_CC"; OPENSSL_LIB="$NIX_SSL"; OPENSSL_INC="$NIX_INC"
  elif command -v cc &>/dev/null && [ -f "/lib/x86_64-linux-gnu/libcrypto.so.3" ]; then
    CC_CMD="cc"; OPENSSL_LIB="/lib/x86_64-linux-gnu/libcrypto.so.3"; OPENSSL_INC="/usr/include"
  fi
  if [ -n "$CC_CMD" ] && [ -f "$OPENSSL_LIB" ]; then
    $CC_CMD -Wall -O2 -fPIC -I"$OPENSSL_INC" \
      src/c/libartcb_chain.c -o src/c/libartcb_chain.so -shared \
      "$OPENSSL_LIB" 2>/dev/null \
      && echo "  libartcb_chain.so compilé ✅" \
      || echo "  ⚠️ libartcb_chain.so échoué — mode fallback Python"
  else
    echo "  ⚠️ Compilateur/OpenSSL non trouvé — mode fallback Python"
  fi
else
  echo "  libartcb_chain.so déjà présent ✅"
fi

# ── 6. Build frontend EN ARRIÈRE-PLAN si dist absent/obsolète ────
# CRITIQUE déploiement : npm build (~45s) NE DOIT PAS bloquer uvicorn.
# Le healthcheck Replit Autoscale timeout à ~60s → uvicorn doit ouvrir
# le port 5000 AVANT la fin du build. FastAPI retourne 200 sur /
# même sans dist/ (fallback JSON) le temps que le build se termine.
echo "[6/6] Frontend React (arrière-plan si nécessaire)..."
FRONTEND_DIST="$REPL_DIR/frontend/dist/index.html"
FRONTEND_SRC="$REPL_DIR/frontend/src"
if [ ! -f "$FRONTEND_DIST" ] || [ -n "$(find "$FRONTEND_SRC" -newer "$FRONTEND_DIST" 2>/dev/null | head -1)" ]; then
  echo "  ⚡ dist/ absent ou obsolète — build lancé en arrière-plan (non bloquant)"
  (
    cd "$REPL_DIR/frontend"
    npm install -q 2>&1 | tail -2
    npm run build 2>&1 | tail -5
    echo "  ✅ Frontend buildé en arrière-plan — rechargez la page"
  ) &
  disown 2>/dev/null || true
else
  echo "  dist/ à jour ✅"
fi

# ── PQC POST-START : liboqs installé EN ARRIÈRE-PLAN ─────────────
# P0-1 FIX : liboqs cmake build (2-5 min) est déplacé APRÈS le démarrage
# d'uvicorn pour ne PAS bloquer le healthcheck Replit (timeout 60s).
# Le script setup_pqc_background.sh est lancé en parallèle et s'arrête
# dès qu'uvicorn est prêt, sans jamais bloquer l'API.
_launch_pqc_background() {
  if $PYTHON -c "import oqs; oqs.get_enabled_sig_mechanisms()" &>/dev/null 2>&1; then
    echo "PQC: liboqs déjà opérationnel ✅"
    return
  fi
  if ! command -v cmake &>/dev/null; then
    echo "PQC: cmake absent — fallback Ed25519 actif"
    return
  fi
  echo "PQC: installation liboqs-python en arrière-plan (~2-5 min)..."
  $PIP install --no-user "liboqs-python>=0.14.0" -q 2>&1 | tail -2 || true
  if $PYTHON -c "import oqs; oqs.get_enabled_sig_mechanisms()" &>/dev/null 2>&1; then
    echo "PQC: liboqs-python installé — ML-DSA-65 + ML-KEM-768 ACTIFS ✅ (redémarrage conseillé)"
  else
    echo "PQC: compilation échouée — fallback Ed25519/X25519 actif"
  fi
}
export -f _launch_pqc_background 2>/dev/null || true
( _launch_pqc_background 2>&1 | while IFS= read -r line; do echo "$(date -u +%H:%M:%S) $line"; done ) &
disown 2>/dev/null || true

# ── Démarrage ARTCB API (< 30s après le script) ───────────────────
echo ""
echo "  ✅ Démarrage ARTCB API sur :5000 (Replit webview)..."
exec $PYTHON -m uvicorn src.api.main:app \
  --host 0.0.0.0 \
  --port 5000 \
  --log-level info
