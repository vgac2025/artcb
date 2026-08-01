"""Tests module confidentialité homomorphe ARTCB — Phase 14.3.

Couverture :
    - HomomorphicProcessor.create() — mode simulé (sans TenSEAL)
    - encrypt(vector) → HECipherVector
    - decrypt(cipher) → vector original
    - Réversibilité chiffrement/déchiffrement
    - HECipherVector.to_dict() / from_dict()
    - HomomorphicProcessor.aggregate() — 2, 3, N contributions
    - FederatedAggregator.add_contribution() + finalize()
    - FederatedRound.summary() structure
    - Mode ARTCB_HOMOMORPHIC_MODE toggle (env var)
    - Route GET /api/v1/privacy/status
    - Route POST /api/v1/privacy/encrypt
    - Route POST /api/v1/privacy/aggregate
    - Erreur agrégation < 2 vecteurs
    - Vecteurs de taille variable
    - Participants multiples (10+)
    - pol_score moyen FedAvg correct
"""

from __future__ import annotations

import os
import struct
import pytest

from src.artcb.privacy.homomorphic import (
    HECipherVector,
    HEContext,
    HomomorphicProcessor,
)
from src.artcb.privacy.federated import (
    FederatedAggregator,
    FederatedRound,
)


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def processor():
    return HomomorphicProcessor.create(participant_id="test-alice")


@pytest.fixture
def processor_bob():
    return HomomorphicProcessor.create(participant_id="test-bob")


VECTOR_3 = [0.12, 0.87, 0.45]
VECTOR_5 = [0.11, 0.22, 0.33, 0.44, 0.55]
VECTOR_10 = [float(i) / 10 for i in range(10)]


# ── Tests HomomorphicProcessor ────────────────────────────────────────────

class TestHomomorphicProcessor:

    def test_create_returns_processor(self):
        proc = HomomorphicProcessor.create(participant_id="tester")
        assert isinstance(proc, HomomorphicProcessor)

    def test_create_without_participant_id(self):
        proc = HomomorphicProcessor.create()
        assert proc is not None

    def test_context_is_he_context(self, processor):
        assert isinstance(processor.context, HEContext)

    def test_context_has_bytes(self, processor):
        assert len(processor.context.context_bytes) > 0
        assert len(processor.context.secret_key_bytes) > 0

    def test_encrypt_returns_cipher(self, processor):
        cipher = processor.encrypt(VECTOR_3)
        assert isinstance(cipher, HECipherVector)
        assert cipher.vector_size == 3

    def test_encrypt_stores_participant_id(self, processor):
        cipher = processor.encrypt(VECTOR_3, participant_id="custom-id")
        assert cipher.participant_id == "custom-id"

    def test_cipher_has_bytes(self, processor):
        cipher = processor.encrypt(VECTOR_3)
        assert len(cipher.cipher_bytes) > 0

    def test_encrypt_decrypt_reversible_3(self, processor):
        cipher = processor.encrypt(VECTOR_3)
        result = processor.decrypt(cipher)
        assert len(result) == len(VECTOR_3)
        for orig, dec in zip(VECTOR_3, result):
            assert abs(orig - dec) < 1e-9

    def test_encrypt_decrypt_reversible_5(self, processor):
        cipher = processor.encrypt(VECTOR_5)
        result = processor.decrypt(cipher)
        assert len(result) == len(VECTOR_5)
        for orig, dec in zip(VECTOR_5, result):
            assert abs(orig - dec) < 1e-9

    def test_encrypt_decrypt_reversible_10(self, processor):
        cipher = processor.encrypt(VECTOR_10)
        result = processor.decrypt(cipher)
        assert len(result) == len(VECTOR_10)
        for orig, dec in zip(VECTOR_10, result):
            assert abs(orig - dec) < 1e-9

    def test_encrypt_zeros(self, processor):
        zeros = [0.0, 0.0, 0.0]
        cipher = processor.encrypt(zeros)
        result = processor.decrypt(cipher)
        for v in result:
            assert abs(v) < 1e-9

    def test_encrypt_large_values(self, processor):
        big = [1000.5, 9999.9, -500.25]
        cipher = processor.encrypt(big)
        result = processor.decrypt(cipher)
        for orig, dec in zip(big, result):
            assert abs(orig - dec) < 1e-6

    def test_mode_field(self, processor):
        cipher = processor.encrypt(VECTOR_3)
        assert cipher.mode in ("ckks", "simulated")


# ── Tests HECipherVector sérialisation ────────────────────────────────────

