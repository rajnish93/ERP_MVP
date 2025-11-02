# Docker Dependency Management Guide

## How It Works

When you run `docker-compose up --build`, Docker:

1. **Builds the image** using the `Dockerfile`
2. **Runs commands INSIDE the container** during build (all `RUN` commands)
3. **Installs UV** using the official standalone installer (no pip needed)
4. **Installs dependencies** using UV (10-100x faster than traditional tools)
5. **Starts the container** and runs your FastAPI app

## Current Setup

**Dockerfile:**
- Uses UV's official installer (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Installs dependencies with `uv pip install --system -r requirements.txt`
- No pip usage - UV handles everything

**What happens when you run `docker-compose up --build`:**
```
Step 1: Base Python 3.13 image
Step 2: Install curl (for UV installer)
Step 3: Install UV via official installer  ← No pip!
Step 4: Copy requirements.txt
Step 5: RUN uv pip install --system -r requirements.txt  ← Happens INSIDE Docker (10-100x faster)
Step 6: Copy app code
Step 7: Start uvicorn server
```

## Why UV?

**Benefits:**
- ✅ **10-100x faster** dependency resolution
- ✅ **No pip needed** - UV installed via official installer
- ✅ **Smaller Docker image** - UV is lightweight
- ✅ **Faster CI/CD builds** - significantly reduced build times
- ✅ **Works with requirements.txt** - no migration needed

## What Runs Inside Docker

| Step | Command | Purpose |
|------|---------|---------|
| **Install UV** | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | Install UV standalone binary |
| **Install Dependencies** | `uv pip install --system -r requirements.txt` | Install packages with UV (super fast) |

**Note:** `uv pip` is UV's pip-compatible command interface - it's not actual pip!

## Local Development vs Docker

| Environment | Dependency Manager | File Used |
|-------------|-------------------|-----------|
| **Local Dev** | UV | `requirements.txt` or `pyproject.toml` |
| **Docker** | UV | `requirements.txt` |

**Current Setup:**
- **Docker:** Uses UV exclusively via `Dockerfile`
- **Local:** Uses UV exclusively
- **Consistent:** Same tool everywhere for a seamless experience

### Local Development Setup

```bash
# Install UV locally
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv pip install -r requirements.txt

# Run the app
uv run uvicorn app.main:app --reload
```

This gives you the same fast experience locally as in Docker.

## Troubleshooting

### Docker build fails or is slow

```bash
# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Dependencies not found in container

```bash
# Make sure requirements.txt is up to date
# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### UV installation fails in Docker

```bash
# Check network connectivity
docker-compose build --progress=plain

# Verify curl is available
docker run --rm python:3.13-slim curl --version
```

### Health check fails

The health check uses Python's built-in `urllib` (no curl needed). If it fails:
- Check if the app is running: `docker-compose logs app`
- Verify port 8000 is accessible inside container

## Verification

To verify UV is being used, check the build logs:

```bash
docker-compose build
```

You should see:
```
Step 5/8 : RUN curl -LsSf https://astral.sh/uv/install.sh | sh
Step 7/8 : RUN uv pip install --system -r requirements.txt
```

## Summary

- ✅ **Docker:** Uses UV exclusively (installed via official installer, no pip)
- ✅ **Local:** Uses UV exclusively
- ✅ **Fast builds:** 10-100x faster than traditional tools
- ✅ **Simple:** Single Dockerfile, UV-only workflow
- ✅ **Modern:** Latest Python 3.13 with latest stable dependencies
- ✅ **Consistent:** Same tool everywhere

**Just run `docker-compose up --build` - UV handles everything!**
