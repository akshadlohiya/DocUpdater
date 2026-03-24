#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import re

# Required Libraries
try:
    from google import genai
    from PIL import Image, ImageGrab
    import pyautogui
    import psutil
    from markdown import markdown
    
    # xhtml2pdf is the PDF generator (pure Python, no GTK needed)
    try:
        from xhtml2pdf import pisa
        PDF_AVAILABLE = True
    except ImportError:
        print("⚠️ xhtml2pdf not available (PDF generation disabled)")
        PDF_AVAILABLE = False
        
    if sys.platform.startswith('win'):
        import win32gui
        import win32ui
        import win32con
        import win32process
except ImportError:
    print("Installing missing dependencies...")
    packages = ["google-genai", "pyautogui", "Pillow", "markdown", "xhtml2pdf", "psutil", "groq"]
    if sys.platform.startswith('win'):
        packages.append("pywin32")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-U"] + packages)
    from google import genai
    from PIL import Image, ImageGrab
    import pyautogui
    import psutil
    from markdown import markdown
    
    try:
        from weasyprint import HTML, CSS
        WEASYPRINT_AVAILABLE = True
    except (ImportError, OSError):
        print("⚠️ WeasyPrint could not be loaded even after install (GTK+ missing?)")
        WEASYPRINT_AVAILABLE = False
        
    if sys.platform.startswith('win'):
        import win32gui
        import win32ui
        import win32con
        import win32process

try:
    import pdfcompare
    PDF_COMPARE_AVAILABLE = True
except ImportError:
    PDF_COMPARE_AVAILABLE = False
    print("Warning: pdfcompare module could not be imported")

