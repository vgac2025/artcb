# ARTCB — Intégration N8N

N8N est un outil d'automatisation de workflows. Avec ARTCB, tu peux créer des workflows qui gravent automatiquement des données dans la blockchain ou interrogent la mémoire collective.

## Architecture

```
N8N Workflow
    └── HTTP Request Node
            └── POST http://localhost:8000/api/v1/...
                        └── ARTCB API
```

ARTCB expose une API REST complète. N8N peut l'appeler directement avec le node **HTTP Request** intégré.

---

## Prérequis

1. ARTCB API lancée : `python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000`
2. N8N accessible (local ou cloud) : `npx n8n start`
3. Si N8N et ARTCB sont sur des machines différentes → utiliser l'IP publique ou ngrok pour exposer ARTCB

---

## Workflows prêts à l'emploi

### 1. Graver une donnée dans ARTCB

**Node : HTTP Request**
```
Method  : POST
URL     : http://localhost:8000/api/v1/store
Headers : Content-Type: application/json
Body    :
{
  "text": "{{ $json.message }}",
  "visibility": "public"
}
```

**Réponse :**
```json
{
  "block_index": 42,
  "pol_score": 0.87,
  "block_hash": "abc123...",
  "message": "Bloc gravé"
}
```

---

### 2. Mémo IA (graver une pensée avec score PoL)

```
Method  : POST
URL     : http://localhost:8000/api/v1/ai/memo
Body    :
{
  "text": "{{ $json.content }}",
  "memo_type": "observation",
  "visibility": "private"
}
```

---

### 3. Recherche sémantique dans la blockchain

```
Method  : GET
URL     : http://localhost:8000/api/v1/chain/search?q={{ $json.query }}&limit=5
```

**Réponse :** liste des blocs les plus pertinents avec score de similarité.

---

### 4. Importer une transaction Ethereum dans ARTCB

```
Method  : POST
URL     : http://localhost:8000/api/v1/bridges/import
Body    :
{
  "chain": "ethereum",
  "tx_hash": "{{ $json.eth_tx_hash }}"
}
```

---

### 5. Statut des bridges blockchain

```
Method  : GET
URL     : http://localhost:8000/api/v1/bridges/status
```

---

### 6. Créer un wallet ARTCB

```
Method  : POST
URL     : http://localhost:8000/api/v1/wallet/create
Body    :
{
  "name": "{{ $json.wallet_name }}"
}
```

---

## Exemple de workflow complet

**Déclencheur : Webhook N8N → Graver dans ARTCB → Notifier Telegram**

```
[Webhook] ──→ [HTTP Request: POST /api/v1/ai/memo] ──→ [Telegram Bot]
                        ↓
              block_index + pol_score retournés
              Telegram : "Bloc #42 gravé (PoL=0.87)"
```

---

## Utilisation via MCP HTTP (alternative)

Si tu préfères utiliser le protocole MCP directement depuis N8N :

```
Method  : POST
URL     : http://localhost:8001/mcp
Headers : Content-Type: application/json
Body    :
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "artcb_memo",
    "arguments": {
      "text": "{{ $json.message }}"
    }
  }
}
```

Le serveur MCP ARTCB écoute sur le port 8001 :
```bash
python -m src.artcb.mcp.server --http 8001
```

---

## Variables d'environnement utiles dans N8N

| Variable N8N | Valeur | Usage |
|-------------|--------|-------|
| `ARTCB_BASE_URL` | `http://localhost:8000` | URL de base API |
| `ARTCB_MCP_URL` | `http://localhost:8001` | URL MCP HTTP |

Définir dans N8N : **Settings → n8n Environment Variables**

---

## Node custom ARTCB (roadmap)

Un node N8N natif est prévu en Phase 14.2.2 — il permettra d'utiliser ARTCB directement depuis la palette de nodes N8N sans configuration HTTP manuelle. Voir [`ROADMAP_GENERAL_ARTCB`](../ROADMAP_GENERAL_ARTCB) jalon 14.2.2.
