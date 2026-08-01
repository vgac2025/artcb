#!/usr/bin/env python3
"""
Script interactif de test bridges ARTCB — à lancer manuellement.

Usage :
    python3 scripts/test_bridges_live.py

    # Avec clé Infura :
    ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/TON_KEY python3 scripts/test_bridges_live.py

    # Pour tester une transaction spécifique :
    python3 scripts/test_bridges_live.py --chain ethereum --tx 0xabc123...

Ce script montre :
1. L'état des 6 RPC publics (ping)
2. L'import d'une vraie transaction Bitcoin (gratuit)
3. L'import d'une vraie transaction Ethereum (si clé disponible)
4. Le texte IR PoL généré pour chaque transaction
5. Ce qui se passerait si on gravait ce texte dans la chaîne ARTCB

Aucune clé requise pour Bitcoin/Solana/BNB/Polygon/Avalanche.
Clé recommandée uniquement pour Ethereum (Infura ou Alchemy).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.artcb.bridges.manager import BridgeError, BridgeManager, SUPPORTED_CHAINS

# ─── Transactions de démonstration (publiques, immuables) ────────────────────

DEMO_TRANSACTIONS = {
    "bitcoin": {
        "tx_hash": "0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098",
        "description": "Premier bloc Bitcoin miné (bloc 1 — 3 janvier 2009)",
        "source": "https://mempool.space/tx/0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098",
    },
    "ethereum": {
        "tx_hash": "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060",
        "description": "Premier transfert ETH de l'histoire (bloc 46147 — 7 août 2015)",
        "source": "https://etherscan.io/tx/0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060",
    },
}

SEPARATOR = "─" * 70


def section(title: str) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def test_ping_all(mgr: BridgeManager) -> dict[str, dict]:
    section("1. PING DE TOUS LES ENDPOINTS RPC")
    results = {}
    for chain in SUPPORTED_CHAINS:
        status = mgr.ping_chain(chain)
        results[chain] = status
        icon = "✅" if status["status"] == "ok" else "❌"
        rpc_url = os.getenv(
            f"{chain.upper()}_RPC_URL",
            os.getenv("BITCOIN_API_URL" if chain == "bitcoin" else f"{chain.upper()}_RPC_URL", "public")
        )
        extra = ""
        if status["status"] == "ok":
            if "tip_height" in status:
                extra = f"bloc #{status['tip_height']:,}"
            elif "block" in status:
                extra = f"bloc #{status['block']:,}"
            elif "slot" in status:
                extra = f"slot #{status['slot']:,}"
        elif "error" in status:
            extra = f"ERREUR: {status['error'][:60]}"
        print(f"  {icon} {chain:12} | {extra}")

    ok_count = sum(1 for s in results.values() if s["status"] == "ok")
    print(f"\n  Résultat : {ok_count}/{len(SUPPORTED_CHAINS)} RPC opérationnels")

    # Conseil si Ethereum échoue
    if results.get("ethereum", {}).get("status") != "ok":
        print("""
  ⚠️  Ethereum RPC indisponible ou rate-limité (Cloudflare public).
     Solution : ajouter dans .env :
       ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/VOTRE_PROJECT_ID
     Obtenir une clé gratuite : https://infura.io
     → Sign Up → Create Project → Copy "Mainnet HTTPS" URL
        """)

    return results


def test_import_bitcoin(mgr: BridgeManager) -> None:
    section("2. IMPORT BITCOIN — GRATUIT, AUCUNE CLÉ")
    demo = DEMO_TRANSACTIONS["bitcoin"]
    print(f"  Transaction : {demo['description']}")
    print(f"  Source      : {demo['source']}")
    print(f"  Hash        : {demo['tx_hash']}")

    print("\n  → Appel mempool.space API...")
    try:
        result = mgr._fetch_bitcoin(demo["tx_hash"])
    except BridgeError as exc:
        print(f"\n  ❌ Erreur : {exc}")
        print("     Vérifier la connexion Internet.")
        return

    print(f"\n  ✅ Transaction importée avec succès !")
    print(f"     Chaîne   : {result.chain}")
    print(f"     De       : {result.from_address}")
    print(f"     Vers     : {result.to_address[:30]}…")
    print(f"     Valeur   : {result.value}")
    print(f"     Bloc     : #{result.block_number}")
    print(f"     Timestamp: {result.timestamp}")
    print(f"\n  Texte IR PoL généré (ce qui serait gravé dans ARTCB) :")
    print(f"  ┌{'─' * 65}")
    for line in result.ir_text.split(". "):
        if line.strip():
            print(f"  │ {line.strip()}.")
    print(f"  └{'─' * 65}")


def test_import_ethereum(mgr: BridgeManager) -> None:
    section("3. IMPORT ETHEREUM")
    rpc_url = os.getenv("ETHEREUM_RPC_URL", "")
    demo = DEMO_TRANSACTIONS["ethereum"]

    if not rpc_url or "cloudflare" in rpc_url:
        print("""
  ⚠️  Utilisation du RPC Cloudflare public (souvent rate-limité).
     Pour des résultats fiables, configurer dans .env :
       ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/VOTRE_PROJECT_ID

  Comment obtenir une clé Infura GRATUITE :
  ─────────────────────────────────────────
  1. Aller sur https://infura.io
  2. Cliquer "Sign Up" (compte gratuit)
  3. Créer un projet : "Create New Key" → sélectionner "Web3 API"
  4. Donner un nom (ex: "ARTCB-bridge")
  5. Dans le tableau de bord : copier l'URL "Mainnet HTTPS"
     Format : https://mainnet.infura.io/v3/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  6. Ajouter dans .env :
     ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/xxxxxxxxxxxxxxxxxxxxxxxx

  Alternative : Alchemy (https://alchemy.com)
  1. Sign Up → Create App → Network = Ethereum Mainnet
  2. Copy "HTTPS" URL
  Format : https://eth-mainnet.g.alchemy.com/v2/xxxxxxxxxxxxxxxxxxxxxxxx
        """)

    print(f"  Transaction : {demo['description']}")
    print(f"  Source      : {demo['source']}")

    eth_url = os.getenv("ETHEREUM_RPC_URL", "https://cloudflare-eth.com")
    print(f"\n  → Appel RPC : {eth_url[:60]}…")

    try:
        result = mgr._fetch_evm("ethereum", demo["tx_hash"], eth_url)
    except BridgeError as exc:
        print(f"\n  ❌ Erreur : {exc}")
        if "cloudflare" in eth_url:
            print("     → Essayer avec une clé Infura (voir instructions ci-dessus)")
        return

    print(f"\n  ✅ Transaction Ethereum importée !")
    print(f"     De       : {result.from_address}")
    print(f"     Vers     : {result.to_address}")
    print(f"     Valeur   : {result.value}")
    print(f"     Bloc     : #{result.block_number:,}")
    print(f"\n  Texte IR PoL :")
    print(f"  ┌{'─' * 65}")
    for line in result.ir_text.split(". "):
        if line.strip():
            print(f"  │ {line.strip()}.")
    print(f"  └{'─' * 65}")


def show_configuration() -> None:
    section("0. CONFIGURATION ACTUELLE")
    vars_to_show = [
        ("ETHEREUM_RPC_URL", "Ethereum RPC"),
        ("BITCOIN_API_URL", "Bitcoin API"),
        ("BNB_RPC_URL", "BNB Chain RPC"),
        ("POLYGON_RPC_URL", "Polygon RPC"),
        ("AVALANCHE_RPC_URL", "Avalanche RPC"),
        ("SOLANA_RPC_URL", "Solana RPC"),
        ("ARTCB_PUBLIC_HOST", "IP publique nœud"),
        ("ARTCB_OLLAMA_URL", "Ollama URL"),
    ]
    for env_var, label in vars_to_show:
        value = os.getenv(env_var, "")
        if value:
            # Masquer les clés API dans l'URL
            display = value
            if "/v3/" in value:
                parts = value.split("/v3/")
                display = parts[0] + "/v3/" + parts[1][:8] + "…" if len(parts) > 1 else value
            elif "/v2/" in value:
                parts = value.split("/v2/")
                display = parts[0] + "/v2/" + parts[1][:8] + "…" if len(parts) > 1 else value
            print(f"  ✅ {label:20} = {display}")
        else:
            defaults = {
                "ETHEREUM_RPC_URL": "https://cloudflare-eth.com (défaut, rate-limité)",
                "BITCOIN_API_URL": "https://mempool.space/api (défaut, GRATUIT)",
                "BNB_RPC_URL": "https://bsc.publicnode.com (défaut, gratuit)",
                "POLYGON_RPC_URL": "https://polygon-rpc.com (défaut, gratuit)",
                "AVALANCHE_RPC_URL": "https://api.avax.network/ext/bc/C/rpc (défaut, gratuit)",
                "SOLANA_RPC_URL": "https://api.mainnet-beta.solana.com (défaut, gratuit)",
                "ARTCB_PUBLIC_HOST": "NON DÉFINI (nœud s'annonce comme 127.0.0.1)",
                "ARTCB_OLLAMA_URL": "NON DÉFINI (Ollama sur 127.0.0.1:11434)",
            }
            print(f"  ⚪ {label:20} = {defaults.get(env_var, 'non défini')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test bridges ARTCB live")
    parser.add_argument("--chain", choices=SUPPORTED_CHAINS, help="Tester une seule chaîne")
    parser.add_argument("--tx", help="Hash de transaction à importer")
    args = parser.parse_args()

    print("\n" + "═" * 70)
    print("  ARTCB BRIDGES — Test live")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * 70)

    # Charger .env si présent
    try:
        from dotenv import load_dotenv
        if load_dotenv(".env"):
            print("  .env chargé ✅")
    except ImportError:
        pass

    show_configuration()

    mgr = BridgeManager()

    if args.chain and args.tx:
        # Import d'une transaction spécifique
        section(f"IMPORT TRANSACTION {args.chain.upper()}")
        try:
            result = mgr.import_transaction(chain=args.chain, tx_hash=args.tx)
            print(f"\n  ✅ Résultat :")
            print(json.dumps(
                {"chain": result.chain, "tx_hash": result.tx_hash[:20] + "…",
                 "block": result.block_number, "value": result.value,
                 "ir_text": result.ir_text[:200] + "…"},
                indent=4, ensure_ascii=False
            ))
        except BridgeError as exc:
            print(f"\n  ❌ Erreur : {exc}")
        return

    # Tests complets
    test_ping_all(mgr)
    test_import_bitcoin(mgr)
    test_import_ethereum(mgr)

    section("RÉSUMÉ")
    print("""
  Ce que le bridge ARTCB peut faire :
  ─────────────────────────────────────
  1. LIRE une transaction sur une blockchain externe (Bitcoin, ETH, SOL…)
  2. CONVERTIR son contenu en texte sémantique (IR PoL)
  3. GRAVER ce texte dans la chaîne ARTCB comme un bloc d'apprentissage
  
  → Aucun token ne transite : seule la CONNAISSANCE de la transaction est gravée.
  
  Pour graver une transaction Bitcoin dans ARTCB :
    POST http://localhost:8000/api/v1/bridges/import
    {"chain": "bitcoin", "tx_hash": "0e3e2357..."}
  
  Pour voir les bridges actifs :
    GET http://localhost:8000/api/v1/bridges/status
    """)


if __name__ == "__main__":
    main()
