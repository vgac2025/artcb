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

set -Eeuo pipefail
REPL_DIR="$(pwd)"

# ── Journal de run : créé avant toute étape de démarrage ──────────
# stdout/stderr restent visibles dans le workflow tout en étant conservés
# dans un fichier corrélé à cette tentative.
umask 077
STARTUP_LOG_DIR="${ARTCB_LOG_DIR:-$REPL_DIR/logs}"
mkdir -p "$STARTUP_LOG_DIR"
STARTUP_TS="$(date -u +%Y%m%dT%H%M%SZ)"
STARTUP_ID="${STARTUP_TS}_$$"
STARTUP_LOG="$STARTUP_LOG_DIR/startup_${STARTUP_ID}.log"
export ARTCB_STARTUP_ID="$STARTUP_ID"
export ARTCB_STARTUP_LOG="$STARTUP_LOG"
exec > >(tee -a "$STARTUP_LOG") 2>&1

CURRENT_STEP="bootstrap"
UVICORN_PID=""
FRONTEND_PID=""
PQC_PID=""

_log() {
  printf '[%s] [startup_id=%s] [step=%s] %s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$STARTUP_ID" "$CURRENT_STEP" "$*"
}

_on_error() {
  local status=$?
  _log "ERROR command=${BASH_COMMAND@Q} status=$status"
}

_on_exit() {
  local status=$?
  _log "EXIT status=$status uvicorn_pid=${UVICORN_PID:-none} frontend_pid=${FRONTEND_PID:-none} pqc_pid=${PQC_PID:-none}"
}

_on_signal() {
  local signal="$1"
  _log "SIGNAL received=$signal"
  for pid in "$UVICORN_PID" "$FRONTEND_PID" "$PQC_PID"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill -TERM "$pid" 2>/dev/null || true
    fi
  done
  exit 128
}

trap _on_error ERR
trap _on_exit EXIT
trap '_on_signal TERM' TERM
trap '_on_signal INT' INT
_log "START pid=$$ repl_dir=$REPL_DIR log_file=$STARTUP_LOG"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║         ARTCB Replit — Démarrage complet v4              ║"
echo "╚══════════════════════════════════════════════════════════╝"

# ── 0. Pull GitHub EN PREMIER — avant tout build ─────────────────
CURRENT_STEP="git_sync"
_log "STEP begin"
if [ -d .git ] && git remote -v 2>/dev/null | grep -q github; then
  echo "[0/6] Pull GitHub (mise à jour code) ..."
  git config --global --add safe.directory "$REPL_DIR" 2>/dev/null || true
  git pull origin "${GITHUB_BRANCH:-main}" --ff-only \
    && echo "  Code à jour ✅" \
    || echo "  ⚠️ git pull échoué — démarrage avec code existant"
fi
_log "STEP end"

# ── 1. Venv Python isolé (contourne NixOS PEP 668) ───────────────
CURRENT_STEP="python_venv"
_log "STEP begin"
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
_log "STEP end venv=$VENV"

# ── 2. Installation des dépendances via venv ──────────────────────
CURRENT_STEP="python_dependencies"
_log "STEP begin"
echo "[2/6] Installation des dépendances Python..."
$PIP install --no-user -r requirements.txt \
    --ignore-requires-python \
    2>&1
# Fallback litellm
if ! $PIP show litellm-ibm-bob &>/dev/null; then
  $PIP install --no-user "litellm>=1.0.0" 2>&1 || _log "WARN litellm fallback installation failed"
fi
_log "STEP end"

# ── 3. Patch oqs.py — évite l'auto-install bloquant ──────────────
CURRENT_STEP="oqs_patch"
_log "STEP begin"
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
" || _log "WARN oqs.py patch skipped"
_log "STEP end"

# ── 4. Injecter secrets Doppler (si token disponible) ────────────
CURRENT_STEP="doppler"
_log "STEP begin"
_DTOKEN="${DOPPLER_TOKEN:-${DOPPLER_TOKEN_REPLIT:-}}"
if [ -n "$_DTOKEN" ] && command -v doppler &>/dev/null; then
  echo "[4/6] Injection secrets Doppler..."
  doppler configure set token "$_DTOKEN" || _log "WARN Doppler token configuration failed"
  doppler configure set project artcb-blockchain || _log "WARN Doppler project configuration failed"
  doppler configure set config dev || _log "WARN Doppler config configuration failed"
  if _DOPPLER_ENV="$(doppler secrets download --no-file --format env | grep -v '^#')"; then
    eval "$_DOPPLER_ENV"
  else
    _log "WARN Doppler secrets download failed"
  fi
  echo "      Secrets Doppler injectés"
else
  echo "[4/6] Doppler ignoré — variables Replit utilisées"
fi
_log "STEP end"

