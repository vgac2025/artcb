# ARTCB Node — Dockerfile
# Usage : docker build -t artcb/node . && docker run -p 8000:8000 artcb/node
# Zero dépendance à ngrok — l'API est exposée directement sur le port 8000

FROM python:3.12-slim

# Outils de build pour liboqs et dépendances C
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc cmake make libssl-dev git curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copier d'abord les requirements pour profiter du cache Docker
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY data/ ./data/
COPY Makefile ./

# Variables d'environnement par défaut
ENV ARTCB_DEBUG=true \
    ARTCB_DATA_DIR=/app/data \
    ARTCB_LOG_DIR=/app/logs \
    ARTCB_REPORTS_DIR=/app/rapports \
    PYTHONPATH=/app \
    ARTCB_KEM_ENABLED=true

# Port API et port MCP HTTP
EXPOSE 8000 8001

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "src.api.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
