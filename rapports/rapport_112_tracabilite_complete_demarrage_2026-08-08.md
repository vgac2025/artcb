# Rapport 112 — Garantie de traçabilité complète de chaque démarrage

**Date :** 2026-08-08  
**Objet :** Mise en place et vérification d’une traçabilité complète du démarrage  
**Rapports précédents conservés :**

- `rapports/rapport_110_explication_healthcheck_500_2026-08-08.md`
- `rapports/rapport_111_verification_profonde_tracabilite_healthcheck_2026-08-08.md`

**Type d’intervention :** correction ciblée de la journalisation et validation réelle  
**Avancement :** 100 %  
**Statut :** ✅ Implémenté et vérifié

---

## 1. Résumé exécutif

La traçabilité complète du démarrage est maintenant active sur trois niveaux :

1. **Shell de démarrage**
   - journal créé avant le premier affichage ;
   - stdout et stderr conservés simultanément dans le workflow et dans un fichier local ;
   - identifiant unique de démarrage ;
   - étapes nommées ;
   - erreurs, signaux, PID et code de sortie enregistrés.

2. **Application Python**
   - configuration du root logger avant l’import des routeurs et de l’état applicatif ;
   - logs de tous les modules ARTCB regroupés dans un fichier JSONL ;
   - logs Uvicorn et accès HTTP regroupés dans le même fichier ;
   - `startup_id`, PID et exceptions ajoutés à chaque événement.

3. **Validation réelle**
   - workflow relancé ;
   - journal shell produit ;
   - journal JSONL produit ;
   - démarrage Uvicorn confirmé ;
   - endpoints `/`, `/health`, `/api/v1/health` et `/api/v1/chain/verify` testés ;
   - quatre réponses HTTP 200 obtenues.

Résultat vérifié :

```text
startup_log=logs/startup_20260808T113518Z_46115.log
json_log=logs/20260808_artcb_startup.json
startup_first=[2026-08-08T11:35:18Z] ... START ...
json_lines=75
json_startup_ids=1
http_statuses=/:200 /health:200 /api/v1/health:200 /api/v1/chain/verify:200
```

---

## 2. Problème avant correction

Le rapport 111 a démontré que les logs étaient fragmentés :

- le script Bash écrivait principalement dans stdout/stderr ;
- le workflow capturait une partie de ces sorties ;
- Uvicorn écrivait ses logs séparément ;
- `logs/20260808_artcb_api.json` ne contenait que le logger `artcb.api` ;
- les modules importés avant `setup_logging("artcb.api")` pouvaient émettre des erreurs sans être persistés dans le fichier applicatif ;
- les tâches arrière-plan liboqs et frontend étaient détachées avec `disown` ;
- plusieurs sorties étaient réduites avec `tail` ;
- plusieurs erreurs étaient absorbées par `|| true`.

Cette structure ne permettait pas de répondre avec certitude, pour un incident donné, à ces questions :

```text
Quelle tentative de démarrage est concernée ?
Quelle étape était active ?
Quel PID a échoué ?
Quelle commande exacte a retourné une erreur ?
Uvicorn était-il prêt ?
Le healthcheck a-t-il atteint l’application ?
Quel code HTTP a été retourné ?
Quel était le résultat final des tâches arrière-plan ?
```

---

## 3. Corrections appliquées

### 3.1 `scripts/replit_start.sh` — journal créé immédiatement

Fichier exact :

```text
scripts/replit_start.sh
```

#### Avant

Anciennes lignes 13–16 :

```bash
set -e
REPL_DIR="$(pwd)"

echo ""
```

Le premier `echo` était exécuté sans journal local de run.

#### Après

Nouvelles lignes 13–27 :

```bash
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
```

#### Effet

Le journal est créé avant :

- le bandeau de démarrage ;
- le `git pull` ;
- la vérification du venv ;
- l’installation Python ;
- le patch `oqs.py` ;
- la configuration Doppler ;
- la compilation C ;
- le build frontend ;
- le lancement PQC ;
- le lancement Uvicorn.

Preuve de la relance :

```text
[2026-08-08T11:35:18Z] [startup_id=20260808T113518Z_46115]
[step=bootstrap] START pid=46115
repl_dir=/home/runner/workspace
log_file=/home/runner/workspace/logs/startup_20260808T113518Z_46115.log
```

Cette ligne est la première ligne du fichier de run.

---

### 3.2 Identifiant de corrélation et état courant

Fichier exact :

```text
scripts/replit_start.sh
```

