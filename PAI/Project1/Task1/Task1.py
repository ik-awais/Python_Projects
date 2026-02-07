"""
Part 1: PDF Processing & Page Extraction
=========================================
Multi-Modal Document Intelligence System

This module handles PDF file processing including:
- Extracting specific pages from a PDF
- Saving extracted pages as individual PDF files
- Extracting images from specified pages
- Generating metadata reports

Required Libraries: PyPDF2, pdfplumber, pdf2image, Pillow
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

try:
    import PyPDF2
    from PyPDF2 import PdfReader, PdfWriter
except ImportError:
    print("Error: PyPDF2 is required. Install with: pip install PyPDF2")
    sys.exit(1)

try:
    import pdfplumber
except ImportError:
    print("Error: pdfplumber is required. Install with: pip install pdfplumber")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow is required. Install with: pip install Pillow")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    # Fallback if tqdm is not installed
    def tqdm(iterable, **kwargs):
        return iterable


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# Constants
# ============================================================

# Pages to extract (1-indexed as per requirement)
PAGES_TO_EXTRACT: List[int] = [1, 2, 3, 4, 5, 7, 10, 15, 16, 17, 18, 19]

# Pages from which to extract images (1-indexed)
IMAGE_EXTRACTION_PAGES: List[int] = [10, 15, 16, 17, 18, 19]


# ============================================================
# PDF Metadata Extraction
# ============================================================

def get_pdf_metadata(pdf_path: str) -> Dict:
    """
    Extract metadata from a PDF file.

    Args:
        pdf_path (str): Path to the input PDF file.

    Returns:
        Dict: Dictionary containing PDF metadata including
              total pages, file size, title, author, etc.

    Raises:
        FileNotFoundError: If the PDF file does not exist.
        PyPDF2.errors.PdfReadError: If the file is not a valid PDF.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    file_size_bytes = os.path.getsize(pdf_path)
    file_size_kb = file_size_bytes / 1024
    file_size_mb = file_size_kb / 1024

    metadata = {
        "file_path": pdf_path,
        "file_name": os.path.basename(pdf_path),
        "file_size_bytes": file_size_bytes,
        "file_size_kb": round(file_size_kb, 2),
        "file_size_mb": round(file_size_mb, 2),
    }

    # Read PDF-specific metadata using PyPDF2
    reader = PdfReader(pdf_path)
    metadata["total_pages"] = len(reader.pages)

    # Extract document info if available
    if reader.metadata:
        metadata["title"] = reader.metadata.get("/Title", "N/A")
        metadata["author"] = reader.metadata.get("/Author", "N/A")
        metadata["subject"] = reader.metadata.get("/Subject", "N/A")
        metadata["creator"] = reader.metadata.get("/Creator", "N/A")
        metadata["producer"] = reader.metadata.get("/Producer", "N/A")
    else:
        metadata["title"] = "N/A"
        metadata["author"] = "N/A"
        metadata["subject"] = "N/A"
        metadata["creator"] = "N/A"
        metadata["producer"] = "N/A"

    logger.info(f"Metadata extracted for: {metadata['file_name']}")
    logger.info(f"  Total pages: {metadata['total_pages']}")
    logger.info(f"  File size: {metadata['file_size_mb']} MB")

    return metadata


# ============================================================
# Page Extraction
# ============================================================

