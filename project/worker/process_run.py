#!/usr/bin/env python3
"""
Worker: process_run.py
- Polls Supabase `runs` table for `pending` runs (or take `--run-id` argument)
- Uses Playwright to capture a live screenshot of the project's URL
- Compares a documentation image (from Supabase Storage `doc_images` or `docs` bucket)
  with the live screenshot using SSIM (skimage) and OpenCV utilities
- Uploads live screenshot to Supabase Storage `live_screenshots` and inserts `comparisons` and
  `change_details` rows using the Supabase service role key

Notes:
- Requires env vars in `.env` or system env:
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY  # required for inserts/uploads
  DOCS_BUCKET_NAME (optional, defaults to 'doc_images')
  LIVE_BUCKET_NAME (optional, defaults to 'live_screenshots')

Run: python process_run.py --run-id <uuid>
Or run without args to poll once and process the first pending run.
"""

import os
import io
import sys
import time
import argparse
import tempfile
import traceback
from dotenv import load_dotenv
from supabase import create_client
import requests
import numpy as np
import cv2
from playwright.sync_api import sync_playwright
import google.generativeai as genai

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
DOCS_BUCKET = os.getenv('DOCS_BUCKET_NAME', 'doc_images')
LIVE_BUCKET = os.getenv('LIVE_BUCKET_NAME', 'live_screenshots')
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '5'))
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print('Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in environment', file=sys.stderr)
    sys.exit(1)

if not GEMINI_API_KEY:
    print('Missing GEMINI_API_KEY in environment', file=sys.stderr)
    # Optionally, exit or proceed without Gemini features
    # For now, we will proceed but log a warning
    print('[WARNING] GEMINI_API_KEY is missing. AI analysis will be skipped.', file=sys.stderr)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    # Configure Gemini API
gemini_model = None
if GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            # Use 'gemini-pro' as a more general model, 'gemini-pro-vision' might be regional or specific
            gemini_model = genai.GenerativeModel('gemini-pro') 
            print("[DEBUG] Gemini model 'gemini-pro' initialized successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to initialize Gemini model 'gemini-pro': {e}", file=sys.stderr)
            gemini_model = None


def download_storage_file(bucket: str, path: str) -> bytes | None:
    print(f"[DEBUG] Attempting to download '{path}' from bucket '{bucket}'")
    try:
        # Use storage public or signed URL API
        res = supabase.storage.from_(bucket).download(path)
        if res:  # returns a Response-like object
            print(f"[DEBUG] Download response for '{path}': {res}")
            return res
        print(f"[DEBUG] No direct download response for '{path}'")
    except Exception as e:
        print(f"[ERROR] Error during direct download for '{path}': {e}", file=sys.stderr)
        # fallback to REST download via public url (if public) or signed url - try get_public_url
        try:
            print(f"[DEBUG] Attempting fallback public URL download for '{path}'")
            url_data = supabase.storage.from_(bucket).get_public_url(path)
            public_url = url_data.get('publicUrl') if isinstance(url_data, dict) else url_data # Handle both dict and direct string return
            if public_url:
                print(f"[DEBUG] Public URL for '{path}': {public_url}")
                r = requests.get(public_url)
                if r.status_code == 200:
                    print(f"[DEBUG] Successfully downloaded '{path}' via public URL.")
                    return r.content
                else:
                    print(f"[ERROR] Public URL download for '{path}' failed with status {r.status_code}", file=sys.stderr)
            else:
                print(f"[DEBUG] No public URL found for '{path}'")
        except Exception as e:
            print(f"[ERROR] Error during fallback public URL download for '{path}': {e}", file=sys.stderr)
    return None


