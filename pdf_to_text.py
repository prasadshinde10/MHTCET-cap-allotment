#!/usr/bin/env python3
"""
PDF Text Extractor
Extracts text from a PDF file and saves it into a text file (.txt).
"""

import sys
import os
from pathlib import Path

def _process_page_text(page_text: str, skip_top_lines: int = 7, is_last_page: bool = False) -> str:
    """Removes first `skip_top_lines` lines and bottom lines (3 for normal pages, 2 for last page)."""
    if not page_text:
        return ""
    lines = page_text.splitlines()
    
    # Skip top lines
    lines = lines[skip_top_lines:]
    
    # Determine how many lines to remove from bottom
    skip_bottom_lines = 2 if is_last_page else 3
    
    if skip_bottom_lines > 0 and len(lines) >= skip_bottom_lines:
        lines = lines[:-skip_bottom_lines]
    elif skip_bottom_lines > 0:
        lines = []

    return "\n".join(lines)


def extract_text_pypdf(pdf_path: str, skip_top_lines: int = 7) -> str:
    """Extract text from PDF using pypdf library, skipping header and footer lines."""
    import pypdf
    reader = pypdf.PdfReader(pdf_path)
    text_content = []
    
    total_pages = len(reader.pages)
    print(f"Processing {total_pages} page(s)...")
    
    for idx, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text()
        is_last = (idx == total_pages)
        processed_text = _process_page_text(raw_text, skip_top_lines=skip_top_lines, is_last_page=is_last)
        
        if processed_text.strip():
            text_content.append(f"--- Page {idx} ---\n{processed_text}\n")
        else:
            text_content.append(f"--- Page {idx} ---\n[No extractable text found after trimming]\n")
            
    return "\n".join(text_content)


def extract_text_pdfplumber(pdf_path: str, skip_top_lines: int = 7) -> str:
    """Extract text from PDF using pdfplumber library as fallback, skipping header and footer lines."""
    import pdfplumber
    text_content = []
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Processing {total_pages} page(s)...")
        for idx, page in enumerate(pdf.pages, start=1):
            raw_text = page.extract_text()
            is_last = (idx == total_pages)
            processed_text = _process_page_text(raw_text, skip_top_lines=skip_top_lines, is_last_page=is_last)
            
            if processed_text.strip():
                text_content.append(f"--- Page {idx} ---\n{processed_text}\n")
            else:
                text_content.append(f"--- Page {idx} ---\n[No extractable text found after trimming]\n")
                
    return "\n".join(text_content)


def extract_text_pymupdf(pdf_path: str, skip_top_lines: int = 7) -> str:
    """Extract text from PDF using PyMuPDF library, skipping header and footer lines."""
    import pymupdf
    doc = pymupdf.open(pdf_path)
    text_content = []
    
    total_pages = len(doc)
    print(f"Processing {total_pages} page(s) with PyMuPDF...")
    
    for idx, page in enumerate(doc, start=1):
        raw_text = page.get_text()
        is_last = (idx == total_pages)
        processed_text = _process_page_text(raw_text, skip_top_lines=skip_top_lines, is_last_page=is_last)
        
        if processed_text.strip():
            text_content.append(f"--- Page {idx} ---\n{processed_text}\n")
        else:
            text_content.append(f"--- Page {idx} ---\n[No extractable text found after trimming]\n")
            
    return "\n".join(text_content)


def extract_pdf_to_text(pdf_path: str, output_path: str = None) -> str:
    """
    Extracts text from a PDF file and writes to output_path.
    If output_path is not specified, generates one with .txt extension.
    """
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"Input PDF file not found: {pdf_path}")
        
    if not output_path:
        output_path = pdf_file.with_suffix('.txt')
    else:
        output_path = Path(output_path)

    # Attempt extraction
    extracted_text = None
    
    # Try pymupdf first, then pypdf, then pdfplumber
    try:
        extracted_text = extract_text_pymupdf(str(pdf_file))
    except ImportError:
        try:
            extracted_text = extract_text_pypdf(str(pdf_file))
        except ImportError:
            try:
                extracted_text = extract_text_pdfplumber(str(pdf_file))
            except ImportError:
                raise RuntimeError(
                    "No PDF extraction library installed. "
                    "Please install PyMuPDF (`pip install PyMuPDF`), pypdf (`pip install pypdf`), or pdfplumber."
                )

    # Write output file
    output_path.write_text(extracted_text, encoding='utf-8')
    print(f"Successfully extracted text to: {output_path}")
    return str(output_path)


def main():
    if len(sys.argv) < 2:
        print("Usage: python pdf_to_text.py <path_to_pdf_file> [output_text_file]")
        sys.exit(1)
        
    input_pdf = sys.argv[1]
    output_txt = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        extract_pdf_to_text(input_pdf, output_txt)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
