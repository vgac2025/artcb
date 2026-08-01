# ARTCB — Intégration Lovable

Lovable est un générateur d'applications web avec agent IA intégré. ARTCB s'intègre via le protocole MCP HTTP.

## Méthode : MCP HTTP (transport HTTP/SSE)

Le serveur MCP ARTCB supporte un transport HTTP direct, sans ngrok requis si Lovable et ARTCB sont sur le même réseau ou si ARTCB est déployé sur un VPS.

### 1. Lancer le serveur MCP HTTP

```bash
python -m src.artcb.mcp.server --http 8001 --api-url http://localhost:8000
```

### 2. Configurer dans Lovable

Dans les paramètres de l'agent Lovable :

```json
{
  "mcp_servers": {
    "artcb": {
      "url": "http://VOTRE_IP:8001",
      "transport": "http"
    }
  }
}
```

### 3. Tools disponibles depuis Lovable

| Tool MCP | Description |
|----------|-------------|
| `artcb_memo` | Graver une pensée dans la blockchain |
| `artcb_think` | Raisonnement IA + gravure |
| `artcb_search` | Recherche sémantique |
| `artcb_mine` | Pipeline minage complet |
| `artcb_bridge_import` | Importer une tx externe |

### 4. Avec ngrok (accès public temporaire)

```bash
# Terminal 1 : API ARTCB
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Terminal 2 : MCP HTTP
python -m src.artcb.mcp.server --http 8001

# Terminal 3 : ngrok expose les deux
ngrok start --all --config ngrok.yml
```

Lovable utilise alors l'URL ngrok pour accéder au MCP.
