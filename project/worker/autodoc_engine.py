"""
AutoDoc Engine
Extracted and refactored from Advanced Backend.ipynb
"""
import os
import json
import time
import base64
import re
import traceback
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging
import cv2
import numpy as np
from PIL import Image
import pyautogui

# Desktop Window Management
try:
    import pygetwindow as gw
except ImportError:
    gw = None

# Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException,
    WebDriverException,
    TimeoutException,
    NoSuchElementException
)

# ReportLab (PDF Generation)
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Image as RLImage,
    Spacer, PageBreak, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors

# Word Document (Alternative to PDF)
from docx import Document as DocxDocument
from docx.shared import Inches, Pt, RGBColor

# Gemini
import google.generativeai as genai

# Logging Setup
logger = logging.getLogger(__name__)

class Config:
    SCREENSHOT_DELAY = 2.0
    CHANGE_THRESHOLD = 0.95 # 98% similar = Unchanged
    DUPLICATE_THRESHOLD = 0.80 # 95% similar = Duplicate
    MATCH_CONFIDENCE = 0.70 # 70% match = Same Page
    MAX_SCREENSHOTS = 5 # Increased from 12
   
    # NEW: Advanced settings
    PAGE_LOAD_TIMEOUT = 60
    SCRIPT_TIMEOUT = 30
    SCROLL_PAUSE = 2
    SCROLL_STEP = 800
    ENABLE_SCROLL_CAPTURE = True
   
    # Report formats
    GENERATE_PDF = True
    GENERATE_DOCX = False 
    GENERATE_HTML = True
   
    # Feature flags
    USE_FEATURE_MATCHING = True # Use ORB/SIFT for better matching
    GENERATE_HEATMAPS = False # Visual diff heatmaps
    ENABLE_RESUME = True # Resume from last checkpoint
    # NEW: Prefer full page captures
    PREFER_FULL_PAGE = True

