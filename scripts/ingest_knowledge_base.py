#!/usr/bin/env python3
"""
Ingestion globale — ARTCB Knowledge Base → Blockchain
======================================================
Grave TOUS les fichiers .md et docs de référence dans la blockchain
comme memos de type "lesson" (apprentissage global du projet).

Chaque fichier devient un bloc signé immuable :
  - Contenu tronqué à 8000 chars max (limite MemoRequest)
  - Fichiers > 8000 chars divisés en chunks
  - Tags : ["knowledge_base", "file:<basename>", "phase:<inferred>"]
  - Source : ai:memo:lesson
  - Visibility : private (contenu interne projet)

Usage :
  python3 scripts/ingest_knowledge_base.py
"""

import os
import sys
import time
import glob as globmod
from pathlib import Path

from fastapi.testclient import TestClient
from src.api.main import create_app

# ── Configuration ─────────────────────────────────────────────────────────────
CHUNK_SIZE = 7500          # chars max par bloc (marge sous 8000)
DELAY_BETWEEN_BLOCS = 0.1  # secondes entre chaque appel (bypass actif, pas de rate-limit)
MEMO_TYPE = "lesson"
VISIBILITY = "private"

# ── Fichiers à ingérer (tous les .md + docs de référence sans extension) ──────
ROOT = Path(__file__).parent.parent

DOCS_SANS_EXTENSION = [
    "AUTO_PROMPT_ARTCB",
    "PROTOCOLE_ARTCB",
    "ROADMAP_GENERAL_ARTCB",
    "CAHIER_DES_CHARGES_ARTCB",
    "LEÇONS_APPRISES_ARTCB",
    "STANDARD_NAMES_ARTCB",
    "INDEX_ARTCB",
    "CONFIGURATION_ARTCB",
    "CHECKLIST_PRE_DEV_ARTCB",
    "QUESTIONS_OUVERTES_ARTCB",
]

# Patterns exclus (non pertinents pour l'apprentissage)
EXCLUDE_PATTERNS = [
    "node_modules", ".git", "__pycache__", "dist", "build",
    ".venv", "venv", ".pytest_cache", ".bob",
]

# ── Couleurs ──────────────────────────────────────────────────────────────────
G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; B = "\033[94m"
E = "\033[0m"; BOLD = "\033[1m"

def log_ok(msg):  print(f"  {G}✅ {msg}{E}")
def log_warn(msg): print(f"  {Y}⚠️  {msg}{E}")
def log_err(msg):  print(f"  {R}❌ {msg}{E}")
def log_info(msg): print(f"  {B}ℹ  {msg}{E}")


def should_exclude(path: Path) -> bool:
    for exc in EXCLUDE_PATTERNS:
        if exc in str(path):
            return True
    return False


def collect_files() -> list[Path]:
    """Collecte tous les fichiers à ingérer."""
    files = []

    # Docs de référence sans extension
    for name in DOCS_SANS_EXTENSION:
        p = ROOT / name
        if p.exists():
            files.append(p)

    # Tous les .md (récursif, hors exclusions)
    for p in sorted(ROOT.rglob("*.md")):
        if not should_exclude(p):
            files.append(p)

    # Dédoublonnage (ordre préservé)
    seen = set()
    unique = []
    for f in files:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return unique


def infer_tags(path: Path) -> list[str]:
    """Infère des tags depuis le chemin du fichier."""
    tags = ["knowledge_base", f"file:{path.name}"]
    name = path.name.lower()
    rel = str(path.relative_to(ROOT))

    if "rapport" in rel or rel.startswith("rapports/"):
        tags.append("rapport")
        # Extraire numéro de rapport
        import re
        m = re.search(r"(\d{3})", path.name)
        if m:
            tags.append(f"rapport_{m.group(1)}")
    if "roadmap" in name:    tags.append("roadmap")
    if "protocole" in name:  tags.append("protocole")
    if "cahier" in name:     tags.append("spec")
    if "lecon" in name or "leçon" in name: tags.append("lessons")
    if "auto_prompt" in name: tags.append("autoprompt")
    if "readme" in name:     tags.append("readme")
    if "index" in name:      tags.append("index")
    if "securite" in name or "security" in name: tags.append("securite")
    if "benchmark" in name:  tags.append("benchmark")
    if "i18n" in name or "traduction" in name: tags.append("i18n")
    if "api" in name:        tags.append("api")
    if "blockchain" in name or "chain" in name: tags.append("blockchain")
    if "minage" in name or "mining" in name: tags.append("mining")
    if "anti_sybil" in name or "sybil" in name: tags.append("antisybil")
    return list(set(tags))


def split_chunks(content: str, path: Path) -> list[tuple[str, str]]:
    """
    Divise le contenu en chunks de CHUNK_SIZE.
    Retourne list[(chunk_text, chunk_label)]
    """
    if len(content) <= CHUNK_SIZE:
        return [(content, path.name)]
    chunks = []
    total = (len(content) + CHUNK_SIZE - 1) // CHUNK_SIZE
    for i in range(total):
        start = i * CHUNK_SIZE
        end = min(start + CHUNK_SIZE, len(content))
        label = f"{path.name} [part {i+1}/{total}]"
        chunks.append((content[start:end], label))
    return chunks