class DocumentationDB:
    def __init__(self, db_path="documentation.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database with documentation table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documentation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                version TEXT NOT NULL,
                description TEXT,
                output_path TEXT NOT NULL,
                markdown_path TEXT,
                pdf_path TEXT,
                screenshot_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'completed'
            )
        ''')
        conn.commit()
        conn.close()
    
    def add_documentation(self, app_name, version, description, output_path, 
                         markdown_path, pdf_path, screenshot_count):
        """Add new documentation entry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO documentation 
            (app_name, version, description, output_path, markdown_path, pdf_path, screenshot_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (app_name, version, description, output_path, markdown_path, pdf_path, screenshot_count))
        conn.commit()
        doc_id = cursor.lastrowid
        conn.close()
        return doc_id
    
    def get_all_documentation(self):
        """Retrieve all documentation entries"""
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

class SmartGUIExplorer:
    def __init__(self, api_key, output_base="documentation", is_installer=False):
        # Ensure absolute path is used for output directory
        self.output_base = Path(output_base).resolve()
        self.output_base.mkdir(parents=True, exist_ok=True)
        self.client = genai.Client(api_key=api_key, http_options={'api_version': 'v1'})
        self.model_id = self.find_best_model()
        self.screenshots = []
        self.app_process = None
        self.app_window_handle = None
        self.app_pid = None
        self.app_exe_path = None  # Track the installer executable path
        self.visited_states = set()
        self.navigation_stack = []
        self.is_installer = is_installer
        self.installation_steps = []
        self.last_screenshot_path = None  # Track last screenshot for deduplication
        pyautogui.FAILSAFE = False

    def find_best_model(self):
        try:
            models = self.client.models.list()
            names = [m.name for m in models if "flash" in m.name.lower()]
            for target in ["models/gemini-2.0-flash-exp", "models/gemini-1.5-flash"]:
                if target in names: return target
            return names[0] if names else "gemini-1.5-flash"
        except: 
            return "gemini-1.5-flash"

    def find_any_window_by_pid(self, pid):
        """Find ANY window belonging to the process (including installer dialogs)"""
        def callback(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd):
                _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                if found_pid == pid:
                    title = win32gui.GetWindowText(hwnd)
                    if title:  # Only windows with titles
                        hwnds.append((hwnd, title))
            return True
        
        hwnds = []
        win32gui.EnumWindows(callback, hwnds)
        return hwnds
    
    def find_child_processes(self, parent_pid):
        """Find all child processes of a parent PID"""
        try:
            parent = psutil.Process(parent_pid)
            children = parent.children(recursive=True)
            return [p.pid for p in children if p.is_running()]
        except:
            return []
    
    def find_window_by_title_pattern(self, pattern):
        """Find window by title pattern (case-insensitive)"""
        pattern_lower = pattern.lower()
        def callback(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title and pattern_lower in title.lower():
                    hwnds.append((hwnd, title))
            return True
        
        hwnds = []
        win32gui.EnumWindows(callback, hwnds)
        return hwnds
    
    def is_system_window(self, hwnd, title):
        """Check if window is a system window (File Explorer, Desktop, etc.)"""
        try:
            # Get window class name
            class_name = win32gui.GetClassName(hwnd)
            
            # Exclude File Explorer windows by class
            explorer_classes = ['CabinetWClass', 'ExploreWClass', 'Progman', 'WorkerW']
            if class_name in explorer_classes:
                print(f"   🚫 Excluded by class '{class_name}': '{title}'")
                return True
            
            # Exclude windows with these titles (case-insensitive)
            excluded_titles = [
                'file explorer',
                'downloads',
                'program manager',
                'desktop',
                'task view',
                'start',
                'cortana',
                'search'
            ]
            
            title_lower = title.lower()
            for excluded in excluded_titles:
                if excluded in title_lower:
                    print(f"   🚫 Excluded by title '{excluded}': '{title}'")
                    return True
            
            # CRITICAL: Exclude ALL explorer.exe windows
            try:
                _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(window_pid)
                proc_name = proc.name().lower()
                
                if proc_name == 'explorer.exe':
                    print(f"   🚫 Excluded explorer.exe window: '{title}' (PID: {window_pid})")
                    return True
                
                # If we have the installer path, only accept windows from that executable
                if self.app_exe_path:
                    proc_exe = proc.exe().lower()
                    installer_exe = self.app_exe_path.lower()
                    
                    # Check if process is running our installer or a child with same name
                    if proc_exe != installer_exe:
                        # Allow common installer helpers
                        proc_basename = os.path.basename(proc_exe)
                        if proc_basename not in ['msiexec.exe', 'setup.exe', 'install.exe']:
                            print(f"   🚫 Excluded non-installer process: '{proc_basename}' (expected {os.path.basename(installer_exe)})")
                            return True
            except:
                pass
            
            return False
        except:
            return False
    
    def find_installer_windows(self, app_name, main_pid):
        """Aggressively find installer windows using multiple strategies"""
        all_windows = []
        process_tree_windows = []  # Windows from actual process tree (highest priority)
        
        # Strategy 1: Search by main PID (HIGHEST PRIORITY)
        windows = self.find_any_window_by_pid(main_pid)
        if windows:
            print(f"   Found {len(windows)} window(s) for main PID {main_pid}")
            for w in windows:
                if not self.is_system_window(w[0], w[1]):
                    process_tree_windows.append(w)
                else:
                    print(f"   Excluded system window: '{w[1]}'")
        
        # Strategy 2: Search child processes (HIGH PRIORITY)
        child_pids = self.find_child_processes(main_pid)
        if child_pids:
            print(f"   Found {len(child_pids)} child process(es)")
            for child_pid in child_pids:
                child_windows = self.find_any_window_by_pid(child_pid)
                if child_windows:
                    print(f"   Found {len(child_windows)} window(s) for child PID {child_pid}")
                    for w in child_windows:
                        if not self.is_system_window(w[0], w[1]):
                            process_tree_windows.append(w)
                        else:
                            print(f"   Excluded system window: '{w[1]}'")
        
        # If we found windows in the process tree, prioritize them
        if process_tree_windows:
            print(f"   ✅ Found {len(process_tree_windows)} non-system window(s) in process tree")
            return process_tree_windows
        
        # Strategy 3: Search by app name in title (FALLBACK)
        if app_name:
            title_windows = self.find_window_by_title_pattern(app_name)
            if title_windows:
                print(f"   Found {len(title_windows)} window(s) matching '{app_name}'")
                for w in title_windows:
                    if not self.is_system_window(w[0], w[1]):
                        hwnd_exists = any(existing[0] == w[0] for existing in all_windows)
                        if not hwnd_exists:
                            all_windows.append(w)
        
        # Strategy 4: Common installer window titles (LAST RESORT)
        # Only use this if we found nothing in process tree
        if not all_windows:
            installer_keywords = ['setup', 'install', 'wizard', 'welcome']
            for keyword in installer_keywords:
                kw_windows = self.find_window_by_title_pattern(keyword)
                if kw_windows:
                    for w in kw_windows:
                        if self.is_system_window(w[0], w[1]):
                            continue
                        
                        hwnd_exists = any(existing[0] == w[0] for existing in all_windows)
                        if not hwnd_exists:
                            # Verify it's a recent window (likely from our launch)
                            try:
                                _, found_pid = win32process.GetWindowThreadProcessId(w[0])
                                proc = psutil.Process(found_pid)
                                # Check if process started recently (within last 30 seconds)
                                if time.time() - proc.create_time() < 30:
                                    print(f"   Found recent installer window: '{w[1]}' (PID: {found_pid})")
                                    all_windows.append(w)
                            except:
                                pass
        
        return all_windows

    def launch_application(self, app_path, app_name):
        print(f"🚀 Launching: {app_path}")
        try:
            if sys.platform.startswith('win'):
                # Store the executable path for filtering
                self.app_exe_path = os.path.abspath(app_path)
                print(f"📝 Tracking executable: {self.app_exe_path}")
                
                self.app_process = subprocess.Popen([app_path], 
                                                    stdout=subprocess.DEVNULL, 
                                                    stderr=subprocess.DEVNULL)
                self.app_pid = self.app_process.pid
                print(f"⏳ Waiting for application to start (PID: {self.app_pid})...")
                print(f"🔍 Using aggressive window detection for installers...")
                print(f"🚫 Will exclude ALL explorer.exe windows")
                
                # Wait and retry multiple times for installer windows
                max_retries = 5
                for attempt in range(max_retries):
                    wait_time = 3 + (attempt * 2)  # 3, 5, 7, 9, 11 seconds
                    time.sleep(wait_time)
                    
                    print(f"   Attempt {attempt + 1}/{max_retries}: Searching for windows...")
                    windows = self.find_installer_windows(app_name, self.app_pid)
                    
                    if windows:
                        # Prefer windows with app name in title
                        for hwnd, title in windows:
                            if app_name.lower() in title.lower():
                                self.app_window_handle = hwnd
                                # Get the PID of the actual window for tracking
                                _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                                self.app_pid = window_pid  # Update to actual window PID
                                print(f"\n✅ Window detected: '{title}'")
                                print(f"   Handle: {hwnd}, PID: {window_pid}")
                                return True
                        
                        # Otherwise use first window
                        self.app_window_handle = windows[0][0]
                        _, window_pid = win32process.GetWindowThreadProcessId(windows[0][0])
                        self.app_pid = window_pid  # Update to actual window PID
                        print(f"\n✅ Window detected: '{windows[0][1]}'")
                        print(f"   Handle: {windows[0][0]}, PID: {window_pid}")
                        return True
                    
                    if attempt < max_retries - 1:
                        print(f"   No window found yet, waiting longer...")
                
                print("⚠️ No windows found after all retries, will use full screen capture")
                return True
            else:
                self.app_process = subprocess.Popen([app_path], 
                                                    stdout=subprocess.DEVNULL, 
                                                    stderr=subprocess.DEVNULL)
                self.app_pid = self.app_process.pid
                time.sleep(6)
                res = subprocess.run(["xdotool", "search", "--pid", str(self.app_pid)], 
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                if res.stdout.strip():
                    self.app_window_handle = res.stdout.strip().split('\n')[-1]
                    print(f"✅ Window detected (ID: {self.app_window_handle})")
                    return True
                return False
        except Exception as e:
            print(f"✗ Launch failed: {e}")
            return False

    def capture_window_screenshot(self):
        """Capture screenshot using ImageGrab (more reliable)"""
        if not self.app_window_handle:
            print("⚠️ No window handle, using full screen")
            return pyautogui.screenshot()
        
        try:
            # Update window handle if it changed (installer dialogs)
            all_pids = [self.app_pid] + self.find_child_processes(self.app_pid)
            for pid in all_pids:
                windows = self.find_any_window_by_pid(pid)
                if windows:
                    # Find visible window
                    for hwnd, title in windows:
                        if win32gui.IsWindowVisible(hwnd):
                            self.app_window_handle = hwnd
                            print(f"📐 Current window: '{title}' (Handle: {hwnd})")
                            break
                    break
            
            win32gui.ShowWindow(self.app_window_handle, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self.app_window_handle)
            time.sleep(0.8)
            
            left, top, right, bottom = win32gui.GetWindowRect(self.app_window_handle)
            width = right - left
            height = bottom - top
            
            print(f"📐 Window size: {width}x{height} at ({left},{top})")
            
            # Use ImageGrab directly (more reliable than PrintWindow)
            img = ImageGrab.grab(bbox=(left, top, right, bottom))
            print(f"✅ Captured: {img.size}")
            return img
            
        except Exception as e:
            print(f"⚠️ Window capture failed: {e}")
            return pyautogui.screenshot()

    def activate_window(self):
        """Bring application window to focus - updated for installer windows"""
        if sys.platform.startswith('win'):
            # Update window handle in case installer created new dialog
            all_pids = [self.app_pid] + self.find_child_processes(self.app_pid)
            for pid in all_pids:
                windows = self.find_any_window_by_pid(pid)
                if windows:
                    for hwnd, title in windows:
                        if win32gui.IsWindowVisible(hwnd):
                            self.app_window_handle = hwnd
                            try:
                                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                                win32gui.SetForegroundWindow(hwnd)
                                time.sleep(0.5)
                                return
                            except:
                                pass

    def capture(self, name, description):
        """Take screenshot and save metadata (with deduplication)"""
        self.activate_window()
        time.sleep(0.8)
        
        filename = f"{name}.png"
        path = self.output_base / filename
        temp_path = self.output_base / f"temp_{datetime.now().strftime('%H%M%S%f')}.png"
        
        # Capture to temporary path first
        if sys.platform.startswith('win'):
            img = self.capture_window_screenshot()
            if img:
                img.save(temp_path)
        else:
            if self.app_window_handle:
                subprocess.run(["import", "-window", self.app_window_handle, str(temp_path)], 
                             stderr=subprocess.DEVNULL)
            else:
                img = pyautogui.screenshot()
                img.save(temp_path)
        
        # Check for duplicate screenshot (99.5% similarity threshold)
        if self.last_screenshot_path and os.path.exists(self.last_screenshot_path):
            similarity = self.compare_screenshots(self.last_screenshot_path, str(temp_path))
            
            if similarity >= 0.995:
                print(f"⏭️  Skipping duplicate screenshot ({similarity*100:.1f}% similar)")
                # Delete temp file
                try:
                    os.remove(temp_path)
                except:
                    pass
                # Return the previous screenshot path instead
                return self.last_screenshot_path
        
        # Not a duplicate - move temp to final path
        try:
            os.replace(temp_path, path)
        except:
            # If replace fails, try copy and delete
            import shutil
            shutil.copy(temp_path, path)
            try:
                os.remove(temp_path)
            except:
                pass
        
        # Update tracking
        self.last_screenshot_path = str(path)
        
        self.screenshots.append({
            'name': name, 
            'description': description, 
            'filename': filename, 
            'path': str(path)
        })
        print(f"📸 Captured: {description}")
        return str(path)

    def get_screen_hash(self, img_path):
        """Create simple hash of screen to detect unique states"""
        img = Image.open(img_path)
        img = img.resize((50, 50))
        import numpy as np
        return str(np.array(img).flatten().tolist())
    
    def compare_screenshots(self, img1_path, img2_path, threshold=0.995):
        """
        Compare two screenshots using Structural Similarity Index (SSIM).
        Returns similarity score (0.0 to 1.0).
        If similarity >= threshold (default 98%), images are considered duplicates.
        """
        try:
            from skimage.metrics import structural_similarity as ssim
            from skimage.io import imread
            from skimage.color import rgb2gray
            import numpy as np
            
            # Load images  
            img1 = imread(img1_path)
            img2 = imread(img2_path)
            
            # Convert to grayscale if needed
            if len(img1.shape) == 3:
                img1 = rgb2gray(img1)
            if len(img2.shape) == 3:
                img2 = rgb2gray(img2)
            
            # Resize to same dimensions if different
            if img1.shape != img2.shape:
                from skimage.transform import resize
                img2 = resize(img2, img1.shape, anti_aliasing=True)
            
            # Calculate SSIM
            similarity_score = ssim(img1, img2, data_range=1.0)
            
            print(f"📊 Screenshot similarity: {similarity_score*100:.1f}%")
            return similarity_score
            
        except Exception as e:
            print(f"⚠️ Error comparing screenshots: {e}")
            # On error, assume images are different (safe fallback)
            return 0.0

    def analyze_clickable_elements(self, screenshot_path):
        """Use Gemini Vision to detect buttons and clickable elements"""
        print("🔍 Analyzing UI elements with AI...")
        
        img = Image.open(screenshot_path)
        print(f"📊 Analyzing image size: {img.size[0]}x{img.size[1]}")
        
        if self.is_installer:
            prompt = """You are analyzing a screenshot of an APPLICATION INSTALLER WINDOW.

Analyze the installer window and identify ALL clickable UI elements.

For each element, provide:
1. Element type (button, checkbox, radio, dropdown, link, etc.)
2. Label/text on the element (the actual text you see)
3. Approximate position as percentage (format: "X%,Y%" where 0,0 is top-left, 100,100 is bottom-right)
4. Purpose/what it likely does

INCLUDE:
- "Next", "Install", "Continue", "Accept", "I Agree" buttons
- Checkboxes for license agreements, optional components
- Input fields for installation path, username, etc.
- Dropdown menus for language, installation type, etc.
- Any visible clickable elements

EXCLUDE ONLY:
- Window control buttons (X, minimize, maximize in top-right corner)

Return ONLY a valid JSON array like this:
[
  {"type": "button", "label": "Next", "position": "70,85", "purpose": "Proceed to next step"},
  {"type": "checkb ox", "label": "I accept the terms", "position": "30,60", "purpose": "Accept license agreement"},
  {"type": "button", "label": "Install", "position": "70,85", "purpose": "Start installation"}
]

IMPORTANT: Give precise percentage coordinates RELATIVE TO THIS WINDOW ONLY."""
        else:
            prompt = """You are analyzing a screenshot of a SINGLE APPLICATION WINDOW.

Analyze the window and identify ALL clickable UI elements.

For each element, provide:
1. Element type (button, menu, tab, link, icon, etc.)
2. Label/text on the element (the actual text you see, or describe the icon)
3. Approximate position as percentage (format: "X%,Y%" where 0,0 is top-left, 100,100 is bottom-right)
4. Purpose/what it likely does

INCLUDE ALL:
- Buttons with text labels
- Menu items
- Toolbar buttons and icons
- Tabs
- Links
- Any visible clickable elements

EXCLUDE ONLY:
- Window control buttons (X, minimize, maximize in top-right corner)

Return ONLY a valid JSON array like this:
[
  {"type": "button", "label": "Save", "position": "15,10", "purpose": "Save document"},
  {"type": "menu", "label": "File", "position": "5,3", "purpose": "File menu"}
]

IMPORTANT: Give precise percentage coordinates RELATIVE TO THIS WINDOW ONLY."""

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[prompt, img]
            )
            
            text = response.text.strip()
            if text.startswith('```'):
                text = text.split('```')[1]
                if text.startswith('json'):
                    text = text[4:]
            text = text.strip()
            
            elements = json.loads(text)
            
            valid_elements = []
            for elem in elements:
                pos = elem.get('position', '50,50')
                try:
                    x_pct, y_pct = map(float, pos.split(','))
                    if 0 <= x_pct <= 100 and 0 <= y_pct <= 100:
                        valid_elements.append(elem)
                except:
                    valid_elements.append(elem)
            
            print(f"✅ Found {len(valid_elements)} valid clickable elements")
            return valid_elements
            
        except Exception as e:
            print(f"⚠️ Analysis error: {e}")
            return []

    def is_safe_to_click(self, element, window_rect):
        """Enhanced safety filter - blocks dangerous buttons and empty areas, allows legitimate UI"""
        label = element.get('label', '').lower().strip()
        purpose = element.get('purpose', '').lower().strip()
        position = element.get('position', '50,50')
        elem_type = element.get('type', '').lower()
        
        # Skip truly empty labels only
        if not label or label == '':
            print(f"   ⚠️ Skipping element with empty label")
            return False
        
        # Block generic/meaningless labels that AI sometimes detects
        generic_labels = ['icon', 'button', 'area', 'viewport', 'workspace', '3d view',
                         'canvas', 'window', 'panel', 'unknown', 'object', 'scene']
        if label in generic_labels:
            print(f"   ⚠️ Skipping generic label: '{label}'")
            return False
        
        # Block viewport display/visibility toggles that don't help exploration
        display_prefixes = ['show ', 'hide ', 'display ', 'toggle ']
        viewport_subjects = ['lamp', 'camera', 'light', 'grid', 'axis', 'gizmo', 
                           'overlay', 'wireframe', 'bone', 'armature', 'reference']
        
        for prefix in display_prefixes:
            if label.startswith(prefix):
                # Check if it's a viewport visibility toggle
                for subject in viewport_subjects:
                    if subject in label:
                        print(f"   ⚠️ Skipping viewport display toggle: '{label}'")
                        return False
        
        # Require minimum length for labels (except recognized UI types)
        recognized_ui_types = ['menu', 'tab', 'checkbox', 'radio', 'dropdown', 'input']
        if len(label) < 2 and elem_type not in recognized_ui_types:
            print(f"   ⚠️ Skipping too-short label: '{label}'")
            return False
        
        if self.is_installer:
            # For installers: whitelist approach for common good buttons
            installer_good = ['next', 'install', 'continue', 'accept', 'agree', 'finish', 
                             'yes', 'ok', 'browse', 'change', 'forward', 'proceed', 'start']
            
            # Check if it's a recognized good button - allow immediately
            for good_word in installer_good:
                if good_word in label or good_word in purpose:
                    print(f"   ✅ Allowing installer button: '{element.get('label', 'N/A')}'")
                    return True
            
            # Block clearly dangerous buttons
            installer_bad = ['cancel', 'close', 'exit', 'quit', 'minimize', 'maximize', 'x button', 'window control']
            
            for bad_word in installer_bad:
                if bad_word in label or bad_word in purpose:
                    print(f"   🚫 Blocked dangerous installer button: '{element.get('label', 'N/A')}' (reason: {bad_word})")
                    return False
            
            # Allow installer UI elements
            if element.get('type', '') in recognized_ui_types:
                return True
            
            # For installers, allow most other buttons except those in bad position
            try:
                x_pct, y_pct = map(float, position.split(','))
                if x_pct > 90 and y_pct < 5:
                    print(f"   ⚠️ Skipping top-right corner: '{label}'")
                    return False
            except:
                pass
            
            # If it's not in the bad list and not in top corner, allow it
            return True
            
        else:
            # For normal apps: block only clearly dangerous buttons
            danger_words = ['close', 'exit', 'quit', 'shut down', 'log out', 'sign out']
            danger_symbols = ['×', '✕', '✖', '☒']  # Common close symbols
            
            # Check for danger words
            for word in danger_words:
                if word == label or word in purpose:
                    print(f"   🚫 Blocked dangerous button: '{element.get('label', 'N/A')}' (reason: {word})")
                    return False
            
            # Check for close symbols
            for symbol in danger_symbols:
                if symbol in label:
                    print(f"   🚫 Blocked close symbol: '{label}'")
                    return False
            
            # Position-based filtering
            try:
                x_pct, y_pct = map(float, position.split(','))
                
                # Block top-right corner (window controls)
                if x_pct > 90 and y_pct < 5:
                    print(f"   ⚠️ Skipping top-right corner: '{label}'")
                    return False
                
                # Block suspicious center/middle clicks UNLESS it's a recognized UI element
                in_center_region = (30 < x_pct < 70 and 30 < y_pct < 70)
                
                if in_center_region:
                    # Only allow center clicks for clear UI elements with good labels
                    if elem_type not in recognized_ui_types:
                        # Must have a clear, specific label (length >= 3)
                        if len(label) < 3:
                            print(f"   ⚠️ Skipping center area with short label: '{label}' at ({x_pct:.1f}%, {y_pct:.1f}%)")
                            return False
                        
                        # Block if label suggests it's a workspace area
                        workspace_keywords = ['view', 'workspace', 'canvas', '3d', 'viewport', 'scene']
                        if any(keyword in label for keyword in workspace_keywords):
                            print(f"   ⚠️ Skipping workspace area: '{label}'")
                            return False
                            
            except:
                pass
        
        # Default: allow the click
        return True

    def get_click_coordinates(self, position_str):
        """Convert position percentage to actual coordinates within window - FIXED for ImageGrab"""
        try:
            # Parse position string more robustly
            if not position_str or not isinstance(position_str, str):
                position_str = "50,50"
            
            # Clean the string
            position_str = position_str.strip().replace('%', '').replace(' ', '')
            
            if ',' in position_str:
                parts = position_str.split(',')
                try:
                    x_pct = float(parts[0])
                    y_pct = float(parts[1])
                except (ValueError, IndexError):
                    print(f"   ⚠️ Invalid position format: '{position_str}', using center")
                    x_pct, y_pct = 50, 50
            else:
                x_pct, y_pct = 50, 50
            
            # Clamp values to valid range
            x_pct = max(0, min(100, x_pct))
            y_pct = max(0, min(100, y_pct))
            
            if sys.platform.startswith('win') and self.app_window_handle:
                # Get current window rect (may have changed for installer dialogs)
                windows = self.find_any_window_by_pid(self.app_pid)
                if windows:
                    for hwnd, title in windows:
                        if win32gui.IsWindowVisible(hwnd):
                            self.app_window_handle = hwnd
                            break
                
                # Get window rect
                left, top, right, bottom = win32gui.GetWindowRect(self.app_window_handle)
                width = right - left
                height = bottom - top
                
                # Correct Logic: Map percentages to the FULL window rect (since ImageGrab captures the full window)
                # Do NOT offset for client area/title bar, as the AI sees the title bar in the screenshot
                
                x = left + (width * x_pct / 100)
                y = top + (height * y_pct / 100)
                
                print(f"   📐 Window: ({left},{top}) to ({right},{bottom}) - {width}x{height}")
                print(f"   🎯 Position: {x_pct:.1f}%,{y_pct:.1f}% -> Click: ({int(x)},{int(y)})")
            else:
                screen_width, screen_height = pyautogui.size()
                x = screen_width * x_pct / 100
                y = screen_height * y_pct / 100
            
            return (int(x), int(y))
        except Exception as e:
            print(f"   ❌ Coordinate calculation error: {e}")
            print(f"   ⚠️ Position string was: '{position_str}'")
            # Return center of screen as fallback
            screen_width, screen_height = pyautogui.size()
            return (screen_width // 2, screen_height // 2)

    def check_window_still_exists(self):
        """Check if ANY window from the process still exists (installer may create new windows)"""
        if sys.platform.startswith('win') and self.app_pid:
            try:
                # Check if process is still running
                process = psutil.Process(self.app_pid)
                if not process.is_running():
                    # Check child processes
                    children = self.find_child_processes(self.app_pid)
                    if not children:
                        return False
                    # If children exist, check their windows
                    for child_pid in children:
                        windows = self.find_any_window_by_pid(child_pid)
                        if windows:
                            self.app_window_handle = windows[0][0]
                            self.app_pid = child_pid  # Update to child PID
                            return True
                    return False
                
                # Check if any visible windows exist for this process or its children
                all_pids = [self.app_pid] + self.find_child_processes(self.app_pid)
                
                for pid in all_pids:
                    windows = self.find_any_window_by_pid(pid)
                    if windows:
                        # Update to current visible window
                        for hwnd, title in windows:
                            if win32gui.IsWindowVisible(hwnd):
                                self.app_window_handle = hwnd
                                if pid != self.app_pid:
                                    self.app_pid = pid  # Update to correct PID
                                return True
                
                return False
            except psutil.NoSuchProcess:
                return False
            except:
                return False
        return True

    def run_installation_guide(self, max_steps=50):
        """Run through installer and capture each step - FIXED VERSION"""
        print("\n" + "="*70)
        print("    STARTING INSTALLATION GUIDE CAPTURE")
        print("="*70 + "\n")
        
        step_count = 0
        
        initial_path = self.capture(
            f"step_{step_count:02}_welcome", 
            "Installation Welcome Screen"
        )
        self.installation_steps.append({
            'step': step_count,
            'title': 'Welcome Screen',
            'description': 'Initial installation screen',
            'screenshot': initial_path
        })
        step_count += 1
        
        action_history = []
        stall_counter = 0
        max_stalls = 10
        
        last_screenshot_hash = self.get_screen_hash(initial_path)
        same_screen_count = 0
        
        installation_phase = "pre-install"
        
        print(f"✅ Initial screen captured\n")
        
        while step_count < max_steps:
            print("=" * 70)
            print(f"STEP {step_count}/{max_steps} - Phase: {installation_phase}")
            print("=" * 70)
            
            # FIXED: More lenient window checking
            if not self.check_window_still_exists():
                if step_count < 10:  # Increased from 5
                    print("⚠️ Window not detected, waiting 5s...")
                    time.sleep(5)
                    if self.check_window_still_exists():
                        print("   ✅ Window reappeared, continuing...")
                    else:
                        print("⚠️ Still no window, trying one more time...")
                        time.sleep(5)
                        if not self.check_window_still_exists():
                            print("❌ Installation window closed")
                            break
                else:
                    print("✅ Installation completed - window closed")
                    break
            
            # Capture current screenshot
            current_path = self.capture(
                f"step_{step_count:02}_installer",
                f"Installation step {step_count}"
            )
            
            # Check if screen changed from last one
            current_hash = self.get_screen_hash(current_path)
            if current_hash == last_screenshot_hash:
                same_screen_count += 1
                print(f"⚠️ Screen appears unchanged (count: {same_screen_count})")
                
                if same_screen_count >= 3:
                    print("❌ Screen stuck for 3+ iterations, stopping")
                    break
            else:
                same_screen_count = 0
                last_screenshot_hash = current_hash
            
            # Analyze clickable elements
            print("🔍 Analyzing installer UI...")
            elements = self.analyze_clickable_elements(current_path)
            
            if not elements:
                print("⚠️ No clickable elements found")
                stall_counter += 1
                if stall_counter >= max_stalls:
                    print("❌ Max stalls reached, stopping")
                    break
                time.sleep(2)
                continue
            
            # Filter safe elements for installer
            safe_elements = []
            window_rect = None
            if sys.platform.startswith('win') and self.app_window_handle:
                try:
                    window_rect = win32gui.GetWindowRect(self.app_window_handle)
                except:
                    pass
            
            for elem in elements:
                if self.is_safe_to_click(elem, window_rect):
                    safe_elements.append(elem)
            
            print(f"📋 Found {len(elements)} elements, {len(safe_elements)} safe to click")
            
            if not safe_elements:
                print("⚠️ No safe elements to click")
                stall_counter += 1
                if stall_counter >= max_stalls:
                    print("❌ Max stalls reached, stopping")
                    break
                time.sleep(2)
                continue
            
            # Prioritize installer advancement buttons
            priority_keywords = ['next', 'install', 'continue', 'accept', 'agree', 'finish', 'yes', 'ok']
            best_element = None
            
            for keyword in priority_keywords:
                for elem in safe_elements:
                    label = elem.get('label', '').lower()
                    purpose = elem.get('purpose', '').lower()
                    if keyword in label or keyword in purpose:
                        best_element = elem
                        break
                if best_element:
                    break
            
            # If no priority button, use first safe element
            if not best_element:
                best_element = safe_elements[0]
            
            # Click the selected element
            label = best_element.get('label', 'Unknown')
            elem_type = best_element.get('type', 'button')
            position = best_element.get('position', '50,50')
            
            print(f"🖱️  Clicking: {elem_type} '{label}'")
            
            try:
                x, y = self.get_click_coordinates(position)
                self.activate_window()
                
                # Get screen hash before click for verification
                pre_click_hash = self.get_screen_hash(current_path)
                
                # Hover before clicking
                time.sleep(0.3)
                pyautogui.moveTo(x, y, duration=0.5)
                time.sleep(0.3)  # Hover pause
                
                # Perform click
                pyautogui.click(x, y)
                print(f"   ✅ Clicked at ({x}, {y})")
                
                # Wait for screen to update
                time.sleep(2)
                
                # Verify the click worked by checking if screen changed
                verification_path = self.capture(
                    f"step_{step_count:02}_verify",
                    f"Verification after clicking {label}"
                )
                post_click_hash = self.get_screen_hash(verification_path)
                
                    # If screen didn't change, retry with spiral search
                if pre_click_hash == post_click_hash:
                    print(f"   ⚠️ Screen unchanged, starting spiral search...")
                    
                    retry_succeeded = False
                    # Spiral offsets: Center -> R5 -> R10 -> R15
                    spiral_offsets = [
                        (0, -5), (0, 5), (-5, 0), (5, 0),   # Radius 5 (Cross)
                        (-5, -5), (-5, 5), (5, 5), (5, -5), # Radius 7 (Corners)
                        (0, -10), (0, 10), (-10, 0), (10, 0), # Radius 10 (Cross)
                        (-10, -10), (-10, 10), (10, 10), (10, -10), # Radius 14 (Corners)
                        (0, -15), (0, 15), (-15, 0), (15, 0)  # Radius 15 (Cross)
                    ]
                    
                    for i, (offset_x, offset_y) in enumerate(spiral_offsets):
                        retry_x = x + offset_x
                        retry_y = y + offset_y
                        
                        print(f"   Spiral Retry {i+1}/{len(spiral_offsets)}: ({retry_x}, {retry_y}) [Offset: {offset_x},{offset_y}]")
                        
                        # Move and click
                        pyautogui.moveTo(retry_x, retry_y, duration=0.2)
                        time.sleep(0.1)
                        pyautogui.click(retry_x, retry_y)
                        
                        # Wait for potential update
                        time.sleep(1.5)
                        
                        # Verify
                        verify_retry_path = self.capture(
                            f"step_{step_count:02}_retry{i+1}",
                            f"Spiral retry {i+1} at offset {offset_x},{offset_y}"
                        )
                        retry_hash = self.get_screen_hash(verify_retry_path)
                        
                        if retry_hash != pre_click_hash:
                            print(f"   ✅ Spiral retry successful at offset ({offset_x}, {offset_y})!")
                            retry_succeeded = True
                            break
                    
                    if not retry_succeeded:
                        print(f"   ⚠️ Click had no effect after spiral search")
                        stall_counter += 1
                        if stall_counter >= max_stalls:
                            print("❌ Max stalls reached, stopping")
                            break
                        continue
                
                # Add to installation steps
                self.installation_steps.append({
                    'step': step_count,
                    'title': f'{elem_type.capitalize()}: {label}',
                    'description': f'Clicked {label} button to proceed',
                    'screenshot': current_path
                })
                
                # Wait and check for progress
                time.sleep(3)
                
                # Detect installation phase
                if 'install' in label.lower():
                    installation_phase = "installing"
                    print("📦 Installation phase detected")
                elif 'finish' in label.lower() or 'complete' in label.lower():
                    installation_phase = "post-install"
                    print("✅ Installation finishing")
                
                # If installing, wait longer
                if installation_phase == "installing":
                    print("⏳ Waiting for installation to complete...")
                    time.sleep(10)
                
                step_count += 1
                stall_counter = 0
                
            except Exception as e:
                print(f"❌ Click failed: {e}")
                stall_counter += 1
                if stall_counter >= max_stalls:
                    print("❌ Max stalls reached, stopping")
                    break
                continue
        
        print(f"\n✅ Installation guide completed with {step_count} steps captured")

    def generate_installation_doc(self, app_name):
        """Generate installation guide documentation"""
        print(f"\n--- Generating Installation Guide for {app_name} ---")
        
        steps_text = "\n\n".join([
            f"<div class='step'>\n**Step {s['step'] + 1}: {s['title']}**\n{s['description']}\n\n![Step {s['step'] + 1}]({Path(s['screenshot']).name})\n</div>"
            for s in self.installation_steps
        ])
        
        prompt = f"""Create a comprehensive Installation Guide for '{app_name}'.

You have {len(self.installation_steps)} screenshots showing the installation process.

INSTALLATION STEPS CAPTURED:
{steps_text}

Generate a complete installation guide in Markdown format.

IMPORTANT FORMATTING RULE:
Wrap each step in a <div class="step">...</div> block. Inside the block, place the text description first, then the image.

Structure:
- Title
- Overview
- System Requirements
- Installation Steps (numbered, with screenshots)
- Post-Installation
- Troubleshooting"""

        contents = [prompt] + [Image.open(s['screenshot']) for s in self.installation_steps]
        
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.model_id, 
                    contents=contents
                )
                return response.text
            except Exception as e:
                wait_time = (2 ** attempt) * 5
                print(f"⚠️ Error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
        
        return None

    def save_versioned_and_pdf(self, app_name, version, content):
        """Save documentation as Markdown and PDF"""
        folder_name = app_name.replace(" ", "_").lower()
        target_dir = self.output_base / folder_name / version
        target_dir.mkdir(parents=True, exist_ok=True)
        
        if self.is_installer:
            md_path = target_dir / "INSTALLATION_GUIDE.md"
        else:
            md_path = target_dir / "USER_MANUAL.md"
            
        md_path.write_text(content, encoding='utf-8')
        
        # Move screenshots
        if self.is_installer:
            for s in self.installation_steps:
                dest_path = target_dir / Path(s['screenshot']).name
                if os.path.exists(s['screenshot']):
                    os.replace(s['screenshot'], dest_path)
        else:
            for s in self.screenshots:
                dest_path = target_dir / s['filename']
                if os.path.exists(s['path']):
                    os.replace(s['path'], dest_path)
        
        pdf_path = None
        
        # CSS Styles for better PDF layout
        css_styles = """
        <style>
            @page { margin: 2cm; }
            body { font-family: Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; }
            img { max-width: 95%; height: auto; display: block; margin: 20px auto; border: 1px solid #ddd; box-shadow: 2px 2px 8px rgba(0,0,0,0.1); }
            h1, h2, h3 { color: #2c3e50; margin-top: 1.5em; border-bottom: 1px solid #eee; padding-bottom: 0.5em; }
            h1 { font-size: 24pt; text-align: center; }
            h2 { font-size: 18pt; }
            p { margin-bottom: 1em; text-align: justify; }
            code { background: #f4f4f4; padding: 2px 5px; border-radius: 3px; font-family: msgothic, monospace; }
            pre { background: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }
            blockquote { border-left: 4px solid #3498db; padding-left: 10px; color: #7f8c8d; }
            .step { page-break-inside: avoid; margin-bottom: 2em; border-bottom: 1px solid #eee; padding-bottom: 1em; }
        </style>
        """

        # Convert markdown to HTML then to PDF
        try:
            # Convert image paths to absolute file URIs for PDF generation
            def make_absolute(match):
                path = match.group(1)
                if not path.startswith('http') and not path.startswith('file:'):
                     # Resolve path relative to target_dir
                     full_path = (target_dir / path).resolve()
                     return f'src="{full_path.as_uri()}"'
                return match.group(0)

            if 'WEASYPRINT_AVAILABLE' in globals() and WEASYPRINT_AVAILABLE:
                html_content = css_styles + markdown(content)
                # Fix image paths
                html_content = re.sub(r'src="([^"]+)"', make_absolute, html_content)
                
                if self.is_installer:
                    pdf_path = target_dir / "INSTALLATION_GUIDE.pdf"
                else:
                    pdf_path = target_dir / "USER_MANUAL.pdf"
                    
                HTML(string=html_content).write_pdf(str(pdf_path))
                print(f"📕 PDF: {pdf_path}")
            elif 'PDF_AVAILABLE' in globals() and PDF_AVAILABLE:
                html_content = css_styles + markdown(content)
                # Fix image paths
                html_content = re.sub(r'src="([^"]+)"', make_absolute, html_content)
                
                if self.is_installer:
                    pdf_path = target_dir / "INSTALLATION_GUIDE.pdf"
                else:
                    pdf_path = target_dir / "USER_MANUAL.pdf"
                
                with open(pdf_path, "wb") as pdf_file:
                    pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
                
                if pisa_status.err:
                     print(f"⚠️ xhtml2pdf error: {pisa_status.err}")
                     pdf_path = None
                else:
                     print(f"📕 PDF (via xhtml2pdf): {pdf_path}")
            else:
                print("⚠️  Skipping PDF generation (WeasyPrint and xhtml2pdf missing)")
                
            print(f"\n✅ SUCCESS!")
            print(f"📄 Markdown: {md_path}")
            
        except Exception as e:
            print(f"⚠️ PDF Generation failed: {e}")
            print(f"📄 Markdown saved: {md_path}")
        
        return str(md_path), str(pdf_path) if pdf_path else None

    def explore_app_intelligently(self, max_depth=2, max_screenshots=30):
        """Intelligently explore application by detecting and clicking elements"""
        print("\n--- Starting Intelligent UI Exploration ---")
        
        screenshot_count = 0
        
        initial_path = self.capture(
            f"{screenshot_count:03}_main_interface", 
            "Main application interface"
        )
        screenshot_count += 1
        initial_hash = self.get_screen_hash(initial_path)
        self.visited_states.add(initial_hash)
        
        self._explore_recursive(initial_path, depth=0, max_depth=max_depth, 
                               screenshot_count=screenshot_count, 
                               max_screenshots=max_screenshots)

    def _explore_recursive(self, current_screenshot, depth, max_depth, screenshot_count, max_screenshots):
        """Recursively explore UI by clicking elements"""
        
        if depth >= max_depth or screenshot_count >= max_screenshots:
            return screenshot_count
        
        if not self.check_window_still_exists():
            print("❌ Application window closed unexpectedly!")
            return screenshot_count
        
        elements = self.analyze_clickable_elements(current_screenshot)
        
        safe_elements = []
        if sys.platform.startswith('win') and self.app_window_handle:
            window_rect = win32gui.GetWindowRect(self.app_window_handle)
        else:
            window_rect = None
            
        for element in elements:
            if self.is_safe_to_click(element, window_rect):
                safe_elements.append(element)
        
        print(f"📋 Found {len(elements)} elements, {len(safe_elements)} are safe to click")
        
        for element in safe_elements:
            if screenshot_count >= max_screenshots:
                break
            
            if not self.check_window_still_exists():
                print("❌ Application window closed!")
                return screenshot_count
                
            label = element.get('label', 'Unknown')
            elem_type = element.get('type', 'element')
            position = element.get('position', '50,50')
            
            print(f"\n🖱️  Preparing to click: {elem_type} '{label}'")
            
            print("📸 Capturing current state before click...")
            time.sleep(0.5)
            temp_path = self.output_base / f"temp_preclick_{screenshot_count}.png"
            
            self.activate_window()
            time.sleep(0.8)
            
            if sys.platform.startswith('win'):
                fresh_img = self.capture_window_screenshot()
                if fresh_img:
                    fresh_img.save(temp_path)
            else:
                fresh_img = pyautogui.screenshot()
                fresh_img.save(temp_path)
            
            print("🔍 Re-analyzing current UI state...")
            current_elements = self.analyze_clickable_elements(str(temp_path))
            
            matching_element = None
            for curr_elem in current_elements:
                if (curr_elem.get('label', '').lower() == label.lower() and 
                    curr_elem.get('type', '').lower() == elem_type.lower()):
                    matching_element = curr_elem
                    break
            
            if temp_path.exists():
                temp_path.unlink()
            
            if not matching_element:
                print(f"⚠️  Element '{label}' no longer visible, skipping...")
                continue
            
            current_position = matching_element.get('position', position)
            print(f"✅ Element confirmed at: {current_position}")
            
            x, y = self.get_click_coordinates(current_position)
            try:
                self.activate_window()
                pyautogui.click(x, y)
                time.sleep(2)
                
                if not self.check_window_still_exists():
                    print("❌ Click closed the application!")
                    return screenshot_count
                
                new_path = self.capture(
                    f"{screenshot_count:03}_{elem_type}_{label.replace(' ', '_').lower()[:30]}", 
                    f"{elem_type.capitalize()}: {label}"
                )
                screenshot_count += 1
                
                new_hash = self.get_screen_hash(new_path)
                
                if new_hash not in self.visited_states:
                    self.visited_states.add(new_hash)
                    
                    if depth + 1 < max_depth:
                        screenshot_count = self._explore_recursive(
                            new_path, depth + 1, max_depth, 
                            screenshot_count, max_screenshots
                        )
                
                if not self.check_window_still_exists():
                    print("❌ Application closed during exploration!")
                    return screenshot_count
                    
                print("⬅️  Navigating back...")
                pyautogui.press('escape')
                time.sleep(1)
                
            except Exception as e:
                print(f"⚠️ Click failed: {e}")
                continue
        
        return screenshot_count

    def generate_doc_with_retry(self, app_name, app_desc, user_notes, max_retries=3):
        """Generate documentation using AI"""
        print(f"\n--- Generating Documentation with {self.model_id} ---")
        
        image_list_text = "\n".join([
            f"- {s['filename']}: {s['description']}" 
            for s in self.screenshots
        ])
        
        prompt = f"""Act as a professional technical writer. Create a comprehensive Markdown User Manual for '{app_name}'.

Application Description: {app_desc}
Additional Notes: {user_notes}

You have {len(self.screenshots)} screenshots showing different parts of the application.

INSTRUCTIONS:
1. Create a well-structured manual with clear sections
2. Embed screenshots using: ![Description](filename.png)
3. Explain each feature shown in the screenshots
4. Include step-by-step instructions where appropriate
5. Use professional, clear language
6. Organize content logically (Getting Started, Features, Advanced Usage, etc.)

AVAILABLE SCREENSHOTS:
{image_list_text}

Generate a complete, professional user manual in Markdown format."""

        contents = [prompt] + [Image.open(s['path']) for s in self.screenshots]
        
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_id, 
                    contents=contents
                )
                return response.text
            except Exception as e:
                wait_time = (2 ** attempt) * 5
                print(f"⚠️ Error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
        
        return None

def run_agent(config):
    """Run the agent with configuration from the web interface"""
    print(f"Starting exploration for: {config['app_name']}")
    
    api_key = config.get('api_key', '')
    app_path = config.get('app_path', '')
    app_name = config.get('app_name', '')
    version = config.get('version', 'v1.0')
    description = config.get('description', 'Application documentation')
    notes = config.get('notes', '')
    max_depth = int(config.get('max_depth', 2))
    max_screenshots = int(config.get('max_screenshots', 30))
    output_path = config.get('output_path', 'documentation')
    is_installer = config.get('is_installer', False)
    
    explorer = SmartGUIExplorer(api_key, output_base=output_path, is_installer=is_installer)
    
    if explorer.launch_application(app_path, app_name):
        print("✅ Application launched successfully")
        
        if sys.platform.startswith('win') and explorer.app_window_handle:
            print("⚠️  Application window detected. Starting exploration...")
            time.sleep(2)
        
        if is_installer:
            max_install_steps = int(config.get('max_install_steps', 50))
            explorer.run_installation_guide(max_steps=max_install_steps)
            
            doc = explorer.generate_installation_doc(app_name)
            if doc:
                md_path, pdf_path = explorer.save_versioned_and_pdf(app_name, version, doc)
                
                db = DocumentationDB()
                doc_id = db.add_documentation(
                    app_name=app_name,
                    version=version,
                    description=f"Installation Guide - {description}",
                    output_path=output_path,
                    markdown_path=md_path,
                    pdf_path=pdf_path,
                    screenshot_count=len(explorer.installation_steps)
                )
                print(f"✅ Installation guide saved to database (ID: {doc_id})")
            else:
                print("❌ Installation guide generation failed")
        else:
            explorer.explore_app_intelligently(max_depth=max_depth, max_screenshots=max_screenshots)
            
            doc = explorer.generate_doc_with_retry(app_name, description, notes)
            if doc:
                md_path, pdf_path = explorer.save_versioned_and_pdf(app_name, version, doc)
                
                db = DocumentationDB()
                doc_id = db.add_documentation(
                    app_name=app_name,
                    version=version,
                    description=description,
                    output_path=output_path,
                    markdown_path=md_path,
                    pdf_path=pdf_path,
                    screenshot_count=len(explorer.screenshots)
                )
                print(f"✅ Documentation saved to database (ID: {doc_id})")
            else:
                print("❌ Documentation generation failed")
        
        # --- PDF COMPARISON STEP ---
        prev_pdf = config.get('previous_pdf_path')
        if prev_pdf and os.path.exists(prev_pdf) and 'pdf_path' in locals() and pdf_path and os.path.exists(pdf_path):
            if PDF_COMPARE_AVAILABLE:
                print(f"\n⚡ Starting comparison with previous version: {os.path.basename(prev_pdf)}")
                report_name = f"Comparison_{version}_vs_prev.md"
                report_path = os.path.join(output_path, app_name, version, report_name)
                
                try:
                    result = pdfcompare.compare_pdfs(prev_pdf, pdf_path, report_path)
                    if result['success']:
                        print(f"✅ Comparison Report Generated: {report_path}")
                        print(f"📊 Changes found: {result['changes_found']} pages")
                    else:
                        print(f"❌ Comparison failed: {result['message']}")
                except Exception as e:
                    print(f"❌ Comparison error: {e}")
            else:
                print("⚠️  Skipping PDF comparison (module not available)")

        
        if explorer.app_process:
            try:
                explorer.app_process.terminate()
                print("🛑 Application closed")
            except:
                pass
    else:
        print("❌ Application launch/detection failed.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        config_data = {}
        
        if os.path.exists(arg):
            try:
                print(f"📂 Reading config from file: {arg}")
                with open(arg, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            except Exception as e:
                print(f"❌ Failed to read config file: {e}")
                input("Press Enter to exit...")
                sys.exit(1)
        else:
            try:
                config_data = json.loads(arg)
            except json.JSONDecodeError:
                print("❌ Invalid config argument")
                input("Press Enter to exit...")
                sys.exit(1)
                
        run_agent(config_data)
        input("\nProcess Finished. Press Enter to close this admin window...")