class BrowserManager:
    """Manages browser selection and initialization"""
   
    @staticmethod
    def get_available_browsers():
        """Detect available browsers"""
        browsers = []
       
        # Check Edge
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        if any(Path(p).exists() for p in edge_paths):
            browsers.append("edge")
       
        # Chrome (via webdriver-manager)
        browsers.append("chrome")
       
        return browsers
   
    @staticmethod
    def create_driver(browser="edge"):
        """Create web driver with robust settings"""
        logger.info(f"Initializing {browser} browser...")
       
        if browser == "edge":
            options = EdgeOptions()
        else:
            options = ChromeOptions()
       
        # Common options
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        # Enable CDP for full page screenshots
        options.add_argument("--enable-chrome-browser-cloud-management")
        
        # Headless mode for automation (optional, can be configured)
        # options.add_argument("--headless=new") 
       
        # Create driver
        try:
            if browser == "edge":
                driver = webdriver.Edge(options=options)
            else:
                from webdriver_manager.chrome import ChromeDriverManager
                service = ChromeService(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
           
            driver.set_page_load_timeout(Config.PAGE_LOAD_TIMEOUT)
            driver.set_script_timeout(Config.SCRIPT_TIMEOUT)
           
            logger.info("[OK] Browser initialized")
            return driver
           
        except Exception as e:
            logger.error(f"Failed to initialize {browser}: {e}")
            raise

class DeterministicExplorer:
    """
    IMPROVED: Better element detection and tracking
    """
    def __init__(self):
        self.visited_signatures = set()
        self.avoid_keywords = [
            "logout", "sign out", "delete", "remove",
            "exit", "cancel", "close", "back"
        ]
        self.interaction_log = []

    def get_element_signature(self, element):
        """IMPROVED: More robust signature generation"""
        try:
            text = (element.text.strip() or
                   element.get_attribute("aria-label") or
                   element.get_attribute("name") or
                   element.get_attribute("id") or
                   "element")
           
            loc = element.location
            tag = element.tag_name
           
            # Create a more unique signature
            return f"{tag}_{text[:30]}_{loc['x']}_{loc['y']}"
        except:
            return None

    def is_safe_element(self, element):
        """IMPROVED: Better safety checks"""
        try:
            text = (element.text.strip() or
                   element.get_attribute("aria-label") or
                   element.get_attribute("name") or "").lower()
           
            # Check for dangerous keywords
            if any(bad in text for bad in self.avoid_keywords):
                return False
           
            # Check if element is in a modal/dialog that might be destructive
            if element.get_attribute("role") in ["alertdialog", "dialog"]:
                return False
           
            return True
        except:
            return False

    def get_next_interactive_element(self, driver):
        """
        IMPROVED: Better element selection with multiple strategies
        """
        # Strategy 1: Find all interactive elements
        selectors = [
            "//a[@href]",
            "//button[not(@disabled)]",
            "//input[@type='submit']",
            "//input[@type='button']",
            "//*[@role='button']",
            "//*[@onclick]"
        ]
       
        candidates = []
        for selector in selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                candidates.extend(elements)
            except:
                continue
       
        valid_elements = []
        for el in candidates:
            try:
                if not el.is_displayed() or not el.is_enabled():
                    continue
               
                if not self.is_safe_element(el):
                    continue
               
                sig = self.get_element_signature(el)
                if not sig or sig in self.visited_signatures:
                    continue
               
                loc = el.location
                size = el.size
                text = el.text.strip()[:50] or el.get_attribute("aria-label") or "unlabeled"
               
                valid_elements.append({
                    "element": el,
                    "signature": sig,
                    "text": text,
                    "y": loc['y'],
                    "x": loc['x'],
                    "area": size['width'] * size['height']
                })
            except:
                continue
        if not valid_elements:
            return None, None
       
        # SORT: Top -> Bottom, Left -> Right (Symmetric Exploration)
        # Prioritize larger elements (likely more important)
        valid_elements.sort(key=lambda k: (k['y'] // 100, k['x'] // 100, -k['area']))
        # Get first unvisited element
        for item in valid_elements:
            sig = item['signature']
            if sig not in self.visited_signatures:
                self.visited_signatures.add(sig)
                self.interaction_log.append({
                    "timestamp": time.time(),
                    "signature": sig,
                    "text": item['text']
                })
                return item['element'], item['text']
       
        return None, None

class ScreenshotCapture:
    """
    IMPROVED: Multiple capture strategies with fallbacks
    - FIXED: Prefer full page captures for scrollable content
    """
   
    @staticmethod
    def capture_web_screenshot(driver, path, method="full"):
        """
        IMPROVED: Default to full page capture
        """
        try:
            if method == "full":
                return ScreenshotCapture._full_page_capture(driver, path)
            elif method == "smart":
                # Try full page first if enabled
                if Config.PREFER_FULL_PAGE:
                    success = ScreenshotCapture._full_page_capture(driver, path)
                    if success:
                        return True
                # Fallback to viewport
                driver.save_screenshot(str(path))
                return True
            else:
                # Simple viewport capture
                driver.save_screenshot(str(path))
                return True
               
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            # Fallback to basic screenshot
            try:
                driver.save_screenshot(str(path))
                return True
            except:
                return False
   
    @staticmethod
    def _full_page_capture(driver, path):
        """IMPROVED: Better full-page capture using CDP"""
        try:
            # Get dimensions
            total_height = driver.execute_script("return Math.max(document.body.scrollHeight, document.body.offsetHeight, document.documentElement.clientHeight, document.documentElement.scrollHeight, document.documentElement.offsetHeight);")
            viewport_height = driver.execute_script("return window.innerHeight")
            viewport_width = driver.execute_script("return window.innerWidth")
           
            # If page is short, just take viewport
            if total_height <= viewport_height * 1.2:
                driver.save_screenshot(str(path))
                return True
           
            # For long pages, use CDP
            try:
                # Set device metrics to full page size
                driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
                    "width": viewport_width,
                    "height": total_height,
                    "deviceScaleFactor": 1,
                    "mobile": False
                })
               
                # Capture full screenshot
                res = driver.execute_cdp_cmd("Page.captureScreenshot", {
                    "format": "png",
                    "captureBeyondViewport": True
                })
               
                # Reset metrics
                driver.execute_cdp_cmd("Emulation.clearDeviceMetricsOverride", {})
               
                # Save the full page image
                with open(path, "wb") as f:
                    f.write(base64.b64decode(res['data']))
               
                logger.info(f"[Full Page] Captured full page screenshot: {total_height}px height")
                return True
               
            except Exception as cdp_e:
                logger.warning(f"CDP full capture failed: {cdp_e}, falling back to viewport")
                driver.save_screenshot(str(path))
                return True
               
        except Exception as e:
            logger.error(f"Full page capture failed: {e}")
            return False

class AutoDocEngine:
    def __init__(self, project_name, output_dir, gemini_api_key=None):
        self.project_name = project_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.gemini_api_key = gemini_api_key
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.output_dir / "autodoc.log", encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        # Initialize Gemini
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.model = self._init_gemini()
        else:
            self.model = None
            logger.warning("No Gemini API key provided. AI features will be disabled.")

    def _init_gemini(self):
        models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-pro"]
        for model_name in models:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config={"temperature": 0.2, "max_output_tokens": 1000}
                )
                logger.info(f"[OK] Initialized Gemini model: {model_name}")
                return model
            except Exception as e:
                logger.warning(f"Could not initialize {model_name}: {str(e)[:100]}")
        return None

    def run_web_exploration(self, url, max_screenshots=None):
        if max_screenshots:
            Config.MAX_SCREENSHOTS = max_screenshots
            
        logger.info(f"[Web] Exploring Web App: {url}")
        
        driver = None
        browsers = BrowserManager.get_available_browsers()
        
        for browser in browsers:
            try:
                driver = BrowserManager.create_driver(browser)
                break
            except:
                continue
        
        if not driver:
            raise Exception("Could not initialize any browser")
            
        explorer = DeterministicExplorer()
        screenshots = []
        
        try:
            # Load page
            logger.info("Loading page...")
            driver.get(url)
            time.sleep(3)
            
            # Wait for page to be ready
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                logger.warning("Page load timeout, continuing anyway...")
            
            screenshot_count = 0
            
            # Phase 1: Initial full page capture
            logger.info("Phase 1: Initial full page capture")
            filename = f"screen_{screenshot_count:03d}_initial_full.png"
            path = self.output_dir / filename
            if ScreenshotCapture.capture_web_screenshot(driver, path, "full"):
                screenshots.append(path)
                screenshot_count += 1
                logger.info(f" [Screenshot] {screenshot_count}: Initial full page")
            
            # Phase 2: Interactive exploration
            if screenshot_count < Config.MAX_SCREENSHOTS:
                logger.info("Phase 2: Interactive element exploration with full page captures")
                
                # Scroll back to top
                try:
                    driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(1)
                except:
                    pass
                
                for i in range(Config.MAX_SCREENSHOTS - screenshot_count):
                    element, text = explorer.get_next_interactive_element(driver)
                    
                    if not element:
                        logger.info(" [STOP] No more interactive elements found")
                        break
                    
                    logger.info(f" [Click] '{text}'")
                    
                    try:
                        driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});",
                            element
                        )
                        time.sleep(0.5)
                        element.click()
                        time.sleep(3)
                        
                        # Capture result
                        filename = f"screen_{screenshot_count:03d}_action_{int(time.time())}_full.png"
                        path = self.output_dir / filename
                        
                        if ScreenshotCapture.capture_web_screenshot(driver, path, "full"):
                            screenshots.append(path)
                            screenshot_count += 1
                            logger.info(f" [Screenshot] {screenshot_count}: Full page after clicking '{text}'")
                            
                    except Exception as e:
                        logger.warning(f"Failed to interact with '{text}': {e}")
                        continue
                        
        finally:
            if driver:
                driver.quit()
                
        return screenshots

    def generate_report(self, screenshots):
        # Placeholder for report generation logic from the notebook
        # For now, just logging
        logger.info(f"Generating report for {len(screenshots)} screenshots...")
        # TODO: Implement full PDF/HTML generation logic here
        pass
