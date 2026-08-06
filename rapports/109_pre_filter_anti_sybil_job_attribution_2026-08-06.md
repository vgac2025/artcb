# Rapport 109 — Pré-filtrage Anti-Sybil avant attribution de job
**Correction faille : wallets en cooldown exclus AVANT de recevoir un travail**

**Date :** 2026-08-06T24:00:00Z  
**Auteur :** Agent Bob  
**Commit :** pushed sur `main`  
**Tests :** 500/500 PASS | 8 skipped | +12 nouveaux tests

---

## 1. La faille — énoncé exact

**Avant ce rapport**, un wallet en cooldown (ayant miné il y a < 60s) pouvait :

1. Être inclus dans la liste des contributeurs d'un nouveau bloc
2. Recevoir un chunk de travail dans le pool distribué
3. Calculer, compresser, signer — **puis voir tout le bloc annulé** à cause de lui
4. Faire perdre leur travail à tous les autres contributeurs éligibles du même bloc

```
AVANT (bugué) :
  T=0s   Bob mine bloc #530
  T=5s   Coordinateur assemble équipe : alice, bob, carol, dave
           ← bob est inclus malgré cooldown = 5s
  T=35s  Bloc prêt → validate_block() → bob.elapsed=35s < 60s → REJET
           alice, carol, dave : 30s de travail perdu
           → La faute était au COORDINATEUR, pas à bob
```

---

## 2. La correction

**Règle :** Personne ne reçoit de job tant qu'il est dans sa limite de cooldown.

### Nouveau point d'entrée : `is_eligible()` dans [`anti_sybil.py`](src/artcb/security/anti_sybil.py)

```python
ok, reason = anti_sybil.is_eligible("artcb1bob")
# → (False, "wallet artcb1bob... en cooldown : 35s écoulées sur 60s requises (encore 25s)")
```

Vérifie **avant tout travail** :
1. Wallet blacklisté explicitement → refus
2. Réputation dégradée (taux rejet > 50%, min 1 bloc réel) → refus
3. Encore dans le cooldown → refus avec temps restant

### Nouveau point d'entrée : `filter_eligible_contributors()` dans [`anti_sybil.py`](src/artcb/security/anti_sybil.py)

```python
eligible, excluded = anti_sybil.filter_eligible_contributors(candidates)
# → eligible = [alice, carol, dave]
# → excluded = [{"address": "artcb1bob", "reason": "... en cooldown ..."}]
```

---

## 3. Les 4 points d'application dans le code

| Fichier | Où | Ce qui change |
|---------|-----|---------------|
| [`src/artcb/mining/pipeline.py:build_contributors()`](src/artcb/mining/pipeline.py) | Construction liste contributeurs | Filtre AVANT d'ajouter à la liste |
| [`src/artcb/mining/pipeline.py:run_from_text()`](src/artcb/mining/pipeline.py) | Appel `build_contributors()` | Passe `anti_sybil=self.chain.anti_sybil` |
| [`src/artcb/pool/service.py:create_job()`](src/artcb/pool/service.py) | Création job pool distribué | Filtre workers AVANT d'attribuer chunks |
| [`src/api/pool_routes.py:create_pool_job()`](src/api/pool_routes.py) | Route POST /pool/jobs | Passe `anti_sybil` depuis l'état applicatif |

---

## 4. Le flux corrigé

```
APRÈS (correct) :
  T=0s   Bob mine bloc #530 → bob.last_block_time = T+0s
  T=5s   Coordinateur veut assembler bloc #531
           anti_sybil.is_eligible("artcb1alice") → ✅ (3min depuis dernier bloc)
           anti_sybil.is_eligible("artcb1bob")   → ❌ (5s < 60s — "encore 55s")
           anti_sybil.is_eligible("artcb1carol") → ✅
           anti_sybil.is_eligible("artcb1dave")  → ✅
           → bob n'est PAS inclus dans la liste
           → bob ne reçoit AUCUN chunk
           → bob ne calcule RIEN
  T=35s  Bloc gravé avec alice, carol, dave uniquement → JAMAIS de rejet
```

---

## 5. Rétrocompatibilité

`build_contributors()` et `create_job()` fonctionnent exactement comme avant si `anti_sybil=None` (paramètre optionnel). Zéro régression.

---

## 6. Tests

**12 nouveaux tests** dans [`tests/test_anti_sybil_pre_filter.py`](tests/test_anti_sybil_pre_filter.py) :

| Test | Vérifie |
|------|---------|
| `test_is_eligible_never_mined` | Wallet sans historique = toujours éligible |
| `test_is_eligible_after_cooldown` | 90s > 60s → éligible |
| `test_is_eligible_in_cooldown` | 30s < 60s → inéligible + raison |
| `test_is_eligible_just_at_limit` | Exactement 60s → éligible |
| `test_is_eligible_suspended` | Blacklisté → inéligible |
| `test_filter_all_eligible` | Tous passent |
| `test_filter_removes_cooldown_wallet` | Bob retiré, alice+carol gardés |
| `test_filter_all_excluded_returns_empty` | Tous en cooldown → liste vide |
| `test_build_contributors_filters_cooldown` | bob exclu avant liste finale |
| `test_build_contributors_no_sybil_unchanged` | Rétrocompat sans anti_sybil |
| `test_pool_create_job_filters_cooldown_worker` | Chunks assignés uniquement aux éligibles |
| `test_pool_create_job_raises_if_no_eligible_worker` | PoolError explicite si 0 éligible |

**Total : 500/500 PASS | 8 skipped normaux**

---

**Avancement global : 98 % → 98.5 %**
