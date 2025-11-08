# Multi-stage Dockerfile optimized for UV package management
FROM python:3.11-slim AS builder

# Install system dependencies and UV
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    g++ \
    make \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /build

# Copy dependency files first (for better layer caching)
COPY pyproject.toml uv.lock* ./

# Install dependencies using UV
RUN uv pip install --system -r pyproject.toml

# Production stage
FROM python:3.11-slim AS production

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser migrations/ ./migrations/
COPY --chown=appuser:appuser pyproject.toml ./

# Set environment variables
ENV PYTHONPATH=/app/src:${PYTHONPATH}
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "complianceguard.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Development stage
FROM builder AS development

# Install UV in development mode
RUN uv pip install --system -e ".[dev]"

WORKDIR /app

# Copy all application code
COPY . .

# Install pre-commit hooks
RUN pre-commit install || true

ENV PYTHONPATH=/app/src:${PYTHONPATH}
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Development command with auto-reload
CMD ["uvicorn", "complianceguard.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]