#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import json
import sqlite3
import ctypes
import io
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 encoding for console output (fixes box display issue on Windows)
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- ENHANCED CONFIGURATION ---
# Calibration system for precise clicking
TITLE_BAR_HEIGHT = 31       # Standard Windows title bar
BORDER_WIDTH = 8            # Standard Windows border
MANUAL_Y_OFFSET = 0         # Additional fine-tuning if needed
MANUAL_X_OFFSET = 0         # Additional fine-tuning if needed
WATCHER_TIMEOUT = 5         # How long to watch screen for changes (seconds)
CALIBRATION_MODE = False    # Set to True to test click accuracy
WINDOW_DETECT_TIMEOUT = 30  # Extended timeout for slow-loading apps
# ---------------------

# Required Libraries
try:
    from google import genai
    from PIL import Image, ImageGrab, ImageChops, ImageDraw
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
        import win32api
except ImportError:
    print("Installing missing dependencies...")
    packages = ["google-genai", "pyautogui", "Pillow", "markdown", "xhtml2pdf", "psutil"]
    if sys.platform.startswith('win'):
        packages.append("pywin32")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-U"] + packages)
    from google import genai
    from PIL import Image, ImageGrab, ImageChops, ImageDraw
    import pyautogui
    import psutil
    from markdown import markdown
    
    try:
        from xhtml2pdf import pisa
        PDF_AVAILABLE = True
    except (ImportError, OSError):
        print("⚠️ xhtml2pdf could not be loaded")
        PDF_AVAILABLE = False
        
    if sys.platform.startswith('win'):
        import win32gui
        import win32ui
        import win32con
        import win32process
        import win32api

# --- CRITICAL: HIGH-DPI AWARENESS FIX ---
try:
    if sys.platform.startswith('win'):
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor DPI Aware V2
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # Per-Monitor DPI Aware
    except:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass
