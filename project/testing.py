"""
Integrated PDF Toolkit
A comprehensive tool for PDF processing including:
- Image extraction
- Text extraction
- PDF unflattening
- PDF comparison with document validation

This script combines all PDF processing functionality into a single tool.
"""

import fitz  # PyMuPDF
import sys
import os
from PIL import Image
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from difflib import SequenceMatcher


class PDFToolkit:
    """Comprehensive PDF processing toolkit"""
    
    def __init__(self, pdf_path):
        """
        Initialize the toolkit with a PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file '{pdf_path}' not found!")
        
        self.pdf_path = pdf_path
        self.pdf_document = None
        self.pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
    
    def open(self):
        """Open the PDF document"""
        if self.pdf_document is None:
            self.pdf_document = fitz.open(self.pdf_path)
        return self.pdf_document
    
    def close(self):
        """Close the PDF document"""
        if self.pdf_document is not None:
            self.pdf_document.close()
            self.pdf_document = None
    
    # ==================== IMAGE EXTRACTION ====================
    
    def extract_images(self, output_folder, output_format=None):
        """
        Extract all images from the PDF.
        
        Args:
            output_folder (str): Folder to save extracted images
            output_format (str): Optional format conversion ('png' or 'jpg')
        
        Returns:
            int: Number of images extracted
        """
        try:
            # Create output folder
            os.makedirs(output_folder, exist_ok=True)
            print(f"📁 Output folder: {output_folder}")
            
            doc = self.open()
            print(f"📄 Processing: {self.pdf_path}")
            print(f"📖 Total pages: {len(doc)}\n")
            
            image_count = 0
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images(full=True)
                
                if image_list:
                    print(f"Page {page_num + 1}: Found {len(image_list)} image(s)")
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    
                    try:
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        
                        image_count += 1
                        
                        if output_format:
                            # Convert to specified format
                            pil_image = Image.open(io.BytesIO(image_bytes))
                            
                            if output_format == 'jpg' and pil_image.mode == 'RGBA':
                                pil_image = pil_image.convert('RGB')
                            
                            image_filename = f"page{page_num + 1}_img{img_index + 1}.{output_format}"
                            image_path = os.path.join(output_folder, image_filename)
                            
                            if output_format == 'png':
                                pil_image.save(image_path, 'PNG')
                            else:
                                pil_image.save(image_path, 'JPEG', quality=95)
                        else:
                            # Keep original format
                            image_filename = f"page{page_num + 1}_img{img_index + 1}.{image_ext}"
                            image_path = os.path.join(output_folder, image_filename)
                            
                            with open(image_path, "wb") as img_file:
                                img_file.write(image_bytes)
                        
                        print(f"  ✓ Saved: {image_filename}")
                        
                    except Exception as e:
                        print(f"  ✗ Error extracting image {img_index + 1}: {e}")
            
            print(f"\n{'='*60}")
            print(f"✅ Extraction complete! Total images: {image_count}")
            print(f"{'='*60}\n")
            
            return image_count
            
        except Exception as e:
            print(f"❌ Error extracting images: {e}")
            raise
    
    # ==================== TEXT EXTRACTION ====================
    
    def extract_text(self, output_folder, mode="single", output_format="txt"):
        """
        Extract text from the PDF.
        
        Args:
            output_folder (str): Folder to save extracted text
            mode (str): 'single' for one file, 'pages' for separate files
            output_format (str): 'txt' or 'md'
        
        Returns:
            int: Number of characters extracted
        """
        try:
            os.makedirs(output_folder, exist_ok=True)
            print(f"📁 Output folder: {output_folder}")
            
            doc = self.open()
            print(f"📄 Processing: {self.pdf_path}")
            print(f"📖 Total pages: {len(doc)}\n")
            
            if mode == "pages":
                return self._extract_text_by_page(doc, output_folder)
            else:
                return self._extract_text_single(doc, output_folder, output_format)
                
        except Exception as e:
            print(f"❌ Error extracting text: {e}")
            raise
    
    def _extract_text_single(self, doc, output_folder, output_format):
        """Extract all text into a single file"""
        output_filename = f"{self.pdf_basename}_extracted_text.{output_format}"
        output_path = os.path.join(output_folder, output_filename)
        
        all_text = []
        total_chars = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            if text.strip():
                print(f"Page {page_num + 1}: Extracted {len(text)} characters")
                
                if output_format == "md":
                    all_text.append(f"\n## Page {page_num + 1}\n")
                else:
                    all_text.append(f"\n{'='*60}\nPAGE {page_num + 1}\n{'='*60}\n")
                
                all_text.append(text)
                total_chars += len(text)
            else:
                print(f"Page {page_num + 1}: No text found")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(''.join(all_text))
        
        print(f"\n{'='*60}")
        print(f"✅ Text extraction complete!")
        print(f"📄 Output file: {output_path}")
        print(f"📊 Total characters: {total_chars}")
        print(f"{'='*60}\n")
        
        return total_chars
    
    def _extract_text_by_page(self, doc, output_folder):
        """Extract text with separate file per page"""
        pages_with_text = 0
        total_chars = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            if text.strip():
                output_filename = f"{self.pdf_basename}_page{page_num + 1}.txt"
                output_path = os.path.join(output_folder, output_filename)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                
                print(f"Page {page_num + 1}: Saved {len(text)} characters to {output_filename}")
                pages_with_text += 1
                total_chars += len(text)
            else:
                print(f"Page {page_num + 1}: No text found (skipped)")
        
        print(f"\n{'='*60}")
        print(f"✅ Text extraction complete!")
        print(f"📊 Pages with text: {pages_with_text}/{len(doc)}")
        print(f"📊 Total characters: {total_chars}")
        print(f"📁 Files saved to: {output_folder}")
        print(f"{'='*60}\n")
        
        return total_chars
    
    # ==================== PDF UNFLATTENING ====================
    
    def unflatten(self, output_pdf_path, mode="simple"):
        """
        Unflatten the PDF to make text selectable.
        
        Args:
            output_pdf_path (str): Path to save unflattened PDF
            mode (str): 'simple' (recommended) or 'rebuild'
        
        Returns:
            bool: Success status
        """
        try:
            if mode == "rebuild":
                return self._unflatten_rebuild(output_pdf_path)
            else:
                return self._unflatten_simple(output_pdf_path)
                
        except Exception as e:
            print(f"❌ Error unflattening PDF: {e}")
            raise
    
    def _unflatten_simple(self, output_pdf_path):
        """Create searchable PDF by overlaying text on images"""
        doc = self.open()
        
        print(f"📄 Processing: {self.pdf_path}")
        print(f"📖 Total pages: {len(doc)}")
        print(f"🔄 Creating searchable PDF with text overlay...\n")
        
        output_doc = fitz.open()
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            print(f"Processing page {page_num + 1}...")
            
            # Create new page with same dimensions
            new_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)
            
            # Get page as image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            new_page.insert_image(new_page.rect, pixmap=pix)
            
            # Extract and overlay text
            text_instances = page.get_text("dict")
            text_count = 0
            
            if text_instances and "blocks" in text_instances:
                for block in text_instances["blocks"]:
                    if block["type"] == 0:
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                text = span["text"]
                                
                                if text.strip():
                                    bbox = span["bbox"]
                                    font_size = span["size"]
                                    
                                    # Insert invisible searchable text
                                    new_page.insert_text(
                                        (bbox[0], bbox[3]),
                                        text,
                                        fontsize=font_size,
                                        color=(0, 0, 0),
                                        render_mode=3
                                    )
                                    text_count += 1
                
                print(f"  Added {text_count} searchable text elements")
            
            print(f"  Page {page_num + 1} complete\n")
        
        # Save
        output_doc.save(output_pdf_path, garbage=4, deflate=True, clean=True)
        output_doc.close()
        
        print(f"{'='*60}")
        print(f"✅ Unflattening complete!")
        print(f"📄 Output: {output_pdf_path}")
        print(f"📊 Original: {os.path.getsize(self.pdf_path) / 1024:.2f} KB")
        print(f"📊 New: {os.path.getsize(output_pdf_path) / 1024:.2f} KB")
        print(f"{'='*60}\n")
        
        return True
    
    def _unflatten_rebuild(self, output_pdf_path):
        """Rebuild PDF with separate text and images"""
        doc = self.open()
        temp_folder = "./temp_unflatten"
        
        os.makedirs(temp_folder, exist_ok=True)
        
        print(f"📄 Processing: {self.pdf_path}")
        print(f"📖 Total pages: {len(doc)}")
        print(f"🔄 Rebuilding PDF...\n")
        
        c = canvas.Canvas(output_pdf_path, pagesize=letter)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            print(f"Processing page {page_num + 1}...")
            
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            
            c.setPageSize((page_width, page_height))
            
            # Extract and add images
            image_list = page.get_images(full=True)
            
            if image_list:
                print(f"  Found {len(image_list)} image(s)")
                
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        img_rects = page.get_image_rects(xref)
                        
                        if img_rects:
                            for rect in img_rects:
                                x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
                                img_width = x1 - x0
                                img_height = y1 - y0
                                y_position = page_height - y1
                                
                                temp_img_path = os.path.join(temp_folder, f"page{page_num + 1}_img{img_index + 1}.png")
                                
                                pil_image = Image.open(io.BytesIO(image_bytes))
                                pil_image.save(temp_img_path, 'PNG')
                                
                                c.drawImage(temp_img_path, x0, y_position, 
                                           width=img_width, height=img_height, 
                                           preserveAspectRatio=True, mask='auto')
                                
                                print(f"    Added image {img_index + 1}")
                    
                    except Exception as e:
                        print(f"    Warning: Could not add image {img_index + 1}: {e}")
            
            # Extract and add text
            text_instances = page.get_text("dict")
            text_count = 0
            
            if text_instances and "blocks" in text_instances:
                for block in text_instances["blocks"]:
                    if block["type"] == 0:
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                text = span["text"]
                                
                                if text.strip():
                                    font_size = span["size"]
                                    color = span["color"]
                                    x = span["bbox"][0]
                                    y = page_height - span["bbox"][3]
                                    
                                    try:
                                        c.setFont("Helvetica", font_size)
                                    except:
                                        c.setFont("Helvetica", 12)
                                    
                                    r = ((color >> 16) & 0xFF) / 255.0
                                    g = ((color >> 8) & 0xFF) / 255.0
                                    b = (color & 0xFF) / 255.0
                                    c.setFillColorRGB(r, g, b)
                                    
                                    c.drawString(x, y, text)
                                    text_count += 1
                
                print(f"  Added {text_count} text elements")
            
            c.showPage()
            print(f"  Page {page_num + 1} complete\n")
        
        c.save()
        
        print(f"{'='*60}")
        print(f"✅ Unflattening complete!")
        print(f"📄 Output: {output_pdf_path}")
        print(f"📊 Original: {os.path.getsize(self.pdf_path) / 1024:.2f} KB")
        print(f"📊 New: {os.path.getsize(output_pdf_path) / 1024:.2f} KB")
        print(f"{'='*60}\n")
        
        # Cleanup
        print("🧹 Cleaning up temporary files...")
        for file in os.listdir(temp_folder):
            os.remove(os.path.join(temp_folder, file))
        os.rmdir(temp_folder)
        print("✓ Cleanup complete!\n")
        
        return True
    
    # ==================== PDF COMPARISON ====================
    
    @staticmethod
    def _calculate_text_similarity(text1, text2):
        """
        Calculate similarity ratio between two texts.
        
        Args:
            text1 (str): First text
            text2 (str): Second text
        
        Returns:
            float: Similarity ratio between 0 and 1
        """
        # Clean and normalize text
        text1_clean = ' '.join(text1.split()).lower()
        text2_clean = ' '.join(text2.split()).lower()
        
        # Calculate similarity
        return SequenceMatcher(None, text1_clean, text2_clean).ratio()
    
    @staticmethod
    def _validate_documents_are_related(doc1, doc2, similarity_threshold=0.3):
        """
        Validate that two PDFs are related versions of the same document.
        
        Args:
            doc1: First PDF document
            doc2: Second PDF document
            similarity_threshold (float): Minimum similarity ratio (0-1)
        
        Returns:
            tuple: (is_valid, similarity_score, reason)
        """
        # Sample first few pages for comparison (max 3 pages)
        sample_pages = min(3, len(doc1), len(doc2))
        
        if sample_pages == 0:
            return False, 0.0, "One or both PDFs are empty"
        
        # Extract sample text from both documents
        text1_samples = []
        text2_samples = []
        
        for page_num in range(sample_pages):
            if page_num < len(doc1):
                text1 = doc1[page_num].get_text().strip()
                if text1:
                    text1_samples.append(text1)
            
            if page_num < len(doc2):
                text2 = doc2[page_num].get_text().strip()
                if text2:
                    text2_samples.append(text2)
        
        # If no text in either document, check page count similarity
        if not text1_samples and not text2_samples:
            page_diff_ratio = abs(len(doc1) - len(doc2)) / max(len(doc1), len(doc2))
            if page_diff_ratio > 0.5:  # More than 50% difference in page count
                return False, 0.0, "Both PDFs contain no text and have very different page counts"
            return True, 0.5, "Both PDFs contain no text but have similar page counts (image-only PDFs)"
        
        # If only one has text, they're likely different documents
        if not text1_samples or not text2_samples:
            return False, 0.0, "Only one PDF contains extractable text"
        
        # Calculate average similarity across sampled pages
        similarities = []
        for t1, t2 in zip(text1_samples, text2_samples):
            sim = PDFToolkit._calculate_text_similarity(t1, t2)
            similarities.append(sim)
        
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
        
        # Check if documents are related
        if avg_similarity < similarity_threshold:
            return False, avg_similarity, f"Content similarity too low ({avg_similarity:.1%}). These appear to be different documents."
        
        return True, avg_similarity, "Documents appear to be related versions"
    
    @staticmethod
    def compare_pdfs(pdf1_path, pdf2_path, output_folder="./comparison_output", 
                     similarity_threshold=0.3, force_compare=False):
        """
        Compare two PDFs and generate comparison report.
        Validates that PDFs are related versions before comparing.
        
        Args:
            pdf1_path (str): Path to first PDF (old version)
            pdf2_path (str): Path to second PDF (new version)
            output_folder (str): Folder to save comparison results
            similarity_threshold (float): Minimum similarity to consider documents related (0-1)
            force_compare (bool): Skip validation and force comparison
        
        Returns:
            dict: Comparison results or None if validation fails
        """
        try:
            os.makedirs(output_folder, exist_ok=True)
            
            print(f"📊 Comparing PDFs")
            print(f"📄 PDF 1 (Old): {pdf1_path}")
            print(f"📄 PDF 2 (New): {pdf2_path}\n")
            
            doc1 = fitz.open(pdf1_path)
            doc2 = fitz.open(pdf2_path)
            
            # Validate documents are related (unless forced)
            if not force_compare:
                print("🔍 Validating documents are related versions...")
                is_valid, similarity, reason = PDFToolkit._validate_documents_are_related(
                    doc1, doc2, similarity_threshold
                )
                
                print(f"   Similarity score: {similarity:.1%}")
                print(f"   {reason}\n")
                
                if not is_valid:
                    print(f"{'='*60}")
                    print(f"❌ VALIDATION FAILED")
                    print(f"{'='*60}")
                    print(f"\n⚠️  These PDFs appear to be completely different documents!")
                    print(f"   Similarity: {similarity:.1%} (threshold: {similarity_threshold:.1%})")
                    print(f"   Reason: {reason}")
                    print(f"\n💡 Tips:")
                    print(f"   • Make sure you're comparing the old and new versions of the SAME document")
                    print(f"   • Check that you haven't accidentally selected a different file")
                    print(f"   • If you're sure these are related, use --force flag to skip validation")
                    print(f"\nComparison aborted.\n")
                    
                    doc1.close()
                    doc2.close()
                    return None
                
                print(f"✅ Validation passed! Proceeding with comparison...\n")
            else:
                print("⚠️  Skipping validation (forced comparison mode)\n")
            
            results = {
                'pdf1': pdf1_path,
                'pdf2': pdf2_path,
                'pages1': len(doc1),
                'pages2': len(doc2),
                'differences': [],
                'validation': {
                    'forced': force_compare,
                    'similarity': similarity if not force_compare else 'N/A'
                }
            }
            
            print(f"PDF 1: {len(doc1)} pages")
            print(f"PDF 2: {len(doc2)} pages\n")
            
            max_pages = max(len(doc1), len(doc2))
            
            for page_num in range(max_pages):
                diff = {'page': page_num + 1}
                
                if page_num >= len(doc1):
                    diff['status'] = 'Only in PDF 2 (New page added)'
                    results['differences'].append(diff)
                    print(f"Page {page_num + 1}: Only exists in PDF 2 (NEW)")
                    continue
                
                if page_num >= len(doc2):
                    diff['status'] = 'Only in PDF 1 (Page removed)'
                    results['differences'].append(diff)
                    print(f"Page {page_num + 1}: Only exists in PDF 1 (REMOVED)")
                    continue
                
                page1 = doc1[page_num]
                page2 = doc2[page_num]
                
                # Compare text
                text1 = page1.get_text()
                text2 = page2.get_text()
                
                text_match = text1 == text2
                diff['text_match'] = text_match
                
                # Calculate text similarity for changed pages
                if not text_match and text1.strip() and text2.strip():
                    page_similarity = PDFToolkit._calculate_text_similarity(text1, text2)
                    diff['text_similarity'] = page_similarity
                
                # Compare images
                images1 = len(page1.get_images())
                images2 = len(page2.get_images())
                
                diff['images1'] = images1
                diff['images2'] = images2
                diff['images_match'] = images1 == images2
                
                if not text_match or not diff['images_match']:
                    results['differences'].append(diff)
                    status = []
                    if not text_match:
                        if 'text_similarity' in diff:
                            status.append(f"Text changed (similarity: {diff['text_similarity']:.1%})")
                        else:
                            status.append("Text changed")
                    if not diff['images_match']:
                        status.append(f"Images differ ({images1} → {images2})")
                    
                    print(f"Page {page_num + 1}: {', '.join(status)}")
                else:
                    print(f"Page {page_num + 1}: Identical")
            
            doc1.close()
            doc2.close()
            
            # Save detailed report
            report_path = os.path.join(output_folder, "comparison_report.txt")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("PDF COMPARISON REPORT\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"PDF 1 (Old): {pdf1_path} ({results['pages1']} pages)\n")
                f.write(f"PDF 2 (New): {pdf2_path} ({results['pages2']} pages)\n\n")
                
                if not force_compare:
                    f.write(f"Validation Similarity: {results['validation']['similarity']:.1%}\n\n")
                
                f.write(f"Total differences found: {len(results['differences'])}\n")
                f.write(f"Identical pages: {max_pages - len(results['differences'])}\n\n")
                
                if results['differences']:
                    f.write("DIFFERENCES:\n")
                    f.write("-" * 60 + "\n\n")
                    
                    for diff in results['differences']:
                        f.write(f"Page {diff['page']}:\n")
                        if 'status' in diff:
                            f.write(f"  {diff['status']}\n")
                        else:
                            f.write(f"  Text match: {diff['text_match']}\n")
                            if 'text_similarity' in diff:
                                f.write(f"  Text similarity: {diff['text_similarity']:.1%}\n")
                            f.write(f"  Images: {diff['images1']} → {diff['images2']}\n")
                            f.write(f"  Images match: {diff['images_match']}\n")
                        f.write("\n")
                else:
                    f.write("\n✅ PDFs are identical!\n")
            
            print(f"\n{'='*60}")
            print(f"✅ Comparison complete!")
            print(f"📄 Report saved: {report_path}")
            print(f"📊 Total differences: {len(results['differences'])}")
            print(f"📊 Identical pages: {max_pages - len(results['differences'])}")
            print(f"{'='*60}\n")
            
            return results
            
        except Exception as e:
            print(f"❌ Error comparing PDFs: {e}")
            raise


def print_usage():
    """Print usage information"""
    print("""
