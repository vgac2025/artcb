#!/bin/bash
# ARTCB — SSH Persistant pour Replit
# =============================================================================
# Ce script garantit que la clé SSH GitHub est toujours disponible,
# même après un redémarrage de session Replit.
#
# Usage : bash scripts/setup_ssh_git.sh
# Appel automatique : ajouté dans scripts/replit_start.sh
#
# Ordre de recherche de la clé :
#   1. Variable SSH_PRIVATE_KEY (Doppler ou secret Replit)
#   2. doppler secrets get SSH_PRIVATE_KEY
#   3. Clé publique seule via SSH_REPLIT
#   4. Génération d'urgence (affiche la clé publique à ajouter sur GitHub)
# =============================================================================

set -e

mkdir -p ~/.ssh
chmod 700 ~/.ssh

KEY_PATH="$HOME/.ssh/id_ed25519"
REPO="${GITHUB_REPO:-vgac2025/lvx}"
BRANCH="${GITHUB_BRANCH:-main}"
GIT_EMAIL="${GIT_USER_EMAIL:-artcb-mvp@hackathon.raise2026}"
GIT_NAME="${GIT_USER_NAME:-vgac2025}"
FOUND=0

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║       ARTCB — Setup SSH Git persistant (Replit)          ║"
echo "╚══════════════════════════════════════════════════════════╝"

# ── Étape 1 : Clé privée depuis variable d'environnement ─────────────────────
if [ -n "$SSH_PRIVATE_KEY" ] && echo "$SSH_PRIVATE_KEY" | grep -q "BEGIN"; then
    printf '%s\n' "$SSH_PRIVATE_KEY" > "$KEY_PATH"
    chmod 600 "$KEY_PATH"
    ssh-keygen -y -f "$KEY_PATH" > "${KEY_PATH}.pub" 2>/dev/null || true
    echo "[1/4] ✅ Clé privée chargée depuis SSH_PRIVATE_KEY (env)"
    FOUND=1
fi

# ── Étape 2 : Doppler CLI ─────────────────────────────────────────────────────
if [ "$FOUND" -eq 0 ] && command -v doppler &>/dev/null; then
    PRIV=$(doppler secrets get SSH_PRIVATE_KEY --plain 2>/dev/null || true)
    if [ -n "$PRIV" ] && echo "$PRIV" | grep -q "BEGIN"; then
        printf '%s\n' "$PRIV" > "$KEY_PATH"
        chmod 600 "$KEY_PATH"
        ssh-keygen -y -f "$KEY_PATH" > "${KEY_PATH}.pub" 2>/dev/null || true
        echo "[1/4] ✅ Clé privée chargée depuis Doppler (SSH_PRIVATE_KEY)"
        FOUND=1
    fi
fi

# ── Étape 3 : SSH_REPLIT (clé publique seulement — push impossible) ───────────
if [ "$FOUND" -eq 0 ] && [ -n "$SSH_REPLIT" ]; then
    echo "$SSH_REPLIT" > "${KEY_PATH}.pub"
    echo "[1/4] ⚠️  Seulement la clé PUBLIQUE trouvée (SSH_REPLIT)"
    echo "         → git clone OK, git push IMPOSSIBLE sans clé privée"
    echo "         → Ajoutez SSH_PRIVATE_KEY dans les secrets Replit"
    FOUND=1
fi

# ── Étape 4 : Génération d'urgence ────────────────────────────────────────────
if [ "$FOUND" -eq 0 ]; then
    echo "[1/4] ⚠️  Aucune clé persistante — génération d'urgence"
    ssh-keygen -t ed25519 -C "artcb-replit-$(date +%Y%m%d)" \
               -f "$KEY_PATH" -N ""
    echo ""
    echo "┌─── NOUVELLE CLÉ PUBLIQUE — À AJOUTER SUR GITHUB ─────────────┐"
    cat "${KEY_PATH}.pub"
    echo "└───────────────────────────────────────────────────────────────┘"
    echo ""
    echo "→ GitHub : https://github.com/settings/ssh/new"
    echo ""
    echo "Pour rendre cette clé PERSISTANTE (ne plus la régénérer) :"
    echo "   doppler secrets set SSH_PRIVATE_KEY=\"\$(cat $KEY_PATH)\""
    echo "   OU ajoutez SSH_PRIVATE_KEY dans les Secrets Replit"
fi

# ── Config SSH GitHub ─────────────────────────────────────────────────────────
cat > ~/.ssh/config << 'SSHCFG'
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no
    ServerAliveInterval 60
    ServerAliveCountMax 30
    BatchMode yes
SSHCFG
chmod 600 ~/.ssh/config

# ── Config Git ────────────────────────────────────────────────────────────────
git config --global user.email "$GIT_EMAIL"
git config --global user.name  "$GIT_NAME"
git config --global init.defaultBranch main

# ── Basculer le remote en SSH ─────────────────────────────────────────────────
if [ -d .git ]; then
    git remote set-url origin "git@github.com:${REPO}.git" 2>/dev/null || true
    echo "[2/4] ✅ Remote origin → git@github.com:${REPO}.git"
fi

# ── Afficher la clé publique active ──────────────────────────────────────────
if [ -f "${KEY_PATH}.pub" ]; then
    PUB=$(cat "${KEY_PATH}.pub")
    echo "[3/4] 📋 Clé publique active :"
    echo "       $PUB"
    # Sauvegarder pour référence
    cp "${KEY_PATH}.pub" ./github_ssh_key.txt
    echo "       → Sauvée dans github_ssh_key.txt"
fi

# ── Test connexion GitHub ─────────────────────────────────────────────────────
echo "[4/4] Test connexion GitHub..."
RESULT=$(ssh -T git@github.com 2>&1 || true)
if echo "$RESULT" | grep -q "Hi "; then
    echo "       ✅ GitHub répond : $RESULT"
else
    echo "       ⚠️  Réponse GitHub : $RESULT"
    echo "       → Vérifiez que la clé publique ci-dessus est dans :"
    echo "         https://github.com/settings/ssh/new"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Setup terminé. Commandes utiles :                       ║"
echo "║  git pull origin ${BRANCH}                                    ║"
echo "║  git push origin ${BRANCH}                                    ║"
echo "║  python3 -m pytest tests/ -x -q                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
