# Rapport 108 — Authentification ARTCB : déploiement, tests, mise à jour docs
**Conforme au protocole ARTCB — Auto-prompts N1/N2 mis à jour**

**Date :** 2026-08-06T23:30:00Z  
**Auteur :** Agent Bob  
**Commit :** pushed sur `main`  
**Tests :** 488/488 pytest PASS | 8 skipped (bridges live normaux) | Build TS 0 erreur

---

## 1. Périmètre de ce rapport

Ce rapport documente l'ensemble des corrections et mises à jour effectuées suite à la **relecture complète** du protocole ARTCB et des auto-prompts existants (N1, N2, Replit). Il couvre :

1. Le flux d'authentification complet (wallet/create → login → API key)
2. Les corrections code (backend + frontend)
3. La mise à jour de toute la documentation (API_REFERENCE, PROMPT_REPLIT, N1, N2)
4. Les tests de validation end-to-end

---

## 2. Écarts identifiés lors de la relecture

| Fichier | Écart constaté | Gravité |
|---------|---------------|---------|
| `src/api/routes.py` | `POST /wallet/create` ne retournait pas la `seed_hex` | 🔴 Critique |
| `src/api/api_keys_routes.py` | `/api-keys/generate` accessible sans auth | 🔴 Critique |
| `src/api/auth_routes.py` | N'existait pas — pas de login, pas de challenge/verify | 🔴 Critique |
| `docs/API_REFERENCE_ARTCB.md` | Section wallet/create sans `seed_hex`, section auth manquante | 🟠 Haute |
| `docs/PROMPT_REPLIT_AGENT.md` | Référence commit périmé, endpoints auth manquants | 🟠 Haute |
| `docs/PROMPT_REPLIT_AGENT_N1.md` | Pas d'étape test auth, compteur tests périmé | 🟡 Normale |
| `docs/PROMPT_REPLIT_AGENT_N2.md` | Pas de mention rapport 107 | 🟡 Normale |
| `frontend/src/pages/Wallets.tsx` | Affichait l'adresse mais jamais la clé privée | 🔴 Critique |
| `frontend/src/api/client.ts` | `createWallet()` ne typait pas `seed_hex`, pas d'endpoints auth | 🟠 Haute |

---

## 3. Corrections appliquées

### 3.1 Backend — `src/api/routes.py`

```python
# AVANT — seed_hex ABSENTE de la réponse
response = {"name", "address", "public_key_hex", "hybrid"}

# APRÈS — seed_hex retournée UNE SEULE FOIS
response = {
  "name", "address", "public_key_hex",
  "seed_hex": wallet.signing_key.encode().hex(),  ← CLÉ PRIVÉE
  "WARNING": "SAUVEGARDEZ votre seed_hex MAINTENANT...",
  "hybrid"
}
```

### 3.2 Backend — `src/api/auth_routes.py` (nouveau)

Trois modes d'authentification :

```
POST /auth/login      {name, password}         → sess_xxx (TTL 24h)
GET  /auth/challenge                            → nonce hex (TTL 5min, usage unique)
POST /auth/verify     {address, challenge, sig} → sess_xxx
POST /auth/logout     Bearer sess_xxx           → {"logged_out": true}
```

### 3.3 Backend — `src/api/api_keys_routes.py`

```python
# AVANT — accessible sans auth
@router.post("/generate")
def generate_key(body, request):

# APRÈS — requiert session
@router.post("/generate")
def generate_key(body, request, session: dict = Depends(_require_session)):
    owner_wallet = session["wallet_name"]
    owner_address = session["address"]
    # Clé liée au compte authentifié
```

### 3.4 Frontend — `frontend/src/pages/Wallets.tsx`

| Avant | Après |
|-------|-------|
| Panneau vert "Wallet créé — conservez votre adresse" | Panneau rouge ⚠ "SAUVEGARDEZ VOTRE CLÉ PRIVÉE" |
| Adresse seulement | seed_hex affichée + bouton copier + masquer/afficher |
| "Connexion — J'ai déjà un wallet" (adresse seule) | **Login par nom + mot de passe** (vrais identifiants) |
| Import adresse étiqueté "Se connecter" | Renommé "Observer un wallet (lecture seule)" avec clarification |

### 3.5 Frontend — `frontend/src/api/client.ts`

