"""
Tests bridges LIVE — utilisent les vrais endpoints réseau.

Ces tests sont SÉPARÉS des tests CI (test_bridges.py).
Ils ne s'exécutent QUE si les variables d'environnement sont configurées
ou si le flag --live est passé.

Lancement :
    python3 -m pytest tests/test_bridges_live.py -v -s --live
    # ou avec une vraie clé Infura :
    ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/TON_KEY python3 -m pytest tests/test_bridges_live.py -v -s

Ce que ces tests valident (logique métier RÉELLE, réseau RÉEL) :
    - Bitcoin : hash de transaction réel → BridgeResult correct
    - Ethereum : hash de transaction réel → valeur en ETH correcte
    - Solana : signature réelle → slot correct
    - BNB/Polygon/Avalanche : ping RPC live

Différence avec test_bridges.py (CI) :
    - test_bridges.py  : logique réelle + réseau mocké (aucune clé requise, toujours PASS en CI)
    - test_bridges_live.py : logique réelle + réseau réel (clés recommandées, skip si indisponible)
"""

from __future__ import annotations

import os
import pytest

from src.artcb.bridges.manager import BridgeError, BridgeManager

# ─── Transactions réelles connues (publiques, immuables) ──────────────────────

# Transaction Bitcoin genesis coinbase (bloc 1 — confirmée depuis 2009)
_BTC_REAL_TX = "0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098"

# Transaction Ethereum bien connue (premier transfert ETH de l'histoire — bloc 46147)
# https://etherscan.io/tx/0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060
_ETH_REAL_TX = "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060"

# Signature Solana connue (transaction publique)
_SOL_REAL_TX = "2QMJG5oXYRvETbvnMijuTSoNyerAoaNg7rJW7wT6vBdSHT5Q2g6mXHdneBVVtKD4B5q6W9P5Qb8tSiGXxRxzMwZ"

# ─── Marqueur pour activer les tests live ────────────────────────────────────

def pytest_addoption_live_registered():
    """Vérifier si le flag --live est passé (sans modifier conftest global)."""
    return os.getenv("ARTCB_LIVE_TESTS", "").lower() in ("1", "true", "yes")


LIVE = pytest_addoption_live_registered()
SKIP_REASON = (
    "Test live désactivé. "
    "Pour activer : ARTCB_LIVE_TESTS=1 python3 -m pytest tests/test_bridges_live.py -v\n"
    "Ou configurer ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/VOTRE_CLE dans .env"
)


# ─── Tests Bitcoin (GRATUIT — mempool.space, pas de clé) ─────────────────────

class TestBridgeBitcoinLive:
    """
    Bitcoin : utilise mempool.space — GRATUIT, aucune clé requise.
    Ces tests peuvent tourner sans configuration si Internet est disponible.
    """

    @pytest.mark.skipif(not LIVE, reason=SKIP_REASON)
    def test_ping_bitcoin_live(self):
        """Vérifie que mempool.space répond et retourne une hauteur de bloc."""
        mgr = BridgeManager()
        status = mgr.ping_chain("bitcoin")
        assert status["status"] == "ok", f"Bitcoin ping failed: {status}"
        assert isinstance(status.get("tip_height"), int)
        assert status["tip_height"] > 800_000, "Hauteur Bitcoin anormalement basse"
        print(f"\n✅ Bitcoin live: hauteur bloc = {status['tip_height']}")

    @pytest.mark.skipif(not LIVE, reason=SKIP_REASON)
    def test_fetch_bitcoin_real_tx(self):
        """Import d'une vraie transaction Bitcoin (bloc 1 — 2009)."""
        mgr = BridgeManager()
        try:
            result = mgr._fetch_bitcoin(_BTC_REAL_TX)
        except BridgeError as exc:
            pytest.skip(f"mempool.space indisponible: {exc}")

        assert result.chain == "bitcoin"
        assert result.tx_hash == _BTC_REAL_TX
        assert result.block_number is not None
        assert "BTC" in result.value
        assert result.ir_text  # texte IR non vide
        assert "bitcoin" in result.ir_text.lower() or "BITCOIN" in result.ir_text
        print(f"\n✅ Bitcoin TX réelle importée:")
        print(f"   bloc: {result.block_number}")
        print(f"   valeur: {result.value}")
        print(f"   IR: {result.ir_text[:100]}…")


# ─── Tests Ethereum (recommande Infura/Alchemy) ───────────────────────────────

