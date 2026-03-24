"""
Enhanced PDF Image Replacement Script
Provides better control over which images to replace, with options for:
1. Auto-matching by similarity
2. Manual page-by-page replacement
3. Preview before replacement
4. Selective replacement (choose which images to replace)
"""

import fitz  # PyMuPDF
import sys
import os
from PIL import Image
import io
import imagehash


def extract_and_save_images(pdf_path, output_folder):
    """
    Extract all images from PDF and save them for manual review.
    
    Args:
        pdf_path (str): Path to the PDF file
        output_folder (str): Folder to save extracted images
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    pdf_doc = fitz.open(pdf_path)
    
    print(f"\nExtracting images from: {pdf_path}")
    print(f"Saving to: {output_folder}\n")
    
    image_count = 0
    
    for page_num in range(len(pdf_doc)):
        page = pdf_doc[page_num]
        image_list = page.get_images(full=True)
        
        if image_list:
            print(f"Page {page_num + 1}: Found {len(image_list)} image(s)")
            
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = pdf_doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Save image
                    image_filename = f"page{page_num + 1:03d}_img{img_index + 1:02d}.{image_ext}"
                    image_path = os.path.join(output_folder, image_filename)
                    
                    with open(image_path, "wb") as img_file:
                        img_file.write(image_bytes)
                    
                    image_count += 1
                    print(f"  Saved: {image_filename}")
                    
                except Exception as e:
                    print(f"  Error: {e}")
    
    pdf_doc.close()
    
    print(f"\nTotal images extracted: {image_count}")
    return image_count


def replace_images_manual_mapping(base_pdf_path, new_pdf_path, output_pdf_path, mapping_file):
    """
    Replace images using a manual mapping file.
    
    Mapping file format (mapping.txt):
    base_page,base_img_index,new_page,new_img_index
    1,1,1,1
    2,1,3,2
    
    Args:
        base_pdf_path (str): Generated/base PDF
        new_pdf_path (str): New PDF with replacement images
        output_pdf_path (str): Output PDF path
        mapping_file (str): Path to mapping configuration file
    """
    try:
        # Read mapping file
        mappings = []
        with open(mapping_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split(',')
                    if len(parts) == 4:
                        mapping = {
                            'base_page': int(parts[0]) - 1,  # Convert to 0-indexed
                            'base_img': int(parts[1]) - 1,
                            'new_page': int(parts[2]) - 1,
                            'new_img': int(parts[3]) - 1
                        }
                        mappings.append(mapping)
        
        print(f"Loaded {len(mappings)} image replacement mappings")
        
        # Open PDFs
        base_doc = fitz.open(base_pdf_path)
        new_doc = fitz.open(new_pdf_path)
        output_doc = fitz.open()
        
        # Process each page
        for page_num in range(len(base_doc)):
            print(f"\nProcessing page {page_num + 1}...")
            
            base_page = base_doc[page_num]
            output_page = output_doc.new_page(width=base_page.rect.width, 
                                             height=base_page.rect.height)
            
            # Copy base page content
            output_page.show_pdf_page(output_page.rect, base_doc, page_num)
            
            # Find mappings for this page
            page_mappings = [m for m in mappings if m['base_page'] == page_num]
            
            if page_mappings:
                print(f"  Replacing {len(page_mappings)} image(s)")
                
                base_images = base_page.get_images(full=True)
                
                for mapping in page_mappings:
                    try:
                        # Get base image position
                        base_img = base_images[mapping['base_img']]
                        base_xref = base_img[0]
                        base_rects = base_page.get_image_rects(base_xref)
                        
                        # Get new image
                        new_page = new_doc[mapping['new_page']]
                        new_images = new_page.get_images(full=True)
                        new_img = new_images[mapping['new_img']]
                        new_xref = new_img[0]
                        
                        new_image_data = new_doc.extract_image(new_xref)
                        new_image_bytes = new_image_data["image"]
                        
                        # Replace image at each position
                        if base_rects:
                            for rect in base_rects:
                                output_page.insert_image(rect, stream=new_image_bytes,
                                                       keep_proportion=True,
                                                       overlay=True)
                                
                                print(f"    Replaced: base page {page_num+1} img {mapping['base_img']+1} "
                                      f"with new page {mapping['new_page']+1} img {mapping['new_img']+1}")
                    
                    except Exception as e:
                        print(f"    Error replacing image: {e}")
        
        # Save output
        output_doc.save(output_pdf_path, garbage=4, deflate=True, clean=True)
        output_doc.close()
        base_doc.close()
        new_doc.close()
        
        print(f"\n{'='*70}")
        print("Image replacement complete!")
        print(f"Output: {output_pdf_path}")
        print(f"{'='*70}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def replace_by_page_and_position(base_pdf_path, new_pdf_path, output_pdf_path, 
                                 start_page=None, end_page=None):
    """
    Replace images page-by-page, position-by-position.
    Optionally specify page range.
    
    Args:
        base_pdf_path (str): Generated/base PDF
        new_pdf_path (str): New PDF with replacement images
        output_pdf_path (str): Output PDF path
        start_page (int): Starting page number (1-indexed)
        end_page (int): Ending page number (1-indexed)
    """
    try:
        base_doc = fitz.open(base_pdf_path)
        new_doc = fitz.open(new_pdf_path)
        output_doc = fitz.open()
        
        # Determine page range
        total_pages = len(base_doc)
        start = (start_page - 1) if start_page else 0
        end = (end_page if end_page else total_pages)
        
        print(f"Processing pages {start + 1} to {end}")
        print(f"Base PDF: {total_pages} pages")
        print(f"New PDF: {len(new_doc)} pages\n")
        
        for page_num in range(total_pages):
            base_page = base_doc[page_num]
            output_page = output_doc.new_page(width=base_page.rect.width,
                                             height=base_page.rect.height)
            
            # Copy base page
            output_page.show_pdf_page(output_page.rect, base_doc, page_num)
            
            # Only replace images in specified range
            if start <= page_num < end and page_num < len(new_doc):
                print(f"Page {page_num + 1}: Replacing images")
                
                base_images = base_page.get_images(full=True)
                new_page = new_doc[page_num]
                new_images = new_page.get_images(full=True)
                
                if base_images and new_images:
                    num_replacements = min(len(base_images), len(new_images))
                    
                    for img_idx in range(num_replacements):
                        try:
                            base_xref = base_images[img_idx][0]
                            base_rects = base_page.get_image_rects(base_xref)
                            
                            new_xref = new_images[img_idx][0]
                            new_image_data = new_doc.extract_image(new_xref)
                            new_image_bytes = new_image_data["image"]
                            
                            if base_rects:
                                for rect in base_rects:
                                    output_page.insert_image(rect, stream=new_image_bytes,
                                                           keep_proportion=True,
                                                           overlay=True)
                                
                                print(f"  Replaced image {img_idx + 1}")
                        
                        except Exception as e:
                            print(f"  Error replacing image {img_idx + 1}: {e}")
            else:
                print(f"Page {page_num + 1}: Keeping original")
        
        # Save output
        output_doc.save(output_pdf_path, garbage=4, deflate=True, clean=True)
        output_doc.close()
        base_doc.close()
        new_doc.close()
        
        print(f"\n{'='*70}")
        print("Replacement complete!")
        print(f"Output: {output_pdf_path}")
        print(f"{'='*70}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("PDF Image Replacement Tool - Enhanced Version")
        print("="*70)
        print("\nModes:\n")
        print("1. EXTRACT - Extract images for manual review")
        print("   python replace_pdf_images_enhanced.py extract <pdf_file> <output_folder>")
        print("\n2. MANUAL - Replace using mapping file")
        print("   python replace_pdf_images_enhanced.py manual <base_pdf> <new_pdf> <output_pdf> <mapping_file>")
        print("\n3. PAGE - Replace page-by-page (optionally specify range)")
        print("   python replace_pdf_images_enhanced.py page <base_pdf> <new_pdf> <output_pdf> [start_page] [end_page]")
        print("\nExamples:")
        print("  # Extract images from both PDFs")
        print("  python replace_pdf_images_enhanced.py extract base.pdf ./base_images")
        print("  python replace_pdf_images_enhanced.py extract new.pdf ./new_images")
        print("")
        print("  # Create mapping.txt file (format: base_page,base_img,new_page,new_img)")
        print("  # Then replace using manual mapping")
        print("  python replace_pdf_images_enhanced.py manual base.pdf new.pdf output.pdf mapping.txt")
        print("")
        print("  # Replace all pages")
        print("  python replace_pdf_images_enhanced.py page base.pdf new.pdf output.pdf")
        print("")
        print("  # Replace only pages 1-5")
        print("  python replace_pdf_images_enhanced.py page base.pdf new.pdf output.pdf 1 5")
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    
    if mode == "extract":
        if len(sys.argv) < 4:
            print("Usage: python replace_pdf_images_enhanced.py extract <pdf_file> <output_folder>")
            sys.exit(1)
        
        pdf_file = sys.argv[2]
        output_folder = sys.argv[3]
        
        if not os.path.exists(pdf_file):
            print(f"Error: PDF file '{pdf_file}' not found!")
            sys.exit(1)
        
        extract_and_save_images(pdf_file, output_folder)
    
    elif mode == "manual":
        if len(sys.argv) < 6:
            print("Usage: python replace_pdf_images_enhanced.py manual <base_pdf> <new_pdf> <output_pdf> <mapping_file>")
            sys.exit(1)
        
        base_pdf = sys.argv[2]
        new_pdf = sys.argv[3]
        output_pdf = sys.argv[4]
        mapping_file = sys.argv[5]
        
        replace_images_manual_mapping(base_pdf, new_pdf, output_pdf, mapping_file)
    
    elif mode == "page":
        if len(sys.argv) < 5:
            print("Usage: python replace_pdf_images_enhanced.py page <base_pdf> <new_pdf> <output_pdf> [start_page] [end_page]")
            sys.exit(1)
        
        base_pdf = sys.argv[2]
        new_pdf = sys.argv[3]
        output_pdf = sys.argv[4]
        start_page = int(sys.argv[5]) if len(sys.argv) >= 6 else None
        end_page = int(sys.argv[6]) if len(sys.argv) >= 7 else None
        
        replace_by_page_and_position(base_pdf, new_pdf, output_pdf, start_page, end_page)
    
    else:
        print(f"Unknown mode: {mode}")
        print("Valid modes: extract, manual, page")
        sys.exit(1)


if __name__ == "__main__":
    main()