def upload_live_screenshot(bucket: str, dest_path: str, data: bytes) -> str | None:
    print(f"[DEBUG] Attempting to upload screenshot to '{bucket}/{dest_path}'")
    try:
        upload_res = supabase.storage.from_(bucket).upload(dest_path, data, {'content-type': 'image/png'})
        print(f"[DEBUG] Supabase upload response: {upload_res}")
        # Check for specific error structure from supabase-py
        if isinstance(upload_res, dict) and 'error' in upload_res:
            print(f"[ERROR] Supabase upload error response: {upload_res.get('error')}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"[ERROR] Exception during screenshot upload: {e}", file=sys.stderr)
        # Further attempt to parse supabase-py specific errors if they wrap in an exception
        if hasattr(e, '__dict__') and 'json' in e.__dict__:
            try:
                error_json = e.__dict__['json']
                print(f"[ERROR] Supabase client exception details: {error_json}", file=sys.stderr)
            except Exception:
                pass
        return None

    # Get public URL
    print(f"[DEBUG] Attempting to get public URL for '{bucket}/{dest_path}'")
    try:
        url_data = supabase.storage.from_(bucket).get_public_url(dest_path)
        print(f"[DEBUG] Public URL data: {url_data}")
        public_url = url_data.get('publicUrl') if isinstance(url_data, dict) else url_data # Handle both dict and direct string return
        if public_url:
            print(f"[DEBUG] Successfully got public URL: {public_url}")
            return public_url
        else:
            print(f"[ERROR] Public URL not found in response: {url_data}", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] Exception getting public URL: {e}", file=sys.stderr)
    return None


def _bytes_to_rgb_array(img_bytes: bytes):
    # Decode image bytes to OpenCV BGR array then convert to RGB
    arr = np.frombuffer(img_bytes, np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError('Could not decode image bytes')
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return rgb


def compute_ssim_and_diff(img1_bytes: bytes, img2_bytes: bytes):
    """
    Compute SSIM between two images (bytes) using OpenCV and return
    (similarity_percent, regions, diff_image_bytes)
    """
    img1_arr = _bytes_to_rgb_array(img1_bytes)
    img2_arr = _bytes_to_rgb_array(img2_bytes)

    # Resize to smallest common size
    h1, w1 = img1_arr.shape[:2]
    h2, w2 = img2_arr.shape[:2]
    w = min(w1, w2)
    h = min(h1, h2)
    img1_resized = cv2.resize(img1_arr, (w, h), interpolation=cv2.INTER_AREA)
    img2_resized = cv2.resize(img2_arr, (w, h), interpolation=cv2.INTER_AREA)

    # Convert to grayscale
    gray1 = cv2.cvtColor(img1_resized, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gray2 = cv2.cvtColor(img2_resized, cv2.COLOR_RGB2GRAY).astype(np.float32)

    # --- SSIM implementation (from standard formula) ---
    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2

    # Gaussian kernel for mean and variance
    kernel = (11, 11)
    sigma = 1.5

    mu1 = cv2.GaussianBlur(gray1, kernel, sigma)
    mu2 = cv2.GaussianBlur(gray2, kernel, sigma)

    mu1_sq = mu1 * mu1
    mu2_sq = mu2 * mu2
    mu1_mu2 = mu1 * mu2

    sigma1_sq = cv2.GaussianBlur(gray1 * gray1, kernel, sigma) - mu1_sq
    sigma2_sq = cv2.GaussianBlur(gray2 * gray2, kernel, sigma) - mu2_sq
    sigma12 = cv2.GaussianBlur(gray1 * gray2, kernel, sigma) - mu1_mu2

    # SSIM map
    num = (2 * mu1_mu2 + C1) * (2 * sigma12 + C2)
    den = (mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2)
    ssim_map = np.divide(num, den, out=np.zeros_like(num), where=den != 0)

    score = float(np.mean(ssim_map))

    # produce diff image (normalize 0..255)
    diff = (1.0 - ssim_map)  # higher where different
    diff_norm = (np.clip(diff, 0.0, 1.0) * 255.0).astype('uint8')

    # threshold diff to get contours
    _, thresh = cv2.threshold(diff_norm, 30, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    for cnt in contours:
        x, y, wbox, hbox = cv2.boundingRect(cnt)
        area = wbox * hbox
        if area < 50:
            continue
        regions.append({'x': int(x), 'y': int(y), 'width': int(wbox), 'height': int(hbox), 'area': int(area)})

    # encode diff image to PNG bytes for optional use
    diff_bgr = cv2.cvtColor(diff_norm, cv2.COLOR_GRAY2BGR)
    is_success, buffer = cv2.imencode('.png', diff_bgr)
    diff_bytes = buffer.tobytes() if is_success else None

    similarity_percent = float(score) * 100.0
    return similarity_percent, regions, diff_bytes


def process_run_id(run_id: str):
    try:
        # fetch run with project
        r = supabase.table('runs').select('*, projects(*)').eq('id', run_id).maybe_single().execute()
        if not r.data:
            print('Run not found', run_id)
            return
        run = r.data

        project = run.get('projects')
        project_id = run.get('project_id')
        tolerance = project.get('comparison_tolerance') if project else 98.0
        app_url = project.get('app_url') if project else None
        print(f"[DEBUG] Retrieved app_url for project: {app_url}")

        # mark processing
        supabase.table('runs').update({'status': 'processing'}).eq('id', run_id).execute()

        # find doc images for this project: look into `documents` table first
        docs_res = supabase.table('documents').select('*').eq('project_id', project_id).execute()
        doc_images = []
        if docs_res.data:
            for d in docs_res.data:
                if d.get('storage_url'):
                    doc_images.append({'path': d.get('file_path'), 'url': d.get('storage_url')})
                else:
                    doc_images.append({'path': d.get('file_path'), 'url': None})

        # If no documents, try listing bucket 'docs' or DOCS_BUCKET
        if not doc_images:
            try:
                items = supabase.storage.from_(DOCS_BUCKET).list('', {'limit': 100})
                if items:
                    for item in items:
                        doc_images.append({'path': (item.get('name') or item.get('path') or item['name']), 'url': None})
            except Exception:
                pass

        # fallback sample
        if not doc_images:
            print('No doc images found, using sample placeholders')
            doc_images = [{'path': 'screenshots/login-page.png', 'url': None}]

        total_images = 0
        changes_detected = 0

        print(f"[DEBUG] Project app_url: {app_url}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1280, 'height': 720})

            try:
                for doc in doc_images:
                    total_images += 1
                    filename = os.path.basename(doc['path'])

                    # Capture live screenshot for project.app_url
                    if app_url:
                        try:
                            page.goto(app_url, wait_until='networkidle', timeout=30000)
                            time.sleep(1)
                            screenshot_bytes = page.screenshot(full_page=True)
                            print(f"[DEBUG] Playwright captured screenshot. Size: {len(screenshot_bytes) if screenshot_bytes else 0} bytes.")
                            if not screenshot_bytes:
                                print("[ERROR] Playwright returned empty screenshot bytes.", file=sys.stderr)
                        except Exception as e:
                            print('Playwright navigation failed or screenshot error:', e, file=sys.stderr)
                            screenshot_bytes = None
                    else:
                        print("[DEBUG] No app_url specified, skipping live screenshot capture.")
                        screenshot_bytes = None

                    # Download doc image from storage if possible
                    doc_bytes = None
                    if doc.get('url'):
                        try:
                            print(f"[DEBUG] Attempting to download doc image from URL: {doc.get('url')}")
                            r = requests.get(doc.get('url'))
                            if r.status_code == 200:
                                doc_bytes = r.content
                                print(f"[DEBUG] Downloaded doc image from URL. Size: {len(doc_bytes)} bytes.")
                            else:
                                print(f"[ERROR] Failed to download doc image from URL {doc.get('url')}. Status: {r.status_code}", file=sys.stderr)
                        except Exception as e:
                            print(f"[ERROR] Exception downloading doc image from URL: {e}", file=sys.stderr)
                    else:
                        # try download via bucket
                        try:
                            print(f"[DEBUG] Attempting to download doc image from bucket '{DOCS_BUCKET}', path '{doc['path']}'")
                            maybe = download_storage_file(DOCS_BUCKET, doc['path'])
                            if maybe:
                                if isinstance(maybe, bytes):
                                    doc_bytes = maybe
                                    print(f"[DEBUG] Downloaded doc image from bucket. Size: {len(doc_bytes)} bytes.")
                                else:
                                    # supabase-py returns a Response-like object sometimes
                                    # Assuming this response object contains the bytes
                                    doc_bytes = maybe.content # Access content from the response-like object
                                    print(f"[DEBUG] Downloaded doc image from bucket (response object). Size: {len(doc_bytes)} bytes.")
                            else:
                                print(f"[ERROR] Failed to download doc image from bucket '{DOCS_BUCKET}', path '{doc['path']}'. No data returned.", file=sys.stderr)
                        except Exception as e:
                            print(f"[ERROR] Exception downloading doc image from bucket: {e}", file=sys.stderr)

                    # If no doc image, skip comparison and just upload live screenshot
                    if not doc_bytes:
                        print("[WARNING] No documentation image found for comparison.", file=sys.stderr)

                    live_path = f'runs/{run_id}/live/{filename}'
                    live_url = None
                    if screenshot_bytes:
                        live_url = upload_live_screenshot(LIVE_BUCKET, live_path, screenshot_bytes)
                        print(f"[DEBUG] Uploaded live screenshot. Returned URL: {live_url}")
                    else:
                        print("[WARNING] No live screenshot bytes available for upload.", file=sys.stderr)

                    similarity = None
                    regions = []
                    status = 'error' # Default to error if comparison fails or images are missing

                    print(f"[DEBUG] Before comparison: doc_bytes {'present' if doc_bytes else 'MISSING'}, screenshot_bytes {'present' if screenshot_bytes else 'MISSING'}")

                    if doc_bytes and screenshot_bytes:
                        try:
                            similarity, regions, diff = compute_ssim_and_diff(doc_bytes, screenshot_bytes)
                            status = 'matched' if similarity >= float(tolerance) else 'changed'
                            if status == 'changed':
                                changes_detected += 1
                            print(f"[DEBUG] Comparison completed. Similarity: {similarity:.2f}%, Status: {status}, Changes: {len(regions)} regions.")
                        except Exception as e:
                            print(f'[ERROR] Error computing diff: {e}', file=sys.stderr)
                            similarity = None
                            status = 'error'
                    else:
                        print("[ERROR] Skipping comparison due to missing documentation or live screenshot.", file=sys.stderr)
                        status = 'error'

                    # Insert comparison
                    print(f"[DEBUG] Inserting comparison for doc_path: {doc['path']}, live_path: {live_path}, live_url: {live_url}, status: {status}")
                    comp_insert = {
                        'run_id': run_id,
                        'doc_image_path': doc['path'],
                        'doc_image_url': doc.get('url'),
                        'live_image_path': live_path,
                        'live_image_url': live_url,
                        'similarity_score': float(similarity) if similarity is not None else None,
                        'status': status,
                        'change_severity': 'major' if similarity is not None and similarity < 90 else ('minor' if similarity is not None and similarity < tolerance else None),
                        'processed_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    }

                    comp_res = supabase.table('comparisons').insert(comp_insert).execute()
                    # supabase-py v2 returns data as list for inserts
                    if isinstance(comp_res.data, list):
                        comp_row = comp_res.data[0] if comp_res.data else None
                    else:
                        comp_row = comp_res.data if comp_res.data else None

                    if status == 'changed' and comp_row:
                        # insert change_details for each region
                        for reg in regions:
                            desc = f'Detected change in region area {reg.get("area")}'
                            gemini_analysis_text = "No AI analysis performed."
                            if gemini_model and doc_bytes and screenshot_bytes:
                                try:
                                    print(f"[DEBUG] Sending images to Gemini for region: {reg}")
                                    # Prepare images for Gemini
                                    image_parts = [
                                        {
                                            "mime_type": "image/png",
                                            "data": doc_bytes
                                        },
                                        {
                                            "mime_type": "image/png",
                                            "data": screenshot_bytes
                                        }
                                    ]

                                    # Create a prompt focusing on the detected region
                                    prompt_content = [
                                        "Analyze the two images provided. The first image is the 'documentation image' and the second is the 'live screenshot'.",
                                        "Identify and describe the visual differences between these two images specifically within the bounding box region defined by: ",
                                        f"X: {reg.get('x')}, Y: {reg.get('y')}, Width: {reg.get('width')}, Height: {reg.get('height')}.",
                                        "Focus on changes in layout, text, colors, or presence/absence of elements within this specific area.",
                                        "Provide a concise description of the most prominent change you observe in this region."
                                    ]

                                    response = gemini_model.generate_content(prompt_content + image_parts)
                                    gemini_analysis_text = response.text
                                    print(f"[DEBUG] Gemini analysis for region {reg}: {gemini_analysis_text}")
                                except Exception as e:
                                    print(f"[ERROR] Gemini API analysis failed for region {reg}: {e}", file=sys.stderr)
                                    gemini_analysis_text = f"AI analysis failed: {e}"

                            cd = {
                                'comparison_id': comp_row.get('id'),
                                'change_type': 'visual',
                                'description': desc,
                                'position_x': reg.get('x'),
                                'position_y': reg.get('y'),
                                'width': reg.get('width'),
                                'height': reg.get('height'),
                                'severity': 'major' if reg.get('area', 0) > 1000 else 'minor',
                                'ai_analysis': {
                                    'confidence': 0.8, 
                                    'recommendation': 'Review and approve if intended.',
                                    'gemini_description': gemini_analysis_text
                                }
                            }
                            supabase.table('change_details').insert(cd).execute()
            finally:
                if page:
                    print("[DEBUG] Closing Playwright page.")
                    page.close()
                if browser:
                    print("[DEBUG] Closing Playwright browser.")
                    browser.close()

        # Update run
        supabase.table('runs').update({
            'status': 'completed',
            'completed_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'total_images': total_images,
            'changes_detected': changes_detected,
        }).eq('id', run_id).execute()

        print(f'Processed run {run_id}: images={total_images}, changes={changes_detected}')

    except Exception:
        traceback.print_exc()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', dest='run_id', help='Process a specific run id')
    args = parser.parse_args()

    if args.run_id:
        process_run_id(args.run_id)
    else:
        # poll continuously
        while True:
            print('Polling for pending run...')
            try:
                res = supabase.table('runs').select('id').eq('status', 'pending').order('created_at', desc=False).limit(1).execute()
                if res.data:
                    rid = res.data[0].get('id')
                    print('Found run', rid)
                    process_run_id(rid)
                else:
                    print('No pending runs found, waiting...')
            except Exception:
                traceback.print_exc()
            time.sleep(POLL_INTERVAL)