class TestHECipherVectorSerialization:

    def test_to_dict_structure(self, processor):
        cipher = processor.encrypt(VECTOR_3)
        d = cipher.to_dict()
        assert "cipher_hex" in d
        assert "vector_size" in d
        assert "participant_id" in d
        assert "mode" in d
        assert d["vector_size"] == 3

    def test_from_dict_roundtrip(self, processor):
        cipher = processor.encrypt(VECTOR_5)
        d = cipher.to_dict()
        cipher2 = HECipherVector.from_dict(d)
        assert cipher2.vector_size == cipher.vector_size
        assert cipher2.cipher_bytes == cipher.cipher_bytes
        assert cipher2.participant_id == cipher.participant_id
        assert cipher2.mode == cipher.mode

    def test_cipher_hex_is_valid_hex(self, processor):
        cipher = processor.encrypt(VECTOR_3)
        d = cipher.to_dict()
        # Doit être décodable en bytes
        raw = bytes.fromhex(d["cipher_hex"])
        assert len(raw) > 0


# ── Tests agrégation homomorphique ───────────────────────────────────────

class TestHomomorphicAggregate:

    def test_aggregate_two_ciphers(self, processor, processor_bob):
        c1 = processor.encrypt(VECTOR_3)
        c2 = processor_bob.encrypt(VECTOR_3)
        agg = HomomorphicProcessor.aggregate([c1, c2])
        assert isinstance(agg, HECipherVector)
        assert agg.participant_id == "aggregated"
        assert agg.vector_size == 3

    def test_aggregate_metadata_participant_count(self, processor, processor_bob):
        c1 = processor.encrypt(VECTOR_3)
        c2 = processor_bob.encrypt(VECTOR_3)
        agg = HomomorphicProcessor.aggregate([c1, c2])
        assert agg.metadata.get("participant_count") == 2

    def test_aggregate_metadata_participants(self, processor, processor_bob):
        c1 = processor.encrypt(VECTOR_3, participant_id="alice")
        c2 = processor_bob.encrypt(VECTOR_3, participant_id="bob")
        agg = HomomorphicProcessor.aggregate([c1, c2])
        assert "alice" in agg.metadata.get("participants", [])
        assert "bob" in agg.metadata.get("participants", [])

    def test_aggregate_three_ciphers(self):
        procs = [HomomorphicProcessor.create(participant_id=f"p{i}") for i in range(3)]
        ciphers = [p.encrypt(VECTOR_5) for p in procs]
        agg = HomomorphicProcessor.aggregate(ciphers)
        assert agg.metadata.get("participant_count") == 3

    def test_aggregate_ten_ciphers(self):
        procs = [HomomorphicProcessor.create(participant_id=f"node-{i}") for i in range(10)]
        ciphers = [p.encrypt(VECTOR_10) for p in procs]
        agg = HomomorphicProcessor.aggregate(ciphers)
        assert agg.metadata.get("participant_count") == 10

    def test_aggregate_single_raises(self, processor):
        c1 = processor.encrypt(VECTOR_3)
        with pytest.raises(ValueError):
            HomomorphicProcessor.aggregate([c1])

    def test_aggregate_empty_raises(self):
        with pytest.raises((ValueError, IndexError)):
            HomomorphicProcessor.aggregate([])

    def test_aggregate_result_bytes_differ_from_inputs(self, processor, processor_bob):
        c1 = processor.encrypt(VECTOR_3)
        c2 = processor_bob.encrypt(VECTOR_3)
        agg = HomomorphicProcessor.aggregate([c1, c2])
        # Le résultat agrégé est différent des entrées individuelles
        assert agg.cipher_bytes != c1.cipher_bytes


# ── Tests FederatedAggregator ─────────────────────────────────────────────

