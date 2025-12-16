import argparse
import os
import sys
from pathlib import Path
from autodoc_engine import AutoDocEngine

def main():
    parser = argparse.ArgumentParser(description="AutoDoc: Automated Documentation Generator")
    parser.add_argument("--url", required=True, help="URL of the web application to document")
    parser.add_argument("--project-name", required=True, help="Name of the project")
    parser.add_argument("--output-dir", default="output", help="Directory to save output")
    parser.add_argument("--max-screenshots", type=int, default=5, help="Maximum number of screenshots to capture")
    
    args = parser.parse_args()
    
    # Get API key from env
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("WARNING: GEMINI_API_KEY not found in environment variables.")
    
    try:
        engine = AutoDocEngine(
            project_name=args.project_name,
            output_dir=args.output_dir,
            gemini_api_key=api_key
        )
        
        print(f"Starting AutoDoc for {args.project_name} at {args.url}...")
        screenshots = engine.run_web_exploration(args.url, max_screenshots=args.max_screenshots)
        
        print(f"Captured {len(screenshots)} screenshots.")
        engine.generate_report(screenshots)
        print("Done!")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
