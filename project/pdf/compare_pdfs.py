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
from typing import Optional, Dict, Any, Tuple
from PIL import Image
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from difflib import SequenceMatcher


# ---------------------------------------------------------------------------
# Text-cleaning helper
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """
    Replace characters that standard PDF fonts (Helvetica, Courier, etc.)
    cannot render — they would appear as solid black boxes (■) in the output.

    Sources of problem characters:
      • PDF ligature glyphs  – fi, fl, ff, ffi, ffl stored as single Unicode
        code-points in the "Alphabetic Presentation Forms" block (U+FB00–U+FB06).
      • Private-Use Area     – U+E000–U+F8FF: font-specific symbols with no
        standard glyph.
      • Unicode replacement  – U+FFFD (the classic "?" diamond).
      • Other common symbols – bullets, dashes, smart-quotes, etc. that are
        outside the WinAnsiEncoding range of the standard Type-1 fonts.
    """
    if not text:
        return text

    # ── Ligatures (U+FB00 – U+FB06) ──────────────────────────────────────
    ligature_map = {
        '\uFB00': 'ff',
        '\uFB01': 'fi',
        '\uFB02': 'fl',
        '\uFB03': 'ffi',
        '\uFB04': 'ffl',
        '\uFB05': 'st',
        '\uFB06': 'st',
    }
    for ch, replacement in ligature_map.items():
        text = text.replace(ch, replacement)

    # ── Unicode replacement character ─────────────────────────────────────
    text = text.replace('\uFFFD', '?')

    # ── Smart quotes → straight quotes ───────────────────────────────────
    text = (text
            .replace('\u2018', "'").replace('\u2019', "'")   # '' → '
            .replace('\u201C', '"').replace('\u201D', '"')   # "" → "
            .replace('\u201A', ',').replace('\u201E', '"'))

    # ── Common typographic symbols ────────────────────────────────────────
    text = (text
            .replace('\u2013', '-')    # en dash
            .replace('\u2014', '--')   # em dash
            .replace('\u2022', '*')    # bullet •
            .replace('\u2026', '...')  # ellipsis …
            .replace('\u00B7', '.')    # middle dot ·
            .replace('\u2212', '-')    # minus sign −
            .replace('\u00A0', ' '))   # non-breaking space

    # ── Private-Use Area (U+E000 – U+F8FF) ───────────────────────────────
    # These are font-specific glyphs with no universal meaning; drop them.
    cleaned = []
    for ch in text:
        cp = ord(ch)
        if 0xE000 <= cp <= 0xF8FF:
            continue          # discard private-use characters entirely
        cleaned.append(ch)
    text = ''.join(cleaned)

    # ── Remaining non-WinAnsi characters (> U+00FF, not already handled) ─
    # Keep printable ASCII + Latin-1 supplement; replace everything else
    # with '?' so no boxes appear.
    result = []
    for ch in text:
        cp = ord(ch)
        if cp <= 0x00FF or ch in ('\n', '\r', '\t'):
            result.append(ch)
        else:
            # Character is already handled above (ligatures, dashes, etc.)
            # or is something else outside Latin-1 → replace with '?'
            result.append('?')
    return ''.join(result)


