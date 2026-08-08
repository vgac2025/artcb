# Rapport complet — installation, démarrage et déploiement d’ARTCB

**Date de vérification :** 8 août 2026  
**Dépôt vérifié :** `https://github.com/vgactech/artcb.git`  
**Branche :** `main`  
**Commit vérifié :** `e5a3760`  
**Environnement vérifié :** Replit, Linux/NixOS, Python 3.11.14, Node.js 20.20.0

## 1. Résumé exécutif

Le dépôt était déjà présent directement à la racine du projet Replit. Il n’était donc
pas nécessaire de le cloner une seconde fois ni de supprimer la racine.

La première tentative de démarrage a échoué parce que `liboqs-python` déclenchait
automatiquement une compilation très lourde de `liboqs` pendant l’import Python.
L’API n’ouvrait alors pas le port 5000 dans le délai du healthcheck.

Le démarrage a été corrigé et vérifié :

- workflow `Start application` actif ;
- port 5000 ouvert ;
- `GET /` → HTTP 200 ;
- `GET /health` → HTTP 200 ;
- `GET /setup/status` → HTTP 200 ;
- frontend React et assets → HTTP 200 ;
- `GET /api/health` → HTTP 503 explicite tant que le nœud est en mode bootstrap ;
- `Application startup complete` présent dans les logs Uvicorn.

Le projet n’est **pas encore publié** : le statut de publication Replit vérifié est
`isDeployed=false`. La publication doit donc être lancée manuellement après
l’initialisation du nœud et la validation de la configuration de production.

## 2. Architecture identifiée

Le dépôt contient :

- un backend Python FastAPI/Uvicorn dans `src/` ;
- un frontend React/Vite dans `frontend/` ;
- une bibliothèque native C dans `src/c/` ;
- une couche de cryptographie Ed25519 et optionnellement ML-DSA-65 / ML-KEM-768 ;
- des données persistantes dans `data/` ;
- des journaux dans `logs/` ;
- un script de démarrage Replit dans `scripts/replit_start.sh` ;
- la configuration Replit dans `.replit` et `replit.nix`.

Le démarrage Replit utilise :

```text
bash scripts/replit_start.sh
```

Le script lance l’API sur le port 5000 attendu par l’aperçu Replit. Le frontend
est servi depuis `frontend/dist/` par FastAPI lorsqu’il est construit.

## 3. Attention : dépôt réellement utilisé

Le dépôt réellement vérifié est :

```text
https://github.com/vgactech/artcb.git
```

Certaines anciennes instructions du dépôt et de l’historique mentionnent encore :

```text
https://github.com/vgac2025/artcb.git
```

Pour cette installation, il faut utiliser `vgactech/artcb.git`, qui est le remote
Git confirmé dans le projet :

```bash
git remote -v
```

## 4. Pourquoi le dépôt s’était retrouvé dans un sous-dossier

Cette commande crée un sous-dossier `artcb/` :

```bash
git clone https://github.com/vgactech/artcb.git
```

Pour cloner directement dans le dossier courant, le point final est obligatoire :

```bash
git clone https://github.com/vgactech/artcb.git .
```

Le `.` signifie « utiliser le dossier courant comme destination ».

## 5. Commande destructive à ne pas utiliser sans sauvegarde

L’ancienne instruction proposait :

```bash
cd ~/workspace && find . -mindepth 1 -maxdepth 1 -exec rm -rf {} + && git clone https://github.com/vgactech/artcb.git .
```

Cette commande supprime irréversiblement tout le contenu du dossier courant :

- fichiers Replit ;
- configuration locale ;
- dépendances ;
- fichiers non suivis par Git ;
- données locales ;
- fichiers `.env` ;
- éventuels secrets stockés par erreur dans le dossier.

La tentative précédente avec une variante `rm -rf` a rencontré :

```text
rm: cannot remove 'node_modules': Directory not empty
```

La solution correcte n’est pas de répéter aveuglément une suppression destructive.
Il faut d’abord sauvegarder ce qui est important, vérifier `pwd`, puis choisir entre
un clone dans un sous-dossier ou un remplacement complet volontaire.

Pour ce projet, le dépôt était déjà directement à :

```text
/home/runner/workspace
```

Il fallait donc conserver cette installation et la réparer, ce qui a été fait.

