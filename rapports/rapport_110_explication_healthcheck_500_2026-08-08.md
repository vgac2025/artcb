# Rapport 110 — Explication de l’échec du healthcheck `GET /` en HTTP 500

**Date d’analyse :** 2026-08-08  
**Horodatage de l’incident principal :** 2026-08-08T01:54:25.685Z  
**Agent :** Replit Agent  
**Type :** Rapport d’analyse documentaire et log — aucune correction appliquée  
**Source fournie par l’utilisateur :** `attached_assets/Pasted-2026-08-08T01-54-25-685Z-healthcheck-failed-error-healt_1786154232632.txt`  
**Log de déploiement corrélé :** `/tmp/logs/deployment_20260808_015741_211_899a57d7.log`  
**Rapports de référence :** `rapports/rapport_108_audit_deploiement_port_timeout_2026-08-06.md`, `rapports/rapport_109b_tests_deploiement_post_merge_2026-08-06.md`  
**Avancement de l’analyse :** 100 %  

---

## 1. Résumé exécutif

Le déploiement signale à répétition :

```text
healthcheck failed error=healthcheck / returned status 500
```

Le problème apparaît avant que le serveur Uvicorn soit annoncé comme démarré, puis continue après l’annonce de démarrage :

```text
01:53:48.848 — healthcheck / → 500
01:54:00.395 — Démarrage ARTCB API sur :5000
01:54:00.507 — healthcheck / → 500
01:54:06.390 — démarrage de l’installation automatique de liboqs
01:54:19.931 — début de la compilation C de liboqs
```

La compilation C visible dans le log n’est pas, à elle seule, la cause prouvée du HTTP 500. Elle est lancée en arrière-plan par `liboqs-python` après le démarrage annoncé de l’API. Le log fourni ne contient ni traceback Python, ni ligne Uvicorn indiquant que la requête `GET /` a effectivement atteint la route FastAPI et qu’une exception y a été levée.

La conclusion factuelle est donc la suivante :

> Le healthcheck Replit reçoit HTTP 500 pendant une séquence où le port et/ou l’application ne sont pas encore prêts, puis continue de recevoir 500 après le lancement annoncé d’Uvicorn. Le code actuel définit pourtant une route `/` qui ne retourne explicitement que `200` dans ses deux branches. Il existe donc une divergence entre le comportement observé au déploiement et les branches de routage visibles dans `src/api/main.py`.

La cause exacte reste **non démontrée** avec les éléments disponibles. La priorité de diagnostic est d’obtenir la traceback du processus Uvicorn et de vérifier une requête réelle vers `/` après l’ouverture du port.

---

## 2. Périmètre et règles appliquées

Cette analyse respecte les règles documentaires du projet :

- lecture du `PROTOCOLE_ARTCB` ;
- utilisation des noms réels définis dans `STANDARD_NAMES_ARTCB` ;
- rapport créé dans `rapports/` ;
- ancien rapport non écrasé ;
- mode DEBUG conservé ;
- distinction stricte entre faits prouvés et hypothèses ;
- présentation avant/après avec noms de fichiers et lignes exactes ;
- aucune modification du code, du script, du workflow, des dépendances ou des secrets.

Le fichier joint a été lu sans être modifié.

---

## 3. Preuve brute de l’incident

### 3.1 Extraits exacts du fichier fourni

Fichier source exact :

```text
attached_assets/Pasted-2026-08-08T01-54-25-685Z-healthcheck-failed-error-healt_1786154232632.txt
```

Extraits :

```text
Ligne 001 : 2026-08-08T01:54:25.685Z healthcheck failed error=healthcheck / returned status 500
Ligne 002 : 2026-08-08T01:54:26.005Z [  0%] Building C object src/common/CMakeFiles/common.dir/sha3/sha3x4.c.o
Ligne 003 : 2026-08-08T01:54:26.124Z healthcheck failed error=healthcheck / returned status 500
Ligne 004 : 2026-08-08T01:54:26.343Z [  0%] Building C object src/sig_stfl/lms/CMakeFiles/lms.dir/external/hss_sign_inc.c.o
Ligne 010 : 2026-08-08T01:54:27.178Z healthcheck failed error=healthcheck / returned status 500
Ligne 011 : 2026-08-08T01:54:28.778Z [  1%] Building C object src/sig_stfl/lms/CMakeFiles/lms.dir/external/lm_ots_sign.c.o
Ligne 100 : 2026-08-08T01:54:50.709Z [  3%] Built target bike_l1
```

