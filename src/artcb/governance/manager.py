"""Governance — proposals and majority vote (GOUVERNANCE_ARTCB.md §3).

DROITS CRÉATEUR (immuables — gravés dans le genesis block) :
  - CREATOR_WALLET_ADDRESS : chargé depuis data/founders/creator_rights.json
  - Si le créateur vote NON  → veto absolu, proposition rejetée
  - Si le créateur vote OUI  → acceptation immédiate
  - Le poids du créateur     = CREATOR_VOTE_WEIGHT (999 999 voix ordinaires)
  - Ces règles ne peuvent PAS être modifiées par un vote communautaire
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

logger = logging.getLogger("artcb.governance.manager")

VoteChoice = Literal["yes", "no"]
ProposalStatus = Literal["open", "accepted", "rejected", "expired"]

GOV_ID_PATTERN = re.compile(r"^GOV-\d{4}-\d{2}-\d{2}-\d{3}$")
DEFAULT_VOTE_DAYS = 14

# ─── Droits créateur ────────────────────────────────────────────────────────
# Poids du vote créateur : 1 vote créateur = CREATOR_VOTE_WEIGHT votes ordinaires
CREATOR_VOTE_WEIGHT = 999_999

# Fichier de référence des droits créateur (généré par init_genesis.py)
_CREATOR_RIGHTS_FILE = Path("data/founders/creator_rights.json")

# Mots-clés interdits dans les propositions (protège les droits créateur)
_FORBIDDEN_PROPOSAL_KEYWORDS = [
    "creator_wallet",
    "creator_veto",
    "creator_vote_weight",
    "creator_rights",
    "CREATOR_WALLET",
    "CREATOR_VOTE_WEIGHT",
    "remove creator",
    "retirer createur",
    "supprimer createur",
]


def _load_creator_wallet() -> str | None:
    """Charge l'adresse créateur depuis creator_rights.json (généré au genesis)."""
    if _CREATOR_RIGHTS_FILE.is_file():
        try:
            data = json.loads(_CREATOR_RIGHTS_FILE.read_text(encoding="utf-8"))
            addr = data.get("creator_wallet", "")
            if addr:
                logger.info("Creator wallet loaded: %s...", addr[:16])
                return addr
        except Exception as exc:
            logger.warning("Cannot load creator rights: %s", exc)
    logger.warning(
        "creator_rights.json not found — creator veto disabled. "
        "Run scripts/init_genesis.py to enable."
    )
    return None


# Adresse créateur chargée au démarrage du module
CREATOR_WALLET_ADDRESS: str | None = _load_creator_wallet()


class GovernanceError(Exception):
    """Governance operation failed."""


@dataclass
class Proposal:
    proposal_id: str
    title: str
    description: str
    version: str
    created_at: str
    closes_at: str
    status: ProposalStatus
    created_by: str = "ARTCB"

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "title": self.title,
            "description": self.description,
            "version": self.version,
            "created_at": self.created_at,
            "closes_at": self.closes_at,
            "status": self.status,
            "created_by": self.created_by,
        }


@dataclass
class Vote:
    proposal_id: str
    wallet_address: str
    choice: VoteChoice
    voted_at: str

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "wallet_address": self.wallet_address,
            "choice": self.choice,
            "voted_at": self.voted_at,
        }


