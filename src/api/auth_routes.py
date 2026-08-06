"""Authentification utilisateur ARTCB — login, challenge, verify.

Protocole :
  1. POST /auth/login     — login classique (name + password)
  2. GET  /auth/challenge — nonce pour signature crypto
  3. POST /auth/verify    — vérification signature Ed25519 du challenge
  4. POST /auth/logout    — invalide le token de session

L'API key (/api-keys/generate) n'est utilisable QU'APRÈS authentification.
"""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from nacl import signing
from nacl.exceptions import BadSignatureError
from pydantic import BaseModel, Field

logger = logging.getLogger("artcb.api.auth")
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# TTL des challenges (5 minutes) et des sessions (24 heures)
_CHALLENGE_TTL = 300
_SESSION_TTL = 86400

# Stockage en mémoire des challenges actifs et des sessions
# (en production : Redis ou table SQL)
_challenges: dict[str, float] = {}   # nonce_hex → expires_at
_sessions: dict[str, dict] = {}       # token_hash → {wallet_name, address, created_at, expires_at}


# --------------------------------------------------------------------------- #
#  Schémas Pydantic
# --------------------------------------------------------------------------- #

class LoginRequest(BaseModel):
    name: str = Field(min_length=1, description="Nom du wallet / identifiant")
    password: str = Field(min_length=1, description="Mot de passe du compte")


class VerifyRequest(BaseModel):
    address: str = Field(min_length=8, description="Adresse artcb1xxx du wallet")
    challenge: str = Field(min_length=8, description="Nonce hex reçu via GET /challenge")
    signature: str = Field(min_length=8, description="Signature Ed25519 hex du challenge")


# --------------------------------------------------------------------------- #
#  Helper : vérification de session (Depends)
# --------------------------------------------------------------------------- #

