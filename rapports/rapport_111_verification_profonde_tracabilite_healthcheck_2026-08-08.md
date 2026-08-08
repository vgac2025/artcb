# Rapport 111 — Vérification approfondie de la traçabilité du démarrage et du healthcheck

**Date :** 2026-08-08  
**Incident analysé :** healthcheck `GET /` retournant HTTP 500  
**Rapport précédent conservé :** `rapports/rapport_110_explication_healthcheck_500_2026-08-08.md`  
**Nouvelle demande :** comprendre pourquoi les logs de démarrage manquaient, relancer le service et produire une vérification complète  
**Type d’intervention :** analyse, relance contrôlée et tests HTTP — aucun correctif de code appliqué  
**Avancement :** 100 %

---

## 1. Conclusion immédiate

La remarque de l’utilisateur est fondée : la traçabilité du démarrage n’est pas totale.

Le système possède bien plusieurs sources de logs, mais elles ne jouent pas le même rôle :

1. le script Bash écrit principalement vers la sortie standard du workflow ;
2. le journal du workflow est capturé par l’environnement Replit dans `/tmp/logs/` ;
3. l’application crée un fichier JSON dans `logs/`, mais seulement après l’import des modules et l’initialisation d’une grande partie de l’état applicatif ;
4. les logs Uvicorn et les healthchecks restent dans le journal du workflow et ne sont pas recopiés dans le fichier JSON applicatif ;
5. les tâches en arrière-plan sont lancées avec `disown` et plusieurs erreurs sont volontairement neutralisées par `|| true`.

La conséquence est importante :

> Les logs n’étaient pas réellement absents ; ils étaient fragmentés entre le journal d’exécution du workflow, le journal de déploiement et le fichier JSON applicatif. Le fichier persistant `logs/20260808_artcb_api.json` ne représente donc pas la totalité de la séquence de démarrage.

La relance du workflow montre toutefois que l’application fonctionne actuellement :

```text
Application startup complete.
Uvicorn running on http://0.0.0.0:5000
GET / → 200 OK
GET /health → 200 OK
GET /api/v1/health → 200 OK
GET /api/v1/chain/verify → 200 OK
```

La cause exacte du HTTP 500 de l’incident initial reste non prouvée, car la tentative initiale ne contenait pas la traceback applicative. En revanche, la cause de la traçabilité incomplète est démontrée par le code actuel.

---

## 2. Actions réellement effectuées

Les actions suivantes ont été exécutées dans le Repl :

1. lecture du rapport 110 ;
2. lecture du protocole, des conventions de nommage et des règles de workflow ;
3. inspection du script `scripts/replit_start.sh` ;
4. inspection de `src/api/main.py` ;
5. inspection de `src/artcb/logging_config.py` ;
6. inspection de `src/api/deps.py` ;
7. redémarrage du workflow `Start application` ;
8. lecture complète du nouveau log de workflow ;
9. vérification du processus Uvicorn et du port 5000 ;
10. tests HTTP directs sur `/`, `/health`, `/api/v1/health` et `/api/v1/chain/verify` ;
11. lecture du fichier JSON applicatif ;
12. vérification de l’état Git.

Aucun fichier de code, script de démarrage, workflow, dépendance ou secret n’a été modifié.

Le seul fichier documentaire créé par cette analyse est le présent rapport. Le fichier `rapport_110` n’a pas été écrasé.

---

## 3. Sources et preuves utilisées

### 3.1 Incident initial fourni par l’utilisateur

```text
attached_assets/Pasted-2026-08-08T01-54-25-685Z-healthcheck-failed-error-healt_1786154232632.txt
```

Preuve principale :

```text
2026-08-08T01:54:25.685Z healthcheck failed error=healthcheck / returned status 500
```

Le fichier montre ensuite la compilation C de liboqs entre 0 % et 3 %.

### 3.2 Log de déploiement initial

