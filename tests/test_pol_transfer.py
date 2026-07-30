"""Tests PoL Transfer Protocol — transactions PoL natives ARTCB.

Couvre :
- PolTransfer : __post_init__, to_pol_text(), to_dict/from_dict
- TransferLedger : append, _load_all, by_address, by_id, balance_of, all_transfers
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.artcb.pol.transfer import PolTransfer, TransferLedger


# ─────────────────────────────────────────────────────────────────────────────
#  PolTransfer
# ─────────────────────────────────────────────────────────────────────────────

ALICE = "artcb1alice00000000000000"
BOB   = "artcb1bob00000000000000"
CAROL = "artcb1carol0000000000000"


def _make_transfer(
    transfer_id: str = "ptx_test0001",
    from_wallet: str = ALICE,
    to_wallet: str = BOB,
    amount: float = 10.0,
    memo: str = "test",
) -> PolTransfer:
    return PolTransfer(
        transfer_id=transfer_id,
        from_wallet=from_wallet,
        to_wallet=to_wallet,
        amount_artcb=amount,
        memo=memo,
    )


class TestPolTransfer:

    def test_post_init_sets_timestamp(self):
        t = _make_transfer()
        assert t.timestamp != ""
        assert "T" in t.timestamp

    def test_to_pol_text_contains_fields(self):
        t = _make_transfer()
        text = t.to_pol_text()
        assert "ptx_test0001" in text
        assert ALICE in text
        assert BOB in text
        assert "10.00000000" in text
        assert "test" in text

    def test_to_pol_text_no_memo(self):
        t = _make_transfer(memo="")
        text = t.to_pol_text()
        assert "MOTIF" not in text

    def test_to_pol_text_with_reference(self):
        t = PolTransfer(
            transfer_id="ptx_ref",
            from_wallet=ALICE,
            to_wallet=BOB,
            amount_artcb=5.0,
            reference="INVOICE-2026-001",
        )
        text = t.to_pol_text()
        assert "INVOICE-2026-001" in text

    def test_to_dict_from_dict_roundtrip(self):
        t = _make_transfer()
        d = t.to_dict()
        assert d["transfer_id"] == "ptx_test0001"
        assert d["amount_artcb"] == 10.0
        t2 = PolTransfer.from_dict(d)
        assert t2.transfer_id == t.transfer_id
        assert t2.from_wallet == t.from_wallet
        assert t2.to_wallet == t.to_wallet
        assert t2.amount_artcb == t.amount_artcb
        assert t2.memo == t.memo

    def test_to_dict_optional_fields_defaults(self):
        t = PolTransfer.from_dict({
            "transfer_id": "ptx_minimal",
            "from_wallet": ALICE,
            "to_wallet": BOB,
            "amount_artcb": 1.0,
        })
        assert t.memo == ""
        assert t.reference == ""
        assert t.block_index is None
        assert t.pol_score == 0.0


# ─────────────────────────────────────────────────────────────────────────────
#  TransferLedger (fichier temporaire JSONL)
# ─────────────────────────────────────────────────────────────────────────────

class TestTransferLedger:

    def _ledger(self, tmp_path: Path) -> TransferLedger:
        return TransferLedger(path=str(tmp_path / "test_transfers.jsonl"))

    def test_append_and_all_transfers(self, tmp_path):
        ledger = self._ledger(tmp_path)
        t = _make_transfer()
        ledger.append(t)
        all_t = ledger.all_transfers()
        assert len(all_t) == 1
        assert all_t[0].transfer_id == "ptx_test0001"

    def test_append_multiple(self, tmp_path):
        ledger = self._ledger(tmp_path)
        for i in range(5):
            ledger.append(_make_transfer(transfer_id=f"ptx_{i:04d}", amount=float(i + 1)))
        assert len(ledger.all_transfers()) == 5

    def test_by_address_from(self, tmp_path):
        ledger = self._ledger(tmp_path)
        ledger.append(_make_transfer("ptx_1", ALICE, BOB, 10.0))
        ledger.append(_make_transfer("ptx_2", BOB, CAROL, 5.0))
        ledger.append(_make_transfer("ptx_3", CAROL, ALICE, 2.0))
        alice_transfers = ledger.by_address(ALICE)
        assert len(alice_transfers) == 2  # ptx_1 (from) + ptx_3 (to)

    def test_by_address_excludes_unrelated(self, tmp_path):
        ledger = self._ledger(tmp_path)
        ledger.append(_make_transfer("ptx_x", BOB, CAROL, 1.0))
        assert len(ledger.by_address(ALICE)) == 0

    def test_by_id_found(self, tmp_path):
        ledger = self._ledger(tmp_path)
        ledger.append(_make_transfer("ptx_findme"))
        t = ledger.by_id("ptx_findme")
        assert t is not None
        assert t.transfer_id == "ptx_findme"

    def test_by_id_not_found(self, tmp_path):
        ledger = self._ledger(tmp_path)
        assert ledger.by_id("ghost") is None

    def test_balance_of_positive(self, tmp_path):
        ledger = self._ledger(tmp_path)
        # Alice reçoit 50, envoie 20
        ledger.append(_make_transfer("ptx_a", BOB, ALICE, 50.0))
        ledger.append(_make_transfer("ptx_b", ALICE, CAROL, 20.0))
        balance = ledger.balance_of(ALICE)
        assert balance == pytest.approx(30.0)

    def test_balance_of_zero_initial(self, tmp_path):
        ledger = self._ledger(tmp_path)
        assert ledger.balance_of(ALICE) == 0.0

    def test_balance_of_negative_allowed(self, tmp_path):
        ledger = self._ledger(tmp_path)
        ledger.append(_make_transfer("ptx_neg", ALICE, BOB, 100.0))
        # Alice commence à 0, envoie 100 → solde négatif
        assert ledger.balance_of(ALICE) == pytest.approx(-100.0)
        assert ledger.balance_of(BOB) == pytest.approx(100.0)

    def test_balance_precision(self, tmp_path):
        ledger = self._ledger(tmp_path)
        ledger.append(_make_transfer("ptx_prec1", BOB, ALICE, 0.00000001))
        ledger.append(_make_transfer("ptx_prec2", BOB, ALICE, 0.00000002))
        balance = ledger.balance_of(ALICE)
        assert balance == pytest.approx(0.00000003, abs=1e-9)

    def test_empty_ledger_no_file(self, tmp_path):
        ledger = self._ledger(tmp_path)
        assert ledger.all_transfers() == []

    def test_append_is_persistent(self, tmp_path):
        path = str(tmp_path / "persist.jsonl")
        ledger1 = TransferLedger(path=path)
        ledger1.append(_make_transfer("ptx_persist"))
        # Relire avec une nouvelle instance
        ledger2 = TransferLedger(path=path)
        assert len(ledger2.all_transfers()) == 1

    def test_append_corrupted_line_skipped(self, tmp_path):
        path = tmp_path / "corrupt.jsonl"
        path.write_text('{"transfer_id":"ptx_ok","from_wallet":"' + ALICE + '","to_wallet":"' + BOB + '","amount_artcb":1.0}\nNOT_JSON\n')
        ledger = TransferLedger(path=str(path))
        transfers = ledger.all_transfers()
        assert len(transfers) == 1
        assert transfers[0].transfer_id == "ptx_ok"
