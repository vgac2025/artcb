# Rapport 086 — Phase 12 : Serveur MCP + Interopérabilité Blockchain + Multi-environnement
**Date :** 2026-07-31  
**Agent :** Bob (IBM)  
**Branche :** `main`  
**Avancement global : 87 % → cible 95 % avec Phase 12**  
**Roadmap mise à jour :** `ROADMAP_GENERAL_ARTCB` — Phase 12 ajoutée (41 jalons)

---

## 1. RÉSUMÉ — TROIS NOUVEAUX PILIERS

| Pilier | Sous-phases | Jalons | Priorité | Impact |
|--------|------------|--------|---------|--------|
| **Serveur MCP** | 12.1 | 15 | P1 | ARTCB dans tous les IDE (Cursor, Bob, VSCode, JetBrains, Lovable) |
| **Interopérabilité blockchain** | 12.2 + 12.4 | 17 | P2 | Bridges BTC/ETH/SOL/BNB natifs, ERC-20/721 en lecture |
| **Multi-environnement** | 12.3 | 8 | P1 | Nix/Replit/Codespaces/Docker/Railway/Render |

---

## 2. SERVEUR MCP — POURQUOI ET COMMENT

### 2.1 Qu'est-ce que le MCP (Model Context Protocol) ?

Le MCP est le protocole standard ouvert d'Anthropic (2024) pour connecter n'importe quel **agent IA ou IDE** à n'importe quelle **source de données ou outil externe**. Il est devenu le standard de facto en 2026 — supporté par :

| IDE / Agent | Support MCP |
|------------|------------|
| **Cursor** | ✅ natif (`.cursor/mcp.json`) |
| **Bob IDE (IBM)** | ✅ natif |
| **Claude Desktop** | ✅ natif |
| **VSCode + Copilot** | ✅ via extension |
| **JetBrains AI** | ✅ via plugin |
| **Lovable** | ✅ agents MCP |
| **Replit Agent** | ✅ natif |
| **OpenAI ChatGPT** | ✅ (plugins MCP) |

### 2.2 Architecture du serveur MCP ARTCB

```
[Cursor/Bob/VSCode]
        │
        │  stdio ou HTTP/SSE (MCP Protocol)
        ▼
┌─────────────────────────────────────────┐
│          ARTCB MCP Server               │
│  src/artcb/mcp/server.py                │
│                                         │
│  TOOLS :                                │
│   • artcb_memo(text, type)              │  ← graver une pensée
│   • artcb_think(question)              │  ← IA raisonne + grave
│   • artcb_search(query)               │  ← recherche sémantique
│   • artcb_mine(text)                   │  ← pipeline minage complet
│   • artcb_wallet_balance(address)      │  ← solde wallet
│   • artcb_chain_verify()              │  ← vérification intégrité
│   • artcb_bridge_import(chain, tx_id) │  ← importer tx externe
│                                         │
│  RESOURCES :                            │
│   • artcb://chain/status               │  ← état live chaîne
│   • artcb://chain/blocks/{n}           │  ← dernier bloc
│   • artcb://wallet/{address}          │  ← wallet info
│   • artcb://pol/score                  │  ← PoL courant
│                                         │
│  PROMPTS :                              │
│   • artcb_blockchain_assistant         │  ← prompt système complet
│   • artcb_mining_guide                 │  ← guide minage
│                                         │
└───────────────┬─────────────────────────┘
                │  HTTP REST interne
                ▼
        ARTCB API (port 8000)
```

### 2.3 Fichiers à créer

```
src/artcb/mcp/
├── __init__.py
├── server.py          # Serveur MCP principal (stdio + HTTP)
├── tools.py           # Définition des 7 outils MCP
├── resources.py       # Définition des 4 ressources MCP
└── prompts.py         # Prompts système ARTCB

tests/
└── test_mcp_server.py  # 20+ cas de test

docs/
└── MCP_SETUP.md        # Guide par IDE

.cursor/
└── mcp.json            # Config Cursor (générée automatiquement)
```

