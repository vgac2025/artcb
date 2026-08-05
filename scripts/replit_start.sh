#!/bin/bash
# ARTCB — Script de démarrage Replit (v3 — git pull EN PREMIER, puis build)
# Corrige automatiquement :
#   - PEP 668 (pip bloqué sur Python NixOS)  → venv isolé
#   - litellm-ibm-bob absent sur PyPI public  → litellm standard
#   - liboqs RuntimeError/SystemExit          → patch oqs.py
#   - Port 8000 vs 5000 Replit webview        → port 5000
#   - libartcb_chain.so absent                → compilation auto
#   - git pull AVANT build (v2 avait git pull APRÈS = corrections jamais propagées)
# ──────────────────────────────────────────────────────────────────

set -e
REPL_DIR="$(pwd)"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║         ARTCB Replit — Démarrage complet v3              ║"
echo "╚══════════════════════════════════════════════════════════╝"

# ── 0. Pull GitHub EN PREMIER — avant tout build ─────────────────
# CRITIQUE : le git pull doit être fait AVANT le build frontend et AVANT
# l'installation des dépendances, pour que les nouvelles corrections soient
# prises en compte dès le premier démarrage d'un clone utilisateur.
if [ -d .git ] && git remote -v 2>/dev/null | grep -q github; then
  echo "[0/7] Pull GitHub (mise à jour code) ..."
  git config --global --add safe.directory "$REPL_DIR" 2>/dev/null || true
  git pull origin "${GITHUB_BRANCH:-main}" --ff-only 2>/dev/null \
    && echo "  Code à jour ✅" \
    || echo "  ⚠️ git pull échoué (conflit local ?) — démarrage avec code existant"
fi

# ── 1. Venv Python isolé (contourne NixOS PEP 668) ───────────────
VENV="$HOME/venv"
if [ ! -f "$VENV/bin/python3" ]; then
  echo "[1/7] Création venv Python isolé (NixOS PEP 668)..."
  python3 -m venv "$VENV"
else
  echo "[1/7] Venv existant : $VENV"
fi
export PATH="$VENV/bin:$PATH"
PIP="$VENV/bin/pip"
PYTHON="$VENV/bin/python3"
# Override Replit global pip.conf (user = yes) which breaks venv installs
export PIP_USER=false

# ── 2. Installation des dépendances via venv ──────────────────────
echo "[2/7] Installation des dépendances Python..."
$PIP install --no-user -r requirements.txt -q 2>&1 | grep -v "^Requirement already" | tail -5 || true
# Fallback : litellm-ibm-bob souvent absent sur PyPI public
$PIP show litellm-ibm-bob &>/dev/null || $PIP install --no-user "litellm>=1.0.0" -q 2>/dev/null || true

# ── 2b. Crypto post-quantique (liboqs-python ML-DSA-65 + ML-KEM-768) ─
echo "[2b/7] Vérification crypto post-quantique (liboqs-python)..."
if $PYTHON -c "import oqs; oqs.get_enabled_sig_mechanisms()" &>/dev/null 2>&1; then
  echo "  liboqs-python déjà opérationnel — ML-DSA-65 + ML-KEM-768 ACTIFS ✅"
else
  if command -v cmake &>/dev/null; then
    echo "  cmake détecté — tentative installation liboqs-python (~2-5 min)..."
    $PIP install --no-user "liboqs-python>=0.14.0" -q 2>&1 | tail -3 || true
    if $PYTHON -c "import oqs; oqs.get_enabled_sig_mechanisms()" &>/dev/null 2>&1; then
      echo "  liboqs-python installé — ML-DSA-65 + ML-KEM-768 ACTIFS ✅"
    else
      echo "  ⚠️ liboqs-python compilé mais non fonctionnel — fallback Ed25519/X25519 actif"
    fi
  else
    echo "  ⚠️ cmake absent — liboqs-python non compilable — fallback Ed25519/X25519 actif"
  fi
fi

