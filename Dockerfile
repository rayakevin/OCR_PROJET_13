FROM python:3.12
WORKDIR /app
# The installer requires curl (and certificates) to download the release archive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates stockfish

# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"
ENV PATH="/app/.venv/bin/:$PATH"

# Copy the project into the image
COPY . .

# Sync the project into a new environment, asserting the lockfile is up to date
RUN uv sync --locked

# Setup an app user so the container doesn't run as the root user
RUN useradd app
USER app

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]