Ces lignes prouvent la simultanéité entre les échecs du healthcheck et la compilation liboqs. Elles ne prouvent pas que la compilation a généré le HTTP 500.

### 3.2 Chronologie complète du log de déploiement corrélé

Fichier source exact :

```text
/tmp/logs/deployment_20260808_015741_211_899a57d7.log
```

| Heure UTC | Ligne | Événement |
|---|---:|---|
| 01:53:48.596 | 5 | Création du venv Python |
| 01:53:48.848 à 01:53:58.626 | 6–20 | Plusieurs healthchecks `/` en 500 pendant les étapes 1 et 2 |
| 01:54:00.336 | 21 | Patch `oqs.py` |
| 01:54:00.370 | 23–27 | Étapes 4–6 ; `frontend/dist` déclaré à jour |
| 01:54:00.395 | 28 | Annonce du démarrage de l’API sur le port 5000 |
| 01:54:00.507 à 01:54:06.055 | 29–35 | Healthchecks `/` toujours en 500 |
| 01:54:04.041 | 33 | TenSEAL absent, mode simulé signalé |
| 01:54:06.390 | 36–39 | `liboqs-python` commence une installation automatique |
| 01:54:11.599 | 51 | Clonage de liboqs |
| 01:54:13.530 à 01:54:19.663 | 58–79 | Configuration CMake de liboqs réussie |
| 01:54:19.931 | 80 | Début de la compilation C |
| 01:54:25.685 | 105 | Échec de healthcheck fourni par l’utilisateur |
| 01:54:50.709 | 120 | Compilation seulement à 3 %, cible `bike_l1` construite |

---

## 4. Analyse de la chaîne de démarrage

### 4.1 Script de démarrage

Fichier source exact :

```text
scripts/replit_start.sh
```

Lignes 106–125 :

```bash
# ── 6. Build frontend EN ARRIÈRE-PLAN si dist absent/obsolète ────
...
if [ ! -f "$FRONTEND_DIST" ] || [ -n "$(find "$FRONTEND_SRC" -newer "$FRONTEND_DIST" 2>/dev/null | head -1)" ]; then
  ...
  ( ... npm install ... npm run build ... ) &
else
  echo "  dist/ à jour ✅"
fi
```

Dans le log corrélé, la branche observée est :

```text
[2026-08-08T01:54:00.371Z INFO] [6/6] Frontend React (arrière-plan si nécessaire)...
[2026-08-08T01:54:00.394Z INFO]   dist/ à jour ✅
```

Le build frontend n’est donc pas bloquant dans cette exécution et n’est pas l’explication directe prouvée du HTTP 500.

Lignes 127–151 :

```bash
# ── PQC POST-START : liboqs installé EN ARRIÈRE-PLAN ─────────────
...
_launch_pqc_background() {
  if $PYTHON -c "import oqs; oqs.get_enabled_sig_mechanisms()" &>/dev/null 2>&1; then
    ...
  fi
  ...
  $PIP install --no-user "liboqs-python>=0.14.0" -q 2>&1 | tail -2 || true
  ...
}
...
( _launch_pqc_background 2>&1 | while IFS= read -r line; do echo "$(date -u +%H:%M:%S) $line"; done ) &
```

Lignes 153–159 :

```bash
echo "  ✅ Démarrage ARTCB API sur :5000 (Replit webview)..."
exec $PYTHON -m uvicorn src.api.main:app \
  --host 0.0.0.0 \
  --port 5000 \
  --log-level info
```

**Fait établi :** l’installation automatique de liboqs est lancée en arrière-plan avant l’exécution finale d’Uvicorn, mais sa compilation se déroule parallèlement aux healthchecks.

