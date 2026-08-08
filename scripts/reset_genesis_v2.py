#!/usr/bin/env python3
"""Reset complet blockchain ARTCB — nouveau genesis block v2.

Ce script :
  1. Archive l'ancienne chaîne dans data/chain/blocks_archive_YYYYMMDD.jsonl
  2. Supprime tous les anciens wallets (data/wallets/)
  3. Crée un nouveau genesis block v2 avec la date courante
  4. Remet à zéro le binding wallet-device
  5. Conserve l'identité P2P du nœud (node_identity.json) — inchangée

Usage :
  python3 scripts/reset_genesis_v2.py [--dry-run]

Arguments :
  --dry-run    Affiche ce qui serait fait sans rien modifier
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
CHAIN = DATA / "chain"
WALLETS = DATA / "wallets"
P2P = DATA / "p2p"


def run(dry_run: bool) -> None:
    now = datetime.now(UTC)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}=== ARTCB Genesis Reset v2 — {iso} ===\n")

    # ── 1. Archive l'ancienne chaîne ─────────────────────────────────────────
    blocks = CHAIN / "blocks.jsonl"
    if blocks.exists():
        archive = CHAIN / f"blocks_archive_{timestamp}.jsonl"
        print(f"  → Archive ancienne chaîne : {archive}")
        if not dry_run:
            shutil.copy2(blocks, archive)
            blocks.unlink()
            print(f"  ✓ Ancienne chaîne archivée dans {archive}")
    else:
        print("  ℹ Pas de chaîne existante")

    # ── 2. Supprimer les anciens wallets ─────────────────────────────────────
    if WALLETS.exists():
        wallet_files = list(WALLETS.glob("*.key")) + list(WALLETS.glob("*.json")) + list(WALLETS.glob("*.pqc"))
        # Conserver uniquement les wallets founders (wallet_founders*)
        to_delete = [f for f in wallet_files if not f.name.startswith("founder")]
        print(f"  → Suppression de {len(to_delete)} fichiers wallets (non-founders)")
        for f in to_delete:
            print(f"    - {f.name}")
            if not dry_run:
                f.unlink()
    else:
        print("  ℹ Pas de wallets existants")

    # ── 3. Remettre à zéro le binding wallet-device ──────────────────────────
    binding_file = DATA / "wallet_device_bindings.json"
    if binding_file.exists():
        print(f"  → Remise à zéro : {binding_file}")
        if not dry_run:
            binding_file.write_text("[]", encoding="utf-8")

    # ── 4. Créer le nouveau genesis block v2 ─────────────────────────────────
    genesis = {
        "index": 0,
        "timestamp": iso,
        "prev_hash": "0" * 64,
        "graph_root": "genesis-v2",
        "merkle_root": "genesis-v2",
        "pol_score": 1.0,
        "hash": f"genesis-artcb-v2-{timestamp}",
        "hash_sha3": f"genesis-artcb-v2-sha3-{timestamp}",
        "signature": "genesis-signature-v2",
        "graph_id": f"genesis-v2-{timestamp}",
        "visibility": "public",
        "group_id": None,
        "block_reward": 0,
        "contributors": [],
        "public_symbols": {},
        "block_size_bytes": 0,
        "version": "2",
        "network_id": "artcb-devnet-1",
        "wallet_format": "user_password_required",
        "node_id_format": "artcb_address_v3",
        "pqc_standard": "Ed25519+ML-DSA-65+ML-KEM-768",
    }
    line = json.dumps(genesis, ensure_ascii=False, separators=(",", ":"))
    genesis["block_size_bytes"] = len(line.encode("utf-8"))

    print(f"  → Nouveau genesis block v2 :")
    print(f"    hash       : {genesis['hash']}")
    print(f"    timestamp  : {genesis['timestamp']}")
    print(f"    pqc_standard: {genesis['pqc_standard']}")

    if not dry_run:
        CHAIN.mkdir(parents=True, exist_ok=True)
        with blocks.open("w", encoding="utf-8") as f:
            f.write(json.dumps(genesis, ensure_ascii=False, separators=(",", ":")) + "\n")
        print(f"  ✓ Genesis block v2 écrit dans {blocks}")

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}✅ Reset terminé — anciens wallets invalidés, nouvelle chaîne v2\n")
    if dry_run:
        print("  Relancer sans --dry-run pour appliquer.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset genesis block ARTCB v2")
    parser.add_argument("--dry-run", action="store_true", help="Afficher sans modifier")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
