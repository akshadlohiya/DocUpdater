import os
import sys
import base64
from pdf2image import convert_from_path
from groq import Groq
from PIL import Image
import io

# Ensure UTF-8 encoding for console output (fixes box display issue on Windows)
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configure Poppler path for Windows
POPPLER_PATH = r"C:\poppler\poppler-24.08.0\Library\bin"
if not os.path.exists(POPPLER_PATH):
    # Fallback paths
    POPPLER_PATH = r"C:\poppler\Library\bin"

# ================= CONFIGURATION =================
# Default API Key (can be overridden when calling functions)
GROQ_API_KEY = "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" 

# MODEL SELECTION
MODEL_ID = "meta-llama/llama-4-scout-17b-16e-instruct" 
# =================================================

def get_client(api_key=None):
    """Get Groq client with specified or default API key."""
    key = api_key or GROQ_API_KEY
    return Groq(api_key=key)

def encode_image_to_base64(pil_image):
    """Convert PIL Image to Base64 string for the API."""
    buffered = io.BytesIO()
    # Resize to max 1024px to save API bandwidth/tokens
    if pil_image.width > 1024:
        ratio = 1024 / pil_image.width
        new_height = int(pil_image.height * ratio)
        pil_image = pil_image.resize((1024, new_height))
    
    pil_image.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def pdf_to_images(pdf_path):
    """Converts PDF pages to PIL Images."""
    if not os.path.exists(pdf_path):
        print(f"❌ ERROR: File not found at {pdf_path}")
        return []
    
    try:
        # Convert PDF to list of PIL Images (150 DPI for Vision models)
        images = convert_from_path(pdf_path, dpi=150, poppler_path=POPPLER_PATH)
        print(f"Processing: {os.path.basename(pdf_path)} ({len(images)} pages)...")
        return images
    except Exception as e:
        print(f"❌ ERROR converting PDF: {e}")
        return []

def analyze_page_pair(client, img_v1, img_v2, page_num):
    """Sends images to Groq API."""
    base64_v1 = encode_image_to_base64(img_v1)
    base64_v2 = encode_image_to_base64(img_v2)

    prompt = (
        "Compare these two manual pages (Image 1 = Old, Image 2 = New). "
        "Identify specific changes in: 1. Visuals/Icons, 2. Text/Instructions, 3. Features. "
        "Be concise. If identical, say 'No changes'."
    )

    try:
        completion = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_v1}"}},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_v2}"}}
                    ]
                }
            ],
            temperature=0.1,
            max_completion_tokens=1024,
            stream=False
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"API Error: {str(e)}"

def compare_pdfs(old_pdf_path, new_pdf_path, output_report_path, api_key=None, progress_callback=None):
    """
    Compare two PDF files and generate a markdown report.
    
    Args:
        old_pdf_path: Path to the older version PDF
        new_pdf_path: Path to the newer version PDF
        output_report_path: Path where the comparison report will be saved
        api_key: Optional Groq API key (uses default if not provided)
        progress_callback: Optional callback function(message) for progress updates
    
    Returns:
        dict with keys:
            - success: bool
            - report_path: str (path to the generated report)
            - message: str (status message)
            - changes_found: int (number of pages with changes)
    """
    def log(msg):
        print(msg)
        if progress_callback:
            progress_callback(msg)
    
    log("🚀 Starting PDF Comparison...")
    log(f"📄 Old Version: {os.path.basename(old_pdf_path)}")
    log(f"📄 New Version: {os.path.basename(new_pdf_path)}")
    log(f"📂 Output: {output_report_path}")
    
    # Get client
    client = get_client(api_key)
    
    # Convert PDFs to images
    images_v1 = pdf_to_images(old_pdf_path)
    images_v2 = pdf_to_images(new_pdf_path)

    if not images_v1:
        return {
            "success": False,
            "report_path": None,
            "message": f"Could not read old PDF: {old_pdf_path}",
            "changes_found": 0
        }
    
    if not images_v2:
        return {
            "success": False,
            "report_path": None,
            "message": f"Could not read new PDF: {new_pdf_path}",
            "changes_found": 0
        }

    changes_found = 0
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_report_path), exist_ok=True)
    
    # Open the file to write results
    with open(output_report_path, "w", encoding="utf-8") as f:
        f.write(f"# Change Log: {os.path.basename(old_pdf_path)} vs {os.path.basename(new_pdf_path)}\n\n")
        f.write(f"**Generated:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        
        max_pages = max(len(images_v1), len(images_v2))
        
        for i in range(max_pages):
            log(f"   Analyzing Page {i+1}/{max_pages}...")
            f.write(f"## Page {i+1}\n\n")
            
            if i >= len(images_v1):
                f.write("- **Status:** ✅ New page added in the new version.\n")
                changes_found += 1
            elif i >= len(images_v2):
                f.write("- **Status:** ❌ Page removed in the new version.\n")
                changes_found += 1
            else:
                analysis = analyze_page_pair(client, images_v1[i], images_v2[i], i+1)
                f.write(f"{analysis}\n")
                if "no changes" not in analysis.lower():
                    changes_found += 1
            
            f.write("\n---\n\n")
    
    log(f"✅ Comparison complete! {changes_found} pages with changes detected.")
    log(f"📝 Report saved to: {output_report_path}")
    
    return {
        "success": True,
        "report_path": output_report_path,
        "message": f"Comparison complete. {changes_found} pages with changes.",
        "changes_found": changes_found
    }

def run_standalone_analysis():
    """Run the comparison with hardcoded paths (for standalone use)."""
    # Default standalone paths - update these as needed
    FILE_V1 = r"C:\Users\Yash\Downloads\A1 Merged.pdf"
    FILE_V2 = r"C:\Users\Yash\Downloads\A2 Merged.pdf"
    OUTPUT_DIR = r"C:\Users\Yash\Downloads"
    OUTPUT_FILENAME = "Comparison_Report.md"
    OUTPUT_REPORT = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
    
    result = compare_pdfs(FILE_V1, FILE_V2, OUTPUT_REPORT)
    
    if result["success"]:
        print(f"\n✅ Done! Report saved to: {result['report_path']}")
    else:
        print(f"\n❌ Failed: {result['message']}")

# Execute only when run directly (not when imported)
if __name__ == "__main__":
    run_standalone_analysis()