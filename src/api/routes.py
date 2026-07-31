"""REST routes — CDC §8."""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from src.artcb.ir.encoder import IREncoder
from src.artcb.ir.llm_encoder import LLMEncoder
from src.artcb.ir.models import sha256_text
from src.artcb.rtleg.events import RTLEGEvent

logger = logging.getLogger("artcb.api.routes")
router = APIRouter(prefix="/api/v1")


class EncodeRequest(BaseModel):
    text: str = Field(min_length=1)
    session_id: str = "sess_default"
    use_llm: bool = False


class DecodeRequest(BaseModel):
    graph_id: str


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    graph_id: str | None = None
    top_k: int = 3


class StoreRequest(BaseModel):
    graph_id: str | None = None
    text: str | None = Field(default=None, min_length=1, description="Auto-encode si graph_id absent")
    session_id: str = "sess_default"
    visibility: str = "private"
    group_id: str | None = None
    actor_address: str | None = None
    wallet_name: str | None = Field(default=None, description="Wallet pour signature minage raisonnement")


class AgentRunRequest(BaseModel):
    text: str = Field(min_length=1)
    session_id: str = "sess_default"
    use_llm: bool = False
    llm_provider: str | None = Field(
        default=None,
        description="openai | anthropic | bob — utilise le connecteur utilisateur",
    )


def _state(request: Request):
    return request.app.state.artcb


@router.get("/demo/wailly-excerpt")
def wailly_excerpt(request: Request, max_pages: int = 3) -> dict:
    """Load Wailly book excerpt for demo (D-010)."""
    from src.artcb.io.pdf_loader import extract_pdf_text, resolve_book_path

    path = resolve_book_path()
    state = _state(request)
    if path is None:
        fallback = state.settings.demo_book_pdf
        if fallback.is_file():
            path = fallback
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Wailly PDF not found")
    text = extract_pdf_text(path, max_pages=max_pages)
    return {
        "source": "wailly_le_roi_de_l_inconnu.pdf",
        "max_pages": max_pages,
        "char_count": len(text),
        "text": text,
    }


@router.get("/health")
def health(request: Request) -> dict:
    state = _state(request)
    chain_status = {"available": False}
    try:
        chain_status = {"available": True, **state.chain.verify()}
    except FileNotFoundError as exc:
        chain_status = {"available": False, "message": str(exc)}
    return {
        "status": "ok",
        "debug": state.settings.debug,
        "llm_enabled": state.settings.llm_enabled,
        "bob_configured": bool(state.settings.bob_api_key),
        "demo_book": str(state.settings.demo_book_pdf),
        "chain": chain_status,
    }


@router.post("/encode")
def encode(body: EncodeRequest, request: Request) -> dict:
    state = _state(request)
    graph_id = f"g_{uuid.uuid4().hex[:12]}"
    llm_encoder = LLMEncoder(encoder=state.encoder)
    graph = llm_encoder.encode(body.text, use_llm=body.use_llm, session_id=graph_id)
    state.register_graph(graph)
    state.vectors.index_graph(graph)

    state.timeline.append(
        RTLEGEvent(
            session_id=body.session_id,
            agent="explorer",
            event_type="encode",
            graph_id=graph.graph_id,
            payload={"node_count": len(graph.nodes), "use_llm": body.use_llm},
        )
    )

    compression = IREncoder.compression_ratio(graph)
    return {
        "graph_id": graph.graph_id,
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "compression_ratio": compression,
        "pol_score": None,
        "nodes_preview": [n.model_dump() for n in graph.nodes[:5]],
    }


@router.post("/decode")
def decode(body: DecodeRequest, request: Request) -> dict:
    state = _state(request)
    graph = state.get_graph(body.graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="graph not found")
    metrics = state.decoder.decode_with_metrics(graph)
    return {
        "original_text": metrics["text"],
        "similarity": metrics["similarity"],
        "reversible": metrics["reversible"],
    }


