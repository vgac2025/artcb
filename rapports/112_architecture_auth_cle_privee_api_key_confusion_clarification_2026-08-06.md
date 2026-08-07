# Rapport 112 — Architecture Auth : Clé privée, Mot de passe, API Key — Clarification absolue
**Conforme au protocole ARTCB et aux auto-prompts existants**

**Date :** 2026-08-06  
**Auteur :** Agent Bob  
**Déclencheur :** Question critique de l'utilisateur sur la confusion architecturale wallet / clé publique / API key  
**Statut :** ✅ Conformité vérifiée — le code EST déjà correct depuis le rapport 107

---

## 1. La question posée (résumé fidèle)

> « Un utilisateur crée son compte, reçoit un wallet avec une adresse et doit recevoir sa clé privée.  
> L'API sert juste de connexion entre les différentes plateformes après.  
> Comment est-ce que le gars va rentrer sur son compte avec une API et une adresse seulement ?  
> Pour entrer dans le compte il est obligé de mettre sa clé privée, pas autre chose.  
> Les API ne fonctionnent que si la personne est d'abord entrée dans son compte avec mot de passe et identifiants.  
> Comment un user peut entrer dans son compte privé simplement avec une clé publique ?  
> C'est comme si tu donnes ton mot de passe à tout le monde. »

**La question est PARFAITEMENT CORRECTE et JUSTE.**

---

## 2. Le flux CORRECT — Trois éléments distincts, trois usages distincts

```
╔══════════════════════════════════════════════════════════════════════════╗
║  ÉTAPE 1 — CRÉATION DE COMPTE (une seule fois)                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  POST /wallet/create                                                     ║
║    Body : { "name": "alice", "password": "mon_mot_de_passe_fort" }      ║
║                                                                          ║
║  Réponse (UNE SEULE FOIS) :                                              ║
║    {                                                                     ║
║      "address":        "artcb1xxx…"   ← PUBLIC — IBAN blockchain        ║
║      "public_key_hex": "abcdef…"      ← PUBLIC — cadenas vérifiable     ║
║      "seed_hex":       "deadbeef…"    ← PRIVÉ — CLÉ PRIVÉE              ║
║      "WARNING": "Sauvegardez cette seed — jamais réaffichée"             ║
║    }                                                                     ║
║                                                                          ║
║  L'utilisateur DOIT sauvegarder la seed_hex maintenant.                  ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║  ÉTAPE 2 — CONNEXION À LA PLATEFORME (à chaque session)                 ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  POST /auth/login                                                        ║
║    Body : { "name": "alice", "password": "mon_mot_de_passe_fort" }      ║
║                                                                          ║
║  Réponse :                                                               ║
║    { "session_token": "sess_xxx…", "expires_in": 86400 }                ║
║                                                                          ║
║  C'est EXACTEMENT comme un login classique :                             ║
║    Username + mot de passe → token de session valide 24h                ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║  ÉTAPE 3 — GÉNÉRER UNE API KEY (après connexion SEULEMENT)              ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  POST /api-keys/generate                                                 ║
║    Header : Authorization: Bearer sess_xxx…  ← token de session requis  ║
║    Body :   { "label": "Mon ChatGPT", "scopes": ["read", "write"] }     ║
║                                                                          ║
║  Réponse :                                                               ║
║    { "token": "artcb_yyyy…" }  ← API key pour les connecteurs tiers     ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║  ÉTAPE 4 — UTILISATION PAR UN CONNECTEUR TIERS (ChatGPT, Claude, n8n)  ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  ChatGPT utilise l'API key "artcb_yyyy…" dans ses appels :              ║
║    Authorization: Bearer artcb_yyyy…                                    ║
║                                                                          ║
║  → L'API ARTCB sait QUI appelle (wallet lié à la clé)                   ║
║  → avec QUELS droits (scopes read/write/mining)                          ║
║  → ChatGPT n'a JAMAIS le mot de passe de l'utilisateur                  ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## 3. Tableau de clarté — Qui est quoi, qui sert à quoi

| Élément | Analogie bancaire | Partageable ? | Sert à se connecter ? | Sert à un tiers ? |
|---------|------------------|:------------:|:--------------------:|:----------------:|
| **Adresse** `artcb1xxx` | Numéro de compte IBAN | ✅ OUI | ❌ NON | ❌ NON |
| **Clé publique** `public_key_hex` | Cadenas visible | ✅ OUI | ❌ NON | ❌ NON |
| **`seed_hex`** (clé privée) | Clé physique du coffre | ❌ JAMAIS | ✅ Récupération | ❌ NON |
| **Mot de passe** `password` | Code PIN + code du coffre | ❌ JAMAIS | ✅ Login normal | ❌ NON |
| **`sess_xxx`** (token de session) | Badge temporaire d'entrée | ❌ NON | ✅ pendant 24h | ❌ NON |
| **`artcb_xxx`** (API key) | Token OAuth pour app tierce | Uniquement à la plateforme cible | ❌ NON | ✅ OUI |

**Donner son adresse ou sa clé publique à tout le monde = NORMAL, aucun risque.**  
**Donner sa clé privée (seed_hex) = perdre son compte. Ne jamais partager.**  
**Donner une API key à ChatGPT = normal — c'est fait POUR ça, et seulement après login.**

---

## 4. Pourquoi l'adresse seule NE PEUT PAS donner accès au compte

L'adresse `artcb1xxx` est **dérivée** de la clé publique qui est elle-même **dérivée** de la clé privée.
C'est une opération à sens unique (cryptographie asymétrique) :

```
clé_privée (seed_hex) → [Ed25519] → clé_publique → [hash/bech32] → adresse
```

**La dérivation inverse est cryptographiquement impossible.**  
Connaître l'adresse ne permet pas de retrouver la clé publique complète.  
Connaître la clé publique ne permet pas de retrouver la clé privée.

**L'adresse est un IDENTIFIANT public, pas un secret.**

---

## 5. Pourquoi l'API key ne remplace PAS le mot de passe

L'API key (`artcb_xxx`) est un outil d'**intégration externe**, pas de **connexion personnelle**.

```
ANALOGIE GOOGLE OAUTH :
  1. Tu te connectes à Google avec ton email + mot de passe (LOGIN CLASSIQUE)
  2. Google te demande : "Autoriser cette app à accéder à ton compte ?"
  3. Tu acceptes → l'app reçoit un token OAuth (= API key ARTCB)
  4. L'app agit EN TON NOM avec ce token
  5. L'app n'a JAMAIS ton mot de passe Google