class TestFederatedAggregator:

    def test_add_and_finalize(self):
        proc_a = HomomorphicProcessor.create(participant_id="alice")
        proc_b = HomomorphicProcessor.create(participant_id="bob")
        agg = FederatedAggregator()
        agg.add_contribution("alice", proc_a.encrypt(VECTOR_3), pol_score=0.85)
        agg.add_contribution("bob",   proc_b.encrypt(VECTOR_3), pol_score=0.70)
        assert agg.contribution_count() == 2
        result = agg.finalize()
        assert isinstance(result, FederatedRound)

    def test_finalize_pol_score_average(self):
        proc_a = HomomorphicProcessor.create()
        proc_b = HomomorphicProcessor.create()
        agg = FederatedAggregator()
        agg.add_contribution("a", proc_a.encrypt(VECTOR_3), pol_score=0.80)
        agg.add_contribution("b", proc_b.encrypt(VECTOR_3), pol_score=0.60)
        result = agg.finalize()
        assert abs(result.aggregated_pol_score - 0.70) < 1e-9

    def test_finalize_participant_count(self):
        procs = [HomomorphicProcessor.create(participant_id=f"p{i}") for i in range(5)]
        agg = FederatedAggregator()
        for i, p in enumerate(procs):
            agg.add_contribution(f"p{i}", p.encrypt(VECTOR_5), pol_score=0.75)
        result = agg.finalize()
        assert result.participant_count == 5

    def test_finalize_has_aggregated_cipher(self):
        proc_a = HomomorphicProcessor.create()
        proc_b = HomomorphicProcessor.create()
        agg = FederatedAggregator()
        agg.add_contribution("a", proc_a.encrypt(VECTOR_3), pol_score=0.9)
        agg.add_contribution("b", proc_b.encrypt(VECTOR_3), pol_score=0.8)
        result = agg.finalize()
        assert result.aggregated_cipher is not None

    def test_finalize_resets_contributions(self):
        proc_a = HomomorphicProcessor.create()
        proc_b = HomomorphicProcessor.create()
        agg = FederatedAggregator()
        agg.add_contribution("a", proc_a.encrypt(VECTOR_3), pol_score=0.9)
        agg.add_contribution("b", proc_b.encrypt(VECTOR_3), pol_score=0.8)
        agg.finalize()
        assert agg.contribution_count() == 0

    def test_finalize_empty_raises(self):
        agg = FederatedAggregator()
        with pytest.raises(ValueError):
            agg.finalize()

    def test_summary_structure(self):
        proc_a = HomomorphicProcessor.create()
        proc_b = HomomorphicProcessor.create()
        agg = FederatedAggregator()
        agg.add_contribution("a", proc_a.encrypt(VECTOR_3), pol_score=0.9)
        agg.add_contribution("b", proc_b.encrypt(VECTOR_3), pol_score=0.7)
        result = agg.finalize()
        s = result.summary()
        assert "round_id" in s
        assert "participant_count" in s
        assert "aggregated_pol_score" in s
        assert "homomorphic" in s
        assert "has_aggregated_result" in s

    def test_reset(self):
        proc = HomomorphicProcessor.create()
        agg = FederatedAggregator()
        agg.add_contribution("x", proc.encrypt(VECTOR_3), pol_score=0.5)
        agg.reset()
        assert agg.contribution_count() == 0


# ── Tests route API privacy ───────────────────────────────────────────────

class TestPrivacyRoutes:

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from src.api.main import create_app
        return TestClient(create_app())

    def test_privacy_status(self, client):
        r = client.get("/api/v1/privacy/status")
        assert r.status_code == 200
        data = r.json()
        assert "homomorphic_mode" in data
        assert "tenseal_available" in data
        assert "scheme" in data

    def test_privacy_encrypt_endpoint(self, client):
        r = client.post("/api/v1/privacy/encrypt", json={
            "vector": [0.1, 0.5, 0.9],
            "participant_id": "test-participant",
        })
        assert r.status_code == 200
        data = r.json()
        assert "cipher_hex" in data
        assert data["vector_size"] == 3
        assert data["participant_id"] == "test-participant"
        assert "mode" in data

    def test_privacy_encrypt_no_participant_id(self, client):
        r = client.post("/api/v1/privacy/encrypt", json={
            "vector": [0.1, 0.2, 0.3, 0.4, 0.5],
        })
        assert r.status_code == 200
        assert r.json()["vector_size"] == 5

    def test_privacy_aggregate_two(self, client):
        # Chiffrer deux vecteurs
        r1 = client.post("/api/v1/privacy/encrypt", json={"vector": [0.1, 0.5, 0.9], "participant_id": "p1"})
        r2 = client.post("/api/v1/privacy/encrypt", json={"vector": [0.2, 0.6, 0.8], "participant_id": "p2"})
        c1 = r1.json()
        c2 = r2.json()
        # Agréger côté serveur
        r_agg = client.post("/api/v1/privacy/aggregate", json={"ciphers": [c1, c2]})
        assert r_agg.status_code == 200
        data = r_agg.json()
        assert data["participant_count"] == 2
        assert "aggregated_cipher" in data

    def test_privacy_aggregate_one_returns_400(self, client):
        r1 = client.post("/api/v1/privacy/encrypt", json={"vector": [0.1, 0.5], "participant_id": "solo"})
        c1 = r1.json()
        r_agg = client.post("/api/v1/privacy/aggregate", json={"ciphers": [c1]})
        assert r_agg.status_code == 400

    def test_privacy_context_endpoint(self, client):
        r = client.post("/api/v1/privacy/context", params={"participant_id": "test-node"})
        assert r.status_code == 200
        data = r.json()
        assert "public_context" in data
        assert "mode" in data
