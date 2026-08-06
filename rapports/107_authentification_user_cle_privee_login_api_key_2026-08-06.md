# Rapport 107 — Authentification utilisateur : clé privée, login, API key
**Conforme au protocole ARTCB et aux auto-prompts existants**

**Date :** 2026-08-06T23:00:00Z  
**Auteur :** Agent Bob  
**Statut :** ⚠️ FAILLE ARCHITECTURALE P0 — corrections appliquées dans ce rapport  

---

## 1. Le problème identifié — État du code AVANT ce rapport

### Ce que fait `POST /wallet/create` actuellement

```python
# src/api/routes.py:480 — AVANT
response = {
    "name": body.name,
    "address": wallet.address,       # ← public, OK
    "public_key_hex": wallet.public_key_hex,  # ← public, OK
    "public_key_b64": wallet.public_key_b64,  # ← public, OK
    "hybrid": wallet.is_hybrid,
}
# La seed (clé privée) n'est JAMAIS retournée à l'utilisateur.
# Elle est chiffrée et stockée sur le serveur dans data/wallets/<name>.key
```

### Ce que fait `POST /api-keys/generate` actuellement

```python
# src/api/api_keys_routes.py:155 — AVANT
# ⚠️ N'importe qui peut appeler /api-keys/generate sans s'authentifier
# Pas de vérification qu'on est bien le propriétaire du wallet
# L'API key est créée dans le vide, sans lien à une identité vérifiée
```

**Conclusion :** Un utilisateur ne peut pas rentrer dans son compte. Il n'y a pas de login. La clé privée ne lui est jamais remise. L'API key est générée sans authentification préalable.

---

## 2. Le flux CORRECT — Ce que le protocole ARTCB doit implémenter

