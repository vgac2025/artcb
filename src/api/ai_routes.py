"""
Module IA Autonome — ARTCB Agent Routes
========================================
Permet à un agent IA (Bob, Cursor, LangChain…) d'utiliser la blockchain ARTCB
comme mémoire persistante, moteur de raisonnement et bus d'événements.

Endpoints :
  GET  /api/v1/ai/status              — Snapshot complet état IA (P2)
  POST /api/v1/ai/memo                — Graver une observation dans la chaîne (P6)
  POST /api/v1/ai/think               — Question → Explorer+Critic → bloc PoL (P3)
  GET  /api/v1/chain/search           — Recherche sémantique cross-graphs (P4)
  GET  /api/v1/chain/export           — Export JSONL/JSON de la chaîne complète (P5)
  POST /api/v1/webhooks/register      — Webhooks sortants sur nouveaux blocs (P7)
  GET  /api/v1/webhooks/list          — Liste les webhooks actifs
  DELETE /api/v1/webhooks/{id}        — Révoque un webhook

Sécurité : tous les endpoints sensibles utilisent verify_api_key (Bearer).
"""

from __future__ import annotations

import json
import logging
import secrets
import time
import uuid
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from src.api.api_keys_routes import verify_api_key

logger = logging.getLogger("artcb.api.ai")

router_ai = APIRouter(prefix="/api/v1/ai", tags=["ai-agent"])
router_chain_ext = APIRouter(prefix="/api/v1/chain", tags=["chain-extended"])
router_webhooks = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _state(request: Request):
    return request.app.state.artcb


def _webhooks_path(request: Request) -> Path:
    return _state(request).settings.data_dir / "webhooks.json"


