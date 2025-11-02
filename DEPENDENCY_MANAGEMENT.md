# Dependency Management Guide

This project uses **UV** for dependency management in both Docker and local development.

## Why UV?

UV is the dependency manager for this project because:
- 🚀 **10-100x faster** than traditional tools
- 🔥 **Modern** tool from Astral (makers of Ruff)
- ✅ **Consistent** - same tool in Docker and local dev
- 📦 **Great for Docker** - official installer, no pip needed
- ⚡ **Built-in virtual env management** - no extra setup required

## Setup UV

```bash
# Install UV (recommended method)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

## Using UV

### Install Dependencies

```bash
# Install dependencies from requirements.txt
uv pip install -r requirements.txt

# Or use pyproject.toml (if you migrate)
uv sync
```

### Add a New Dependency

```bash
# Add to requirements.txt manually, or:
uv add package-name

# Add a dev dependency
uv add --dev pytest
```

### Run Commands

```bash
# Run commands in the UV environment
uv run uvicorn app.main:app --reload
```

## Local Development with UV

### Option 1: Direct Install (Simplest)

```bash
# Install dependencies directly
uv pip install -r requirements.txt

# Run the app
uvicorn app.main:app --reload
```

### Option 2: Create Virtual Environment

```bash
# Create virtual environment
uv venv

# Activate it
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt

# Run the app
uvicorn app.main:app --reload
```

### Option 3: Use uv sync (Automatic Management)

```bash
# Sync dependencies (manages venv automatically)
uv sync

# Run the app
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Docker with UV

The `Dockerfile` uses UV automatically:

```bash
# Build and run
docker-compose up --build

# Or build separately
docker-compose build
docker-compose up
```

**What happens in Docker:**
1. UV installed via official installer (no pip)
2. Dependencies installed with `uv pip install --system -r requirements.txt`
3. 10-100x faster than traditional builds

## Project Configuration

### Docker
- **Dockerfile:** Uses UV official installer
- **File:** `requirements.txt`
- **Command:** `uv pip install --system -r requirements.txt`

### Local Development
- **Tool:** UV
- **File:** `requirements.txt`
- **Command:** `uv pip install -r requirements.txt`

## Migrate to pyproject.toml (Optional)

If you want to use `pyproject.toml` instead of `requirements.txt`:

```bash
# Initialize pyproject.toml
uv init

# Add dependencies
uv add fastapi uvicorn[standard] pydantic pydantic-settings

# Sync dependencies
uv sync
```

**Note:** Docker will continue to use `requirements.txt` unless you update the Dockerfile.

## Quick Start Commands

### Install and Run Locally

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv pip install -r requirements.txt

# Run the app
uv run uvicorn app.main:app --reload
```

### Docker

```bash
docker-compose up --build
```

## Summary

- 🐳 **Docker:** UV only (installed via official installer)
- 💻 **Local:** UV only
- 📦 **Files:** `requirements.txt` or `pyproject.toml`
- ⚡ **Speed:** UV is 10-100x faster than traditional tools

**UV is the only dependency manager used in this project!**
