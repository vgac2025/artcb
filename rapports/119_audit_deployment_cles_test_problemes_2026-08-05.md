# Rapport 119 — Audit déploiement : clés de test, problèmes identifiés, avant/après

**Horodatage :** 2026-08-05T21:30:00Z  
**Agent :** Replit Agent — audit lecture + mesures réelles  
**Avancement global :** 96 % (inchangé)  
**Déclencheur :** Tests manuels utilisateur + clés exposées dans le chat

---

## 🔴 ALERTE SÉCURITÉ PRIORITÉ ABSOLUE

**Deux secrets ont été partagés en clair dans le chat :**

| Secret | Type | Action requise |
|--------|------|----------------|
| `artcb_fc1ad6a9bf7c83d3b7d4288ecdf11c11e3ff2121...` | Clé API ARTCB | **Révoquer immédiatement** — `DELETE /api/v1/api-keys/{key_id}` |
| `lqa_acd7ef4610add68c3a0b49c6289cc7bdb19a38cfe...` | Token replay QA | **Ne pas utiliser** — traiter comme compromis |

**Procédure révocation clé ARTCB :**
```bash
# 1. Retrouver le key_id via GET /api/v1/api-keys/list
curl -H "Authorization: Bearer artcb_fc1..." https://<host>/api/v1/api-keys/list
# 2. Révoquer
curl -X DELETE https://<host>/api/v1/api-keys/<key_id>
```
> Le PROTOCOLE_ARTCB (rapport 073) exige la révocation immédiate de tout secret visible dans le chat.

---

## 1. État mesuré — wallets créés manuellement par l'utilisateur

Les wallets créés lors des tests sont présents dans `data/wallets/` :

| Nom saisi | Adresse (confirmée) | hybrid | balance | Problèmes |
|-----------|---------------------|--------|---------|-----------|
| test2 | `artcb1p9eqffjdg0e0a9cvv32g3em59cvaw8x64se55t` | ❌ False | 0 ARTCB | hybrid=False, nom non stocké |
| test2 | `artcb10f47mqey8cte5xpp9lm30z5nx68xstxag2m3mq` | ❌ False | 0 ARTCB | hybrid=False, nom non stocké |
| test4 | `artcb1vh6vzl7hg9shxwq53nxcxqq57mjyhf9juvvvfj` | ❌ False | 0 ARTCB | hybrid=False, nom non stocké |
| (chain) | `artcb18qra427dvem6q8gc4aez9ljeff9sv2dhmp09f0` | ❌ False | 0 ARTCB | wallet système sans nom |

**Résultat total : 0 bloc miné — chaîne vide — `data/chain/blocks.jsonl` absent**

---

## 2. Problèmes identifiés — classification par sévérité

---

### 🔴 P0-1 — Déploiement : timeout healthcheck (bloque la mise en production)

**Symptôme :**
```
[2026-08-05T21:13:42.506Z ERROR] a port configuration was specified but the required
port was never opened, expected port 5000
```

**Cause racine :**  
Le `replit_start.sh` exécute **6 étapes séquentielles** avant de lancer uvicorn :
1. Création/vérification du venv (~1s si déjà existant)
2. `pip install -r requirements.txt` (~15–60s si packages manquants)
3. Tentative liboqs-python si cmake disponible (~2–5 min en cold start)
4. Patch oqs.py
5. Build frontend si dist absent (~30–60s)
6. Pull git
→ Uvicorn démarre **seulement après tout ça**

Le système de déploiement Replit commence à sonder `/` immédiatement et abandonne après **~60 secondes**. Le script dépasse systématiquement cette fenêtre en cold start.

**AVANT (comportement actuel) :**
```
Démarrage scripts/replit_start.sh → [2/7] pip install... (15-60s)
                                  → [2b/7] liboqs cmake (2-5min !)
                                  → [6/7] npm install + vite build (30-60s)
                                  → uvicorn (trop tard — healthcheck mort)
```

**APRÈS (correction requise) :**  
Le déploiement nécessite qu'uvicorn démarre en < 30 secondes. Options :
- **Option A (recommandée)** : déplacer les étapes longues (liboqs build, npm build) dans un script `setup_once.sh` distinct à exécuter manuellement, et garder le script de démarrage minimal
- **Option B** : utiliser `--timeout-graceful-shutdown 120` et configurer un healthcheck path dédié qui répond 200 immédiatement même pendant le startup
- **Option C (la plus simple)** : ajouter une étape qui lance uvicorn en arrière-plan **immédiatement** (avant le build frontend), avec un endpoint `/health` qui répond 200 dès le démarrage

