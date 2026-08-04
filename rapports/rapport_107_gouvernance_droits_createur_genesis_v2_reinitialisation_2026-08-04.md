# Rapport 107 — Gouvernance ARTCB, Droits Créateur et Réinitialisation Genesis v2

**Date :** 2026-08-04
**Branche :** main
**Commit précédent :** 3706859 (droits créateur, CREATOR_RIGHTS_CHARTER.md)
**Tests validés :** 447 passed (suite complète) ✅
**Environnement :** Python 3.12.3 · FastAPI · Ed25519 · ML-DSA-65 FIPS204

---

## 1. Contexte — Ce qui a été fait dans cette session

### 1.1 Droits absolus du créateur — implémentés et documentés

**Demande du fondateur :** En tant que créateur de la blockchain ARTCB, avoir
le droit absolu sur toutes les décisions de gouvernance, avec un compte qui possède
le maximum de poids de vote quelle que soit la quantité d'utilisateurs.

**Résultat :** Implémenté dans `src/artcb/governance/manager.py` :

| Mécanisme | Valeur | Comportement |
|---|---|---|
| Veto absolu (vote NON créateur) | Activé | 1 NON créateur = rejet immédiat, quelle que soit la majorité |
| Validation immédiate (vote OUI créateur) | Activé | 1 OUI créateur = acceptation immédiate |
| Poids de vote créateur | 999 999 voix | 1 vote créateur = 999 999 votes ordinaires |
| Blocage propositions anti-créateur | Activé | Mots-clés interdits bloquent la création |

**Simulation mathématique :**
- 10 000 000 utilisateurs votent OUI, créateur vote NON → **proposition REJETÉE** (veto absolu)
- 10 000 000 utilisateurs votent NON, créateur vote OUI → **proposition ACCEPTÉE** (validation immédiate)

### 1.2 Réinitialisation blockchain — Genesis v2

**Avant (v1) :** 5 comptes fondateurs égaux, 539 blocs, pas de droits créateur onchain.

**Après (v2) :** 2 comptes fondateurs, 1 genesis block, droits créateur gravés onchain.

| Étape | Action |
|---|---|
| Snapshot | 539 blocs sauvegardés hors-ligne (dossier confidentiel — non poussé) |
| Wallets v2 | `scripts/create_founders_wallets_v2.py` → 2 wallets générés |
| Genesis | `scripts/init_genesis.py` → nouveau genesis block v2 avec `creator_rights` |
| Résultat | `data/chain/blocks.jsonl` = 1 bloc (genesis v2) |

### 1.3 Allocation des 2 comptes fondateurs (remplacement des 5 founders v1)

| Compte | Allocation | Rôle |
|---|---|---|
| ARTCB Créateur | 1 000 000 ARTCB | Compte créateur — droits absolus de gouvernance |
| ARTCB Développement | 1 000 000 ARTCB | Compte dédié au développement et à l'infrastructure |
| **Total alloué** | **2 000 000 ARTCB** | **9.52% de la supply totale de 21 000 000 ARTCB** |

Les 5 anciens comptes fondateurs v1 (pondération égale) sont remplacés par ces 2 comptes.
Seul le compte Créateur possède le poids de vote 999 999 et le veto absolu.

---

## 2. Architecture technique des droits créateur

### 2.1 Fichiers créés ou modifiés

| Fichier | Type | Description |
|---|---|---|
| `src/artcb/governance/manager.py` | Modifié | Veto créateur + poids 999 999 + blocage propositions |
| `data/founders/creator_rights.json` | Nouveau | Référence publique de l'adresse créateur |
| `data/founders/founders_allocation_v2.json` | Nouveau | Allocation publique des 2 comptes fondateurs |
| `data/chain/blocks.jsonl` | Réinitialisé | Genesis v2 avec creator_rights gravés |
| `CREATOR_RIGHTS_CHARTER.md` | Nouveau | Charte publique des droits créateur |
| `scripts/create_founders_wallets_v2.py` | Nouveau | Script génération wallets fondateurs v2 |
| `scripts/init_genesis.py` | Nouveau | Script réinitialisation genesis v2 |
| `src/api/dashboard_routes.py` | Modifié | Route /founders/allocation → priorité v2 sur v1 |

### 2.2 Structure du genesis block v2

Le genesis block (bloc index 0) contient les champs suivants :

