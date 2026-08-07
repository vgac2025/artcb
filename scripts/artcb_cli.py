#!/usr/bin/env python3
"""
ARTCB CLI — accès complet API REST pour terminal (Linux, macOS, Windows).

Usage:
  python3 scripts/artcb_cli.py health
  python3 scripts/artcb_cli.py wallet create --name mon_wallet
  python3 scripts/artcb_cli.py pool run --text "..." --distributed --visibility private
  python3 scripts/artcb_cli.py mining pipeline --text "..." --visibility public

Variable d'environnement: ARTCB_API_BASE (défaut http://127.0.0.1:8000)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import httpx

DEFAULT_BASE = os.getenv("ARTCB_API_BASE", "http://127.0.0.1:8000").rstrip("/")
API = "/api/v1"


def _client(base: str) -> httpx.Client:
    return httpx.Client(base_url=base, timeout=120.0)


def _print(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _req(method: str, path: str, *, base: str, **kwargs) -> int:
    with _client(base) as c:
        r = getattr(c, method)(path, **kwargs)
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text, "status_code": r.status_code}
    if r.status_code >= 400:
        _print({"error": True, "status_code": r.status_code, "body": body})
        return 1
    _print(body)
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    return _req("get", f"{API}/health", base=args.base)


def cmd_chain(args: argparse.Namespace) -> int:
    if args.action == "list":
        params = {}
        if args.visibility:
            params["visibility"] = args.visibility
        if args.group_id:
            params["group_id"] = args.group_id
        return _req("get", f"{API}/chain", base=args.base, params=params)
    if args.action == "verify":
        return _req("get", f"{API}/chain/verify", base=args.base)
    if args.action == "block":
        return _req("get", f"{API}/chain/block/{args.index}", base=args.base)
    return 1


def cmd_pol(args: argparse.Namespace) -> int:
    return _req("get", f"{API}/pol/score", base=args.base)


def cmd_faucet(args: argparse.Namespace) -> int:
    if args.status:
        return _req("get", f"{API}/devnet/faucet/status", base=args.base)
    return _req("post", f"{API}/devnet/faucet", base=args.base, json={"address": args.address})


def cmd_symbols(args: argparse.Namespace) -> int:
    if args.action == "registry":
        return _req("get", f"{API}/symbols/registry", base=args.base)
    if args.action == "sync":
        return _req("post", f"{API}/symbols/sync", base=args.base)
    return 1


def cmd_metrics(args: argparse.Namespace) -> int:
    return _req("get", f"{API}/metrics", base=args.base)


def cmd_system(args: argparse.Namespace) -> int:
    if args.action == "hardware":
        return _req("get", f"{API}/system/hardware", base=args.base)
    if args.action == "optimization":
        return _req("get", f"{API}/system/optimization", base=args.base)
    return 1


def cmd_wallet(args: argparse.Namespace) -> int:
    if args.action == "create":
        pwd = getattr(args, "password", None) or "default_test_password"
        return _req("post", f"{API}/wallet/create", base=args.base, json={"name": args.name, "password": pwd})
    if args.action == "list":
        return _req("get", f"{API}/wallet/list", base=args.base)
    if args.action == "balance":
        if args.address:
            return _req("get", f"{API}/wallet/balance/{args.address}", base=args.base)
        return _req("post", f"{API}/wallet/balance", base=args.base, json={"address": args.address or ""})
    return 1


def cmd_agents(args: argparse.Namespace) -> int:
    return _req(
        "post",
        f"{API}/agents/run",
        base=args.base,
        json={
            "text": args.text,
            "session_id": args.session,
            "use_llm": args.use_llm,
        },
    )


def cmd_mining(args: argparse.Namespace) -> int:
    if args.action == "pipeline":
        body: dict[str, Any] = {
            "text": args.text,
            "session_id": args.session,
            "visibility": args.visibility,
            "use_distributed_pool": args.distributed,
            "encrypt_transport": True,
            "auto_finalize": args.auto_finalize,
            "chunk_chars": args.chunk_chars,
        }
        if args.wallet:
            body["wallet_name"] = args.wallet
        if args.actor:
            body["actor_address"] = args.actor
        if args.group_id:
            body["group_id"] = args.group_id
        return _req("post", f"{API}/mining/pipeline", base=args.base, json=body)
    if args.action == "status":
        return _req("get", f"{API}/dashboard/mining/status", base=args.base)
    return 1


def cmd_pool(args: argparse.Namespace) -> int:
    if args.action == "status":
        return _req("get", f"{API}/pool/status", base=args.base)
    if args.action == "preferences":
        if args.set_json:
            data = json.loads(args.set_json)
            return _req("put", f"{API}/pool/preferences", base=args.base, json=data)
        return _req("get", f"{API}/pool/preferences", base=args.base)
    if args.action == "run":
        body: dict[str, Any] = {
            "text": args.text,
            "use_distributed_pool": args.distributed,
            "encrypt_transport": not args.no_encrypt,
            "visibility": args.visibility,
            "auto_finalize": args.auto_finalize,
            "chunk_chars": args.chunk_chars,
        }
        if args.wallet:
            body["wallet_name"] = args.wallet
        if args.actor:
            body["actor_address"] = args.actor
        if args.group_id:
            body["group_id"] = args.group_id
        return _req("post", f"{API}/pool/run", base=args.base, json=body)
    if args.action == "jobs":
        return _req("get", f"{API}/pool/jobs", base=args.base)
    if args.action == "incoming":
        return _req("get", f"{API}/pool/incoming", base=args.base)
    if args.action == "process-all":
        body = {}
        if args.wallet:
            body["wallet_name"] = args.wallet
        if args.actor:
            body["contributor_address"] = args.actor
        return _req("post", f"{API}/pool/incoming/process-all", base=args.base, json=body)
    if args.action == "finalize":
        return _req(
            "post",
            f"{API}/pool/jobs/{args.job_id}/finalize",
            base=args.base,
            json={"full_text": args.text},
        )
    return 1


def cmd_p2p(args: argparse.Namespace) -> int:
    if args.action == "status":
        return _req("get", f"{API}/p2p/status", base=args.base)
    if args.action == "peers":
        return _req("get", f"{API}/p2p/peers", base=args.base)
    if args.action == "add-peer":
        return _req(
            "post",
            f"{API}/p2p/peers",
            base=args.base,
            json={
                "host": args.host,
                "port": args.port,
                "kem_public_key_hex": args.kem,
                "label": args.label or f"{args.host}:{args.port}",
            },
        )
    if args.action == "sync":
        return _req("post", f"{API}/p2p/sync", base=args.base)
    if args.action == "public-blocks":
        return _req("get", f"{API}/p2p/blocks/public", base=args.base)
    return 1


def cmd_groups(args: argparse.Namespace) -> int:
    if args.action == "list":
        params = {"address": args.address} if args.address else {}
        return _req("get", f"{API}/groups", base=args.base, params=params)
    if args.action == "create":
        return _req(
            "post",
            f"{API}/groups",
            base=args.base,
            json={"name": args.name, "founder_address": args.founder},
        )
    if args.action == "get":
        return _req("get", f"{API}/groups/{args.group_id}", base=args.base)
    return 1


def cmd_governance(args: argparse.Namespace) -> int:
    if args.action == "proposals":
        return _req("get", f"{API}/governance/proposals", base=args.base)
    return 1


def cmd_connectors(args: argparse.Namespace) -> int:
    if args.action == "list":
        return _req("get", f"{API}/connectors", base=args.base)
    if args.action == "formats":
        return _req("get", f"{API}/connectors/formats", base=args.base)
    return 1


def cmd_notifications(args: argparse.Namespace) -> int:
    if args.action == "channels":
        return _req("get", f"{API}/notifications/channels", base=args.base)
    return 1


def cmd_store(args: argparse.Namespace) -> int:
    body: dict[str, Any] = {
        "graph_id": args.graph_id,
        "session_id": args.session,
        "visibility": args.visibility,
    }
    if args.group_id:
        body["group_id"] = args.group_id
    if args.wallet:
        body["wallet_name"] = args.wallet
    if args.actor:
        body["actor_address"] = args.actor
    return _req("post", f"{API}/store", base=args.base, json=body)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="ARTCB CLI — API REST complète")
    p.add_argument("--base", default=DEFAULT_BASE, help=f"URL API (défaut {DEFAULT_BASE})")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("health", help="GET /health").set_defaults(func=cmd_health)

    ch = sub.add_parser("chain", help="Chaîne blockchain")
    ch.add_argument("action", choices=["list", "verify", "block"])
    ch.add_argument("--visibility", choices=["private", "public", "group"])
    ch.add_argument("--group-id")
    ch.add_argument("--index", type=int, default=0)
    ch.set_defaults(func=cmd_chain)

    sub.add_parser("pol", help="GET /pol/score").set_defaults(func=cmd_pol)

    sub.add_parser("metrics", help="GET /metrics (CPU, RAM, GPU, optimisations)").set_defaults(func=cmd_metrics)

    sys_cmd = sub.add_parser("system", help="Materiel et optimisations")
    sys_cmd.add_argument("action", choices=["hardware", "optimization"])
    sys_cmd.set_defaults(func=cmd_system)

    fc = sub.add_parser("faucet", help="Faucet tARTCB devnet")
    fc.add_argument("--address", default="")
    fc.add_argument("--status", action="store_true")
    fc.set_defaults(func=cmd_faucet)

    sym = sub.add_parser("symbols", help="Registre symboles IA")
    sym.add_argument("action", choices=["registry", "sync"])
    sym.set_defaults(func=cmd_symbols)

    w = sub.add_parser("wallet", help="Wallets")
    w.add_argument("action", choices=["create", "list", "balance"])
    w.add_argument("--name", default="cli_wallet")
    w.add_argument("--password", default="default_test_password", help="Mot de passe (min 8 chars) — chiffre la clé privée")
    w.add_argument("--address")
    w.set_defaults(func=cmd_wallet)

    ag = sub.add_parser("agents", help="Dual-agent")
    ag.add_argument("--text", required=True)
    ag.add_argument("--session", default="cli_session")
    ag.add_argument("--use-llm", action="store_true")
    ag.set_defaults(func=cmd_agents)

    m = sub.add_parser("mining", help="Minage pipeline")
    m.add_argument("action", choices=["pipeline", "status"])
    m.add_argument("--text", default="")
    m.add_argument("--session", default="cli_mining")
    m.add_argument("--visibility", default="private", choices=["private", "public", "group"])
    m.add_argument("--group-id")
    m.add_argument("--wallet")
    m.add_argument("--actor")
    m.add_argument("--distributed", action="store_true", help="Pool E2E ML-KEM")
    m.add_argument("--auto-finalize", action="store_true")
    m.add_argument("--chunk-chars", type=int, default=400)
    m.set_defaults(func=cmd_mining)

    pl = sub.add_parser("pool", help="Pool calcul distribué E2E")
    pl.add_argument(
        "action",
        choices=["status", "preferences", "run", "jobs", "incoming", "process-all", "finalize"],
    )
    pl.add_argument("--text", default="")
    pl.add_argument("--job-id")
    pl.add_argument("--visibility", default="private", choices=["private", "public", "group"])
    pl.add_argument("--group-id")
    pl.add_argument("--wallet")
    pl.add_argument("--actor")
    pl.add_argument("--distributed", action="store_true")
    pl.add_argument("--no-encrypt", action="store_true", help="Refusé par API si distribué")
    pl.add_argument("--auto-finalize", action="store_true")
    pl.add_argument("--chunk-chars", type=int, default=400)
    pl.add_argument("--set-json", help='JSON préférences ex: {"use_distributed_pool":true}')
    pl.set_defaults(func=cmd_pool)

    p2 = sub.add_parser("p2p", help="Réseau P2P devnet")
    p2.add_argument("action", choices=["status", "peers", "add-peer", "sync", "public-blocks"])
    p2.add_argument("--host", default="127.0.0.1")
    p2.add_argument("--port", type=int, default=8000)
    p2.add_argument("--kem", default="", help="Clé publique ML-KEM hex")
    p2.add_argument("--label")
    p2.set_defaults(func=cmd_p2p)

    g = sub.add_parser("groups", help="Groupes")
    g.add_argument("action", choices=["list", "create", "get"])
    g.add_argument("--address")
    g.add_argument("--name", default="CLI Group")
    g.add_argument("--founder")
    g.add_argument("--group-id")
    g.set_defaults(func=cmd_groups)

    gov = sub.add_parser("governance", help="Gouvernance")
    gov.add_argument("action", choices=["proposals"])
    gov.set_defaults(func=cmd_governance)

    cn = sub.add_parser("connectors", help="Connecteurs données")
    cn.add_argument("action", choices=["list", "formats"])
    cn.set_defaults(func=cmd_connectors)

    nt = sub.add_parser("notifications", help="Alertes Telegram")
    nt.add_argument("action", choices=["channels"])
    nt.set_defaults(func=cmd_notifications)

    st = sub.add_parser("store", help="Gravure bloc")
    st.add_argument("--graph-id", required=True)
    st.add_argument("--session", default="cli_store")
    st.add_argument("--visibility", default="private", choices=["private", "public", "group"])
    st.add_argument("--group-id")
    st.add_argument("--wallet")
    st.add_argument("--actor")
    st.set_defaults(func=cmd_store)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "faucet" and not args.status and not args.address:
        parser.error("faucet requires --address or --status")
    if args.command == "mining" and args.action == "pipeline" and not args.text:
        parser.error("mining pipeline requires --text")
    if args.command == "pool" and args.action == "run" and not args.text:
        parser.error("pool run requires --text")
    if args.command == "pool" and args.action == "finalize" and (not args.job_id or not args.text):
        parser.error("pool finalize requires --job-id and --text")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