# ---------------------------------------

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
        self.app_exe_path = None  # Track the executable path
        self.visited_states = set()
        self.child_pids = []
        self.last_window_rect = None  # (left, top, right, bottom)
        self.client_rect = None  # Client area (without borders/title)
        self.is_installer = is_installer
        self.dpi_scale = self.get_dpi_scale()
        self.last_screenshot_path = None  # Track last screenshot for deduplication
        
        pyautogui.FAILSAFE = False
        
        print(f"🔧 System DPI Scale: {self.dpi_scale}")

    def get_dpi_scale(self):
        """Get the DPI scaling factor"""
        try:
            if sys.platform.startswith('win'):
                user32 = ctypes.windll.user32
                user32.SetProcessDPIAware()
                dpi = user32.GetDpiForSystem()
                return dpi / 96.0  # 96 is the baseline DPI
        except:
            pass
        return 1.0

    def find_best_model(self):
        try:
            models = self.client.models.list()
            names = [m.name for m in models if "flash" in m.name.lower()]
            return names[0] if names else "gemini-1.5-flash"
        except: 
            return "gemini-1.5-flash"

    # --- PROCESS & WINDOW MANAGEMENT ---
    def find_all_process_windows(self, pid):
        """Find ALL windows belonging to process and its children"""
        def callback(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd):
                _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                if found_pid == pid or found_pid in self.child_pids:
                    title = win32gui.GetWindowText(hwnd)
                    if title: 
                        hwnds.append((hwnd, title, found_pid))
            return True
        hwnds = []
        win32gui.EnumWindows(callback, hwnds)
        return hwnds

    def find_windows_by_process_name(self, process_name):
        """Find windows by matching process name (case-insensitive)"""
        def callback(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    proc = psutil.Process(pid)
                    proc_name = proc.name().lower()
                    
                    # Match process name
                    if process_name.lower() in proc_name:
                        title = win32gui.GetWindowText(hwnd)
                        if title:  # Must have a title
                            # Get window rect to check if it's a real window
                            rect = win32gui.GetWindowRect(hwnd)
                            width = rect[2] - rect[0]
                            height = rect[3] - rect[1]
                            
                            # Filter out tiny windows (likely system windows)
                            if width > 100 and height > 100:
                                results.append((hwnd, title, pid, proc_name))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return True
        
        results = []
        win32gui.EnumWindows(callback, results)
        return results

    def update_child_processes(self):
        try:
            parent = psutil.Process(self.app_pid)
            self.child_pids = [child.pid for child in parent.children(recursive=True)]
        except: 
            pass

    def get_window_info(self):
        """Get both window rect and client rect for accurate coordinate mapping"""
        if not self.app_window_handle:
            return None, None
        
        try:
            # Get full window rectangle (includes title bar and borders)
            window_rect = win32gui.GetWindowRect(self.app_window_handle)
            
            # Get client area rectangle (excludes title bar and borders)
            client_rect = win32gui.GetClientRect(self.app_window_handle)
            
            # Convert client rect to screen coordinates
            left, top = win32gui.ClientToScreen(self.app_window_handle, (0, 0))
            right = left + client_rect[2]
            bottom = top + client_rect[3]
            
            client_screen_rect = (left, top, right, bottom)
            
            return window_rect, client_screen_rect
        except:
            return None, None

    def launch_application(self, app_path, app_name):
        print(f"🚀 Launching: {app_path}")
        
        # Extract just the executable name for matching
        exe_name = os.path.basename(app_path).replace('.exe', '')
        
        # 1. Check existing processes first
        print(f"🔍 Searching for existing '{exe_name}' processes...")
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                proc_name = proc.info['name'].replace('.exe', '').lower()
                if exe_name.lower() in proc_name or app_name.lower() in proc_name:
                    self.app_pid = proc.info['pid']
                    print(f"✅ Found existing process: {proc.info['name']} (PID: {self.app_pid})")
                    self.update_child_processes()
                    
                    windows = self.find_all_process_windows(self.app_pid)
                    if windows:
                        self.app_window_handle = windows[0][0]
                        print(f"✅ Found window: '{windows[0][1]}'")
                        win32gui.ShowWindow(self.app_window_handle, win32con.SW_RESTORE)
                        win32gui.SetForegroundWindow(self.app_window_handle)
                        time.sleep(1)
                        return True
        except Exception as e:
            print(f"⚠️ Error checking existing processes: {e}")

        # 2. Launch New Process
        try:
            if sys.platform.startswith('win'):
                print(f"⏳ Starting new process...")
                self.app_process = subprocess.Popen([app_path])
                initial_pid = self.app_process.pid
                print(f"✅ Process started (Initial PID: {initial_pid})")
                
                # Wait for application to initialize
                time.sleep(3)
                
                # Enhanced detection with multiple strategies
                print(f"🔍 Detecting application window (timeout: {WINDOW_DETECT_TIMEOUT}s)...")
                
                for attempt in range(WINDOW_DETECT_TIMEOUT):
                    print(f"   Attempt {attempt + 1}/{WINDOW_DETECT_TIMEOUT}...", end='\r')
                    
                    # Strategy 1: Check original PID
                    self.update_child_processes()
                    windows = self.find_all_process_windows(initial_pid)
                    
                    # Strategy 2: Search by process name (handles launcher scenarios)
                    if not windows:
                        windows = self.find_windows_by_process_name(exe_name)
                        if windows:
                            # Update PID to actual process
                            self.app_pid = windows[0][2]
                            print(f"\n✅ Found via process name: '{windows[0][1]}' (PID: {self.app_pid})")
                    
                    # Strategy 3: Search by app_name if different from exe_name
                    if not windows and app_name.lower() != exe_name.lower():
                        windows = self.find_windows_by_process_name(app_name)
                        if windows:
                            self.app_pid = windows[0][2]
                            print(f"\n✅ Found via app name: '{windows[0][1]}' (PID: {self.app_pid})")
                    
                    # Filter and select best window
                    if windows:
                        # Remove system windows
                        valid_windows = [w for w in windows 
                                       if "program manager" not in w[1].lower() 
                                       and "task switching" not in w[1].lower()]
                        
                        if valid_windows:
                            # Prefer windows with meaningful titles
                            best_window = None
                            for w in valid_windows:
                                title = w[1].lower()
                                # Prefer windows with app name in title
                                if app_name.lower() in title or exe_name.lower() in title:
                                    best_window = w
                                    break
                            
                            if not best_window:
                                best_window = valid_windows[0]
                            
                            self.app_window_handle = best_window[0]
                            self.app_pid = best_window[2]
                            
                            print(f"\n✅ Window detected: '{best_window[1]}'")
                            print(f"   Process: {best_window[3] if len(best_window) > 3 else 'N/A'} (PID: {self.app_pid})")
                            
                            # Bring window to front
                            time.sleep(1)
                            win32gui.ShowWindow(self.app_window_handle, win32con.SW_RESTORE)
                            win32gui.SetForegroundWindow(self.app_window_handle)
                            time.sleep(0.5)
                            
                            # Verify window is still valid
                            if win32gui.IsWindow(self.app_window_handle):
                                return True
                            else:
                                print("⚠️ Window handle became invalid, retrying...")
                                self.app_window_handle = None
                    
                    time.sleep(1)
                
                print(f"\n❌ No valid window found after {WINDOW_DETECT_TIMEOUT} seconds")
                print("💡 Tip: The application may need more time to start, or it may be running in the background.")
                
                # Final attempt: list all visible windows for debugging
                print("\n📋 Currently visible windows:")
                all_windows = self.find_windows_by_process_name("")  # Get all
                for w in all_windows[:10]:  # Show first 10
                    print(f"   - {w[1][:60]} (PID: {w[2]})")
                
                return False
                
        except Exception as e:
            print(f"✗ Launch failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def activate_window(self):
        if self.app_window_handle:
            try:
                win32gui.ShowWindow(self.app_window_handle, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self.app_window_handle)
                time.sleep(0.3)
            except: 
                pass

    def capture_window_screenshot(self):
        """Capture ONLY the client area (content without title bar/borders)"""
        self.activate_window()
        
        window_rect, client_rect = self.get_window_info()
        
        if not client_rect:
            print("⚠️ Window lost, using full screen")
            return pyautogui.screenshot()
        
        # Store both for coordinate calculations
        self.last_window_rect = window_rect
        self.client_rect = client_rect
        
        left, top, right, bottom = client_rect
        
        # Guard against zero-width
        if (right - left) < 10:
            return pyautogui.screenshot()

        try:
            img = ImageGrab.grab(bbox=(left, top, right, bottom))
            
            # Debug info
            if CALIBRATION_MODE:
                print(f"📐 Window Rect: {window_rect}")
                print(f"📐 Client Rect: {client_rect}")
                print(f"📐 Image Size: {img.size}")
            
            return img
        except Exception as e:
            print(f"Screenshot error: {e}")
            return pyautogui.screenshot()

    def sanitize_filename(self, name):
        """Remove invalid characters from filename"""
        # Windows invalid characters: < > : " / \ | ? *
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        # Also replace multiple underscores with single
        while '__' in name:
            name = name.replace('__', '_')
        # Remove leading/trailing underscores and spaces
        name = name.strip('_ ')
        # Limit length
        if len(name) > 100:
            name = name[:100]
        return name
    
    def capture(self, name, description):
        """Take screenshot and save metadata (with deduplication)"""
        # Sanitize the name to ensure valid filename
        safe_name = self.sanitize_filename(name)
        
        # Ensure we have a valid name
        if not safe_name or safe_name == '':
            safe_name = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        filename = f"{safe_name}.png"
        path = self.output_base / filename
        
        # Handle potential filename conflicts
        counter = 1
        while path.exists():
            filename = f"{safe_name}_{counter}.png"
            path = self.output_base / filename
            counter += 1
        
        try:
            img = self.capture_window_screenshot()
            
            # Save to temporary path for comparison
            temp_path = self.output_base / f"temp_{datetime.now().strftime('%H%M%S%f')}.png"
            img.save(temp_path)
            
            # Check for duplicate screenshot (98% similarity threshold)
            if self.last_screenshot_path and os.path.exists(self.last_screenshot_path):
                similarity = self.compare_screenshots(self.last_screenshot_path, str(temp_path))
                
                if similarity >= 0.98:
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
                'name': safe_name, 
                'description': description, 
                'filename': filename, 
                'path': str(path)
            })
            print(f"📸 Captured: {description}")
            return str(path)
        except Exception as e:
            print(f"⚠️ Error saving screenshot: {e}")
            # Try with timestamp fallback
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            fallback_name = f"error_{timestamp}.png"
            fallback_path = self.output_base / fallback_name
            try:
                img.save(fallback_path)
                print(f"📸 Saved with fallback name: {fallback_name}")
                self.last_screenshot_path = str(fallback_path)
                return str(fallback_path)
            except:
                print(f"❌ Failed to save screenshot completely")
                return None

    def get_screen_hash(self, img_path=None, img_obj=None):
        # Robust hash for detecting visual changes
        if img_obj:
            img = img_obj
        elif img_path:
            img = Image.open(img_path)
        else:
            return None
        
        # Use perceptual hash
        img_small = img.resize((16, 16), Image.Resampling.LANCZOS).convert('L')
        import numpy as np
        pixels = np.array(img_small).flatten()
        avg = pixels.mean()
        return ''.join('1' if p > avg else '0' for p in pixels)
    
    def compare_screenshots(self, img1_path, img2_path, threshold=0.98):
        """
        Compare two screenshots using simple pixel difference.
        Returns similarity score (0.0 to 1.0).
        """
        try:
            img1 = Image.open(img1_path).convert('RGB')
            img2 = Image.open(img2_path).convert('RGB')
            
            # Resize to same dimensions if different
            if img1.size != img2.size:
                img2 = img2.resize(img1.size)
            
            # Calculate pixel difference
            diff = ImageChops.difference(img1, img2)
            
            # Convert to grayscale and get statistics
            diff_gray = diff.convert('L')
            stat = diff_gray.getextrema()
            
            # Calculate similarity (inverse of difference)
            max_diff = 255
            avg_diff = sum(diff_gray.getdata()) / (diff_gray.size[0] * diff_gray.size[1])
            similarity = 1.0 - (avg_diff / max_diff)
            
            print(f"📊 Screenshot similarity: {similarity*100:.1f}%")
            return similarity
            
        except Exception as e:
            print(f"⚠️ Error comparing screenshots: {e}")
            # On error, assume images are different (safe fallback)
            return 0.0

    # --- THE "OFFLINE WATCHER" LOGIC ---
    def wait_for_visual_change(self, start_hash, timeout=WATCHER_TIMEOUT):
        """
        Dynamically watches the screen for changes.
        Returns: (True, new_image_path) if changed, (False, None) if not.
        """
        print(f"   👀 Watching for screen changes ({timeout}s)...")
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            time.sleep(0.5)  # Poll interval
            
            # Capture current state directly
            current_img = self.capture_window_screenshot()
            current_hash = self.get_screen_hash(img_obj=current_img)
            
            if current_hash != start_hash:
                print("   ✨ Visual change detected!")
                # Save this new state immediately
                timestamp = datetime.now().strftime("%H%M%S")
                temp_path = self.output_base / f"temp_changed_{timestamp}.png"
                current_img.save(temp_path)
                return True, str(temp_path)
                
        print("   💤 No change detected.")
        return False, None

    # --- AI ANALYSIS ---
    def analyze_clickable_elements(self, screenshot_path):
        """Use Gemini Vision to detect buttons with PIXEL COORDINATES"""
        print("🔍 Analyzing UI elements with AI...")
        img = Image.open(screenshot_path)
        w, h = img.size
        
        prompt = f"""Analyze this {w}x{h} application window screenshot (CLIENT AREA ONLY - no title bar or borders).

Identify ALL clickable UI elements (buttons, menu items, tabs, checkboxes, input fields, icons).

INCLUDE ALL:
- Buttons with text labels
- Menu items
- Toolbar buttons and icons
- Tabs, checkboxes, input fields
- All visible clickable elements

EXCLUDE ONLY:
- Window control buttons (X, minimize, maximize) in top-right corner

COORDINATE INSTRUCTIONS:
1. Provide EXACT pixel coordinates (pixel_x, pixel_y) relative to the TOP-LEFT (0,0) of THIS image
2. pixel_x is horizontal position (0 = left edge, {w} = right edge)
3. pixel_y is vertical position (0 = top edge, {h} = bottom edge)
4. Measure to the CENTER of each clickable element
5. Be PRECISE - accuracy is critical

Return ONLY valid JSON array:
[
  {{"type": "button", "label": "Save", "pixel_x": 500, "pixel_y": 100, "purpose": "Save current file"}},
  {{"type": "menu", "label": "File", "pixel_x": 35, "pixel_y": 8, "purpose": "Open file menu"}},
  {{"type": "icon", "label": "Delete", "pixel_x": 224, "pixel_y": 795, "purpose": "Delete selected object"}}
]

Include ALL visible clickable elements."""
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[prompt, img]
            )
            text = response.text.replace("```json", "").replace("```", "").strip()
            elements = json.loads(text)
            
            if CALIBRATION_MODE:
                print(f"🔍 Found {len(elements)} elements")
                for elem in elements[:3]:  # Show first 3
                    print(f"  - {elem.get('label')}: ({elem.get('pixel_x')}, {elem.get('pixel_y')})")
            
            return elements
        except Exception as e:
            print(f"⚠️ Analysis failed: {e}")
            return []

    def is_safe_to_click(self, element):
        """Enhanced safety filter - blocks dangerous buttons and empty areas, allows legitimate UI"""
        label = element.get('label', '').lower().strip()
        purpose = element.get('purpose', '').lower().strip()
        elem_type = element.get('type', '').lower()
        
        # Skip truly empty labels
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
        
        # Block clearly dangerous buttons
        danger_words = ['close', 'exit', 'quit', 'shut down', 'log out', 'shutdown']
        danger_symbols = ['×', '✕', '✖', '☒']  # Common close symbols
        
        # Check for danger words in label and purpose
        for word in danger_words:
            if word == label or word in purpose:  # Exact match for label or substring in purpose
                print(f"   🚫 Blocked dangerous button: '{element.get('label', 'N/A')}' (reason: {word})")
                return False
        
        # Check for close symbols
        for symbol in danger_symbols:
            if symbol in label:
                print(f"   🚫 Blocked close symbol: '{label}'")
                return False
        
        # Position-based filtering
        pixel_x = element.get('pixel_x', 0)
        pixel_y = element.get('pixel_y', 0)
        
        # Block top-right corner (window controls)
        if pixel_x > 0 and pixel_y > 0:
            if pixel_y < 40 and pixel_x > 1700:  # Very top-right for typical screens
                print(f"   ⚠️ Skipping likely window control: '{label}' at ({pixel_x}, {pixel_y})")
                return False
        
        # Block suspicious center/middle clicks UNLESS it's a recognized UI element
        # Center region is roughly 40% of screen centered
        img_width = 1920  # Typical screenshot width
        img_height = 1080  # Typical screenshot height
        
        center_x_min = img_width * 0.3
        center_x_max = img_width * 0.7
        center_y_min = img_height * 0.3
        center_y_max = img_height * 0.7
        
        in_center_region = (center_x_min < pixel_x < center_x_max and 
                           center_y_min < pixel_y < center_y_max)
        
        if in_center_region:
            # Only allow center clicks for clear UI elements with good labels
            if elem_type not in recognized_ui_types:
                # Must have a clear, specific label (length >= 3)
                if len(label) < 3:
                    print(f"   ⚠️ Skipping center area with short label: '{label}' at ({pixel_x}, {pixel_y})")
                    return False
                
                # Block if label suggests it's a workspace area
                workspace_keywords = ['view', 'workspace', 'canvas', '3d', 'viewport', 'scene']
                if any(keyword in label for keyword in workspace_keywords):
                    print(f"   ⚠️ Skipping workspace area: '{label}'")
                    return False
        
        # Default: allow the click
        return True

    def get_click_coordinates(self, element):
        """
        Convert Image Coordinates -> Screen Coordinates
        CRITICAL: We captured the CLIENT AREA, so coordinates are already relative to content area
        """
        if not self.client_rect:
            return None
        
        # Client rect is the actual screenshot area
        client_left, client_top, client_right, client_bottom = self.client_rect
        
        # Get coordinates from AI (relative to image top-left)
        px = element.get('pixel_x', 0)
        py = element.get('pixel_y', 0)
        
        # Convert to screen coordinates:
        # Screen = ClientTopLeft + ImageCoordinate + ManualAdjustments
        screen_x = client_left + px + MANUAL_X_OFFSET
        screen_y = client_top + py + MANUAL_Y_OFFSET
        
        if CALIBRATION_MODE:
            label = element.get('label', 'unknown')
            print(f"🎯 Calculating click for '{label}':")
            print(f"   Image coords: ({px}, {py})")
            print(f"   Client area: {self.client_rect}")
            print(f"   Screen coords: ({screen_x}, {screen_y})")
        
        return (int(screen_x), int(screen_y))

    def visualize_click_target(self, element, coords):
        """Draw a marker on the screenshot to verify click position"""
        if not CALIBRATION_MODE:
            return
        
        try:
            img = self.capture_window_screenshot()
            draw = ImageDraw.Draw(img)
            
            px = element.get('pixel_x', 0)
            py = element.get('pixel_y', 0)
            
            # Draw crosshair
            size = 10
            draw.line([(px-size, py), (px+size, py)], fill='red', width=2)
            draw.line([(px, py-size), (px, py+size)], fill='red', width=2)
            draw.ellipse([(px-3, py-3), (px+3, py+3)], fill='red')
            
            # Save
            timestamp = datetime.now().strftime("%H%M%S")
            debug_path = self.output_base / f"debug_target_{timestamp}.png"
            img.save(debug_path)
            print(f"   🐛 Debug image saved: {debug_path}")
        except Exception as e:
            print(f"   ⚠️ Visualization failed: {e}")

    # --- MAIN RECURSIVE LOGIC ---
    def explore_app_intelligently(self, max_depth=2, max_screenshots=30):
        print("\n=== STARTING INTELLIGENT EXPLORATION ===")
        
        # Initial Capture
        start_path = self.capture("000_start", "Application Start")
        start_hash = self.get_screen_hash(start_path)
        self.visited_states.add(start_hash)
        
        self._explore_recursive(start_path, 0, max_depth, 1, max_screenshots)

    def _explore_recursive(self, current_img_path, depth, max_depth, shot_count, max_shots):
        if depth >= max_depth or shot_count >= max_shots: 
            return shot_count
        
        # 1. Analyze
        elements = self.analyze_clickable_elements(current_img_path)
        safe_elements = [e for e in elements if self.is_safe_to_click(e)]
        
        print(f"{'  '*depth}Found {len(safe_elements)} clickable elements.")
        
        for idx, elem in enumerate(safe_elements):
            if shot_count >= max_shots: 
                break
            
            label = elem.get('label', 'unknown')
            print(f"\n{'  '*depth}👉 [{idx+1}/{len(safe_elements)}] Target: {label}")
            
            # 2. Prepare Click
            coords = self.get_click_coordinates(elem)
            if not coords: 
                continue
            
            # Visualize in calibration mode
            if CALIBRATION_MODE:
                self.visualize_click_target(elem, coords)
            
            # Capture hash BEFORE click for comparison
            pre_click_img = self.capture_window_screenshot()
            pre_hash = self.get_screen_hash(img_obj=pre_click_img)
            
            # 3. Click with improved accuracy
            print(f"{'  '*depth}   🖱️  Moving to ({coords[0]}, {coords[1]})...")
            
            # Hover before clicking to ensure element is interactive
            pyautogui.moveTo(coords[0], coords[1], duration=0.5)
            time.sleep(0.3)  # Hover pause - allows tooltips/hover states
            
            # Perform click
            pyautogui.click()
            print(f"{'  '*depth}   ✅ Click performed")
            
            # 4. WATCHER: Wait for visual change
            changed, new_img_path = self.wait_for_visual_change(pre_hash)
            
            # 5. Verify click and retry if needed
            if not changed:
                print(f"{'  '*depth}   ⚠️ No change detected. Retrying click...")
                
                # Retry with slight offset adjustments
                retry_succeeded = False
                for retry_attempt in range(2):
                    offsets = [(0, -2), (2, 0), (0, 2), (-2, 0)]  # Try nearby pixels
                    offset_x, offset_y = offsets[retry_attempt % len(offsets)]
                    
                    retry_x = coords[0] + offset_x
                    retry_y = coords[1] + offset_y
                    
                    print(f"{'  '*depth}      Retry {retry_attempt+1}: ({retry_x}, {retry_y})")
                    pyautogui.moveTo(retry_x, retry_y, duration=0.3)
                    time.sleep(0.2)
                    pyautogui.click()
                    
                    # Check again
                    changed, new_img_path = self.wait_for_visual_change(pre_hash, timeout=3)
                    if changed:
                        print(f"{'  '*depth}   ✅ Retry successful!")
                        retry_succeeded = True
                        break
                
                # If all retries failed, skip this element
                if not retry_succeeded and not changed:
                    print(f"{'  '*depth}   ⚠️ Click had no effect after retries. Skipping.")
                    continue
            
            if changed:
                print(f"{'  '*depth}   ✅ Click successful (State changed)")
                
                # Check if this is a new unique state
                new_hash = self.get_screen_hash(new_img_path)
                
                # Save permanent screenshot
                shot_name = f"{shot_count:03d}_click_{self.sanitize_filename(label[:15])}"
                final_path = self.capture(shot_name, f"Clicked {label}")
                
                if not final_path:
                    print(f"{'  '*depth}   ⚠️ Failed to save screenshot, skipping.")
                    continue
                    
                shot_count += 1
                
                if new_hash not in self.visited_states:
                    self.visited_states.add(new_hash)
                    
                    # Recurse deeper!
                    print(f"{'  '*depth}   ✨ New state! Exploring deeper...")
                    shot_count = self._explore_recursive(final_path, depth+1, max_depth, shot_count, max_shots)
                    
                    # Backtrack
                    print(f"{'  '*depth}   🔙 Backtracking...")
                    pyautogui.press('escape')
                    time.sleep(1)
                else:
                    print(f"{'  '*depth}   🔄 State already visited.")
                    pyautogui.press('escape')
                    time.sleep(0.5)
            else:
                print(f"{'  '*depth}   ⚠️ Click had no effect (or timeout). Skipping.")
        
        return shot_count

    # --- DOCUMENTATION GENERATION ---
    def generate_doc(self, app_name, app_desc, notes):
        if not self.screenshots: 
            return None
        print(f"\n📝 Generating Documentation for {app_name}...")
        
        image_list = "\n".join([f"- {s['filename']}: {s['description']}" for s in self.screenshots])
        
        prompt = f"""Create a comprehensive User Manual for '{app_name}'.

Application Context: {app_desc}
Additional Notes: {notes}

Use these screenshots to explain features step-by-step:
{image_list}

Format Requirements:
- Use Markdown with proper headings (# ## ###)
- Include images using: ![Description](filename)
- Organize into logical sections (Getting Started, Features, Tips)
- Be clear and beginner-friendly
"""
        
        try:
            contents = [prompt] + [Image.open(s['path']) for s in self.screenshots]
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=contents
            )
            return response.text
        except Exception as e:
            print(f"Doc Gen Error: {e}")
            return None

    def save_results(self, app_name, version, content):
        target_dir = self.output_base / app_name.replace(" ", "_") / version
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Save Markdown
        md_path = target_dir / "USER_MANUAL.md"
        md_path.write_text(content, encoding='utf-8')
        
        # Move Images
        for s in self.screenshots:
            dest = target_dir / s['filename']
            try: 
                os.replace(s['path'], dest)
            except: 
                pass
            
        # Generate PDF using xhtml2pdf with embedded screenshots
        try:
            if 'PDF_AVAILABLE' in globals() and PDF_AVAILABLE:
                import re
                import base64
                from io import BytesIO
                
                print("  📄 Creating PDF with embedded screenshots...")
                
                # Clean content - remove internal links
                clean_content = content
                
                # Remove manual TOC if present
                lines = clean_content.split('\n')
                filtered_lines = []
                skip_toc = False
                for line in lines:
                    if "table of contents" in line.lower() and (line.startswith('#') or line.startswith('**')):
                        skip_toc = True
                        continue
                    if skip_toc:
                        if line.strip() == "" or line.strip().startswith('-') or line.strip().startswith('*') or re.match(r'^\d+\.', line.strip()):
                            continue
                        else:
                            skip_toc = False
                    filtered_lines.append(line)
                clean_content = '\n'.join(filtered_lines)
                
                # Remove internal anchor links [text](#anchor)
                clean_content = re.sub(r'\[([^\]]+)\]\(#[^\)]+\)', r'\1', clean_content)
                
                # Convert markdown to HTML
                html_content = markdown(clean_content)
                
                # Replace image references with base64 data URIs
                for s in self.screenshots:
                    # Check if image exists in target directory
                    img_file = target_dir / s['filename']
                    if img_file.exists():
                        # Read image and convert to base64
                        with open(img_file, 'rb') as f:
                            img_data = f.read()
                            img_base64 = base64.b64encode(img_data).decode('utf-8')
                            
                        # Replace in HTML: <img src="filename" ... /> with base64 data URI
                        html_content = html_content.replace(
                            f'src="{s["filename"]}"',
                            f'src="data:image/png;base64,{img_base64}"'
                        )
                        html_content = html_content.replace(
                            f"src='{s['filename']}'",
                            f'src="data:image/png;base64,{img_base64}"'
                        )
                
                # Add styling for better PDF appearance
                styled_html = f"""
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        @page {{
                            size: A4;
                            margin: 2cm;
                        }}
                        body {{
                            font-family: Arial, 'Helvetica Neue', sans-serif;
                            font-size: 11pt;
                            line-height: 1.6;
                            color: #333;
                        }}
                        h1 {{
                            color: #2c3e50;
                            font-size: 24pt;
                            margin-top: 20pt;
                            margin-bottom: 10pt;
                            page-break-after: avoid;
                        }}
                        h2 {{
                            color: #34495e;
                            font-size: 18pt;
                            margin-top: 15pt;
                            margin-bottom: 8pt;
                            page-break-after: avoid;
                        }}
                        h3 {{
                            color: #555;
                            font-size: 14pt;
                            margin-top: 12pt;
                            margin-bottom: 6pt;
                        }}
                        img {{
                            max-width: 100%;
                            height: auto;
                            display: block;
                            margin: 10pt auto;
                            border: 1px solid #ddd;
                            padding: 5pt;
                        }}
                        code {{
                            background-color: #f4f4f4;
                            padding: 2pt 4pt;
                            font-family: 'Courier New', monospace;
                            font-size: 10pt;
                        }}
                        pre {{
                            background-color: #f4f4f4;
                            padding: 10pt;
                            border-left: 3pt solid #2c3e50;
                            overflow-x: auto;
                            font-size: 9pt;
                        }}
                        p {{
                            margin: 8pt 0;
                            text-align: justify;
                        }}
                        ul, ol {{
                            margin: 8pt 0;
                            padding-left: 20pt;
                        }}
                        li {{
                            margin: 4pt 0;
                        }}
                    </style>
                </head>
                <body>
                    {html_content}
                </body>
                </html>
                """
                
                # Generate PDF
                pdf_path = target_dir / "USER_MANUAL.pdf"
                with open(pdf_path, "wb") as pdf_file:
                    pisa_status = pisa.CreatePDF(styled_html, dest=pdf_file)
                
                if pisa_status.err:
                    print(f"⚠️ PDF generation had errors")
                    return str(md_path), None
                else:
                    print(f"✅ PDF Saved with embedded screenshots: {pdf_path}")
                    return str(md_path), str(pdf_path)
            else:
                print("⚠️  Skipping PDF generation (xhtml2pdf not available)")
                return str(md_path), None
                
        except Exception as e:
            print(f"❌ PDF generation failed: {e}")
            import traceback
            traceback.print_exc()
            return str(md_path), None

