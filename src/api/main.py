"""FastAPI application — ARTCB MVP Phase 2+3."""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.artcb.logging_config import setup_logging

# Configure the root logger before importing routers and application state.
# Their module-level initialization can emit warnings/errors during startup.
setup_logging("artcb.api")
logger = logging.getLogger("artcb.api")

from src.api.api_keys_routes import router as api_keys_router
from src.api.auth_routes import router as auth_router
from src.api.ai_routes import router_ai, router_chain_ext, router_webhooks
from src.api.security_routes import router_security
from src.api.pol_phase11_routes import router as pol_phase11_router
from src.api.connectors_routes import router as connectors_router
from src.api.dashboard_routes import router as dashboard_router
from src.api.bridges_routes import router as bridges_router
from src.api.deps import build_app_state
from src.api.devnet_routes import router as devnet_router
from src.api.governance_routes import router as governance_router
from src.api.groups_routes import router as groups_router
from src.api.mining_routes import router as mining_router
from src.api.notifications_routes import router as notifications_router
from src.api.p2p_routes import router as p2p_router
from src.api.libp2p_routes import router as libp2p_router
from src.api.pool_routes import router as pool_router
from src.api.routes import router as api_router
from src.api.symbols_routes import router as symbols_router
from src.api.websocket import router as ws_router
from src.api.privacy_routes import router as privacy_router

def create_app() -> FastAPI:
    app = FastAPI(title="ARTCB API", version="0.3.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.artcb = build_app_state()
    app.include_router(auth_router)       # /api/v1/auth/login|challenge|verify|logout
    app.include_router(api_keys_router)
    app.include_router(api_router)
    app.include_router(devnet_router)
    app.include_router(symbols_router)
    app.include_router(groups_router)
    app.include_router(connectors_router)
    app.include_router(mining_router)
    app.include_router(governance_router)
    app.include_router(p2p_router)
    app.include_router(pool_router)
    app.include_router(notifications_router)
    app.include_router(dashboard_router)
    app.include_router(ws_router)
    app.include_router(router_ai)
    app.include_router(router_chain_ext)
    app.include_router(router_webhooks)
    app.include_router(router_security)
    app.include_router(pol_phase11_router)
    app.include_router(bridges_router)
    app.include_router(libp2p_router)
    app.include_router(privacy_router)
    logger.debug("ARTCB API started debug=%s", app.state.artcb.settings.debug)
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "ARTCB API",
            "version": "0.3.0"
        }

    # Serve React frontend (built dist/) at root
    _dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
    _dist = os.path.normpath(_dist)
    if os.path.isdir(_dist):
        app.mount("/assets", StaticFiles(directory=os.path.join(_dist, "assets")), name="assets")

        @app.get("/")
        async def serve_spa_root():
            return FileResponse(os.path.join(_dist, "index.html"))

        @app.get("/{full_path:path}")
        async def serve_spa_fallback(full_path: str):
            # API routes take precedence — only catch unknown paths
            if full_path.startswith("api/") or full_path.startswith("ws"):
                from fastapi import HTTPException
                raise HTTPException(status_code=404)
            return FileResponse(os.path.join(_dist, "index.html"))

    else:
        # FIX DÉPLOIEMENT : frontend pas encore buildé (dist/ absent).
        # Retourner 200 pour que le healthcheck Replit passe pendant le build en arrière-plan.
        from fastapi.responses import JSONResponse

        @app.get("/")
        async def serve_spa_loading():
            return JSONResponse(
                status_code=200,
                content={
                    "status": "starting",
                    "service": "ARTCB API",
                    "version": "0.3.0",
                    "note": "Frontend build in progress — API fully operational at /api/v1/"
                }
            )

        @app.get("/{full_path:path}")
        async def serve_spa_loading_fallback(full_path: str):
            if full_path.startswith("api/") or full_path.startswith("ws"):
                from fastapi import HTTPException
                raise HTTPException(status_code=404)
            return JSONResponse(
                status_code=200,
                content={"status": "starting", "note": "Frontend loading..."}
            )

    return app


app = create_app()