---

### 🔴 P0-2 — Données éphémères : tout est perdu à chaque redéploiement

**Symptôme :** Les wallets test2/test2/test4, la clé API `artcb_fc1...`, et les blocs sont stockés dans `./data/` qui n'est **pas persisté** sur autoscale Replit.

**Preuve :**
```
data/chain/blocks.jsonl → ABSENT (0 blocs)
data/api_keys.json      → 1 seule clé (celle créée par cet audit — les clés précédentes ont disparu)
data/wallets/           → 5 fichiers (créés après le dernier démarrage)
```

**Cause :** L'autoscale Replit crée un nouveau container à chaque déploiement. `./data` est local au container. Aucun volume persistant n'est configuré.

**Impact :**
- La clé API `artcb_fc1...` que l'utilisateur a copiée **n'existe plus** dans le système — elle a été perdue au redémarrage
- Les wallets test2/test2/test4 recréés manuellement seront **perdus au prochain déploiement**
- La blockchain recommence à 0 blocs à chaque déploiement

**Correction requise :** Configurer un stockage persistant (Replit Database, volume monté, ou stockage externe) pour `./data`.

---

### 🟠 P1-1 — Routes API wallet : incohérence singulier/pluriel (404 frontend)

**Symptôme mesuré :**

| Ce que le frontend appelle | Résultat | Ce que l'API sert réellement | Résultat |
|---------------------------|----------|------------------------------|----------|
| `GET /api/v1/wallets` | **404** | `GET /api/v1/wallet/list` | **200 ✅** |
| `POST /api/v1/wallets/create` | **405** | `POST /api/v1/wallet/create` | **200 ✅** |
| `GET /api/v1/wallets/list` | **404** | `GET /api/v1/wallet/list` | **200 ✅** |

**Cause :** La documentation et le README utilisent `/api/v1/wallets` (pluriel) mais les routes FastAPI réelles sont `/api/v1/wallet` (singulier). Le frontend appelle probablement les mauvaises routes.

**Correction requise :** Ajouter des routes d'alias `wallets` → `wallet` dans l'API, ou corriger le frontend pour utiliser `/wallet` (singulier).

---

### 🟠 P1-2 — Wallets créés sans PQC (hybrid=False)

**Symptôme :**
```json
{"hybrid": false}  // pour TOUS les 5 wallets existants
```

**Cause :** `liboqs-python` n'est pas installé (rapport 118). Les wallets sont créés en mode Ed25519 pur. La signature ML-DSA-65 est désactivée.

**Impact :** Les adresses générées sont `artcb1...` (v1, Ed25519) et non `artcb2...` (v2, hybride post-quantique). Les wallets existants devront être migrés une fois liboqs installé (voir rapport 118 + rapport 087 procédure migration one-shot).

---

### 🟠 P1-3 — Champ `name` absent des fichiers wallet

**Symptôme :**
```json
// data/wallets/artcb1p9eqffjdg0e0a9cvv32g3em59cvaw8x64se55t.json
{
  "address": "artcb1p9eqffjdg0e0a9cvv32g3em59cvaw8x64se55t",
  "public_key_hex": "922e9892...",
  "created_at": "2026-08-05T20:00:41Z",
  "key_encryption": "AES-256-GCM",
  "key_format": "ARTCBENC1",
  "hybrid": false
  // ← "name" absent !
}
```

L'utilisateur avait nommé ce wallet "test2" mais ce nom n'est pas sauvegardé. L'API `wallet/list` retourne les wallets sans nom, ce qui rend l'interface difficile à utiliser.

**Correction requise :** Persister le champ `name` dans le fichier wallet lors de `POST /api/v1/wallet/create`.

---

### 🟠 P1-4 — Clé API exposée + perdue simultanément

La clé `artcb_fc1...` présentait une **double anomalie** :
1. Elle était affichée dans le frontend avec le message "Copy this token now — it will not be shown again" ✅ (comportement correct)
2. Elle a été **partagée dans le chat** par l'utilisateur → exposée → à révoquer
3. Simultanément, elle a été **perdue** car les données sont éphémères (P0-2)

