import os
from markdown import markdown
from weasyprint import HTML, CSS
import io

# Simulate the content that might be causing the issue
# Gemini likely generates a TOC or links that don't match the headers exactly as markdown-pdf expects
content_with_bad_link = """
# User Manual

## Table of Contents
- [Getting Started](#1-getting-started)
- [Features](#features)

## 1. Getting Started
This is the getting started section.

## Features
This is the features section.
"""

output_dir = "test_output"
os.makedirs(output_dir, exist_ok=True)


def sanitize_for_pdf(content):
    import re
    clean_content = content
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
    return clean_content

try:
    print("Testing with sanitization...")
    clean_md = sanitize_for_pdf(content_with_bad_link)
    html_content = markdown(clean_md)
    HTML(string=html_content).write_pdf(os.path.join(output_dir, "test_success.pdf"))
    print("PDF Generated successfully with sanitization!")
    
    # Also test the aggressive cleanup if first one fails (simulated)
    print("Testing aggressive cleanup...")
    aggressive_content = re.sub(r'\[([^\]]+)\](#[^\)]+\)', r'\1', content_with_bad_link)
    html_content = markdown(aggressive_content)
    HTML(string=html_content).write_pdf(os.path.join(output_dir, "test_aggressive.pdf"))
    print("Aggressive cleanup also worked!")
    
except Exception as e:
    print(f"Failed: {e}")
