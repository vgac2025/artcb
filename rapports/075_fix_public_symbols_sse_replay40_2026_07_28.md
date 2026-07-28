# Rapport 075 — Fix public_symbols + SSE + replay 40/40 ✅
**Date :** 2026-07-28 | **Branche :** main @ d9674f1  
**Précédent :** Rapport 074 @ 7c96268 — 31/31 avec 2 bugs silencieux

---

## 🔴 Bugs corrigés

### Bug #1 — CRITIQUE : `public_symbols` jamais gravés sur les blocs privés
**Root cause trouvée dans [`src/artcb/chain/manager.py:290`]**

```python
# AVANT (BUG) — public_symbols ignorés si visibility != "public"
public_symbols=dict(public_symbols) if public_symbols and visibility == "public" else {},

# APRÈS (CORRECT) — public_symbols toujours gravés
public_symbols=dict(public_symbols) if public_symbols else {},
```

**Impact :** tous les blocs `visibility="private"` (défaut des memos IA) avaient `public_symbols={}` → 
- `agent_id` → `"unknown"` (étape 6 du replay)
- `memo_type` → `"unknown"` (étape 10)
- `parent_block_index` absent → `children=0` (étape 9)
- `GET /ai/bugs/open` ne trouvait aucun bug (corrigé par chance — les blocs de test étaient successifs)

**Note importante :** la visibilité contrôle l'*accès* aux métadonnées (qui peut les voir), pas si elles sont *stockées*. Ce sont deux préoccupations distinctes — stocker ≠ exposer.

---

### Bug #2 — `MANUS_ID` toujours `None` dans le replay
**Root cause :** `POST /api/v1/connectors` retourne `{"connector": {...}, "message": "..."}` — le `connector_id` est imbriqué dans `connector.connector_id`, pas à la racine.

```python
# AVANT (BUG)
MANUS_ID = r.json().get("connector_id","")  # toujours ""

# APRÈS (CORRECT)
MANUS_ID = r.json().get("connector",{}).get("connector_id","") or r.json().get("connector_id","")
```

**Impact :** étapes 3 et 13 du replay skipaient systématiquement.

---

### Bug #3 — `test_connector()` rejetait `manus` et `google_ai`
**Root cause :** la liste des providers LLM dans `src/artcb/connectors/sources.py:328` ne contenait pas `manus` ni `google_ai` → tombait dans `fetch_learning_text()` → `Unsupported data source: manus`.

```python
# AVANT
if record.provider in {"openai", "anthropic", "bob", "openrouter", "ollama", "cursor", "watsonx"}:

# APRÈS
if record.provider in {"openai", "anthropic", "bob", "openrouter", "ollama", "cursor", "watsonx", "manus", "google_ai"}:
```

---

### Amélioration #4 — SSE heartbeat immédiat
Le générateur SSE envoyait d'abord `new_block` ou `heartbeat` selon l'état de la chaîne, mais ne garantissait pas un message immédiat à la connexion. Ajout d'un event `connected` avant la boucle principale.

---

## 📊 Avant / Après

| Métrique | Avant (074) | Après (075) |
|----------|-------------|-------------|
| Replay validations | 31/31 | **40/40** |
| `agent=unknown` | ❌ Oui | ✅ Non — `bob_write_replay` |
| `memo_type=unknown` | ❌ Oui | ✅ Non — `bug/fix/observation` |
| `children=0` pour bug+fix | ❌ Oui | ✅ `count=1` |
| MANUS_ID None | ❌ Oui | ✅ `conn_xxx` récupéré |
| test_connector manus | ❌ `Unsupported` | ✅ `200 OK` |
| SSE warnings | ⚠️ 1 | ✅ 0 |
| Working tree warning | ⚠️ 1 | ✅ 0 (logs exclus) |

---

## Fichiers modifiés

| Fichier | Modification |
|---------|-------------|
| `src/artcb/chain/manager.py` | L290 — supprimer condition `visibility == "public"` |
| `src/api/ai_routes.py` | Heartbeat immédiat dans `_event_generator()` |
| `src/artcb/connectors/sources.py` | Ajouter `manus` et `google_ai` dans la liste LLM |
| `scripts/replay_ia_autonome_v2.py` | Fix `connector_id`, SSE validation, Git dirty filter |

---

## État de la chaîne après le rapport
- **77 blocs valides** — ML-DSA-65 + Ed25519
- **40 memos IA gravés** (depuis les replays)
- **0 bug ouvert** dans le scope du replay
- **Commit :** `d9674f1` — branche `main`

---

## Prochaines étapes (P2)
1. **Anti-Sybil pour memos IA** — les blocs rapides (< 60s) devraient utiliser un wallet dédié par session au lieu du fallback sans contributors
2. **IR Engine v0.2** — grammaire enrichie, langage autonome sans texte humain
3. **Wikipedia connector** — implémentation manquante (ROADMAP Phase 4)
4. **WatsonX project_id** — documenter dans `.env.example`
5. **i18n complet** — 238 clés × 7 langues sur les 14 pages restantes

---

*Rapport généré automatiquement — PROTOCOLE_ARTCB zéro mock, zéro dette technique*