def main():
    print(f"\n{BOLD}{'═'*65}")
    print("  INGESTION KNOWLEDGE BASE → BLOCKCHAIN ARTCB")
    print(f"{'═'*65}{E}\n")

    # Démarrer l'app
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)

    # Créer une clé dédiée à l'ingestion
    r = client.post("/api/v1/api-keys/generate", json={
        "label": "knowledge_ingest",
        "scopes": ["read", "write"],
        "expires_days": 1,
    })
    if r.status_code != 200:
        log_err(f"Impossible de créer la clé d'ingestion : {r.status_code} {r.text[:80]}")
        sys.exit(1)
    d = r.json()
    token = d["token"]
    wallet = d.get("auto_wallet", "")
    hdr = {"Authorization": f"Bearer {token}"}
    log_ok(f"Clé d'ingestion créée : {token[:20]}… wallet={wallet}")

    # Hauteur chaîne initiale
    r = client.get("/health")
    chain_before = 0
    try:
        r2 = client.get("/api/v1/ai/status", headers=hdr)
        chain_before = r2.json().get("chain", {}).get("height", 0)
    except Exception:
        pass

    # Collecter les fichiers
    files = collect_files()
    log_info(f"Fichiers à ingérer : {len(files)}")
    print()

    # Statistiques
    total_blocs = 0
    total_bytes = 0
    total_chunks = 0
    errors = []

    for i, fpath in enumerate(files):
        rel = str(fpath.relative_to(ROOT))
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            log_warn(f"Lecture échouée {rel}: {exc}")
            errors.append(rel)
            continue

        if not content.strip():
            log_warn(f"Fichier vide ignoré : {rel}")
            continue

        total_bytes += len(content.encode("utf-8"))
        chunks = split_chunks(content, fpath)
        total_chunks += len(chunks)
        tags = infer_tags(fpath)

        for j, (chunk_text, chunk_label) in enumerate(chunks):
            memo_content = (
                f"[KNOWLEDGE BASE — {chunk_label}]\n"
                f"Source: {rel}\n"
                f"---\n"
                f"{chunk_text}"
            )[:8000]  # sécurité absolue

            payload = {
                "content": memo_content,
                "memo_type": MEMO_TYPE,
                "tags": tags,
                "session_id": "knowledge_ingest_global",
                "visibility": VISIBILITY,
            }

            try:
                resp = client.post("/api/v1/ai/memo", json=payload, headers=hdr)
                if resp.status_code == 200:
                    bid = resp.json().get("block_index", "?")
                    total_blocs += 1
                    if len(chunks) > 1:
                        log_ok(f"[{i+1}/{len(files)}] {rel} chunk {j+1}/{len(chunks)} → bloc #{bid}")
                    else:
                        log_ok(f"[{i+1}/{len(files)}] {rel} → bloc #{bid}")
                else:
                    log_err(f"[{i+1}/{len(files)}] {rel} chunk {j+1} → HTTP {resp.status_code} {resp.text[:80]}")
                    errors.append(f"{rel} (chunk {j+1})")
            except Exception as exc:
                log_err(f"[{i+1}/{len(files)}] {rel}: {exc}")
                errors.append(rel)

            time.sleep(DELAY_BETWEEN_BLOCS)

    # Hauteur chaîne finale
    chain_after = 0
    try:
        r2 = client.get("/api/v1/ai/status", headers=hdr)
        chain_after = r2.json().get("chain", {}).get("height", 0)
    except Exception:
        pass

    # Métriques anti-sybil
    anti_sybil_snapshot = {}
    try:
        r3 = client.get("/api/v1/security/anti-sybil/metrics", headers=hdr)
        anti_sybil_snapshot = r3.json().get("totals", {})
    except Exception:
        pass

    # Bilan
    print(f"\n{BOLD}{'═'*65}")
    print("  BILAN INGESTION KNOWLEDGE BASE")
    print(f"{'═'*65}{E}")
    print(f"\n  Fichiers traités  : {len(files)}")
    print(f"  Chunks totaux     : {total_chunks}")
    print(f"  Blocs gravés      : {total_blocs}")
    print(f"  Volume total      : {total_bytes / 1024:.1f} Ko")
    print(f"  Chaîne avant      : {chain_before} blocs")
    print(f"  Chaîne après      : {chain_after} blocs")
    print(f"  Nouveaux blocs    : {chain_after - chain_before}")
    print(f"  Erreurs           : {len(errors)}")
    if errors:
        print(f"\n  {R}Erreurs détail :{E}")
        for e in errors[:10]:
            print(f"    - {e}")
    if anti_sybil_snapshot:
        print(f"\n  Anti-Sybil métriques :")
        print(f"    attempts={anti_sybil_snapshot.get('attempts',0)} "
              f"bypassed={anti_sybil_snapshot.get('bypassed_by_ai_mode',0)} "
              f"hard_rejected={anti_sybil_snapshot.get('hard_rejected',0)}")
        print(f"    → 0 hard_rejected = tous signés ✅" if anti_sybil_snapshot.get('hard_rejected',0)==0 else "")

    col = G if not errors else Y
    print(f"\n  {col}{BOLD}{'✅ INGESTION COMPLÈTE' if not errors else f'⚠️ {len(errors)} erreurs'}{E}")
    print(f"{'═'*65}\n")

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