```
creator_rights :
  creator_wallet           : adresse publique du créateur (permanente)
  creator_veto_enabled     : true
  creator_vote_weight      : 999999
  creator_rights_immutable : true
  established_at           : 2026-08-04T...Z

initial_allocation :
  [adresse créateur]     : 1 000 000 ARTCB, rôle=creator
  [adresse dev]          : 1 000 000 ARTCB, rôle=development

protocol_constants :
  max_supply_artcb        : 21 000 000
  pol_threshold           : 0.6
  pqc_algorithm           : ML-DSA-65 FIPS204
  immutable               : true

mission_statement : "ARTCB : Construire la nouvelle internet,
  blockchain et facon de communiquer adaptee a l IA."
```

### 2.3 Logique de veto dans governance/manager.py

```python
# Extrait du moteur de vote — tally()
if creator_voted_yes:
    majority_accept = True   # Force l'acceptation quelle que soit la majorité
    majority_reject = False
elif creator_voted_no:
    majority_reject = True   # Force le rejet quelle que soit la majorité
    majority_accept = False
```

### 2.4 Protection anti-modification des droits créateur

La méthode `_validate_proposal_content()` bloque toute proposition contenant :
- `creator_wallet`, `creator_veto`, `creator_vote_weight`, `creator_rights`
- `remove creator`, `retirer createur`, `supprimer createur`

Ces termes déclenchent une `GovernanceError` avant même la création de la proposition.

---

## 3. Comparaison avec les blockchains existantes

| Blockchain | Veto fondateur technique | Poids fondateur | Position ARTCB |
|---|---|---|---|
| Bitcoin | Non (Satoshi disparu) | 0 | ARTCB supérieur |
| Ethereum | Non (influence sociale seulement) | 0 onchain | ARTCB supérieur |
| Cosmos | Partiel (33.4% NoWithVeto) | Proportionnel aux tokens | ARTCB supérieur |
| BNB Chain | De facto (Binance contrôle validateurs) | Centralisé | Comparable mais ARTCB plus transparent |
| Solana | Non (influence fondation) | 0 onchain | ARTCB supérieur |
| **ARTCB** | **OUI — absolu (100%)** | **999 999 voix** | **Position unique** |

**Observation :** ARTCB est la seule blockchain de cette liste où :
- Le veto fondateur est **onchain** (gravé dans le genesis block)
- Le veto est **absolu** (1 vote = décision finale, sans seuil de tokens)
- Les droits sont **immuables par code** (toute proposition qui les vise est bloquée)

---

## 4. Mesures de sécurité implémentées

### 4.1 Protection des secrets (clés privées)

| Secret | Stockage | Statut |
|---|---|---|
| Clé privée créateur | Doppler `artcb-blockchain/prd` | ✅ Sécurisé |
| Clé privée dev | Doppler `artcb-blockchain/prd` | ✅ Sécurisé |
| data/founders/founders_wallets_v2.json | .gitignore | ✅ Non poussé |
| Dossier confidentiel/ | .gitignore ligne 33 | ✅ Non poussé |

### 4.2 Protections .gitignore

```
data/founders/founders_wallets.json   # v1 — sensible
data/founders/*.key                   # clés
data/founders/*_private.json          # clés privées
confidentiel/                         # rapports et snapshots — JAMAIS sur GitHub
.env.backup*                          # backups .env
```

---

## 5. Améliorations recommandées (à implémenter avant mise en ligne)

Ces améliorations sont prioritaires mais ne bloquent pas le développement actuel :

### 5.1 Signature cryptographique du genesis block (CRITIQUE)

**Problème :** Le champ `creator_rights` dans `blocks.jsonl` n'est pas signé.
Un accès direct au fichier permettrait de modifier l'adresse créateur.

**Solution :** Signer le champ `creator_rights` avec la clé privée Ed25519 créateur
lors de `scripts/init_genesis.py`, et vérifier cette signature au démarrage de l'API.

### 5.2 Authentification des votes par signature wallet (HAUTE)

**Problème :** L'API `POST /api/v1/governance/vote` accepte une adresse wallet
sans vérifier que l'appelant possède la clé privée correspondante.

**Solution :** Exiger un champ `signature` dans la requête de vote :
la requête signée par la clé privée Ed25519 du wallet votant.

### 5.3 Interface UI vote créateur (MOYENNE)

**Problème :** Le créateur doit actuellement voter via l'API REST directement.