Nouvelles lignes 29–64 :

```bash
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
  ...
}

trap _on_error ERR
trap _on_exit EXIT
trap '_on_signal TERM' TERM
trap '_on_signal INT' INT
_log "START pid=$$ repl_dir=$REPL_DIR log_file=$STARTUP_LOG"
```

#### Effet

Chaque ligne de contrôle contient :

- timestamp UTC ;
- `startup_id` ;
- étape active ;
- événement ;
- PID lorsque nécessaire ;
- code de sortie lorsque disponible.

Les terminaisons et signaux ne sont plus silencieux.

---

### 3.3 Étapes de démarrage nommées

Fichier exact :

```text
scripts/replit_start.sh
```

Exemples de nouvelles lignes :

```bash
CURRENT_STEP="git_sync"
_log "STEP begin"
...
_log "STEP end"
```

Étapes instrumentées :

```text
git_sync
python_venv
python_dependencies
oqs_patch
doppler
c_chain_build
frontend_prepare
frontend_background
pqc_background
uvicorn
```

Preuve issue du journal de relance :

```text
step=git_sync STEP begin
step=git_sync STEP end
step=python_venv STEP begin
step=python_venv STEP end
step=python_dependencies STEP begin
step=python_dependencies STEP end
step=oqs_patch STEP begin
step=oqs_patch STEP end
step=doppler STEP begin
step=doppler STEP end
step=c_chain_build STEP begin
step=c_chain_build STEP end
step=frontend_prepare STEP begin
step=frontend_prepare STEP end
step=uvicorn STEP begin
```

Le contrôle automatisé a trouvé 18 marqueurs d’étape ou de lancement.

---

### 3.4 Sorties d’installation conservées intégralement

Fichier exact :

```text
scripts/replit_start.sh
```

#### Avant

```bash
$PIP install --no-user -r requirements.txt \
    --ignore-requires-python \
    -q 2>&1 | grep -v "^Requirement already" | tail -5 || true
```

Les sorties étaient filtrées et tronquées.

#### Après

```bash
$PIP install --no-user -r requirements.txt \
    --ignore-requires-python \
    2>&1
```

Le résultat complet est capturé par la redirection globale du journal de run.

Le fallback litellm est également journalisé explicitement :

```bash
if ! $PIP show litellm-ibm-bob &>/dev/null; then
  $PIP install --no-user "litellm>=1.0.0" 2>&1 \
    || _log "WARN litellm fallback installation failed"
fi
```

---

### 3.5 Tâches arrière-plan suivies

Fichier exact :

```text
scripts/replit_start.sh
```

#### Avant

```bash
( _launch_pqc_background 2>&1 | while IFS= read -r line; do
    echo "$(date -u +%H:%M:%S) $line"
  done ) &
disown 2>/dev/null || true
```

La tâche était détachée et son PID n’était pas conservé dans l’état principal.

#### Après

```bash
(
  _launch_pqc_background
) &
PQC_PID=$!
_log "BACKGROUND launched name=pqc pid=$PQC_PID"
```

La tâche frontend suit le même principe :

```bash
(
  CURRENT_STEP="frontend_background"
  _log "BACKGROUND begin pid=$BASHPID"
  ...
  _log "BACKGROUND end status=0"
) &
FRONTEND_PID=$!
_log "BACKGROUND launched name=frontend pid=$FRONTEND_PID"
```

Résultat observé pendant la relance :

```text
[2026-08-08T11:35:23Z] ... BACKGROUND launched name=pqc pid=46198
[2026-08-08T11:35:23Z] ... BACKGROUND begin pid=46198
PQC: liboqs déjà opérationnel ✅
[2026-08-08T11:35:24Z] ... BACKGROUND end status=0 result=already_operational
```

---

### 3.6 Gestion Uvicorn sans perte du processus

Fichier exact :

```text
scripts/replit_start.sh
```

#### Avant

```bash
exec $PYTHON -m uvicorn src.api.main:app \
  --host 0.0.0.0 \
  --port 5000 \
  --log-level info
```

Le processus Bash était remplacé par Uvicorn, sans journalisation explicite du PID ou du code de sortie dans le script.

#### Après

```bash
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
```

#### Effet

Le script conserve :

- le PID Uvicorn ;
- l’étape active ;
- la fin du processus ;
- son code de sortie ;
- les signaux reçus.

---

### 3.7 Root logger Python centralisé

Fichier exact :

```text
src/artcb/logging_config.py
```

#### Avant

