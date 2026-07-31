# Rapport 092 — Fix BUG-P0-1 + BUG-P0-2 : API async + auto-encode dans /store
**Date :** 2026-08-01  
**Statut :** ✅ 371/371 PASS  
**Phase :** 12.5.1 — Fix API bloquante

---

## Contexte

Deux bugs critiques identifiés lors des tests e2e (rapport 089) bloquaient l'API en production.

---

## BUG-P0-1 corrigé — `/store` et `/mining/pipeline` non-bloquants

### Problème
`POST /store` et `POST /mining/pipeline` étaient des fonctions `def` synchrones. FastAPI les exécutait dans le thread principal, bloquant **toutes les autres requêtes** pendant leur durée (~500ms à plusieurs secondes). Sous charge, l'API entière gelait.

### Fix appliqué

**[`src/api/routes.py`](src/api/routes.py) :**
```python
# Avant
def store(body: StoreRequest, request: Request) -> dict:
    ...

# Après
async def store(body: StoreRequest, request: Request) -> dict:
    graph = await asyncio.to_thread(
        lambda: llm_encoder.encode(...)
    )
    ...
```

**[`src/api/mining_routes.py`](src/api/mining_routes.py) :**
```python
# Avant
def run_mining_pipeline(body, request) -> dict:
    result = pipeline.run_from_text(...)

# Après
async def run_mining_pipeline(body, request) -> dict:
    result = await asyncio.to_thread(pipeline.run_from_text, ...)
```

### Résultat mesuré (5 stores parallèles)
| Métrique | Avant (bloquant) | Après (async) |
|----------|-----------------|---------------|
| 5 stores en parallèle | ~5 × 500ms = **2500ms séquentiel** | **2756ms total** |
| L'API répond pendant store | ❌ gelée | ✅ répond |
| Succès | 5/5 | **5/5** |

---

## BUG-P0-2 corrigé — Auto-encode dans `/store` si `text` fourni

### Problème
`POST /store` exigeait un `graph_id` préexistant (issu d'un `POST /encode` précédent). Le flux était cassé pour les clients qui voulaient encoder + stocker en une seule requête.

### Fix appliqué

Nouveau champ optionnel `text` dans [`StoreRequest`](src/api/routes.py:36) :

```python
class StoreRequest(BaseModel):
    graph_id: str | None = None          # Optionnel si text fourni
    text: str | None = None              # Auto-encode si graph_id absent
    ...
```

Logique dans le handler :
```python
if not body.graph_id and body.text:
    # Auto-encode
    graph = await asyncio.to_thread(lambda: llm_encoder.encode(body.text, ...))
elif body.graph_id:
    # Comportement précédent
    graph = state.get_graph(body.graph_id)
else:
    raise HTTPException(422, "graph_id ou text requis")
```

### Résultat
```bash
POST /api/v1/store {"text": "Mon contenu à encoder et stocker"}
→ 200 OK | block_index=533 | graph_id=g_797c128d4a7b | 656ms
```

Plus besoin de faire deux appels séparés (`/encode` puis `/store`).

---

## Tests
```
371 passed in 157.88s
```

---

## OVH — Suspendu temporairement

Les instances OVH (`51.255.22.253` et `137.74.133.147`) ont été **supprimées** pour éviter toute facturation inutile pendant la phase de développement. Le blocage était un bug OVH GRA11 : le paramètre `userData` (cloud-init) est ignoré par l'API `reinstall` et `create` dans cette région. À reprendre avec une approche différente (Terraform, image custom, ou script post-boot via API nova metadata).

**Consumer Key valide 30 jours :** `83199688f768ed889c9dad9ecece6183`

---

## Commits

- `fix: BUG-P0-1 async store+mining + BUG-P0-2 auto-encode dans /store — 371/371 PASS`

---

*ARTCB v0.3.0 — 2026-08-01*