class PDFToolkit:
    """Comprehensive PDF processing toolkit"""

    def __init__(self, pdf_path: str) -> None:
        """
        Initialize the toolkit with a PDF file.

        Args:
            pdf_path (str): Path to the PDF file
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(
                f"PDF file '{pdf_path}' not found!"
            )

        self.pdf_path = pdf_path
        self.pdf_document = None
        self.pdf_basename = os.path.splitext(
            os.path.basename(pdf_path)
        )[0]

    def open(self):
        """Open the PDF document"""
        if self.pdf_document is None:
            self.pdf_document = fitz.open(self.pdf_path)
        return self.pdf_document

    def close(self) -> None:
        """Close the PDF document"""
        if self.pdf_document is not None:
            self.pdf_document.close()
            self.pdf_document = None

    # ==================== IMAGE EXTRACTION ====================

    def extract_images(
        self,
        output_folder: str,
        output_format: Optional[str] = None
    ) -> int:
        """
        Extract all images from the PDF.

        Args:
            output_folder (str): Folder to save extracted images
            output_format (str): Optional format ('png' or 'jpg')

        Returns:
            int: Number of images extracted
        """
        try:
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
                    print(
                        f"Page {page_num + 1}: "
                        f"Found {len(image_list)} image(s)"
                    )

                for img_index, img in enumerate(image_list):
                    xref = img[0]

                    try:
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]

                        image_count += 1

                        if output_format:
                            pil_image = Image.open(
                                io.BytesIO(image_bytes)
                            )

                            if (output_format == 'jpg' and
                                    pil_image.mode == 'RGBA'):
                                pil_image = pil_image.convert('RGB')

                            image_filename = (
                                f"page{page_num + 1}_"
                                f"img{img_index + 1}.{output_format}"
                            )
                            image_path = os.path.join(
                                output_folder, image_filename
                            )

                            if output_format == 'png':
                                pil_image.save(image_path, 'PNG')
                            else:
                                pil_image.save(
                                    image_path, 'JPEG', quality=95
                                )
                        else:
                            image_filename = (
                                f"page{page_num + 1}_"
                                f"img{img_index + 1}.{image_ext}"
                            )
                            image_path = os.path.join(
                                output_folder, image_filename
                            )

                            with open(image_path, "wb") as img_file:
                                img_file.write(image_bytes)

                        print(f"  ✓ Saved: {image_filename}")

                    except Exception as e:
                        print(
                            f"  ✗ Error extracting image "
                            f"{img_index + 1}: {e}"
                        )

            print(f"\n{'=' * 60}")
            print(f"✅ Extraction complete! Total images: {image_count}")
            print(f"{'=' * 60}\n")

            return image_count

        except Exception as e:
            print(f"❌ Error extracting images: {e}")
            raise

    # ==================== TEXT EXTRACTION ====================

    def extract_text(
        self,
        output_folder: str,
        mode: str = "single",
        output_format: str = "txt"
    ) -> int:
        try:
            os.makedirs(output_folder, exist_ok=True)
            print(f"📁 Output folder: {output_folder}")

            doc = self.open()
            print(f"📄 Processing: {self.pdf_path}")
            print(f"📖 Total pages: {len(doc)}\n")

            if mode == "pages":
                return self._extract_text_by_page(doc, output_folder)
            else:
                return self._extract_text_single(
                    doc, output_folder, output_format
                )

        except Exception as e:
            print(f"❌ Error extracting text: {e}")
            raise

    def _extract_text_single(self, doc, output_folder: str, output_format: str) -> int:
        output_filename = (
            f"{self.pdf_basename}_extracted_text.{output_format}"
        )
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
                    all_text.append(
                        f"\n{'=' * 60}\nPAGE {page_num + 1}\n{'=' * 60}\n"
                    )

                all_text.append(text)
                total_chars += len(text)
            else:
                print(f"Page {page_num + 1}: No text found")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(''.join(all_text))

        print(f"\n{'=' * 60}")
        print("✅ Text extraction complete!")
        print(f"📄 Output file: {output_path}")
        print(f"📊 Total characters: {total_chars}")
        print(f"{'=' * 60}\n")

        return total_chars

    def _extract_text_by_page(self, doc, output_folder: str) -> int:
        pages_with_text = 0
        total_chars = 0

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()

            if text.strip():
                output_filename = (
                    f"{self.pdf_basename}_page{page_num + 1}.txt"
                )
                output_path = os.path.join(output_folder, output_filename)

                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(text)

                print(
                    f"Page {page_num + 1}: Saved {len(text)} "
                    f"characters to {output_filename}"
                )
                pages_with_text += 1
                total_chars += len(text)
            else:
                print(f"Page {page_num + 1}: No text found (skipped)")

        print(f"\n{'=' * 60}")
        print("✅ Text extraction complete!")
        print(f"📊 Pages with text: {pages_with_text}/{len(doc)}")
        print(f"📊 Total characters: {total_chars}")
        print(f"📁 Files saved to: {output_folder}")
        print(f"{'=' * 60}\n")

        return total_chars

    # ==================== PDF UNFLATTENING ====================

    def unflatten(self, output_pdf_path: str, mode: str = "simple") -> bool:
        try:
            if mode == "rebuild":
                return self._unflatten_rebuild(output_pdf_path)
            else:
                return self._unflatten_simple(output_pdf_path)

        except Exception as e:
            print(f"❌ Error unflattening PDF: {e}")
            raise

    def _unflatten_simple(self, output_pdf_path: str) -> bool:
        doc = self.open()

        print(f"📄 Processing: {self.pdf_path}")
        print(f"📖 Total pages: {len(doc)}")
        print("🔄 Creating searchable PDF with text overlay...\n")

        output_doc = fitz.open()

        for page_num in range(len(doc)):
            page = doc[page_num]
            print(f"Processing page {page_num + 1}...")

            new_page = output_doc.new_page(
                width=page.rect.width,
                height=page.rect.height
            )

            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            new_page.insert_image(new_page.rect, pixmap=pix)

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

        output_doc.save(
            output_pdf_path, garbage=4, deflate=True, clean=True
        )
        output_doc.close()

        orig_size = os.path.getsize(self.pdf_path) / 1024
        new_size = os.path.getsize(output_pdf_path) / 1024

        print(f"{'=' * 60}")
        print("✅ Unflattening complete!")
        print(f"📄 Output: {output_pdf_path}")
        print(f"📊 Original: {orig_size:.2f} KB")
        print(f"📊 New: {new_size:.2f} KB")
        print(f"{'=' * 60}\n")

        return True

    def _unflatten_rebuild(self, output_pdf_path: str) -> bool:
        doc = self.open()
        temp_folder = "./temp_unflatten"

        os.makedirs(temp_folder, exist_ok=True)

        print(f"📄 Processing: {self.pdf_path}")
        print(f"📖 Total pages: {len(doc)}")
        print("🔄 Rebuilding PDF...\n")

        c = canvas.Canvas(output_pdf_path, pagesize=letter)

        for page_num in range(len(doc)):
            page = doc[page_num]
            print(f"Processing page {page_num + 1}...")

            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height

            c.setPageSize((page_width, page_height))

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
                                x0, y0, x1, y1 = (
                                    rect.x0, rect.y0, rect.x1, rect.y1
                                )
                                img_width = x1 - x0
                                img_height = y1 - y0
                                y_position = page_height - y1

                                temp_img_path = os.path.join(
                                    temp_folder,
                                    f"page{page_num + 1}_img{img_index + 1}.png"
                                )

                                pil_image = Image.open(io.BytesIO(image_bytes))
                                pil_image.save(temp_img_path, 'PNG')

                                c.drawImage(
                                    temp_img_path, x0, y_position,
                                    width=img_width, height=img_height,
                                    preserveAspectRatio=True,
                                    mask='auto'
                                )

                                print(f"    Added image {img_index + 1}")

                    except Exception as e:
                        print(f"    Warning: Could not add image {img_index + 1}: {e}")

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
                                    except Exception:
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

        orig_size = os.path.getsize(self.pdf_path) / 1024
        new_size = os.path.getsize(output_pdf_path) / 1024

        print(f"{'=' * 60}")
        print("✅ Unflattening complete!")
        print(f"📄 Output: {output_pdf_path}")
        print(f"📊 Original: {orig_size:.2f} KB")
        print(f"📊 New: {new_size:.2f} KB")
        print(f"{'=' * 60}\n")

        print("🧹 Cleaning up temporary files...")
        for file in os.listdir(temp_folder):
            os.remove(os.path.join(temp_folder, file))
        os.rmdir(temp_folder)
        print("✓ Cleanup complete!\n")

        return True

    @staticmethod
    def create_visual_comparison_pdf(
        pdf2_path: str,
        differences: list,
        output_path: str,
        total_pages: int
    ) -> None:
        try:
            doc2 = fitz.open(pdf2_path)
            output_doc = fitz.open()

            print("Creating visual comparison PDF...")

            diff_map = {}
            for diff in differences:
                page_num = diff.get('page')
                if page_num:
                    diff_map[page_num] = diff

            for page_num in range(len(doc2)):
                page = doc2[page_num]
                actual_page_num = page_num + 1

                new_page = output_doc.new_page(
                    width=page.rect.width,
                    height=page.rect.height
                )

                new_page.show_pdf_page(new_page.rect, doc2, page_num)

                if actual_page_num in diff_map:
                    diff = diff_map[actual_page_num]

                    if 'status' in diff:
                        label = diff['status']
                        color = (0, 0.8, 0)
                    else:
                        changes = []
                        if not diff.get('text_match', True):
                            changes.append("Text")
                        if not diff.get('images_match', True):
                            changes.append("Images")

                        if changes:
                            label = f"{' & '.join(changes)} Modified"
                            color = (1, 0.8, 0)
                        else:
                            label = None
                            color = None

                    if label:
                        rect = fitz.Rect(0, 0, page.rect.width, 30)
                        annot = new_page.add_rect_annot(rect)
                        annot.set_colors(stroke=color, fill=color)
                        annot.set_opacity(0.3)
                        annot.update()

                        text_point = fitz.Point(10, 20)
                        new_page.insert_text(
                            text_point,
                            f"! Page {actual_page_num}: {label}",
                            fontsize=12,
                            color=(0, 0, 0),
                            fontname="helv"
                        )

                        if 'text_changes' in diff and not diff.get('status'):
                            changes = diff['text_changes']
                            additions = changes.get('additions', [])

                            for line in additions:
                                clean_line = line.strip()
                                if len(clean_line) < 3:
                                    continue

                                quads = new_page.search_for(clean_line)
                                if quads:
                                    annot = new_page.add_highlight_annot(quads)
                                    annot.set_colors(stroke=(0.2, 0.8, 0.2))
                                    annot.update()

            output_doc.save(output_path, garbage=4, deflate=True)
            output_doc.close()
            doc2.close()

            print(f"✓ Visual comparison PDF created: {output_path}")

        except Exception as e:
            print(f"Error creating visual PDF: {e}")
            raise

    @staticmethod
    def _calculate_text_similarity(text1: str, text2: str) -> float:
        text1_clean = ' '.join(text1.split()).lower()
        text2_clean = ' '.join(text2.split()).lower()
        return SequenceMatcher(None, text1_clean, text2_clean).ratio()

    @staticmethod
    def _validate_documents_are_related(
        doc1, doc2, similarity_threshold: float = 0.3
    ) -> Tuple[bool, float, str]:
        sample_pages = min(3, len(doc1), len(doc2))

        if sample_pages == 0:
            return False, 0.0, "One or both PDFs are empty"

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

        if not text1_samples and not text2_samples:
            page_diff_ratio = (
                abs(len(doc1) - len(doc2)) / max(len(doc1), len(doc2))
            )
            if page_diff_ratio > 0.5:
                return (
                    False, 0.0,
                    "Both PDFs contain no text and have very different page counts"
                )
            return (
                True, 0.5,
                "Both PDFs contain no text but have similar page counts (image-only PDFs)"
            )

        if not text1_samples or not text2_samples:
            return (False, 0.0, "Only one PDF contains extractable text")

        similarities = []
        for t1, t2 in zip(text1_samples, text2_samples):
            sim = PDFToolkit._calculate_text_similarity(t1, t2)
            similarities.append(sim)

        avg_similarity = (
            sum(similarities) / len(similarities) if similarities else 0.0
        )

        if avg_similarity < similarity_threshold:
            return (
                False, avg_similarity,
                f"Content similarity too low ({avg_similarity:.1%}). "
                "These appear to be different documents."
            )

        return (True, avg_similarity, "Documents appear to be related versions")

    @staticmethod
    def compare_pdfs(
        pdf1_path: str,
        pdf2_path: str,
        output_folder: str = "./comparison_output",
        similarity_threshold: float = 0.3,
        force_compare: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Compare two PDFs and generate comparison report.
        Validates that PDFs are related versions before comparing.
        """
        try:
            os.makedirs(output_folder, exist_ok=True)

            print("📊 Comparing PDFs")
            print(f"📄 PDF 1 (Old): {pdf1_path}")
            print(f"📄 PDF 2 (New): {pdf2_path}\n")

            doc1 = fitz.open(pdf1_path)
            doc2 = fitz.open(pdf2_path)

            if not force_compare:
                print("🔍 Validating documents are related versions...")
                is_valid, similarity, reason = (
                    PDFToolkit._validate_documents_are_related(
                        doc1, doc2, similarity_threshold
                    )
                )

                print(f"   Similarity score: {similarity:.1%}")
                print(f"   {reason}\n")

                if not is_valid:
                    print(f"{'=' * 60}")
                    print("❌ VALIDATION FAILED")
                    print(f"{'=' * 60}")
                    print("\n⚠️  These PDFs appear to be completely different documents!")
                    print(f"   Similarity: {similarity:.1%} (threshold: {similarity_threshold:.1%})")
                    print(f"   Reason: {reason}")
                    print("\n💡 Tips:")
                    print("   • Make sure you're comparing the old and new versions of the SAME document")
                    print("   • Check that you haven't accidentally selected a different file")
                    print("   • If you're sure these are related, use --force flag to skip validation")
                    print("\nComparison aborted.\n")

                    doc1.close()
                    doc2.close()
                    return None

                print("✅ Validation passed! Proceeding with comparison...\n")
            else:
                print("⚠️  Skipping validation (forced comparison)\n")

            results: Dict[str, Any] = {
                'pdf1': pdf1_path,
                'pdf2': pdf2_path,
                'pages1': len(doc1),
                'pages2': len(doc2),
                'differences': [],
                'validation': {
                    'forced': force_compare,
                    'similarity': (similarity if not force_compare else 'N/A')
                }
            }

            print(f"PDF 1: {len(doc1)} pages")
            print(f"PDF 2: {len(doc2)} pages\n")

            max_pages = max(len(doc1), len(doc2))

            for page_num in range(max_pages):
                diff: Dict[str, Any] = {'page': page_num + 1}

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

                # ── Extract and CLEAN text before any comparison or storage ──
                # clean_text() replaces ligatures (fi→fi, fl→fl, etc.) and
                # private-use characters that would render as boxes in the report.
                raw_text1 = page1.get_text()
                raw_text2 = page2.get_text()
                text1 = clean_text(raw_text1)
                text2 = clean_text(raw_text2)

                text_match = text1 == text2
                diff['text_match'] = text_match

                if not text_match and text1.strip() and text2.strip():
                    page_similarity = PDFToolkit._calculate_text_similarity(text1, text2)
                    diff['text_similarity'] = page_similarity

                    import difflib
                    text1_lines = text1.splitlines()
                    text2_lines = text2.splitlines()

                    differ = difflib.Differ()
                    text_diff = list(differ.compare(text1_lines, text2_lines))

                    # Limit to first 5 additions / deletions
                    additions = [line[2:] for line in text_diff if line.startswith('+ ')][:5]
                    deletions = [line[2:] for line in text_diff if line.startswith('- ')][:5]

                    if additions or deletions:
                        diff['text_changes'] = {
                            'additions': additions,
                            'deletions': deletions
                        }

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
                            status.append(
                                f"Text changed (similarity: {diff['text_similarity']:.1%})"
                            )
                        else:
                            status.append("Text changed")
                    if not diff['images_match']:
                        status.append(f"Images differ ({images1} → {images2})")

                    print(f"Page {page_num + 1}: {', '.join(status)}")
                else:
                    print(f"Page {page_num + 1}: Identical")

            doc1.close()
            doc2.close()

            # ── Write the comparison report ───────────────────────────────
            report_path = os.path.join(output_folder, "comparison_report.txt")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write("                    PDF COMPARISON SUMMARY\n")
                f.write("=" * 70 + "\n\n")

                f.write(f"Old Version: {os.path.basename(pdf1_path)} ({results['pages1']} pages)\n")
                f.write(f"New Version: {os.path.basename(pdf2_path)} ({results['pages2']} pages)\n\n")

                if not force_compare:
                    f.write(
                        f"Document Similarity: {results['validation']['similarity']:.1%}\n\n"
                    )

                changes_count = len(results['differences'])
                identical_count = max_pages - changes_count
                f.write(f"Changes Found: {changes_count} page(s) modified\n")
                f.write(f"Identical Pages: {identical_count} page(s)\n\n")

                f.write("-" * 70 + "\n")
                f.write("PAGE-BY-PAGE SUMMARY\n")
                f.write("-" * 70 + "\n\n")

                diff_map = {diff['page']: diff for diff in results['differences']}

                for page_num in range(1, max_pages + 1):
                    if page_num in diff_map:
                        diff = diff_map[page_num]

                        if 'status' in diff:
                            f.write(f"  Page {page_num:3d}: {diff['status']}\n")
                        else:
                            changes = []
                            if not diff.get('text_match', True):
                                changes.append("Text modified")
                            if not diff.get('images_match', True):
                                changes.append("Images modified")

                            change_str = " & ".join(changes) if changes else "Modified"
                            f.write(f"  Page {page_num:3d}: [!] {change_str}\n")

                            # ── Inline diff text right under the page entry ──
                            # This is the key fix: show what actually changed
                            # here in the summary, not only in the detailed section.
                            if 'text_changes' in diff:
                                tc = diff['text_changes']

                                for deletion in tc.get('deletions', []):
                                    # Truncate long lines for readability
                                    truncated = (deletion[:90] + '...') if len(deletion) > 90 else deletion
                                    f.write(f"           REMOVE: {truncated}\n")

                                for addition in tc.get('additions', []):
                                    truncated = (addition[:90] + '...') if len(addition) > 90 else addition
                                    f.write(f"           ADD:    {truncated}\n")

                            if not diff.get('images_match', True):
                                f.write(
                                    f"           Images: {diff['images1']} → {diff['images2']}\n"
                                )
                    else:
                        f.write(f"  Page {page_num:3d}: [OK] No changes\n")

                # ── Detailed analysis (kept for completeness) ─────────────
                if results['differences']:
                    f.write("\n" + "=" * 70 + "\n")
                    f.write("DETAILED ANALYSIS\n")
                    f.write("=" * 70 + "\n\n")

                    for diff in results['differences']:
                        f.write(f"Page {diff['page']}:\n")
                        if 'status' in diff:
                            f.write(f"  Status: {diff['status']}\n")
                        else:
                            f.write(f"  Text Match: {'Yes' if diff['text_match'] else 'No'}\n")
                            if 'text_similarity' in diff:
                                f.write(f"  Text Similarity: {diff['text_similarity']:.1%}\n")

                            if 'text_changes' in diff:
                                tc = diff['text_changes']
                                if tc.get('deletions'):
                                    f.write("  Removed Text:\n")
                                    for deletion in tc['deletions']:
                                        truncated = (deletion[:100] + '...') if len(deletion) > 100 else deletion
                                        f.write(f"    REMOVE: {truncated}\n")
                                if tc.get('additions'):
                                    f.write("  Added Text:\n")
                                    for addition in tc['additions']:
                                        truncated = (addition[:100] + '...') if len(addition) > 100 else addition
                                        f.write(f"    ADD: {truncated}\n")

                            f.write(f"  Images: {diff['images1']} → {diff['images2']}\n")
                            f.write(f"  Images Match: {'Yes' if diff['images_match'] else 'No'}\n")
                        f.write("\n")

            print(f"\n{'=' * 60}")
            print("✅ Comparison complete!")
            print(f"📄 Report saved: {report_path}")
            print(f"📊 Total differences: {len(results['differences'])}")
            print(f"📊 Identical pages: {max_pages - len(results['differences'])}")
            print(f"{'=' * 60}\n")

            return results

        except Exception as e:
            print(f"❌ Error comparing PDFs: {e}")
            raise


