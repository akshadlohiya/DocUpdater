"""
Script to extract all text from a PDF and save it to a text file.
This script uses PyMuPDF (fitz) to extract text.
"""

import fitz  # PyMuPDF
import sys
import os


def extract_text_from_pdf(pdf_path, output_folder, output_format="txt"):
    """
    Extract all text from a PDF file and save it to a file.
    
    Args:
        pdf_path (str): Path to the input PDF file
        output_folder (str): Folder path where text file will be saved
        output_format (str): Output format ('txt' or 'md' for markdown)
    """
    try:
        # Create output folder if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"Created output folder: {output_folder}")
        
        # Open the PDF
        pdf_document = fitz.open(pdf_path)
        
        print(f"Processing PDF: {pdf_path}")
        print(f"Total pages: {len(pdf_document)}")
        print(f"Extracting text to: {output_folder}\n")
        
        # Prepare output filename
        pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
        output_filename = f"{pdf_basename}_extracted_text.{output_format}"
        output_path = os.path.join(output_folder, output_filename)
        
        # Extract text from all pages
        all_text = []
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            # Extract text from the page
            text = page.get_text()
            
            if text.strip():
                print(f"Page {page_num + 1}: Extracted {len(text)} characters")
                
                # Add page separator
                if output_format == "md":
                    all_text.append(f"\n## Page {page_num + 1}\n")
                else:
                    all_text.append(f"\n{'='*60}\nPAGE {page_num + 1}\n{'='*60}\n")
                
                all_text.append(text)
            else:
                print(f"Page {page_num + 1}: No text found")
        
        pdf_document.close()
        
        # Save all text to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(''.join(all_text))
        
        print(f"\n{'='*60}")
        print(f"Text extraction complete!")
        print(f"Output file: {output_path}")
        print(f"Total characters: {len(''.join(all_text))}")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"Error processing PDF: {e}")
        sys.exit(1)


def extract_text_by_page(pdf_path, output_folder):
    """
    Extract text from a PDF and save each page as a separate text file.
    
    Args:
        pdf_path (str): Path to the input PDF file
        output_folder (str): Folder path where text files will be saved
    """
    try:
        # Create output folder if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"Created output folder: {output_folder}")
        
        # Open the PDF
        pdf_document = fitz.open(pdf_path)
        
        print(f"Processing PDF: {pdf_path}")
        print(f"Total pages: {len(pdf_document)}")
        print(f"Extracting text to: {output_folder}\n")
        
        pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
        
        pages_with_text = 0
        
        # Extract text from each page
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            # Extract text from the page
            text = page.get_text()
            
            if text.strip():
                # Save to individual file
                output_filename = f"{pdf_basename}_page{page_num + 1}.txt"
                output_path = os.path.join(output_folder, output_filename)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                
                print(f"Page {page_num + 1}: Saved {len(text)} characters to {output_filename}")
                pages_with_text += 1
            else:
                print(f"Page {page_num + 1}: No text found (skipped)")
        
        pdf_document.close()
        
        print(f"\n{'='*60}")
        print(f"Text extraction complete!")
        print(f"Pages with text: {pages_with_text}/{len(pdf_document)}")
        print(f"Files saved to: {output_folder}")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"Error processing PDF: {e}")
        sys.exit(1)


def extract_text_structured(pdf_path, output_folder):
    """
    Extract text with better structure (preserving layout where possible).
    
    Args:
        pdf_path (str): Path to the input PDF file
        output_folder (str): Folder path where text file will be saved
    """
    try:
        # Create output folder if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"Created output folder: {output_folder}")
        
        # Open the PDF
        pdf_document = fitz.open(pdf_path)
        
        print(f"Processing PDF: {pdf_path}")
        print(f"Total pages: {len(pdf_document)}")
        print(f"Extracting structured text to: {output_folder}\n")
        
        # Prepare output filename
        pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
        output_filename = f"{pdf_basename}_structured_text.txt"
        output_path = os.path.join(output_folder, output_filename)
        
        # Extract text from all pages with structure
        all_text = []
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            # Extract text with layout preserved
            text = page.get_text("text")  # You can also use "blocks", "words", or "dict" for more structure
            
            if text.strip():
                print(f"Page {page_num + 1}: Extracted {len(text)} characters")
                
                all_text.append(f"\n{'='*60}\nPAGE {page_num + 1}\n{'='*60}\n")
                all_text.append(text)
            else:
                print(f"Page {page_num + 1}: No text found")
        
        pdf_document.close()
        
        # Save all text to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(''.join(all_text))
        
        print(f"\n{'='*60}")
        print(f"Text extraction complete!")
        print(f"Output file: {output_path}")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"Error processing PDF: {e}")
        sys.exit(1)


def main():
    """
    Main function to handle command line arguments.
    """
    if len(sys.argv) < 3:
        print("Usage: python extract_text_from_pdf.py <pdf_file> <output_folder> [mode]")
        print("\nArguments:")
        print("  pdf_file       : Path to the PDF file")
        print("  output_folder  : Folder where text file(s) will be saved")
        print("  mode           : (Optional) Extraction mode:")
        print("                   'single' - All text in one file (default)")
        print("                   'pages'  - Separate file for each page")
        print("                   'md'     - Single markdown file")
        print("\nExamples:")
        print("  python extract_text_from_pdf.py document.pdf ./text_output")
        print("  python extract_text_from_pdf.py document.pdf ./text_output pages")
        print("  python extract_text_from_pdf.py document.pdf ./text_output md")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_folder = sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) >= 4 else "single"
    
    # Check if input file exists
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file '{pdf_path}' not found!")
        sys.exit(1)
    
    # Extract based on mode
    if mode.lower() == "pages":
        extract_text_by_page(pdf_path, output_folder)
    elif mode.lower() == "md":
        extract_text_from_pdf(pdf_path, output_folder, "md")
    else:
        extract_text_from_pdf(pdf_path, output_folder, "txt")


if __name__ == "__main__":
    main()