╔════════════════════════════════════════════════════════════╗
║              INTEGRATED PDF TOOLKIT                         ║
╚════════════════════════════════════════════════════════════╝

USAGE:
    python pdf_toolkit.py <command> [arguments]

COMMANDS:

1. Extract Images
   python pdf_toolkit.py extract-images <pdf_file> <output_folder> [format]
   
   Arguments:
     pdf_file       : Path to PDF file
     output_folder  : Folder to save images
     format         : Optional: 'png' or 'jpg' (default: original)
   
   Examples:
     python pdf_toolkit.py extract-images doc.pdf ./images
     python pdf_toolkit.py extract-images doc.pdf ./images png

2. Extract Text
   python pdf_toolkit.py extract-text <pdf_file> <output_folder> [mode] [format]
   
   Arguments:
     pdf_file       : Path to PDF file
     output_folder  : Folder to save text
     mode           : Optional: 'single' or 'pages' (default: single)
     format         : Optional: 'txt' or 'md' (default: txt)
   
   Examples:
     python pdf_toolkit.py extract-text doc.pdf ./text
     python pdf_toolkit.py extract-text doc.pdf ./text pages
     python pdf_toolkit.py extract-text doc.pdf ./text single md

3. Unflatten PDF
   python pdf_toolkit.py unflatten <pdf_file> <output_pdf> [mode]
   
   Arguments:
     pdf_file    : Path to flattened PDF
     output_pdf  : Path to save unflattened PDF
     mode        : Optional: 'simple' or 'rebuild' (default: simple)
   
   Examples:
     python pdf_toolkit.py unflatten doc.pdf doc_searchable.pdf
     python pdf_toolkit.py unflatten doc.pdf doc_rebuilt.pdf rebuild