@router.get("/graph/{graph_id}")
def get_graph(graph_id: str, request: Request) -> dict:
    state = _state(request)
    graph = state.get_graph(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="graph not found")
    return graph.to_canonical_dict()


@router.get("/node/{node_id}")
def get_node(
    node_id: str,
    request: Request,
    graph_id: str | None = Query(default=None),
) -> dict:
    state = _state(request)
    if graph_id:
        graph = state.get_graph(graph_id)
        if not graph:
            raise HTTPException(status_code=404, detail="graph not found")
        for node in graph.nodes:
            if node.id == node_id:
                return node.model_dump()
        raise HTTPException(status_code=404, detail="node not found")

    if node_id in state.node_index:
        gid, _ = state.node_index[node_id]
        graph = state.get_graph(gid)
        if graph:
            for node in graph.nodes:
                if node.id == node_id:
                    return {**node.model_dump(), "graph_id": gid}
    raise HTTPException(status_code=404, detail="node not found")


@router.post("/search")
def search(body: SearchRequest, request: Request) -> dict:
    state = _state(request)
    results = state.vectors.search(body.query, graph_id=body.graph_id, top_k=body.top_k)
    return {"query": body.query, "results": results, "count": len(results)}


@router.post("/store")
async def store(body: StoreRequest, request: Request) -> dict:
    state = _state(request)

    # BUG-P0-2 : auto-encode si text fourni sans graph_id
    if not body.graph_id and body.text:
        graph_id = f"g_{uuid.uuid4().hex[:12]}"
        from src.artcb.ir.llm_encoder import LLMEncoder
        llm_encoder = LLMEncoder(encoder=state.encoder)
        graph = await asyncio.to_thread(
            lambda: llm_encoder.encode(body.text, use_llm=False, session_id=graph_id)
        )
        state.register_graph(graph)
        state.vectors.index_graph(graph)
    elif body.graph_id:
        graph = state.get_graph(body.graph_id)
        if not graph:
            raise HTTPException(status_code=404, detail="graph not found")
    else:
        raise HTTPException(status_code=422, detail="graph_id ou text requis")

    if body.visibility not in ("private", "group", "public"):
        raise HTTPException(status_code=422, detail="visibility must be private, group, or public")

    group_id: str | None = None
    if body.visibility == "group":
        if not body.group_id:
            raise HTTPException(status_code=422, detail="group_id required for visibility=group")
        if not body.actor_address:
            raise HTTPException(status_code=422, detail="actor_address required for visibility=group")
        if not state.groups.is_member(body.group_id, body.actor_address):
            raise HTTPException(status_code=403, detail="not a group member")
        group_id = body.group_id

    result = state.dual.critic.validate(graph)
    pol = result.pol
    if not pol.block_accepted:
        state.pol_state["blocks_rejected"] += 1
        raise HTTPException(
            status_code=422,
            detail={"message": "PoL below threshold", "pol": pol.to_dict()},
        )

    graph_root = sha256_text(graph.checksum).replace("sha256:", "")

    contributors = None
    actor = body.actor_address
    wallet = None
    if body.wallet_name:
        from src.artcb.wallet.manager import WalletManager

        try:
            wallet = WalletManager().load_wallet(name=body.wallet_name)
            actor = actor or wallet.address
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=f"wallet not found: {body.wallet_name}") from exc

    if actor:
        from src.artcb.mining.pipeline import build_contributors

        contributors = build_contributors(
            actor_address=actor,
            pol_score=pol.pol_score,
            wallet=wallet,
            graph_root=graph_root,
        )

    public_symbols = graph.orig_symbols if body.visibility == "public" and graph.orig_symbols else None

    block = state.chain.append_block(
        graph_id=graph.graph_id,
        graph_root=graph_root,
        pol_score=pol.pol_score,
        visibility=body.visibility,
        group_id=group_id,
        contributors=contributors,
        public_symbols=public_symbols,
    )
    if body.visibility == "public" and public_symbols:
        state.publish_public_symbols(
            public_symbols,
            block_index=block.index,
            graph_id=graph.graph_id,
        )
    state.pol_state["pol_score"] = pol.pol_score
    state.pol_state["delta_compression"] = pol.delta_compression
    state.pol_state["validation_rate"] = pol.validation_rate
    state.pol_state["retrieval_accuracy"] = pol.retrieval_accuracy
    state.pol_state["blocks_accepted"] += 1

    state.timeline.append(
        RTLEGEvent(
            session_id=body.session_id,
            agent="critic",
            event_type="block_stored",
            graph_id=graph.graph_id,
            payload={"index": block.index, "hash": block.hash, "pol": pol.pol_score},
        )
    )

    try:
        state.notifications.broadcast(
            event="block_stored",
            subject=f"ARTCB bloc #{block.index}",
            body=(
                f"Graphe {graph.graph_id} gravé — visibilité {block.visibility} — "
                f"PoL {pol.pol_score:.2f} — reward {block.block_reward / 1e8:.4f} ARTCB"
            ),
        )
    except Exception as exc:
        logger.warning("Notification broadcast failed (non bloquant): %s", exc)

    return {
        "block_index": block.index,
        "hash": block.hash,
        "block_reward": block.block_reward,
        "contributors": block.contributors,
        "signature": block.signature,
        "pol_score": pol.pol_score,
        "graph_id": graph.graph_id,
        "visibility": block.visibility,
        "group_id": block.group_id,
    }