# ── 3. Patch oqs.py — évite l'auto-install bloquant ──────────────
# oqs.py lève SystemExit (BaseException) quand le .so natif manque —
# kem.py/pqc.py ont un fallback X25519, mais seulement si on attrape
# l'exception. Ce patch transforme SystemExit → RuntimeError.
echo "[3/7] Patch oqs.py (évite auto-install bloquant liboqs)..."
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
# Replit expose le token sous DOPPLER_TOKEN ou DOPPLER_TOKEN_REPLIT
_DTOKEN="${DOPPLER_TOKEN:-${DOPPLER_TOKEN_REPLIT:-}}"
if [ -n "$_DTOKEN" ] && command -v doppler &>/dev/null; then
  echo "[4/7] Injection secrets Doppler..."
  doppler configure set token "$_DTOKEN" 2>/dev/null || true
  doppler configure set project artcb-blockchain 2>/dev/null || true
  doppler configure set config dev 2>/dev/null || true
  eval "$(doppler secrets download --no-file --format env 2>/dev/null | grep -v '^#' || true)"
  echo "      Secrets Doppler injectés"
else
  echo "[4/7] Doppler ignoré — variables Replit utilisées"
fi

# ── 5. Compiler libartcb_chain.so si absent ───────────────────────
echo "[5/7] Compilation libartcb_chain.so..."
if [ ! -f "src/c/libartcb_chain.so" ]; then
  # Paths connus sur Replit NixOS (évite find /nix/store qui est très lent)
  NIX_CC="/nix/store/a0d7m3zn9p2dfa1h7ag9h2wzzr2w25sn-gcc-wrapper-14.2.1.20250322/bin/cc"
  NIX_SSL="/nix/store/2cwpdm6fcc53f8jgxmagransrfp0igbl-openssl-3.4.1/lib/libcrypto.so"
  NIX_INC="/nix/store/2cwpdm6fcc53f8jgxmagransrfp0igbl-openssl-3.4.1/include"
  CC_CMD=""; OPENSSL_LIB=""; OPENSSL_INC=""
  # Prefer known Nix paths, fall back to PATH
  if [ -x "$NIX_CC" ] && [ -f "$NIX_SSL" ]; then
    CC_CMD="$NIX_CC"; OPENSSL_LIB="$NIX_SSL"; OPENSSL_INC="$NIX_INC"
  elif command -v cc &>/dev/null && [ -f "/lib/x86_64-linux-gnu/libcrypto.so.3" ]; then
    CC_CMD="cc"; OPENSSL_LIB="/lib/x86_64-linux-gnu/libcrypto.so.3"; OPENSSL_INC="/usr/include"
  fi

  if [ -n "$CC_CMD" ] && [ -f "$OPENSSL_LIB" ]; then
    $CC_CMD -Wall -O2 -fPIC \
      -I"$OPENSSL_INC" \
      src/c/libartcb_chain.c -o src/c/libartcb_chain.so -shared \
      "$OPENSSL_LIB" 2>/dev/null \
      && echo "  libartcb_chain.so compilé ✅" \
      || echo "  ⚠️ Compilation libartcb_chain.so échouée — mode fallback Python"
  else
    echo "  ⚠️ Compilateur/OpenSSL non trouvé — mode fallback Python"
  fi
else
  echo "  libartcb_chain.so déjà présent ✅"
fi

# ── 6. Build frontend si dist absent ou sources plus récentes ────
# IMPORTANT : ce build se fait APRÈS git pull (étape 0), donc les
# nouveaux fichiers src/ sont pris en compte à chaque redémarrage.
echo "[6/7] Frontend React..."
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

# ── 7. Lancer l'API ───────────────────────────────────────────────
echo "[7/7] Démarrage ARTCB API..."
echo ""
echo "  ✅ Démarrage ARTCB API sur :5000 (Replit webview)..."
exec $PYTHON -m uvicorn src.api.main:app \
  --host 0.0.0.0 \
  --port 5000 \
  --log-level info
