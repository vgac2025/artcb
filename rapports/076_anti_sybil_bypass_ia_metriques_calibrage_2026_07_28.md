# Rapport 076 — Anti-Sybil Bypass IA + Métriques Calibrage Dynamique
**Date :** 2026-07-28 | **Branche :** main @ 2639237  
**Précédent :** Rapport 075 @ e4f2fbc — 40/40 ✅

---

## 🎯 Objectif

Étudier l'usage réel des blocs IA sans limitation pour calibrer la future limite anti-Sybil sur des données réelles — sans supprimer la sécurité, sans créer de blocage excessif qui pourrait compromettre les utilisateurs.

**Principe :** désactiver ≠ supprimer. La ligne de sécurité reste, mais configurable dynamiquement.

---

## Architecture implémentée

### 3 modes Anti-Sybil (configurables via `.env` ou à chaud via API)

| Mode | Variable | Effet |
|------|----------|-------|
| **Normal (prod)** | `ARTCB_ANTI_SYBIL_AI_BYPASS=false` | Rate-limit 60s actif pour tout le monde |
| **Bypass IA (étude)** | `ARTCB_ANTI_SYBIL_AI_BYPASS=true` | Rate-limit désactivé pour blocs IA seulement — métriques collectées |
| **Study global** | `ARTCB_ANTI_SYBIL_STUDY_MODE=true` | Rate-limit désactivé pour TOUS — métriques collectées |

**Ce qui reste TOUJOURS actif (invariant sécurité) :**
- PoL minimum 0.6 (bloque les blocs de mauvaise qualité)
- Maximum 10 contributeurs par bloc
- Blacklist / adresses suspectes
- Détection adresses dupliquées

---

### Nouveaux fichiers

| Fichier | Contenu |
|---------|---------|
| `src/artcb/security/anti_sybil.py` | Anti-Sybil rewritten : bypass IA, `AntiSybilMetrics`, `RateLimitMetric` |
| `src/api/security_routes.py` | 3 endpoints : config GET/POST, métriques GET |
| `.env.example` | Documentation des variables anti-Sybil |

### Nouveaux endpoints

```
GET  /api/v1/security/anti-sybil/config   — config actuelle (bypass, study, limites)
POST /api/v1/security/anti-sybil/config   — modifier à chaud (en mémoire)
GET  /api/v1/security/anti-sybil/metrics  — métriques usage réel + recommandation
```

---

## Métriques Anti-Sybil — ce que mesure le système

Pour chaque tentative de bloc (que ce soit bypassé ou non), le système enregistre :

```json
{
  "address": "artcb1gcqlzs…",
  "block_index": 85,
  "elapsed_s": 0.52,         // temps depuis le dernier bloc de cette adresse
  "would_reject": true,       // aurait été rejeté avec la limite 60s ?
  "limit_s": 60.0,            // limite au moment de la tentative
  "bypass": true,             // bypassé grâce au mode IA ?
  "source": "ai:memo:observation"
}
```

### Distribution des intervalles réels (1ère run — 3 échantillons)

```
min=0.51s | p50=0.52s | p90=0.55s | max=0.55s
```

**Interprétation :** l'agent IA grave des blocs toutes les ~0.5s lors des replays. La limite actuelle de 60s rejette 100% de ces blocs → sans le bypass, le fallback sans contributors était activé → blocs non signés.

---

## Recommandation dynamique de calibrage

La méthode `_recommend_limit()` calcule automatiquement :

```
Logique : rejeter seulement les <5% les plus rapides (queue basse de distribution)
Formule : p5 = 5ème percentile des intervalles observés, arrondi au multiple de 5s
```

**Avec les données actuelles (3 samples) :** `insufficient_data` — il faut ≥5 intervalles.

**Procédure recommandée :**
1. `ARTCB_ANTI_SYBIL_AI_BYPASS=true` dans `.env` → démarrer le serveur
2. Utiliser normalement pendant quelques heures
3. Consulter `GET /api/v1/security/anti-sybil/metrics` → `recommendation.suggested_limit_s`
4. Quand `sample_count >= 50` → recommandation statistiquement fiable
5. Appliquer `ARTCB_MIN_BLOCK_INTERVAL_SEC=<valeur_suggérée>` dans `.env`
6. Désactiver le bypass → `ARTCB_ANTI_SYBIL_AI_BYPASS=false`

---

## Modifications de code

### `ai_routes.py` — suppression du fallback sans contributors

```python
# AVANT (dette technique)
try:
    block = state.chain.append_block(contributors=contributors, ...)
except Exception as exc:
    if "too fast" in str(exc):
        # fallback sans signature = bloc non signé !
        block = state.chain.append_block(contributors=None, ...)

# APRÈS (propre)
block = state.chain.append_block(
    contributors=contributors,
    source=f"ai:memo:{body.memo_type}",  # ← permet le bypass anti-Sybil
    ...
)
```

### `chain/manager.py` — `source` passé à `validate_block()`

```python
def append_block(self, ..., source: str = "unknown") -> ChainBlock:
    valid, reason = self.anti_sybil.validate_block(
        contributors, pol_score, index, source=source
    )
    # Slashing désactivé si bloc IA bypassé
    bypass_active = (self.anti_sybil.ai_bypass and is_ai) or self.anti_sybil.study_mode
    if not valid and not bypass_active:
        # slash seulement pour de vraies attaques
        ...
```

---

## Résultats du test direct

```
4 memos IA gravés en ~2s (intervalles ~0.5s)
→ 0 SLASH  |  0 hard_rejected  |  100% bypass_rate
→ Tous les blocs sont signés avec le wallet agent_security_test ✅
→ Métriques enregistrées : 3 intervalles observés (0.51s, 0.52s, 0.55s)
```

---

## Replay

**40/40 ✅ | 0 ❌ | 0 SLASH | Blocs 77–92 gravés signés**

---

## État actuel `.env`

```env
ARTCB_MIN_BLOCK_INTERVAL_SEC=60      # limite de référence (inchangée)
ARTCB_ANTI_SYBIL_AI_BYPASS=true      # ← ACTIF — blocs IA libres, métriques collectées
ARTCB_ANTI_SYBIL_STUDY_MODE=false    # mode global désactivé (prod: rate-limit normal)
```

---

## Prochaines étapes

1. **Accumuler des données** — utiliser le système pendant 24–48h avec bypass actif
2. **Consulter la recommandation** — `GET /api/v1/security/anti-sybil/metrics` → `recommendation.suggested_limit_s`
3. **Calibrer** — appliquer la limite suggérée + désactiver le bypass
4. **Monitorer** — si des utilisateurs légitimes sont bloqués → remonter la limite ou déclencher le bypass par clé API

---

*Rapport généré automatiquement — PROTOCOLE_ARTCB zéro mock, zéro dette technique*