```text
/tmp/logs/deployment_20260808_015741_211_899a57d7.log
```

Éléments importants :

```text
01:53:48.848 — healthcheck / returned status 500
01:54:00.395 — Démarrage ARTCB API sur :5000
01:54:00.507 — healthcheck / returned status 500
01:54:06.390 — liboqs-python commence une installation automatique
01:54:19.931 — début de la compilation C
```

### 3.3 Nouveau log produit par la relance

```text
/tmp/logs/Start_application_20260808_112339_164_cc42b52f.log
```

Ce log contient la séquence complète observée lors de la relance :

```text
[0/6] Pull GitHub (mise à jour code) ...
[1/6] Venv existant : /home/runner/venv
[2/6] Installation des dépendances Python...
[3/6] Patch oqs.py (fallback RuntimeError)...
[4/6] Doppler ignoré — variables Replit utilisées
[5/6] Compilation libartcb_chain.so...
[6/6] Frontend React (arrière-plan si nécessaire)...
✅ Démarrage ARTCB API sur :5000
PQC: liboqs déjà opérationnel ✅
Application startup complete.
Uvicorn running on http://0.0.0.0:5000
```

### 3.4 Log applicatif persistant

```text
logs/20260808_artcb_api.json
```

Contenu observé :

```json
{"ts": "2026-08-08T11:17:22.952653+00:00", "level": "DEBUG", "module": "artcb.api", "message": "ARTCB API started debug=True"}
{"ts": "2026-08-08T11:23:35.358246+00:00", "level": "DEBUG", "module": "artcb.api", "message": "ARTCB API started debug=True"}
```

Ce fichier ne contient pas :

- les six étapes du script Bash ;
- les tests healthcheck ;
- `Application startup complete` ;
- `Uvicorn running ...` ;
- les requêtes HTTP d’accès ;
- le début ou la fin de l’installation liboqs ;
- les messages de création du venv ;
- les erreurs du proxy de healthcheck.

---

## 4. Résultat de la relance contrôlée

### 4.1 État du workflow

Le workflow relancé est :

```text
Start application
```

Résultat :

```text
status: RUNNING
run_id: W5a-_Tn5S0yOJuoXRYWcQ
```

Le processus observé est :

```text
/home/runner/venv/bin/python3 -m uvicorn src.api.main:app \
  --host 0.0.0.0 \
  --port 5000 \
  --log-level info
```

### 4.2 Séquence de démarrage réussie

Le nouveau log montre :

```text
11:23:32 PQC: liboqs déjà opérationnel ✅
2026-08-08T11:23:35 [DEBUG] artcb.api: ARTCB API started debug=True
INFO:     Started server process [45705]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:5000 (Press CTRL+C to quit)
```

Cette fois, la preuve de disponibilité applicative est présente.

### 4.3 Tests HTTP directs

Les requêtes ont été exécutées contre `127.0.0.1:5000`.

#### `GET /`

Réponse :

```text
HTTP/1.1 200 OK
content-type: text/html; charset=utf-8
content-length: 777
```

Le corps contient le frontend React :

```html
<!doctype html>
<html lang="en">
...
<title>ARTCB — Terminal Console Dashboard</title>
```

#### `GET /health`

Réponse :

```text
HTTP/1.1 200 OK
{"status":"healthy","service":"ARTCB API","version":"0.3.0"}
```

#### `GET /api/v1/health`

Réponse :

```text
HTTP/1.1 200 OK
{
  "status": "ok",
  "debug": true,
  "llm_enabled": false,
  "bob_configured": false,
  "chain": {
    "available": true,
    "valid": true,
    "message": "chain file not found (empty ok)",
    "block_count": 0,
    "hybrid_signatures": true,
    "pqc_algorithm": "ML-DSA-65"
  }
}
```

#### `GET /api/v1/chain/verify`

Réponse :

