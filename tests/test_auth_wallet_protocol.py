"""Tests authentification utilisateur ARTCB — rapports 107, 108, 111.

Protocole testé :
  1. POST /wallet/create {name, password} → retourne seed_hex + WARNING
  2. POST /wallet/create sans password → 422 (champ obligatoire)
  3. POST /auth/login avec bon mot de passe → session token
  4. POST /auth/login avec mauvais mot de passe → 401 (pas de fallback)
  5. GET  /auth/challenge + POST /auth/verify → session token (voie crypto)
  6. POST /api-keys/generate SANS session → 401
  7. POST /api-keys/generate AVEC session → API key liée au wallet
  8. POST /auth/logout → session invalide
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from nacl import encoding, signing

TEST_PASSWORD = "monMotDePasse42!"  # ≥ 8 chars


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ARTCB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ARTCB_LOG_DIR", str(tmp_path / "logs"))
    from api.main import create_app
    app = create_app()
    return TestClient(app)


# --------------------------------------------------------------------------- #
#  1. wallet/create retourne seed_hex — mot de passe obligatoire
# --------------------------------------------------------------------------- #

def test_wallet_create_returns_seed(client: TestClient) -> None:
    """La clé privée (seed_hex) doit être retournée à la création."""
    r = client.post("/api/v1/wallet/create", json={"name": "alice_test", "password": TEST_PASSWORD})
    assert r.status_code == 200
    data = r.json()

    assert "address" in data
    assert data["address"].startswith("artcb1")
    assert "public_key_hex" in data

    # seed_hex présente + WARNING
    assert "seed_hex" in data, "seed_hex DOIT être retourné à la création"
    assert len(data["seed_hex"]) == 64, "seed Ed25519 = 32 bytes = 64 hex chars"
    assert "WARNING" in data
    assert "SAUVEGARDEZ" in data["WARNING"]


def test_wallet_create_without_password_rejected(client: TestClient) -> None:
    """Créer un wallet sans mot de passe doit retourner 422 — password obligatoire."""
    r = client.post("/api/v1/wallet/create", json={"name": "no_pwd_wallet"})
    assert r.status_code == 422, (
        "POST /wallet/create sans password DOIT retourner 422 — champ obligatoire depuis rapport 111"
    )


def test_wallet_create_seed_is_valid_ed25519(client: TestClient) -> None:
    """La seed retournée doit être une vraie clé Ed25519 qui correspond à l'adresse."""
    r = client.post("/api/v1/wallet/create", json={"name": "bob_test", "password": TEST_PASSWORD})
    assert r.status_code == 200
    data = r.json()

    seed = bytes.fromhex(data["seed_hex"])
    sk = signing.SigningKey(seed)
    pub_hex = sk.verify_key.encode().hex()
    assert pub_hex == data["public_key_hex"], (
        "La seed retournée doit correspondre à la clé publique du wallet"
    )


# --------------------------------------------------------------------------- #
#  2. auth/login — connexion classique
# --------------------------------------------------------------------------- #

def test_auth_login_success(client: TestClient) -> None:
    """Login avec le bon mot de passe → session token."""
    client.post("/api/v1/wallet/create", json={"name": "carol_test", "password": TEST_PASSWORD})

    r = client.post("/api/v1/auth/login", json={"name": "carol_test", "password": TEST_PASSWORD})
    assert r.status_code == 200
    data = r.json()
    assert "session_token" in data
    assert data["session_token"].startswith("sess_")
    assert data["wallet_name"] == "carol_test"
    assert data["address"].startswith("artcb1")


def test_auth_login_wrong_password_rejected(client: TestClient) -> None:
    """Login avec un mauvais mot de passe → 401.
    SÉCURITÉ : pas de fallback sur la passphrase serveur.
    """
    client.post("/api/v1/wallet/create", json={"name": "carol2_test", "password": TEST_PASSWORD})

    r = client.post("/api/v1/auth/login", json={"name": "carol2_test", "password": "mauvais_pass"})
    assert r.status_code == 401, (
        "Un mauvais mot de passe DOIT être rejeté — pas de fallback passphrase serveur"
    )


def test_auth_login_unknown_wallet(client: TestClient) -> None:
    """Login sur un wallet inexistant → 401."""
    r = client.post("/api/v1/auth/login", json={"name": "fantome", "password": "abc12345"})
    assert r.status_code == 401


# --------------------------------------------------------------------------- #
#  3. auth/challenge + auth/verify
# --------------------------------------------------------------------------- #

