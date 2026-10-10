# Production Deployment & Operations Guide

This guide covers production deployment options, host memory requirements, container orchestration, and automated scheduling for the **News Sentiment Analyzer**.

---

## 1. Hardware & Memory Footprint

The system architecture combines a rule-based lexicon with deep transformer neural networks. Memory consumption varies directly based on preloaded models:

| Component / Model | Parameter Count | Disk Size | Runtime RAM (CPU) |
| :--- | :--- | :--- | :--- |
| **VADER** | N/A (Lexicon) | < 1 MB | **~15 MB** |
| **RoBERTa-Sentiment** (`cardiffnlp/twitter-roberta-base-sentiment-latest`) | 125M | ~500 MB | **~550 MB** |
| **FinBERT** (`ProsusAI/finbert`) | 110M | ~440 MB | **~500 MB** |
| **Fine-Tuned DistilRoBERTa** (`distilbert/distilroberta-base`) | 82M | ~330 MB | **~380 MB** |
| **All Models Preloaded (Default)** | ~317M | ~1.3 GB | **~1.6 GB** |

> [!IMPORTANT]
> **Memory-Tight Hosting Policy**:
> If deploying to a host with ≤ 1 GB RAM (such as Render's free 512 MB tier), do not preload all transformer checkpoints simultaneously. Restrict active models by setting:
> ```bash
> ACTIVE_MODELS='["vader"]'
> ```
> This prevents Out-Of-Memory (OOM) process termination while maintaining full API responsiveness.

---

## 2. Recommended Hosting Targets

### A. Backend on Hugging Face Spaces (Recommended: 16 GB RAM Free)
Hugging Face Spaces provides **16 GB RAM and 2 vCPUs** on its free "CPU Basic" tier, making it the ideal host for running multi-model transformer inference without memory constraints.

1. Create a new Space on [huggingface.co/spaces](https://huggingface.co/spaces).
2. Select **Docker** as the Space SDK and choose **Blank** template.
3. Push the repository to the Space Git remote:
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/<your-space-name>
   git push space main
   ```
4. Configure Space repository secrets under **Settings > Variables and secrets**:
   - `ENVIRONMENT=production`
   - `LOG_FORMAT=json`
   - `CORS_ORIGINS=["https://<your-frontend-domain>.vercel.app"]`
   - `CRON_API_KEY=<secure-random-token>`

### B. Backend on Render (Free Tier: 512 MB RAM)
If deploying to Render Web Services:
1. Connect repository and select **Docker** runtime.
2. Set environment variables:
   - `ENVIRONMENT=production`
   - `ACTIVE_MODELS=["vader"]`  *(Memory constrained)*
   - `DATABASE_URL=sqlite:////app/data/news_sentiment.db`
   - `CRON_API_KEY=<secure-random-token>`
3. Attach a persistent disk (`/app/data`) so news headlines survive dyno restarts.

### C. Frontend Dashboard on Vercel or Netlify
The React SPA in `frontend/` compiles to static HTML/JS/CSS assets.

#### Deploying to Vercel:
1. Import repository on [vercel.com](https://vercel.com).
2. Set **Root Directory** to `frontend`.
3. Set **Build Command** to `npm run build` and **Output Directory** to `dist`.
4. Configure Environment Variables:
   - `VITE_API_BASE_URL=https://<your-backend-domain>`
5. Add `frontend/vercel.json` for SPA route rewriting:
   ```json
   {
     "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
   }
   ```

#### Deploying to Netlify:
1. Import repository on [netlify.com](https://netlify.com) with base directory `frontend`.
2. Add a `frontend/public/_redirects` file containing:
   ```text
   /*    /index.html   200
   ```

---

## 3. Local Stack Orchestration (Docker Compose)

Run the complete isolated production stack (FastAPI backend + Nginx React frontend + persistent SQLite volume) locally:

```bash
# Clone the repository
git clone https://github.com/Dhrupal-01/Sentiment-Analyzer.git
cd Sentiment-Analyzer

# Build images and start all services
docker compose up -d

# Verify container status
docker compose ps

# Access services:
# - Frontend Dashboard: http://localhost:3000
# - Backend OpenAPI Docs: http://localhost:8000/docs
# - Backend Health Beacon: http://localhost:8000/api/v1/health

# Stop the stack
docker compose down
```

---

## 4. Scheduled Daily Ingestion & Inference

The system provides two automated execution mechanisms:

### Option 1: GitHub Actions Daily Cron Workflow
The workflow at `.github/workflows/scheduled_collection.yml` runs every day at 06:00 UTC. Configure GitHub Repository Secrets (`Settings > Secrets and variables > Actions`):
- `API_BASE_URL`: URL of the deployed backend (e.g. `https://<space-name>.hf.space`)
- `CRON_API_KEY`: Matching secret configured in backend's `CRON_API_KEY`

When configured, the workflow sends a secure `POST /api/v1/jobs/collect-and-analyze` request to ingest headlines and run model inference.

### Option 2: Host Schedulers (Crontab / Systemd)
On self-hosted instances, schedule `scripts/scheduled_collection.sh` via crontab:
```bash
# Edit crontab
crontab -e

# Run every day at 06:00 UTC
0 6 * * * /path/to/Sentiment-Analyzer/scripts/scheduled_collection.sh >> /var/log/newsent-cron.log 2>&1
```