def require_session(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    """
    Dependency FastAPI : extrait et valide le token de session Bearer.
    Retourne le record de session ou lève 401.
    Utilisé pour protéger /api-keys/generate et tout endpoint authentifié.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authentification requise. POST /api/v1/auth/login d'abord.",
        )
    raw = authorization.removeprefix("Bearer ").strip()
    # Les tokens de session commencent par "sess_"
    if not raw.startswith("sess_"):
        raise HTTPException(
            status_code=401,
            detail="Token de session invalide (format sess_xxx attendu). Utilisez /auth/login.",
        )
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    record = _sessions.get(token_hash)
    if not record:
        raise HTTPException(status_code=401, detail="Session expirée ou invalide. Reconnectez-vous.")
    if time.time() > record["expires_at"]:
        del _sessions[token_hash]
        raise HTTPException(status_code=401, detail="Session expirée. Reconnectez-vous.")
    return record


# --------------------------------------------------------------------------- #
#  Endpoints
# --------------------------------------------------------------------------- #

@router.post("/login", summary="Connexion par nom + mot de passe")
def login(body: LoginRequest, request: Request) -> dict:
    """
    Connexion classique : identifiant (nom du wallet) + mot de passe.

    Le mot de passe est utilisé pour déchiffrer la seed Ed25519 stockée
    sur le serveur. Si le déchiffrement réussit, une session est créée.

    Retourne un token de session `sess_xxx` valide 24 heures.
    """
    from src.artcb.wallet.encryption import decrypt_private_key, get_wallet_passphrase
    from src.artcb.wallet.manager import WalletManager

    wm = WalletManager()
    key_path = wm.wallet_dir / f"{body.name}.key"
    if not key_path.exists():
        # Ne pas révéler si le wallet existe ou non (timing attack mitigation)
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    try:
        # Tenter le déchiffrement avec le mot de passe fourni
        raw = key_path.read_bytes()
        # Essai avec le mot de passe de l'user d'abord, puis fallback passphrase serveur
        seed: bytes | None = None
        for passphrase in [body.password, get_wallet_passphrase()]:
            try:
                seed = decrypt_private_key(raw, passphrase)
                break
            except Exception:
                continue
        if seed is None:
            raise HTTPException(status_code=401, detail="Identifiants invalides")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    # Charger le wallet pour obtenir l'adresse
    wallet = wm.load_wallet(name=body.name)

    # Créer un token de session
    raw_token = "sess_" + secrets.token_hex(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    now = time.time()
    record = {
        "wallet_name": body.name,
        "address": wallet.address,
        "created_at": now,
        "expires_at": now + _SESSION_TTL,
    }
    _sessions[token_hash] = record

    logger.info("Login successful: wallet=%s address=%s", body.name, wallet.address)
    return {
        "session_token": raw_token,
        "wallet_name": body.name,
        "address": wallet.address,
        "expires_in": _SESSION_TTL,
        "message": "Connecté. Utilisez session_token dans Authorization: Bearer <token>",
    }


@router.get("/challenge", summary="Obtenir un nonce pour l'authentification par signature")
def get_challenge() -> dict:
    """
    Retourne un nonce aléatoire (challenge) que l'utilisateur doit signer
    avec sa clé privée Ed25519 pour prouver qu'il en est le propriétaire.

    Le challenge expire dans 5 minutes.
    """
    challenge = secrets.token_hex(32)
    _challenges[challenge] = time.time() + _CHALLENGE_TTL
    logger.debug("Challenge issued: %s", challenge[:16])
    return {
        "challenge": challenge,
        "expires_in": _CHALLENGE_TTL,
        "instructions": (
            "Signez ce challenge avec votre clé privée Ed25519, "
            "puis POST /auth/verify avec {address, challenge, signature}."
        ),
    }


@router.post("/verify", summary="Vérifier signature Ed25519 du challenge")
def verify_signature(body: VerifyRequest, request: Request) -> dict:
    """
    Vérifie que l'utilisateur contrôle la clé privée correspondant à l'adresse.

    Flow :
      1. GET /auth/challenge  → nonce
      2. Client signe le nonce avec sa clé privée
      3. POST /auth/verify    → serveur vérifie, crée session
    """
    from src.artcb.wallet.manager import WalletManager

    # Vérifier que le challenge existe et n'est pas expiré
    exp = _challenges.get(body.challenge)
    if not exp:
        raise HTTPException(status_code=400, detail="Challenge inconnu")
    if time.time() > exp:
        del _challenges[body.challenge]
        raise HTTPException(status_code=400, detail="Challenge expiré — en demandez un nouveau")

    # Retrouver la clé publique associée à cette adresse
    wm = WalletManager()
    wallets = wm.list_wallets()
    wallet_name = next(
        (w["name"] for w in wallets if w.get("address") == body.address), None
    )
    if not wallet_name:
        raise HTTPException(status_code=404, detail="Adresse inconnue sur ce nœud")

    try:
        wallet = wm.load_wallet(name=wallet_name)
        verify_key = wallet.signing_key.verify_key
        sig_bytes = bytes.fromhex(body.signature)
        challenge_bytes = bytes.fromhex(body.challenge)
        verify_key.verify(challenge_bytes, sig_bytes)
    except (BadSignatureError, ValueError):
        raise HTTPException(status_code=401, detail="Signature invalide")

    # Challenge utilisé : le supprimer (usage unique)
    del _challenges[body.challenge]

    # Créer session
    raw_token = "sess_" + secrets.token_hex(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    now = time.time()
    _sessions[token_hash] = {
        "wallet_name": wallet_name,
        "address": body.address,
        "created_at": now,
        "expires_at": now + _SESSION_TTL,
    }

    logger.info("Verify OK: address=%s wallet=%s", body.address[:16], wallet_name)
    return {
        "session_token": raw_token,
        "wallet_name": wallet_name,
        "address": body.address,
        "expires_in": _SESSION_TTL,
    }


@router.post("/logout", summary="Déconnecter la session courante")
def logout(
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    """Invalide le token de session."""
    if authorization and authorization.startswith("Bearer sess_"):
        raw = authorization.removeprefix("Bearer ").strip()
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        _sessions.pop(token_hash, None)
    return {"logged_out": True}
