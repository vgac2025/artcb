"""
Anti-Sybil Validator — Détection attaques Sybil sur réseau ARTCB

Mesures implémentées :
1. Vérification PoL minimum (seuil 0.6)
2. Détection patterns suspects (même IP, même signature)
3. Limite contributeurs par bloc
4. Historique réputation par adresse
5. [STUDY MODE] Compteur métriques — mesure l'usage réel sans limiter les IA
   → permet de calibrer les limites futures sur données réelles

Variables d'environnement :
  ARTCB_MIN_BLOCK_INTERVAL_SEC   Intervalle min entre blocs (défaut: 60s)
  ARTCB_ANTI_SYBIL_AI_BYPASS     "true" = bypass rate-limit pour blocs IA
                                  (ne désactive PAS PoL min ni blacklist)
  ARTCB_ANTI_SYBIL_STUDY_MODE   "true" = log tout sans rejeter pour rate-limit
                                  (utile pendant le dev pour mesurer l'usage réel)
"""

import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ReputationScore:
    """Score de réputation d'une adresse"""
    address: str
    total_blocks: int = 0
    total_pol_score: float = 0.0
    rejected_blocks: int = 0
    last_block_time: datetime | None = None
    suspicious_patterns: list[str] = field(default_factory=list)

    @property
    def avg_pol_score(self) -> float:
        if self.total_blocks == 0:
            return 0.0
        return self.total_pol_score / self.total_blocks

    @property
    def rejection_rate(self) -> float:
        total = self.total_blocks + self.rejected_blocks
        if total == 0:
            return 0.0
        return self.rejected_blocks / total

    @property
    def is_suspicious(self) -> bool:
        return (
            self.rejection_rate > 0.5
            or len(self.suspicious_patterns) >= 3
            or self.avg_pol_score < 0.3
        )


@dataclass
class RateLimitMetric:
    """
    Métrique de tentative (aurait été rejetée ou acceptée).
    Stockée même en mode bypass pour mesurer l'usage réel.
    """
    address: str
    block_index: int
    elapsed_seconds: float        # temps depuis dernier bloc de cette adresse
    would_reject: bool            # True = aurait été rejeté avec la limite courante
    limit_seconds: float          # la limite configurée au moment de la tentative
    bypass_applied: bool          # True = bypass AI activé → bloc gravé quand même
    source: str                   # "ai_memo" | "ai_think" | "mining" | "unknown"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "address": self.address[:16] + "…",
            "block_index": self.block_index,
            "elapsed_s": round(self.elapsed_seconds, 2),
            "would_reject": self.would_reject,
            "limit_s": self.limit_seconds,
            "bypass": self.bypass_applied,
            "source": self.source,
            "ts": self.timestamp,
        }