**Limite :** le script n’affiche pas la traceback Python de l’application dans le log de déploiement fourni. Il est donc impossible de confirmer si l’application Uvicorn a démarré correctement, a démarré avec une exception lors d’une requête, ou si le proxy a répondu 500 avant d’atteindre le processus.

---

## 5. Analyse de la route `GET /`

### 5.1 Construction de l’application

Fichier source exact :

```text
src/api/main.py
```

Lignes 40–49 :

```python
def create_app() -> FastAPI:
    app = FastAPI(title="ARTCB API", version="0.3.0")
    ...
    app.state.artcb = build_app_state()
```

Ligne 49 est importante : l’état applicatif est construit avant l’enregistrement de la route `/health` et avant l’enregistrement de la route racine.

Lignes 73–80 :

```python
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ARTCB API",
        "version": "0.3.0"
    }
```

Cette route existe, mais le healthcheck observé cible `/`, pas `/health`.

### 5.2 Branche frontend présent

Fichier source exact :

```text
src/api/main.py
```

Lignes 82–98 :

```python
_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
_dist = os.path.normpath(_dist)
if os.path.isdir(_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(_dist, "assets")), name="assets")

    @app.get("/")
    async def serve_spa_root():
        return FileResponse(os.path.join(_dist, "index.html"))
```

Dans l’environnement inspecté, le fichier suivant est présent :

```text
frontend/dist/index.html
```

Le log de déploiement indique aussi :

```text
[2026-08-08T01:54:00.394Z INFO] dist/ à jour ✅
```

Dans cette branche, la route `/` tente donc de servir `frontend/dist/index.html`. Si cette route est réellement atteinte et que le fichier est lisible dans l’environnement de déploiement, son comportement nominal est HTTP 200.

### 5.3 Branche frontend absent

Fichier source exact :

```text
src/api/main.py
```

Lignes 100–115 :

```python
else:
    # FIX DÉPLOIEMENT : frontend pas encore buildé (dist/ absent).
    # Retourner 200 pour que le healthcheck Replit passe pendant le build en arrière-plan.
    ...
    @app.get("/")
    async def serve_spa_loading():
        return JSONResponse(
            status_code=200,
            content={
                "status": "starting",
                "service": "ARTCB API",
                "version": "0.3.0",
                "note": "Frontend build in progress — API fully operational at /api/v1/"
            }
        )
```

Même sans frontend, cette seconde branche retourne explicitement HTTP 200.

### 5.4 Déduction contrôlée

Dans le code actuellement lu, les deux branches explicites de `GET /` sont :

| État | Fichier et lignes | Réponse nominale |
|---|---|---|
| `frontend/dist` présent | `src/api/main.py:85–90` | `FileResponse(index.html)` |
| `frontend/dist` absent | `src/api/main.py:100–115` | `JSONResponse(status_code=200)` |

Il n’existe pas, dans ces deux branches, de `status_code=500`.

Le HTTP 500 observé est donc compatible avec l’un des scénarios suivants, mais le log ne permet pas de choisir entre eux :

1. le healthcheck a été envoyé avant que le port 5000 et Uvicorn soient prêts ; le 500 vient alors de la couche de supervision/proxy ;
2. l’import ou `build_app_state()` a produit une erreur avant que la route `/` soit exploitable ;
3. Uvicorn a démarré, mais `FileResponse` a échoué dans l’environnement de déploiement ;
4. l’environnement de déploiement ne correspondait pas exactement au code inspecté dans le workspace ;
5. une dépendance initialisée pendant le démarrage a rendu le processus non prêt ou a provoqué une exception, sans traceback capturée dans le log fourni.

La compilation liboqs est un facteur de concurrence et de durée, mais aucune ligne ne prouve qu’elle est la cause de l’exception HTTP.

---

## 6. Avant / après — état réel, sans modification

Conformément au protocole, le présent rapport distingue l’état observé de l’état attendu. Aucun « après » applicatif n’a été appliqué.

### 6.1 Healthcheck

**Avant — observé dans le déploiement**

Fichiers de log :

- `attached_assets/Pasted-2026-08-08T01-54-25-685Z-healthcheck-failed-error-healt_1786154232632.txt:1`
- `/tmp/logs/deployment_20260808_015741_211_899a57d7.log:6–20, 29–35, 105–120`