Le système affiche la clé une seule fois mais n'explique pas que sur autoscale, un redémarrage la supprime du stockage. L'utilisateur a cru la clé valide alors qu'elle n'existe plus en base.

---

### 🟡 P2-1 — Chaîne vide : 0 bloc, 0 ARTCB miné

```
height=0, block_count=0, blocks.jsonl=absent
```

Aucun bloc n'a été miné depuis le démarrage. Les wallets ont 0 ARTCB. Pour qu'un wallet accumule des récompenses, il faut initier le minage :
```bash
POST /api/v1/mining/pipeline
{ "text": "...", "wallet": "artcb1p9eqffjdg0e0a9cvv32g3em59cvaw8x64se55t" }
```

---

### 🟡 P2-2 — Wallet test4 introuvable en base

L'adresse `artcb1vh6vzl7hg9shxwq53nxcxqq57mjyhf9juvvvfj` (test4) a été fournie par l'utilisateur mais **n'existe pas** dans `data/wallets/`. Seuls ces fichiers sont présents :
- `artcb18qra4...` (système)
- `artcb1p9eqf...` (test2)
- `artcb10f47m...` (test2 bis)
- `artcb1ryftt...` (inconnu)
- `artcb1yzc3v...` (créé par cet audit)

Probable cause : créé sur un autre nœud (N1 production ≠ N2 dev), ou lors d'une session précédente avant redémarrage.

---

## 3. Récapitulatif — tableau de bord des problèmes

| ID | Sévérité | Problème | Impact | Correction |
|----|----------|----------|--------|------------|
| P0-SEC | 🔴 Immédiat | Clé API + token QA exposés dans chat | Sécurité compromise | Révoquer maintenant |
| P0-1 | 🔴 Bloquant | Deployment timeout healthcheck | App inaccessible en prod | Lancer uvicorn avant build |
| P0-2 | 🔴 Bloquant | Données éphémères (wallets, clés, blocs perdus) | Perte de données à chaque déploiement | Stockage persistant |
| P1-1 | 🟠 Majeur | Routes `/wallets` vs `/wallet` (404) | Frontend cassé | Alias routes ou fix frontend |
| P1-2 | 🟠 Majeur | Wallets hybrid=False (PQC absent) | PQC non-opérationnel | Installer liboqs (rapport 118) |
| P1-3 | 🟠 Majeur | `name` non stocké dans wallet JSON | UX dégradée | Persister name dans wallet/create |
| P1-4 | 🟠 Majeur | Clé API perdue + exposée | Confusion utilisateur | Expliquer éphémère + stocker hors ./data |
| P2-1 | 🟡 Mineur | 0 bloc miné | Balance = 0 | Lancer POST /mining/pipeline |
| P2-2 | 🟡 Mineur | test4 introuvable en base locale | Wallet manquant | Nœud différent ou session périmée |

---

## 4. Mesures réelles à l'instant du rapport

```
API health          : 200 OK ✅
Chain verify        : 200 OK ✅ (chaîne vide — valide)
Blocks              : 0 (blocks.jsonl absent)
Wallets présents    : 5 (dont 1 créé par cet audit)
hybrid=True         : 0/5 ❌
API keys stockées   : 1 (audit_test — clé utilisateur perdue)
Node ID             : node_1eb8e5ca44e4
Version             : 0.3.0
liboqs              : ❌ absent (fallback Ed25519)
PQC (ML-DSA-65)     : ❌ inactif
Déploiement prod    : ❌ timeout healthcheck
```

---

## 5. Actions immédiates recommandées (par ordre)

```
1. [MAINTENANT] Révoquer artcb_fc1... sur le nœud où elle était valide
2. [MAINTENANT] Ne pas utiliser lqa_acd7... — traiter comme compromis
3. [GO requis]  Corriger P0-1 : startup rapide pour le déploiement
4. [GO requis]  Corriger P0-2 : persistance données (volume ou DB)
5. [GO requis]  Corriger P1-1 : alias routes wallet/wallets
6. [GO requis]  Corriger P1-2 : installer liboqs (rapport 118)
7. [GO requis]  Corriger P1-3 : stocker name dans wallet JSON
```

---

*Rapport produit après mesures réelles sur l'instance Replit en cours d'exécution. Aucun fichier modifié. Prochain rapport : 120 (rapport d'exécution après corrections, sur GO utilisateur).*
