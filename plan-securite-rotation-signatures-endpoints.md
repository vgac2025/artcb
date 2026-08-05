# Plan — Sécurité rotation clés + Endpoints manquants + Tests réels Replit

**Date :** 2026-08-05  
**Branche :** main  
**Priorité :** CRITIQUE — sécurité blockchain production  
**Nouveau nœud Replit déployé :** https://lvx--supermicro20239.replit.app

---

## Vue d'ensemble

Trois axes de travail :

1. **FAILLE SÉCURITÉ CRITIQUE** — La rotation de clé (créateur ET utilisateur) accepte
   les requêtes sans signature. C'est documenté comme "mode dev" dans le code et les
   tests le valident explicitement. En production cette faille permettrait à n'importe
   qui de tourner une clé sans prouver qu'il possède l'ancienne clé.

2. **Endpoints manquants** — `/api/v1/chain/status`, `/api/v1/node/status`,
   `/api/v1/chain/blocks`, `POST /api/v1/ir/learn`, `POST /api/v1/governance/creator-key-rotation`,
   `POST /api/v1/governance/user-key-rotation`. Ces 404/405 font échouer les tests réels
   (22/25 au lieu de 25/25).

3. **Tests réels niveau production** — Rejouer les tests P2P réels sur le nouveau nœud
   Replit (supermicro20239) et vérifier que tout passe avec les corrections.

---

## Sous-tâche 1 — Bloquer les rotations sans signature (FAILLE CRITIQUE)

**Intent :** Rendre la signature OBLIGATOIRE pour toute rotation de clé. Une rotation
non signée doit retourner `GovernanceError` et être rejetée — peu importe l'environnement
(dev ou prod). Il n'existe pas de "mode dev" pour une opération qui transfère le contrôle
de la blockchain.

**Expected Outcomes :**
- `creator_key_rotation()` sans `signature_hex` → lève `GovernanceError("signature obligatoire")`
- `user_key_rotation()` sans `signature_hex` → lève `GovernanceError("signature obligatoire")`
- `sig_status` ne peut plus jamais valoir `"unsigned"` — les valeurs possibles sont
  `"verified"` ou `"sig_failed"` (et `"sig_failed"` entraîne aussi un rejet)
- `_append_special_block()` ne peut plus écrire `signature: "unsigned"` dans un bloc
- Les tests qui attendaient `"unsigned"` sont mis à jour pour tester le rejet

**Todo List :**
1. Lire `src/artcb/governance/manager.py` lignes 348-537 (creator_key_rotation) et 539-659 (user_key_rotation)
2. Dans `creator_key_rotation()` : supprimer le fallback `sig_status = "unsigned"` —
   si `signature_hex` est absent ou vide, lever `GovernanceError("Signature obligatoire...")`
3. Dans `creator_key_rotation()` : si `sig_status == "sig_failed"` après vérification,
   lever `GovernanceError("Signature invalide — rotation refusée")`
4. Même logique dans `user_key_rotation()`
5. Dans `_append_special_block()` : supprimer la valeur par défaut `"unsigned"` pour
   le champ `signature` — lever une erreur si la signature est absente ou `"unsigned"`