# ── 5. Compiler libartcb_chain.so si absent ───────────────────────
CURRENT_STEP="c_chain_build"
_log "STEP begin"
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
      "$OPENSSL_LIB" \
      && echo "  libartcb_chain.so compilé ✅" \
      || echo "  ⚠️ libartcb_chain.so échoué — mode fallback Python"
  else
    echo "  ⚠️ Compilateur/OpenSSL non trouvé — mode fallback Python"
  fi
else
  echo "  libartcb_chain.so déjà présent ✅"
fi
_log "STEP end"

# ── 6. Build frontend EN ARRIÈRE-PLAN si dist absent/obsolète ────
# CRITIQUE déploiement : npm build (~45s) NE DOIT PAS bloquer uvicorn.
# Le healthcheck Replit Autoscale timeout à ~60s → uvicorn doit ouvrir
# le port 5000 AVANT la fin du build. FastAPI retourne 200 sur /
# même sans dist/ (fallback JSON) le temps que le build se termine.
CURRENT_STEP="frontend_prepare"
_log "STEP begin"
echo "[6/6] Frontend React (arrière-plan si nécessaire)..."
FRONTEND_DIST="$REPL_DIR/frontend/dist/index.html"
FRONTEND_SRC="$REPL_DIR/frontend/src"
if [ ! -f "$FRONTEND_DIST" ] || [ -n "$(find "$FRONTEND_SRC" -newer "$FRONTEND_DIST" 2>/dev/null | head -1)" ]; then
  echo "  ⚡ dist/ absent ou obsolète — build lancé en arrière-plan (non bloquant)"
  (
    CURRENT_STEP="frontend_background"
    _log "BACKGROUND begin pid=$BASHPID"
    cd "$REPL_DIR/frontend"
    npm install 2>&1
    npm run build 2>&1
    echo "  ✅ Frontend buildé en arrière-plan — rechargez la page"
    _log "BACKGROUND end status=0"
  ) &
  FRONTEND_PID=$!
  _log "BACKGROUND launched name=frontend pid=$FRONTEND_PID"
else
  echo "  dist/ à jour ✅"
fi
_log "STEP end"

# ── PQC POST-START : liboqs installé EN ARRIÈRE-PLAN ─────────────
# P0-1 FIX : liboqs cmake build (2-5 min) est déplacé APRÈS le démarrage
# d'uvicorn pour ne PAS bloquer le healthcheck Replit (timeout 60s).
# Le script setup_pqc_background.sh est lancé en parallèle et s'arrête
# dès qu'uvicorn est prêt, sans jamais bloquer l'API.
_launch_pqc_background() {
  CURRENT_STEP="pqc_background"
  _log "BACKGROUND begin pid=$BASHPID"
  if $PYTHON -c "import oqs; oqs.get_enabled_sig_mechanisms()" &>/dev/null 2>&1; then
    echo "PQC: liboqs déjà opérationnel ✅"
    _log "BACKGROUND end status=0 result=already_operational"
    return
  fi
  if ! command -v cmake &>/dev/null; then
    echo "PQC: cmake absent — fallback Ed25519 actif"
    _log "BACKGROUND end status=0 result=fallback_cmake_absent"
    return
  fi
  echo "PQC: installation liboqs-python en arrière-plan (~2-5 min)..."
  if ! $PIP install --no-user "liboqs-python>=0.14.0" 2>&1; then
    _log "WARN liboqs-python installation command failed"
  fi
  if $PYTHON -c "import oqs; oqs.get_enabled_sig_mechanisms()" &>/dev/null 2>&1; then
    echo "PQC: liboqs-python installé — ML-DSA-65 + ML-KEM-768 ACTIFS ✅ (redémarrage conseillé)"
    _log "BACKGROUND end status=0 result=installed"
  else
    echo "PQC: compilation échouée — fallback Ed25519/X25519 actif"
    _log "BACKGROUND end status=1 result=fallback"
    return 1
  fi
}
export -f _launch_pqc_background 2>/dev/null || true
(
  _launch_pqc_background
) &
PQC_PID=$!
_log "BACKGROUND launched name=pqc pid=$PQC_PID"

# ── Démarrage ARTCB API (< 30s après le script) ───────────────────
CURRENT_STEP="uvicorn"
_log "STEP begin"
echo ""
echo "  ✅ Démarrage ARTCB API sur :5000 (Replit webview)..."
"$PYTHON" -m uvicorn src.api.main:app \
  --host 0.0.0.0 \
  --port 5000 \
  --log-level info &
UVICORN_PID=$!
_log "FOREGROUND launched name=uvicorn pid=$UVICORN_PID port=5000"
set +e
wait "$UVICORN_PID"
UVICORN_STATUS=$?
set -e
_log "FOREGROUND end name=uvicorn status=$UVICORN_STATUS"
exit "$UVICORN_STATUS"