**Solution :** Ajouter un panel "Vote Créateur" dans le dashboard (visible uniquement
si le wallet connecté = adresse créateur).

### 5.4 Audit automatique des constantes immuables (BASSE)

**Solution :** Ajouter dans GitHub Actions un step vérifiant que `manager.py`
contient toujours `CREATOR_VOTE_WEIGHT = 999_999`.

---

## 6. Modifications frontend — Wallets et AgentMemory

### 6.1 Wallets.tsx — affichage adresse après création

**Avant :** L'adresse du wallet créé n'était pas affichée à l'utilisateur.
**Après :** L'adresse complète est affichée avec bouton copier, badge `[CREATEUR]`
pour le compte créateur, et panel "Importer un wallet existant".

### 6.2 AgentMemory.tsx — migration CSS global

**Avant :** Styles inline (`inp`, `btn()` helpers locaux).
**Après :** Classes CSS globales ARTCB (`mc-page`, `panel`, `toolbar`, `mc-console`).

### 6.3 Route /founders/allocation — priorité v2

La route `GET /api/v1/dashboard/founders/allocation` lit maintenant :
1. `founders_allocation_v2.json` en priorité (2 comptes — v2)
2. `founders_allocation.json` en fallback (5 founders — v1 legacy)

---

## 7. Tests et qualité

| Indicateur | Valeur |
|---|---|
| Tests unitaires | **447 PASS, 0 FAIL** |
| Tests PQC ML-DSA-65 | **12/12 PASS** |
| Erreurs TypeScript frontend | **0** |
| Build frontend | **OK** |
| Occurrences "VGACTech" dans les sources | **0** |
| Emojis dans frontend/src/ | **0** |

---

## 8. Fichiers poussés dans ce cycle (commit 3706859 + ce commit)

### Déjà pushés (commit 3706859)
- `src/artcb/governance/manager.py` — veto créateur
- `CREATOR_RIGHTS_CHARTER.md` — charte publique
- `data/founders/creator_rights.json` — référence publique
- `data/founders/founders_allocation_v2.json` — allocation publique
- `scripts/create_founders_wallets_v2.py` — script wallets
- `scripts/init_genesis.py` — script genesis
- `.gitignore` — confidentiel/ protégé
- Tous les fichiers VGACTech → ARTCB renommés

### À pousser dans ce commit
- `frontend/src/pages/Wallets.tsx` — affichage adresse + import + badge créateur
- `frontend/src/pages/AgentMemory.tsx` — CSS global MC
- `frontend/src/api/client.ts` — type createWallet corrigé
- `src/api/dashboard_routes.py` — founders v2 priority
- `frontend/dist/` — rebuild
- `rapports/rapport_107_*.md` — ce rapport

### Jamais poussés (confidentiel/)
- `confidentiel/rapport_108_analyse_complete_droits_createur_*.md`
- `confidentiel/rapport_createur_gouvernance_droits_absolus_*.md`
- `confidentiel/rapport_final_gouvernance_createur_genesis_v2_*.md`
- `confidentiel/snapshot_blockchain_avant_reset_20260804_014055/`

---

## 9. Vérification : confidentiel/ est-il protégé ?

```bash
$ git check-ignore -v confidentiel/rapport_108_*.md
.gitignore:33:confidentiel/    confidentiel/rapport_108_*.md
```

**✅ Confirmé : le dossier confidentiel/ est exclu de git par la règle ligne 33 du .gitignore.**

---

## 10. Prochaines étapes recommandées

| Priorité | Action | Impact |
|---|---|---|
| 1 — CRITIQUE | Signature Ed25519 du genesis block | Protection contre modification directe |
| 2 — CRITIQUE | Vérification intégrité creator_rights.json au démarrage | Détection tamper |
| 3 — HAUTE | Authentification vote par signature wallet | Sécurité votes |
| 4 — HAUTE | Panel UI vote créateur dans dashboard | UX fondateur |
| 5 — HAUTE | Backup hors-ligne clés fondateurs (GPG/AES-256) | Résilience |
| 6 — HAUTE | Nœuds P2P sur VPS dédié (non-Replit Autoscale) | Persistance données |
| 7 — MOYENNE | Domaine artcb.io + SSL | Production |

---

**© 2026 ARTCB — contact@artcb.io**
*Ce rapport est public et commité sur GitHub. Il fait partie de la documentation ARTCB.*