```python
logger = logging.getLogger(module)
...
file_path = log_dir / f"{datetime.now(UTC).strftime('%Y%m%d')}_{module.replace('.', '_')}.json"
file_handler = logging.FileHandler(file_path, encoding="utf-8")
...
logger.addHandler(file_handler)
logger.propagate = False
```

Le fichier était lié à un module précis et les autres loggers n’étaient pas centralisés.

#### Après

```python
file_path = log_dir / f"{datetime.now(UTC).strftime('%Y%m%d')}_artcb_startup.json"
root_logger = logging.getLogger()
root_logger.setLevel(level)
...
root_file_handler = logging.FileHandler(file_path, encoding="utf-8")
root_file_handler.setFormatter(JsonLineFormatter())
root_logger.addHandler(root_file_handler)
```

Les loggers Uvicorn sont routés vers le root logger :

```python
for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    uvicorn_logger = logging.getLogger(logger_name)
    uvicorn_logger.setLevel(level)
    uvicorn_logger.handlers.clear()
    uvicorn_logger.propagate = True
```

Le formatter ajoute :

```python
"pid": os.getpid(),
"startup_id": os.getenv("ARTCB_STARTUP_ID"),
```

Les exceptions sont conservées :

```python
if record.exc_info:
    payload["exception"] = self.formatException(record.exc_info)
```

---

### 3.8 Initialisation du logger avant les imports applicatifs lourds

Fichier exact :

```text
src/api/main.py
```

#### Avant

```python
from src.artcb.logging_config import setup_logging
from src.api.api_keys_routes import router as api_keys_router
...
from src.api.deps import build_app_state
...
setup_logging("artcb.api")
logger = logging.getLogger("artcb.api")
```

Les imports des routeurs et de l’état applicatif précédaient la configuration du logger.

#### Après

```python
from src.artcb.logging_config import setup_logging

# Configure the root logger before importing routers and application state.
# Their module-level initialization can emit warnings/errors during startup.
setup_logging("artcb.api")
logger = logging.getLogger("artcb.api")

from src.api.api_keys_routes import router as api_keys_router
...
from src.api.deps import build_app_state
```

Les warnings et erreurs d’initialisation des modules sont maintenant capturés dans le journal JSONL central.

---

## 4. Résultats de la relance réelle

### 4.1 Journal shell

Fichier produit :

```text
logs/startup_20260808T113518Z_46115.log
```

Statut :

```text
35678 bytes
permissions 600
```

Première ligne :

```text
[2026-08-08T11:35:18Z] [startup_id=20260808T113518Z_46115]
[step=bootstrap] START pid=46115
repl_dir=/home/runner/workspace
log_file=/home/runner/workspace/logs/startup_20260808T113518Z_46115.log
```

Cette preuve confirme que la journalisation commence avant la première étape fonctionnelle.

### 4.2 Journal JSONL centralisé

Fichier produit :

```text
logs/20260808_artcb_startup.json
```

Statut :

```text
13861 bytes
permissions 600
75 lignes JSONL
1 seul startup_id
```

Modules observés :

```text
artcb.api
artcb.chain.ffi
artcb.chain.manager
artcb.crypto.pqc
artcb.governance.manager
artcb.privacy.homomorphic
artcb.security.hardware_identity
artcb.system.hardware
artcb.system.optimizer
artcb.wallet.manager
faiss.loader
oqs.oqs
src.artcb.security.anti_sybil
src.artcb.security.slashing
uvicorn.access
uvicorn.error
```

Le fichier contient donc maintenant les événements provenant de plusieurs sous-systèmes, et non plus uniquement `artcb.api`.

### 4.3 Preuves Uvicorn dans le JSONL

```json
{"module": "uvicorn.error", "message": "Started server process [46210]"}
{"module": "uvicorn.error", "message": "Waiting for application startup."}
{"module": "uvicorn.error", "message": "Application startup complete."}
{"module": "uvicorn.error", "message": "Uvicorn running on http://0.0.0.0:5000 (Press CTRL+C to quit)"}
```

### 4.4 Preuves d’accès HTTP dans le JSONL

Les accès sont désormais persistés :

```json
{"module": "uvicorn.access", "message": "127.0.0.1:50346 - \"GET / HTTP/1.1\" 200"}
{"module": "uvicorn.access", "message": "127.0.0.1:50362 - \"GET /health HTTP/1.1\" 200"}
{"module": "uvicorn.access", "message": "127.0.0.1:50372 - \"GET /api/v1/health HTTP/1.1\" 200"}
{"module": "uvicorn.access", "message": "127.0.0.1:50378 - \"GET /api/v1/chain/verify HTTP/1.1\" 200"}
```