@router.get("/chain")
def chain_list(
    request: Request,
    visibility: str | None = Query(None),
    group_id: str | None = Query(None),
) -> dict:
    state = _state(request)
    blocks = state.chain.list_blocks(visibility=visibility, group_id=group_id)
    return {"blocks": blocks, "count": len(blocks)}


@router.get("/chain/block/{block_index}")
def chain_block_detail(block_index: int, request: Request) -> dict:
    state = _state(request)
    blocks = state.chain._read_all_blocks()
    for block in blocks:
        if block.get("index") == block_index:
            return {"block": block}
    raise HTTPException(status_code=404, detail="block not found")


@router.get("/chain/verify")
def chain_verify(request: Request) -> dict:
    state = _state(request)
    return state.chain.verify()


@router.get("/pol/score")
def pol_score(request: Request) -> dict:
    return _state(request).pol_state

@router.get("/metrics")
def system_metrics(request: Request) -> dict:
    """Metriques temps reel + materiel + optimisations actives."""
    try:
        from src.artcb.system.hardware import detect_hardware, live_metrics
        from src.artcb.system.optimizer import build_optimization_profile

        state = request.app.state.artcb
        hw = state.hardware or detect_hardware()
        opt = state.optimization or build_optimization_profile(hw)
        live = live_metrics()
        hw_dict = hw.to_dict()
        return {
            **live,
            "system": hw_dict["platform"],
            "hardware": hw_dict,
            "optimization": opt.to_dict(),
        }
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="psutil not installed") from exc
    except Exception as e:
        logger.error("Error fetching system metrics: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/system/hardware")
def system_hardware(request: Request) -> dict:
    """Profil materiel detecte (CPU, RAM, GPU, disque)."""
    from src.artcb.system.hardware import detect_hardware

    state = request.app.state.artcb
    hw = state.hardware or detect_hardware()
    return hw.to_dict()


@router.get("/system/optimization")
def system_optimization(request: Request) -> dict:
    """Profil d'optimisation runtime adapte au materiel."""
    from src.artcb.system.optimizer import build_optimization_profile

    state = request.app.state.artcb
    if state.optimization is not None:
        return state.optimization.to_dict()
    hw = state.hardware
    return build_optimization_profile(hw).to_dict()


# ============================================================================
# WALLET ROUTES — Rewards & Balance Tracking
# ============================================================================

