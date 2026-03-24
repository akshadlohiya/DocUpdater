"""
Script to compare images between two PDFs and replace matching images
while maintaining proper positioning. This creates a final user-ready document.

This script:
1. Extracts images from both PDFs with position information
2. Compares images to find matches (using image similarity)
3. Replaces matched images from the new PDF into the generated PDF
4. Maintains exact positioning and sizing
"""

import fitz  # PyMuPDF
import sys
import os
from PIL import Image
import io
import imagehash
import numpy as np


def extract_image_with_position(pdf_path):
    """
    Extract all images from a PDF with their position information.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        dict: Dictionary with page numbers as keys and list of image info as values
    """
    pdf_doc = fitz.open(pdf_path)
    images_data = {}
    
    print(f"Extracting images from: {pdf_path}")
    
    for page_num in range(len(pdf_doc)):
        page = pdf_doc[page_num]
        image_list = page.get_images(full=True)
        
        if not image_list:
            continue
            
        images_data[page_num] = []
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            
            try:
                # Extract image data
                base_image = pdf_doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Get PIL image
                pil_image = Image.open(io.BytesIO(image_bytes))
                
                # Get image position and dimensions
                img_rects = page.get_image_rects(xref)
                
                if img_rects:
                    for rect in img_rects:
                        # Calculate image hash for comparison
                        img_hash = imagehash.average_hash(pil_image)
                        
                        image_info = {
                            'xref': xref,
                            'image_bytes': image_bytes,
                            'pil_image': pil_image,
                            'hash': img_hash,
                            'rect': rect,
                            'bbox': (rect.x0, rect.y0, rect.x1, rect.y1),
                            'width': rect.x1 - rect.x0,
                            'height': rect.y1 - rect.y0,
                            'page_num': page_num,
                            'img_index': img_index
                        }
                        
                        images_data[page_num].append(image_info)
                        
            except Exception as e:
                print(f"  Warning: Could not extract image {img_index} on page {page_num + 1}: {e}")
    
    pdf_doc.close()
    
    total_images = sum(len(imgs) for imgs in images_data.values())
    print(f"  Extracted {total_images} images with position data\n")
    
    return images_data


def compare_images(img1_hash, img2_hash, threshold=10):
    """
    Compare two images using perceptual hashing.
    
    Args:
        img1_hash: Hash of first image
        img2_hash: Hash of second image
        threshold: Maximum difference to consider images as matching (lower = more strict)
        
    Returns:
        bool: True if images match, False otherwise
    """
    return (img1_hash - img2_hash) <= threshold


def find_matching_images(generated_images, new_images, similarity_threshold=10):
    """
    Find matching images between generated PDF and new PDF.
    
    Args:
        generated_images (dict): Images from generated PDF
        new_images (dict): Images from new PDF
        similarity_threshold (int): Threshold for image matching
        
    Returns:
        list: List of matches with replacement information
    """
    matches = []
    
    print("Comparing images to find matches...")
    
    for gen_page, gen_imgs in generated_images.items():
        for gen_img in gen_imgs:
            
            # Search for matching image in new PDF
            for new_page, new_imgs in new_images.items():
                for new_img in new_imgs:
                    
                    # Compare image hashes
                    if compare_images(gen_img['hash'], new_img['hash'], similarity_threshold):
                        match_info = {
                            'generated_page': gen_page,
                            'generated_img': gen_img,
                            'new_img': new_img,
                            'similarity_score': gen_img['hash'] - new_img['hash']
                        }
                        matches.append(match_info)
                        
                        print(f"  Match found: Page {gen_page + 1} (generated) -> "
                              f"Page {new_page + 1} (new) | Similarity: {match_info['similarity_score']}")
                        
                        break  # Found a match, move to next generated image
    
    print(f"\nTotal matches found: {len(matches)}\n")
    return matches


