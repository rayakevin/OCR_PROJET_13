FROM python:3.12-slim

# Version fixe ; uv reste accessible aussi à l'utilisateur non privilégié.
COPY --from=ghcr.io/astral-sh/uv:0.11.15 /uv /usr/local/bin/uv

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates stockfish \
    && rm -rf /var/lib/apt/lists/*

# Cette couche reste en cache quand seul le code change.
# Aucun groupe optionnel : pas de sentence-transformers, PyTorch ou CUDA.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-default-groups --no-install-project --no-cache

# L'API n'a pas besoin des scripts, corpus locaux ou artefacts d'évaluation.
COPY backend ./backend

RUN useradd --create-home app
USER app

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
