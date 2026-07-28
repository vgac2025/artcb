"""Dashboard utility routes — logs réels, founders, minage (PROTOCOLE: pas de mock)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from src.artcb.tokenomics import HALVING_INTERVAL, INITIAL_BLOCK_REWARD_SATOSHI, MAX_HALVINGS

logger = logging.getLogger("artcb.api.dashboard")
router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _settings(request: Request):
    return request.app.state.artcb.settings


@router.get("/logs/demo-live")
def demo_live_log(request: Request) -> dict:
    settings = _settings(request)
    path = settings.log_dir / "demo_live_latest.txt"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="demo_live_latest.txt not found")
    content = path.read_text(encoding="utf-8", errors="replace")
    lines = content.strip().splitlines()
    return {"path": str(path), "lines": lines, "line_count": len(lines), "content": content}


@router.get("/logs/mining-latest")
def mining_latest_log(request: Request) -> dict:
    settings = _settings(request)
    log_dir = settings.log_dir
    candidates = sorted(log_dir.glob("mining_results_*.json"), reverse=True)
    if not candidates:
        raise HTTPException(status_code=404, detail="no mining_results_*.json in logs/")
    path = candidates[0]
    data = json.loads(path.read_text(encoding="utf-8"))
    return {"path": str(path), "data": data}


@router.get("/founders/allocation")
def founders_allocation(request: Request) -> dict:
    settings = _settings(request)
    path = settings.data_dir / "founders" / "founders_allocation.json"
    if not path.is_file():
        path = Path("data/founders/founders_allocation.json")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="founders_allocation.json not found")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/mining/status")
def mining_status(request: Request) -> dict:
    state = request.app.state.artcb
    blocks = state.chain._read_all_blocks()
    block_count = len(blocks)
    epoch_fixe = block_count // HALVING_INTERVAL if block_count else 0
    epoch_dyn  = state.chain._compute_dynamic_epoch(144, 86_400)
    epoch_total = epoch_fixe + epoch_dyn
    current_reward_satoshi = 0 if epoch_total >= MAX_HALVINGS else INITIAL_BLOCK_REWARD_SATOSHI >> epoch_total
    blocks_until_halving = HALVING_INTERVAL - (block_count % HALVING_INTERVAL) if block_count else HALVING_INTERVAL
    total_rewards = sum(b.get("block_reward", 0) for b in blocks)
    return {
        "block_count": block_count,
        "current_reward_artcb": current_reward_satoshi / 1e8,
        "current_reward_satoshi": current_reward_satoshi,
        "halving_interval": HALVING_INTERVAL,
        "blocks_until_halving": blocks_until_halving,
        "next_halving_at": ((block_count // HALVING_INTERVAL) + 1) * HALVING_INTERVAL,
        "total_rewards_artcb": total_rewards / 1e8,
        "pol_score": state.pol_state.get("pol_score"),
        "epoch_fixe": epoch_fixe,
        "epoch_dynamique": epoch_dyn,
        "epoch_total": epoch_total,
    }


@router.get("/wallet/{address}/rewards")
def wallet_rewards(address: str, request: Request) -> dict:
    state = request.app.state.artcb
    blocks = state.chain._read_all_blocks()
    rewards: list[dict] = []
    total = 0
    for block in blocks:
        for c in block.get("contributors", []):
            if c.get("address") == address:
                sat = int(c.get("reward_satoshi", 0))
                total += sat
                rewards.append({
                    "block_index": block.get("index"),
                    "reward_satoshi": sat,
                    "reward_artcb": sat / 1e8,
                    "pol_score": c.get("pol_score"),
                    "timestamp": block.get("timestamp"),
                })
    return {"address": address, "rewards": rewards, "total_satoshi": total, "total_artcb": total / 1e8}