def replace_images_in_pdf(generated_pdf_path, new_pdf_path, output_pdf_path, 
                         similarity_threshold=10, preserve_quality=True):
    """
    Replace matched images from new PDF into generated PDF while maintaining positioning.
    
    Args:
        generated_pdf_path (str): Path to the generated/unflattened PDF
        new_pdf_path (str): Path to the new PDF with replacement images
        output_pdf_path (str): Path to save the final PDF
        similarity_threshold (int): Threshold for image matching (0-64, lower = stricter)
        preserve_quality (bool): Whether to preserve original image quality
    """
    try:
        print("="*70)
        print("PDF Image Replacement Tool")
        print("="*70 + "\n")
        
        # Step 1: Extract images with positions from both PDFs
        print("Step 1: Extracting images from both PDFs...")
        generated_images = extract_image_with_position(generated_pdf_path)
        new_images = extract_image_with_position(new_pdf_path)
        
        # Step 2: Find matching images
        print("Step 2: Finding matching images...")
        matches = find_matching_images(generated_images, new_images, similarity_threshold)
        
        if not matches:
            print("No matching images found. Creating copy of generated PDF...")
            # Just copy the generated PDF
            gen_doc = fitz.open(generated_pdf_path)
            gen_doc.save(output_pdf_path)
            gen_doc.close()
            return
        
        # Step 3: Create output PDF with replaced images
        print("Step 3: Replacing images in PDF...")
        
        gen_doc = fitz.open(generated_pdf_path)
        new_doc = fitz.open(new_pdf_path)
        
        # Create output document
        output_doc = fitz.open()
        
        # Process each page
        for page_num in range(len(gen_doc)):
            print(f"Processing page {page_num + 1}...")
            
            # Get the original page
            gen_page = gen_doc[page_num]
            
            # Create new page with same dimensions
            output_page = output_doc.new_page(width=gen_page.rect.width, 
                                             height=gen_page.rect.height)
            
            # Copy everything from generated page
            output_page.show_pdf_page(output_page.rect, gen_doc, page_num)
            
            # Find matches for this page
            page_matches = [m for m in matches if m['generated_page'] == page_num]
            
            if page_matches:
                print(f"  Found {len(page_matches)} image(s) to replace on this page")
                
                for match in page_matches:
                    try:
                        gen_img = match['generated_img']
                        new_img = match['new_img']
                        
                        # Delete old image
                        # Note: We'll overlay the new image instead of deleting
                        
                        # Get new image bytes
                        new_image_bytes = new_img['image_bytes']
                        
                        # Get position from generated PDF
                        bbox = gen_img['bbox']
                        rect = fitz.Rect(bbox)
                        
                        # Insert new image at the same position
                        output_page.insert_image(rect, stream=new_image_bytes, 
                                               keep_proportion=True, 
                                               overlay=True)
                        
                        print(f"    Replaced image at position ({bbox[0]:.1f}, {bbox[1]:.1f})")
                        
                    except Exception as e:
                        print(f"    Warning: Could not replace image: {e}")
            else:
                print(f"  No images to replace on this page")
        
        # Save output PDF
        output_doc.save(output_pdf_path, garbage=4, deflate=True, clean=True)
        output_doc.close()
        gen_doc.close()
        new_doc.close()
        
        print(f"\n{'='*70}")
        print("Image replacement complete!")
        print(f"Output PDF saved to: {output_pdf_path}")
        print(f"Original size: {os.path.getsize(generated_pdf_path) / 1024:.2f} KB")
        print(f"New size: {os.path.getsize(output_pdf_path) / 1024:.2f} KB")
        print(f"Total images replaced: {len(matches)}")
        print(f"{'='*70}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def replace_all_images_by_page(generated_pdf_path, new_pdf_path, output_pdf_path):
    """
    Simpler approach: Replace ALL images on matching page numbers.
    Assumes both PDFs have same structure.
    
    Args:
        generated_pdf_path (str): Path to the generated/unflattened PDF
        new_pdf_path (str): Path to the new PDF with replacement images
        output_pdf_path (str): Path to save the final PDF
    """
    try:
        print("="*70)
        print("PDF Image Replacement Tool (Page-by-Page Mode)")
        print("="*70 + "\n")
        
        gen_doc = fitz.open(generated_pdf_path)
        new_doc = fitz.open(new_pdf_path)
        
        print(f"Generated PDF: {len(gen_doc)} pages")
        print(f"New PDF: {len(new_doc)} pages\n")
        
        # Create output document
        output_doc = fitz.open()
        
        max_pages = min(len(gen_doc), len(new_doc))
        
        for page_num in range(max_pages):
            print(f"Processing page {page_num + 1}...")
            
            gen_page = gen_doc[page_num]
            new_page = new_doc[page_num]
            
            # Create new page
            output_page = output_doc.new_page(width=gen_page.rect.width, 
                                             height=gen_page.rect.height)
            
            # Copy text and structure from generated PDF
            output_page.show_pdf_page(output_page.rect, gen_doc, page_num)
            
            # Get images from both pages
            gen_images = gen_page.get_images(full=True)
            new_images = new_page.get_images(full=True)
            
            if gen_images and new_images:
                print(f"  Replacing {len(gen_images)} image(s)")
                
                # Replace each image
                for img_index in range(min(len(gen_images), len(new_images))):
                    try:
                        gen_xref = gen_images[img_index][0]
                        new_xref = new_images[img_index][0]
                        
                        # Get position from generated PDF
                        gen_rects = gen_page.get_image_rects(gen_xref)
                        
                        # Get new image
                        new_image = new_doc.extract_image(new_xref)
                        new_image_bytes = new_image["image"]
                        
                        if gen_rects:
                            for rect in gen_rects:
                                # Insert new image at old position
                                output_page.insert_image(rect, stream=new_image_bytes,
                                                       keep_proportion=True,
                                                       overlay=True)
                                
                                print(f"    Replaced image {img_index + 1}")
                    
                    except Exception as e:
                        print(f"    Warning: Could not replace image {img_index + 1}: {e}")
        
        # Save output
        output_doc.save(output_pdf_path, garbage=4, deflate=True, clean=True)
        output_doc.close()
        gen_doc.close()
        new_doc.close()
        
        print(f"\n{'='*70}")
        print("Image replacement complete!")
        print(f"Output PDF: {output_pdf_path}")
        print(f"{'='*70}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """
    Main function to handle command line arguments.
    """
    if len(sys.argv) < 4:
        print("Usage: python replace_pdf_images.py <generated_pdf> <new_pdf> <output_pdf> [mode] [threshold]")
        print("\nArguments:")
        print("  generated_pdf : Path to the generated/unflattened PDF")
        print("  new_pdf       : Path to the PDF with new/replacement images")
        print("  output_pdf    : Path to save the final output PDF")
        print("  mode          : (Optional) Replacement mode:")
        print("                  'smart'  - Compare and match images by similarity (default)")
        print("                  'page'   - Replace all images on same page numbers")
        print("  threshold     : (Optional) Similarity threshold for 'smart' mode (0-64, default: 10)")
        print("                  Lower = stricter matching, Higher = more lenient")
        print("\nExamples:")
        print("  # Smart matching with default threshold")
        print("  python replace_pdf_images.py generated.pdf new.pdf output.pdf")
        print("")
        print("  # Smart matching with custom threshold")
        print("  python replace_pdf_images.py generated.pdf new.pdf output.pdf smart 15")
        print("")
        print("  # Page-by-page replacement")
        print("  python replace_pdf_images.py generated.pdf new.pdf output.pdf page")
        sys.exit(1)
    
    generated_pdf = sys.argv[1]
    new_pdf = sys.argv[2]
    output_pdf = sys.argv[3]
    mode = sys.argv[4] if len(sys.argv) >= 5 else "smart"
    threshold = int(sys.argv[5]) if len(sys.argv) >= 6 else 10
    
    # Check if files exist
    if not os.path.exists(generated_pdf):
        print(f"Error: Generated PDF '{generated_pdf}' not found!")
        sys.exit(1)
    
    if not os.path.exists(new_pdf):
        print(f"Error: New PDF '{new_pdf}' not found!")
        sys.exit(1)
    
    # Process based on mode
    if mode.lower() == "page":
        replace_all_images_by_page(generated_pdf, new_pdf, output_pdf)
    else:
        replace_images_in_pdf(generated_pdf, new_pdf, output_pdf, threshold)


if __name__ == "__main__":
    main()