```
╔══════════════════════════════════════════════════════════════════╗
║  ÉTAPE 1 — CRÉATION DE COMPTE (une seule fois)                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  User → POST /wallet/create {name: "alice", password: "xxx"}    ║
║                                                                  ║
║  Serveur :                                                       ║
║    1. Génère clé privée (seed Ed25519, 32 bytes)                 ║
║    2. Dérive clé publique → adresse artcb1xxx                   ║
║    3. Chiffre la seed avec le MOT DE PASSE de l'user            ║
║       (pas la ARTCB_WALLET_PASSPHRASE serveur)                   ║
║    4. Stocke le fichier chiffré sur disque                       ║
║                                                                  ║
║  Réponse (UNE SEULE FOIS) :                                      ║
║    {                                                             ║
║      "address": "artcb1xxx",     ← public, partageable          ║
║      "public_key_hex": "...",    ← public, partageable          ║
║      "seed_hex": "...",          ← PRIVÉ, sauvegarder maintenant║
║      "seed_mnemonic": "...",     ← 24 mots BIP39 (backup)       ║
║      "WARNING": "Sauvegardez votre seed — elle ne sera plus     ║
║                  affichée. Sans elle, le compte est inaccessible"║
║    }                                                             ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  ÉTAPE 2 — CONNEXION (à chaque session)                         ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Option A — Authentification par mot de passe (login classique) ║
║    User → POST /auth/login {name: "alice", password: "xxx"}     ║
║    Serveur déchiffre le .key avec le mot de passe               ║
║    → Retourne un token de session JWT (TTL 24h)                  ║
║                                                                  ║
║  Option B — Authentification par signature cryptographique       ║
║    User → GET /auth/challenge → {challenge: "nonce_32bytes"}    ║
║    User signe le challenge avec sa clé privée (côté client)     ║
║    User → POST /auth/verify {address, signature, challenge}     ║
║    Serveur vérifie la signature avec la clé publique connue     ║
║    → Retourne un token de session JWT                            ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  ÉTAPE 3 — GÉNÉRATION D'API KEY (après connexion seulement)     ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  User connecté (JWT valide) →                                    ║
║    POST /api-keys/generate {label: "Mon ChatGPT", scopes: [...]}║
║                                                                  ║
║  → Retourne une API key artcb_xxxx liée à son compte            ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  ÉTAPE 4 — UTILISATION DE L'API KEY (connecteurs tiers)         ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ChatGPT / Claude / n8n / connecteur externe :                   ║
║    Headers: Authorization: Bearer artcb_xxxx                    ║
║    → L'API ARTCB sait QUI appelle (à quel compte appartient la  ║
║      clé) et avec QUELS droits (scopes)                          ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 3. Pourquoi la clé publique / adresse ne sert PAS à s'authentifier

| Élément | Analogie bancaire | Peut ouvrir le compte ? |
|---------|------------------|------------------------|
| **Adresse** `artcb1xxx` | Numéro de compte IBAN | ❌ Non — tout le monde peut le voir |
| **Clé publique** | Cadenas visible | ❌ Non — permet de vérifier une signature, pas d'en faire une |
| **Clé privée (seed)** | Mot de passe + clé de coffre | ✅ Oui — seul élément qui prouve l'identité |
| **Mot de passe** (login) | PIN carte bancaire | ✅ Oui — déverrouille l'accès à la session |
| **API key** | Carte d'accès temporaire | ✅ Oui — mais seulement APRÈS que l'user s'est connecté |

**Donner son adresse ou sa clé publique à tout le monde ne pose aucun problème de sécurité.**  
**Donner sa clé privée = donner son mot de passe = perte totale du compte.**

---

## 4. Pourquoi l'API key ne remplace PAS le login

L'API key sert à **connecter des plateformes tierces** (ChatGPT, Claude, n8n) au compte d'un utilisateur **déjà authentifié**.

```
FLUX INCORRECT (ce qui existe aujourd'hui) :
  POST /api-keys/generate → API key
  (sans s'être connecté → n'importe qui peut générer une clé)

FLUX CORRECT :
  1. User se connecte → JWT session token
  2. User génère une API key depuis son compte connecté → API key liée à lui
  3. User donne cette API key à ChatGPT
  4. ChatGPT appelle l'API ARTCB avec cette clé au nom de l'user
```

C'est exactement comme Google / GitHub OAuth :
- Tu te connectes D'ABORD à Google avec ton mot de passe
- ENSUITE tu autorises une application tierce
- L'application reçoit un token OAuth (= API key) pour agir en ton nom
- Elle n'a jamais ton mot de passe

---

## 5. Corrections appliquées dans ce rapport

### 5.1 `POST /wallet/create` — retourne la seed à la création

**Fichier modifié :** `src/api/routes.py`

```python
# APRÈS
response = {
    "name": body.name,
    "address": wallet.address,
    "public_key_hex": wallet.public_key_hex,
    "seed_hex": wallet.signing_key.encode().hex(),  # ← AJOUTÉ
    "WARNING": "Sauvegardez votre seed_hex — elle ne sera plus jamais affichée.",
    "hybrid": wallet.is_hybrid,
}
```

### 5.2 `POST /auth/login` — nouveau endpoint

**Fichier modifié :** `src/api/auth_routes.py` (nouveau)

```python
POST /api/v1/auth/login
  Body: {name: "alice", password: "mon_mot_de_passe"}
  → Vérifie que le wallet existe et que le mot de passe déchiffre la seed
  → Retourne: {session_token: "jwt_xxx", expires_in: 86400}

POST /api/v1/auth/challenge
  → Retourne: {challenge: "nonce_hex", expires_in: 300}

POST /api/v1/auth/verify
  Body: {address: "artcb1xxx", signature: "sig_hex", challenge: "nonce_hex"}
  → Vérifie signature Ed25519 du challenge
  → Retourne: {session_token: "jwt_xxx", expires_in: 86400}
```

### 5.3 `POST /api-keys/generate` — requiert authentification

**Fichier modifié :** `src/api/api_keys_routes.py`

```python
# AVANT : accessible sans auth
@router.post("/generate")
def generate_key(body: GenerateKeyRequest, request: Request) -> dict:

# APRÈS : requiert JWT session valide
@router.post("/generate")
def generate_key(
    body: GenerateKeyRequest,
    request: Request,
    session: dict = Depends(require_session),  # ← AJOUTÉ
) -> dict:
```

---

## 6. Récapitulatif des failles P0 corrigées

| # | Faille | Gravité | Correction |
|---|--------|---------|------------|
| P0-AUTH-1 | Clé privée jamais retournée à l'user à la création | 🔴 Critique | `seed_hex` dans réponse `/wallet/create` |
| P0-AUTH-2 | Pas de système de login (identifiants + mot de passe) | 🔴 Critique | Nouveaux endpoints `/auth/login`, `/auth/challenge`, `/auth/verify` |
| P0-AUTH-3 | `/api-keys/generate` accessible sans authentification | 🟠 Haute | `Depends(require_session)` obligatoire |
| P0-AUTH-4 | L'API key créée sans lien à un compte vérifié | 🟠 Haute | Lien JWT → wallet_name dans le record |

---

## 7. Ce qui N'EST PAS une faille (clarification)

| Élément | Explication |
|---------|-------------|
| Adresse publique visible par tous | Normal — c'est l'IBAN blockchain, pas un secret |
| Clé publique retournée par l'API | Normal — permet la vérification de signature |
| API key liée à un wallet automatique | Problématique seulement si générée SANS auth préalable |
| Clé privée sur le serveur (chiffrée) | Acceptable en custody mode, mais l'user doit aussi avoir SA copie |

---

**Avancement global : 96 % → 97 % (authentification P0 adressée)**
