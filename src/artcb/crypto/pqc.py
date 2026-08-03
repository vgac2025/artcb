"""Post-quantum cryptography — ML-DSA-65 (NIST) via liboqs."""

from __future__ import annotations

import logging
import os
from typing import Final

logger = logging.getLogger("artcb.crypto.pqc")

PQC_SIG_ALGORITHM: Final[str] = "ML-DSA-65"
ENV_PQC_ENABLED = "ARTCB_PQC_ENABLED"

# ML-DSA-65 fixed key sizes (liboqs FIPS204)
PQC_SECRET_KEY_LEN: Final[int] = 4032
PQC_PUBLIC_KEY_LEN: Final[int] = 1952


class PQCError(Exception):
    """Post-quantum crypto operation failed."""


def pqc_enabled() -> bool:
    return os.getenv(ENV_PQC_ENABLED, "true").lower() in ("1", "true", "yes", "on")


def _import_oqs():
    try:
        import oqs  # liboqs-python
        # Vérifie que le .so natif est chargé — API stable liboqs-python
        oqs.get_enabled_sig_mechanisms()
    except ImportError as exc:
        raise PQCError(
            "liboqs-python not installed — run: pip install liboqs-python"
        ) from exc
    except (AttributeError, RuntimeError, OSError, SystemExit, BaseException) as exc:
        raise PQCError(
            "liboqs native library not found — fallback Ed25519 actif. "
            "Compiler liboqs (cmake) pour ML-DSA-65 complet."
        ) from exc
    return oqs


def generate_keypair() -> tuple[bytes, bytes]:
    """Return (secret_key, public_key) bytes for ML-DSA-65."""
    oqs = _import_oqs()
    with oqs.Signature(PQC_SIG_ALGORITHM) as signer:
        public_key = signer.generate_keypair()
        secret_key = signer.export_secret_key()
    logger.debug("Generated %s keypair (pub=%d bytes)", PQC_SIG_ALGORITHM, len(public_key))
    return secret_key, public_key


def pack_keypair(secret_key: bytes, public_key: bytes) -> bytes:
    if len(secret_key) != PQC_SECRET_KEY_LEN or len(public_key) != PQC_PUBLIC_KEY_LEN:
        raise PQCError(f"Invalid ML-DSA-65 key sizes: sk={len(secret_key)} pk={len(public_key)}")
    return secret_key + public_key


def unpack_keypair(blob: bytes) -> tuple[bytes, bytes]:
    if len(blob) < PQC_SECRET_KEY_LEN + PQC_PUBLIC_KEY_LEN:
        raise PQCError(f"Invalid packed keypair length: {len(blob)}")
    secret = blob[:PQC_SECRET_KEY_LEN]
    public = blob[PQC_SECRET_KEY_LEN : PQC_SECRET_KEY_LEN + PQC_PUBLIC_KEY_LEN]
    return secret, public


def sign_message(message: bytes, secret_key: bytes) -> bytes:
    oqs = _import_oqs()
    with oqs.Signature(PQC_SIG_ALGORITHM, secret_key=secret_key) as signer:
        return signer.sign(message)


def verify_message(message: bytes, signature: bytes, public_key: bytes) -> bool:
    oqs = _import_oqs()
    try:
        with oqs.Signature(PQC_SIG_ALGORITHM) as verifier:
            return verifier.verify(message, signature, public_key)
    except Exception as exc:
        logger.debug("PQC verify failed: %s", exc)
        return False