# --- CALIBRATION HELPER ---
def run_calibration_test(explorer):
    """Interactive calibration mode to test click accuracy"""
    print("\n" + "="*60)
    print("🎯 CALIBRATION MODE")
    print("="*60)
    print("This will help you verify click accuracy.")
    print("The mouse will move to detected elements without clicking.")
    print("Press Ctrl+C to exit at any time.")
    print("="*60 + "\n")
    
    input("Press Enter when the application window is visible...")
    
    # Capture current state
    img_path = explorer.capture("calibration_test", "Calibration Screenshot")
    
    # Analyze elements
    elements = explorer.analyze_clickable_elements(img_path)
    
    if not elements:
        print("❌ No elements detected!")
        return
    
    print(f"\n✅ Found {len(elements)} elements\n")
    
    for i, elem in enumerate(elements):
        label = elem.get('label', 'unknown')
        coords = explorer.get_click_coordinates(elem)
        
        if not coords:
            continue
        
        print(f"[{i+1}/{len(elements)}] Testing: {label}")
        print(f"  Moving to: {coords}")
        
        # Visualize
        explorer.visualize_click_target(elem, coords)
        
        # Move mouse slowly
        pyautogui.moveTo(coords[0], coords[1], duration=1.0)
        time.sleep(2)
        
        response = input("  Was this correct? (y/n/skip/quit): ").lower()
        
        if response == 'quit' or response == 'q':
            break
        elif response == 'skip' or response == 's':
            continue

