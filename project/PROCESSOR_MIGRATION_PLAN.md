# Processor Migration Plan — Playwright + OpenCV

Goal: Replace the current simulated `process-run` implementation with a production-capable processor that captures live UI screenshots, performs pixel/structural diffs with OpenCV, and provides AI-assisted analysis for human-readable change descriptions.

Scope
- Capture screenshots (web apps) using Playwright.
- Store screenshots in Supabase Storage.
- Use OpenCV (Python or Node) to compute diffs, bounding boxes, and similarity scores.
- Generate change severity and descriptions; optionally call an LLM for natural-language analysis.
- Insert comparison and change detail rows into Postgres (Supabase) and mark the run lifecycle.
- Run the processor as a server-side worker (not client-side) to keep service-role privileges safe.

Architecture Options
1. Edge Function (Deno) orchestrator + Background Worker
   - Keep a small edge function to accept a `runId` request and enqueue a job (e.g., using a queue table in Postgres).
   - A separate worker (container/VM or serverless job) picks up queued runs and executes Playwright + OpenCV (recommended for heavy processing).

2. Self-contained Edge Function
   - Implement Playwright + OpenCV directly within an edge function. This is possible but limited by runtime constraints and binary availability (less flexible).

Recommendation: Use an external worker (container) for Playwright + OpenCV; keep edge function as lightweight trigger/enqueuer.

Components & Responsibilities
- Trigger (Edge Function)
  - Accepts `POST { runId }`.
  - Validates run exists and is `pending`.
  - Updates run `status` to `processing` (service-role key required).
  - Enqueues job (insert into `processing_queue` table) or calls worker webhook.

- Worker (Container / Serverless Job)
  - Environment: Node.js or Python container with Playwright and OpenCV available.
  - Steps:
    1. Mark run as `processing` (if not already).
    2. Load project config (tolerance, capture config) from `projects` row.
    3. For each documentation image path:
       - Determine live URL / way to capture (project.app_url or executable metadata).
       - Use Playwright to navigate and capture a screenshot matching documentation viewport.
       - Upload live screenshot to Supabase Storage with a predictable path (e.g., `runs/{runId}/live/{image}`) and obtain `live_image_url`.
       - Retrieve document image (from docs storage) and download locally.
       - Run OpenCV comparison:
         - Compute global similarity (e.g., SSIM) and bounding boxes for changed regions.
         - Compute per-region metrics (area, centroid, bounding box).
       - Classify change type heuristically (layout, visual, content) based on detected deltas.
       - Assign severity using thresholds and heuristics (e.g., large area change -> major/critical).
       - Insert a `comparisons` row and `change_details` rows for each detected region.
    4. Update `runs` row with `completed_at`, `total_images`, `changes_detected`.
    5. Optionally call an LLM (secure server-side API key) sending cropped regions + metadata to produce a natural language description and recommendation. Store `ai_analysis` in `change_details`.

- Storage
  - Use Supabase Storage buckets for both `doc_images` and `live_screenshots`.
  - Set lifecycle and access rules; only store signed URLs in DB records if necessary.

- Security
  - All DB writes that require elevated permissions must use the Supabase Service Role Key (worker or edge function with service role).
  - Do not expose service role keys to the browser.
  - Use RLS and `processing_queue` ownership checks as needed.

Implementation Details
- Playwright (Node)
  - Install `playwright` and browsers in container.
  - Use headless mode; configure viewport and device emulation from project `capture_config`.
  - Use repeatable screenshot naming and deterministic timing (waitForNetworkIdle / specific selectors).

- OpenCV
  Option A — Python worker
    - Use `opencv-python` and `scikit-image` for SSIM.
    - Benefit: Mature OpenCV bindings and ecosystem for advanced analysis.
  Option B — Node worker
    - Use `opencv4nodejs` or `@u4/opencv4nodejs` (may be harder to install, requires native builds).

  Recommendation: Use a Python worker (Docker container) for OpenCV analysis, and expose a small HTTP API the orchestrator can call. Playwright can be called from Node or via Python Playwright bindings; choose the language you prefer for orchestration.

- LLM Integration
  - Prepare a concise prompt template that includes:
    - `change_type`, `severity`, cropped image(s) (or links), numeric metrics, and suggested action.
  - Use a server-side LLM API key and only send necessary information (avoid sending whole images if not needed; use base64 or signed storage URLs with short TTL).

- Observability
  - Log each step with runId context.
  - Emit metrics for processing time, images processed, errors, and LLM confidence.

- Deployment
  - Build a Docker image for the worker with Playwright and OpenCV installed.
  - Deploy the worker to a container service (e.g., Fly, DigitalOcean App Platform, AWS ECS/Fargate) or use a serverless container provider.
  - Keep the edge function as the public trigger (it enqueues jobs or calls the worker webhook).

Milestones & Tasks
1. Prototype Playwright capture for one sample project (1–2 days).
2. Prototype OpenCV SSIM/contour diff and produce comparison numbers (1–2 days).
3. Create a small end-to-end worker that: captures, compares, writes `comparisons` and `change_details` (2–3 days).
4. Integrate optional LLM analysis and store `ai_analysis` (1–2 days).
5. Add robust error handling, retries, and observability (1–2 days).
6. Replace simulated `process-run` with orchestrator + worker in production config; update docs (1 day).

Quick Dev Notes
- Use a `processing_queue` DB table to keep retries and status visible.
- Use short-lived signed URLs for image transfer to LLMs if sending images.
- Tune OpenCV thresholds using real sample images from your documentation.

Example tools / libs
- Playwright (Node): `playwright`
- Playwright (Python): `playwright`
- OpenCV Python: `opencv-python`, `scikit-image`
- Containerize: `Dockerfile` with Playwright browsers and Python deps
- Job runner: simple loop worker or use a job queue (BullMQ / Redis) if needed

Estimated Effort: ~1.5–2 weeks to reach a reliable MVP (captures, diffs, DB writes, LLM analysis optional).


If you want, I can now:
- Add a lightweight `processing_queue` table + trigger in the DB migration and an edge function that enqueues jobs;
- Create a sample Dockerfile and small Python worker sketch for Playwright+OpenCV;
- Or implement the minimal client-side trigger (already added) and test end-to-end with the current simulated function.
