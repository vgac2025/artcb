"""Tests PoL NFT — Tokens Non-Fongibles Sémantiques ARTCB.

Couvre :
- PolNFT : __post_init__, to_pol_text(), transfer_to(), to_dict/from_dict
- NFTRegistry : mint, get, by_owner, by_creator, transfer, list_all
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.artcb.pol.nft import NFTRegistry, PolNFT


# ─────────────────────────────────────────────────────────────────────────────
#  PolNFT
# ─────────────────────────────────────────────────────────────────────────────

def _make_nft(nft_id: str = "nft_test0001") -> PolNFT:
    return PolNFT(
        nft_id=nft_id,
        title="Œuvre test ARTCB",
        creator_wallet="artcb1alice00000000000000",
        owner_wallet="artcb1alice00000000000000",
        content_hash="sha256:abc123deadbeef",
        description="Description test",
        content_text="Contenu textuel",
        license="CC-BY-4.0",
        edition="1/1",
    )


class TestPolNFT:

    def test_post_init_sets_created_at(self):
        nft = _make_nft()
        assert nft.created_at != ""
        assert "T" in nft.created_at  # format ISO

    def test_post_init_sets_owner_from_creator_if_empty(self):
        nft = PolNFT(
            nft_id="nft_x",
            title="T",
            creator_wallet="artcb1creator0000000000",
            owner_wallet="",
            content_hash="",
        )
        assert nft.owner_wallet == "artcb1creator0000000000"

    def test_to_pol_text_contains_fields(self):
        nft = _make_nft()
        text = nft.to_pol_text()
        assert "nft_test0001" in text
        assert "artcb1alice" in text
        assert "CC-BY-4.0" in text
        assert "sha256:abc123deadbeef" in text

    def test_to_pol_text_no_hash(self):
        nft = PolNFT(
            nft_id="nft_nohash",
            title="Sans hash",
            creator_wallet="artcb1creator0000000000",
            owner_wallet="artcb1creator0000000000",
            content_hash="",
        )
        text = nft.to_pol_text()
        assert "HASH_CONTENU" not in text

    def test_transfer_to_returns_new_instance(self):
        nft = _make_nft()
        nft2 = nft.transfer_to("artcb1bob00000000000000", "ptx_transfer01")
        assert nft2.owner_wallet == "artcb1bob00000000000000"
        assert nft.owner_wallet == "artcb1alice00000000000000"  # original inchangé
        assert len(nft2.transfer_history) == 1
        assert nft2.transfer_history[0]["from"] == "artcb1alice00000000000000"
        assert nft2.transfer_history[0]["transfer_id"] == "ptx_transfer01"

    def test_transfer_chain(self):
        nft = _make_nft()
        nft2 = nft.transfer_to("artcb1bob00000000000000", "ptx_001")
        nft3 = nft2.transfer_to("artcb1carol0000000000", "ptx_002")
        assert len(nft3.transfer_history) == 2
        assert nft3.owner_wallet == "artcb1carol0000000000"

    def test_to_dict_from_dict_roundtrip(self):
        nft = _make_nft()
        d = nft.to_dict()
        assert d["nft_id"] == "nft_test0001"
        assert d["title"] == "Œuvre test ARTCB"
        nft2 = PolNFT.from_dict(d)
        assert nft2.nft_id == nft.nft_id
        assert nft2.title == nft.title
        assert nft2.creator_wallet == nft.creator_wallet
        assert nft2.content_hash == nft.content_hash

    def test_to_dict_from_dict_with_transfer_history(self):
        nft = _make_nft()
        nft2 = nft.transfer_to("artcb1bob00000000000000", "ptx_x")
        d = nft2.to_dict()
        nft3 = PolNFT.from_dict(d)
        assert len(nft3.transfer_history) == 1


# ─────────────────────────────────────────────────────────────────────────────
#  NFTRegistry (fichier temporaire)
# ─────────────────────────────────────────────────────────────────────────────

class TestNFTRegistry:

    def _registry(self, tmp_path: Path) -> NFTRegistry:
        return NFTRegistry(path=str(tmp_path / "test_nfts.json"))

    def test_mint_and_get(self, tmp_path):
        reg = self._registry(tmp_path)
        nft = _make_nft()
        reg.mint(nft)
        fetched = reg.get("nft_test0001")
        assert fetched is not None
        assert fetched.title == "Œuvre test ARTCB"

    def test_mint_duplicate_raises(self, tmp_path):
        reg = self._registry(tmp_path)
        nft = _make_nft()
        reg.mint(nft)
        with pytest.raises(ValueError, match="existe déjà"):
            reg.mint(nft)

    def test_get_nonexistent_returns_none(self, tmp_path):
        reg = self._registry(tmp_path)
        assert reg.get("ghost_nft") is None

    def test_by_owner(self, tmp_path):
        reg = self._registry(tmp_path)
        alice = "artcb1alice00000000000000"
        bob   = "artcb1bob00000000000000"
        nft1 = PolNFT(nft_id="nft_a1", title="A1", creator_wallet=alice, owner_wallet=alice, content_hash="")
        nft2 = PolNFT(nft_id="nft_b1", title="B1", creator_wallet=bob, owner_wallet=bob, content_hash="")
        reg.mint(nft1)
        reg.mint(nft2)
        alice_nfts = reg.by_owner(alice)
        assert len(alice_nfts) == 1
        assert alice_nfts[0].nft_id == "nft_a1"

    def test_by_creator(self, tmp_path):
        reg = self._registry(tmp_path)
        alice = "artcb1alice00000000000000"
        nft1 = PolNFT(nft_id="nft_c1", title="C1", creator_wallet=alice, owner_wallet=alice, content_hash="")
        nft2 = PolNFT(nft_id="nft_c2", title="C2", creator_wallet=alice, owner_wallet="artcb1bob00000000000000", content_hash="")
        reg.mint(nft1)
        reg.mint(nft2)
        created = reg.by_creator(alice)
        assert len(created) == 2

    def test_transfer(self, tmp_path):
        reg = self._registry(tmp_path)
        nft = _make_nft("nft_to_transfer")
        reg.mint(nft)
        updated = reg.transfer("nft_to_transfer", "artcb1bob00000000000000", "ptx_transfer_test")
        assert updated.owner_wallet == "artcb1bob00000000000000"
        assert len(updated.transfer_history) == 1
        # Vérifier persisté
        fetched = reg.get("nft_to_transfer")
        assert fetched.owner_wallet == "artcb1bob00000000000000"

    def test_transfer_nonexistent_raises(self, tmp_path):
        reg = self._registry(tmp_path)
        with pytest.raises(ValueError, match="introuvable"):
            reg.transfer("ghost_nft", "artcb1bob00000000000000")

    def test_list_all(self, tmp_path):
        reg = self._registry(tmp_path)
        for i in range(4):
            reg.mint(PolNFT(nft_id=f"nft_{i:04d}", title=f"NFT {i}",
                            creator_wallet="artcb1creator0000000000",
                            owner_wallet="artcb1creator0000000000",
                            content_hash=""))
        all_nfts = reg.list_all()
        assert len(all_nfts) == 4

    def test_empty_registry(self, tmp_path):
        reg = self._registry(tmp_path)
        assert reg.list_all() == []
