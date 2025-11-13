## ---- Build stage: install only production dependencies into a venv ----
FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	VIRTUAL_ENV=/opt/venv \
	PATH="/opt/venv/bin:$PATH"

RUN python -m venv /opt/venv \
 && pip install --no-cache-dir --upgrade pip

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Optionally: copy sources for type checking/build steps only (kept minimal)

## ---- Runtime stage: minimal, non-root, healthcheck, hardened ----
FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	VIRTUAL_ENV=/opt/venv \
	PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Create non-root user with fixed UID/GID for better portability
RUN useradd -m -u 10001 appuser \
 && mkdir -p /app/logs \
 && chown -R appuser:appuser /app

# Copy virtualenv with installed runtime deps only
COPY --from=builder /opt/venv /opt/venv

# Copy application code (only what is necessary to run)
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser alembic ./alembic
COPY --chown=appuser:appuser alembic.ini ./alembic.ini
COPY --chown=appuser:appuser pyproject.toml requirements.txt README.md ./

EXPOSE 8000

# Healthcheck using Python stdlib (no curl needed)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD ["python","-c","import sys,urllib.request,urllib.error;\ntry:\n    r=urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)\n    sys.exit(0 if r.getcode()==200 else 1)\nexcept Exception:\n    sys.exit(1)"]

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
