import uvicorn
import json
import asyncio
import subprocess
import sys
import os
import tempfile
import sqlite3
import re
import shutil
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Depends, Header
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from pydantic import BaseModel
from typing import Optional
from middleware import AuthUser, require_auth, require_admin, get_current_user

# Import PDF comparison module - use pdf folder version for visual comparison
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pdf'))
try:
    from compare_pdfs import compare_pdfs
    PDF_COMPARE_AVAILABLE = True
    print("✓ Visual PDF comparison module loaded (from pdf folder)")
except ImportError:
    # Fallback to pdfcompare.py AI version
    try:
        from pdfcompare import compare_pdfs
        PDF_COMPARE_AVAILABLE = True
        print("✓ AI PDF comparison module loaded (from pdfcompare.py)")
    except ImportError:
        PDF_COMPARE_AVAILABLE = False
        print("Warning: PDF comparison module not available")

app = FastAPI()

# Add CORS middleware to allow requests from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for authentication system (project2)
auth_dist_path = Path(__file__).parent / "project2" / "dist"
if auth_dist_path.exists():
    app.mount("/assets", StaticFiles(directory=str(auth_dist_path / "assets")), name="auth_assets")


class DocumentationDB:
    def __init__(self, db_path="documentation.db"):
        self.db_path = db_path
    
    def get_all_documentation(self):
        """Retrieve all documentation entries"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM documentation 
                ORDER BY created_at DESC
            ''')
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Database error: {e}")
            return []
    
    def get_library_entries(self):
        """Retrieve all documentation with file paths for library view"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, app_name, version, pdf_path, markdown_path, created_at
                FROM documentation 
                WHERE pdf_path IS NOT NULL
                ORDER BY created_at DESC
            ''')
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Database error: {e}")
            return []

class VersionCheckRequest(BaseModel):
    output_path: str
    app_name: str

class CompareRequest(BaseModel):
    old_pdf_path: str
    new_pdf_path: str
    output_report_path: str

class BrowseRequest(BaseModel):
    path: str = ""
    mode: str = "file"  # "file" or "directory"

def parse_version(version_str: str) -> tuple:
    """Parse version string like 'v1.0' or 'v2.1' into tuple (major, minor)"""
    match = re.match(r'v?(\d+)\.?(\d*)', version_str.lower())
    if match:
        major = int(match.group(1))
        minor = int(match.group(2)) if match.group(2) else 0
        return (major, minor)
    return (0, 0)

def increment_version(version_str: str) -> str:
    """Increment the major version number: v1.0 -> v2.0"""
    major, minor = parse_version(version_str)
    return f"v{major + 1}.0"

def get_latest_version_info(output_path: str, app_name: str) -> dict:
    """
    Scan the output directory for existing versions of an app.
    Returns info about the latest version found.
    """
    app_folder = os.path.join(output_path, app_name)
    
    if not os.path.exists(app_folder):
        return {
            "exists": False,
            "latest_version": None,
            "next_version": "v1.0",
            "latest_pdf_path": None,
            "all_versions": []
        }
    
    # Get all version folders
    versions = []
    try:
        for item in os.listdir(app_folder):
            item_path = os.path.join(app_folder, item)
            if os.path.isdir(item_path):
                # Check if it looks like a version folder (v1.0, v2.0, etc.)
                if re.match(r'v?\d+\.?\d*', item.lower()):
                    versions.append(item)
    except Exception as e:
        print(f"Error scanning folder: {e}")
        return {
            "exists": False,
            "latest_version": None,
            "next_version": "v1.0",
            "latest_pdf_path": None,
            "all_versions": []
        }
    
    if not versions:
        return {
            "exists": True,  # Folder exists but no versions
            "latest_version": None,
            "next_version": "v1.0",
            "latest_pdf_path": None,
            "all_versions": []
        }
    
    # Sort versions to find the latest
    versions.sort(key=lambda v: parse_version(v), reverse=True)
    latest_version = versions[0]
    
    # Find PDF in the latest version folder
    latest_folder = os.path.join(app_folder, latest_version)
    latest_pdf_path = None
    
    try:
        for item in os.listdir(latest_folder):
            if item.lower().endswith('.pdf'):
                latest_pdf_path = os.path.join(latest_folder, item)
                break
    except Exception as e:
        print(f"Error finding PDF: {e}")
    
    next_version = increment_version(latest_version)
    
    return {
        "exists": True,
        "latest_version": latest_version,
        "next_version": next_version,
        "latest_pdf_path": latest_pdf_path,
        "all_versions": versions
    }

@app.get("/")
async def get():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    return HTMLResponse(content="<h1>Error: index.html not found</h1>")

@app.get("/auth")
async def get_auth():
    auth_html = Path(__file__).parent / "project2" / "dist" / "index.html"
    if auth_html.exists():
        with open(auth_html, "r", encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    return HTMLResponse(content="<h1>Error: Authentication system not built</h1>")

# WebSocket Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WebSocket] Client connected")
    try:
        while True:
            # Receive data and log it
            data = await websocket.receive_text()
            print(f"[WebSocket] Received: {data}")
            
            # Here we would normally plug into agent_worker.py to generate docs
            # For now, just echo acknowledging receipt
            await websocket.send_text(json.dumps({"status": "received"}))
            
    except WebSocketDisconnect:
        print("[WebSocket] Client disconnected")
    except Exception as e:
        print(f"[WebSocket] Error: {e}")

# API endpoint to get library entries
@app.get("/api/library")
async def get_library():
    """Get all documentation entries for the library view"""
    db = DocumentationDB()
    docs = db.get_library_entries()
    return JSONResponse(content={"library": docs})

# API endpoint to download PDF
@app.get("/api/download/{doc_id}")
async def download_pdf(doc_id: int):
    """Download a PDF file by documentation ID"""
    db = DocumentationDB()
    docs = db.get_all_documentation()
    
    doc = next((d for d in docs if d['id'] == doc_id), None)
    if not doc or not doc.get('pdf_path'):
        return JSONResponse(content={"error": "PDF not found"}, status_code=404)
    
    pdf_path = doc['pdf_path']
    if not os.path.exists(pdf_path):
        return JSONResponse(content={"error": "PDF file not found on disk"}, status_code=404)
    
    # Get the app name and version for the filename
    app_name = doc.get('app_name', 'documentation')
    version = doc.get('version', 'v1.0')
    filename = f"{app_name}_{version}.pdf"
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename
    )

# API endpoint to compare PDFs
@app.post("/api/compare-pdfs")
async def compare_pdfs_endpoint(
    pdf1: UploadFile = File(...),
    pdf2: UploadFile = File(...),
    threshold: float = Form(0.3),
    force_compare: str = Form("false")
):
    """API endpoint to compare two PDFs and return the result PDF for download"""
    if not PDF_COMPARE_AVAILABLE:
        return JSONResponse(
            content={"message": "PDF comparison module not available"},
            status_code=500
        )
    
    # Create temp directory for uploaded files
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create output file paths
        pdf1_path = os.path.join(temp_dir, "pdf1.pdf")
        pdf2_path = os.path.join(temp_dir, "pdf2.pdf")
        
        with open(pdf1_path, "wb") as f:
            f.write(await pdf1.read())
        
        with open(pdf2_path, "wb") as f:
            f.write(await pdf2.read())
        
        # Convert force_compare string to boolean
        force_compare_bool = force_compare.lower() in ('true', '1', 'yes')
        print(f"[Server] force_compare: {force_compare} -> {force_compare_bool}")
        
        # Step 1: Generate visual comparison PDF using pdf folder's compare_pdfs
        print(f"[Server] Starting visual PDF comparison with threshold {threshold} (force_compare={force_compare_bool})...")
        result = compare_pdfs(pdf1_path, pdf2_path, similarity_threshold=threshold, force_compare=force_compare_bool)
        
        if not result.get('success'):
            return JSONResponse(
                content={"message": result.get('message', 'Comparison failed')},
                status_code=500
            )
        
        # Get the comparison PDF path from the result
        comparison_pdf = result.get('details', {}).get('comparison', {}).get('result_pdf')
        log_txt_path = result.get('details', {}).get('comparison', {}).get('log_file')
        
        if not comparison_pdf or not os.path.exists(comparison_pdf):
            return JSONResponse(
                content={"message": "Comparison PDF not generated"},
                status_code=500
            )
        
        
        # Step 2: Convert the text log to a modern, professional PDF
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle, HRFlowable
        
        log_pdf_path = os.path.join(temp_dir, "comparison_log.pdf")
        
        doc = SimpleDocTemplate(log_pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Modern, professional styles
        title_style = ParagraphStyle(
            'ModernTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=20,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'ModernHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2563eb'),  # Modern blue
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold',
            borderWidth=2,
            borderColor=colors.HexColor('#2563eb'),
            borderPadding=8,
            backColor=colors.HexColor('#eff6ff')  # Light blue background
        )
        
        normal_style = ParagraphStyle(
            'ModernNormal',
            parent=styles['Normal'],
            fontSize=11,
            leading=16,
            textColor=colors.HexColor('#374151'),
            fontName='Helvetica'
        )
        
        added_style = ParagraphStyle(
            'AddedText',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#166534'),  # Dark green
            fontName='Courier',
            leftIndent=20,
            rightIndent=20,
            spaceBefore=0,
            spaceAfter=0
        )

        removed_style = ParagraphStyle(
            'RemovedText',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#991b1b'),  # Dark red
            fontName='Courier',
            leftIndent=20,
            rightIndent=20,
            spaceBefore=0,
            spaceAfter=0
        )
        
        # Add title with modern styling
        story.append(Paragraph("<b>PDF Comparison Report</b>", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Add a horizontal line
        from reportlab.platypus import HRFlowable
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#e5e7eb'), spaceBefore=0, spaceAfter=20))
        
        # Read and add log content with modern formatting
        if log_txt_path and os.path.exists(log_txt_path):
            with open(log_txt_path, 'r', encoding='utf-8') as f:
                log_content = f.read()
            
            import html
            in_section = False
            section_lines = []
            
            for line in log_content.split('\n'):
                stripped = line.strip()
                
                # Detect section headers
                if stripped and all(c in '=' for c in stripped):
                    # Major section separator
                    if section_lines:
                        # Flush previous section
                        for sl in section_lines:
                            story.append(sl)
                        section_lines = []
                    story.append(Spacer(1, 0.15*inch))
                    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=5, spaceAfter=5))
                    in_section = True
                    continue
                elif stripped and all(c in '-' for c in stripped):
                    # Minor section separator
                    if section_lines:
                        for sl in section_lines:
                            story.append(sl)
                        section_lines = []
                    story.append(Spacer(1, 0.1*inch))
                    in_section = True
                    continue
                
                if stripped:
                    # Clean special characters and problematic Unicode
                    # Sanitize with UTF-8 encoding to preserve actual text
                    try:
                        cleaned_line = line.encode('utf-8', errors='replace').decode('utf-8')
                    except:
                        cleaned_line = line
                    safe_line = (html.escape(cleaned_line)
                                .replace('✓', '✓')
                                .replace('✗', '✗')
                                .replace('⚠', '⚠'))
                    
                    # Detect if this is a heading line
                    if in_section and not line.startswith(' '):
                        # Section heading
                        story.append(Paragraph(f"<b>{safe_line}</b>", heading_style))
                        in_section = False
                    elif line.startswith('  Page'):
                        # Page entry - use table for better alignment
                        parts = safe_line.split(':', 1)
                        if len(parts) == 2:
                            page_num = parts[0].strip()
                            status = parts[1].strip()
                            
                            # Color code based on status
                            if '[OK]' in status or 'No changes' in status:
                                bg_color = colors.HexColor('#f0fdf4')  # Light green
                                text_color = colors.HexColor('#166534')  # Dark green
                            elif '[!]' in status or 'modified' in status.lower():
                                bg_color = colors.HexColor('#fef3c7')  # Light yellow
                                text_color = colors.HexColor('#92400e')  # Dark yellow
                            else:
                                bg_color = colors.HexColor('#f9fafb')
                                text_color = colors.HexColor('#1f2937')
                            
                            table_data = [[page_num, status]]
                            t = Table(table_data, colWidths=[1.2*inch, 5*inch])
                            t.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (-1, -1), bg_color),
                                ('TEXTCOLOR', (0, 0), (-1, -1), text_color),
                                ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
                                ('FONTNAME', (1, 0), (1, 0), 'Helvetica'),
                                ('FONTSIZE', (0, 0), (-1, -1), 10),
                                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                                ('ALIGN', (1, 0), (1, 0), 'LEFT'),
                                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                                ('TOPPADDING', (0, 0), (-1, -1), 4),
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb'))
                            ]))
                            story.append(t)
                        else:
                            story.append(Paragraph(safe_line, code_style))
                    elif 'ADD:' in stripped:
                        # Highlight added text
                        story.append(Paragraph(safe_line, added_style))
                    elif 'REMOVE:' in stripped:
                        # Highlight removed text
                        story.append(Paragraph(safe_line, removed_style))
                    else:
                        # Regular content
                        story.append(Paragraph(safe_line, normal_style))
                else:
                    story.append(Spacer(1, 0.08*inch))
        else:
            story.append(Paragraph("No detailed log available.", normal_style))
        
        doc.build(story)
        print(f"[Server] Log PDF created: {log_pdf_path}")
        
        # Create a ZIP file with both PDFs
        import zipfile
        zip_path = os.path.join(temp_dir, "comparison_results.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(comparison_pdf, "comparison_visual.pdf")
            zipf.write(log_pdf_path, "comparison_log.pdf")
        
        print(f"[Server] ZIP created with both PDFs: {zip_path}")
        
        # Return the ZIP file containing both PDFs
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename="pdf_comparison_results.zip"
        )
    
    except Exception as e:
        print(f"[Server] Error during comparison: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            content={"message": f"Error during comparison: {str(e)}"},
            status_code=500
        )
    finally:
        # Don't delete temp_dir immediately, let the file be served first
        pass



@app.get("/api/documentation")
async def get_documentation():
    """Get all documentation entries (no authentication required)"""
    db = DocumentationDB()
    docs = db.get_all_documentation()
    return JSONResponse(content={"documentation": docs})

@app.get("/api/library")
async def get_library(user: AuthUser = Depends(require_auth)):
    """API endpoint to get library entries for download (requires authentication)"""
    db = DocumentationDB()
    entries = db.get_library_entries()
    return JSONResponse(content={"library": entries})

@app.get("/api/download/{doc_id}")
async def download_pdf(doc_id: int, user: AuthUser = Depends(require_auth)):
    """Download a PDF file from the library (requires authentication)"""
    db = DocumentationDB()
    docs = db.get_all_documentation()
    
    doc = next((d for d in docs if d['id'] == doc_id), None)
    if not doc:
        return JSONResponse(content={"error": "Documentation not found"}, status_code=404)
    
    pdf_path = doc.get('pdf_path')
    if not pdf_path or not os.path.exists(pdf_path):
        return JSONResponse(content={"error": "PDF file not found"}, status_code=404)
    
    # Generate a friendly filename
    filename = f"{doc.get('app_name', 'documentation')}_{doc.get('version', 'v1')}.pdf"
    
    return FileResponse(
        path=pdf_path,
        filename=filename,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.post("/api/check-version")
async def check_version(request: VersionCheckRequest):
    """API endpoint to check existing versions and get next version"""
    result = get_latest_version_info(request.output_path, request.app_name)
    return JSONResponse(content=result)

@app.post("/api/browse")
async def browse_filesystem(request: BrowseRequest):
    """API endpoint to browse file system"""
    current_path = request.path
    
    # Handle empty path (start at drives or current dir)
    if not current_path:
        current_path = os.getcwd()
        # On Windows, maybe we want to list drives? For now, stick to CWD or user home
        # actually, let's try to detect drives if path is empty/root
        if os.name == 'nt':
            drives = [f"{d}:\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:")]
            return JSONResponse({
                "current_path": "",
                "parent_path": "",
                "items": [{"name": d, "path": d, "type": "directory"} for d in drives]
            })
    
    if not os.path.exists(current_path):
        return JSONResponse(content={"error": "Path not found"}, status_code=404)
        
    try:
        items = []
        # Get parent path
        parent_path = os.path.dirname(os.path.abspath(current_path))
        
        # Scan directory
        with os.scandir(current_path) as it:
            for entry in it:
                try:
                    item_type = "directory" if entry.is_dir() else "file"
                    # Filter based on mode if needed, but usually we show both so user can navigate
                    items.append({
                        "name": entry.name,
                        "path": entry.path,
                        "type": item_type
                    })
                except PermissionError:
                    continue
                    
        # Sort: directories first, then files
        items.sort(key=lambda x: (x['type'] != 'directory', x['name'].lower()))
        
        return JSONResponse({
            "current_path": os.path.abspath(current_path),
            "parent_path": parent_path,
            "items": items
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

class OpenFolderRequest(BaseModel):
    path: str

@app.post("/api/open-folder")
async def open_folder(request: OpenFolderRequest):
    """API endpoint to open a folder in the system file explorer"""
    path = request.path
    
    if not path or not os.path.exists(path):
        return JSONResponse(content={"success": False, "message": "Path does not exist"}, status_code=404)
        
    try:
        if os.name == 'nt':  # Windows
            os.startfile(path)
        elif sys.platform == 'darwin':  # macOS
            subprocess.Popen(['open', path])
        else:  # Linux
            subprocess.Popen(['xdg-open', path])
            
        return JSONResponse(content={"success": True, "message": "Folder opened"})
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)

@app.post("/api/pick-native")
async def pick_native(request: BrowseRequest):
    """
    Open a native file/folder picker dialog on the server side (user's machine).
    mode: 'file' or 'folder'
    """
    try:
        mode = request.mode
        initial_dir = request.path if os.path.exists(request.path) else os.getcwd()
        
        # Use Tkinter via subprocess to avoid main thread issues and PowerShell restrictions
        # This works better across different Windows environments
        if True: # Use for all platforms
            import sys
            
            script_content = ""
            safe_initial_dir = initial_dir.replace('\\', '\\\\')
            
            if mode == 'file':
                script_content = f"""
import tkinter as tk
from tkinter import filedialog
import os

root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)

initial = r'{safe_initial_dir}'
if not os.path.exists(initial):
    initial = os.getcwd()

path = filedialog.askopenfilename(initialdir=initial, title='Select Executable', filetypes=[('Executables', '*.exe'), ('All files', '*.*')])
if path:
    print(path)
"""
            else: # directory
                script_content = f"""
import tkinter as tk
from tkinter import filedialog
import os

root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)

initial = r'{safe_initial_dir}'
if not os.path.exists(initial):
    initial = os.getcwd()

path = filedialog.askdirectory(initialdir=initial, title='Select Directory')
if path:
    print(path)
"""
            
            # Run the script in a separate process
            process = subprocess.run(
                [sys.executable, "-c", script_content],
                capture_output=True,
                text=True
            )
            
            if process.stderr:
                print(f"Picker stderr: {process.stderr}")
            
            path = process.stdout.strip()
            if path:
                return JSONResponse(content={"success": True, "path": path})
            else:
                return JSONResponse(content={"success": False, "message": "Cancelled"})
        
        # Fallback removed as we use one unified method
        pass

    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)

@app.post("/api/compare-pdfs")
async def compare_pdfs_endpoint_auth(
    pdf1: UploadFile = File(...),
    pdf2: UploadFile = File(...),
    threshold: float = Form(0.3),
    force_compare: bool = Form(False),
    user: AuthUser = Depends(require_admin)
):
    """API endpoint to compare two PDFs and return the result PDF for download (admin only)"""
    if not PDF_COMPARE_AVAILABLE:
        return JSONResponse(
            content={"success": False, "message": "PDF comparison module not available"},
            status_code=500
        )
    
    temp_pdf1 = None
    temp_pdf2 = None
    temp_work_dir = None
    
    try:
        # Create temporary directory with proper cross-platform support
        temp_base_dir = tempfile.gettempdir()
        temp_work_dir = tempfile.mkdtemp(prefix="pdf_compare_", dir=temp_base_dir)
        
        print(f"[API] Created temp work directory: {temp_work_dir}")
        
        # Save uploaded files to temporary locations
        temp_pdf1 = os.path.join(temp_work_dir, pdf1.filename or "pdf1.pdf")
        temp_pdf2 = os.path.join(temp_work_dir, pdf2.filename or "pdf2.pdf")
        
        print(f"[API] Saving PDF 1: {temp_pdf1}")
        with open(temp_pdf1, 'wb') as f:
            contents = await pdf1.read()
            f.write(contents)
            print(f"[API] Saved {len(contents)} bytes")
        
        print(f"[API] Saving PDF 2: {temp_pdf2}")
        with open(temp_pdf2, 'wb') as f:
            contents = await pdf2.read()
            f.write(contents)
            print(f"[API] Saved {len(contents)} bytes")
        
        # Convert force_compare string to boolean (FormData sends as string)
        force_compare_bool = force_compare
        if isinstance(force_compare, str):
            force_compare_bool = force_compare.lower() in ('true', '1', 'yes')
        
        print(f"[API] force_compare received: {force_compare} (type: {type(force_compare)})")
        print(f"[API] force_compare_bool converted: {force_compare_bool}")
        
        # Call the comparison function
        print(f"[API] Starting PDF comparison with threshold {threshold} (force_compare={force_compare_bool})...")
        result = compare_pdfs(temp_pdf1, temp_pdf2, similarity_threshold=threshold, force_compare=force_compare_bool)
        
        print(f"[API] Comparison result: {result['success']}")
        
        if not result["success"]:
            error_msg = result.get("error", "Comparison failed")
            print(f"[API] Error: {error_msg}")
            return JSONResponse(
                content={"success": False, "message": error_msg},
                status_code=500
            )
        
        # Get the comparison PDF path from results
        comparison_pdf_path = result["details"]["comparison"]["result_pdf"]
        log_file_path = result["details"]["comparison"].get("log_file")
        
        print(f"[API] Checking comparison PDF: {comparison_pdf_path}")
        
        if not os.path.exists(comparison_pdf_path):
            error_msg = "Comparison PDF was not created"
            print(f"[API] Error: {error_msg}")
            return JSONResponse(
                content={"success": False, "message": error_msg},
                status_code=500
            )
        
        file_size = os.path.getsize(comparison_pdf_path)
        print(f"[API] PDF file size: {file_size} bytes")
        
        if file_size == 0:
            error_msg = "Comparison PDF file is empty"
            print(f"[API] Error: {error_msg}")
            return JSONResponse(
                content={"success": False, "message": error_msg},
                status_code=500
            )
        
        # Save to Downloads folder
        downloads_folder = os.path.expanduser("~/Downloads")
        os.makedirs(downloads_folder, exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"pdf_comparison_{timestamp}.pdf"
        output_path = os.path.join(downloads_folder, output_filename)
        
        print(f"[API] Copying PDF to Downloads: {output_path}")
        
        # Copy the PDF to Downloads
        shutil.copy2(comparison_pdf_path, output_path)
        
        # Copy log file if it exists
        log_filename = None
        if log_file_path and os.path.exists(log_file_path):
            log_filename = f"pdf_comparison_{timestamp}_log.txt"
            log_output_path = os.path.join(downloads_folder, log_filename)
            shutil.copy2(log_file_path, log_output_path)
            print(f"[API] Copied log file to: {log_output_path}")
        
        print(f"[API] Successfully saved to Downloads")
        print(f"[API] File: {output_path}")
        if log_filename:
            print(f"[API] Log: {log_filename}")
        
        # Return the PDF file for download
        return FileResponse(
            path=output_path,
            filename=output_filename,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={output_filename}"}
        )
    
    except Exception as e:
        print(f"[API] PDF comparison error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            content={"success": False, "message": str(e)},
            status_code=500
        )
    
    finally:
        # Clean up temporary directory
        if temp_work_dir and os.path.exists(temp_work_dir):
            try:
                shutil.rmtree(temp_work_dir)
                print(f"[API] Cleaned up temp directory: {temp_work_dir}")
            except Exception as e:
                print(f"[API] Error cleaning up: {e}")

@app.get("/api/browse-directory")
async def browse_directory_endpoint(path: str = "/"):
    """API endpoint to browse directory structure"""
    try:
        result = browse_directory(path)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )

class SaveReportRequest(BaseModel):
    comparison_data: dict
    pdf1_path: str
    pdf2_path: str
    output_path: str

@app.post("/api/save-html-report")
async def save_html_report_endpoint(request: SaveReportRequest):
    """API endpoint to save comparison report as HTML"""
    try:
        result = generate_html_report(
            request.pdf1_path,
            request.pdf2_path,
            request.comparison_data,
            request.output_path
        )
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )

@app.get("/api/file/{file_type}/{doc_id}")
async def get_file(file_type: str, doc_id: int):
    """Serve markdown or PDF files"""
    db = DocumentationDB()
    docs = db.get_all_documentation()
    
    doc = next((d for d in docs if d['id'] == doc_id), None)
    if not doc:
        return JSONResponse(content={"error": "Documentation not found"}, status_code=404)
    
    if file_type == "markdown":
        file_path = doc.get('markdown_path')
    elif file_type == "pdf":
        file_path = doc.get('pdf_path')
    else:
        return JSONResponse(content={"error": "Invalid file type"}, status_code=400)
    
    if not file_path or not os.path.exists(file_path):
        return JSONResponse(content={"error": "File not found"}, status_code=404)
    
    return FileResponse(file_path)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            config = json.loads(data)
            
            # Check for version info request via WebSocket
            if config.get('action') == 'check_version':
                result = get_latest_version_info(
                    config.get('output_path', 'documentation'),
                    config.get('app_name', '')
                )
                await websocket.send_text(f"VERSION_INFO:{json.dumps(result)}")
                continue
            
            # Check for PDF comparison request via WebSocket
            if config.get('action') == 'compare_pdfs':
                if not PDF_COMPARE_AVAILABLE:
                    await websocket.send_text("LOG:❌ PDF comparison module not available")
                    continue
                
                await websocket.send_text("LOG:🔄 Starting PDF comparison...")
                
                def progress_callback(msg):
                    # This will be called synchronously, we'll batch messages
                    pass
                
                try:
                    result = pdfcompare.compare_pdfs(
                        config.get('old_pdf_path'),
                        config.get('new_pdf_path'),
                        config.get('output_report_path'),
                        progress_callback=progress_callback
                    )
                    
                    if result['success']:
                        await websocket.send_text(f"LOG:✅ {result['message']}")
                        await websocket.send_text(f"LOG:📝 Report: {result['report_path']}")
                        await websocket.send_text(f"COMPARE_RESULT:{json.dumps(result)}")
                    else:
                        await websocket.send_text(f"LOG:❌ {result['message']}")
                except Exception as e:
                    await websocket.send_text(f"LOG:❌ Comparison failed: {str(e)}")
                continue
            
            # Regular documentation generation request
            fd, config_path = tempfile.mkstemp(suffix='.json', text=True)
            with os.fdopen(fd, 'w', encoding='utf-8') as tmp:
                json.dump(config, tmp)
            
            current_dir = os.getcwd()
            
            # Determine which script to run based on installation mode
            is_installer = config.get('is_installer', False)
            script_name = 'agent_worker.py' if is_installer else 'app.py'
            mode_text = "Installation Guide" if is_installer else "Application Explorer"
            
            # Use cmd /k to keep the window open so user can see errors
            # We wrap the python command in a batch command
            python_cmd = f"python {script_name} \"{config_path}\""
            
            cmd = [
                "powershell.exe", 
                "-Command", 
                f"Start-Process cmd -WorkingDirectory '{current_dir}' -ArgumentList '/k {python_cmd}' -Verb RunAs"
            ]
            
            await websocket.send_text(f"LOG:🚀 Requesting Admin permissions...")
            await websocket.send_text(f"LOG:📋 Mode: {mode_text}")
            
            # Send version info if available
            version_info = get_latest_version_info(
                config.get('output_path', 'documentation'),
                config.get('app_name', '')
            )
            if version_info['exists'] and version_info['latest_version']:
                await websocket.send_text(f"LOG:📦 Previous version found: {version_info['latest_version']}")
                if version_info['latest_pdf_path']:
                    await websocket.send_text(f"LOG:📄 Will compare with: {os.path.basename(version_info['latest_pdf_path'])}")
            
            try:
                subprocess.Popen(cmd)
                await websocket.send_text(f"LOG:✅ Admin window triggered. Check your taskbar!")
                await websocket.send_text(f"LOG:ℹ️  Config saved to: {config_path}")
                await websocket.send_text(f"LOG:🔧 Running: {script_name}")
            except Exception as e:
                await websocket.send_text(f"LOG:❌ Failed to start process: {str(e)}")

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Host on 0.0.0.0 to allow network access from other devices
    # Access from other PCs using: http://<server-ip>:8001/auth
    uvicorn.run(app, host="0.0.0.0", port=8001)