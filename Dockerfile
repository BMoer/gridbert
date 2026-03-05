# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

# --- Stage 1: Frontend Build ---
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Python API ---
FROM python:3.12-slim AS runtime

# System deps for pdfplumber (poppler) and psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpoppler-cpp-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY pyproject.toml ./
RUN pip install --no-cache-dir . && pip install --no-cache-dir psycopg[binary]

# Copy application code
COPY gridbert/ gridbert/

# Copy frontend build output
COPY --from=frontend-build /app/frontend/dist /app/static

# Create non-root user
RUN useradd -m -r gridbert && mkdir -p /data /data/uploads && chown -R gridbert:gridbert /data
USER gridbert

# Environment
ENV ENVIRONMENT=production
ENV DATABASE_URL=sqlite:////data/gridbert.db
ENV UPLOAD_DIR=/data/uploads
ENV PORT=8000

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "gridbert.api.app:create_app", \
     "--factory", "--host", "0.0.0.0", "--port", "8000"]
