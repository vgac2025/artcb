#!/usr/bin/env python3
"""Création des 2 wallets fondateurs ARTCB v2 — Créateur + Développement.

NOUVELLE CONFIGURATION (remplacement des 5 founders v1) :
  Wallet 0 — ARTCB Créateur     : 1 000 000 ARTCB + droits créateur absolus
  Wallet 1 — ARTCB Développement: 1 000 000 ARTCB dédié au développement

Usage :
    python3 scripts/create_founders_wallets_v2.py

SECURITE :
  - founders_wallets_v2.json est dans .gitignore — JAMAIS commiter
  - Stocker les clés privées dans Doppler (projet ARTCB-WALLET-SECRETS)
  - Sauvegarder hors-ligne (coffre-fort chiffré)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from nacl import encoding, signing

# ── Configuration ──────────────────────────────────────────────────────────
CREATOR_ALLOCATION_ARTCB    = 1_000_000  # Compte créateur (ARTCB)
DEVELOPER_ALLOCATION_ARTCB  = 1_000_000  # Compte développement
TOTAL_SUPPLY_ARTCB          = 21_000_000
SATOSHI_PER_ARTCB           = 100_000_000
CREATOR_VOTE_WEIGHT         = 999_999    # Poids vote absolu du créateur

DATA_DIR    = Path("data/founders")
DATA_DIR.mkdir(parents=True, exist_ok=True)

WALLETS_FILE    = DATA_DIR / "founders_wallets_v2.json"
ALLOC_FILE      = DATA_DIR / "founders_allocation_v2.json"


def generate_wallet(name: str, allocation_artcb: int, is_creator: bool = False) -> dict:
    """Génère une paire Ed25519 pour un wallet fondateur."""
    signing_key = signing.SigningKey.generate()
    verify_key  = signing_key.verify_key
    address     = verify_key.encode(encoder=encoding.Base64Encoder).decode("ascii")
    private_key = signing_key.encode(encoder=encoding.HexEncoder).decode("ascii")

    return {
        "name":               name,
        "address":            address,
        "private_key":        private_key,  # SENSIBLE — JAMAIS COMMITER
        "allocation_artcb":   allocation_artcb,
        "allocation_satoshi": allocation_artcb * SATOSHI_PER_ARTCB,
        "is_creator":         is_creator,
        "creator_veto":       is_creator,
        "vote_weight":        CREATOR_VOTE_WEIGHT if is_creator else 1,
        "created_at":         datetime.now(UTC).isoformat(),
    }


def main() -> None:
    print("=" * 60)
    print("CRÉATION WALLETS FONDATEURS ARTCB v2")
    print("=" * 60)
    print(f"  Créateur   : {CREATOR_ALLOCATION_ARTCB:,} ARTCB (vote weight={CREATOR_VOTE_WEIGHT:,})")
    print(f"  Développement : {DEVELOPER_ALLOCATION_ARTCB:,} ARTCB")
    print(f"  Total alloué : {CREATOR_ALLOCATION_ARTCB + DEVELOPER_ALLOCATION_ARTCB:,} ARTCB / {TOTAL_SUPPLY_ARTCB:,}")
    print("=" * 60)

    wallets = [
        generate_wallet("ARTCB Createur",      CREATOR_ALLOCATION_ARTCB,   is_creator=True),
        generate_wallet("ARTCB Developpement", DEVELOPER_ALLOCATION_ARTCB, is_creator=False),
    ]

    # ── Fichier wallets (SENSIBLE) ─────────────────────────────────────────
    output = {
        "version":              "2.0",
        "schema":               "artcb-founders-wallets-v2",
        "genesis_date":         datetime.now(UTC).isoformat(),
        "total_supply_artcb":   TOTAL_SUPPLY_ARTCB,
        "founders_count":       2,
        "creator_wallet_index": 0,
        "creator_vote_weight":  CREATOR_VOTE_WEIGHT,
        "wallets":              wallets,
        "_note": (
            "CONFIDENTIEL — Ne JAMAIS commiter ce fichier. "
            "Stocker dans Doppler projet ARTCB-WALLET-SECRETS. "
            "wallets[0] = créateur (droits absolus). "
            "wallets[1] = développement."
        ),
    }
    WALLETS_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    # ── Fichier allocation (public — sans clés privées) ───────────────────
    alloc = {
        "version":           "2.0",
        "schema":            "artcb-founders-allocation-v2",
        "genesis_date":      datetime.now(UTC).isoformat(),
        "total_supply_artcb": TOTAL_SUPPLY_ARTCB,
        "founders": [
            {
                "name":           w["name"],
                "address":        w["address"],
                "allocation_artcb": w["allocation_artcb"],
                "allocation_satoshi": w["allocation_satoshi"],
                "is_creator":     w["is_creator"],
                "vote_weight":    w["vote_weight"],
            }
            for w in wallets
        ],
    }
    ALLOC_FILE.write_text(json.dumps(alloc, indent=2, ensure_ascii=False))

    # ── Affichage ──────────────────────────────────────────────────────────
    print()
    for i, w in enumerate(wallets):
        print(f"[{i}] {w['name']}")
        print(f"     Address     : {w['address']}")
        print(f"     Allocation  : {w['allocation_artcb']:,} ARTCB")
        print(f"     Vote weight : {w['vote_weight']:,}")
        print(f"     Is creator  : {w['is_creator']}")
        print()

    creator_addr = wallets[0]["address"]
    print("=" * 60)
    print("IMPORTANT — NOTER CES INFORMATIONS :")
    print(f"  CREATOR_WALLET = {creator_addr}")
    print()
    print("  1. Graver cette adresse dans scripts/init_genesis.py")
    print("  2. Stocker les clés dans Doppler (ARTCB-WALLET-SECRETS)")
    print(f"  3. Fichier sensible : {WALLETS_FILE}")
    print(f"  4. Fichier public   : {ALLOC_FILE}")
    print("=" * 60)

    # ── Écrire l'adresse créateur dans un fichier temporaire pour init_genesis.py ──
    creator_ref = Path("data/founders/.creator_wallet_address")
    creator_ref.write_text(creator_addr)
    print(f"\n  Adresse créateur enregistrée dans {creator_ref}")
    print("  (utilisée par scripts/init_genesis.py)")


if __name__ == "__main__":
    main()
