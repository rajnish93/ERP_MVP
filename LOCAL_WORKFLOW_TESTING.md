# Local Workflow Testing Guide

This guide explains how to test our GitHub Actions workflows locally on your machine using [act](https://github.com/nektos/act).

## Prerequisites

1.  **Docker Desktop**: Must be installed and running.
2.  **Act**: The CLI tool to run GitHub Actions locally.

### Install `act` (macOS)
```bash
brew install act
```

## Running the Workflow

Because we are using **Apple Silicon (M1/M2/M3)** and newer Python versions (3.13), simply running `act push` is not enough. We must specify the correct Linux architecture and a modern Ubuntu image.

### The "Magic" Command 🪄

Run this command in your terminal:

```bash
act push -P ubuntu-latest=catthehacker/ubuntu:act-22.04 --container-architecture linux/amd64
```

### Explanation of Flags
*   **`-P ubuntu-latest=catthehacker/ubuntu:act-22.04`**:
    *   By default, `act` uses a "Micro" image (Debian Buster) which is too old and lacks modern libraries.
    *   This flag forces it to use a full Ubuntu 22.04 image, similar to the real GitHub Actions runner.
*   **`--container-architecture linux/amd64`**:
    *   Since GitHub Actions runners are Intel (AMD64) based, and your Mac is ARM64, we must tell Docker to emulate AMD64.
    *   Without this, steps like `setup-python` will fail to find ARM64 versions of tools.

## Troubleshooting Common Issues

### 1. `Bind for 0.0.0.0:5432 failed: port is already allocated`
**Cause**: You have a local Postgres server or another Docker container running on port 5432.
**Fix**: Stop your local services before running `act`.
```bash
# Verify what's running
docker ps
# Stop all containers (optional)
docker stop $(docker ps -a -q)
```

### 2. Deployment Step Failures
**Cause**: The workflow works, but the final "Deploy to Cloud Run" step fails.
**Reason**: `act` does not have access to your GitHub Repository Secrets (`GCP_SA_KEY`, etc.) by default.
**Fix**: This is expected!
*   If the **Test** job passes (`✅ Success - Main Install dependencies`, etc.), your code is good.
*   You can ignore the deployment failure locally unless you configure secrets using `act --secret-file my.secrets`.

### 3. `uv: command not found`
**Fix**: Ensure `deploy.yml` uses `pip install uv` instead of the curl script.
```yaml
- name: Install uv
  run: pip install uv
```

## Running Specific Jobs
To save time, you can run just the specific job (e.g., `test-and-deploy`) instead of the whole push event:

```bash
act -j test-and-deploy -P ubuntu-latest=catthehacker/ubuntu:act-22.04 --container-architecture linux/amd64
```
