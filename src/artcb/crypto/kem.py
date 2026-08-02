"""Post-quantum key encapsulation — ML-KEM-768 (NIST) via liboqs.

Fallback automatique : si liboqs-python n'est pas installé, utilise X25519 ECDH
(via la bibliothèque `cryptography` déjà requise). Zéro dépendance supplémentaire.
Mode PQC activé/désactivé via ARTCB_KEM_ENABLED (défaut=true) — mais le fallback
s'active AUTOMATIQUEMENT si liboqs absent, sans exception fatale.
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from typing import Final

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    PrivateFormat,
    NoEncryption,
)

logger = logging.getLogger("artcb.crypto.kem")

KEM_ALGORITHM: Final[str] = "ML-KEM-768"
KEM_FALLBACK_ALGORITHM: Final[str] = "X25519-fallback"
ENV_KEM_ENABLED = "ARTCB_KEM_ENABLED"
NONCE_LEN = 12
POOL_CHUNK_CONTEXT: Final[bytes] = b"artcb-pool-chunk-v1"
POOL_RESULT_CONTEXT: Final[bytes] = b"artcb-pool-result-v1"

# Cache de disponibilité liboqs (testé une seule fois au démarrage)
_OQS_AVAILABLE: bool | None = None


class KEMError(Exception):
    """ML-KEM operation failed."""


def kem_enabled() -> bool:
    return os.getenv(ENV_KEM_ENABLED, "true").lower() in ("1", "true", "yes", "on")


def _oqs_available() -> bool:
    """Vérifie si liboqs-python est disponible — résultat mis en cache.

    Attrape ImportError (paquet absent), RuntimeError et SystemExit (lib native
    absente — levés par oqs.py lors du chargement du .so), et BaseException en
    dernier recours.
    """
    global _OQS_AVAILABLE
    if _OQS_AVAILABLE is None:
        try:
            import oqs as _oqs_test  # noqa: F401
            _oqs_test.get_enabled_KEMs()  # vérifie que le .so natif est chargé
            _OQS_AVAILABLE = True
        except (ImportError, RuntimeError, OSError, SystemExit, BaseException):
            _OQS_AVAILABLE = False
            logger.warning(
                "liboqs-python non disponible ou bibliothèque native absente — "
                "fallback X25519 activé. "
                "Installer liboqs + cmake pour ML-KEM-768 complet."
            )
    return _OQS_AVAILABLE


def _import_oqs():
    """Importe oqs ou lève KEMError si absent (utilisation directe ML-KEM uniquement)."""
    try:
        import oqs
        oqs.get_enabled_KEMs()  # vérifie que le .so natif est chargé
    except ImportError as exc:
        raise KEMError("liboqs-python not installed — pip install liboqs-python") from exc
    except (RuntimeError, OSError, SystemExit, BaseException) as exc:
        raise KEMError(
            "liboqs native library not found — fallback X25519 actif. "
            "Compiler liboqs (cmake) pour ML-KEM-768."
        ) from exc
    return oqs


# ---------------------------------------------------------------------------
# API principale — avec fallback automatique
# ---------------------------------------------------------------------------

def generate_kem_keypair() -> tuple[bytes, bytes]:
    """Return (secret_key, public_key).

    Utilise ML-KEM-768 si liboqs disponible, sinon X25519 (fallback).
    """
    if _oqs_available():
        oqs = _import_oqs()
        with oqs.KeyEncapsulation(KEM_ALGORITHM) as kem:
            public_key = kem.generate_keypair()
            secret_key = kem.export_secret_key()
        logger.debug("Generated %s keypair pub=%d bytes", KEM_ALGORITHM, len(public_key))
        return secret_key, public_key
    # Fallback X25519
    private = X25519PrivateKey.generate()
    secret_key = private.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    public_key = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    logger.debug("Generated %s keypair (fallback) pub=%d bytes", KEM_FALLBACK_ALGORITHM, len(public_key))
    return secret_key, public_key


def encapsulate(peer_public_key: bytes) -> tuple[bytes, bytes]:
    """Return (ciphertext, shared_secret) for sending to peer.

    ML-KEM si liboqs disponible, sinon ECDH X25519 éphémère.
    """
    if _oqs_available():
        oqs = _import_oqs()
        with oqs.KeyEncapsulation(KEM_ALGORITHM) as kem:
            ciphertext, shared_secret = kem.encap_secret(peer_public_key)
        return ciphertext, shared_secret
    # Fallback X25519 : générer une paire éphémère côté émetteur
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey
    ephemeral = X25519PrivateKey.generate()
    ephemeral_pub = ephemeral.public_key()
    peer_pub = X25519PublicKey.from_public_bytes(peer_public_key[:32])  # 32 bytes X25519
    shared_secret = ephemeral.exchange(peer_pub)
    ciphertext = ephemeral_pub.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return ciphertext, shared_secret


def decapsulate(ciphertext: bytes, secret_key: bytes) -> bytes:
    """Recover shared secret from ciphertext using our secret key.

    ML-KEM si liboqs disponible, sinon ECDH X25519.
    """
    if _oqs_available():
        oqs = _import_oqs()
        with oqs.KeyEncapsulation(KEM_ALGORITHM, secret_key=secret_key) as kem:
            return kem.decap_secret(ciphertext)
    # Fallback X25519
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey, X25519PrivateKey as _X
    private = _X.from_private_bytes(secret_key[:32])
    ephemeral_pub = X25519PublicKey.from_public_bytes(ciphertext[:32])
    return private.exchange(ephemeral_pub)


def derive_aes_key(shared_secret: bytes, *, context: bytes = b"artcb-p2p-v1") -> bytes:
    return hashlib.sha256(shared_secret + context).digest()


def encrypt_payload(
    plaintext: bytes,
    peer_public_key: bytes,
    *,
    context: bytes = b"artcb-p2p-v1",
) -> dict[str, str]:
    """ML-KEM encapsulation + AES-256-GCM payload."""
    if not kem_enabled():
        raise KEMError("ML-KEM disabled — set ARTCB_KEM_ENABLED=true")
    ciphertext, shared = encapsulate(peer_public_key)
    key = derive_aes_key(shared, context=context)
    nonce = secrets.token_bytes(NONCE_LEN)
    sealed = AESGCM(key).encrypt(nonce, plaintext, None)
    return {
        "kem_alg": KEM_ALGORITHM,
        "kem_ct": ciphertext.hex(),
        "nonce": nonce.hex(),
        "ciphertext": sealed.hex(),
        "context": context.decode("ascii", errors="replace"),
    }


def decrypt_payload(
    envelope: dict[str, str],
    secret_key: bytes,
    *,
    context: bytes | None = None,
) -> bytes:
    """Decrypt envelope received from a peer."""
    if envelope.get("kem_alg") != KEM_ALGORITHM:
        raise KEMError(f"Unsupported KEM: {envelope.get('kem_alg')}")
    ctx = context
    if ctx is None and envelope.get("context"):
        ctx = envelope["context"].encode("utf-8")
    if ctx is None:
        ctx = b"artcb-p2p-v1"
    kem_ct = bytes.fromhex(envelope["kem_ct"])
    nonce = bytes.fromhex(envelope["nonce"])
    sealed = bytes.fromhex(envelope["ciphertext"])
    shared = decapsulate(kem_ct, secret_key)
    key = derive_aes_key(shared, context=ctx)
    return AESGCM(key).decrypt(nonce, sealed, None)