# ============ COMPATIBILITY WRAPPER FOR SERVER.PY ============


def compare_pdfs(
    pdf1_path: str,
    pdf2_path: str,
    output_folder: Optional[str] = None,
    similarity_threshold: float = 0.3,
    force_compare: bool = False
) -> Dict[str, Any]:
    """
    Wrapper function for backward compatibility with server.py.
    """
    import tempfile

    try:
        if output_folder is None:
            output_folder = tempfile.mkdtemp(prefix="pdf_comparison_")
        else:
            os.makedirs(output_folder, exist_ok=True)

        result = PDFToolkit.compare_pdfs(
            pdf1_path,
            pdf2_path,
            output_folder,
            similarity_threshold,
            force_compare
        )

        if result is None:
            return {
                "success": False,
                "message": (
                    "Document validation failed. These PDFs appear "
                    "to be completely different documents."
                ),
                "error": (
                    "Validation failed - documents are not related "
                    "versions of the same document"
                )
            }

        comparison_log = os.path.join(output_folder, "comparison_report.txt")

        result_pdf = os.path.join(output_folder, "comparison_visual.pdf")

        try:
            PDFToolkit.create_visual_comparison_pdf(
                pdf2_path,
                result['differences'],
                result_pdf,
                result['pages2']
            )
        except Exception as e:
            print(f"Warning: Could not create visual PDF: {e}")
            result_pdf = comparison_log

        return {
            "success": True,
            "message": (
                f"Comparison complete. Found "
                f"{len(result['differences'])} differences."
            ),
            "details": {
                "comparison": {
                    "result_pdf": (
                        result_pdf if os.path.exists(result_pdf)
                        else comparison_log
                    ),
                    "log_file": comparison_log,
                    "total_pages": max(result['pages1'], result['pages2']),
                    "differences_count": len(result['differences']),
                    "validation": result.get('validation', {})
                }
            },
            "result": result
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": f"Comparison failed: {str(e)}",
            "error": str(e)
        }