### 2.4 Exemple d'usage — Cursor IDE

Une fois le serveur MCP branché, dans Cursor :

```
// Dans le chat Cursor :
@ARTCB grave cette idée dans la blockchain

// Cursor appelle automatiquement artcb_memo()
// → retourne : "Gravé en bloc #526, PoL=0.75, hash=2f261fca…"

@ARTCB cherche tous les blocs parlant de "cryptographie post-quantique"

// Cursor appelle artcb_search()
// → retourne : 12 blocs pertinents avec scores de similarité
```

### 2.5 Configuration `.cursor/mcp.json` (à créer)

```json
{
  "mcpServers": {
    "artcb": {
      "command": "python",
      "args": ["-m", "src.artcb.mcp.server"],
      "env": {
        "ARTCB_API_URL": "http://localhost:8000",
        "ARTCB_API_KEY": "${ARTCB_API_KEY}"
      }
    }
  }
}
```

### 2.6 Configuration Bob IDE

```json
{
  "mcp": {
    "servers": {
      "artcb-blockchain": {
        "transport": "stdio",
        "command": ["python", "-m", "src.artcb.mcp.server"],
        "env": { "ARTCB_API_URL": "http://localhost:8000" }
      }
    }
  }
}
```

---

## 3. INTEROPÉRABILITÉ BLOCKCHAIN — ARCHITECTURE

### 3.1 Problème identifié

Aujourd'hui, Bitcoin, Ethereum, Solana et ARTCB sont des **silos**. Un utilisateur qui a des ETH ne peut pas l'utiliser directement dans ARTCB, et inversement. La Phase 12.2 résout ça avec des **bridges sémantiques PoL**.

### 3.2 Principe du bridge sémantique PoL

```
[Transaction Ethereum]          [Transaction ARTCB]
{ from: 0xAlice,                →  IR Graph :
  to: 0xBob,                       nodes: [
  value: 1.5 ETH,                    E: "Alice envoie 1.5 ETH à Bob"
  block: 22.4M,                      C: "bloc Ethereum #22400000"
  sig: 0x... }                       P: "hash_original: 0x..."
                                   ]
                                   + signature ML-DSA-65 ARTCB
                                   + PoL score calculé
```

**La transaction Ethereum est encodée en IR PoL et gravée dans ARTCB.** Elle devient :
- Immuable ML-DSA-65 post-quantique
- Recherchable sémantiquement
- Disponible hors ligne
- Enrichie de contexte (pourquoi ce transfert ?)

### 3.3 Bridges par chaîne

| Bridge | Protocole | Données lues | Méthode |
|--------|-----------|-------------|---------|
| **Bitcoin** | Bitcoin Core RPC / mempool.space API | Transactions, inscriptions Ordinals | REST publique |
| **Ethereum** | JSON-RPC + web3.py | Transactions ETH, events ERC-20/721 | Infura/Alchemy |
| **Solana** | Solana JSON-RPC | Transactions, events programs | QuickNode/Helius |
| **BNB Chain** | EVM (fork Ethereum) | Compatible `evm_generic.py` | BSC RPC public |
| **Polygon** | EVM (fork Ethereum) | Compatible `evm_generic.py` | Polygon RPC public |
| **Avalanche** | EVM (C-Chain) | Compatible `evm_generic.py` | Avalanche API |

### 3.4 Endpoints ajoutés à l'API

```
POST /api/v1/bridges/import          → importer une tx externe dans ARTCB
GET  /api/v1/bridges/status          → état des 6 bridges (ping RPC)
GET  /api/v1/bridges/{chain}/last    → dernière tx synchronisée par chaîne
GET  /api/v1/interop/chains          → liste des chaînes supportées
POST /api/v1/bridges/export          → exporter un bloc ARTCB vers une chaîne EVM (P3)
```