4. Compare PDFs (with validation)
   python pdf_toolkit.py compare <pdf1> <pdf2> [output_folder] [--force] [--threshold X.X]
   
   Arguments:
     pdf1           : Path to first PDF (old version)
     pdf2           : Path to second PDF (new version)
     output_folder  : Optional: Folder for report (default: ./comparison_output)
     --force        : Skip validation and force comparison
     --threshold    : Similarity threshold 0.0-1.0 (default: 0.3)
   
   Examples:
     python pdf_toolkit.py compare old_doc.pdf new_doc.pdf
     python pdf_toolkit.py compare v1.pdf v2.pdf ./results
     python pdf_toolkit.py compare doc1.pdf doc2.pdf --force
     python pdf_toolkit.py compare doc1.pdf doc2.pdf --threshold 0.5

5. Process All (Extract everything)
   python pdf_toolkit.py process-all <pdf_file> <output_folder>
   
   Extracts both images and text from the PDF.
   
   Examples:
     python pdf_toolkit.py process-all doc.pdf ./output

╔════════════════════════════════════════════════════════════╗
║  DOCUMENT VALIDATION:                                       ║
║  The compare command now validates that PDFs are related    ║
║  versions of the same document before comparing. This       ║
║  prevents accidental comparison of completely different     ║
║  documents. Use --force to skip validation if needed.       ║
╚════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════╗
║  For more help, visit: https://pymupdf.readthedocs.io      ║
╚════════════════════════════════════════════════════════════╝
    """)


def main():
    """Main entry point for the CLI"""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    try:
        if command == "extract-images":
            if len(sys.argv) < 4:
                print("❌ Error: Missing arguments for extract-images")
                print("Usage: python pdf_toolkit.py extract-images <pdf_file> <output_folder> [format]")
                sys.exit(1)
            
            pdf_file = sys.argv[2]
            output_folder = sys.argv[3]
            output_format = sys.argv[4] if len(sys.argv) >= 5 else None
            
            toolkit = PDFToolkit(pdf_file)
            toolkit.extract_images(output_folder, output_format)
            toolkit.close()
        
        elif command == "extract-text":
            if len(sys.argv) < 4:
                print("❌ Error: Missing arguments for extract-text")
                print("Usage: python pdf_toolkit.py extract-text <pdf_file> <output_folder> [mode] [format]")
                sys.exit(1)
            
            pdf_file = sys.argv[2]
            output_folder = sys.argv[3]
            mode = sys.argv[4] if len(sys.argv) >= 5 else "single"
            output_format = sys.argv[5] if len(sys.argv) >= 6 else "txt"
            
            toolkit = PDFToolkit(pdf_file)
            toolkit.extract_text(output_folder, mode, output_format)
            toolkit.close()
        
        elif command == "unflatten":
            if len(sys.argv) < 4:
                print("❌ Error: Missing arguments for unflatten")
                print("Usage: python pdf_toolkit.py unflatten <pdf_file> <output_pdf> [mode]")
                sys.exit(1)
            
            pdf_file = sys.argv[2]
            output_pdf = sys.argv[3]
            mode = sys.argv[4] if len(sys.argv) >= 5 else "simple"
            
            toolkit = PDFToolkit(pdf_file)
            toolkit.unflatten(output_pdf, mode)
            toolkit.close()
        
        elif command == "compare":
            if len(sys.argv) < 4:
                print("❌ Error: Missing arguments for compare")
                print("Usage: python pdf_toolkit.py compare <pdf1> <pdf2> [output_folder] [--force] [--threshold X.X]")
                sys.exit(1)
            
            pdf1 = sys.argv[2]
            pdf2 = sys.argv[3]
            
            # Parse optional arguments
            output_folder = "./comparison_output"
            force_compare = False
            similarity_threshold = 0.3
            
            i = 4
            while i < len(sys.argv):
                arg = sys.argv[i]
                if arg == "--force":
                    force_compare = True
                elif arg == "--threshold":
                    if i + 1 < len(sys.argv):
                        try:
                            similarity_threshold = float(sys.argv[i + 1])
                            if not 0 <= similarity_threshold <= 1:
                                print("❌ Error: Threshold must be between 0.0 and 1.0")
                                sys.exit(1)
                            i += 1
                        except ValueError:
                            print("❌ Error: Invalid threshold value")
                            sys.exit(1)
                    else:
                        print("❌ Error: --threshold requires a value")
                        sys.exit(1)
                elif not arg.startswith("--"):
                    output_folder = arg
                i += 1
            
            PDFToolkit.compare_pdfs(pdf1, pdf2, output_folder, similarity_threshold, force_compare)
        
        elif command == "process-all":
            if len(sys.argv) < 4:
                print("❌ Error: Missing arguments for process-all")
                print("Usage: python pdf_toolkit.py process-all <pdf_file> <output_folder>")
                sys.exit(1)
            
            pdf_file = sys.argv[2]
            output_folder = sys.argv[3]
            
            print("🚀 Processing PDF: Extracting images and text...\n")
            
            toolkit = PDFToolkit(pdf_file)
            
            images_folder = os.path.join(output_folder, "images")
            text_folder = os.path.join(output_folder, "text")
            
            toolkit.extract_images(images_folder)
            toolkit.extract_text(text_folder)
            toolkit.close()
            
            print(f"✅ All processing complete! Output in: {output_folder}")
        
        else:
            print(f"❌ Unknown command: {command}")
            print_usage()
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()