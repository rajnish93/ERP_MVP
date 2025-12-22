# Deployment Strategy & Architecture

## 1. Selected Architecture: Serverless Reverse Proxy
We have chosen a **Google Cloud Platform (GCP) Cloud Run** architecture. This provides a "Serverless" environment where Google manages the underlying infrastructure.

### The Flow
1.  **User** visits `https://erp-mvp.run.app` (Frontend).
2.  **Frontend** (Next.js) serves the UI.
3.  **Frontend** calls API at `https://api-erp-mvp.run.app` (Backend).
4.  **Backend** (FastAPI) processes request -> Connects to Database.

## 2. Why this choice? (Cost & Scale)
-   **Scale to Zero**: Cloud Run scales down to 0 instances when idle. **Cost = $0.00** during nights/weekends or when not used.
-   **Free Tier**: GCP offers 2 million requests/month for free.
-   **No Maintenance**: No OS patches, no Nginx configuration, no SSL certificate management. Google handles HTTPS automatically.

## 3. Multi-Repository Workflow
We adhere to the **"Decoupled Build, Unified Deploy"** philosophy.

### Repo A: Frontend (`ERP_MVP_FE`)
-   **Trigger**: Push to `main`.
-   **Action**: Builds Next.js Docker Image.
-   **Output**: Pushes image to Google Artifact Registry.
-   **Deploy**: Updates `frontend` Cloud Run service.

### Repo B: Backend (`ERP_MVP`)
-   **Trigger**: Push to `main`.
-   **Action**: Runs Tests (`e2e_test.py`) -> Builds FastAPI Docker Image.
-   **Output**: Pushes image to Google Artifact Registry.
-   **Deploy**: Updates `backend` Cloud Run service.

## 4. Security & Access Control
To prevent unexpected costs from public access during the demo phase:

### Recommendation: Private (IAM Auth)
-   **Setting**: "Require Authentication" on Cloud Run.
-   **Access**: Only users with IAM permissions (e.g., your Google Account) can access the URL.
-   **Benefit**: secure from botnets and public scraping. **Zero unexpected costs.**

#### How to Invite Users
To give a client or colleague access to the private app:
1.  Go to **Google Cloud Console** -> **Cloud Run**.
2.  Click on the service name (e.g., `erp-frontend`).
3.  Go to the **Permissions** tab.
4.  Click **Add Principal**.
5.  Enter their Google Email (e.g., `client@gmail.com`).
6.  Select Role: **Cloud Run Invoker**.
7.  Click **Save**. They can now access the URL by signing in.

### Alternative: Public with Safety Nets
-   **Max Instances**: Cap at `1` instance.
-   **Budget Alert**: Set at `$1.00`.

## 5. Prerequisities
1.  **GCP Project**: Created in Google Cloud Console.
2.  **Artifact Registry**: A Docker repository named `erp-images` (or similar).
3.  **Service Account**: A JSON key for GitHub Actions to authenticate (`GCP_SA_KEY` secret).