## 6. Procédure manuelle d’installation sur Replit

### 6.1 Vérifier le dossier et le dépôt

```bash
pwd
ls -la
git remote -v
git status --short --branch
git log -1 --oneline --decorate
```

Résultat attendu :

```text
/home/runner/workspace
origin https://github.com/vgactech/artcb.git
```

Si le projet n’est pas encore présent et que le dossier courant est vide ou
explicitement sauvegardé :

```bash
git clone https://github.com/vgactech/artcb.git .
```

### 6.2 Vérifier les outils système

```bash
python3 --version
node --version
npm --version
cmake --version
cc --version
git --version
```

Les versions observées ici étaient :

```text
Python 3.11.14
Node.js 20.20.0
npm 10.8.2
cmake 3.31.6
git 2.49.0
```

Le fichier `replit.nix` demande les outils système suivants :

- Python ;
- CMake ;
- Ninja ;
- GCC ;
- OpenSSL ;
- curl ;
- Git.

### 6.3 Créer l’environnement Python isolé

NixOS peut bloquer une installation globale avec l’erreur PEP 668. Il faut utiliser
un environnement virtuel :

```bash
python3 -m venv "$HOME/venv"
source "$HOME/venv/bin/activate"
python --version
```

Le script Replit utilise automatiquement :

```text
/home/runner/venv
```

### 6.4 Installer les dépendances Python

Commande exacte :

```bash
source "$HOME/venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install --no-user -r requirements.txt --ignore-requires-python
```

Le script de démarrage exécute la variante suivante avec le chemin absolu du venv :

```bash
/home/runner/venv/bin/pip install --no-user -r requirements.txt --ignore-requires-python
```

### 6.5 Dépendances Python directes du projet

Le fichier `requirements.txt` installe les dépendances directes suivantes.
Les dépendances transitives sont résolues automatiquement par `pip`.

#### API et réseau

```text
pydantic
python-dotenv
fastapi
uvicorn[standard]
httpx
httpx2
aiofiles
```

#### Cryptographie et blockchain

```text
pynacl
cryptography
liboqs-python
```

`liboqs-python` est particulier : le paquet Python peut tenter de télécharger et
compiler la bibliothèque native `liboqs` au premier import.

#### IA et LLM

```text
litellm
```

Le paquet privé `litellm-ibm-bob` n’est pas utilisé, car il n’est pas disponible
sur l’index PyPI public Replit.

#### Documents et fichiers

```text
pypdf
python-docx
openpyxl
xlrd
pyyaml
beautifulsoup4
ebooklib
striprtf
Pillow
pytesseract
```

#### Recherche vectorielle et système

```text
faiss-cpu
numpy<2.0
psutil
```

#### MCP, Kaggle et connecteurs

```text
mcp
kaggle
psycopg2-binary
pymysql
```

#### Tests et qualité

```text
pytest
pytest-cov
pytest-asyncio
ruff
```

### 6.6 Installer et construire le frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

Le `package-lock.json` existe dans le dépôt. Pour une installation strictement
reproductible sur une machine propre, `npm ci` peut être utilisé à la place de
`npm install` si le lockfile est conforme à la version npm utilisée :

```bash
cd frontend
npm ci
npm run build
cd ..
```

Dépendances frontend directes :

```text
axios
cytoscape
react
react-dom
react-router-dom
@types/cytoscape
@types/react
@types/react-dom
@vitejs/plugin-react
typescript
vite
```

Le build vérifié a réussi avec :

```text
tsc -b
vite build
114 modules transformed
```

## 7. Configuration `.env`

Copier l’exemple :

```bash
cp .env.example .env
```

Ne jamais committer `.env` et ne jamais afficher ses valeurs :

```bash
grep -vE '(^|_)(KEY|TOKEN|SECRET|PASSWORD)=' .env
```

Variables importantes pour un premier démarrage :

```dotenv
ARTCB_DEBUG=true
ARTCB_LOG_LEVEL=DEBUG
ARTCB_LOG_DIR=./logs
ARTCB_REPORTS_DIR=./rapports
ARTCB_DATA_DIR=./data
ARTCB_ENCODE_MODE=rule-based
ARTCB_LLM_ENABLED=false
ARTCB_NETWORK=local
ARTCB_ANTI_SYBIL_AI_BYPASS=false
ARTCB_ANTI_SYBIL_STUDY_MODE=false
```