def print_usage() -> None:
    print("""
╔════════════════════════════════════════════════════════════╗
║              INTEGRATED PDF TOOLKIT                         ║
╚════════════════════════════════════════════════════════════╝

USAGE:
    python pdf_toolkit.py <command> [arguments]

COMMANDS:

1. Extract Images
   python pdf_toolkit.py extract-images <pdf_file> <output_folder> [format]

2. Extract Text
   python pdf_toolkit.py extract-text <pdf_file> <output_folder> [mode] [format]

3. Unflatten PDF
   python pdf_toolkit.py unflatten <pdf_file> <output_pdf> [mode]

4. Compare PDFs (with validation)
   python pdf_toolkit.py compare <pdf1> <pdf2> [output_folder] [--force] [--threshold X.X]

5. Process All (Extract everything)
   python pdf_toolkit.py process-all <pdf_file> <output_folder>

╔════════════════════════════════════════════════════════════╗
║  For more help, visit: https://pymupdf.readthedocs.io      ║
╚════════════════════════════════════════════════════════════╝
    """)


def main() -> None:
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()

    try:
        if command == "extract-images":
            if len(sys.argv) < 4:
                print("❌ Error: Missing arguments for extract-images")
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
                sys.exit(1)

            pdf1 = sys.argv[2]
            pdf2 = sys.argv[3]

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

            PDFToolkit.compare_pdfs(
                pdf1, pdf2, output_folder,
                similarity_threshold, force_compare
            )

        elif command == "process-all":
            if len(sys.argv) < 4:
                print("❌ Error: Missing arguments for process-all")
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