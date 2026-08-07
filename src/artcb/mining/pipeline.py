"""Pipeline minage unifié — apprentissage (sources) + raisonnement (dual-agent) + récompense PoL."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.artcb.ir.models import sha256_text
from src.artcb.rtleg.events import RTLEGEvent

if TYPE_CHECKING:
    from src.artcb.agents.critic import DualAgentLoop
    from src.artcb.chain.manager import ChainManager
    from src.artcb.connectors.manager import ConnectorManager
    from src.artcb.groups.manager import GroupManager
    from src.artcb.rtleg.timeline import RTLEGTimeline
    from src.artcb.wallet.manager import Wallet, WalletManager

logger = logging.getLogger("artcb.mining.pipeline")


@dataclass
class MiningPipelineResult:
    graph_id: str
    node_count: int
    pol_score: float
    block_index: int | None
    block_hash: str | None
    block_reward: int
    contributors: list[dict]
    phases: dict[str, Any]
    message: str


def build_contributors(
    *,
    actor_address: str,
    pol_score: float,
    wallet: Wallet | None = None,
    graph_root: str | None = None,
    extra_contributors: list[dict] | None = None,
    anti_sybil=None,
    source: str = "unknown",
) -> list[dict]:
    """
    Construit la liste contributeurs pour minage collectif PoL.

    PRE-FILTRE ANTI-SYBIL :
    Si anti_sybil est fourni, chaque candidat est vérifié AVANT d'être inclus.
    Un wallet en cooldown ou blacklisté n'est jamais ajouté à la liste —
    il ne reçoit ni job ni calcul à faire.

    - role ``learner``  : ingestion source externe
    - role ``reasoner`` : dual-agent Explorateur + Critique (raisonnement)
    """
    candidates: list[dict] = []
    for extra in extra_contributors or []:
        candidates.append({
            "address": extra["address"],
            "pol_score": float(extra.get("pol_score", pol_score)),
            "signature": extra.get("signature", ""),
            "role": extra.get("role", "contributor"),
        })

    signature = ""
    if wallet and graph_root:
        signature = wallet.sign(graph_root.encode("utf-8"))

    if actor_address and not any(c.get("address") == actor_address for c in candidates):
        candidates.append({
            "address": actor_address,
            "pol_score": pol_score,
            "signature": signature,
            "role": "reasoner",
        })

    # ── PRE-FILTRE : exclure les wallets inéligibles AVANT attribution ─
    if anti_sybil is not None and candidates:
        eligible, excluded = anti_sybil.filter_eligible_contributors(
            candidates, source=source
        )
        if excluded:
            import logging as _log
            _log.getLogger("artcb.mining.pipeline").warning(
                "build_contributors: %d wallet(s) exclus avant attribution job : %s",
                len(excluded),
                [e["address"][:12] + "… — " + e["reason"] for e in excluded],
            )
        return eligible

    return candidates


class MiningPipeline:
    """Enchaîne apprentissage → raisonnement → minage blockchain (connectés)."""

    def __init__(
        self,
        *,
        dual: DualAgentLoop,
        chain: ChainManager,
        wallet_manager: WalletManager | None = None,
        connectors: ConnectorManager | None = None,
        groups: GroupManager | None = None,
        timeline: RTLEGTimeline | None = None,
        register_graph=None,
        publish_public_symbols=None,
    ) -> None:
        self.dual = dual
        self.chain = chain
        self.wallet_manager = wallet_manager
        self.connectors = connectors
        self.groups = groups
        self.timeline = timeline
        self._register_graph = register_graph
        self._publish_public_symbols = publish_public_symbols

    def run_from_text(
        self,
        text: str,
        *,
        session_id: str = "mining_session",
        use_llm: bool = False,
        llm_provider: str | None = None,
        actor_address: str | None = None,
        wallet_name: str | None = None,
        wallet_password: str | None = None,
        visibility: str = "private",
        group_id: str | None = None,
        store_block: bool = True,
        learning_source: str | None = None,
        learning_offset: int = 0,
        extra_contributors: list[dict] | None = None,
    ) -> MiningPipelineResult:
        from src.artcb.ir.llm_encoder import LLMEncoder

        phases: dict[str, Any] = {"learning": None, "reasoning": None, "mining": None}

        if learning_source:
            phases["learning"] = {
                "source": learning_source,
                "chars": len(text),
                "offset": learning_offset,
            }

        if use_llm and self.connectors:
            graph = LLMEncoder(connectors=self.connectors).encode(
                text,
                use_llm=True,
                session_id=f"g_{uuid.uuid4().hex[:12]}",
                llm_provider=llm_provider,
            )
            result = self.dual.critic.validate(graph)
        else:
            result = self.dual.run(text)

        graph = result.graph
        pol = result.pol
        phases["reasoning"] = {
            "explorer_nodes": result.nodes_proposed,
            "critic_validated": result.nodes_validated,
            "pol_score": pol.pol_score,
            "block_accepted": pol.block_accepted,
        }

        if self._register_graph:
            self._register_graph(graph)

        if not pol.block_accepted:
            return MiningPipelineResult(
                graph_id=graph.graph_id,
                node_count=len(graph.nodes),
                pol_score=pol.pol_score,
                block_index=None,
                block_hash=None,
                block_reward=0,
                contributors=[],
                phases=phases,
                message="Raisonnement rejeté — PoL < seuil 0.6",
            )

        block_index = None
        block_hash = None
        block_reward = 0
        contributors: list[dict] = []

        if store_block:
            wallet = None
            if wallet_name and self.wallet_manager:
                try:
                    wallet = self.wallet_manager.load_wallet(name=wallet_name, user_password=wallet_password)
                    if not actor_address:
                        actor_address = wallet.address
                except Exception:
                    logger.warning("Wallet %s not found or wrong password for mining signature", wallet_name)

            if (
                visibility == "group"
                and group_id
                and self.groups
                and actor_address
                and not self.groups.is_member(group_id, actor_address)
            ):
                raise ValueError("actor not a group member")

            graph_root = sha256_text(graph.checksum).replace("sha256:", "")
            # PRE-FILTRE : passer l'anti_sybil pour que seuls les wallets
            # éligibles soient inclus — aucun inéligible ne reçoit un job
            anti_sybil = getattr(self.chain, "anti_sybil", None)
            contributors = build_contributors(
                actor_address=actor_address or "",
                pol_score=pol.pol_score,
                wallet=wallet,
                graph_root=graph_root,
                extra_contributors=extra_contributors,
                anti_sybil=anti_sybil,
                source="mining",
            )

            public_symbols = graph.orig_symbols if visibility == "public" and graph.orig_symbols else None

            block = self.chain.append_block(
                graph_id=graph.graph_id,
                graph_root=graph_root,
                pol_score=pol.pol_score,
                visibility=visibility,
                group_id=group_id,
                contributors=contributors if actor_address else None,
                public_symbols=public_symbols,
            )
            if visibility == "public" and public_symbols and self._publish_public_symbols:
                self._publish_public_symbols(
                    public_symbols,
                    block_index=block.index,
                    graph_id=graph.graph_id,
                )
            block_index = block.index
            block_hash = block.hash
            block_reward = block.block_reward
            contributors = block.contributors
            phases["mining"] = {
                "block_index": block_index,
                "reward_satoshi": block_reward,
                "contributor_count": len(contributors),
            }

            if self.timeline:
                self.timeline.append(
                    RTLEGEvent(
                        session_id=session_id,
                        agent="critic",
                        event_type="mining_block_stored",
                        graph_id=graph.graph_id,
                        payload={
                            "index": block_index,
                            "pol": pol.pol_score,
                            "learning_source": learning_source,
                            "phases": ["learning", "reasoning", "mining"],
                        },
                    )
                )

        return MiningPipelineResult(
            graph_id=graph.graph_id,
            node_count=len(graph.nodes),
            pol_score=pol.pol_score,
            block_index=block_index,
            block_hash=block_hash,
            block_reward=block_reward,
            contributors=contributors,
            phases=phases,
            message="Pipeline complet : apprentissage + raisonnement + minage PoL",
        )

    def run_from_connector(
        self,
        connector_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
        batch_index: int = 0,
        **kwargs: Any,
    ) -> MiningPipelineResult:
        from src.artcb.connectors.sources import DataSourceError, fetch_learning_text_batched

        if not self.connectors:
            raise DataSourceError("ConnectorManager not configured")
        record = self.connectors.get_connector(connector_id)
        if not record:
            raise DataSourceError("Connector not found")

        batch = fetch_learning_text_batched(record, limit=limit, offset=offset)
        source_label = f"{record.provider}:{record.label}:batch_{batch_index}"
        return self.run_from_text(
            batch.text,
            learning_source=source_label,
            learning_offset=offset,
            **kwargs,
        )
