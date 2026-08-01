@echo off
REM ARTCB — Script d'installation Windows
REM Testé sur Windows 10/11 avec Python 3.12+
REM ================================================================

echo ================================================================
echo   ARTCB Blockchain Node — Installation Windows
echo ================================================================

REM ── 1. Vérification Python ──────────────────────────────────────
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Python non trouvé.
    echo Télécharger Python 3.12+ : https://python.org/downloads
    echo Cocher "Add to PATH" lors de l'installation.
    pause
    exit /b 1
)

python -c "import sys; exit(0 if sys.version_info >= (3,12) else 1)"
if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Python 3.12+ requis.
    pause
    exit /b 1
)
echo [OK] Python détecté

REM ── 2. Environnement virtuel ────────────────────────────────────
if not exist ".venv" (
    echo [INFO] Création environnement virtuel...
    python -m venv .venv
)
call .venv\Scripts\activate.bat
echo [OK] Environnement virtuel activé

REM ── 3. Dépendances Python ───────────────────────────────────────
echo [INFO] Installation des dépendances Python...
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo [OK] Dépendances installées

REM ── 4. Fichier .env ─────────────────────────────────────────────
if not exist ".env" (
    copy .env.example .env
    echo [INFO] .env créé depuis .env.example
    echo [INFO] Editer .env si nécessaire ^(ETHEREUM_RPC_URL, etc.^)
)

REM ── 5. Répertoires ──────────────────────────────────────────────
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "rapports" mkdir rapports

REM ── 6. PYTHONPATH ───────────────────────────────────────────────
set PYTHONPATH=%CD%
set ARTCB_DEBUG=true

REM ── 7. Smoke test ───────────────────────────────────────────────
echo [INFO] Smoke test...
python -c "from src.artcb.ir.encoder import IREncoder; print('[OK] IR Engine')"
python -c "from src.artcb.chain.manager import ChainManager; print('[OK] Chain')"
python -c "from src.artcb.mcp.server import ArtcbMCPServer; print('[OK] MCP Server')"

echo.
echo ================================================================
echo   Installation terminee !
echo.
echo   Lancer l'API  : python -m uvicorn src.api.main:app --port 8000
echo   Lancer MCP    : python -m src.artcb.mcp.server --http 8001
echo   Lancer tests  : python -m pytest tests\ -q
echo.
echo   Pour activer le MCP dans VSCode :
echo   Copier .vscode\settings.json dans votre projet
echo   (deja present dans ce repo)
echo ================================================================
pause