```text
HTTP/1.1 200 OK
{
  "valid": true,
  "message": "chain file not found (empty ok)",
  "block_count": 0,
  "hybrid_signatures": true,
  "pqc_algorithm": "ML-DSA-65"
}
```

#### Requête locale `/` visible dans le log Uvicorn

Après les tests directs, le workflow a enregistré :

```text
INFO:     127.0.0.1:33186 - "GET / HTTP/1.1" 200 OK
```

Cela confirme que le serveur lui-même reçoit et traite correctement la racine `/` lors de la relance.

---

## 5. Pourquoi les logs de démarrage étaient incomplets

## 5.1 Le logging applicatif est activé trop tard

Fichier exact :

```text
src/api/main.py
```

Lignes 8–34 :

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.artcb.logging_config import setup_logging
...
from src.api.deps import build_app_state
...
```

Ligne 36 :

```python
setup_logging("artcb.api")
```

Ligne 49 :

```python
app.state.artcb = build_app_state()
```

Ligne 130 :

```python
app = create_app()
```

### Conséquence

Les imports des modules situés aux lignes 13–34 se produisent avant l’appel à `setup_logging("artcb.api")`.

De plus, la construction de l’état applicatif démarre seulement après cette configuration, mais elle utilise de nombreux loggers distincts :

```text
artcb.chain.manager
artcb.privacy.homomorphic
artcb.crypto.pqc
artcb.security.*
artcb.p2p.*
```

Ces loggers ne sont pas tous configurés par l’appel `setup_logging("artcb.api")`.

Le fichier `logs/20260808_artcb_api.json` ne peut donc pas être considéré comme le journal complet de l’application.

## 5.2 Le fichier JSON ne capture qu’un logger précis

Fichier exact :

```text
src/artcb/logging_config.py
```

Lignes 17–28 :

```python
def setup_logging(module: str) -> logging.Logger:
    level_name = os.getenv("ARTCB_LOG_LEVEL", "DEBUG" if _debug_enabled() else "INFO")
    level = getattr(logging, level_name.upper(), logging.DEBUG)

    log_dir = Path(os.getenv("ARTCB_LOG_DIR", "./logs"))
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(module)
    if logger.handlers:
        return logger

    logger.setLevel(level)
```

Lignes 34–39 :

```python
stream_handler = logging.StreamHandler()
...
logger.addHandler(stream_handler)

file_path = log_dir / f"{datetime.now(UTC).strftime('%Y%m%d')}_{module.replace('.', '_')}.json"
file_handler = logging.FileHandler(file_path, encoding="utf-8")
```

Lignes 51–53 :

```python
file_handler.setFormatter(JsonLineFormatter())
logger.addHandler(file_handler)
logger.propagate = False
```

### Conséquence

L’appel avec `module="artcb.api"` crée un fichier pour `artcb_api`, puis empêche la propagation de ce logger vers le root logger.

Il ne configure pas automatiquement tous les loggers `artcb.*` et ne récupère pas les sorties :

- du shell ;
- d’Uvicorn ;
- de la supervision Replit ;
- de `pip` ;
- de CMake ;
- des processus enfants ;
- des tâches lancées en arrière-plan.

Le fichier JSON contient donc seulement le message final :

```text
ARTCB API started debug=True
```

Ce comportement explique directement pourquoi la traçabilité persistante paraît « manquer ».

## 5.3 Le script Bash ne crée pas de journal de démarrage local

Fichier exact :

```text
scripts/replit_start.sh
```

Ligne 13 :

```bash
set -e
```

Le script affiche ses étapes avec `echo`, mais il ne redirige pas globalement sa sortie vers un fichier `logs/`.

Lignes 153–159 :

```bash
echo ""
echo "  ✅ Démarrage ARTCB API sur :5000 (Replit webview)..."
exec $PYTHON -m uvicorn src.api.main:app \
  --host 0.0.0.0 \
  --port 5000 \
  --log-level info
