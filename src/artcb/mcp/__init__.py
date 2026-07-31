"""ARTCB MCP Server — Model Context Protocol.

Rend ARTCB accessible depuis tout IDE compatible MCP :
Cursor, Bob (IBM), VSCode + Copilot, JetBrains AI, Lovable, Replit Agent, Claude Desktop.

Lancement :
    python -m src.artcb.mcp.server              # mode stdio (Cursor/Bob/VSCode)
    python -m src.artcb.mcp.server --http 8001  # mode HTTP/SSE (pour Replit/ngrok-free)

Config Cursor : .cursor/mcp.json
Config Bob    : voir docs/MCP_SETUP.md
"""
from .server import main, ArtcbMCPServer

__all__ = ["ArtcbMCPServer", "main"]