### 3.5 Comparaison avec les bridges existants

| Solution | Approche | Décentralisation | Sémantique |
|----------|----------|-----------------|-----------|
| **LayerZero** | Messaging omnichain | Moderate (oracles) | ❌ |
| **Wormhole** | Bridge de tokens | Moderate (guardians) | ❌ |
| **Polkadot XCMP** | Parachains | Haute | ❌ |
| **Cosmos IBC** | Inter-blockchain | Haute | ❌ |
| **ARTCB Bridge (PoL)** | Import sémantique | Haute (données locales) | ✅ **UNIQUE** |

**Différence fondamentale :** ARTCB ne déplace pas les tokens entre chaînes — il **encode le sens** des transactions dans sa chaîne sémantique. C'est une couche de compréhension, pas de transfert.

---

## 4. MULTI-ENVIRONNEMENT — STRATÉGIE NIX + DOCKER

### 4.1 Pourquoi Nix ?

Nix est le gestionnaire de paquets reproductible utilisé par :
- **Replit** (nativement via `replit.nix`)
- **Devbox** (outil populaire 2026)
- **Nixpacks** (Railway, Render)
- **NixOS** (systèmes d'exploitation reproductibles)

Avec Nix, l'environnement ARTCB est identique sur **toutes les machines**, sans `pip install`, sans version incompatible, sans "ça marche sur ma machine".

### 4.2 Fichiers à créer

#### `flake.nix`
```nix
{
  description = "ARTCB Blockchain Node";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  
  outputs = { self, nixpkgs }: {
    devShells.default = nixpkgs.legacyPackages.x86_64-linux.mkShell {
      packages = with nixpkgs.legacyPackages.x86_64-linux; [
        python312
        python312Packages.pip
        gcc  # pour liboqs natif
        cmake
        nodejs_22
        ngrok
      ];
      shellHook = ''
        pip install -r requirements.txt --quiet
        echo "ARTCB devenv ready — make api"
      '';
    };
  };
}
```

#### `.replit`
```toml
run = "make api"
language = "python3"
entrypoint = "src/api/main.py"

[nix]
channel = "stable-23_11"

[deployment]
run = ["sh", "-c", "make api"]
deploymentTarget = "cloudrun"
```

#### `replit.nix`
```nix
{ pkgs }: {
  deps = [
    pkgs.python312
    pkgs.python312Packages.pip
    pkgs.gcc
    pkgs.cmake
    pkgs.nodejs_22
  ];
}
```

#### `.devcontainer/devcontainer.json`
```json
{
  "name": "ARTCB Blockchain",
  "image": "mcr.microsoft.com/devcontainers/python:3.12",
  "postCreateCommand": "pip install -r requirements.txt",
  "forwardPorts": [8000, 5173],
  "customizations": {
    "vscode": {
      "extensions": ["ms-python.python", "anthropic.claude-mcp"]
    }
  }
}
```

### 4.3 Tableau des environnements supportés

| Environnement | Fichier | Commande | Statut |
|--------------|---------|---------|--------|
| **Local (Linux)** | `Makefile` | `make api` | ✅ opérationnel |
| **Nix devshell** | `flake.nix` | `nix develop && make api` | [ ] à créer |
| **Replit** | `.replit` + `replit.nix` | Bouton Run | [ ] à créer |
| **GitHub Codespaces** | `.devcontainer/` | Bouton Codespaces | [ ] à créer |
| **Gitpod** | `.devcontainer/` | `gp init` | [ ] à créer |
| **Docker** | `Dockerfile` | `docker run artcb/node` | [ ] à créer |
| **Railway** | `railway.toml` | `railway up` | [ ] à créer |
| **Render** | `render.yaml` | Auto-deploy Git | [ ] à créer |

---

## 5. TABLEAU DE BORD — PHASE 12 COMPLÈTE

### 5.1 Résumé jalons (41 total)

| Sous-phase | Jalons | Priorité | Effort estimé |
|-----------|--------|---------|--------------|
| 12.1 MCP Server | 15 | P1 | 2–3 jours |
| 12.2 Bridges blockchain | 11 | P2 | 3–5 jours |
| 12.3 Multi-env | 8 | P1 | 1–2 jours |
| 12.4 Protocoles standards | 6 | P2–P3 | 2–4 jours |
| **Total Phase 12** | **40** | | **~10 jours** |

### 5.2 Ordre d'exécution recommandé

```
Semaine 1 :
  Jour 1–2 : Phase 12.1 MCP (server.py + tools + config Cursor + Bob)
  Jour 3   : Phase 12.3 Nix + Docker + Replit + Devcontainer

Semaine 2 :
  Jour 4–5 : Phase 12.2 Bridge ETH (ethereum.py + evm_generic.py)
  Jour 6   : Phase 12.2 Bridge SOL (solana.py) + BTC (bitcoin.py)
  Jour 7   : Phase 12.4 ERC-20/721 lecture + tests complets
```

### 5.3 Impact sur l'avancement global

| Métrique | Avant Phase 12 | Après Phase 12 |
|---------|---------------|---------------|
| Avancement global | 87 % | ~95 % |
| IDEs supportés | 0 (API manuelle) | 7 (MCP natif) |
| Blockchains interopérables | 0 | 6 (BTC/ETH/SOL/BNB/Polygon/Avalanche) |
| Environnements de déploiement | 1 (Linux local) | 8 |
| NFT standards supportés | ARTCB uniquement | ERC-20 + ERC-721 (lecture) + ARTCB |

---

## 6. CE QUI EXISTE DÉJÀ (à réutiliser)

| Module existant | Utilisé par Phase 12 |
|----------------|---------------------|
| `src/artcb/sdk/artcb_sdk.py` | Base du MCP server (appels API) |
| `src/api/ai_routes.py` (`/ai/memo`, `/ai/think`) | Tools MCP `artcb_memo`, `artcb_think` |
| `src/artcb/connectors/manager.py` | Réutilisé pour bridges externes |
| `src/artcb/ir/encoder.py` | Encoder les txs externes en IR PoL |
| `src/artcb/crypto/pqc.py` (ML-DSA-65) | Signer les blocs importés |
| `scripts/artcb_cli.py` | Base pour MCP en mode stdio |
| `src/artcb/p2p/sync.py` | Réutilisé pour sync bridges |

---

## 7. PROCHAINES ACTIONS CONCRÈTES

### Action immédiate — Serveur MCP (2 jours)

```bash
# 1. Créer la structure MCP
mkdir -p src/artcb/mcp
touch src/artcb/mcp/__init__.py
touch src/artcb/mcp/server.py
touch src/artcb/mcp/tools.py
touch src/artcb/mcp/resources.py
touch src/artcb/mcp/prompts.py

# 2. Installer le SDK MCP
pip install "mcp[cli]>=1.0"

# 3. Lancer le serveur MCP
python -m src.artcb.mcp.server

# 4. Tester avec Cursor
# Ajouter dans .cursor/mcp.json et redémarrer Cursor
```

### Action immédiate — Nix/Docker (1 jour)

```bash
# Créer flake.nix, .replit, Dockerfile, devcontainer.json
# → Make cibles env-nix, env-docker, env-replit
make env-docker   # build + test dans Docker
make env-replit   # simuler l'env Replit localement
```

### Action immédiate — Bridge ETH (3 jours)

```bash
# Installer dépendances bridges
pip install web3 solana httpx

# Configurer dans .env
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_KEY
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
BITCOIN_API_URL=https://mempool.space/api

# Tester bridge ETH (lecture seule)
curl -X POST http://localhost:8000/api/v1/bridges/import \
  -H "Content-Type: application/json" \
  -d '{"chain":"ethereum","tx_hash":"0xabc..."}'
```