### 4.5 Tests HTTP

| Endpoint | Résultat |
|---|---:|
| `/` | HTTP 200 |
| `/health` | HTTP 200 |
| `/api/v1/health` | HTTP 200 |
| `/api/v1/chain/verify` | HTTP 200 |

Réponse API de santé :

```json
{
  "status": "ok",
  "debug": true,
  "llm_enabled": false,
  "bob_configured": false,
  "chain": {
    "available": true,
    "valid": true,
    "hybrid_signatures": true,
    "pqc_algorithm": "ML-DSA-65"
  }
}
```

---

## 5. Vérifications techniques

### Syntaxe Bash

Commande :

```bash
bash -n scripts/replit_start.sh
```

Résultat :

```text
bash-ok
```

### Syntaxe Python

Commande :

```bash
$HOME/venv/bin/python3 -m py_compile \
  src/artcb/logging_config.py \
  src/api/main.py
```

Résultat :

```text
python-ok
```

### Contrôle des espaces et du diff

Commande :

```bash
git diff --check
```

Résultat : aucune erreur.

### Workflow

Le workflow `Start application` reste en état :

```text
RUNNING
```

---

## 6. Avant / après global

### Avant

```text
Le premier echo précédait tout journal local.
Le script ne possédait pas d’identifiant de run.
Les étapes n’étaient pas corrélées.
Les sorties de pip/CMake/npm étaient tronquées.
Les tâches arrière-plan étaient détachées.
Le root logger n’était pas centralisé.
Uvicorn n’était pas dans le JSON applicatif.
Les erreurs de modules importés tôt pouvaient manquer.
Le fichier JSON contenait principalement artcb.api.
```

### Après

```text
Le fichier startup_<timestamp>_<pid>.log est créé avant le premier echo.
Chaque tentative possède un startup_id unique.
Chaque étape possède un begin/end et un nom.
Les PIDs frontend/PQC/Uvicorn sont enregistrés.
Les erreurs, signaux et codes de sortie sont enregistrés.
Les sorties complètes sont conservées dans le journal de run.
Les modules ARTCB convergent vers le root logger.
Uvicorn error/access est inclus dans le JSONL.
Les exceptions Python peuvent être sérialisées.
Les endpoints vérifiés sont tracés avec leur code HTTP.
```

---

## 7. Limites restantes

La traçabilité du processus de démarrage est maintenant complète dans le workspace, mais deux limites externes subsistent :

1. le healthcheck généré par la plateforme Replit est visible dans les logs de déploiement de la plateforme, pas comme une requête contrôlée par l’application ;
2. les lignes du workflow peuvent être présentées de manière tronquée dans l’interface, même si le fichier local de run conserve la sortie complète.

Ces limites ne masquent plus les logs applicatifs ou shell locaux : les deux fichiers suivants permettent maintenant de reconstituer la tentative :

```text
logs/startup_20260808T113518Z_46115.log
logs/20260808_artcb_startup.json
```

---

## 8. État Git et fichiers produits

Fichiers applicatifs modifiés :

```text
scripts/replit_start.sh
src/api/main.py
src/artcb/logging_config.py
```

Fichier de log généré :

```text
logs/20260808_artcb_startup.json
```

Le fichier shell de run est protégé par les permissions `600` :

```text
logs/startup_20260808T113518Z_46115.log
```

Les rapports antérieurs sont conservés :

```text
rapports/rapport_110_explication_healthcheck_500_2026-08-08.md
rapports/rapport_111_verification_profonde_tracabilite_healthcheck_2026-08-08.md
```

---

## 9. Conclusion

La demande « garantir la traçabilité complète de chaque démarrage » est satisfaite et vérifiée.

La preuve la plus importante est l’ordre réel du journal :

```text
START
→ git_sync begin/end
→ python_venv begin/end
→ python_dependencies begin/end
→ oqs_patch begin/end
→ doppler begin/end
→ c_chain_build begin/end
→ frontend_prepare begin/end
→ pqc background begin/end
→ uvicorn launched
→ Application startup complete
→ accès HTTP 200
```

Le système peut maintenant relier les événements shell, Python, Uvicorn et HTTP à une même tentative grâce à `startup_id`.

**Statut final :** ✅ traçabilité de démarrage opérationnelle, workflow sain, endpoints validés, rapports précédents conservés.
