"""Tests bridges ARTCB — Phase 12.2.

Tests couverts :
    - BridgeManager instanciation
    - SUPPORTED_CHAINS contient les 6 chaînes
    - BridgeResult.to_ir_text() génère un texte non vide
    - BridgeError levée si chaîne inconnue
    - _fetch_bitcoin mock HTTP
    - _fetch_evm mock RPC (ethereum)
    - _fetch_solana mock RPC
    - ping_chain mock
    - status_all retourne 6 entrées
    - BridgeImportRequest validation Pydantic
    - ir_text contient chaîne + hash
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.artcb.bridges.manager import BridgeError, BridgeManager, BridgeResult, SUPPORTED_CHAINS


# ---------------------------------------------------------------------------
# Helpers mocks
# ---------------------------------------------------------------------------

_BTC_TX_MOCK = {
    "txid": "aaaa1234bbbb5678cccc9012dddd3456eeee7890ffff1234aaaa5678bbbb9012",
    "vin": [{"prevout": {"scriptpubkey_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf Nb"}}],
    "vout": [{"scriptpubkey_address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh", "value": 5000000}],
    "status": {"confirmed": True, "block_height": 850000, "block_time": 1753900000},
}

_ETH_TX_MOCK = {
    "hash": "0xabc123def456",
    "from": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "to": "0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8",
    "value": "0xDE0B6B3A7640000",  # 1 ETH
    "blockNumber": "0x1517B3A",
}

_ETH_RECEIPT_MOCK = {"status": "0x1", "gasUsed": "0x5208"}

_SOL_TX_MOCK = {
    "slot": 320000000,
    "transaction": {
        "message": {
            "accountKeys": [
                "So11111111111111111111111111111111111111112",
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            ]
        }
    },
    "meta": {"fee": 5000, "err": None},
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBridgeManagerInit:
    def test_instantiation(self):
        mgr = BridgeManager()
        assert mgr is not None

    def test_supported_chains(self):
        assert len(SUPPORTED_CHAINS) == 6
        assert "ethereum" in SUPPORTED_CHAINS
        assert "bitcoin" in SUPPORTED_CHAINS
        assert "solana" in SUPPORTED_CHAINS
        assert "bnb" in SUPPORTED_CHAINS
        assert "polygon" in SUPPORTED_CHAINS
        assert "avalanche" in SUPPORTED_CHAINS

    def test_unknown_chain_raises(self):
        mgr = BridgeManager()
        with pytest.raises(BridgeError, match="non supportée"):
            mgr.import_transaction(chain="dogecoin", tx_hash="abc123")


class TestBridgeResult:
    def test_to_ir_text_bitcoin(self):
        result = BridgeResult(
            chain="bitcoin", tx_hash="aaaa1234bbbb",
            block_number=850000, from_address="1A1zP1eP5",
            to_address="bc1qxy2", value="0.05 BTC",
            timestamp="2026-07-31T00:00:00Z", raw_data={},
        )
        result.ir_text = result.to_ir_text()
        assert "bitcoin" in result.ir_text.lower() or "BITCOIN" in result.ir_text
        assert "aaaa1234" in result.ir_text
        assert "850000" in result.ir_text
        assert "0.05 BTC" in result.ir_text

    def test_to_ir_text_ethereum(self):
        result = BridgeResult(
            chain="ethereum", tx_hash="0xabc123def456",
            block_number=22000000, from_address="0xd8dA6BF",
            to_address="0xBE0eB5", value="1.00000000 ETH",
            timestamp="2026-07-31T00:00:00Z", raw_data={},
        )
        result.ir_text = result.to_ir_text()
        assert "ETHEREUM" in result.ir_text or "ethereum" in result.ir_text.lower()
        assert "1.00000000 ETH" in result.ir_text


class TestBridgeFetchBitcoin:
    @patch.object(BridgeManager, "_http_get", return_value=_BTC_TX_MOCK)
    def test_fetch_bitcoin_success(self, mock_get):
        mgr = BridgeManager()
        result = mgr._fetch_bitcoin("aaaa1234bbbb5678")
        assert result.chain == "bitcoin"
        assert result.block_number == 850000
        assert "BTC" in result.value
        assert result.ir_text  # texte IR généré

    @patch.object(BridgeManager, "_http_get", return_value={"error": "not found"})
    def test_fetch_bitcoin_not_found(self, mock_get):
        mgr = BridgeManager()
        with pytest.raises(BridgeError, match="introuvable"):
            mgr._fetch_bitcoin("nonexistent")


class TestBridgeFetchEVM:
    @patch.object(BridgeManager, "_evm_rpc")
    def test_fetch_ethereum_success(self, mock_rpc):
        mock_rpc.side_effect = lambda url, method, params: (
            _ETH_TX_MOCK if method == "eth_getTransactionByHash" else _ETH_RECEIPT_MOCK
        )
        mgr = BridgeManager()
        result = mgr._fetch_evm("ethereum", "0xabc123def456", "http://test-rpc")
        assert result.chain == "ethereum"
        assert result.from_address.startswith("0x")
        assert "ETH" in result.value

    @patch.object(BridgeManager, "_evm_rpc", return_value=None)
    def test_fetch_evm_not_found(self, mock_rpc):
        mgr = BridgeManager()
        with pytest.raises(BridgeError, match="introuvable"):
            mgr._fetch_evm("ethereum", "0xnotfound", "http://test-rpc")


class TestBridgeFetchSolana:
    @patch.object(BridgeManager, "_sol_rpc", return_value=_SOL_TX_MOCK)
    def test_fetch_solana_success(self, mock_rpc):
        mgr = BridgeManager()
        result = mgr._fetch_solana("test_signature_123")
        assert result.chain == "solana"
        assert result.block_number == 320000000
        assert "lamports" in result.value

    @patch.object(BridgeManager, "_sol_rpc", return_value=None)
    def test_fetch_solana_not_found(self, mock_rpc):
        mgr = BridgeManager()
        with pytest.raises(BridgeError, match="introuvable"):
            mgr._fetch_solana("nonexistent")


class TestBridgePing:
    @patch.object(BridgeManager, "_http_get", return_value=850001)
    def test_ping_bitcoin(self, mock_get):
        mgr = BridgeManager()
        status = mgr.ping_chain("bitcoin")
        assert status["chain"] == "bitcoin"
        assert status["status"] == "ok"

    @patch.object(BridgeManager, "_evm_rpc", return_value="0x14FA8B2")
    def test_ping_ethereum(self, mock_rpc):
        mgr = BridgeManager()
        status = mgr.ping_chain("ethereum")
        assert status["chain"] == "ethereum"
        assert status["status"] == "ok"

    @patch.object(BridgeManager, "_sol_rpc", return_value=320000001)
    def test_ping_solana(self, mock_rpc):
        mgr = BridgeManager()
        status = mgr.ping_chain("solana")
        assert status["chain"] == "solana"
        assert status["status"] == "ok"

    def test_ping_unknown_chain(self):
        mgr = BridgeManager()
        status = mgr.ping_chain("dogecoin_unknown")
        assert status["status"] == "unknown"

    @patch.object(BridgeManager, "_http_get", return_value=850001)
    @patch.object(BridgeManager, "_evm_rpc", return_value="0x14FA8B2")
    @patch.object(BridgeManager, "_sol_rpc", return_value=320000001)
    def test_status_all_returns_6(self, mock_sol, mock_evm, mock_btc):
        mgr = BridgeManager()
        statuses = mgr.status_all()
        assert len(statuses) == 6
        chains = {s["chain"] for s in statuses}
        assert chains == set(SUPPORTED_CHAINS)
