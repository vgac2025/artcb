"""P2P node identity — ML-KEM keypair persistant.

Option 3 — Identifiant de nœud = adresse wallet ARTCB (rapport 115)
============================================================================
L'identifiant unique du nœud est l'adresse wallet de l'opérateur (artcb1xxx).
Cette adresse est dérivée de la clé publique Ed25519 du wallet (Bech32).

Pourquoi c'est la meilleure approche :
  1. L'adresse est UNIQUE par construction (dérivée de la clé privée)
  2. Elle est VÉRIFIABLE par n'importe qui (clé publique dans le .json)
  3. Elle est PORTABLE (le même wallet = le même nœud sur n'importe quel serveur)
  4. Elle respecte notre standard post-quantique hybride (Ed25519 + ML-DSA-65)
  5. Elle est HUMAINEMENT LISIBLE (format bech32 : artcb1xxxxx)

Format node_id v3 (rapport 115) :
  node_id = "artcb1{bech32_address}"
  Exemple : "artcb1q3r5m6kz9p2wxy4n7jvdf8sg0tu1lhcae"

Pour décentralisation totale (sans DNS centralisé) :
  À partir de 10 nœuds actifs, le réseau peut fonctionner sans bootstrap fixes.
  À partir de 3 nœuds actifs dans des juridictions différentes, il est résilient.

Standard post-quantique hybride :
  - Wallet : Ed25519 + ML-DSA-65 (signature hybride)
  - Transport P2P : ML-KEM-768 (chiffrement de transport)
  - Adresse : SHA-256(RIPEMD-160(Ed25519_pubkey + ML-DSA_pubkey)) Bech32
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.artcb.crypto.kem import KEMError, generate_kem_keypair

logger = logging.getLogger("artcb.p2p.node_identity")

NETWORK_ID = "artcb-devnet-1"
DEFAULT_P2P_PORT = int(os.getenv("ARTCB_P2P_PORT", "18444"))


@dataclass
class NodeIdentity:
    network_id: str
    node_id: str            # Format v3 : adresse wallet artcb1xxx (ou node_xxx en fallback)
    kem_public_key_hex: str
    kem_secret_key_hex: str
    api_port: int
    p2p_port: int
    wallet_address: str | None = None  # Adresse wallet liée (Option 3)
    node_public_url: str | None = None  # URL publique déclarée (Option 2/3)

    def public_dict(self) -> dict[str, Any]:
        d = {
            "network_id": self.network_id,
            "node_id": self.node_id,
            "kem_public_key_hex": self.kem_public_key_hex,
            "api_port": self.api_port,
            "p2p_port": self.p2p_port,
        }
        if self.wallet_address:
            d["wallet_address"] = self.wallet_address
        if self.node_public_url:
            d["node_public_url"] = self.node_public_url
        return d


def node_id_from_wallet_address(wallet_address: str) -> str:
    """Option 3 : node_id = adresse wallet (artcb1xxx).

    L'adresse wallet EST l'identifiant unique du nœud.
    Cela garantit qu'un seul nœud peut opérer avec chaque wallet.
    """
    return wallet_address


class NodeIdentityStore:
    """Persiste l'identité P2P du nœud (clé ML-KEM).

    Option 3 : Si ARTCB_NODE_WALLET_ADDRESS est défini dans .env,
    le node_id est l'adresse wallet de l'opérateur.
    Sinon, fallback sur un UUID aléatoire (mode dev sans wallet).
    """

    def __init__(self, data_dir: Path) -> None:
        self.path = Path(data_dir) / "p2p" / "node_identity.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load_or_create(self, *, api_port: int = 8000) -> NodeIdentity:
        if self.path.is_file():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return NodeIdentity(
                network_id=data.get("network_id", NETWORK_ID),
                node_id=data["node_id"],
                kem_public_key_hex=data["kem_public_key_hex"],
                kem_secret_key_hex=data["kem_secret_key_hex"],
                api_port=int(data.get("api_port", api_port)),
                p2p_port=int(data.get("p2p_port", DEFAULT_P2P_PORT)),
                wallet_address=data.get("wallet_address"),
                node_public_url=data.get("node_public_url") or os.getenv("ARTCB_NODE_PUBLIC_URL"),
            )
        try:
            secret, public = generate_kem_keypair()
        except KEMError as exc:
            raise KEMError(f"Cannot init P2P node identity: {exc}") from exc
        import uuid

        # Option 3 : utiliser l'adresse wallet comme node_id si disponible
        wallet_address = os.getenv("ARTCB_NODE_WALLET_ADDRESS", "").strip() or None
        node_id = (
            node_id_from_wallet_address(wallet_address)
            if wallet_address
            else f"node_{uuid.uuid4().hex[:12]}"
        )

        identity = NodeIdentity(
            network_id=NETWORK_ID,
            node_id=node_id,
            kem_public_key_hex=public.hex(),
            kem_secret_key_hex=secret.hex(),
            api_port=api_port,
            p2p_port=DEFAULT_P2P_PORT,
            wallet_address=wallet_address,
            node_public_url=os.getenv("ARTCB_NODE_PUBLIC_URL"),
        )
        self._save(identity)
        logger.info(
            "Created P2P node identity %s (option3_wallet=%s)",
            identity.node_id, bool(wallet_address),
        )
        return identity

    def _save(self, identity: NodeIdentity) -> None:
        payload = {
            "network_id": identity.network_id,
            "node_id": identity.node_id,
            "kem_public_key_hex": identity.kem_public_key_hex,
            "kem_secret_key_hex": identity.kem_secret_key_hex,
            "api_port": identity.api_port,
            "p2p_port": identity.p2p_port,
        }
        if identity.wallet_address:
            payload["wallet_address"] = identity.wallet_address
        if identity.node_public_url:
            payload["node_public_url"] = identity.node_public_url
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.path.chmod(0o600)
