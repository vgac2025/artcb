"""Module bridges ARTCB — interopérabilité avec blockchains externes.

Principe : lecture seule des chaînes externes → encodage IR PoL → gravure ARTCB.
Aucun token ne transite — seule la sémantique de la transaction est gravée.

Chaînes supportées :
    ethereum  — JSON-RPC (Infura/Alchemy/public)
    bitcoin   — mempool.space API (pas de nœud requis)
    solana    — JSON-RPC public
    bnb       — EVM générique (BSC RPC public)
    polygon   — EVM générique
    avalanche — EVM C-Chain

Configuration (.env) :
    ETHEREUM_RPC_URL  — ex: https://mainnet.infura.io/v3/YOUR_KEY (défaut: public Cloudflare)
    SOLANA_RPC_URL    — ex: https://api.mainnet-beta.solana.com
    BITCOIN_API_URL   — ex: https://mempool.space/api (défaut)
"""

from .manager import BridgeManager, BridgeError, BridgeResult

__all__ = ["BridgeManager", "BridgeError", "BridgeResult"]
