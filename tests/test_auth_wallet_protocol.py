"""Tests authentification utilisateur ARTCB — rapport 107.

Protocole testé :
  1. POST /wallet/create → retourne seed_hex + WARNING
  2. POST /auth/login → session token
  3. GET  /auth/challenge + POST /auth/verify → session token (voie crypto)
  4. POST /api-keys/generate SANS session → 401
  5. POST /api-keys/generate AVEC session → API key liée au wallet
  6. POST /auth/logout → session invalide
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from nacl import encoding, signing


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ARTCB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ARTCB_LOG_DIR", str(tmp_path / "logs"))
    from api.main import create_app
    app = create_app()
    return TestClient(app)


# --------------------------------------------------------------------------- #
#  1. wallet/create retourne seed_hex
# --------------------------------------------------------------------------- #

def test_wallet_create_returns_seed(client: TestClient) -> None:
    """La clé privée (seed_hex) doit être retournée à la création."""
    r = client.post("/api/v1/wallet/create", json={"name": "alice_test"})
    assert r.status_code == 200
    data = r.json()

    # Champs publics toujours présents
    assert "address" in data
    assert data["address"].startswith("artcb1")
    assert "public_key_hex" in data

    # NOUVEAU : seed_hex présent + WARNING
    assert "seed_hex" in data, "seed_hex DOIT être retourné à la création (rapport 107)"
    assert len(data["seed_hex"]) == 64, "seed Ed25519 = 32 bytes = 64 hex chars"
    assert "WARNING" in data, "Le WARNING de sauvegarde doit être présent"
    assert "SAUVEGARDEZ" in data["WARNING"]


def test_wallet_create_seed_is_valid_ed25519(client: TestClient) -> None:
    """La seed retournée doit être une vraie clé Ed25519 qui correspond à l'adresse."""
    r = client.post("/api/v1/wallet/create", json={"name": "bob_test"})
    assert r.status_code == 200
    data = r.json()

    # Vérifier que la seed reconstruit la clé publique
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
    """Login avec nom + mot de passe (fallback passphrase serveur)."""
    # Créer le wallet d'abord
    client.post("/api/v1/wallet/create", json={"name": "carol_test"})

    # Login
    r = client.post("/api/v1/auth/login", json={"name": "carol_test", "password": "mauvais_pass"})
    # Le fallback passphrase serveur doit permettre la connexion en mode dev
    assert r.status_code == 200
    data = r.json()
    assert "session_token" in data
    assert data["session_token"].startswith("sess_")
    assert data["wallet_name"] == "carol_test"
    assert data["address"].startswith("artcb1")


def test_auth_login_unknown_wallet(client: TestClient) -> None:
    """Login sur un wallet inexistant → 401."""
    r = client.post("/api/v1/auth/login", json={"name": "fantome", "password": "abc12345"})
    assert r.status_code == 401


# --------------------------------------------------------------------------- #
#  3. auth/challenge + auth/verify
# --------------------------------------------------------------------------- #

def test_auth_challenge_verify(client: TestClient) -> None:
    """Authentification par signature Ed25519 du challenge."""
    # Créer wallet et récupérer seed
    cr = client.post("/api/v1/wallet/create", json={"name": "dave_test"})
    seed_hex = cr.json()["seed_hex"]
    address = cr.json()["address"]

    # Obtenir un challenge
    ch_r = client.get("/api/v1/auth/challenge")
    assert ch_r.status_code == 200
    challenge = ch_r.json()["challenge"]

    # Signer le challenge avec la clé privée
    sk = signing.SigningKey(bytes.fromhex(seed_hex))
    sig = sk.sign(bytes.fromhex(challenge)).signature.hex()

    # Vérifier
    v_r = client.post("/api/v1/auth/verify", json={
        "address": address,
        "challenge": challenge,
        "signature": sig,
    })
    assert v_r.status_code == 200
    assert v_r.json()["session_token"].startswith("sess_")


def test_auth_verify_bad_signature(client: TestClient) -> None:
    """Signature invalide → 401."""
    cr = client.post("/api/v1/wallet/create", json={"name": "eve_test"})
    address = cr.json()["address"]

    ch_r = client.get("/api/v1/auth/challenge")
    challenge = ch_r.json()["challenge"]

    # Signature bidon
    v_r = client.post("/api/v1/auth/verify", json={
        "address": address,
        "challenge": challenge,
        "signature": "00" * 64,
    })
    assert v_r.status_code == 401


def test_auth_challenge_replay_blocked(client: TestClient) -> None:
    """Un challenge ne peut être utilisé qu'une seule fois (anti-replay)."""
    cr = client.post("/api/v1/wallet/create", json={"name": "frank_test"})
    seed_hex = cr.json()["seed_hex"]
    address = cr.json()["address"]

    ch_r = client.get("/api/v1/auth/challenge")
    challenge = ch_r.json()["challenge"]
    sk = signing.SigningKey(bytes.fromhex(seed_hex))
    sig = sk.sign(bytes.fromhex(challenge)).signature.hex()

    # Première utilisation → OK
    v1 = client.post("/api/v1/auth/verify", json={"address": address, "challenge": challenge, "signature": sig})
    assert v1.status_code == 200

    # Deuxième utilisation du même challenge → 400
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
    # Créer wallet + login
    client.post("/api/v1/wallet/create", json={"name": "grace_test"})
    login_r = client.post("/api/v1/auth/login", json={"name": "grace_test", "password": "x"})
    sess_token = login_r.json()["session_token"]

    # Générer l'API key avec le token de session
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
    client.post("/api/v1/wallet/create", json={"name": "henry_test"})
    login_r = client.post("/api/v1/auth/login", json={"name": "henry_test", "password": "x"})
    sess_token = login_r.json()["session_token"]

    # Logout
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
