"""P2P artcb-devnet REST routes — sync blocs publics + transport ML-KEM."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from src.artcb.p2p.sync import P2PSyncError

logger = logging.getLogger("artcb.api.p2p")
router = APIRouter(prefix="/api/v1/p2p", tags=["p2p"])


class AddPeerRequest(BaseModel):
    host: str = Field(min_length=3)
    port: int = Field(ge=1, le=65535)
    kem_public_key_hex: str = Field(min_length=32)
    label: str = ""


class ReceiveBlocksRequest(BaseModel):
    envelope: dict[str, str]


def _state(request: Request):
    return request.app.state.artcb


@router.get("/status")
def p2p_status(request: Request) -> dict:
    state = _state(request)
    identity = state.p2p_identity
    peers = state.p2p_peers.list_peers()
    public_count = len(state.chain.list_blocks(visibility="public"))
    incoming_count = len(state.p2p_archive.list_blocks())
    return {
        "network_id": identity.network_id,
        "node_id": identity.node_id,
        "kem_public_key_hex": identity.kem_public_key_hex,
        "kem_algorithm": "ML-KEM-768",
        "p2p_port": identity.p2p_port,
        "api_port": identity.api_port,
        "peer_count": len(peers),
        "public_blocks_local": public_count,
        "public_blocks_incoming": incoming_count,
        "private_never_synced": True,
        "pool_e2e_available": True,
        "pool_crypto": "ML-KEM-768",
        "message": "Calcul local par défaut — pool opt-in E2E ML-KEM ; sync P2P = blocs publics chiffrés",
    }


@router.get("/peers")
def list_peers(request: Request) -> dict:
    peers = _state(request).p2p_peers.list_peers()
    return {"peers": [p.to_dict() for p in peers], "count": len(peers)}


@router.post("/peers")
def add_peer(body: AddPeerRequest, request: Request) -> dict:
    mgr = _state(request).p2p_peers
    try:
        peer = mgr.add_peer(
            host=body.host,
            port=body.port,
            kem_public_key_hex=body.kem_public_key_hex,
            label=body.label,
        )
        return {"peer": peer.to_dict(), "message": "Pair ajouté"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/peers/{peer_id}")
def remove_peer(peer_id: str, request: Request) -> dict:
    if not _state(request).p2p_peers.remove_peer(peer_id):
        raise HTTPException(status_code=404, detail="Peer not found")
    return {"deleted": peer_id}


@router.get("/blocks/public")
def get_public_blocks(
    request: Request,
    from_index: int = Query(0, ge=0),
) -> dict:
    """Liste blocs publics locaux — endpoint pull devnet."""
    sync = _state(request).p2p_sync
    blocks = sync.get_public_blocks(from_index=from_index)
    return {"blocks": blocks, "count": len(blocks), "from_index": from_index}


@router.get("/blocks/incoming")
def list_incoming_public(request: Request, from_index: int = Query(0, ge=0)) -> dict:
    archive = _state(request).p2p_archive
    blocks = archive.list_blocks(from_index=from_index)
    return {"blocks": blocks, "count": len(blocks), "source": "p2p_incoming_public"}


@router.post("/blocks/receive")
def receive_encrypted_blocks(body: ReceiveBlocksRequest, request: Request) -> dict:
    """Reçoit un lot de blocs publics chiffré ML-KEM."""
    sync = _state(request).p2p_sync
    try:
        payload = sync.decrypt_envelope(body.envelope)
        blocks = payload.get("blocks", [])
        from_node = body.envelope.get("from_node_id", "unknown")
        imported = sync.import_public_blocks(blocks, from_node_id=from_node)
        return {"imported": imported, "received": len(blocks), "encrypted": True}
    except Exception as exc:
        logger.error("P2P receive failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sync")
def sync_all(request: Request, from_index: int = Query(0, ge=0)) -> dict:
    sync = _state(request).p2p_sync
    results = sync.sync_all_peers(from_index=from_index)
    return {"results": results, "peer_count": len(results)}


@router.post("/sync/{peer_id}")
def sync_peer(peer_id: str, request: Request, from_index: int = Query(0, ge=0)) -> dict:
    state = _state(request)
    peer = state.p2p_peers.get_peer(peer_id)
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")
    sync = state.p2p_sync
    try:
        pulled = sync.pull_from_peer(peer, from_index=from_index)
        pushed = sync.push_to_peer(peer, from_index=from_index)
        sym = state.symbol_sync.sync_all_peers()
        return {"peer_id": peer_id, "pull": pulled, "push": pushed, "symbols": sym}
    except P2PSyncError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/symbols/public")
def get_public_symbols(request: Request) -> dict:
    symbols = _state(request).symbol_sync.get_local_symbols()
    return {"symbols": symbols, "count": len(symbols), "node_id": _state(request).p2p_identity.node_id}


@router.post("/symbols/receive")
def receive_symbols(body: dict, request: Request) -> dict:
    state = _state(request)
    symbols = body.get("symbols", {})
    from_node = body.get("from_node_id", "unknown")
    merged = state.symbol_sync.import_remote_symbols(symbols, from_node_id=from_node)
    return {"merged": merged, "received": len(symbols)}


@router.post("/symbols/sync")
def sync_symbols(request: Request) -> dict:
    results = _state(request).symbol_sync.sync_all_peers()
    return {"results": results}


@router.get("/gossip/announcements")
def gossip_announcements(request: Request) -> dict:
    return {"announcements": _state(request).gossip.list_announcements()}


@router.post("/gossip/announce")
def gossip_announce(request: Request, host: str = "127.0.0.1") -> dict:
    """Annonce ce nœud sur le réseau gossip.
    Le paramètre ``host`` peut être passé en query string pour exposer
    l'adresse publique réelle (ex: IP OVH, domaine ngrok…) plutôt que
    127.0.0.1 qui n'est accessible qu'en local.
    """
    state = _state(request)
    identity = state.p2p_identity
    import os
    public_host = os.getenv("ARTCB_PUBLIC_HOST", host)
    entry = state.gossip.announce(
        node_id=identity.node_id,
        host=public_host,
        api_port=identity.api_port,
        p2p_port=identity.p2p_port,
        kem_public_key_hex=identity.kem_public_key_hex,
        symbol_count=len(state.symbol_registry.export()),
    )
    return {"announcement": entry, "network_id": "artcb-devnet-1", "p2p_port": identity.p2p_port}


@router.post("/gossip/receive")
def gossip_receive(body: dict, request: Request) -> dict:
    entry = body.get("announcement", body)
    ok = _state(request).gossip.merge_remote_announcement(entry)
    return {"merged": ok}
