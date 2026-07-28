# Rapport 078 — inject_context chaque prompt + block-sizes + tokenomics
**Date :** 2026-07-28 | **Branche :** main  
**Précédent :** Rapport 077 @ 35c2fdc  
**Replay :** 48/48 ✅ | 0 ❌ | 0 SLASH

---

## Demande utilisateur — ce qui a été implémenté

> *"le contexte doit se faire à chaque fois que tu reçois un nouveau prompt et pas que au début de session"*

→ **Implémenté :** `inject_context=True` (défaut) sur `POST /ai/memo` **ET** `POST /ai/think`.  
L'agent ne repart plus jamais de zéro, même en milieu de conversation.

---

## 1. `inject_context=True` — contexte automatique à chaque prompt

### Comportement

| Avant | Après |
|-------|-------|
| L'agent oubliait tout entre deux prompts | Chaque prompt contient un snapshot du contexte |
| `/ai/context` devait être appelé manuellement | Injection automatique, transparente, gravée dans le bloc |
| Un agent relancé était aveugle | L'agent sait immédiatement : hauteur chaîne, bugs ouverts, derniers memos |

### Ce qui est injecté dans chaque prompt

```
[ARTCB CONTEXT — 2026-07-28T15:14:46Z]
Chain: 519 blocs | 480 memos IA
Bugs ouverts: #109, #175, #201
Tes 5 derniers memos:
  [lesson #507] 2026-07-28 [knowledge_base,rapport]
  [observation #516] 2026-07-28
  [bug #517] 2026-07-28
  [fix #518] 2026-07-28 [memory,fix,public_symbols]
  [observation #519] 2026-07-28
[FIN CONTEXTE — continue depuis ici]
```

### Paramètres modifiés

`MemoRequest` et `ThinkRequest` acceptent maintenant :
```python
inject_context: bool = True  # défaut ON → l'agent se souvient toujours
                              # False → prompt brut (utile pour tests unitaires)
```

### Fonction `_build_context_snippet()`

Nouvelle fonction helper dans [`src/api/ai_routes.py`](src/api/ai_routes.py) :
- Lit la chaîne en O(n) une seule fois
- Compact : 5 memos max, 1 ligne par memo — ne pollue pas le prompt
- Non bloquant : si erreur → snippet vide, le prompt passe quand même
- Inclut toujours : hauteur chaîne, bugs ouverts, derniers memos de cet agent

---

## 2. `GET /api/v1/chain/block-sizes` — taille des blocs + tokenomics

### La taille d'un bloc affecte-t-elle les coins disponibles ?

**NON.** Le reward est calculé uniquement depuis l'**index** du bloc :

```
halvings = block_index // 210_000
reward = 1 ARTCB >> halvings
```

Un bloc de 622 octets et un bloc de 665 Ko reçoivent **le même reward** au même index.

### Ce qui affecte RÉELLEMENT les coins

| Facteur | Impact |
|---------|--------|
| `block_index` | Détermine l'époque (halving) |
| Nombre de `contributors` | Split du reward entre participants |
| `pol_score` des contributors | Pondération du split (proportionnel au PoL) |
| `block_size_bytes` | **AUCUN impact** sur le reward |
| `visibility` (private/public) | **AUCUN impact** sur le reward |

### Table des halvings ARTCB

| Blocs | Reward/bloc | Époque |
|-------|-------------|--------|
| 0 → 209 999 | 1 ARTCB | 0 (actuel) |
| 210 000 → 419 999 | 0.5 ARTCB | 1 |
| 420 000 → 629 999 | 0.25 ARTCB | 2 |
| … | … | … |
| ≥ halving 64 | 0 ARTCB | — |
| **Total supply max** | **21 000 000 ARTCB** | — |

### État actuel de la chaîne (520 blocs)

```json
{
  "block_count": 520,
  "mined_artcb": 814.0,
  "mined_pct": 0.003876,
  "remaining_artcb": 20999186.0,
  "current_epoch": 0,
  "current_reward_artcb": 1.0,
  "next_halving_at_block": 210000,
  "blocks_until_halving": 209480
}
```

### Distribution des tailles

```
min = 622 B    (bloc mémo court)
avg = 28 380 B (environ 28 Ko)
max = 665 671 B (document long ingéré)
p50 (médiane) : ~14 Ko
p90 : ~68 Ko
```

**Buckets :**
```
<1KB    : 9 blocs    (memos courts)
1-10KB  : 44 blocs   (memos standards)
10-100KB: 450 blocs  (memos avec graphes IR)
100KB-1MB: 17 blocs  (knowledge base ingérée)
>1MB    : 0 blocs
```

### Comment la taille est calculée ?

```python
# Dans ChainBlock.to_json_line() — src/artcb/chain/manager.py
line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
payload["block_size_bytes"] = len(line.encode("utf-8"))
return json.dumps(payload, ...)
```

Chaque nouveau bloc stocke `block_size_bytes` directement dans sa propre ligne JSONL.  
Pour les blocs anciens (avant Rapport 078) : recalcul à la volée depuis le JSON.

**Décomposition d'un bloc type (28 Ko) :**
```
header         : ~600 B   (index, hash, signature, timestamp…)
contributors[] : ~800 B   (1 contributor avec signature ML-DSA-65 + Ed25519)
public_symbols : ~27 Ko   (graphe IR encodé, contenu texte, métadonnées IA)
```

---

## Fichiers modifiés

| Fichier | Modification |
|---------|-------------|
| `src/api/ai_routes.py` | `_build_context_snippet()` + `inject_context` dans MemoRequest/ThinkRequest + `chain_block_sizes()` |
| `src/artcb/chain/manager.py` | `block_size_bytes` gravé dans `to_json_line()` |
| `scripts/replay_ia_autonome_v2.py` | Étapes 14 (inject_context) + 15 (block-sizes) ajoutées |

---

## Avant / Après

| Étape replay | Avant | Après |
|---|---|---|
| Total validations | 40/40 | **48/48** |
| inject_context validé | — | **✅ étape 14** |
| block-sizes validé | — | **✅ étape 15** |
| `_build_context_snippet` importable | — | **✅ étape 16** |

---

*Rapport généré automatiquement — PROTOCOLE_ARTCB zéro mock, zéro dette technique*
