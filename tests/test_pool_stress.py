"""Tests stress pool — volume chunks et jobs concurrents."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ARTCB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ARTCB_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("ARTCB_MIN_BLOCK_INTERVAL_SEC", "0")
    return TestClient(create_app())


def test_pool_stress_many_chunks(client: TestClient) -> None:
    client.post("/api/v1/wallet/create", json={"name": "stress_wallet", "password": "devpassword1"})
    status = client.get("/api/v1/p2p/status").json()
    # Texte long → nombreux chunks
    text = "Segment ARTCB stress. " * 80
    r = client.post(
        "/api/v1/pool/jobs",
        json={
            "text": text,
            "visibility": "private",
            "workers": [{
                "node_id": status["node_id"],
                "kem_public_hex": status["kem_public_key_hex"],
                "base_url": "http://testserver",
            }],
            "chunk_chars": 100,
            "auto_dispatch": False,
            "encrypt_transport": True,
        },
    )
    assert r.status_code == 200, r.text
    job = r.json()["job"]
    assert len(job["chunks"]) >= 10
    for chunk in job["chunks"]:
        assert chunk["envelope"]["kem_alg"] == "ML-KEM-768"


def test_pool_stress_concurrent_jobs(client: TestClient) -> None:
    status = client.get("/api/v1/p2p/status").json()
    worker = {
        "node_id": status["node_id"],
        "kem_public_hex": status["kem_public_key_hex"],
        "base_url": "http://testserver",
    }
    job_ids = []
    for i in range(5):
        r = client.post(
            "/api/v1/pool/jobs",
            json={
                "text": f"Job stress concurrent {i}. " + "Donnée. " * 20,
                "visibility": "private",
                "workers": [worker],
                "auto_dispatch": False,
            },
        )
        assert r.status_code == 200, r.text
        job_ids.append(r.json()["job"]["job_id"])
    listed = client.get("/api/v1/pool/jobs").json()
    assert listed["count"] >= 5
    assert len(set(job_ids)) == 5


def test_pool_stress_finalize_after_batch_process(client: TestClient) -> None:
    w = client.post("/api/v1/wallet/create", json={"name": "batch_wallet", "password": "test_pwd_123"}).json()
    text = "Batch process stress. " * 30
    created = client.post(
        "/api/v1/pool/run",
        json={
            "text": text,
            "use_distributed_pool": True,
            "encrypt_transport": True,
            "visibility": "public",
            "actor_address": w["address"],
            "wallet_name": "batch_wallet",
            "wallet_password": "test_pwd_123",
            "auto_finalize": True,
            "chunk_chars": 100,
        },
    )
    assert created.status_code == 200, created.text
    data = created.json()
    assert data["job_status"] == "completed"
    assert data["block_index"] is not None
