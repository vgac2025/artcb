#!/bin/bash
# ARTCB — Script de démarrage Replit (v2 — compatible NixOS PEP 668)
# Corrige automatiquement :
#   - PEP 668 (pip bloqué sur Python NixOS)  → venv isolé
#   - litellm-ibm-bob absent sur PyPI public  → litellm standard
#   - liboqs RuntimeError/SystemExit          → patch oqs.py
#   - Port 8000 vs 5000 Replit webview        → port 5000
#   - libartcb_chain.so absent                → compilation auto
# ──────────────────────────────────────────────────────────────────

set -e
REPL_DIR="$(pwd)"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║         ARTCB Replit — Démarrage complet v2              ║"
echo "╚══════════════════════════════════════════════════════════╝"

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

# ── 2. Installation des dépendances via venv ──────────────────────
echo "[2/6] Installation des dépendances Python..."
$PIP install -r requirements.txt -q 2>&1 | grep -v "^Requirement already" | tail -5 || true
# Fallback : litellm-ibm-bob souvent absent sur PyPI public
$PIP show litellm-ibm-bob &>/dev/null || $PIP install "litellm>=1.0.0" -q 2>/dev/null || true

# ── 3. Patch oqs.py — évite l'auto-install bloquant ──────────────
# oqs.py lève SystemExit (BaseException) quand le .so natif manque —
# kem.py/pqc.py ont un fallback X25519, mais seulement si on attrape
# l'exception. Ce patch transforme SystemExit → RuntimeError.
echo "[3/6] Patch oqs.py (évite auto-install bloquant liboqs)..."
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

# ── 4. Installer Doppler CLI + injecter secrets ───────────────────
if ! command -v doppler &>/dev/null; then
  echo "[4/6] Installation Doppler CLI..."
  curl -Ls --tlsv1.2 --proto "=https" --retry 3 \
    https://cli.doppler.com/install.sh | sh 2>/dev/null || true
else
  echo "[4/6] Doppler CLI $(doppler --version 2>/dev/null | head -1)"
fi

if [ -n "$DOPPLER_TOKEN" ]; then
  echo "      Injection secrets Doppler (projet artcb-blockchain)..."
  doppler configure set token "$DOPPLER_TOKEN" 2>/dev/null || true
  doppler configure set project artcb-blockchain 2>/dev/null || true
  doppler configure set config dev 2>/dev/null || true
  eval "$(doppler secrets download --no-file --format env 2>/dev/null | grep -v '^#' || true)"
  echo "      Secrets Doppler injectés"
else
  echo "      DOPPLER_TOKEN absent — variables Replit utilisées"
fi

# ── 5. Compiler libartcb_chain.so si absent ───────────────────────
echo "[5/6] Compilation libartcb_chain.so..."
if [ ! -f "src/c/libartcb_chain.so" ]; then
  # Chercher un compilateur C fonctionnel
  CC_CMD=""
  for candidate in cc gcc "$(find /nix/store -name 'cc' -path '*/bin/cc' 2>/dev/null | grep runtime | head -1)"; do
    if command -v "$candidate" &>/dev/null 2>&1; then
      CC_CMD="$candidate"
      break
    fi
  done

  if [ -n "$CC_CMD" ]; then
    # Chercher OpenSSL : d'abord le système, sinon le store Nix
    OPENSSL_LIB="/lib/x86_64-linux-gnu/libcrypto.so.3"
    OPENSSL_INC="/usr/include"
    if [ ! -f "$OPENSSL_LIB" ]; then
      OPENSSL_LIB="$(find /nix/store -name 'libcrypto.so' -not -name '*.drv' 2>/dev/null | head -1)"
      OPENSSL_INC="$(find /nix/store -name 'openssl' -path '*/include/*' -not -name '*.drv' 2>/dev/null | head -1 | xargs dirname 2>/dev/null)"
    fi

    if [ -f "$OPENSSL_LIB" ]; then
      $CC_CMD -Wall -O2 -fPIC \
        -I"$OPENSSL_INC" \
        src/c/libartcb_chain.c -o src/c/libartcb_chain.so -shared \
        "$OPENSSL_LIB" 2>/dev/null \
        && echo "  libartcb_chain.so compilé ✅" \
        || echo "  ⚠️ Compilation libartcb_chain.so échouée — mode fallback Python"
    else
      echo "  ⚠️ OpenSSL non trouvé — compilation libartcb_chain.so ignorée"
    fi
  else
    echo "  ⚠️ Compilateur C non trouvé — libartcb_chain.so ignoré"
  fi
else
  echo "  libartcb_chain.so déjà présent ✅"
fi

# ── 6. Pull GitHub + lancer l'API ────────────────────────────────
if [ -d .git ] && git remote -v 2>/dev/null | grep -q github; then
  echo "[6/6] Pull GitHub..."
  git pull origin "${GITHUB_BRANCH:-main}" 2>/dev/null || true
fi

echo ""
echo "  ✅ Démarrage ARTCB API sur :5000 (Replit webview)..."
exec $PYTHON -m uvicorn src.api.main:app \
  --host 0.0.0.0 \
  --port 5000 \
  --log-level info
