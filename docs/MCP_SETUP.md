# ARTCB — Guide d'installation MCP

Le serveur MCP ARTCB permet à n'importe quel agent IA (Bob, Cursor, Claude, VSCode) d'interagir directement avec la blockchain ARTCB.

## Prérequis

```bash
# 1. Lancer l'API ARTCB
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000

# 2. Vérifier que l'API répond
curl http://127.0.0.1:8000/api/v1/health
```

---

## Bob IDE

Fichier : [`.bob/mcp.json`](.bob/mcp.json) — déjà configuré.

L'agent Bob peut utiliser directement :
- `artcb_memo` — graver une pensée
- `artcb_think` — raisonner et graver
- `artcb_search` — recherche sémantique
- `artcb_mine` — pipeline minage complet

---

## Cursor

Fichier : [`.cursor/mcp.json`](.cursor/mcp.json) — déjà configuré.

Aucune action requise. Relancer Cursor pour activer.

---

## VSCode

Ajouter dans `.vscode/settings.json` :
```json
{
  "mcp.servers": {
    "artcb": {
      "command": "python",
      "args": ["-m", "src.artcb.mcp.server"],
      "env": { "ARTCB_API_URL": "http://localhost:8000", "PYTHONPATH": "${workspaceFolder}" }
    }
  }
}
```

---

## Claude Desktop

Ajouter dans `~/.claude/claude_desktop_config.json` :
```json
{
  "mcpServers": {
    "artcb": {
      "command": "python",
      "args": ["-m", "src.artcb.mcp.server"],
      "env": { "ARTCB_API_URL": "http://localhost:8000" }
    }
  }
}
```

---

## Replit Agent / HTTP

```bash
# Démarrer en mode HTTP (port 8001)
python -m src.artcb.mcp.server --http 8001

# L'agent appelle directement :
curl -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"artcb_memo","arguments":{"text":"ma pensée"}}}'
```

---

## Tools disponibles

| Tool | Description | Paramètres |
|------|-------------|-----------|
| `artcb_memo` | Graver une pensée dans la blockchain | `text` (requis), `wallet_name`, `visibility` |
| `artcb_think` | Raisonner + graver le résultat | `question` (requis), `wallet_name` |
| `artcb_search` | Recherche sémantique dans les blocs | `query` (requis), `top_k` |
| `artcb_mine` | Pipeline minage complet | `text` (requis), `wallet_name`, `visibility` |
| `artcb_store` | Encoder + graver en un appel | `text` OU `graph_id` (requis) |

## Resources disponibles

| Resource | Description |
|----------|-------------|
| `artcb://chain/status` | État de la chaîne (blocs, PoL, nœuds) |
| `artcb://wallet/{address}` | Balance et historique d'un wallet |
