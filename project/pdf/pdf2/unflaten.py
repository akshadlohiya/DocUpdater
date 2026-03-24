"""
Script to unflatten a PDF by extracting images and text, then reconstructing
them into a new PDF with selectable text and embedded images.
This script uses PyMuPDF (fitz) and ReportLab.
"""

import fitz  # PyMuPDF
import sys
import os
from PIL import Image
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def unflatten_pdf(input_pdf_path, output_pdf_path, temp_folder="./temp_unflatten"):
    """
    Unflatten a PDF by extracting text and images, then reconstructing
    them into a new PDF with selectable text.
    
    Args:
        input_pdf_path (str): Path to the input flattened PDF
        output_pdf_path (str): Path to save the unflattened PDF
        temp_folder (str): Temporary folder for storing extracted images
    """
    try:
        # Create temp folder if it doesn't exist
        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder)
            print(f"Created temporary folder: {temp_folder}")
        
        # Open the input PDF
        input_doc = fitz.open(input_pdf_path)
        
        print(f"Processing PDF: {input_pdf_path}")
        print(f"Total pages: {len(input_doc)}")
        print(f"Creating unflattened PDF...\n")
        
        # Create output PDF using ReportLab
        c = canvas.Canvas(output_pdf_path, pagesize=letter)
        
        # Process each page
        for page_num in range(len(input_doc)):
            page = input_doc[page_num]
            
            print(f"Processing page {page_num + 1}...")
            
            # Get page dimensions
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            
            # Set page size to match original
            c.setPageSize((page_width, page_height))
            
            # Extract and add images
            image_list = page.get_images(full=True)
            
            if image_list:
                print(f"  Found {len(image_list)} image(s)")
                
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = input_doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # Get image position and size
                        img_rects = page.get_image_rects(xref)
                        
                        if img_rects:
                            for rect in img_rects:
                                # Convert coordinates (PDF coordinates origin is bottom-left)
                                x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
                                img_width = x1 - x0
                                img_height = y1 - y0
                                
                                # Flip Y coordinate (ReportLab uses bottom-left origin)
                                y_position = page_height - y1
                                
                                # Save image temporarily
                                temp_img_path = os.path.join(temp_folder, f"page{page_num + 1}_img{img_index + 1}.png")
                                
                                pil_image = Image.open(io.BytesIO(image_bytes))
                                pil_image.save(temp_img_path, 'PNG')
                                
                                # Draw image on canvas
                                c.drawImage(temp_img_path, x0, y_position, 
                                           width=img_width, height=img_height, 
                                           preserveAspectRatio=True, mask='auto')
                                
                                print(f"    Added image {img_index + 1}")
                    
                    except Exception as e:
                        print(f"    Warning: Could not add image {img_index + 1}: {e}")
            
            # Extract and add text
            text_instances = page.get_text("dict")
            
            if text_instances and "blocks" in text_instances:
                text_count = 0
                
                for block in text_instances["blocks"]:
                    if block["type"] == 0:  # Text block
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                text = span["text"]
                                
                                if text.strip():
                                    # Get text properties
                                    font_size = span["size"]
                                    font_name = span["font"]
                                    color = span["color"]
                                    
                                    # Get text position
                                    x = span["bbox"][0]
                                    y = page_height - span["bbox"][3]  # Flip Y coordinate
                                    
                                    # Set font
                                    try:
                                        c.setFont("Helvetica", font_size)
                                    except:
                                        c.setFont("Helvetica", 12)
                                    
                                    # Set color (convert from integer to RGB)
                                    r = ((color >> 16) & 0xFF) / 255.0
                                    g = ((color >> 8) & 0xFF) / 255.0
                                    b = (color & 0xFF) / 255.0
                                    c.setFillColorRGB(r, g, b)
                                    
                                    # Draw text
                                    c.drawString(x, y, text)
                                    text_count += 1
                
                print(f"  Added {text_count} text elements")
            
            # Finish the page
            c.showPage()
            print(f"  Page {page_num + 1} complete\n")
        
        # Save the PDF
        c.save()
        input_doc.close()
        
        print(f"{'='*60}")
        print(f"Unflattening complete!")
        print(f"Output PDF: {output_pdf_path}")
        print(f"Original size: {os.path.getsize(input_pdf_path) / 1024:.2f} KB")
        print(f"New size: {os.path.getsize(output_pdf_path) / 1024:.2f} KB")
        print(f"{'='*60}")
        
        # Clean up temp folder
        print("\nCleaning up temporary files...")
        for file in os.listdir(temp_folder):
            os.remove(os.path.join(temp_folder, file))
        os.rmdir(temp_folder)
        print("Cleanup complete!")
        
    except Exception as e:
        print(f"Error processing PDF: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def unflatten_pdf_simple(input_pdf_path, output_pdf_path):
    """
    Simplified version: Create a searchable PDF by overlaying text on images.
    This maintains visual fidelity while making text selectable.
    
    Args:
        input_pdf_path (str): Path to the input flattened PDF
        output_pdf_path (str): Path to save the unflattened PDF
    """
    try:
        # Open the input PDF
        input_doc = fitz.open(input_pdf_path)
        
        print(f"Processing PDF: {input_pdf_path}")
        print(f"Total pages: {len(input_doc)}")
        print(f"Creating searchable PDF with text overlay...\n")
        
        # Create a new PDF document
        output_doc = fitz.open()
        
        # Process each page
        for page_num in range(len(input_doc)):
            page = input_doc[page_num]
            
            print(f"Processing page {page_num + 1}...")
            
            # Create a new page with same dimensions
            new_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)
            
            # Get page as image (to preserve visual appearance)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x resolution for quality
            
            # Insert the image
            img_rect = new_page.rect
            new_page.insert_image(img_rect, pixmap=pix)
            
            # Extract text with position information
            text_instances = page.get_text("dict")
            
            if text_instances and "blocks" in text_instances:
                text_count = 0
                
                for block in text_instances["blocks"]:
                    if block["type"] == 0:  # Text block
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                text = span["text"]
                                
                                if text.strip():
                                    # Get text position and size
                                    bbox = span["bbox"]
                                    font_size = span["size"]
                                    
                                    # Insert invisible text at the same position
                                    # This makes the text selectable and searchable
                                    text_rect = fitz.Rect(bbox)
                                    
                                    # Insert text (making it invisible by setting opacity to 0)
                                    new_page.insert_text(
                                        (bbox[0], bbox[3]),
                                        text,
                                        fontsize=font_size,
                                        color=(0, 0, 0),
                                        render_mode=3  # Invisible text (searchable but not visible)
                                    )
                                    text_count += 1
                
                print(f"  Added {text_count} searchable text elements")
            
            print(f"  Page {page_num + 1} complete\n")
        
        # Save the PDF
        output_doc.save(output_pdf_path, garbage=4, deflate=True, clean=True)
        output_doc.close()
        input_doc.close()
        
        print(f"{'='*60}")
        print(f"Unflattening complete!")
        print(f"Output PDF: {output_pdf_path}")
        print(f"Original size: {os.path.getsize(input_pdf_path) / 1024:.2f} KB")
        print(f"New size: {os.path.getsize(output_pdf_path) / 1024:.2f} KB")
        print(f"{'='*60}")
        print("\nThe PDF now has selectable and searchable text!")
        
    except Exception as e:
        print(f"Error processing PDF: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """
    Main function to handle command line arguments.
    """
    if len(sys.argv) < 3:
        print("Usage: python unflatten_pdf.py <input_pdf> <output_pdf> [mode]")
        print("\nArguments:")
        print("  input_pdf   : Path to the flattened PDF file")
        print("  output_pdf  : Path to save the unflattened PDF")
        print("  mode        : (Optional) Unflattening mode:")
        print("                'simple' - Image with text overlay (default, recommended)")
        print("                'rebuild' - Reconstruct with separate text and images")
        print("\nExamples:")
        print("  python unflatten_pdf.py document.pdf document_unflattened.pdf")
        print("  python unflatten_pdf.py document.pdf document_unflattened.pdf simple")
        print("  python unflatten_pdf.py document.pdf document_unflattened.pdf rebuild")
        print("\nNote: 'simple' mode is recommended as it preserves visual appearance")
        print("      while making text selectable and searchable.")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) >= 4 else "simple"
    
    # Check if input file exists
    if not os.path.exists(input_pdf):
        print(f"Error: Input PDF file '{input_pdf}' not found!")
        sys.exit(1)
    
    # Process based on mode
    if mode.lower() == "rebuild":
        unflatten_pdf(input_pdf, output_pdf)
    else:
        unflatten_pdf_simple(input_pdf, output_pdf)


if __name__ == "__main__":
    main()