# --- RUNNER ---
if __name__ == "__main__":
    # --- CONFIGURATION INPUT ---
    # Default configuration with all required fields
    default_config = {
        "api_key": "YOUR_API_KEY_HERE",
        "app_path": r"C:\Users\revor\AppData\Local\GitHubDesktop\GitHubDesktop.exe",
        "app_name": "GitHub Desktop",
        "version": "1.0",
        "description": "Git version control GUI application",
        "max_depth": 2,
        "max_screenshots": 30
    }
    
    # Load from file if provided
    if len(sys.argv) > 1:
        try:
            with open(sys.argv[1], 'r') as f: 
                user_config = json.load(f)
                # Merge user config with defaults (user config takes precedence)
                config = {**default_config, **user_config}
        except Exception as e:
            print(f"⚠️ Error loading config file: {e}")
            print("Using default configuration...")
            config = default_config
    else:
        config = default_config
    
    # Validate required fields
    required_fields = ['api_key', 'app_path', 'app_name']
    missing_fields = [field for field in required_fields if not config.get(field) or config.get(field) == "YOUR_API_KEY_HERE"]
    
    if missing_fields:
        print(f"❌ Error: Missing required configuration fields: {', '.join(missing_fields)}")
        print("\nPlease provide a config.json file with at least:")
        print(json.dumps({
            "api_key": "your_google_gemini_api_key",
            "app_path": "C:\\Path\\To\\Application.exe",
            "app_name": "ApplicationName"
        }, indent=2))
        sys.exit(1)
    
    # Check for calibration mode
    if len(sys.argv) > 2 and sys.argv[2] == "--calibrate":
        CALIBRATION_MODE = True
    
    # Initialize
    explorer = SmartGUIExplorer(config['api_key'])
    
    if explorer.launch_application(config['app_path'], config['app_name']):
        
        if CALIBRATION_MODE:
            run_calibration_test(explorer)
        else:
            # Run Exploration
            explorer.explore_app_intelligently(
                max_depth=config.get('max_depth', 2),
                max_screenshots=config.get('max_screenshots', 30)
            )
            
            # Generate Docs
            doc_content = explorer.generate_doc(
                config.get('app_name', 'Application'), 
                config.get('description', 'Software Application'), 
                config.get('notes', '')
            )
            
            if doc_content:
                md, pdf = explorer.save_results(
                    config.get('app_name', 'Application'), 
                    config.get('version', '1.0'), 
                    doc_content
                )
                
                # Save to DB
                db = DocumentationDB()
                db.add_documentation(
                    config.get('app_name', 'Application'), 
                    config.get('version', '1.0'), 
                    config.get('description', 'Software Application'),
                    "documentation", 
                    md, 
                    pdf, 
                    len(explorer.screenshots)
                )
                print("\n🎉 Process Complete!")
            else:
                print("❌ Failed to generate documentation content.")
    else:
        print("❌ Could not launch application.")