def extract_pages(
    pdf_path: str,
    pages: List[int],
    output_dir: str
) -> List[str]:
    """
    Extract specific pages from a PDF and save each as a separate PDF file.

    Pages are 1-indexed (page 1 is the first page of the document).
    Each extracted page is saved as 'page_X.pdf' in the output directory.

    Args:
        pdf_path (str): Path to the input PDF file.
        pages (List[int]): List of 1-indexed page numbers to extract.
        output_dir (str): Directory where extracted page PDFs will be saved.

    Returns:
        List[str]: List of file paths for the extracted page PDFs.

    Raises:
        FileNotFoundError: If the PDF file does not exist.
        ValueError: If any page number is out of range.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    extracted_files = []

    logger.info(f"Extracting {len(pages)} pages from '{pdf_path}'...")

    for page_num in tqdm(pages, desc="Extracting pages"):
        # Validate page number
        if page_num < 1 or page_num > total_pages:
            logger.warning(
                f"Page {page_num} is out of range (1-{total_pages}). Skipping."
            )
            continue

        # PyPDF2 uses 0-indexed pages
        page_index = page_num - 1
        page = reader.pages[page_index]

        # Create a new PDF writer for this single page
        writer = PdfWriter()
        writer.add_page(page)

        # Save the extracted page
        output_filename = f"page_{page_num}.pdf"
        output_path = os.path.join(output_dir, output_filename)

        with open(output_path, "wb") as output_file:
            writer.write(output_file)

        extracted_files.append(output_path)
        logger.info(f"  Extracted page {page_num} -> {output_path}")

    logger.info(f"Successfully extracted {len(extracted_files)} pages.")
    return extracted_files


# ============================================================
# Image Extraction from PDF Pages
# ============================================================

def extract_images_from_pages(
    pdf_path: str,
    pages: List[int],
    output_dir: str
) -> Tuple[List[str], int]:
    """
    Extract all images from specified pages of a PDF file.

    Uses pdfplumber to identify and extract images from each specified
    page. Images are saved as PNG files with descriptive filenames.

    Args:
        pdf_path (str): Path to the input PDF file.
        pages (List[int]): List of 1-indexed page numbers to extract images from.
        output_dir (str): Directory where extracted images will be saved.

    Returns:
        Tuple[List[str], int]: A tuple containing:
            - List of file paths for extracted images
            - Total number of images found across all pages

    Raises:
        FileNotFoundError: If the PDF file does not exist.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Create images output directory
    images_dir = os.path.join(output_dir, "extracted_images")
    os.makedirs(images_dir, exist_ok=True)

    extracted_image_files = []
    total_images_found = 0

    logger.info(f"Extracting images from pages {pages}...")

    with pdfplumber.open(pdf_path) as pdf:
        total_pdf_pages = len(pdf.pages)

        for page_num in tqdm(pages, desc="Extracting images"):
            # Validate page number
            if page_num < 1 or page_num > total_pdf_pages:
                logger.warning(
                    f"Page {page_num} out of range. Skipping image extraction."
                )
                continue

            # pdfplumber uses 0-indexed pages
            page = pdf.pages[page_num - 1]
            page_images = page.images

            if not page_images:
                logger.info(f"  No images found on page {page_num}.")
                continue

            logger.info(
                f"  Found {len(page_images)} image(s) on page {page_num}."
            )

            for img_index, img in enumerate(page_images):
                total_images_found += 1

                # Extract image bounding box information
                x0 = img.get("x0", 0)
                y0 = img.get("top", 0)
                x1 = img.get("x1", 0)
                y1 = img.get("bottom", 0)

                # Crop the image region from the page
                # Convert page to image first, then crop
                page_image = page.to_image(resolution=300)
                
                # Calculate crop coordinates
                crop_bbox = (
                    int(x0 * 300 / 72),   # Convert PDF points to pixels
                    int(y0 * 300 / 72),
                    int(x1 * 300 / 72),
                    int(y1 * 300 / 72)
                )

                # Crop and save the image
                cropped = page_image.original.crop(crop_bbox)
                
                # Generate descriptive filename
                img_filename = f"page{page_num}_image{img_index + 1}.png"
                img_path = os.path.join(images_dir, img_filename)
                
                cropped.save(img_path, "PNG")
                extracted_image_files.append(img_path)

                logger.info(
                    f"    Saved image {img_index + 1} from page {page_num} "
                    f"-> {img_path}"
                )

    logger.info(
        f"Total images extracted: {len(extracted_image_files)} "
        f"(found {total_images_found} across all pages)"
    )

    return extracted_image_files, total_images_found


# ============================================================
# Alternative Image Extraction using PyPDF2
# ============================================================

