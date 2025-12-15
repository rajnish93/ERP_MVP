# =============================================================================
# Multi-stage Dockerfile for FastAPI Application
# =============================================================================
# This Dockerfile uses a two-stage build process:
# 1. Builder stage: Installs UV and Python dependencies into a virtualenv
# 2. Runtime stage: Copies only the virtualenv and app code (no UV needed)
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
# Purpose: Install UV, create virtualenv, and install all Python dependencies
# Note: UV is only needed during build, not at runtime
# -----------------------------------------------------------------------------
FROM python:3.13-slim AS builder

# Install UV using pip (UV is only needed in builder stage)
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy dependency files (for better Docker layer caching)
# If pyproject.toml or uv.lock changes, only this layer needs to be rebuilt
COPY pyproject.toml uv.lock* ./

# Sync dependencies from lock file into a virtualenv
# UV sync reads pyproject.toml and uv.lock for deterministic installs
# --frozen: Use exact versions from lock file (no updates)
# --no-dev: Skip dev dependencies for production builds
RUN uv sync --frozen --no-dev


# -----------------------------------------------------------------------------
# Stage 2: Runtime
# -----------------------------------------------------------------------------
# Purpose: Create minimal runtime image with only Python, virtualenv, and app
# Note: UV is NOT included - only the installed packages are copied
# -----------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

# Set working directory
WORKDIR /app

# -----------------------------------------------------------------------------
# Environment Variables
# -----------------------------------------------------------------------------
# VIRTUAL_ENV: Points to the virtualenv location
# PATH: Adds virtualenv's bin directory so Python can find installed packages
# PYTHONDONTWRITEBYTECODE: Prevents Python from creating .pyc files
# PYTHONUNBUFFERED: Ensures Python output is unbuffered (logs appear immediately)
# -----------------------------------------------------------------------------
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy the virtualenv from builder stage
# This includes all installed Python packages but NOT UV itself
COPY --from=builder /app/.venv /app/.venv

# Create a non-root user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

# Copy application code
COPY --chown=appuser:appgroup ./app /app/app

# Copy Alembic configuration and migrations
COPY --chown=appuser:appgroup ./alembic /app/alembic
COPY --chown=appuser:appgroup ./alembic.ini /app/alembic.ini

# Create uploads directory and set permissions
# This ensures appuser can write to it at runtime
RUN mkdir -p /app/uploads && \
    chown -R appuser:appgroup /app/uploads

# Switch to non-root user
USER appuser

# Expose port 8000 for the FastAPI application
EXPOSE 8000

# Run the FastAPI application using uvicorn in production mode
# Workers should be managed by the container orchestrator (e.g., K8s) or set via Gunicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