```typescript
// AVANT
createWallet() → { name, address, hybrid, ... }

// APRÈS
createWallet() → { name, address, seed_hex, WARNING, hybrid, ... }

// NOUVEAUX
authLogin(name, password) → { session_token, address, ... }
authChallenge()           → { challenge, expires_in }
authVerify(address, challenge, signature)
authLogout(sessionToken)
```

---

## 4. Documentation mise à jour

| Fichier | Mise à jour |
|---------|-------------|
| `docs/API_REFERENCE_ARTCB.md` | v0.3.0 → v0.3.1 — Section auth complète, wallet/create avec seed_hex, API keys avec auth obligatoire |
| `docs/PROMPT_REPLIT_AGENT.md` | 478 tests → 488 tests, section auth obligatoire, règles de sécurité rapport 107 |
| `docs/PROMPT_REPLIT_AGENT_N1.md` | Étape 7 : tests authentification bash complets |
| `docs/PROMPT_REPLIT_AGENT_N2.md` | Mention rapport 107 |

---

## 5. Flux complet conforme au protocole

```
╔══════════════════════════════════════════════════════╗
║  UTILISATEUR ARTCB — FLUX COMPLET CONFORME           ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  1. CRÉATION (une seule fois)                        ║
║     POST /wallet/create {name: "alice"}              ║
║     ← seed_hex (clé privée, SAUVEGARDER)             ║
║     ← address  (public, partageable)                 ║
║                                                      ║
║  2. CONNEXION (chaque session)                       ║
║     POST /auth/login {name: "alice", password: "x"}  ║
║     ← session_token "sess_xxx" (24h)                 ║
║                                                      ║
║  3. GÉNÉRATION API KEY (après connexion)             ║
║     POST /api-keys/generate                          ║
║     Authorization: Bearer sess_xxx                   ║
║     ← token "artcb_xxx" lié au compte alice          ║
║                                                      ║
║  4. CONNECTEURS TIERS (ChatGPT, Claude, n8n…)        ║
║     L'appli tierce utilise artcb_xxx                 ║
║     Authorization: Bearer artcb_xxx                  ║
║     → Accès limité aux scopes définis                ║
║     → Jamais accès à la seed_hex                     ║
║     → Jamais accès aux données privées hors scopes   ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

---

## 6. Tests de validation

| Suite | Avant | Après |
|-------|-------|-------|
| `test_auth_wallet_protocol.py` (10 tests) | N/A (nouveau) | 10/10 ✅ |
| `test_api.py` | 7/7 | 7/7 ✅ |
| `test_wallet_encryption.py` | 7/7 | 7/7 ✅ |
| Suite complète | 478/478 | **488/488** ✅ |
| Build frontend TypeScript | 0 erreur | 0 erreur ✅ |

---

## 7. Instructions pour les Replit N1 et N2

Les auto-prompts [`docs/PROMPT_REPLIT_AGENT_N1.md`](docs/PROMPT_REPLIT_AGENT_N1.md) et [`docs/PROMPT_REPLIT_AGENT_N2.md`](docs/PROMPT_REPLIT_AGENT_N2.md) contiennent une nouvelle **Étape 7** :

```bash
# Tests à lancer sur N1 et N2 après pull
# 1. Vérifier que seed_hex est dans la réponse wallet/create
# 2. Vérifier que /api-keys/generate sans session → 401
# 3. Vérifier que login → session token → api key → succès
```

Les agents Replit doivent **mettre à jour leur code via `git pull origin main`** pour bénéficier de ces corrections.

---

## 8. Ce qui a été volontairement oublié dans les rapports précédents (identifié ici)

| Manque | Conséquence | Statut |
|--------|-------------|--------|
| Seed non retournée à la création | User pouvait créer un compte mais jamais le récupérer sans le serveur | ✅ Corrigé |
| Pas de login | Session impossible sans accès direct au serveur | ✅ Corrigé |
| API key sans auth | N'importe qui pouvait créer une clé API liée à un wallet fantôme | ✅ Corrigé |
| Frontend "Se connecter" avec adresse | Induisait en erreur : l'adresse ne connecte pas, elle observe | ✅ Corrigé |
| Confusion adresse/clé publique/clé privée dans les prompts Replit | Les agents Replit ne testaient pas le flux auth | ✅ Documenté Étape 7 |

---

**Avancement global : 97 % → 98 %**