def extract_images_pypdf2(
    pdf_path: str,
    pages: List[int],
    output_dir: str
) -> Tuple[List[str], int]:
    """
    Extract embedded images from PDF pages using PyPDF2.

    This is an alternative approach that extracts images embedded
    directly in the PDF's internal structure (XObject images).

    Args:
        pdf_path (str): Path to the input PDF file.
        pages (List[int]): List of 1-indexed page numbers.
        output_dir (str): Directory for saving extracted images.

    Returns:
        Tuple[List[str], int]: Paths of extracted images and count.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    images_dir = os.path.join(output_dir, "extracted_images_pypdf2")
    os.makedirs(images_dir, exist_ok=True)

    reader = PdfReader(pdf_path)
    extracted_files = []
    image_count = 0

    for page_num in tqdm(pages, desc="Extracting images (PyPDF2)"):
        if page_num < 1 or page_num > len(reader.pages):
            continue

        page = reader.pages[page_num - 1]

        # Check if page has XObject resources containing images
        if "/XObject" not in page.get("/Resources", {}):
            continue

        x_objects = page["/Resources"]["/XObject"].get_object()

        for obj_name in x_objects:
            obj = x_objects[obj_name].get_object()

            # Check if the XObject is an image
            if obj.get("/Subtype") == "/Image":
                image_count += 1

                # Determine image format
                width = obj.get("/Width", 0)
                height = obj.get("/Height", 0)
                color_space = obj.get("/ColorSpace", "/DeviceRGB")

                # Extract image data
                data = obj.get_data()

                # Determine the appropriate file extension
                filters = obj.get("/Filter", "")
                if isinstance(filters, list):
                    filter_name = filters[0] if filters else ""
                else:
                    filter_name = filters

                if filter_name == "/DCTDecode":
                    # JPEG image
                    ext = "jpg"
                elif filter_name == "/FlateDecode":
                    # PNG-like image
                    ext = "png"
                elif filter_name == "/JPXDecode":
                    # JPEG 2000
                    ext = "jp2"
                else:
                    ext = "png"

                # Save the image
                img_filename = (
                    f"page{page_num}_xobj_{obj_name.strip('/')}_{image_count}.{ext}"
                )
                img_path = os.path.join(images_dir, img_filename)

                if ext == "jpg":
                    with open(img_path, "wb") as f:
                        f.write(data)
                else:
                    # For non-JPEG, try to reconstruct the image
                    try:
                        if color_space == "/DeviceRGB":
                            mode = "RGB"
                        elif color_space == "/DeviceGray":
                            mode = "L"
                        else:
                            mode = "RGB"

                        img = Image.frombytes(mode, (width, height), data)
                        img.save(img_path)
                    except Exception as e:
                        logger.warning(
                            f"Could not reconstruct image: {e}. "
                            f"Saving raw data."
                        )
                        with open(img_path, "wb") as f:
                            f.write(data)

                extracted_files.append(img_path)
                logger.info(
                    f"  Extracted XObject image from page {page_num}: "
                    f"{img_filename} ({width}x{height})"
                )

    return extracted_files, image_count


# ============================================================
# Metadata Report Generation
# ============================================================

def generate_metadata_report(
    pdf_path: str,
    extracted_pages: List[str],
    extracted_images: List[str],
    total_images_found: int,
    output_dir: str,
    processing_time: float
) -> str:
    """
    Generate a comprehensive metadata report for the PDF processing.

    The report includes file information, extraction statistics,
    and a listing of all output files created during processing.

    Args:
        pdf_path (str): Path to the original PDF file.
        extracted_pages (List[str]): List of extracted page file paths.
        extracted_images (List[str]): List of extracted image file paths.
        total_images_found (int): Total number of images found.
        output_dir (str): Output directory path.
        processing_time (float): Time taken for processing in seconds.

    Returns:
        str: Path to the generated metadata report file.
    """
    metadata = get_pdf_metadata(pdf_path)

    report_lines = [
        "=" * 70,
        "    PDF PROCESSING METADATA REPORT",
        "=" * 70,
        "",
        "--- File Information ---",
        f"  File Name:        {metadata['file_name']}",
        f"  File Path:        {metadata['file_path']}",
        f"  File Size:        {metadata['file_size_bytes']} bytes "
        f"({metadata['file_size_kb']} KB / {metadata['file_size_mb']} MB)",
        f"  Total Pages:      {metadata['total_pages']}",
        "",
        "--- Document Metadata ---",
        f"  Title:            {metadata.get('title', 'N/A')}",
        f"  Author:           {metadata.get('author', 'N/A')}",
        f"  Subject:          {metadata.get('subject', 'N/A')}",
        f"  Creator:          {metadata.get('creator', 'N/A')}",
        f"  Producer:         {metadata.get('producer', 'N/A')}",
        "",
        "--- Extraction Summary ---",
        f"  Pages Extracted:          {len(extracted_pages)}",
        f"  Pages Requested:          {PAGES_TO_EXTRACT}",
        f"  Total Images Found:       {total_images_found}",
        f"  Images Successfully Saved: {len(extracted_images)}",
        f"  Image Source Pages:        {IMAGE_EXTRACTION_PAGES}",
        "",
        "--- Processing Time ---",
        f"  Total Processing Time:    {processing_time:.2f} seconds",
        "",
        "--- Extracted Page Files ---",
    ]

    for page_file in extracted_pages:
        file_size = os.path.getsize(page_file) if os.path.exists(page_file) else 0
        report_lines.append(
            f"  {os.path.basename(page_file):30s} "
            f"({file_size / 1024:.1f} KB)"
        )

    report_lines.append("")
    report_lines.append("--- Extracted Image Files ---")

    for img_file in extracted_images:
        file_size = os.path.getsize(img_file) if os.path.exists(img_file) else 0
        report_lines.append(
            f"  {os.path.basename(img_file):30s} "
            f"({file_size / 1024:.1f} KB)"
        )

    report_lines.extend(["", "=" * 70])

    # Write report to file
    report_path = os.path.join(output_dir, "pdf_metadata_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    # Also save as JSON for programmatic access
    json_report = {
        "metadata": metadata,
        "extraction_summary": {
            "pages_extracted": len(extracted_pages),
            "pages_requested": PAGES_TO_EXTRACT,
            "total_images_found": total_images_found,
            "images_saved": len(extracted_images),
            "image_source_pages": IMAGE_EXTRACTION_PAGES,
        },
        "extracted_page_files": extracted_pages,
        "extracted_image_files": extracted_images,
        "processing_time_seconds": round(processing_time, 2),
    }

    json_path = os.path.join(output_dir, "pdf_metadata_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_report, f, indent=2)

    logger.info(f"Metadata report saved to: {report_path}")
    logger.info(f"JSON report saved to: {json_path}")

    return report_path


# ============================================================
# Main Processing Function
# ============================================================

def process_pdf(pdf_path: str, output_dir: str) -> Dict:
    """
    Main function to run the complete PDF processing pipeline.

    This function orchestrates the entire Part 1 workflow:
    1. Validate input file
    2. Extract specified pages as individual PDFs
    3. Extract images from specified pages
    4. Generate metadata report

    Args:
        pdf_path (str): Path to the input PDF file.
        output_dir (str): Root output directory for all results.

    Returns:
        Dict: Summary dictionary with processing results including
              extracted file paths and statistics.

    Raises:
        FileNotFoundError: If the input PDF does not exist.
        Exception: For any processing errors.
    """
    start_time = time.time()

    print("\n" + "=" * 60)
    print("  PART 1: PDF PROCESSING & PAGE EXTRACTION")
    print("=" * 60)

    # Validate input
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Input PDF not found: {pdf_path}")

    # Create output directories
    pages_dir = os.path.join(output_dir, "extracted_pages")
    os.makedirs(pages_dir, exist_ok=True)

    # Step 1: Extract specific pages
    print("\n[Step 1/3] Extracting pages...")
    extracted_pages = extract_pages(pdf_path, PAGES_TO_EXTRACT, pages_dir)

    # Step 2: Extract images from specified pages
    print("\n[Step 2/3] Extracting images from pages...")
    extracted_images, total_images = extract_images_from_pages(
        pdf_path, IMAGE_EXTRACTION_PAGES, output_dir
    )

    # Step 3: Generate metadata report
    processing_time = time.time() - start_time
    print("\n[Step 3/3] Generating metadata report...")
    report_path = generate_metadata_report(
        pdf_path,
        extracted_pages,
        extracted_images,
        total_images,
        output_dir,
        processing_time
    )

    # Summary
    total_time = time.time() - start_time
    summary = {
        "extracted_pages": extracted_pages,
        "extracted_images": extracted_images,
        "total_images_found": total_images,
        "report_path": report_path,
        "processing_time": total_time,
    }

    print(f"\n  PDF Processing Complete!")
    print(f"  Pages extracted: {len(extracted_pages)}")
    print(f"  Images extracted: {len(extracted_images)}")
    print(f"  Time elapsed: {total_time:.2f}s")
    print(f"  Report: {report_path}")

    return summary


# ============================================================
# Script Entry Point
# ============================================================

if __name__ == "__main__":
    """
    Run Part 1 as a standalone script.
    
    Usage:
        python pdf_processing.py <input_pdf> [output_directory]
    
    Examples:
        python pdf_processing.py research_paper.pdf
        python pdf_processing.py research_paper.pdf ./output
    """
    if len(sys.argv) < 2:
        print("Usage: python pdf_processing.py <input_pdf> [output_directory]")
        print("Example: python pdf_processing.py research_paper.pdf ./output")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_directory = sys.argv[2] if len(sys.argv) > 2 else "./output"

    try:
        results = process_pdf(input_pdf, output_directory)
        print("\nPart 1 completed successfully!")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error during PDF processing: {e}")
        sys.exit(1)