class GovernanceManager:
    """Persist proposals and votes — 1 wallet = 1 voix."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir) / "governance"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.proposals_path = self.data_dir / "proposals.jsonl"
        self.votes_path = self.data_dir / "votes.jsonl"

    def _read_proposals(self) -> list[Proposal]:
        if not self.proposals_path.is_file():
            return []
        items: list[Proposal] = []
        for line in self.proposals_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                data = json.loads(line)
                items.append(Proposal(**data))
        return items

    def _write_proposals(self, proposals: list[Proposal]) -> None:
        with self.proposals_path.open("w", encoding="utf-8") as handle:
            for proposal in proposals:
                handle.write(json.dumps(proposal.to_dict(), ensure_ascii=False) + "\n")

    def _read_votes(self) -> list[Vote]:
        if not self.votes_path.is_file():
            return []
        items: list[Vote] = []
        for line in self.votes_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                items.append(Vote(**json.loads(line)))
        return items

    def _append_vote(self, vote: Vote) -> None:
        with self.votes_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(vote.to_dict(), ensure_ascii=False) + "\n")

    def _next_proposal_id(self) -> str:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        prefix = f"GOV-{today}-"
        existing = [p.proposal_id for p in self._read_proposals() if p.proposal_id.startswith(prefix)]
        seq = len(existing) + 1
        return f"{prefix}{seq:03d}"

    def _validate_proposal_content(self, title: str, description: str) -> None:
        """Rejette toute proposition qui tenterait de modifier les droits créateur."""
        combined = (title + " " + description).lower()
        for keyword in _FORBIDDEN_PROPOSAL_KEYWORDS:
            if keyword.lower() in combined:
                raise GovernanceError(
                    f"CREATOR_RIGHTS_IMMUTABLE: Cette proposition contient le terme interdit "
                    f"'{keyword}'. Les droits du créateur sont gravés dans le genesis block "
                    f"et ne peuvent jamais etre soumis au vote."
                )

    def create_proposal(
        self,
        *,
        title: str,
        description: str,
        version: str,
        vote_days: int = DEFAULT_VOTE_DAYS,
        created_by: str = "ARTCB",
        proposal_id: str | None = None,
    ) -> Proposal:
        # Validation anti-modification des droits créateur
        self._validate_proposal_content(title, description)

        now = datetime.now(UTC)
        closes = now + timedelta(days=vote_days)
        pid = proposal_id or self._next_proposal_id()
        if not GOV_ID_PATTERN.match(pid):
            raise GovernanceError(f"Invalid proposal id format: {pid}")
        proposal = Proposal(
            proposal_id=pid,
            title=title,
            description=description,
            version=version,
            created_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            closes_at=closes.strftime("%Y-%m-%dT%H:%M:%SZ"),
            status="open",
            created_by=created_by,
        )
        with self.proposals_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(proposal.to_dict(), ensure_ascii=False) + "\n")
        logger.info("Created governance proposal %s", pid)
        return proposal

    def list_proposals(self, status: ProposalStatus | None = None) -> list[Proposal]:
        proposals = self._refresh_statuses(self._read_proposals())
        if status:
            return [p for p in proposals if p.status == status]
        return proposals

    def get_proposal(self, proposal_id: str) -> Proposal | None:
        for proposal in self._refresh_statuses(self._read_proposals()):
            if proposal.proposal_id == proposal_id:
                return proposal
        return None

    def _refresh_statuses(self, proposals: list[Proposal]) -> list[Proposal]:
        now = datetime.now(UTC)
        changed = False
        for proposal in proposals:
            if proposal.status != "open":
                continue
            closes = datetime.strptime(proposal.closes_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
            if now <= closes:
                continue
            tally = self.tally(proposal.proposal_id)
            if tally["total_votes"] == 0:
                proposal.status = "expired"
            elif tally["majority_reject"]:
                proposal.status = "rejected"
            elif tally["majority_accept"]:
                proposal.status = "accepted"
            else:
                proposal.status = "expired"
            changed = True
        if changed:
            self._write_proposals(proposals)
        return proposals

    def cast_vote(self, *, proposal_id: str, wallet_address: str, choice: VoteChoice) -> Vote:
        from src.artcb.wallet.address import verify_address

        if choice not in ("yes", "no"):
            raise GovernanceError("choice must be 'yes' or 'no'")
        if not verify_address(wallet_address):
            raise GovernanceError("Invalid wallet address")

        proposal = self.get_proposal(proposal_id)
        if not proposal:
            raise GovernanceError("Proposal not found")
        if proposal.status != "open":
            raise GovernanceError(f"Proposal is not open (status={proposal.status})")

        now = datetime.now(UTC)
        closes = datetime.strptime(proposal.closes_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
        if now > closes:
            raise GovernanceError("Voting period has ended")

        for vote in self._read_votes():
            if vote.proposal_id == proposal_id and vote.wallet_address == wallet_address:
                raise GovernanceError("Wallet already voted on this proposal")

        vote = Vote(
            proposal_id=proposal_id,
            wallet_address=wallet_address,
            choice=choice,
            voted_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        self._append_vote(vote)
        logger.info("Vote cast proposal=%s wallet=%s choice=%s", proposal_id, wallet_address[:12], choice)
        return vote

    def tally(self, proposal_id: str) -> dict:
        """Calcule les résultats du vote avec droits créateur.

        Règles créateur (immuables) :
          - Vote OUI créateur → acceptation immédiate (quelles que soient les autres voix)
          - Vote NON créateur → veto absolu (rejet immédiat)
          - Poids créateur    = CREATOR_VOTE_WEIGHT (999 999 voix)
        """
        votes = [v for v in self._read_votes() if v.proposal_id == proposal_id]

        # ── Détecter le vote créateur ────────────────────────────────────
        creator_voted_yes = False
        creator_voted_no  = False
        if CREATOR_WALLET_ADDRESS:
            for v in votes:
                if v.wallet_address == CREATOR_WALLET_ADDRESS:
                    creator_voted_yes = (v.choice == "yes")
                    creator_voted_no  = (v.choice == "no")
                    break

        # ── Calcul pondéré ───────────────────────────────────────────────
        yes_weight = 0
        no_weight  = 0
        for v in votes:
            weight = (
                CREATOR_VOTE_WEIGHT
                if (CREATOR_WALLET_ADDRESS and v.wallet_address == CREATOR_WALLET_ADDRESS)
                else 1
            )
            if v.choice == "yes":
                yes_weight += weight
            else:
                no_weight += weight

        total = yes_weight + no_weight
        majority_accept = total > 0 and yes_weight > total / 2
        majority_reject = total > 0 and no_weight  > total / 2

        # ── Droits créateur absolus ──────────────────────────────────────
        if creator_voted_yes:
            majority_accept = True
            majority_reject = False
            logger.info(
                "CREATOR VOTE YES — proposal %s accepted by creator override", proposal_id
            )
        elif creator_voted_no:
            majority_reject = True
            majority_accept = False
            logger.warning(
                "CREATOR VETO NON — proposal %s rejected by creator veto", proposal_id
            )

        return {
            "proposal_id":        proposal_id,
            "yes":                yes_weight,
            "no":                 no_weight,
            "total_votes":        total,
            "majority_accept":    majority_accept,
            "majority_reject":    majority_reject,
            "requires_rollback":  majority_reject,
            "creator_voted_yes":  creator_voted_yes,
            "creator_voted_no":   creator_voted_no,
            "creator_veto_active": creator_voted_no,
            "creator_override":   creator_voted_yes,
            "creator_rights_enabled": CREATOR_WALLET_ADDRESS is not None,
        }

    def proposal_with_tally(self, proposal_id: str) -> dict:
        proposal = self.get_proposal(proposal_id)
        if not proposal:
            raise GovernanceError("Proposal not found")
        return {
            "proposal": proposal.to_dict(),
            "tally": self.tally(proposal_id),
        }
