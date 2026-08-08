#!/bin/bash
# ARTCB — Script de démarrage Replit (v5 — bootstrap automatique + port dynamique)
# Corrige automatiquement :
#   - PEP 668 (pip bloqué sur Python NixOS)        → venv isolé
#   - litellm-ibm-bob absent sur PyPI public        → litellm standard
#   - liboqs RuntimeError/SystemExit                → patch oqs.py
#   - Port 8000 vs 5000 Replit webview              → port 5000 (dynamique si occupé)
#   - libartcb_chain.so absent                      → compilation auto
#   - git pull AVANT build (v3 corrigé)
#   - liboqs cmake build EN ARRIÈRE-PLAN (v4)       → démarrage < 30s garanti
#   - ARTCB_NODE_WALLET_ADDRESS absent (v5 NEW)     → mode bootstrap, API partielle
#   - URL publique Replit (v5 NEW)                  → détectée + injectée auto
#   - Port déjà occupé (v5 NEW)                     → fallback port libre automatique
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
echo "║         ARTCB Replit — Démarrage complet v5              ║"
echo "╚══════════════════════════════════════════════════════════╝"

# ── 0b. Injection URL publique Replit AVANT tout le reste ────────
# Replit injecte REPLIT_DOMAINS = "lvx--supermicro20238.repl.co"
# (peut contenir plusieurs domaines séparés par des virgules).
# On injecte ARTCB_NODE_PUBLIC_URL si pas déjà défini par l'opérateur.
# Cette variable est lue par setup_routes.py::_detect_public_url()
# et par logging_config.py::_node_suffix().
CURRENT_STEP="public_url_detect"
_log "STEP begin"
if [ -z "${ARTCB_NODE_PUBLIC_URL:-}" ]; then
  # Essai 1 : REPLIT_DOMAINS (format moderne Replit)
  if [ -n "${REPLIT_DOMAINS:-}" ]; then
    # Prendre le premier domaine (CSV possible)
    _FIRST_DOMAIN="$(echo "$REPLIT_DOMAINS" | cut -d',' -f1 | tr -d ' ')"
    export ARTCB_NODE_PUBLIC_URL="https://${_FIRST_DOMAIN}"
    _log "public_url detected from REPLIT_DOMAINS: $ARTCB_NODE_PUBLIC_URL"
  # Essai 2 : REPL_SLUG + REPL_OWNER (ancienne convention)
  elif [ -n "${REPL_SLUG:-}" ] && [ -n "${REPL_OWNER:-}" ]; then
    export ARTCB_NODE_PUBLIC_URL="https://${REPL_OWNER}--${REPL_SLUG}.repl.co"
    _log "public_url detected from REPL_SLUG+REPL_OWNER: $ARTCB_NODE_PUBLIC_URL"
  else
    _log "WARN public_url not detected — ARTCB_NODE_PUBLIC_URL will be empty"
  fi
else
  _log "public_url from env: $ARTCB_NODE_PUBLIC_URL"
fi
_log "STEP end public_url=${ARTCB_NODE_PUBLIC_URL:-UNKNOWN}"

