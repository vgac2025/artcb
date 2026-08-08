# Rapport 121 — Dépôt vgactech/artcb, liboqs non-bloquant, erreurs frontend bootstrap, install one-shot

**Horodatage :** 2026-08-08T10:00:00Z  
**Agent :** Bob (local)  
**Déclencheur :** Travail de l'agent Replit sur `ma-branche` + erreurs debug frontend (503 PoL/Chain, Method Not Allowed /health) + renommage dépôt `vgactech/artcb`  
**Tests :** 519 passed, 8 skipped — zéro régression  
**Commits :** rapport 121

---

## 1. Contexte — ce que l'agent Replit a résolu sur `ma-branche`

L'agent Replit a démarré depuis zéro sur une installation vierge et a rencontré le **même problème que le rapport 120** : `liboqs-python` bloque le démarrage en compilant automatiquement `liboqs` pendant l'import Python, empêchant Uvicorn d'ouvrir le port dans les 60 secondes du healthcheck Replit.

### Solution trouvée par l'agent Replit (correcte, intégrée)

Il a créé `src/artcb/crypto/liboqs_runtime.py` : un module qui vérifie la présence du `.so` natif **sans jamais importer `oqs`**, via `ctypes.util.find_library()` et un scan des chemins connus. Ce module est utilisé comme garde avant tout import dans `pqc.py`, `kem.py` et `replit_start.sh`.

**Pourquoi c'est la bonne approche :**
- `import oqs` déclenche la compilation si `liboqs.so` est absent (comportement du paquet PyPI)
- `ctypes.util.find_library("oqs")` ne déclenche rien — il cherche uniquement dans les chemins système
- Résultat : si `liboqs.so` absent → fallback immédiat sans délai

---

## 2. Corrections appliquées dans ce rapport

### 2.1 — Dépôt renommé : `vgac2025/artcb` → `vgactech/artcb`

**Fichiers mis à jour :**

| Fichier | Avant | Après |
|---------|-------|-------|
| `git remote origin` | `vgac2025/artcb.git` | `vgactech/artcb.git` ✅ |
| `README.md` (3 occurrences) | `vgac2025/artcb` | `vgactech/artcb` |
| `.env.example` | `vgac2025/artcb` | `vgactech/artcb` |
| `docs/DEPLOY_GUIDE.md` (2) | `vgac2025/artcb` | `vgactech/artcb` |
| `docs/PROMPT_REPLIT_AGENT.md` (3) | `vgac2025/artcb` | `vgactech/artcb` |

