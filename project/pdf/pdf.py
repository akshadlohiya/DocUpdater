"""
Script to extract all images from a PDF and save them as PNG/JPG files in a folder.
This script uses PyMuPDF (fitz) to extract images.
"""

import fitz  # PyMuPDF
import sys
import os
from PIL import Image
import io


def extract_images_from_pdf(pdf_path, output_folder):
    """
    Extract all images from a PDF file and save them to a folder.
    
    Args:
        pdf_path (str): Path to the input PDF file
        output_folder (str): Folder path where images will be saved
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
        print(f"Extracting images to: {output_folder}\n")
        
        image_count = 0
        
        # Iterate through each page
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            # Get all images on the page
            image_list = page.get_images(full=True)
            
            if image_list:
                print(f"Page {page_num + 1}: Found {len(image_list)} image(s)")
            
            # Extract each image
            for img_index, img in enumerate(image_list):
                xref = img[0]  # xref is the image reference number
                
                try:
                    # Extract image
                    base_image = pdf_document.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]  # png, jpeg, etc.
                    
                    # Create filename
                    image_count += 1
                    image_filename = f"page{page_num + 1}_img{img_index + 1}.{image_ext}"
                    image_path = os.path.join(output_folder, image_filename)
                    
                    # Save the image
                    with open(image_path, "wb") as img_file:
                        img_file.write(image_bytes)
                    
                    print(f"  ✓ Saved: {image_filename} ({image_ext.upper()})")
                    
                except Exception as e:
                    print(f"  ✗ Error extracting image {img_index + 1} on page {page_num + 1}: {e}")
        
        pdf_document.close()
        
        print(f"\n{'='*50}")
        print(f"Extraction complete!")
        print(f"Total images extracted: {image_count}")
        print(f"Images saved to: {output_folder}")
        print(f"{'='*50}")
        
    except Exception as e:
        print(f"Error processing PDF: {e}")
        sys.exit(1)


def extract_images_convert_format(pdf_path, output_folder, output_format="png"):
    """
    Extract all images from a PDF and convert them to a specific format (PNG or JPG).
    
    Args:
        pdf_path (str): Path to the input PDF file
        output_folder (str): Folder path where images will be saved
        output_format (str): Desired output format ('png' or 'jpg')
    """
    try:
        # Create output folder if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"Created output folder: {output_folder}")
        
        # Validate format
        output_format = output_format.lower()
        if output_format not in ['png', 'jpg', 'jpeg']:
            print("Invalid format. Using PNG as default.")
            output_format = 'png'
        
        if output_format == 'jpeg':
            output_format = 'jpg'
        
        # Open the PDF
        pdf_document = fitz.open(pdf_path)
        
        print(f"Processing PDF: {pdf_path}")
        print(f"Total pages: {len(pdf_document)}")
        print(f"Output format: {output_format.upper()}")
        print(f"Extracting images to: {output_folder}\n")
        
        image_count = 0
        
        # Iterate through each page
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            # Get all images on the page
            image_list = page.get_images(full=True)
            
            if image_list:
                print(f"Page {page_num + 1}: Found {len(image_list)} image(s)")
            
            # Extract each image
            for img_index, img in enumerate(image_list):
                xref = img[0]
                
                try:
                    # Extract image
                    base_image = pdf_document.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # Convert to PIL Image
                    pil_image = Image.open(io.BytesIO(image_bytes))
                    
                    # Convert RGBA to RGB if saving as JPG
                    if output_format == 'jpg' and pil_image.mode == 'RGBA':
                        pil_image = pil_image.convert('RGB')
                    
                    # Create filename
                    image_count += 1
                    image_filename = f"page{page_num + 1}_img{img_index + 1}.{output_format}"
                    image_path = os.path.join(output_folder, image_filename)
                    
                    # Save the image
                    if output_format == 'png':
                        pil_image.save(image_path, 'PNG')
                    else:  # jpg
                        pil_image.save(image_path, 'JPEG', quality=95)
                    
                    print(f"  ✓ Saved: {image_filename}")
                    
                except Exception as e:
                    print(f"  ✗ Error extracting image {img_index + 1} on page {page_num + 1}: {e}")
        
        pdf_document.close()
        
        print(f"\n{'='*50}")
        print(f"Extraction complete!")
        print(f"Total images extracted: {image_count}")
        print(f"Images saved to: {output_folder}")
        print(f"{'='*50}")
        
    except Exception as e:
        print(f"Error processing PDF: {e}")
        sys.exit(1)


def main():
    """
    Main function to handle command line arguments.
    """
    if len(sys.argv) < 3:
        print("Usage: python extract_images_from_pdf.py <pdf_file> <output_folder> [format]")
        print("\nArguments:")
        print("  pdf_file       : Path to the PDF file")
        print("  output_folder  : Folder where images will be saved")
        print("  format         : (Optional) Output format: 'png' or 'jpg' (default: original format)")
        print("\nExamples:")
        print("  python extract_images_from_pdf.py document.pdf ./images")
        print("  python extract_images_from_pdf.py document.pdf ./images png")
        print("  python extract_images_from_pdf.py document.pdf ./images jpg")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_folder = sys.argv[2]
    
    # Check if input file exists
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file '{pdf_path}' not found!")
        sys.exit(1)
    
    # Check if format is specified
    if len(sys.argv) >= 4:
        output_format = sys.argv[3]
        extract_images_convert_format(pdf_path, output_folder, output_format)
    else:
        extract_images_from_pdf(pdf_path, output_folder)


if __name__ == "__main__":
    main()