```text
healthcheck failed error=healthcheck / returned status 500
```

**Après — modification**

```text
Aucune modification appliquée.
```

**État attendu d’après le code lu**

- `src/api/main.py:88–90` : servir `frontend/dist/index.html` ;
- ou `src/api/main.py:105–115` : retourner explicitement HTTP 200 si `dist/` est absent.

### 6.2 Démarrage de l’API

**Avant — observé**

Fichier :

```text
/tmp/logs/deployment_20260808_015741_211_899a57d7.log:28
```

```text
✅ Démarrage ARTCB API sur :5000 (Replit webview)...
```

**Après — modification**

```text
Aucune modification appliquée à scripts/replit_start.sh.
```

**État attendu**

Le démarrage Uvicorn doit être suivi d’une ligne de log Uvicorn confirmant l’application prête et d’une requête vérifiable vers `/`. Ces preuves ne figurent pas dans le fichier joint ni dans l’extrait de déploiement fourni.

### 6.3 Compilation liboqs

**Avant — observé**

Fichier :

```text
/tmp/logs/deployment_20260808_015741_211_899a57d7.log:36–120
```

```text
liboqs not found, installing it in /home/runner/_oqs
[  0%] Building C object ...
[  3%] Built target bike_l1
```

**Après — modification**

```text
Aucune modification appliquée à scripts/replit_start.sh,
à la dépendance liboqs ou à la configuration CMake.
```

**Conclusion**

La compilation a progressé, mais le fichier analysé s’arrête à 3 %. Son succès final ou son échec final n’est pas établi par la pièce jointe.

---

## 7. Causes écartées ou non prouvées

### 7.1 Cause non prouvée : « la compilation C a retourné HTTP 500 »

Les lignes CMake montrent une compilation en cours, pas une erreur de compilation :

```text
[  0%] Building C object ...
[  1%] Built target sha3_avx512vl_low
[  3%] Built target bike_l1
```

Les erreurs affichées sur les lignes voisines sont des messages de supervision :

```text
healthcheck failed error=healthcheck / returned status 500
```

Aucune sortie `error:` de compilateur, `CMake Error`, `make: ***` ou traceback Python ne relie directement les deux événements.

### 7.2 Cause non retenue comme cause directe : build frontend bloquant

Le rapport 108 avait identifié ce risque dans une version antérieure. Dans l’exécution étudiée, le log indique :

```text
[6/6] Frontend React (arrière-plan si nécessaire)...
dist/ à jour ✅
```

Le build frontend n’est donc pas lancé dans cette séquence.

### 7.3 Cause possible : initialisation applicative avant routage

`src/api/main.py:49` appelle `build_app_state()` avant la déclaration de `/health` et de `/`. Si cette initialisation lève une exception ou bloque, aucune route ne peut être considérée comme prête.

Cette cause est techniquement plausible, mais elle n’est pas prouvée : aucune traceback ni erreur de `build_app_state()` n’est présente dans le log fourni.

### 7.4 Cause possible : healthcheck trop précoce

Le premier 500 apparaît dès `01:53:48.848`, alors que le script est encore à l’étape de création du venv (`deployment log:5–13`). À ce moment, le script n’a pas encore annoncé le démarrage d’Uvicorn.

Cela prouve qu’au moins une partie des réponses 500 précède la disponibilité nominale de l’API. Cela ne suffit cependant pas à expliquer les 500 qui continuent après `01:54:00.395`.

---

## 8. Informations manquantes pour prouver la cause racine

Les éléments suivants ne sont pas présents dans le fichier joint :

1. la sortie Uvicorn complète au moment du lancement ;
2. la traceback d’une éventuelle exception Python ;
3. la ligne d’accès Uvicorn correspondant à `GET /` ;
4. le corps de la réponse HTTP 500 ;
5. le résultat d’un appel direct à `/`, `/health` et `/api/v1/health` après l’ouverture du port ;
6. le statut final de l’installation `liboqs-python` ;
7. la confirmation que le snapshot de déploiement contenait exactement le même `src/api/main.py` et le même `frontend/dist/index.html`.