Pour un déploiement, utiliser `ARTCB_DEBUG=false` et ne pas activer les bypass
d’étude.

### Sécurité constatée et corrigée

L’ancien `.env.example` contenait une valeur ressemblant à un token LoopQA réel.
Un fichier d’exemple ne doit contenir aucun secret. La valeur a été remplacée par :

```dotenv
LOOPQA_API_TOKEN=REMPLACER_PAR_VOTRE_TOKEN_LOOPQA
```

Si cette ancienne valeur a déjà été utilisée ailleurs, il faut la révoquer et en
générer une nouvelle auprès du service concerné.

## 8. Premier démarrage : mode bootstrap

Sur une installation neuve, l’absence de `ARTCB_NODE_WALLET_ADDRESS` et de
`data/.node_config` place le nœud en mode bootstrap.

Démarrer Replit avec :

```bash
bash scripts/replit_start.sh
```

Le script fait automatiquement :

1. crée ou réutilise `$HOME/venv` ;
2. installe les dépendances Python ;
3. applique le correctif de compatibilité `oqs.py` si nécessaire ;
4. détecte l’URL Replit ;
5. trouve un port libre, normalement 5000 ;
6. vérifie ou compile `src/c/libartcb_chain.so` ;
7. construit le frontend si `frontend/dist` est absent ou obsolète ;
8. démarre Uvicorn ;
9. tente séparément l’installation de la couche PQC.

Le workflow Replit configuré utilise déjà :

```text
Start application → bash scripts/replit_start.sh
```

## 9. Initialiser le nœud une seule fois

Vérifier le statut :

```bash
curl -sS http://localhost:5000/setup/status
```

Ou, via le proxy Replit :

```bash
curl -sS http://localhost:80/setup/status
```

Initialiser le nœud avec un mot de passe choisi par l’opérateur :

```bash
curl -X POST http://localhost:80/setup/init-node \
  -H 'Content-Type: application/json' \
  -d '{"node_name":"mon_noeud","password":"REMPLACER_PAR_UN_MOT_DE_PASSE_FORT","public_url":""}'
```

Contraintes :

- le mot de passe doit avoir au moins 8 caractères ;
- la réponse contient `seed_hex` une seule fois ;
- `seed_hex` est une clé privée : la sauvegarder hors du serveur ;
- ne jamais l’écrire dans Git, un ticket, un log partagé ou le rapport ;
- l’endpoint refuse une seconde initialisation avec HTTP 409.

Après l’appel, vérifier la réponse et sauvegarder uniquement les valeurs sensibles
dans un gestionnaire sécurisé. Puis redémarrer :

```bash
bash scripts/replit_start.sh
```

Vérifier :

```bash
curl -sS http://localhost:80/setup/status
curl -sS http://localhost:80/health
```

## 10. Cryptographie PQC : problème rencontré et solution

### Symptôme initial

Le premier démarrage a dépassé le délai de supervision et n’a pas ouvert le port
5000. Les logs montraient :

```text
liboqs not found, installing it in /home/runner/_oqs
Cloning into 'liboqs'...
[...]
Building C object ...
```

La cause était l’import de `oqs` pendant la création de l’application. La version
installée de `liboqs-python` déclenche une compilation automatique lorsqu’elle ne
trouve pas `liboqs.so`.

### Correctif appliqué

Le projet contient maintenant :

```text
src/artcb/crypto/liboqs_runtime.py
```

Ce module vérifie la présence d’une bibliothèque native déjà installée sans
importer `oqs`. Les modules `pqc.py`, `kem.py` et le script de démarrage utilisent
cette vérification non bloquante.

Le comportement est désormais :

- `liboqs.so` présent : le mode PQC peut être activé ;
- `liboqs.so` absent : démarrage immédiat avec fallback Ed25519/X25519 ;
- le statut reste visible dans `/health` ;
- le serveur ne prétend pas que ML-DSA-65 est actif lorsque ce n’est pas le cas.

### État vérifié

Dans l’environnement testé :

```json
{
  "available": false,
  "algorithm": "Ed25519 (fallback)"
}
```

Le nœud fonctionne, mais la sécurité post-quantique complète n’est pas active.
Il faut traiter ce point comme une limitation de sécurité de production, pas comme
un simple avertissement esthétique.