def test_auth_challenge_verify(client: TestClient) -> None:
    """Authentification par signature Ed25519 du challenge."""
    cr = client.post("/api/v1/wallet/create", json={"name": "dave_test", "password": TEST_PASSWORD})
    seed_hex = cr.json()["seed_hex"]
    address = cr.json()["address"]

    ch_r = client.get("/api/v1/auth/challenge")
    assert ch_r.status_code == 200
    challenge = ch_r.json()["challenge"]

    sk = signing.SigningKey(bytes.fromhex(seed_hex))
    sig = sk.sign(bytes.fromhex(challenge)).signature.hex()

    v_r = client.post("/api/v1/auth/verify", json={
        "address": address,
        "challenge": challenge,
        "signature": sig,
    })
    assert v_r.status_code == 200
    assert v_r.json()["session_token"].startswith("sess_")


def test_auth_verify_bad_signature(client: TestClient) -> None:
    """Signature invalide → 401."""
    cr = client.post("/api/v1/wallet/create", json={"name": "eve_test", "password": TEST_PASSWORD})
    address = cr.json()["address"]

    ch_r = client.get("/api/v1/auth/challenge")
    challenge = ch_r.json()["challenge"]

    v_r = client.post("/api/v1/auth/verify", json={
        "address": address,
        "challenge": challenge,
        "signature": "00" * 64,
    })
    assert v_r.status_code == 401


def test_auth_challenge_replay_blocked(client: TestClient) -> None:
    """Un challenge ne peut être utilisé qu'une seule fois (anti-replay)."""
    cr = client.post("/api/v1/wallet/create", json={"name": "frank_test", "password": TEST_PASSWORD})
    seed_hex = cr.json()["seed_hex"]
    address = cr.json()["address"]

    ch_r = client.get("/api/v1/auth/challenge")
    challenge = ch_r.json()["challenge"]
    sk = signing.SigningKey(bytes.fromhex(seed_hex))
    sig = sk.sign(bytes.fromhex(challenge)).signature.hex()

    v1 = client.post("/api/v1/auth/verify", json={"address": address, "challenge": challenge, "signature": sig})
    assert v1.status_code == 200

    # Deuxième utilisation → 400
    v2 = client.post("/api/v1/auth/verify", json={"address": address, "challenge": challenge, "signature": sig})
    assert v2.status_code == 400


# --------------------------------------------------------------------------- #
#  4. api-keys/generate : SANS session → 401
# --------------------------------------------------------------------------- #

def test_apikey_generate_without_auth_rejected(client: TestClient) -> None:
    """Générer une API key SANS session doit être refusé (401)."""
    r = client.post("/api/v1/api-keys/generate", json={"label": "test_key"})
    assert r.status_code == 401, (
        "POST /api-keys/generate DOIT exiger une session (rapport 107 — P0-AUTH-3)"
    )


# --------------------------------------------------------------------------- #
#  5. api-keys/generate : AVEC session → API key liée au wallet
# --------------------------------------------------------------------------- #

def test_apikey_generate_with_auth_success(client: TestClient) -> None:
    """Générer une API key AVEC session valide → succès, clé liée au wallet."""
    client.post("/api/v1/wallet/create", json={"name": "grace_test", "password": TEST_PASSWORD})
    login_r = client.post("/api/v1/auth/login", json={"name": "grace_test", "password": TEST_PASSWORD})
    sess_token = login_r.json()["session_token"]

    r = client.post(
        "/api/v1/api-keys/generate",
        json={"label": "Mon ChatGPT"},
        headers={"Authorization": f"Bearer {sess_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["token"].startswith("artcb_")
    assert data["owner_wallet"] == "grace_test"
    assert "owner_address" in data
    assert data["owner_address"].startswith("artcb1")


# --------------------------------------------------------------------------- #
#  6. auth/logout → session invalide
# --------------------------------------------------------------------------- #

def test_auth_logout(client: TestClient) -> None:
    """Après logout, le token de session ne peut plus être utilisé."""
    client.post("/api/v1/wallet/create", json={"name": "henry_test", "password": TEST_PASSWORD})
    login_r = client.post("/api/v1/auth/login", json={"name": "henry_test", "password": TEST_PASSWORD})
    sess_token = login_r.json()["session_token"]

    out = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {sess_token}"})
    assert out.status_code == 200
    assert out.json()["logged_out"] is True

    # Tenter de générer une API key → 401
    r = client.post(
        "/api/v1/api-keys/generate",
        json={"label": "après logout"},
        headers={"Authorization": f"Bearer {sess_token}"},
    )
    assert r.status_code == 401
