# Quick Start Guide

## TL;DR

**Docker:** Uses UV exclusively  
**Local Dev:** Use UV exclusively

---

## Docker (UV Only)

The project uses UV in Docker automatically:

```bash
# Build and run
docker-compose up --build

# Access the app
# API: http://localhost
# Docs: http://localhost/api/v1/docs
```

**What happens:**
- UV installed via official installer (no pip)
- Dependencies installed with UV (10-100x faster)
- FastAPI app starts on port 8000

---

## Local Development (UV Only)

### Install UV

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

### Install Dependencies and Run

```bash
# Install dependencies
uv pip install -r requirements.txt

# Run the app
uv run uvicorn app.main:app --reload
```

### Alternative: Use Virtual Environment

```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt

# Run the app
uvicorn app.main:app --reload
```

---

## Why UV?

- ⚡ **10-100x faster** than traditional tools
- 🔥 **Modern** and actively maintained
- ✅ **Consistent** - same tool in Docker and local
- 📦 **Simple** - works with your existing `requirements.txt`

---

## Complete Workflow

```bash
# 1. Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies
uv pip install -r requirements.txt

# 3. Run locally
uv run uvicorn app.main:app --reload

# Or use Docker (also uses UV)
docker-compose up --build
```

That's it! No other tools needed - UV handles everything.