## 11. Bug API rencontré et corrigé

`/api/health` renvoyait HTTP 500 avec :

```text
NameError: cannot access free variable 'JSONResponse'
```

La cause était un import local de `JSONResponse` dans une branche de `create_app()`,
qui rendait le nom local à toute la fonction et le rendait indisponible dans le
handler bootstrap.

Le correctif a supprimé l’import local inutile et utilise l’import global déjà
présent.

Comportement final en mode bootstrap :

- `/health` → HTTP 200 avec le statut du nœud ;
- `/api/health` et `/api/v1/health` → HTTP 503 explicite, car les routes métier
  ne sont pas encore activées ;
- `/setup/status` → HTTP 200 ;
- `/setup/init-node` → endpoint de configuration ;
- les assets frontend restent accessibles.

## 12. Frontend en mode bootstrap

Un second problème a été trouvé : le catch-all bootstrap bloquait les assets React
avec HTTP 503.

Le correctif sert maintenant :

- `/` avec `frontend/dist/index.html` ;
- `/assets/...` avec `StaticFiles` ;
- les routes frontend inconnues avec `index.html` ;
- les routes métier non initialisées avec une réponse bootstrap protégée.

Vérification réalisée :

```text
GET /                       → HTTP 200 text/html
GET /assets/index-BpsK4RrI.js → HTTP 200 text/javascript
```

## 13. Commandes de vérification utilisées

### Syntaxe Python

```bash
python3 -m py_compile \
  src/artcb/crypto/liboqs_runtime.py \
  src/artcb/crypto/pqc.py \
  src/artcb/crypto/kem.py
```

### Contrôle du diff

```bash
git diff --check
```

### Build frontend

```bash
cd frontend
npm run build
cd ..
```

### Import sans déclencher la compilation PQC

```bash
HOME=/home/runner \
PYTHONPATH=/home/runner/workspace \
ARTCB_PQC_ENABLED=false \
/home/runner/venv/bin/python3 - <<'PY'
from src.artcb.crypto.liboqs_runtime import native_liboqs_available
from src.artcb.crypto.pqc import pqc_available
from src.artcb.crypto.kem import _oqs_available

print("native_liboqs_available=", native_liboqs_available())
print("pqc_available=", pqc_available())
print("kem_available=", _oqs_available())
PY
```

Résultat observé :

```text
native_liboqs_available= False
pqc_available= False
kem_available= False
```

### Contrôle HTTP via le proxy Replit

```bash
curl -i http://localhost:80/
curl -i http://localhost:80/health
curl -i http://localhost:80/api/health
curl -i http://localhost:80/setup/status
curl -i http://localhost:80/assets/index-BpsK4RrI.js
```

## 14. Résultat de la vérification finale

| Vérification | Résultat |
|---|---|
| Workflow `Start application` | ACTIF |
| Uvicorn | `Application startup complete` |
| Port 5000 | OUVERT |
| `/` | HTTP 200 |
| `/health` | HTTP 200 |
| `/setup/status` | HTTP 200 |
| `/api/health` en bootstrap | HTTP 503 explicite |
| Asset frontend | HTTP 200 |
| Build frontend | RÉUSSI |
| Syntaxe Python modifiée | RÉUSSIE |
| `git diff --check` | RÉUSSI |
| Publication Replit | PAS ENCORE EFFECTUÉE |
| PQC ML-DSA-65 / ML-KEM-768 | NON DISPONIBLE dans cet environnement |

## 15. Déploiement Replit manuel

### 15.1 Avant publication

1. Vérifier que le workflow démarre sans erreur.
2. Initialiser le nœud avec `POST /setup/init-node`.
3. Sauvegarder `seed_hex` de manière sécurisée.
4. Redémarrer le workflow.
5. Vérifier `/health`.
6. Vérifier que `pqc.available` correspond à votre niveau de sécurité attendu.
7. Vérifier les variables de production dans les Secrets Replit.
8. Vérifier `ARTCB_DEBUG=false`.
9. Vérifier que les bypass d’étude sont désactivés.

### 15.2 Configuration déjà présente

`.replit` contient déjà :

```toml
[deployment]
run = ["bash", "scripts/replit_start.sh"]
deploymentTarget = "autoscale"
```