6. Mettre à jour la docstring pour supprimer la mention "mode dev accepté"
7. Dans `tests/test_governance_rotation.py` :
   - Supprimer le test `test_user_rotation_sans_signature_marquee_unsigned` (ou le
     convertir en test qui vérifie que l'absence de signature lève bien une `GovernanceError`)
   - Supprimer toute assertion `sig_status in ("verified", "sig_failed", "unsigned")`
   - Vérifier que tous les autres tests de rotation fournissent une signature valide

**Relevant Context :**
- `src/artcb/governance/manager.py` L421-454 (creator — bloc sig_status = "unsigned")
- `src/artcb/governance/manager.py` L580-611 (user — bloc sig_status = "unsigned")
- `src/artcb/governance/manager.py` L811 (`_append_special_block` — `"unsigned"` par défaut)
- `tests/test_governance_rotation.py` L167-178 (test "unsigned" accepté)
- `tests/test_governance_rotation.py` L164 (assert `in ("verified", "sig_failed", "unsigned")`)
- `src/artcb/crypto/hybrid.py` — `verify_hybrid()` à utiliser pour toute vérification

**Status :** [ ] pending

---

## Sous-tâche 2 — Ajouter les endpoints REST de rotation manquants

**Intent :** Implémenter les routes `POST /api/v1/governance/creator-key-rotation` et
`POST /api/v1/governance/user-key-rotation` dans `governance_routes.py`. Ces routes sont
référencées dans la docstring du code (L389) mais ne sont pas implémentées.
Elles doivent vérifier la signature AVANT d'appeler la méthode du manager.

**Expected Outcomes :**
- `POST /api/v1/governance/creator-key-rotation` retourne 200 avec le bloc de rotation
  si signature valide, 400 si signature invalide ou absente
- `POST /api/v1/governance/user-key-rotation` retourne 200 avec le bloc de rotation
  si signature valide, 400 si signature invalide ou absente
- Les deux endpoints requièrent `signature_hex` dans le body (non optionnel)

**Todo List :**
1. Lire `src/api/governance_routes.py` en entier
2. Ajouter `CreatorKeyRotationRequest(BaseModel)` avec `old_address`, `new_address`,
   `signature_hex` (obligatoire), `blocks_path` (optionnel)
3. Ajouter `UserKeyRotationRequest(BaseModel)` avec mêmes champs
4. Implémenter `POST /creator-key-rotation` — appelle `mgr.creator_key_rotation()`
5. Implémenter `POST /user-key-rotation` — appelle `mgr.user_key_rotation()`
6. Retourner 400 si `GovernanceError` (signature manquante ou invalide)

**Relevant Context :**
- `src/api/governance_routes.py` L40-41 (`_gov_http_error`)
- `src/artcb/governance/manager.py` L348 (`creator_key_rotation` signature)
- `src/artcb/governance/manager.py` L539 (`user_key_rotation` signature)
- Pattern existant : `cast_vote` L84-100 dans `governance_routes.py`

**Status :** [ ] pending

---

## Sous-tâche 3 — Ajouter les endpoints status/blocks manquants (404 dans logs)

**Intent :** Les logs Replit montrent des 404 pour `/api/v1/chain/status`,
`/api/v1/node/status`, et `/api/v1/chain/blocks`. Ces routes sont appelées par des
clients externes (monitoring, explorateur). Ajouter des routes minimales qui retournent
les informations pertinentes depuis les sources existantes.

**Expected Outcomes :**
- `GET /api/v1/chain/status` retourne 200 avec hauteur de chaîne, hash du dernier bloc, timestamp
- `GET /api/v1/node/status` retourne 200 avec node_id, version, uptime
- `GET /api/v1/chain/blocks` retourne 200 avec la liste des blocs (alias de `/api/v1/chain`)

**Todo List :**
1. Lire `src/api/routes.py` — identifier les données disponibles via `state.chain`
2. Ajouter `GET /chain/status` dans `routes.py` — utiliser `state.chain.verify()` et
   `state.chain.list_blocks()` pour construire la réponse
3. Ajouter `GET /chain/blocks` comme alias de `GET /chain` (redirect ou réimplémentation simple)
4. Ajouter `GET /node/status` — retourner `node_id` depuis `state.p2p` si disponible,
   sinon construire depuis `hostname` + version API

**Relevant Context :**
- `src/api/routes.py` L312-336 (routes chain existantes)
- `src/api/routes.py` L83-98 (`health` — pattern à suivre)
- `src/api/p2p_routes.py` L31 (`/status` — source du `node_id`)

**Status :** [ ] pending

---

## Sous-tâche 4 — Corriger POST /api/v1/ir/learn (405 dans les tests P2P)

**Intent :** Le script de test `scripts/test_replit_p2p_reel.py` utilise
`POST /api/v1/ir/learn` qui retourne 405 (Method Not Allowed). La route correcte est
`POST /api/v1/store` avec `text` + `visibility`. Créer un alias `POST /api/v1/ir/learn`
qui accepte `{wallet_address, content, visibility}` et appelle la logique de store.
Cela permettra au test de miner des blocs réels (étapes "N1 ir/learn" et "N1 bloc PUBLIC gravé").

**Expected Outcomes :**
- `POST /api/v1/ir/learn` retourne 200 avec `graph_id`
- Le script de test P2P passe de 22/25 à 25/25 étapes OK
- `bloc_mine_n1: true` et `sync_n2_received_public: true` dans les conclusions

**Todo List :**
1. Lire `src/api/routes.py` lignes 187-310 (POST /store — logique existante)
2. Créer un modèle `LearnRequest` avec `wallet_address`, `content`, `visibility`
3. Implémenter `POST /ir/learn` dans `routes.py` — encode le contenu et appelle
   la logique de store, retourne `{"graph_id": ..., "block_index": ...}` si bloc gravé
4. Mettre à jour `scripts/test_replit_p2p_reel.py` pour utiliser la nouvelle route
   (ou l'adapter pour utiliser directement `/store` si l'alias n'est pas souhaité)

**Relevant Context :**
- `src/api/routes.py` L187 (`POST /store`)
- `scripts/test_replit_p2p_reel.py` L137-148 (appel `POST /api/v1/ir/learn`)
- `src/api/routes.py` L101-128 (`POST /encode` — pattern d'encodage)

**Status :** [ ] pending

---

## Sous-tâche 5 — Rapport + tests réels sur Replit supermicro20239 + push

**Intent :** Après toutes les corrections, rejouer les tests P2P réels sur le nouveau
nœud déployé (supermicro20239 = N2), mettre à jour le script de test pour le nouveau
déploiement, sauvegarder les résultats, rédiger un rapport dans `confidentiel/` et
pusher sur `main`.

**Expected Outcomes :**
- Fichier `logs/test_replit_p2p_reel_20260805.json` créé avec résultats niveau prod
- Score 25/25 ou explication claire pour chaque FAIL résiduel
- `conclusions.bloc_mine_n1: true` et `conclusions.sync_n2_received_public: true`
- Rapport `confidentiel/rapport_115_securite_rotation_signature_obligatoire_endpoints_2026-08-05.md`
- `git add -A && git commit -m "..." && git push origin main`

**Todo List :**
1. Mettre à jour `scripts/test_replit_p2p_reel.py` pour utiliser
   `https://lvx--supermicro20239.replit.app` comme N2 (déjà configuré) et
   `https://lvx--supermicro20238.replit.app` comme N1
2. Exécuter `python3 scripts/test_replit_p2p_reel.py` (les corrections doivent être déployées)
3. Analyser les résultats — identifier les FAILs résiduels
4. Rédiger rapport `confidentiel/rapport_115_...` avec :
   - Liste des failles corrigées (unsigned → obligatoire)
   - Endpoints ajoutés
   - Résultats tests P2P réels (avant/après)
   - Tests unitaires avant/après
5. Exécuter la suite de tests : `python3 -m pytest tests/ -v --tb=short`
6. Vérifier qu'aucun test ne régresse
7. `git add -A && git commit && git push origin main`

**Relevant Context :**
- `scripts/test_replit_p2p_reel.py` — script test P2P
- `logs/test_replit_p2p_reel_20260804.json` — résultats précédents (22/25)
- N2 déployé : `https://lvx--supermicro20239.replit.app`
- N1 (ancien) : `https://lvx--supermicro20238.replit.app`

**Status :** [ ] pending

---

## Notes importantes pour l'implémentation

### Sur la signature obligatoire

La vérification de signature dans `creator_key_rotation()` a un problème actuel :
le `now_str` est calculé DANS la méthode, donc le message signé par le client doit
utiliser le même timestamp. Une approche correcte : le client fournit aussi le
`timestamp` dans la requête REST, et la méthode utilise ce timestamp fourni (et
vérifié) plutôt que de calculer `now_str` lui-même. **Attention :** ceci est un
problème de design à résoudre dans la sous-tâche 2 (endpoint REST) — l'API doit
fournir un `challenge` signable au client, ou le client fournit le timestamp.

### Sur les tests

Avant toute modification des tests, vérifier le nombre exact de tests qui passent
actuellement : `python3 -m pytest tests/test_governance_rotation.py -v`

### Architecture des sous-tâches

Les sous-tâches 1 et 2 sont liées (modification du manager + endpoints),
les sous-tâches 3 et 4 sont indépendantes, la sous-tâche 5 dépend de toutes les autres.
