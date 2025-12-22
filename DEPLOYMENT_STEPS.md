# Step-by-Step Deployment Guide: FastAPI on Google Cloud Run

This guide covers setting up your Google Cloud Platform (GCP) environment and configuring steps to deploy your FastAPI application.

## 1. Prerequisites (GCP Console)

Before deploying, you need to set up the infrastructure on Google Cloud.

1.  **Create a GCP Project**:
    *   Go to [Google Cloud Console](https://console.cloud.google.com/).
    *   Create a new project (e.g., `project-1`).
    *   Note your **Project ID**.

2.  **Enable Required APIs**:
    *   Open the "APIs & Services" > "Library".
    *   Enable the following APIs:
        *   **Cloud Run Admin API**
        *   **Artifact Registry API** (for storing Docker images)
        *   **IAM API** (for permissions)

3.  **Create Artifact Registry Repository**:
    *   Go to **Artifact Registry**.
    *   Click **Create Repository**.
    *   Name: `erp-images`
    *   Format: **Docker**
    *   Region: `asia-southeast1` (or your preferred region)
    *   Click **Create**.

## 2. Production Database Setup (Critical)

**Cloud Run is stateless**, meaning any files or databases inside the container are **deleted** when the container restarts. You CANNOT use a local `sqlite` or a `postgres` container running inside Cloud Run. You must connect to an external hosted database.

### Option A: Neon.tech (Recommended for Free Tier)
1.  Go to [Neon.tech](https://neon.tech) and sign up.
2.  Create a project (e.g., `project-1`).
3.  Copy the **Connection String** (e.g., `postgresql://user:pass@ep-xyz.aws.neon.tech/neondb?sslmode=require`).
4.  This is your `PROD_DATABASE_URL`.

### Option B: Google Cloud SQL (Robust but costs money)
1.  Go to **Cloud SQL** in GCP Console.
2.  Create a PostgreSQL instance.
3.  *Note: This costs ~$10-20/mo minimum unless using free tier specific configurations.*

## 3. Service Account Setup (For GitHub Actions)

To allow GitHub to deploy automatically, you need a Service Account.

1.  **Create Service Account**:
    *   Go to **IAM & Admin** > **Service Accounts**.
    *   Click **Create Service Account**.
    *   Name: `github-deployer`
    *   Click **Create and Continue**.

2.  **Grant Permissions**:
    *   Assign the following roles:
        *   **Cloud Run Admin** (to deploy services)
        *   **Service Account User** (to act as the compute identity)
        *   **Artifact Registry Writer** (to push images)
        *   **Storage Admin** (optional, sometimes needed for build logs)

3.  **Create Key**:
    *   Click on the newly created Service Account (`github-deployer@...`).
    *   Go to the **Keys** tab.
    *   Click **Add Key** > **Create new key**.
    *   Select **JSON**.
    *   **Save this file securely**. You will need it for GitHub Secrets.

## 4. GitHub Secrets Configuration

1.  Go to your GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions**.
2.  Add the following Repository Secrets:
    *   `GCP_PROJECT_ID`: Your Project ID (e.g., `project-1`).
    *   `GCP_SA_KEY`: The content of the JSON key file you just downloaded.
    *   `PROD_DATABASE_URL`: Your production database URL (e.g., from Neon, Supabase, or Cloud SQL).
    *   `PROD_SECRET_KEY`: A strong random string for security.

## 5. Manual Deployment (Testing Locally)

If you want to deploy *without* pushing to GitHub yet (and you have `gcloud` installed):

```bash
# 1. Login to Google Cloud
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 2. Configure Docker to use gcloud credentials
gcloud auth configure-docker asia-southeast1-docker.pkg.dev

# 3. Build the Image
docker build -t asia-southeast1-docker.pkg.dev/YOUR_PROJECT_ID/erp-images/backend:manual .

# 4. Push the Image
docker push asia-southeast1-docker.pkg.dev/YOUR_PROJECT_ID/erp-images/backend:manual

# 5. Deploy to Cloud Run
gcloud run deploy api-erp-mvp \
  --image asia-southeast1-docker.pkg.dev/YOUR_PROJECT_ID/erp-images/backend:manual \
  --region asia-southeast1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8000 \
  --set-env-vars DATABASE_URL="YOUR_DB_URL",SECRET_KEY="YOUR_key"
```

## 6. Verification

Once deployed, Cloud Run will give you a URL (e.g., `https://api-erp-mvp-xyz.a.run.app`).
Visit `https://api-erp-mvp-xyz.a.run.app/docs` to see your Swagger UI.