C'est EXACTEMENT le même principe avec ARTCB :
  1. Tu te connectes à ARTCB avec ton nom + mot de passe (POST /auth/login)
  2. Tu génères une API key (POST /api-keys/generate) — SEULEMENT si connecté
  3. Tu donnes cette API key à ChatGPT / Claude / n8n
  4. Ces outils agissent en ton nom avec cette clé
  5. Ils n'ont JAMAIS ton mot de passe
```

---

## 6. Vérification du code — Conformité totale

### `POST /wallet/create` — [`src/api/routes.py:477`](../src/api/routes.py)

```python
# ✅ CONFORME — seed_hex retournée à la création
seed_hex = wallet.signing_key.encode().hex()
response = {
    "name": body.name,
    "address": wallet.address,           # public
    "public_key_hex": wallet.public_key_hex,  # public
    "seed_hex": seed_hex,                # ← CLÉ PRIVÉE — UNE SEULE FOIS
    "WARNING": "SAUVEGARDEZ votre seed_hex MAINTENANT — c'est votre clé privée, "
               "elle ne sera plus jamais affichée.",
}
```

**État : ✅ CONFORME depuis rapport 107**

---

### `POST /auth/login` — [`src/api/auth_routes.py:93`](../src/api/auth_routes.py)

```python
# ✅ CONFORME — login classique nom + mot de passe
@router.post("/login")
def login(body: LoginRequest, request: Request) -> dict:
    # body.name = nom du wallet
    # body.password = mot de passe de l'utilisateur
    # → déchiffre la seed avec le mot de passe
    # → si succès : session_token valide 24h
    # → si échec : 401 "Identifiants invalides"
```

**État : ✅ CONFORME depuis rapport 107**

---

### `POST /api-keys/generate` — [`src/api/api_keys_routes.py:163`](../src/api/api_keys_routes.py)

```python
# ✅ CONFORME — session obligatoire avant de générer une API key
@router.post("/generate")
def generate_key(
    body: GenerateKeyRequest,
    request: Request,
    session: Annotated[dict, Depends(_require_session)],  # ← session obligatoire
) -> dict:
    # Sans session valide : 401
    # Avec session : API key créée et liée au wallet de la session
```

**État : ✅ CONFORME depuis rapport 107**

---

### Frontend `Wallets.tsx` — [`frontend/src/pages/Wallets.tsx`](../frontend/src/pages/Wallets.tsx)

```tsx
// ✅ CONFORME — trois sections bien séparées dans l'interface :
// 1. "Créer un wallet" — nom + mot de passe + confirmation (lignes 351-384)
// 2. "Connexion — J'ai déjà un compte" — nom + mot de passe (lignes 467-500)
// 3. "Observer un wallet (lecture seule)" — adresse seulement (lignes 502-521)
```

**État : ✅ CONFORME depuis rapport 111**

---

## 7. Ce qui était mal conçu AVANT le rapport 107 (pour mémoire)

| # | Faille | Description |
|---|--------|-------------|
| P0-AUTH-1 | Clé privée jamais retournée | La `seed_hex` n'était pas dans la réponse de `/wallet/create` |
| P0-AUTH-2 | Pas de login | Aucun endpoint `/auth/login` — l'utilisateur ne pouvait pas se connecter |
| P0-AUTH-3 | API key sans auth | N'importe qui pouvait générer une API key sans se connecter |
| P0-AUTH-4 | API key sans propriétaire | La clé était créée sans être liée à un compte vérifié |

**Toutes ces failles ont été corrigées dans le rapport 107 (2026-08-06).**  
**Le rapport 108 a déployé et documenté ces corrections.**

---

## 8. Ce rapport 112

Ce rapport est rédigé en réponse à la question de l'utilisateur pour confirmer que :

1. ✅ L'architecture est **déjà correcte** dans le code
2. ✅ Le flux création → login → API key est **déjà implémenté**
3. ✅ La clé privée est **déjà retournée** à la création du wallet
4. ✅ L'API key **ne peut pas** être générée sans connexion préalable
5. ✅ L'adresse publique **ne donne pas** accès au compte (intentionnel)
6. ✅ Le frontend expose **trois sections distinctes** : créer / connexion / lecture seule

**Aucune correction de code n'est nécessaire — le code était déjà conforme.**  
Ce rapport documente la conformité et explicite l'architecture pour éviter toute confusion future.

---

**Avancement global : 97 % (inchangé — conformité confirmée)**
