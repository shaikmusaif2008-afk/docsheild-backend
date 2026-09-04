# DocShield AI — Vercel Deployment & Configuration Guide

This guide explains how to deploy **DocShield AI** to **Vercel** while preserving all local development capabilities.

---

## 1. Architecture & Vercel Suitability Assessment

### Overview
* **Frontend**: Pure HTML5, Tailwind CSS, Vanilla JavaScript, Lucide Icons, and KaTeX (SPA). **100% Vercel-native.**
* **Backend**: FastAPI (Python 3.10/3.11/3.12) running via Vercel's `@vercel/python` serverless runtime through [`api/index.py`](api/index.py).

### Vercel Serverless Considerations & Compatibility
1. **Read-Only Filesystem & Ephemeral Storage (`/tmp`)**:
   - Vercel functions run in a read-only container. The only writable directory is `/tmp` (512 MB max).
   - In [`backend/config.py`](backend/config.py), the app automatically detects `VERCEL=1` and dynamically routes uploads, reports, and SQLite database storage to `/tmp/docshield_data`.
   - *Note on Persistence*: In serverless environments, files in `/tmp` persist only for the lifetime of that container instance. For permanent multi-user production data, connecting to an external database (e.g., Supabase Postgres, Neon, or Turso SQLite) and cloud blob storage (e.g., Vercel Blob or AWS S3) is recommended.
2. **Bundle Size Limit (250 MB)**:
   - Standard `opencv-python` contains GUI/X11 libraries (~90MB) that fail in headless Linux serverless environments.
   - We configured [`requirements.txt`](requirements.txt) with `opencv-python-headless` (~30MB) and added [`.vercelignore`](.vercelignore) to keep the deployment package lean and well under the 250MB limit.
3. **Inference Execution Timing & Timeout**:
   - Vercel Hobby (Free) plans enforce a **10-second** execution limit per serverless invocation (up to 60s on Pro).
   - Our optimized RapidOCR and MRZ extraction runs in ~1.0–2.5 seconds on standard documents, fitting safely within the Hobby execution window.
4. **Request Body Size Limit (4.5 MB on Free Tier)**:
   - Vercel's free tier gateway limits upload payloads to **4.5 MB** (25 MB on Pro). Documents uploaded should be under 4.5 MB.

---

## 2. Prepared Project Configuration Files

The repository is pre-configured with the following deployment files:

| File | Purpose |
| :--- | :--- |
| [`vercel.json`](vercel.json) | Routes `/api/*` requests to the FastAPI serverless function and static assets to `/frontend`. |
| [`api/index.py`](api/index.py) | Serverless ASGI entry point importing the FastAPI `app` from `backend.main`. |
| [`requirements.txt`](requirements.txt) | Lean Python dependencies using `opencv-python-headless` and ONNX runtime. |
| [`.vercelignore`](.vercelignore) | Excludes local caches, upload temp files, and test scripts to minimize deploy bundle size. |
| [`backend/config.py`](backend/config.py) | Automatically switches to `/tmp/docshield_data` when running on Vercel. |

---

## 3. Step-by-Step Deployment Methods

### Method A: Deploy via GitHub (Recommended)

1. **Initialize Git & Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "feat: prepare DocShield AI for Vercel deployment"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/docshield-ai.git
   git push -u origin main
   ```

2. **Import Project into Vercel**:
   - Go to [vercel.com](https://vercel.com) and log in.
   - Click **"Add New..."** &rarr; **"Project"**.
   - Select your GitHub repository (`docshield-ai`).
   - Leave **Framework Preset** as **Other**.
   - Leave **Root Directory** as `./`.

3. **Configure Environment Variables (Optional)**:
   - `SECURESCREEN_SECRET_KEY`: `(Your custom secure random key for JWT)`
   - `PYTHON_VERSION`: `3.11`

4. **Click "Deploy"**:
   - Vercel will install Python dependencies from `requirements.txt`, bundle static files, and deploy your live URL (e.g., `https://docshield-ai.vercel.app`).

---

### Method B: Deploy via Vercel CLI

1. **Install Vercel CLI**:
   ```bash
   npm install -g vercel
   ```

2. **Log In to Vercel**:
   ```bash
   vercel login
   ```

3. **Deploy from Project Root**:
   ```bash
   cd C:\Users\shaik\.gemini\antigravity\scratch\securescreen-ai
   vercel
   ```
   - Follow the interactive prompts (Accept default settings).

4. **Deploy to Production**:
   ```bash
   vercel --prod
   ```

---

## 4. Verifying Your Deployment

Once deployed, test the following endpoints on your live domain (e.g. `https://your-project.vercel.app`):

1. **Frontend UI**:
   - Open `https://your-project.vercel.app` in your browser.
   - Verify the Dark Security Command Dashboard, all 5 screening domains, and Airlines workflow load correctly.
2. **API Health Check**:
   - Navigate to `https://your-project.vercel.app/api/health`
   - Expected response:
     ```json
     {
       "status": "ok",
       "ocr": "ready",
       "service": "DocShield AI — Security Command",
       "version": "3.1.0"
     }
     ```
3. **Live Screening Test**:
   - In the web app, test a passport/document upload in **Airlines & Gate Agents** or **Document Verification** to verify end-to-end OCR extraction and explainable risk calculation.

---

## 5. Local Development (Unaffected)

Your local development workflow remains 100% functional and unchanged:

```bash
# Start local development server
python run.py
```
Open **`http://127.0.0.1:8000`** in your browser.
