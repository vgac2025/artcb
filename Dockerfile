# ARTCB — Image Docker officielle
# Build : docker build -t artcb/node:latest .
# Run   : docker run -p 8000:8000 --env-file .env artcb/node:latest

FROM python:3.12-slim-bullseye

LABEL maintainer="ARTCB <vgacofficiel@gmail.com>"
LABEL description="ARTCB Blockchain — Post-Quantum PoL Node"
LABEL version="0.3.0"

# Dépendances système pour liboqs (PQC ML-DSA-65 + ML-KEM-768)
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake \
    ninja-build \
    gcc \
    g++ \
    libssl-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copier requirements en premier (cache Docker layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Créer les répertoires runtime
RUN mkdir -p data/chain data/wallets data/fixtures logs rapports

# Variables d'environnement par défaut
ENV PYTHONPATH=/app \
    ARTCB_DEBUG=false \
    ARTCB_ENCODE_MODE=rule-based \
    ARTCB_LLM_ENABLED=false \
    ARTCB_DATA_DIR=/app/data \
    ARTCB_LOG_DIR=/app/logs \
    ARTCB_REPORTS_DIR=/app/rapports \
    ARTCB_PORT=8000 \
    ARTCB_HOST=0.0.0.0

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["python", "-m", "uvicorn", "src.api.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--log-level", "info"]
