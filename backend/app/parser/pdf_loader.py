import os
from typing import Any

try:
    try:
        import pymupdf as fitz  # type: ignore
    except ImportError:
        import fitz  # type: ignore
except ImportError:
    fitz = None

try:
    import pdfplumber  # type: ignore
except ImportError:
    pdfplumber = None


class PDFLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.document: Any = None
        self._pdfplumber_doc: Any = None

    def load(self) -> int:
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"PDF file not found: {self.file_path}")

        if fitz is not None:
            self.document = fitz.open(self.file_path)
            return len(self.document)
        elif pdfplumber is not None:
            self._pdfplumber_doc = pdfplumber.open(self.file_path)
            return len(self._pdfplumber_doc.pages)
        else:
            raise ImportError("Neither PyMuPDF (fitz) nor pdfplumber is installed.")

    def get_page_text(self, page_number: int) -> str:
        # page_number is 1-indexed for the user of this API
        if self.document is not None:
            if page_number < 1 or page_number > len(self.document):
                raise ValueError(f"Invalid page number {page_number}")
            page = self.document[page_number - 1]
            return page.get_text() or ""
        elif self._pdfplumber_doc is not None:
            if page_number < 1 or page_number > len(self._pdfplumber_doc.pages):
                raise ValueError(f"Invalid page number {page_number}")
            page = self._pdfplumber_doc.pages[page_number - 1]
            return page.extract_text() or ""
        return ""

    def get_page_count(self) -> int:
        if self.document is not None:
            return len(self.document)
        elif self._pdfplumber_doc is not None:
            return len(self._pdfplumber_doc.pages)
        return 0

    def close(self) -> None:
        if self.document is not None:
            self.document.close()
            self.document = None
        if self._pdfplumber_doc is not None:
            self._pdfplumber_doc.close()
            self._pdfplumber_doc = None

    def __enter__(self) -> "PDFLoader":
        self.load()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