# ── 0c. Détection port libre ──────────────────────────────────────
# Replit webview attend le port 5000. Si ce port est déjà occupé
# (redémarrage rapide, autre processus), on cherche le prochain libre.
CURRENT_STEP="port_detect"
_log "STEP begin"
_find_free_port() {
  local preferred="$1"
  # Vérifier si le port préféré est libre (nc -z → succès si occupé)
  if ! nc -z 127.0.0.1 "$preferred" 2>/dev/null; then
    echo "$preferred"
    return
  fi
  # Port occupé → chercher un port libre à partir de preferred+1
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
_log "STEP end port=$ARTCB_PORT"
if [ "$ARTCB_PORT" != "5000" ]; then
  echo "  ⚠️  Port 5000 occupé — utilisation du port $ARTCB_PORT"
  echo "  ⚠️  Si Replit webview ne répond pas, redémarrez le Repl pour libérer le port."
fi

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
#
# POURQUOI liboqs revient à ❌ après chaque redéploiement ?
#   liboqs-python sur PyPI COMPILE liboqs depuis les sources via cmake.
#   Sur Replit : le venv est recréé à chaque cold start → liboqs est
#   recompilé à chaque démarrage (~2-5 min). Si cmake échoue ou timeout,
#   le paquet s'installe SANS le .so natif → oqs importable MAIS non fonctionnel.
#   Solution : forcer une recompilation propre si le .so est absent/cassé.
_launch_pqc_background() {
  CURRENT_STEP="pqc_background"
  _log "BACKGROUND begin pid=$BASHPID"

  # Test 1 : liboqs déjà opérationnel (le cas normal après le 1er démarrage réussi)
  if $PYTHON -c "import oqs; oqs.get_enabled_sig_mechanisms()" &>/dev/null 2>&1; then
    echo "PQC: liboqs déjà opérationnel ✅"
    _log "BACKGROUND end status=0 result=already_operational"
    return 0
  fi

  # Test 2 : cmake disponible ?
  if ! command -v cmake &>/dev/null; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  ⚠️  PQC DÉGRADÉ — cmake absent                            ║"
    echo "╠══════════════════════════════════════════════════════════════╣"
    echo "║  ML-DSA-65 + ML-KEM-768 ne peuvent pas être compilés.      ║"
    echo "║  Les wallets seront créés en mode Ed25519 pur (hybrid=False)║"
    echo "║                                                              ║"
    echo "║  Pour activer le mode post-quantique :                      ║"
    echo "║  1. Vérifiez que replit.nix contient pkgs.cmake + pkgs.gcc  ║"
    echo "║  2. Redémarrez le Repl pour recharger l'environnement Nix   ║"
    echo "║  3. Vérifiez avec : which cmake && cmake --version           ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    _log "BACKGROUND end status=0 result=fallback_cmake_absent"
    return 0
  fi

  echo "PQC: cmake trouvé ($(cmake --version | head -1)) — compilation liboqs-python..."
  _log "BACKGROUND cmake_found version=$(cmake --version | head -1)"

  # Tentative 1 : installation standard pip (utilise le cache wheel si disponible)
  echo "PQC: tentative 1/2 — pip install liboqs-python..."
  if $PIP install --no-user --upgrade "liboqs-python>=0.14.0" 2>&1; then
    _log "BACKGROUND pip install returned 0"
  else
    _log "WARN pip install liboqs-python returned non-zero"
  fi

  # Vérification immédiate après pip
  if $PYTHON -c "import oqs; oqs.get_enabled_sig_mechanisms()" &>/dev/null 2>&1; then
    echo "PQC: liboqs-python installé ✅ ML-DSA-65 + ML-KEM-768 ACTIFS (redémarrage conseillé pour les wallets existants)"
    _log "BACKGROUND end status=0 result=installed_pip"
    return 0
  fi

  # Tentative 2 : forcer la recompilation depuis les sources (--no-binary)
  echo "PQC: tentative 2/2 — recompilation depuis les sources (--no-binary)..."
  _log "BACKGROUND attempt2 no_binary"
  if $PIP install --no-user --upgrade --no-binary liboqs-python "liboqs-python>=0.14.0" 2>&1; then
    _log "BACKGROUND pip install --no-binary returned 0"
  else
    _log "WARN pip install --no-binary returned non-zero"
  fi

  # Vérification finale
  if $PYTHON -c "import oqs; oqs.get_enabled_sig_mechanisms()" &>/dev/null 2>&1; then
    echo "PQC: liboqs-python compilé depuis sources ✅ ML-DSA-65 + ML-KEM-768 ACTIFS"
    _log "BACKGROUND end status=0 result=installed_source"
    return 0
  fi

  # Échec définitif — afficher un message d'action clair
  echo ""
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║  ❌  PQC DÉGRADÉ — liboqs compilation échouée              ║"
  echo "╠══════════════════════════════════════════════════════════════╣"
  echo "║  ML-DSA-65 + ML-KEM-768 désactivés.                        ║"
  echo "║  Les wallets créés auront hybrid=False (Ed25519 pur).       ║"
  echo "║                                                              ║"
  echo "║  ACTIONS REQUISES :                                          ║"
  echo "║  1. Vérifier replit.nix : pkgs.cmake + pkgs.gcc + pkgs.ninja║"
  echo "║  2. Redémarrer le Repl (shell Nix rechargé)                 ║"
  echo "║  3. Dans le shell : pip install liboqs-python --no-binary   ║"
  echo "║  4. Si toujours échoué : les logs du build ci-dessus        ║"
  echo "║     contiennent l'erreur cmake exacte.                      ║"
  echo "║                                                              ║"
  echo "║  Le nœud FONCTIONNE normalement sans PQC (sécurité réduite).║"
  echo "║  Vérifier le statut : GET /health → pqc.available           ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
  echo ""
  _log "BACKGROUND end status=1 result=fallback_compile_failed"
  return 1
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
if [ -z "${ARTCB_NODE_WALLET_ADDRESS:-}" ]; then
  # Vérifier aussi le .node_config persisté
  _DATA_DIR="${ARTCB_DATA_DIR:-$REPL_DIR/data}"
  _NODE_CFG="$_DATA_DIR/.node_config"
  if [ -f "$_NODE_CFG" ] && python3 -c "import json,sys; d=json.load(open('$_NODE_CFG')); sys.exit(0 if d.get('wallet_address') else 1)" 2>/dev/null; then
    echo "  ✅ Identité nœud lue depuis .node_config — démarrage normal"
  else
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  ⚠️  MODE BOOTSTRAP — Premier déploiement détecté           ║"
    echo "╠══════════════════════════════════════════════════════════════╣"
    echo "║  Ce nœud n'a pas encore d'identité configurée.              ║"
    echo "║  L'API démarre en mode limité.                               ║"
    echo "║                                                              ║"
    echo "║  → Ouvrez le dashboard et appelez :                         ║"
    echo "║    POST /setup/init-node                                     ║"
    echo "║    { \"node_name\": \"mon_noeud\", \"password\": \"VotrePass123\" }   ║"
    echo "║                                                              ║"
    echo "║  → Sauvegardez la seed_hex retournée (1 seule fois)         ║"
    echo "║  → Redémarrez le nœud — il démarrera en mode normal         ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
  fi
fi
echo "  ✅ Démarrage ARTCB API sur :${ARTCB_PORT} (Replit webview)..."
_log "FOREGROUND launching uvicorn port=$ARTCB_PORT public_url=${ARTCB_NODE_PUBLIC_URL:-NONE}"
"$PYTHON" -m uvicorn src.api.main:app \
  --host 0.0.0.0 \
  --port "$ARTCB_PORT" \
  --log-level info &
UVICORN_PID=$!
_log "FOREGROUND launched name=uvicorn pid=$UVICORN_PID port=$ARTCB_PORT"
set +e
wait "$UVICORN_PID"
UVICORN_STATUS=$?
set -e
_log "FOREGROUND end name=uvicorn status=$UVICORN_STATUS"
exit "$UVICORN_STATUS"
