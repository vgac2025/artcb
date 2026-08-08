"""Tests post-quantum crypto — ML-DSA-65 hybrid signatures."""

from __future__ import annotations

import pytest
from nacl import signing

from artcb.crypto.hashing import dual_hash_hex, sha3_256_hex
from artcb.crypto.hybrid import HybridSignature, sign_hybrid, verify_hybrid
from artcb.crypto.pqc import (
    PQC_SIG_ALGORITHM,
    generate_keypair,
    pack_keypair,
    pqc_enabled,
    sign_message,
    unpack_keypair,
    verify_message,
)
from artcb.wallet.address import hybrid_address_v2, verify_address_v2
from artcb.wallet.manager import WalletManager

def _oqs_installed() -> bool:
    # oqs lève SystemExit (pas ImportError) quand cmake est absent.
    # Le script replit_start.sh patche ce comportement sur Replit,
    # mais sur un clone neuf ou en CI standard, il faut attraper les deux.
    try:
        import oqs  # noqa: F401
        return True
    except (ImportError, SystemExit, RuntimeError):
        return False


pytestmark = pytest.mark.skipif(
    not pqc_enabled() or not _oqs_installed(),
    reason="liboqs-python non installé ou ARTCB_PQC_ENABLED=false",
)


class TestPQCCore:
    def test_generate_keypair_sizes(self):
        sk, pk = generate_keypair()
        assert len(sk) == 4032
        assert len(pk) == 1952

    def test_pack_unpack_roundtrip(self):
        sk, pk = generate_keypair()
        packed = pack_keypair(sk, pk)
        sk2, pk2 = unpack_keypair(packed)
        assert sk == sk2 and pk == pk2

    def test_sign_verify_message(self):
        sk, pk = generate_keypair()
        msg = b"ARTCB-PQC-TEST"
        sig = sign_message(msg, sk)
        assert verify_message(msg, sig, pk)
        assert not verify_message(b"tampered", sig, pk)

    def test_dual_hash(self):
        result = dual_hash_hex("ARTCB")
        assert len(result["sha256"]) == 64
        assert len(result["sha3_256"]) == 64
        assert result["sha3_256"] == sha3_256_hex("ARTCB")


class TestHybridSignatures:
    def test_hybrid_sign_verify(self):
        ed = signing.SigningKey.generate()
        sk, pk = generate_keypair()
        msg = b"hybrid-block-hash"
        sig = sign_hybrid(ed25519_key=ed, pqc_secret_key=sk, message=msg)
        assert sig.startswith("hybrid:")
        assert verify_hybrid(
            message=msg,
            signature_value=sig,
            ed25519_public_key=ed.verify_key.encode(),
            pqc_public_key=pk,
        )

    def test_hybrid_parse_roundtrip(self):
        parsed = HybridSignature.parse("hybrid:ed25519:aa|mldsa65:bb")
        assert parsed is not None
        assert parsed.ed25519_hex == "aa"
        assert parsed.mldsa_hex == "bb"

    def test_legacy_ed25519_still_verifies(self):
        ed = signing.SigningKey.generate()
        msg = b"legacy"
        sig_hex = ed.sign(msg).signature.hex()
        assert verify_hybrid(
            message=msg,
            signature_value=f"ed25519:{sig_hex}",
            ed25519_public_key=ed.verify_key.encode(),
            pqc_public_key=b"",
        )


class TestHybridWallet:
    def test_create_hybrid_wallet(self, tmp_path):
        wm = WalletManager(wallet_dir=tmp_path)
        wallet = wm.create_wallet(name="hybrid")
        assert wallet.is_hybrid
        assert wallet.address_v2 is not None
        assert verify_address_v2(wallet.address_v2)
        assert (tmp_path / "hybrid.pqc").exists()
        pqc_blob = (tmp_path / "hybrid.pqc").read_bytes()
        assert pqc_blob.startswith(b"ARTCBENC1")

    def test_hybrid_sign_message(self, tmp_path):
        wm = WalletManager(wallet_dir=tmp_path)
        wallet = wm.create_wallet(name="signer")
        sig = wallet.sign(b"join-challenge")
        assert sig.startswith("hybrid:")

    def test_load_hybrid_wallet(self, tmp_path):
        wm = WalletManager(wallet_dir=tmp_path)
        created = wm.create_wallet(name="reload")
        loaded = wm.load_wallet(name="reload")
        assert loaded.is_hybrid
        assert loaded.address_v2 == created.address_v2
        assert loaded.sign(b"x").startswith("hybrid:")


class TestHybridChain:
    def test_block_has_sha3_and_hybrid_sig(self, tmp_path):
        from artcb.chain.manager import ChainManager

        chain = ChainManager(tmp_path / "blocks.jsonl", key_path=tmp_path / "chain.key")
        block = chain.append_block(graph_id="g_pqc", graph_root="a" * 64, pol_score=0.75)
        assert block.hash_sha3 is not None
        assert len(block.hash_sha3) == 64
        if chain.is_hybrid:
            assert block.signature.startswith("hybrid:")

    def test_artcb2_address_from_keys(self):
        ed = signing.SigningKey.generate()
        _, pk = generate_keypair()
        addr = hybrid_address_v2(ed.verify_key.encode(), pk)
        assert addr.startswith("artcb2")
        assert verify_address_v2(addr)
        assert PQC_SIG_ALGORITHM == "ML-DSA-65"
