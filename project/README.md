# GUI Agent v2.0 - Automated Documentation Engine

This project provides a web-based interface to automatically explore GUI applications and generate documentation using AI.

## Files

- `sever.py` - FastAPI server that hosts the web interface and handles WebSocket connections
- `index.html` - Web dashboard for configuring and launching the documentation agent
- `agent_worker.py` - Core logic for GUI exploration using AI vision and automation

## Prerequisites

Install required Python packages:
```bash
pip install fastapi uvicorn websockets google-genai pyautogui Pillow markdown-pdf psutil pywin32
```

## How to Run

1. **Start the server:**
   ```bash
   python sever.py
   ```
   The server will start on `http://localhost:8000`

2. **Open the web interface:**
   - Navigate to `http://localhost:8000` in your browser
   - Fill in the required fields:
     - **Gemini API Key**: Your Google Gemini API key
     - **App Executable Path**: Full path to the .exe file you want to document
     - **App Name**: Name of the application (as shown in title bar)

3. **Click "RUN WITH ADMIN":**
   - This will trigger a UAC prompt to run the agent with admin privileges
   - The agent will launch the application, explore its GUI, and generate documentation
   - Progress will be shown in the terminal output on the dashboard

## Issues Fixed

✅ **Fixed `run_agent` function** - Now properly initializes SmartGUIExplorer and runs the full exploration workflow
✅ **Installed dependencies** - Added all required packages (fastapi, uvicorn, websockets)
✅ **Port handling** - Server configured to run on port 8000

## Note on Filename

The server file is named `sever.py` (note the typo). You may want to rename it to `server.py` for clarity, but you'll also need to update how you run it.

## How It Works

1. The web interface sends configuration via WebSocket to the server
2. Server launches `agent_worker.py` as an admin process using PowerShell
3. Agent worker:
   - Launches the target application
   - Uses AI vision to detect clickable UI elements
   - Automatically explores the interface
   - Takes screenshots of different states
   - Generates comprehensive documentation using Gemini AI
4. Documentation is saved as both Markdown and PDF in the `documentation/` folder