Sans ces éléments, déclarer une cause unique serait contraire à la règle du protocole qui impose de ne pas présenter une hypothèse comme un fait.

---

## 9. Plan de vérification recommandé — aucune action exécutée

Les actions ci-dessous sont des recommandations de diagnostic uniquement. Elles n’ont pas été exécutées et n’ont modifié aucun fichier.

### 9.1 Vérifier si le 500 vient de l’application

Après ouverture effective du port 5000, collecter séparément :

```bash
curl -i http://127.0.0.1:5000/
curl -i http://127.0.0.1:5000/health
curl -i http://127.0.0.1:5000/api/v1/health
```

Puis comparer les réponses avec les lignes d’accès Uvicorn.

### 9.2 Rechercher la traceback complète

La prochaine exécution doit conserver la sortie standard et la sortie d’erreur du processus Uvicorn, notamment toute erreur sur :

- `build_app_state()` ;
- import d’un module ;
- initialisation d’un wallet ;
- ouverture d’un fichier de chaîne ;
- `FileResponse` vers `frontend/dist/index.html`.

### 9.3 Distinguer les deux phases de l’incident

Le diagnostic doit séparer :

1. les 500 reçus avant `01:54:00.395`, avant l’annonce de démarrage ;
2. les 500 reçus après `01:54:00.395`, lorsque le script annonce Uvicorn lancé.

Ces deux groupes peuvent avoir des causes différentes.

### 9.4 Ne pas conclure à une panne cryptographique sur le seul pourcentage CMake

Le pourcentage de compilation liboqs indique une tâche longue en arrière-plan. Il ne constitue pas une preuve d’erreur HTTP. Il faut attendre le résultat final de cette tâche et comparer son statut avec les logs applicatifs.

---

## 10. État final constaté

| Élément | Statut | Preuve |
|---|---|---|
| Fichier de healthcheck fourni | ✅ Lu | fichier joint, lignes 1–100 |
| Log de déploiement corrélé | ✅ Lu | `/tmp/logs/deployment_20260808_015741_211_899a57d7.log` |
| Healthcheck `GET /` | ❌ Échec observé, HTTP 500 | lignes de log citées |
| Démarrage annoncé sur port 5000 | ✅ Annoncé | log de déploiement, ligne 28 |
| API réellement confirmée prête après cette annonce | ⚠️ Non démontré dans la pièce jointe | absence de preuve Uvicorn suffisante |
| Route `/` avec réponse explicite 200 sans frontend | ✅ Présente dans le code | `src/api/main.py:100–115` |
| Frontend `frontend/dist/index.html` dans le workspace | ✅ Présent | vérification de présence |
| Compilation liboqs | 🔄 Incomplète dans le log fourni | progression jusqu’à 3 % |
| Traceback de la cause HTTP 500 | ❌ Absente | constat documentaire |
| Modification du code | ❌ Aucune | analyse uniquement |
| Modification du workflow ou des secrets | ❌ Aucune | analyse uniquement |

---

## 11. Conclusion

Le problème décrit est un échec du healthcheck Replit sur la racine `/`, répété pendant le démarrage et encore observé après l’annonce du lancement de l’API.

Le code actuel de `src/api/main.py` prévoit une réponse nominale non-500 pour `/` lorsque `frontend/dist` est présent ou absent. Le log de déploiement indique en outre que `dist/` était considéré comme à jour. La compilation liboqs est exécutée en parallèle et ralentit fortement la phase de démarrage, mais aucune erreur de compilation ni traceback ne permet de la déclarer responsable du HTTP 500.

La cause la plus rigoureuse à retenir à ce stade est :

> **Divergence non résolue entre le healthcheck externe et la disponibilité réelle de l’application, possiblement aggravée par l’initialisation applicative et l’installation automatique de liboqs.**

Ce rapport ne déclare pas de correctif appliqué, car l’utilisateur a explicitement demandé une explication sans rien modifier. La prochaine preuve indispensable est la traceback Uvicorn et la réponse directe de `/` après ouverture effective du port.