Le service expose le port local 5000 vers le port externe HTTP.

### 15.3 Publier

Dans Replit :

1. ouvrir l’outil **Publish** ;
2. vérifier la cible `Autoscale` ;
3. vérifier la commande de lancement :
   `bash scripts/replit_start.sh` ;
4. vérifier les variables/secrets de production ;
5. choisir la visibilité ;
6. cliquer sur **Publish** ;
7. attendre la fin du build ;
8. ouvrir l’URL de production fournie par Replit ;
9. tester `/`, `/health` et `/setup/status`.

Le statut avant publication de ce rapport est :

```text
isDeployed=false
primaryUrl=""
hasSuccessfulBuild=false
```

Aucune URL de production ne doit être inventée à partir de `REPLIT_DOMAINS` :
cette variable correspond à l’environnement de développement Replit, pas
nécessairement à l’URL publiée.

## 16. Déploiement Docker manuel

Le dépôt fournit également un `Dockerfile`.

Construire :

```bash
docker build -t artcb/node:latest .
```

Lancer :

```bash
docker run --rm \
  -p 8000:8000 \
  --env-file .env \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/logs:/app/logs" \
  artcb/node:latest
```

Vérifier :

```bash
curl -i http://localhost:8000/health
```

Le Dockerfile installe CMake, Ninja, GCC, G++, OpenSSL, curl et Git avant les
dépendances Python. Il utilise le port 8000 par défaut, contrairement au workflow
Replit qui utilise le port 5000.

## 17. Points à ne pas oublier en production

1. Ne jamais utiliser un mot de passe d’exemple.
2. Ne jamais committer `.env`.
3. Ne jamais publier `seed_hex`.
4. Ne jamais considérer `pqc.available=false` comme acceptable sans décision
   explicite de sécurité.
5. Ne pas activer `ARTCB_ANTI_SYBIL_AI_BYPASS` en production.
6. Ne pas activer `ARTCB_ANTI_SYBIL_STUDY_MODE` en production.
7. Conserver `data/` et les journaux selon une stratégie de sauvegarde.
8. Utiliser une base de données ou un stockage persistant adapté si plusieurs
   instances Autoscale doivent partager l’état.
9. Vérifier que l’URL publique du nœud est réellement joignable pour le P2P.
10. Après toute modification du code de démarrage, redémarrer le workflow et
    attendre la preuve `Application startup complete`.

## 18. Modifications réalisées pendant cette reprise

### Correctifs fonctionnels

- vérification non bloquante de la présence native de `liboqs` ;
- prévention de la compilation automatique de `liboqs` pendant l’import API ;
- fallback cryptographique explicite et observable ;
- correction de la portée de `JSONResponse` ;
- réponse HTTP 200 de `/` en bootstrap ;
- service des assets React en bootstrap ;
- conservation de la protection des routes métier avant initialisation.

### Correction sécurité

- remplacement du token LoopQA ressemblant à un secret dans `.env.example` par
  un placeholder.

### Éléments préexistants à examiner

L’état Git au début de la reprise contenait déjà des suppressions locales :

```text
attached_assets/Pasted-2026-08-08T01:54:25-685Z-healthcheck-failed-error-healt_1786154232632.txt
frontend/dist/assets/index-CYyAdQP8.js
```

Ces suppressions n’ont pas été recréées automatiquement, car elles étaient
antérieures à la correction et le frontend possède déjà un build valide avec de
nouveaux noms d’assets générés par Vite. Si le fichier de diagnostic supprimé doit
être conservé comme archive, il faut le restaurer depuis un checkpoint ou une copie
de sauvegarde, pas le recréer artificiellement.

## 19. Commande de démarrage recommandée à retenir

Pour un Repl déjà installé :

```bash
bash scripts/replit_start.sh
```

Pour une installation manuelle complète sur une machine Linux :

```bash
git clone https://github.com/vgactech/artcb.git
cd artcb
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
cd frontend
npm install
npm run build
cd ..
ARTCB_HOST=0.0.0.0 ARTCB_PORT=8000 \
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Pour Replit, ne pas lancer le backend et le frontend dans deux serveurs
indépendants si l’objectif est d’utiliser la configuration actuelle : le script
Replit construit le frontend et FastAPI le sert sur le même port 5000.