"""Module API Keys public — génération de clés Bearer pour accès tiers (Cursor, ChatGPT, LangChain…)."""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import time
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger("artcb.api.api_keys")
router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])

# --------------------------------------------------------------------------- #
#  Stockage fichier JSON local  (data/api_keys.json)
# --------------------------------------------------------------------------- #

def _keys_path(request: Request) -> Path:
    state = request.app.state.artcb
    return state.settings.data_dir / "api_keys.json"


def _load_keys(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except Exception:
        return []


def _save_keys(path: Path, keys: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(keys, indent=2))


# --------------------------------------------------------------------------- #
#  Schémas Pydantic
# --------------------------------------------------------------------------- #

class GenerateKeyRequest(BaseModel):
    label: str = Field(min_length=1, max_length=128, description="Nom lisible de la clé (ex: 'Cursor dev')")
    scopes: list[str] = Field(
        default=["read", "write"],
        description="Droits: read, write, mining, admin",
    )
    expires_days: int | None = Field(
        default=None,
        ge=1,
        le=3650,
        description="Durée de validité en jours (None = illimitée)",
    )


class ApiKeyOut(BaseModel):
    key_id: str
    label: str
    scopes: list[str]
    created_at: float
    expires_at: float | None
    last_used_at: float | None
    active: bool
    key_preview: str  # artcb_xxxx…xxxx (masqué)


# --------------------------------------------------------------------------- #
#  Middleware helper — réutilisé dans les autres routes
# --------------------------------------------------------------------------- #

def _find_key_record(keys: list[dict], raw_token: str) -> dict | None:
    """Retrouve un enregistrement de clé par son token brut (comparaison par hash)."""
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    for k in keys:
        if k.get("token_hash") == token_hash and k.get("active", True):
            # Vérifier expiration
            exp = k.get("expires_at")
            if exp and time.time() > exp:
                return None
            return k
    return None


def verify_api_key(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> dict | None:
    """
    Dependency FastAPI : extrait et valide le token Bearer ARTCB.
    Retourne le record de clé ou None si absent (accès public toléré).
    Pour forcer l'auth, lever HTTPException si retourne None.
    """
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        return None
    raw = authorization.removeprefix("Bearer ").strip()
    if not raw.startswith("artcb_"):
        return None
    path = _keys_path(request)
    keys = _load_keys(path)
    record = _find_key_record(keys, raw)
    if record:
        # Mettre à jour last_used_at
        record["last_used_at"] = time.time()
        _save_keys(path, keys)
    return record


# --------------------------------------------------------------------------- #
#  P0-2 — require_scope : helper pour enforcer les scopes Bearer
# --------------------------------------------------------------------------- #

def require_scope(scope: str):
    """
    Dependency FastAPI : vérifie que la clé Bearer possède le scope requis.
    Usage : Depends(require_scope("write"))
    Retourne le key_record si valide, lève 403 si scope absent.
    Retourne None (sans erreur) si aucun token fourni (accès public toléré par défaut).
    Pour forcer l'auth + scope : lever 401 si retourne None.
    """
    def _check(
        request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> dict | None:
        if not authorization:
            return None  # pas de token → accès public toléré
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Format Bearer requis")
        raw = authorization.removeprefix("Bearer ").strip()
        if not raw.startswith("artcb_"):
            raise HTTPException(status_code=401, detail="Token ARTCB invalide (préfixe artcb_ requis)")
        path = _keys_path(request)
        keys = _load_keys(path)
        record = _find_key_record(keys, raw)
        if record is None:
            raise HTTPException(status_code=401, detail="Token invalide ou expiré")
        if scope not in record.get("scopes", []) and "admin" not in record.get("scopes", []):
            raise HTTPException(
                status_code=403,
                detail=f"Scope '{scope}' requis — clé actuelle: {record.get('scopes', [])}",
            )
        return record
    return _check


# --------------------------------------------------------------------------- #
#  Endpoints
# --------------------------------------------------------------------------- #

@router.post("/generate", summary="Générer une nouvelle clé API")
def generate_key(body: GenerateKeyRequest, request: Request) -> dict:
    """
    Crée une clé API personnelle `artcb_<64hex>`.
    La clé complète n'est retournée **qu'une seule fois** — conservez-la.
    """
    path = _keys_path(request)
    keys = _load_keys(path)

    raw_token = "artcb_" + secrets.token_hex(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    key_id = "kid_" + secrets.token_hex(8)

    now = time.time()
    expires_at = now + body.expires_days * 86400 if body.expires_days else None

    # P0-3 — Wallet automatique lié à la clé API
    auto_wallet_name = f"agent_{body.label.replace(' ', '_').replace('-', '_')[:32]}"
    wallet_created = False
    try:
        from src.artcb.wallet.manager import WalletManager
        wm = WalletManager()
        existing = [w["name"] for w in wm.list_wallets()]
        if auto_wallet_name not in existing:
            wm.create_wallet(name=auto_wallet_name)
            wallet_created = True
            logger.info("Auto-wallet created for key %s: %s", key_id, auto_wallet_name)
    except Exception as exc:
        logger.warning("Auto-wallet creation failed for %s: %s", body.label, exc)
        auto_wallet_name = None

    record = {
        "key_id": key_id,
        "label": body.label,
        "scopes": body.scopes,
        "token_hash": token_hash,
        "key_preview": raw_token[:12] + "…" + raw_token[-4:],
        "created_at": now,
        "expires_at": expires_at,
        "last_used_at": None,
        "active": True,
        "auto_wallet": auto_wallet_name,  # P0-3 wallet lié
    }
    keys.append(record)
    _save_keys(path, keys)

    logger.info("API key created: %s (%s) wallet=%s", key_id, body.label, auto_wallet_name)
    return {
        "key_id": key_id,
        "label": body.label,
        "scopes": body.scopes,
        "token": raw_token,          # ← affiché UNE SEULE FOIS
        "key_preview": record["key_preview"],
        "created_at": now,
        "expires_at": expires_at,
        "auto_wallet": auto_wallet_name,
        "wallet_created": wallet_created,
        "message": "Conservez ce token — il ne sera plus affiché.",
    }


@router.get("/list", summary="Lister les clés actives")
def list_keys(request: Request) -> dict:
    """Liste toutes les clés (tokens masqués)."""
    path = _keys_path(request)
    keys = _load_keys(path)
    now = time.time()
    out = []
    for k in keys:
        exp = k.get("expires_at")
        active = k.get("active", True) and (not exp or now < exp)
        out.append(ApiKeyOut(
            key_id=k["key_id"],
            label=k["label"],
            scopes=k.get("scopes", []),
            created_at=k["created_at"],
            expires_at=exp,
            last_used_at=k.get("last_used_at"),
            active=active,
            key_preview=k.get("key_preview", "artcb_…"),
        ).model_dump())
    return {"keys": out, "count": len(out)}


@router.get("/me", summary="Info sur la clé courante")
def key_info(
    request: Request,
    key_record: Annotated[dict | None, Depends(verify_api_key)] = None,
) -> dict:
    """Retourne les métadonnées de la clé utilisée dans le header Authorization."""
    if not key_record:
        raise HTTPException(status_code=401, detail="Token Bearer artcb_xxx manquant ou invalide")
    return {
        "key_id": key_record["key_id"],
        "label": key_record["label"],
        "scopes": key_record.get("scopes", []),
        "created_at": key_record["created_at"],
        "expires_at": key_record.get("expires_at"),
        "last_used_at": key_record.get("last_used_at"),
        "active": key_record.get("active", True),
    }


@router.delete("/{key_id}", summary="Révoquer une clé")
def revoke_key(key_id: str, request: Request) -> dict:
    """Révoque (désactive) une clé par son key_id."""
    path = _keys_path(request)
    keys = _load_keys(path)
    for k in keys:
        if k["key_id"] == key_id:
            k["active"] = False
            _save_keys(path, keys)
            logger.info("API key revoked: %s", key_id)
            return {"revoked": True, "key_id": key_id}
    raise HTTPException(status_code=404, detail=f"Clé {key_id} introuvable")

# Made with Bob