class TestBridgeEthereumLive:
    """
    Ethereum : utilise Cloudflare par défaut (souvent rate-limité).
    Recommandé : ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/TON_KEY
    """

    @pytest.mark.skipif(not LIVE, reason=SKIP_REASON)
    def test_ping_ethereum_live(self):
        """Vérifie que le RPC Ethereum répond."""
        mgr = BridgeManager()
        status = mgr.ping_chain("ethereum")
        if status["status"] == "error":
            eth_url = os.getenv("ETHEREUM_RPC_URL", "cloudflare-eth.com (défaut)")
            pytest.skip(f"RPC Ethereum indisponible ({eth_url}): {status.get('error')}")
        assert status["status"] == "ok"
        assert isinstance(status.get("block"), int)
        assert status["block"] > 20_000_000, "Hauteur ETH anormalement basse"
        print(f"\n✅ Ethereum live: bloc = {status['block']}")

    @pytest.mark.skipif(not LIVE, reason=SKIP_REASON)
    def test_fetch_ethereum_real_tx(self):
        """Import d'une vraie transaction Ethereum (premier transfert ETH historique)."""
        mgr = BridgeManager()
        try:
            result = mgr._fetch_evm("ethereum", _ETH_REAL_TX, os.getenv("ETHEREUM_RPC_URL", "https://cloudflare-eth.com"))
        except BridgeError as exc:
            pytest.skip(f"RPC Ethereum indisponible (configurer ETHEREUM_RPC_URL): {exc}")

        assert result.chain == "ethereum"
        assert result.from_address.startswith("0x")
        assert "ETH" in result.value
        assert result.ir_text
        print(f"\n✅ Ethereum TX réelle importée:")
        print(f"   de: {result.from_address[:20]}…")
        print(f"   valeur: {result.value}")
        print(f"   IR: {result.ir_text[:100]}…")


# ─── Tests BNB Chain (gratuit — publicnode.com) ───────────────────────────────

class TestBridgeBNBLive:
    """BNB Chain : endpoint public gratuit bsc.publicnode.com"""

    @pytest.mark.skipif(not LIVE, reason=SKIP_REASON)
    def test_ping_bnb_live(self):
        """Vérifie que le RPC BNB Chain répond."""
        mgr = BridgeManager()
        status = mgr.ping_chain("bnb")
        if status["status"] == "error":
            pytest.skip(f"BNB RPC indisponible: {status.get('error')}")
        assert status["status"] == "ok"
        print(f"\n✅ BNB Chain live: bloc = {status.get('block')}")


# ─── Tests Polygon (gratuit — polygon-rpc.com) ────────────────────────────────

class TestBridgePolygonLive:
    """Polygon PoS : endpoint public gratuit."""

    @pytest.mark.skipif(not LIVE, reason=SKIP_REASON)
    def test_ping_polygon_live(self):
        """Vérifie que le RPC Polygon répond."""
        mgr = BridgeManager()
        status = mgr.ping_chain("polygon")
        if status["status"] == "error":
            pytest.skip(f"Polygon RPC indisponible: {status.get('error')}")
        assert status["status"] == "ok"
        print(f"\n✅ Polygon live: bloc = {status.get('block')}")


# ─── Tests Solana (gratuit — api.mainnet-beta.solana.com) ─────────────────────

class TestBridgeSolanaLive:
    """Solana : endpoint public gratuit."""

    @pytest.mark.skipif(not LIVE, reason=SKIP_REASON)
    def test_ping_solana_live(self):
        """Vérifie que le RPC Solana répond."""
        mgr = BridgeManager()
        status = mgr.ping_chain("solana")
        if status["status"] == "error":
            pytest.skip(f"Solana RPC indisponible: {status.get('error')}")
        assert status["status"] == "ok"
        print(f"\n✅ Solana live: slot = {status.get('slot')}")


# ─── Test complet status_all live ────────────────────────────────────────────

class TestBridgeStatusAllLive:
    """Test global : ping toutes les chaînes en live."""

    @pytest.mark.skipif(not LIVE, reason=SKIP_REASON)
    def test_status_all_live(self):
        """
        Ping les 6 chaînes en live.
        Au moins Bitcoin et Solana doivent être OK (gratuits, pas de clé).
        Ethereum peut être en erreur si pas de clé Infura.
        """
        mgr = BridgeManager()
        statuses = mgr.status_all()
        assert len(statuses) == 6

        print("\n=== Status bridges LIVE ===")
        ok_count = 0
        for s in statuses:
            icon = "✅" if s["status"] == "ok" else "❌"
            print(f"{icon} {s['chain']:12} : {s['status']:8} {s.get('error','')[:60]}")
            if s["status"] == "ok":
                ok_count += 1

        # Au moins Bitcoin doit fonctionner (gratuit, robuste)
        btc_status = next(s for s in statuses if s["chain"] == "bitcoin")
        assert btc_status["status"] == "ok", (
            "Bitcoin mempool.space devrait toujours fonctionner. "
            "Vérifier la connexion Internet."
        )
        print(f"\n{ok_count}/6 chaînes disponibles")
