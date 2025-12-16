Python Worker — Playwright + OpenCV prototype

Purpose
- This worker processes `runs` created by the frontend and produces real `comparisons` and `change_details` rows.

Requirements
- Docker (recommended) or Python 3.11+ for local run
- Environment variables (put in `.env` or provide as container env):
  - `SUPABASE_URL` (e.g. https://<project>.supabase.co)
  - `SUPABASE_SERVICE_ROLE_KEY` (service role key — required to write DB & upload storage)
  - `DOCS_BUCKET_NAME` (optional, defaults to `doc_images`)
  - `LIVE_BUCKET_NAME` (optional, defaults to `live_screenshots`)

Quick local run (without Docker)
1. Create a virtualenv and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install
```

2. Export env vars (PowerShell example):

```powershell
$env:SUPABASE_URL = 'https://your.supabase.co'
$env:SUPABASE_SERVICE_ROLE_KEY = 'your-service-role-key'
```

3. Run the worker for a specific run:

```powershell
python process_run.py --run-id <uuid>
```

Quick Docker run

```powershell
# build
docker build -t docupdater-worker:latest .

# run (pass env vars)
docker run --rm -e SUPABASE_URL="https://your.supabase.co" -e SUPABASE_SERVICE_ROLE_KEY="<service-role>" docupdater-worker:latest python process_run.py --run-id <uuid>
```

Notes & Limitations
- This is a prototype: it handles basic web captures and SSIM-based comparison. It doesn't yet support desktop apps or sophisticated ML-based change detection.
- The script expects `documents` rows in the DB or doc images in the `DOCS_BUCKET_NAME` storage bucket. If none are found, it uses a placeholder sample.
- For production, run this worker behind a job queue; don't expose service role keys in the browser.

Next Improvements
- Add queue record and ack/retry logic
- Add LLM analysis step (use the provided LLM API key in a secure server env)
- Add better image alignment and multi-resolution matching, or OCR-based content comparison
- Add metrics/log aggregation and structured errors