```

### Conséquence

Avant `exec uvicorn`, les traces du script existent principalement dans le flux stdout/stderr du workflow. Elles ne sont pas écrites dans le fichier JSON de l’application.

Après `exec`, Uvicorn remplace le processus Bash. Les logs Uvicorn vont eux aussi dans le flux du workflow, pas dans `logs/20260808_artcb_api.json`.

## 5.4 Les tâches arrière-plan ne sont pas rattachées à un journal durable

Fichier exact :

```text
scripts/replit_start.sh
```

Lignes 116–122 :

```bash
(
  cd "$REPL_DIR/frontend"
  npm install -q 2>&1 | tail -2
  npm run build 2>&1 | tail -5
  echo "  ✅ Frontend buildé en arrière-plan — rechargez la page"
) &
disown 2>/dev/null || true
```

Lignes 149–151 :

```bash
export -f _launch_pqc_background 2>/dev/null || true
( _launch_pqc_background 2>&1 | while IFS= read -r line; do echo "$(date -u +%H:%M:%S) $line"; done ) &
disown 2>/dev/null || true
```

### Conséquence

Ces tâches :

- écrivent vers stdout/stderr ;
- tournent en parallèle ;
- sont détachées avec `disown` ;
- ne possèdent pas de fichier de run dédié ;
- ne possèdent pas d’identifiant de tentative corrélé ;
- ne garantissent pas que leur résultat final sera présent dans le même journal que le démarrage.

Cette architecture peut laisser un journal principal avec le début de la tâche, sans son résultat final.

## 5.5 Plusieurs erreurs sont volontairement absorbées

Fichier exact :

```text
scripts/replit_start.sh
```

Lignes 73–77 :

```bash
$PIP install --no-user -r requirements.txt \
    --ignore-requires-python \
    -q 2>&1 | grep -v "^Requirement already" | tail -5 || true
```

Lignes 142–146 :

```bash
$PIP install --no-user "liboqs-python>=0.14.0" -q 2>&1 | tail -2 || true
if $PYTHON -c "import oqs; oqs.get_enabled_sig_mechanisms()" &>/dev/null 2>&1; then
  ...
else
  echo "PQC: compilation échouée — fallback Ed25519/X25519 actif"
fi
```

### Conséquence

Le script peut continuer après une erreur d’installation ou de compilation. C’est utile pour préserver le démarrage de l’API, mais cela réduit la traçabilité si la sortie détaillée n’est pas conservée dans un fichier de run.

`set -e` ne suffit donc pas à garantir une trace complète :

- certaines commandes sont suivies de `|| true` ;
- les pipelines peuvent masquer l’erreur originale ;
- les tâches sont en arrière-plan ;
- les sorties sont tronquées par `tail`.

---

## 6. Ce que la relance a réellement démontré

### 6.1 La route `/` est fonctionnelle dans l’état courant

Le code de `src/api/main.py` contient une branche frontend présent :

```python
if os.path.isdir(_dist):
    ...
    @app.get("/")
    async def serve_spa_root():
        return FileResponse(os.path.join(_dist, "index.html"))