class AntiSybilMetrics:
    """
    Accumulateur de métriques Anti-Sybil — étude mode study / mode bypass.

    Toutes les tentatives sont comptées, qu'elles soient bypassées ou rejetées.
    Ces données permettront de calibrer les limites futures sur l'usage réel.
    """

    def __init__(self, window_seconds: int = 3600):
        self.window_seconds = window_seconds          # fenêtre glissante analyse
        self._events: list[RateLimitMetric] = []      # historique complet

        # Compteurs globaux
        self.total_attempts: int = 0
        self.total_would_reject: int = 0              # auraient été rejetés
        self.total_bypassed: int = 0                  # bypassés grâce au bypass AI
        self.total_hard_rejected: int = 0             # vraiment rejetés (pas de bypass)

        # Par adresse : intervalles observés (pour calibrage)
        self._intervals_by_addr: dict[str, list[float]] = defaultdict(list)

    def record(self, metric: RateLimitMetric) -> None:
        self.total_attempts += 1
        if metric.would_reject:
            self.total_would_reject += 1
            if metric.bypass_applied:
                self.total_bypassed += 1
            else:
                self.total_hard_rejected += 1
        if metric.elapsed_seconds > 0:
            self._intervals_by_addr[metric.address].append(metric.elapsed_seconds)
        self._events.append(metric)

    def _recent(self) -> list[RateLimitMetric]:
        """Événements dans la fenêtre glissante."""
        cutoff = time.time() - self.window_seconds
        return [e for e in self._events if e.timestamp >= cutoff]

    def snapshot(self) -> dict:
        """
        Snapshot complet pour l'endpoint /security/anti-sybil/metrics.
        Contient tout ce qu'il faut pour calibrer la limite future.
        """
        recent = self._recent()
        n_recent = len(recent)
        n_would_reject_recent = sum(1 for e in recent if e.would_reject)
        n_bypass_recent = sum(1 for e in recent if e.bypass_applied)

        # Distribution des intervalles observés (toutes adresses)
        all_intervals: list[float] = []
        for intervals in self._intervals_by_addr.values():
            all_intervals.extend(intervals)

        interval_stats: dict[str, Any] = {}
        if all_intervals:
            sorted_iv = sorted(all_intervals)
            n = len(sorted_iv)
            interval_stats = {
                "min_s": round(sorted_iv[0], 2),
                "p50_s": round(sorted_iv[n // 2], 2),
                "p90_s": round(sorted_iv[int(n * 0.9)], 2),
                "p99_s": round(sorted_iv[int(n * 0.99)], 2),
                "max_s": round(sorted_iv[-1], 2),
                "sample_count": n,
            }

        # Par adresse : résumé
        per_addr: list[dict] = []
        addr_counts: dict[str, dict] = {}
        for e in recent:
            k = e.address
            if k not in addr_counts:
                addr_counts[k] = {"attempts": 0, "would_reject": 0, "bypass": 0, "source": e.source}
            addr_counts[k]["attempts"] += 1
            if e.would_reject:
                addr_counts[k]["would_reject"] += 1
            if e.bypass_applied:
                addr_counts[k]["bypass"] += 1
        for addr, cnt in addr_counts.items():
            ivs = self._intervals_by_addr.get(addr, [])
            cnt["min_interval_s"] = round(min(ivs), 2) if ivs else None
            per_addr.append(cnt)
        per_addr.sort(key=lambda x: x["attempts"], reverse=True)

        # Recommandation dynamique de limite
        recommendation = self._recommend_limit(all_intervals)

        return {
            "window_seconds": self.window_seconds,
            "totals": {
                "attempts": self.total_attempts,
                "would_have_been_rejected": self.total_would_reject,
                "bypassed_by_ai_mode": self.total_bypassed,
                "hard_rejected": self.total_hard_rejected,
                "bypass_rate_pct": round(
                    self.total_bypassed / self.total_would_reject * 100, 1
                ) if self.total_would_reject > 0 else 0.0,
            },
            "recent_window": {
                "attempts": n_recent,
                "would_reject": n_would_reject_recent,
                "bypassed": n_bypass_recent,
            },
            "interval_distribution": interval_stats,
            "per_address_top10": per_addr[:10],
            "recommendation": recommendation,
            "last_events": [e.to_dict() for e in list(reversed(self._events))[:20]],
        }

    def _recommend_limit(self, intervals: list[float]) -> dict:
        """
        Calcule une recommandation dynamique de limite basée sur les intervalles réels.
        Logique : ne rejeter que les <5% les plus rapides (queue basse).
        """
        if len(intervals) < 5:
            return {
                "status": "insufficient_data",
                "message": f"Besoin de ≥5 intervalles observés (actuellement {len(intervals)}). Continue en mode étude.",
                "suggested_limit_s": None,
            }
        sorted_iv = sorted(intervals)
        n = len(sorted_iv)
        # p5 = 5ème percentile → rejeter seulement ce qui est plus rapide que ça
        p5 = sorted_iv[max(0, int(n * 0.05))]
        p50 = sorted_iv[n // 2]
        # Arrondi au multiple de 5s le plus proche
        suggested = max(1, round(p5 / 5) * 5)
        return {
            "status": "ready",
            "message": (
                f"Sur {n} intervalles observés : médiane={p50:.0f}s, p5={p5:.1f}s. "
                f"Limite suggérée : {suggested}s (rejetterait ~5% des blocs les plus rapides)."
            ),
            "suggested_limit_s": suggested,
            "p5_interval_s": round(p5, 2),
            "p50_interval_s": round(p50, 2),
            "sample_count": n,
        }


class AntiSybilValidator:
    """
    Validateur Anti-Sybil pour prévenir attaques réseau.

    Règles actives :
    - PoL minimum 0.6 par bloc                         → TOUJOURS actif
    - Maximum 10 contributeurs par bloc                → TOUJOURS actif
    - Blacklist / réputation suspecte                  → TOUJOURS actif
    - Rate-limit (1 bloc / ARTCB_MIN_BLOCK_INTERVAL_SEC) →
        * Désactivé pour blocs IA si ARTCB_ANTI_SYBIL_AI_BYPASS=true
        * Logué même si bypassé (métriques)
        * Désactivé pour TOUS si ARTCB_ANTI_SYBIL_STUDY_MODE=true

    En mode bypass/study : le slashing est aussi supprimé pour les memos IA.
    """

    def __init__(
        self,
        min_pol_score: float = 0.6,
        max_contributors_per_block: int = 10,
        min_block_interval_seconds: int | None = None,
        reputation_file: Path | None = None,
    ):
        if min_block_interval_seconds is None:
            min_block_interval_seconds = int(os.getenv("ARTCB_MIN_BLOCK_INTERVAL_SEC", "60"))

        self.min_pol_score = min_pol_score
        self.max_contributors_per_block = max_contributors_per_block
        self.min_block_interval = timedelta(seconds=min_block_interval_seconds)
        self.reputation_file = reputation_file or Path("data/reputation.json")

        # Modes configurables via .env
        self.ai_bypass: bool = os.getenv("ARTCB_ANTI_SYBIL_AI_BYPASS", "false").lower() == "true"
        self.study_mode: bool = os.getenv("ARTCB_ANTI_SYBIL_STUDY_MODE", "false").lower() == "true"

        # Cache réputation en mémoire
        self.reputation: dict[str, ReputationScore] = {}

        # Métriques
        self.metrics = AntiSybilMetrics()

        logger.info(
            "AntiSybilValidator initialized: min_pol=%.2f max_contributors=%d "
            "min_interval=%ds ai_bypass=%s study_mode=%s",
            min_pol_score,
            max_contributors_per_block,
            min_block_interval_seconds,
            self.ai_bypass,
            self.study_mode,
        )

    def validate_block(
        self,
        contributors: list[dict],
        pol_score: float,
        block_index: int,
        source: str = "unknown",   # "ai_memo" | "ai_think" | "mining"
    ) -> tuple[bool, str | None]:
        """
        Valide un bloc contre attaques Sybil.

        Args:
            contributors: Liste contributeurs [{"address": str, "pol_score": float, ...}]
            pol_score: Score PoL global du bloc
            block_index: Index du bloc
            source: Origine du bloc (utilisé pour le bypass AI)

        Returns:
            (valid, reason) — True si valide, sinon (False, raison)
        """
        # ── Règle 1 : PoL minimum (TOUJOURS actif) ─────────────────────────
        if pol_score < self.min_pol_score:
            reason = f"PoL score {pol_score:.2f} < minimum {self.min_pol_score}"
            logger.warning("Block %d rejected: %s", block_index, reason)
            return False, reason

        # ── Règle 2 : Nombre contributeurs (TOUJOURS actif) ────────────────
        if len(contributors) > self.max_contributors_per_block:
            reason = f"{len(contributors)} contributors > max {self.max_contributors_per_block}"
            logger.warning("Block %d rejected: %s", block_index, reason)
            return False, reason

        # ── Règle 3 : Par contributeur ─────────────────────────────────────
        now = datetime.now(UTC)
        limit_s = self.min_block_interval.total_seconds()
        is_ai_source = source.startswith("ai:")
        bypass_rate_limit = self.ai_bypass and is_ai_source or self.study_mode

        for contributor in contributors:
            address = contributor.get("address", "")
            contrib_pol = contributor.get("pol_score", 0.0)

            # PoL individuel minimum (TOUJOURS actif)
            if contrib_pol < 0.3:
                reason = f"Contributor {address[:12]}... PoL {contrib_pol:.2f} < 0.3"
                logger.warning("Block %d rejected: %s", block_index, reason)
                self._record_rejection(address, reason)
                return False, reason

            # Rate-limit — mesurer + conditionnel
            if address in self.reputation:
                rep = self.reputation[address]
                if rep.last_block_time:
                    elapsed = (now - rep.last_block_time).total_seconds()
                    would_reject = elapsed < limit_s

                    # Toujours enregistrer la métrique (étude)
                    self.metrics.record(RateLimitMetric(
                        address=address,
                        block_index=block_index,
                        elapsed_seconds=elapsed,
                        would_reject=would_reject,
                        limit_seconds=limit_s,
                        bypass_applied=bypass_rate_limit and would_reject,
                        source=source,
                    ))

                    if would_reject:
                        if bypass_rate_limit:
                            # Bypass AI — on log mais on n'arrête pas
                            logger.debug(
                                "Anti-Sybil rate-limit BYPASSED (ai_bypass=%s study=%s): "
                                "%s… %.1fs < %.0fs — bloc IA signé normalement",
                                self.ai_bypass, self.study_mode,
                                address[:12], elapsed, limit_s,
                            )
                        else:
                            reason = (
                                f"Contributor {address[:12]}... too fast: "
                                f"{elapsed:.1f}s < {limit_s:.0f}s"
                            )
                            logger.warning("Block %d rejected: %s", block_index, reason)
                            self._record_rejection(address, "rate_limit")
                            return False, reason

                # Blacklist / réputation (TOUJOURS actif)
                if rep.is_suspicious:
                    reason = (
                        f"Contributor {address[:12]}... suspicious "
                        f"(rejection_rate={rep.rejection_rate:.2f}, "
                        f"patterns={len(rep.suspicious_patterns)})"
                    )
                    logger.warning("Block %d rejected: %s", block_index, reason)
                    return False, reason

        # ── Règle 4 : Adresses dupliquées (TOUJOURS actif) ─────────────────
        addresses = [c.get("address", "") for c in contributors]
        if len(addresses) != len(set(addresses)):
            reason = "Duplicate addresses in contributors"
            logger.warning("Block %d rejected: %s", block_index, reason)
            return False, reason

        logger.debug("Block %d passed anti-Sybil validation (source=%s)", block_index, source)
        return True, None

    def record_valid_block(
        self,
        contributors: list[dict],
        pol_score: float,
        block_index: int,
    ) -> None:
        now = datetime.now(UTC)
        for contributor in contributors:
            address = contributor.get("address", "")
            contrib_pol = contributor.get("pol_score", 0.0)
            if address not in self.reputation:
                self.reputation[address] = ReputationScore(address=address)
            rep = self.reputation[address]
            rep.total_blocks += 1
            rep.total_pol_score += contrib_pol
            rep.last_block_time = now
        logger.debug("Block %d recorded in reputation for %d contributors", block_index, len(contributors))

    def _record_rejection(self, address: str, reason: str) -> None:
        if address not in self.reputation:
            self.reputation[address] = ReputationScore(address=address)
        rep = self.reputation[address]
        rep.rejected_blocks += 1
        if reason not in rep.suspicious_patterns:
            rep.suspicious_patterns.append(reason)

    def get_reputation(self, address: str) -> ReputationScore | None:
        return self.reputation.get(address)

    def blacklist_address(self, address: str, reason: str) -> None:
        if address not in self.reputation:
            self.reputation[address] = ReputationScore(address=address)
        rep = self.reputation[address]
        rep.suspicious_patterns.append(f"BLACKLISTED: {reason}")
        rep.rejected_blocks += 100
        logger.warning("Address %s... blacklisted: %s", address[:12], reason)

    def get_suspicious_addresses(self) -> list[str]:
        return [addr for addr, rep in self.reputation.items() if rep.is_suspicious]