**Note :** Les fichiers `FORMULAIRE_SOUMISSION_HACKATHON_RAISE_2026.md`, `SCRIPT_VIDEO_PRESENTATION_1MIN.md`, et `INSTRUCTIONS_SSH_GITHUB.md` contiennent des références à `vgac2025/lvx` (l'ancien nom du dépôt avant renommage) — ces références sont dans des documents historiques et ne sont pas modifiées.

### 2.2 — Intégration des corrections `ma-branche`

#### `src/artcb/crypto/liboqs_runtime.py` (nouveau fichier)

```python
def native_liboqs_available() -> bool:
    """Vérifie si liboqs.so existe — sans jamais importer oqs."""
    if ctypes.util.find_library("oqs") or ctypes.util.find_library("liboqs"):
        return True
    # Fallback : chercher dans $HOME/_oqs (path par défaut de liboqs-python)
    install_root = Path(os.getenv("OQS_INSTALL_PATH", str(Path.home() / "_oqs")))
    ...
```

#### `src/artcb/crypto/pqc.py` — garde native avant `import oqs`

**AVANT :**
```python
def pqc_available() -> bool:
    try:
        import oqs as _oqs_test  # ← peut déclencher compilation bloquante
```

**APRÈS :**
```python
def pqc_available() -> bool:
    if not native_liboqs_available():
        _PQC_AVAILABLE = False; return False  # immédiat, sans import
    try:
        import oqs as _oqs_test  # import seulement si .so déjà présent
```

#### `src/artcb/crypto/kem.py` — même garde dans `_oqs_available()` et `_import_oqs()`

#### `scripts/replit_start.sh` — `_check_liboqs_native()` remplace `import oqs`

**AVANT :**
```bash
if $PYTHON -c "import oqs; oqs.get_enabled_sig_mechanisms()" ...
# peut déclencher compilation en arrière-plan ET bloquer le test
```

**APRÈS :**
```bash
_check_liboqs_native() {
    $PYTHON -c "import ctypes.util; ... find_library('oqs') ..."
    # vérifie uniquement si .so présent — zéro compilation
}
```

### 2.3 — Correction `.env.example` : token LoopQA exposé

**AVANT :** `LOOPQA_API_TOKEN=lqa_c13a64b1339ea4e9927f6f365f823b14e947d65b43a9fce5` (vrai token)  
**APRÈS :** `LOOPQA_API_TOKEN=REMPLACER_PAR_VOTRE_TOKEN_LOOPQA`

⚠️ Ce token était dans un fichier versionné public depuis plusieurs commits. Il doit être **révoqué immédiatement** sur https://qa.replay.io/settings/tokens.

---

### 2.4 — Correction erreurs debug frontend (`503 PoL`, `503 Chain`, `Method Not Allowed`)

**Symptômes :**
```
[!] PoL: AxiosError: Request failed with status code 503
[!] Chain: AxiosError: Request failed with status code 503
[!] API /health timeout     >>>>>>>> Method Not Allowed
```

**Cause racine :**

Le `DashboardLayout.tsx` et `Home.tsx` appellent ces URLs au démarrage :
- `GET /api/v1/health` — n'existait pas en mode bootstrap (catch-all retournait 503)
- `GET /api/v1/chain/verify` — bloqué par bootstrap_catchall (commence par `api/`)
- `GET /api/v1/pol/score` — idem

Le mode bootstrap bloquait toute URL commençant par `api/` avec 503, ce qui faisait afficher les alerts dans le debug panel après création de compte.

**Corrections dans `src/api/main.py` :**

1. **Alias `GET /api/v1/health`** ajouté en mode bootstrap → retourne le statut bootstrap au lieu de 503
2. **Frontend servi** (`/` + `/assets/*`) en mode bootstrap → le dashboard est accessible pour appeler `/setup/init-node`
3. **`_dist_dir` initialisé avant le catchall** → suppression du `NameError: JSONResponse` (bug de portée du commit précédent)
4. **Suppression `from fastapi.responses import JSONResponse`** dupliqué (import global déjà présent ligne 12)

**AVANT (mode bootstrap) :**
```
GET /api/v1/health → 503 (caught by full_path catchall)
GET /           → 404
GET /assets/*   → 503
```

**APRÈS :**
```
GET /health         → 200 {"status": "bootstrap", "pqc": {...}}
GET /api/v1/health  → 200 {"status": "bootstrap", ...}  ← nouveau
GET /               → 200 (index.html si frontend buildé, sinon JSON)
GET /assets/*       → 200 (StaticFiles montées en bootstrap)
GET /api/v1/*       → 503 avec message actionnable (sauf /api/v1/health)
```

### 2.5 — `install.sh` one-shot

Nouveau fichier `install.sh` à la racine du dépôt :

```bash
git clone https://github.com/vgactech/artcb.git && cd artcb && bash install.sh
```

Installe tout en une seule commande :
1. venv Python (`$REPO_DIR/.venv`)
2. toutes les dépendances Python (avec fallback si cmake absent)
3. détection PQC sans blocage
4. frontend React (npm install + build)
5. libartcb_chain.so (si compilateur disponible)
6. `.env` depuis `.env.example` si absent

---

## 3. Ce qui reste à faire (hors scope de ce rapport)

| ID | Problème | Source |
|----|----------|--------|
| P1-1 | Routes `/wallets` vs `/wallet` (404 frontend) | rapport 119 |
| P1-3 | Champ `name` non stocké dans wallet JSON | rapport 119 |
| P0-2 | Données éphémères sur autoscale Replit | rapport 119 |

---

## 4. Mesures réelles

```
Tests                : 519 passed, 8 skipped
Syntaxe Python       : OK (py_compile sur tous les fichiers modifiés)
Remote git           : https://github.com/vgactech/artcb.git ✅
liboqs local         : présent (0.15.0, ML-DSA-65 + ML-KEM-768 actifs)
/health bootstrap    : retourne pqc.available + action_required
/api/v1/health       : disponible en bootstrap (nouveau)
frontend en bootstrap: servi ✅
install.sh           : créé, syntaxe bash vérifiée
```

---

## 5. Procédure de reprise manuelle (one-shot)

```bash
# Cloner + installer en une seule commande
git clone https://github.com/vgactech/artcb.git && cd artcb && bash install.sh

# Démarrer (Replit)
bash scripts/replit_start.sh

# Démarrer (local)
source .venv/bin/activate
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Vérifier
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/setup/status

# Initialiser le nœud (première fois)
curl -X POST http://localhost:8000/setup/init-node \
  -H 'Content-Type: application/json' \
  -d '{"node_name":"mon_noeud","password":"VotreMotDePasseFort"}'
# → sauvegarder seed_hex, redémarrer
```

---

*Rapport 121 — aucun mock, mesures réelles. Prochain rapport : 122 (P1-1 routes /wallets alias + P1-3 name dans wallet JSON).*