class CreateWalletRequest(BaseModel):
    name: str = "default"


class WalletBalanceRequest(BaseModel):
    address: str


@router.post("/wallet/create")
def wallet_create(body: CreateWalletRequest, request: Request) -> dict:
    """Create new ARTCB wallet with Ed25519 keypair."""
    from src.artcb.wallet.manager import WalletManager

    _state(request)
    wallet_mgr = WalletManager()

    try:
        wallet = wallet_mgr.create_wallet(name=body.name)
        logger.info("Created wallet name=%s address=%s", body.name, wallet.address)
        return {
            "name": body.name,
            "address": wallet.address,
            "public_key_hex": wallet.public_key_hex,
            "public_key_b64": wallet.public_key_b64,
        }
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/wallet/list")
def wallet_list(request: Request) -> dict:
    """List all wallets."""
    from src.artcb.wallet.manager import WalletManager

    wallet_mgr = WalletManager()
    wallets = wallet_mgr.list_wallets()
    return {"wallets": wallets, "count": len(wallets)}


@router.post("/wallet/balance")
def wallet_balance(body: WalletBalanceRequest, request: Request) -> dict:
    """Get wallet balance from blockchain."""
    from src.artcb.wallet.manager import WalletManager

    state = _state(request)
    wallet_mgr = WalletManager()

    balance = wallet_mgr.get_balance_with_faucet(
        body.address,
        state.chain.blocks_path,
        state.faucet.ledger_path,
    )
    return balance


@router.get("/wallet/balance/{address}")
def wallet_balance_get(address: str, request: Request) -> dict:
    """Get wallet balance from blockchain (GET variant)."""
    from src.artcb.wallet.manager import WalletManager

    state = _state(request)
    wallet_mgr = WalletManager()

    balance = wallet_mgr.get_balance_with_faucet(
        address,
        state.chain.blocks_path,
        state.faucet.ledger_path,
    )
    return balance




@router.post("/agents/run")
def agents_run(body: AgentRunRequest, request: Request) -> dict:
    state = _state(request)
    if body.use_llm:
        graph = LLMEncoder(encoder=state.encoder, connectors=state.connectors).encode(
            body.text,
            use_llm=True,
            session_id=f"g_{uuid.uuid4().hex[:12]}",
            llm_provider=body.llm_provider,
        )
        result = state.dual.critic.validate(graph)
    else:
        result = state.dual.run(body.text)

    graph = result.graph
    state.register_graph(graph)
    state.vectors.index_graph(graph)

    pol = result.pol
    state.pol_state["pol_score"] = pol.pol_score
    state.pol_state["compression_rate"] = pol.delta_compression
    state.pol_state["validation_rate"] = pol.validation_rate
    state.pol_state["retrieval_accuracy"] = pol.retrieval_accuracy
    if pol.block_accepted:
        state.pol_state["blocks_accepted"] += 1
    else:
        state.pol_state["blocks_rejected"] += 1

    state.timeline.append(
        RTLEGEvent(
            session_id=body.session_id,
            agent="critic",
            event_type="pol_validated",
            graph_id=graph.graph_id,
            payload=pol.to_dict(),
        )
    )

    return {
        "graph_id": graph.graph_id,
        "node_count": len(graph.nodes),
        "pol": pol.to_dict(),
        "nodes_validated": result.nodes_validated,
        "nodes_proposed": result.nodes_proposed,
        "symbol_proposals": [
            {"concept": p.concept, "symbol": p.symbol, "status": p.status, "reason": p.reason}
            for p in result.symbol_proposals
        ],
        "orig_symbols": graph.orig_symbols,
    }


@router.get("/rtleg/events")
def rtleg_events(
    request: Request,
    session_id: str | None = None,
    limit: int = 100,
) -> dict:
    state = _state(request)
    events = state.timeline.list_events(session_id=session_id, limit=limit)
    return {"events": [e.model_dump() for e in events], "count": len(events)}
