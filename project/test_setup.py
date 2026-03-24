"""
Quick Test Script - Verify your setup is working
"""
import subprocess
import time
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

print("=" * 60)
print("GUI AGENT v2.0 - SETUP VERIFICATION")
print("=" * 60)

# Test 1: Check if required packages are installed
print("\n[1/4] Checking Python packages...")
required = ["fastapi", "uvicorn", "websockets", "google.genai", "pyautogui", "PIL", "psutil"]
missing = []

for package in required:
    try:
        if package == "google.genai":
            __import__("google.genai")
        elif package == "PIL":
            __import__("PIL")
        else:
            __import__(package)
        print(f"  [OK] {package}")
    except ImportError:
        print(f"  [FAIL] {package} - MISSING")
        missing.append(package)

if missing:
    print(f"\n[WARNING] Missing packages: {', '.join(missing)}")
    print("Install with: pip install fastapi uvicorn websockets google-genai pyautogui Pillow psutil")
else:
    print("\n[OK] All packages installed!")

# Test 2: Check if server is running
print("\n[2/4] Checking if server is running on port 8000...")
result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
if ":8000" in result.stdout and "LISTENING" in result.stdout:
    print("  [OK] Server is already running on port 8000")
    server_running = True
else:
    print("  [INFO] Server is not running. Start it with: python sever.py")
    server_running = False

# Test 3: Check files
print("\n[3/4] Checking project files...")
import os
files = {
    "sever.py": "FastAPI server",
    "index.html": "Web interface",
    "agent_worker.py": "AI agent logic"
}

for file, desc in files.items():
    if os.path.exists(file):
        print(f"  [OK] {file} ({desc})")
    else:
        print(f"  [FAIL] {file} - MISSING")

# Test 4: Try to access the web interface
if server_running:
    print("\n[4/4] Testing web interface...")
    try:
        import urllib.request
        response = urllib.request.urlopen("http://localhost:8000", timeout=2)
        if response.status == 200:
            print("  [OK] Web interface accessible at http://localhost:8000")
        else:
            print(f"  [WARNING] Unexpected response: {response.status}")
    except Exception as e:
        print(f"  [FAIL] Could not access interface: {e}")
else:
    print("\n[4/4] Skipping web interface test (server not running)")

# Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

if not missing and server_running:
    print("\n[SUCCESS] Everything is ready!")
    print("\nNext steps:")
    print("  1. Open http://localhost:8000 in your browser")
    print("  2. Enter your Gemini API key")
    print("  3. Specify the application path and name")
    print("  4. Click 'RUN WITH ADMIN' to start exploration")
elif not missing:
    print("\n[OK] Setup is complete!")
    print("\nTo start the server:")
    print("  python sever.py")
    print("\n  Then open http://localhost:8000")
else:
    print("\n[WARNING] Some dependencies are missing")
    print("  Run: pip install " + " ".join(missing))

print("\n" + "=" * 60)