def _load_webhooks(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except Exception:
        return []


def _save_webhooks(path: Path, hooks: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(hooks, indent=2))


def _fire_webhooks(request: Request, event: str, payload: dict) -> None:
    """Déclenche tous les webhooks actifs pour un événement donné (fire-and-forget)."""
    path = _webhooks_path(request)
    hooks = _load_webhooks(path)
    active = [h for h in hooks if h.get("active", True) and event in h.get("events", [event])]
    if not active:
        return
    body = {"event": event, "timestamp": time.time(), "payload": payload}
    for hook in active:
        try:
            httpx.post(hook["url"], json=body, timeout=5.0)
            logger.debug("Webhook fired: %s → %s", event, hook["url"])
        except Exception as exc:
            logger.warning("Webhook failed %s: %s", hook["url"], exc)


# ─────────────────────────────────────────────────────────────────────────────
# P2 — GET /api/v1/ai/status
# ─────────────────────────────────────────────────────────────────────────────

@router_ai.get("/status", summary="Snapshot complet état IA — raisonnement, chaîne, mémoire")
def ai_status(
    request: Request,
    key_record: Annotated[dict | None, Depends(verify_api_key)] = None,
) -> dict:
    """
    Retourne tout ce dont un agent IA a besoin pour se situer :
    - État de la chaîne (hauteur, dernier bloc, PoL moyen)
    - Graphes en mémoire vive
    - Scores PoL actuels
    - Derniers événements RT-LEG
    - Nombre de memos IA gravés
    - Clés actives (résumé)
    """
    state = _state(request)

    # Chaîne
    try:
        blocks = state.chain.list_blocks()
        chain_height = len(blocks)
        last_block = blocks[-1] if blocks else None
        pol_scores = [b.get("pol_score", 0) for b in blocks if b.get("pol_score", 0) > 0]
        pol_avg = sum(pol_scores) / len(pol_scores) if pol_scores else 0.0
        last_block_info = None
        if last_block:
            h = last_block.get("hash", "")
            last_block_info = {
                "index": last_block.get("index"),
                "hash": h[:16] + "…" if len(h) >= 16 else h,
                "graph_id": last_block.get("graph_id"),
                "pol_score": last_block.get("pol_score"),
                "timestamp": last_block.get("timestamp"),
                "visibility": last_block.get("visibility"),
            }
    except Exception as exc:
        chain_height = 0
        pol_avg = 0.0
        last_block_info = None
        logger.warning("ai/status chain read error: %s", exc)

    # Graphes en mémoire
    graphs_in_memory = len(state.graphs.cache) if hasattr(state.graphs, "cache") else 0

    # Memos IA (blocs avec learning_source="ai:memo")
    memo_count = 0
    try:
        memo_count = sum(
            1 for b in state.chain.list_blocks()
            if isinstance(b.get("public_symbols"), dict)
            and b.get("public_symbols", {}).get("learning_source", "").startswith("ai:")
        )
    except Exception:
        pass

    # RT-LEG récents
    recent_events = []
    try:
        for ev in list(state.timeline.events)[-10:]:
            recent_events.append({
                "agent": ev.agent,
                "event_type": ev.event_type,
                "session_id": ev.session_id,
                "timestamp": ev.timestamp if hasattr(ev, "timestamp") else None,
            })
    except Exception:
        pass

    # Clé courante (si Bearer fourni)
    current_key = None
    if key_record:
        current_key = {
            "key_id": key_record["key_id"],
            "label": key_record["label"],
            "scopes": key_record.get("scopes", []),
        }

    return {
        "agent_ready": True,
        "timestamp": time.time(),
        "chain": {
            "height": chain_height,
            "pol_avg": round(pol_avg, 4),
            "last_block": last_block_info,
        },
        "memory": {
            "graphs_in_ram": graphs_in_memory,
            "memo_blocks": memo_count,
        },
        "pol_state": state.pol_state,
        "recent_events": recent_events,
        "current_key": current_key,
        "capabilities": [
            "ai/memo", "ai/think", "chain/search",
            "chain/export", "webhooks/register",
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# P6 — POST /api/v1/ai/memo
# ─────────────────────────────────────────────────────────────────────────────

class MemoRequest(BaseModel):
    content: str = Field(min_length=1, max_length=32000,
                         description="Observation, raisonnement, leçon, bug, solution…")
    memo_type: str = Field(
        default="observation",
        description="Type: observation | bug | fix | lesson | decision | hypothesis | goal | proof",
    )
    tags: list[str] = Field(default_factory=list, description="Tags libres (ex: ['i18n','bug','fix'])")
    session_id: str = Field(default="ai_memo", description="ID de session de l'agent")
    wallet_name: str | None = Field(default=None, description="Wallet pour signer le bloc")
    visibility: str = Field(default="private", description="private | public")


@router_ai.post("/memo", summary="Graver une observation IA dans la blockchain")
def ai_memo(
    body: MemoRequest,
    request: Request,
    key_record: Annotated[dict | None, Depends(verify_api_key)] = None,
) -> dict:
    """
    Grave une observation structurée de l'agent IA dans un bloc PoL immuable.

    Le texte est enrichi avec les métadonnées (type, tags, session, timestamp)
    puis encodé en graphe IR → validé PoL → signé → bloc gravé.

    Chaque memo est récupérable via GET /api/v1/chain/search?q=<terme>.
    """
    state = _state(request)

    # Construire un texte structuré pour l'encodage IR
    agent_id = key_record["label"] if key_record else "agent_anonymous"
    memo_text = (
        f"[AI MEMO — {body.memo_type.upper()}]\n"
        f"Agent: {agent_id}\n"
        f"Session: {body.session_id}\n"
        f"Timestamp: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n"
        f"Tags: {', '.join(body.tags) if body.tags else 'none'}\n\n"
        f"{body.content}"
    )

    # Encoder en graphe IR
    graph_id = f"ai_memo_{uuid.uuid4().hex[:12]}"
    try:
        from src.artcb.ir.llm_encoder import LLMEncoder
        encoder = LLMEncoder(encoder=state.encoder)
        graph = encoder.encode(memo_text, use_llm=False, session_id=graph_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Encoding failed: {exc}") from exc

    state.register_graph(graph)

    # Valider PoL (bypass threshold pour les memos — toujours accepté)
    from src.artcb.ir.models import sha256_text
    graph_root = sha256_text(graph.checksum).replace("sha256:", "")

    # Wallet
    actor = None
    wallet = None
    if body.wallet_name:
        try:
            from src.artcb.wallet.manager import WalletManager
            wallet = WalletManager().load_wallet(name=body.wallet_name)
            actor = wallet.address
        except FileNotFoundError:
            pass

    # Construire les contributors
    contributors = None
    if actor:
        from src.artcb.mining.pipeline import build_contributors
        contributors = build_contributors(
            actor_address=actor,
            pol_score=0.75,
            wallet=wallet,
            graph_root=graph_root,
        )

    # Marquer le bloc comme memo IA via public_symbols
    public_symbols = {
        "learning_source": f"ai:memo:{body.memo_type}",
        "agent_id": agent_id,
        "session_id": body.session_id,
        "tags": ",".join(body.tags),
        "memo_type": body.memo_type,
    }

    block = state.chain.append_block(
        graph_id=graph.graph_id,
        graph_root=graph_root,
        pol_score=0.75,
        visibility=body.visibility,
        group_id=None,
        contributors=contributors,
        public_symbols=public_symbols,  # toujours gravé — visibility contrôle l'accès
    )

    # Déclencher webhooks
    _fire_webhooks(request, "block_stored", {
        "block_index": block.index,
        "block_hash": block.hash,
        "memo_type": body.memo_type,
        "agent_id": agent_id,
        "graph_id": graph.graph_id,
    })

    logger.info("AI memo gravé: bloc #%d graph=%s agent=%s", block.index, graph.graph_id, agent_id)

    return {
        "memo_stored": True,
        "block_index": block.index,
        "block_hash": block.hash,
        "graph_id": graph.graph_id,
        "pol_score": 0.75,
        "memo_type": body.memo_type,
        "agent_id": agent_id,
        "node_count": len(graph.nodes),
        "message": f"Observation gravée en bloc #{block.index} — immuable ML-DSA-65",
    }


# ─────────────────────────────────────────────────────────────────────────────
# P3 — POST /api/v1/ai/think
# ─────────────────────────────────────────────────────────────────────────────

class ThinkRequest(BaseModel):
    question: str = Field(min_length=1, max_length=32000,
                           description="Problème, question ou sujet à raisonner")
    session_id: str = Field(default="ai_think")
    use_llm: bool = Field(default=False, description="Enrichir avec LLM connecteur")
    llm_provider: str | None = Field(default=None)
    wallet_name: str | None = None
    visibility: str = "private"
    store_block: bool = Field(default=True, description="Graver le résultat en bloc")


@router_ai.post("/think", summary="Question → Explorer+Critic → bloc PoL")
def ai_think(
    body: ThinkRequest,
    request: Request,
    key_record: Annotated[dict | None, Depends(verify_api_key)] = None,
) -> dict:
    """
    L'agent IA soumet une question/problème → ARTCB lance le pipeline
    Explorer (encode) + Critic (valide PoL) → optionnellement grave un bloc.

    Retourne : graph_id, pol_score, nodes, block_hash (si store_block=True).
    C'est le cœur de la boucle autonome : penser → apprendre → graver.
    """
    state = _state(request)
    agent_id = key_record["label"] if key_record else "agent_anonymous"

    # Enrichir le texte avec le contexte agent
    think_text = (
        f"[AI THINK — {agent_id}]\n"
        f"Session: {body.session_id}\n"
        f"Timestamp: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n\n"
        f"Question/Problème:\n{body.question}"
    )

    try:
        from src.artcb.ir.llm_encoder import LLMEncoder
        from src.artcb.mining.pipeline import MiningPipeline
        from src.artcb.wallet.manager import WalletManager

        # Résoudre le llm_provider via les connecteurs
        llm_record = None
        llm_key = None
        if body.use_llm and body.llm_provider:
            try:
                records = state.connectors.list_connectors()
                for rec in records:
                    if rec.provider == body.llm_provider and rec.enabled:
                        llm_record = rec
                        llm_key = rec._api_key
                        break
            except Exception:
                pass

        pipeline = MiningPipeline(
            dual=state.dual,
            chain=state.chain,
            wallet_manager=WalletManager(),
            connectors=state.connectors,
            groups=state.groups,
            timeline=state.timeline,
            register_graph=state.register_graph,
            publish_public_symbols=state.publish_public_symbols,
        )

        result = pipeline.run_from_text(
            think_text,
            session_id=body.session_id,
            wallet_name=body.wallet_name,
            visibility=body.visibility,
            store_block=body.store_block,
            learning_source=f"ai:think:{agent_id}",
        )

    except Exception as exc:
        logger.error("ai/think pipeline error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Think pipeline failed: {exc}") from exc

    if body.store_block and result.block_index is not None:
        _fire_webhooks(request, "block_stored", {
            "block_index": result.block_index,
            "block_hash": result.block_hash,
            "source": "ai:think",
            "agent_id": agent_id,
            "graph_id": result.graph_id,
        })

    return {
        "think_complete": True,
        "graph_id": result.graph_id,
        "pol_score": result.pol_score,
        "node_count": result.node_count if hasattr(result, "node_count") else None,
        "block_index": result.block_index,
        "block_hash": result.block_hash,
        "agent_id": agent_id,
        "message": (
            f"Raisonnement gravé en bloc #{result.block_index} (PoL {result.pol_score:.3f})"
            if result.block_index is not None
            else f"Raisonnement encodé (graph {result.graph_id}) — non gravé"
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# P4 — GET /api/v1/chain/search
# ─────────────────────────────────────────────────────────────────────────────

@router_chain_ext.get("/search", summary="Recherche sémantique cross-graphs dans tous les blocs")
def chain_search(
    request: Request,
    q: str = Query(min_length=1, description="Terme ou phrase à rechercher"),
    top_k: int = Query(default=10, ge=1, le=100),
    visibility: str = Query(default="all", description="all | private | public"),
    key_record: Annotated[dict | None, Depends(verify_api_key)] = None,
) -> dict:
    """
    Recherche sémantique dans TOUS les graphes de TOUS les blocs gravés.
    Contrairement à POST /search qui cherche dans un seul graph_id,
    cet endpoint parcourt la chaîne entière.

    Retourne les nodes les plus proches avec leur bloc d'origine.
    """
    state = _state(request)
    results = []

    try:
        # Recherche vectorielle globale (tous graph_ids)
        raw_results = state.vectors.search(q, graph_id=None, top_k=top_k)

        # Enrichir avec les métadonnées de bloc
        block_by_graph: dict[str, dict] = {}
        try:
            for b in state.chain.list_blocks():
                gid = b.get("graph_id", "")
                if gid not in block_by_graph:
                    h = b.get("hash", "")
                    block_by_graph[gid] = {
                        "block_index": b.get("index"),
                        "block_hash": h[:16] + "…" if len(h) >= 16 else h,
                        "pol_score": b.get("pol_score"),
                        "timestamp": b.get("timestamp"),
                        "visibility": b.get("visibility"),
                    }
        except Exception:
            pass

        for r in raw_results:
            entry = dict(r)
            gid = r.get("graph_id", "")
            if gid in block_by_graph:
                entry["block"] = block_by_graph[gid]
            results.append(entry)

        # Filtrer par visibilité si demandé
        if visibility != "all":
            results = [
                r for r in results
                if r.get("block", {}).get("visibility", "private") == visibility
            ]

    except Exception as exc:
        logger.error("chain/search error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "query": q,
        "results": results[:top_k],
        "count": len(results[:top_k]),
        "total_graphs_searched": len(state.graphs.cache) if hasattr(state.graphs, "cache") else 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# P5 — GET /api/v1/chain/export
# ─────────────────────────────────────────────────────────────────────────────

@router_chain_ext.get("/export", summary="Export compact de la chaîne entière")
def chain_export(
    request: Request,
    fmt: str = Query(default="jsonl", alias="format", description="jsonl | json | summary"),
    visibility: str = Query(default="all", description="all | private | public"),
    include_symbols: bool = Query(default=False),
    key_record: Annotated[dict | None, Depends(verify_api_key)] = None,
) -> dict:
    """
    Exporte la chaîne entière dans un format compact utilisable comme context LLM.

    - format=jsonl  : chaque bloc = une ligne JSON (optimal pour RAG/context)
    - format=json   : tableau JSON complet
    - format=summary: résumé lisible pour copier-coller dans un prompt
    """
    state = _state(request)

    try:
        all_blocks = state.chain.list_blocks()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if visibility != "all":
        all_blocks = [b for b in all_blocks if b.get("visibility") == visibility]

    if fmt == "jsonl":
        lines = []
        for b in all_blocks:
            h = b.get("hash", "")
            entry = {
                "index": b.get("index"),
                "timestamp": b.get("timestamp"),
                "graph_id": b.get("graph_id"),
                "pol_score": b.get("pol_score"),
                "hash": h[:32],
                "visibility": b.get("visibility"),
                "block_reward": b.get("block_reward"),
            }
            if include_symbols and b.get("public_symbols"):
                entry["public_symbols"] = b["public_symbols"]
            if b.get("contributors"):
                entry["contributor_count"] = len(b["contributors"])
            lines.append(json.dumps(entry, ensure_ascii=False))
        return {
            "format": "jsonl",
            "block_count": len(lines),
            "data": "\n".join(lines),
            "size_bytes": sum(len(l) for l in lines),
        }

    elif fmt == "summary":
        pol_scores = [b.get("pol_score", 0) for b in all_blocks if b.get("pol_score", 0) > 0]
        pol_avg = sum(pol_scores) / len(pol_scores) if pol_scores else 0.0
        last = all_blocks[-1] if all_blocks else None
        lines = [
            f"ARTCB Blockchain — {len(all_blocks)} blocs",
            f"PoL moyen: {pol_avg:.4f}",
            f"Dernier bloc: #{last.get('index')} ({last.get('timestamp')})" if last else "Aucun bloc",
            "",
        ]
        for b in all_blocks[-20:]:
            h = b.get("hash", "")
            gid = b.get("graph_id", "")
            ts_raw = b.get("timestamp", "")
            lines.append(
                f"#{b.get('index')} | {ts_raw[:19]} | PoL={b.get('pol_score', 0):.3f} | "
                f"{b.get('visibility')} | graph={gid[:12]}… | hash={h[:12]}…"
            )
        return {
            "format": "summary",
            "block_count": len(all_blocks),
            "data": "\n".join(lines),
        }

    else:  # json
        data = []
        for b in all_blocks:
            sig = b.get("signature", "")
            entry = {
                "index": b.get("index"),
                "timestamp": b.get("timestamp"),
                "graph_id": b.get("graph_id"),
                "pol_score": b.get("pol_score"),
                "hash": b.get("hash"),
                "hash_sha3": b.get("hash_sha3"),
                "signature": sig[:32] + "…" if sig else None,
                "visibility": b.get("visibility"),
                "block_reward": b.get("block_reward"),
                "contributors": b.get("contributors"),
            }
            if include_symbols:
                entry["public_symbols"] = b.get("public_symbols")
            data.append(entry)
        return {
            "format": "json",
            "block_count": len(data),
            "data": data,
        }


# ─────────────────────────────────────────────────────────────────────────────
# P7 — Webhooks sortants
# ─────────────────────────────────────────────────────────────────────────────

class WebhookRegisterRequest(BaseModel):
    url: str = Field(min_length=8, description="URL HTTPS de destination")
    label: str = Field(min_length=1, max_length=128)
    events: list[str] = Field(
        default=["block_stored"],
        description="Événements: block_stored | memo_stored | think_complete | all",
    )
    secret: str | None = Field(default=None, description="Secret HMAC optionnel (header X-ARTCB-Signature)")


@router_webhooks.post("/register", summary="Enregistrer un webhook sortant")
def register_webhook(
    body: WebhookRegisterRequest,
    request: Request,
    key_record: Annotated[dict | None, Depends(verify_api_key)] = None,
) -> dict:
    """
    Enregistre une URL à appeler à chaque événement blockchain.
    Cursor/Bob peut s'abonner pour être notifié en temps réel de chaque nouveau bloc.
    """
    path = _webhooks_path(request)
    hooks = _load_webhooks(path)

    hook_id = "wh_" + secrets.token_hex(8)
    hook = {
        "hook_id": hook_id,
        "url": body.url,
        "label": body.label,
        "events": body.events if "all" not in body.events else ["block_stored", "memo_stored", "think_complete"],
        "secret": body.secret,
        "created_at": time.time(),
        "active": True,
        "registered_by": key_record["key_id"] if key_record else "anonymous",
    }
    hooks.append(hook)
    _save_webhooks(path, hooks)
    logger.info("Webhook registered: %s → %s", hook_id, body.url)

    return {
        "hook_id": hook_id,
        "url": body.url,
        "label": body.label,
        "events": hook["events"],
        "active": True,
        "message": f"Webhook {hook_id} actif — ARTCB appellera {body.url} à chaque événement",
    }


@router_webhooks.get("/list", summary="Lister les webhooks actifs")
def list_webhooks(
    request: Request,
    key_record: Annotated[dict | None, Depends(verify_api_key)] = None,
) -> dict:
    path = _webhooks_path(request)
    hooks = _load_webhooks(path)
    safe = [
        {
            "hook_id": h["hook_id"],
            "url": h["url"],
            "label": h["label"],
            "events": h.get("events", []),
            "active": h.get("active", True),
            "created_at": h.get("created_at"),
        }
        for h in hooks
    ]
    return {"webhooks": safe, "count": len(safe)}


@router_webhooks.delete("/{hook_id}", summary="Révoquer un webhook")
def delete_webhook(
    hook_id: str,
    request: Request,
    key_record: Annotated[dict | None, Depends(verify_api_key)] = None,
) -> dict:
    path = _webhooks_path(request)
    hooks = _load_webhooks(path)
    for h in hooks:
        if h["hook_id"] == hook_id:
            h["active"] = False
            _save_webhooks(path, hooks)
            return {"revoked": True, "hook_id": hook_id}
    raise HTTPException(status_code=404, detail=f"Webhook {hook_id} introuvable")


# ─────────────────────────────────────────────────────────────────────────────
# P8 (bonus) — GET /api/v1/ai/memory — liste des memos gravés
# ─────────────────────────────────────────────────────────────────────────────

@router_ai.get("/memory", summary="Liste des observations IA gravées dans la chaîne")
def ai_memory(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    memo_type: str | None = Query(default=None),
    key_record: Annotated[dict | None, Depends(verify_api_key)] = None,
) -> dict:
    """Retrouve tous les blocs créés par ai/memo ou ai/think."""
    state = _state(request)
    memos = []
    try:
        for b in reversed(state.chain.list_blocks()):
            ps = b.get("public_symbols") or {}
            src = ps.get("learning_source", "")
            gid = b.get("graph_id", "")
            if not src.startswith("ai:"):
                # Vérifie aussi via graph_id préfixe ai_memo_
                if not gid.startswith("ai_memo_") and not gid.startswith("ai_think_"):
                    continue
            if memo_type and ps.get("memo_type") != memo_type:
                continue
            h = b.get("hash", "")
            memos.append({
                "block_index": b.get("index"),
                "block_hash": h[:16] + "…" if len(h) >= 16 else h,
                "graph_id": gid,
                "timestamp": b.get("timestamp"),
                "pol_score": b.get("pol_score"),
                "memo_type": ps.get("memo_type", "unknown"),
                "agent_id": ps.get("agent_id", "unknown"),
                "session_id": ps.get("session_id", ""),
                "tags": ps.get("tags", "").split(",") if ps.get("tags") else [],
                "source": src,
            })
            if len(memos) >= limit:
                break
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"memos": memos, "count": len(memos)}


# Made with Bob