```

Le fichier suivant est présent dans le workspace :

```text
frontend/dist/index.html
```

La requête réelle a retourné :

```text
HTTP/1.1 200 OK
```

### 6.2 La compilation liboqs n’a pas bloqué cette relance

Lors de la relance :

```text
11:23:32 PQC: liboqs déjà opérationnel ✅
```

Il n’y a pas eu de nouvelle compilation C liboqs dans cette tentative.

Cela explique une différence majeure avec l’incident initial :

```text
Incident initial : liboqs absent → installation automatique → compilation à 0–3 %
Relance : liboqs déjà opérationnel → pas de compilation bloquante observée
```

Le système de fichiers et l’environnement Python étaient donc dans un état différent entre les deux séquences.

### 6.3 L’état cryptographique est partiellement dégradé mais non bloquant

Le workflow relancé a signalé :

```text
TenSEAL non installé — mode simulé (TESTS UNIQUEMENT). Production : pip install tenseal
```

Cette alerte provient de :

```text
src/artcb/privacy/homomorphic.py:30–40
```

Le workflow a également signalé :

```text
Chain PQC key generation skipped:
ARTCB_WALLET_PASSPHRASE is not set —
cannot encrypt or decrypt wallet private keys.
```

Cette alerte est émise depuis :

```text
src/artcb/chain/manager.py:143–149
```

Elle n’a pas empêché le démarrage ni les tests HTTP, mais elle doit rester considérée comme un état de configuration incomplet pour les clés privées de wallet.

### 6.4 Les healthchecks actuels sont différents de l’incident initial

Pendant la relance, les requêtes observées sont :

```text
GET /api/v1/health HTTP/1.1" 200 OK
GET /api/v1/chain HTTP/1.1" 200 OK
GET /api/v1/chain/verify HTTP/1.1" 200 OK
GET / HTTP/1.1" 200 OK
```

Aucun HTTP 500 n’a été observé pendant cette relance.

---

## 7. Pourquoi l’incident initial reste partiellement indéterminé

Le log initial indique des 500 avant et après l’annonce de démarrage :

```text
01:53:48.848 — healthcheck / → 500
...
01:54:00.395 — annonce du démarrage API
01:54:00.507 — healthcheck / → 500
```

Mais il ne contient pas :

- `Started server process` ;
- `Waiting for application startup` ;
- `Application startup complete` ;
- `Uvicorn running ...` ;
- `GET / HTTP/1.1` côté Uvicorn ;
- traceback ;
- corps de la réponse 500.

Il est donc impossible de démontrer si :

1. le healthcheck a frappé un proxy avant que l’application ne soit prête ;
2. l’application a commencé mais a échoué pendant `build_app_state()` ;
3. `FileResponse(index.html)` a échoué dans le snapshot de déploiement ;
4. la compilation liboqs a saturé ou retardé l’environnement ;
5. le déploiement utilisait un état de fichier différent du workspace inspecté ;
6. plusieurs de ces événements se sont produits simultanément.

La relance prouve seulement que l’état courant est sain, pas quelle branche exacte a causé l’incident historique.

---

## 8. Avant / après — traçabilité

Conformément au protocole, aucun changement applicatif n’a été effectué. Le tableau ci-dessous compare l’état observé et l’état vérifié après relance, sans présenter la relance comme un correctif.

### 8.1 Journal du démarrage

**Avant — état observé**

```text
scripts/replit_start.sh
```

Les étapes étaient visibles dans le journal du workflow, mais pas dans un fichier persistent local dédié au run.

**Après — vérification**

Le journal du workflow de la relance contient toutes les étapes :

```text
/tmp/logs/Start_application_20260808_112339_164_cc42b52f.log
```

Cela améliore la visibilité de cette tentative, mais ne change pas le code de journalisation.

### 8.2 Journal applicatif JSON

**Avant — contenu réel**

```text
logs/20260808_artcb_api.json
```

Seulement deux entrées `ARTCB API started debug=True`.

**Après — vérification**

Le fichier contient encore uniquement les messages du logger `artcb.api`. Les logs Bash, Uvicorn, healthchecks et sous-modules n’y sont pas ajoutés.

**Modification appliquée**

```text
Aucune.
```

### 8.3 Healthcheck `/`

**Avant — incident**

```text
HTTP 500
```

**Après — relance**

```text
HTTP 200 OK
```

### 8.4 PQC

**Avant — incident**

```text
liboqs absent
installation automatique
compilation C démarrée
progression visible jusqu’à 3 %
```

**Après — relance**

```text
PQC: liboqs déjà opérationnel ✅
```

---

## 9. État des fichiers après vérification

L’état Git observé après la relance indique :

```text
?? logs/20260808_artcb_api.json
```

Le fichier de log applicatif est donc généré localement mais non suivi par Git dans l’état observé.

Le rapport précédent reste présent :

```text
rapports/rapport_110_explication_healthcheck_500_2026-08-08.md
```

Le présent rapport est ajouté séparément :

```text
rapports/rapport_111_verification_profonde_tracabilite_healthcheck_2026-08-08.md
```

Aucun ancien rapport n’a été écrasé.

---

## 10. Correctifs recommandés, non appliqués

L’utilisateur a demandé une vérification et un rapport, sans demander explicitement de modifier le système. Les recommandations suivantes sont donc documentées mais non exécutées.

### 10.1 Créer un journal de run dès la première ligne Bash

Le script devrait créer un identifiant de tentative et rediriger stdout/stderr vers un fichier dédié avant toute opération :

```text
logs/startup_<timestamp>_<run_id>.log
```

Ce journal devrait recevoir :

- le shell ;
- les commandes ;
- les erreurs ;
- les étapes ;
- les PID ;
- les codes de retour ;
- la fin des tâches arrière-plan.

### 10.2 Ajouter un `trap` de fin et d’erreur

Le script devrait enregistrer au minimum :

- la commande en échec ;
- le code de sortie ;
- l’heure UTC ;
- l’étape courante ;
- le PID concerné ;
- le dernier message produit.

### 10.3 Configurer le root logger avant les imports applicatifs lourds

Le logger actuel `artcb.api` est insuffisant pour une traçabilité globale. Il faudrait un logger racine ou une configuration centralisée qui capture :

- `artcb.*` ;
- Uvicorn ;
- les sous-modules ;
- les erreurs de startup ;
- les erreurs de requêtes.

### 10.4 Ne pas tronquer les erreurs des tâches d’installation

Les usages suivants masquent des informations :

```bash
| tail -2
| tail -5
|| true
```

Ils peuvent être conservés pour la tolérance au démarrage uniquement si la sortie complète est enregistrée dans un fichier durable avant réduction de l’affichage.

### 10.5 Corréler les healthchecks externes avec les accès Uvicorn

Chaque tentative devrait permettre de répondre à ces questions :

```text
Le healthcheck a-t-il atteint Uvicorn ?
Quel était le code HTTP ?
Quel était le corps de réponse ?
Le processus était-il déjà en écoute ?
Application startup complete avait-il déjà été émis ?
```

---

## 11. Verdict final

### Sur la question « pourquoi les logs manquaient-ils ? »

Ils manquaient du fichier local principal parce que le projet n’a pas un journal global de démarrage. Les informations étaient distribuées entre :

- stdout/stderr du script ;
- log workflow Replit ;
- log de déploiement ;
- fichier JSON du logger `artcb.api`.

Le fichier JSON applicatif est créé trop tard et ne couvre pas toute la chaîne.

### Sur la question « que se passe-t-il vraiment ? »

La séquence actuelle est saine :

```text
PQC disponible
→ état applicatif construit
→ Application startup complete
→ Uvicorn écoute sur 5000
→ / répond 200
→ /health répond 200
→ /api/v1/health répond 200
```

La séquence historique était différente :

```text
healthchecks 500 très précoces
→ installation automatique liboqs
→ compilation C longue
→ absence de preuve Uvicorn exploitable
→ absence de traceback persistée
```

### Conclusion de fiabilité

Le healthcheck 500 initial est un incident réel, mais sa cause racine ne peut pas être affirmée sans les logs de démarrage complets de cette tentative. La lacune de traçabilité, elle, est confirmée par le code et doit être traitée comme un problème distinct de fiabilité opérationnelle.

**État final après relance :** service opérationnel, aucune erreur HTTP 500 observée, traçabilité persistante complète non garantie par l’architecture actuelle.
