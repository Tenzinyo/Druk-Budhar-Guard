# ============================================================
# BioTerrace Sentinel — Backend Container
# Base: python:3.11-slim  (~50 MB compressed)
# ============================================================

FROM python:3.11-slim

# Avoid interactive prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive
# Disable .pyc file generation; force stdout/stderr to be unbuffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ── System dependencies ───────────────────────────────────────
# curl is needed only for healthcheck scripts — removed in future hardening
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ───────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────
COPY . .

# ── Runtime directories ───────────────────────────────────────
# SQLite edge cache and audio cache are mounted as volumes in production,
# but must exist in the image for non-volume (dev) runs.
RUN mkdir -p app/db \
             app/audio_cache/templates

# ── Non-root user ─────────────────────────────────────────────
RUN addgroup --system sentinel && adduser --system --ingroup sentinel sentinel
RUN chown -R sentinel:sentinel /app
USER sentinel

# ── Expose & run ─────────────────────────────────────────────
EXPOSE 8000

# Single worker: edge deployment on low-RAM devices (512 MB–1 GB).
# Increase --workers for cloud deployment.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
