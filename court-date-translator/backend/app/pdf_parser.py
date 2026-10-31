"""
PDF text extraction module.

Extracts plain text from uploaded PDF files. Uses pdfplumber for the highest
quality extraction, with PyPDF2 as a fallback if pdfplumber is unavailable.
"""

import io

try:
    import pdfplumber

    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    from pypdf import PdfReader

    HAS_PYPDF = True
except ImportError:
    try:
        from PyPDF2 import PdfReader

        HAS_PYPDF = True
    except ImportError:
        HAS_PYPDF = False


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract all text from a PDF given its raw bytes.

    Returns the extracted text, or an empty string if nothing could be read.
    Raises a ValueError if the data does not appear to be a readable PDF.
    """
    if not file_bytes:
        raise ValueError("Empty file provided.")

    # Quick sanity check: PDFs must start with %PDF
    if not file_bytes.startswith(b"%PDF"):
        raise ValueError("The uploaded file is not a valid PDF.")

    text_parts = []

    # Primary extractor: pdfplumber
    if HAS_PDFPLUMBER:
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        text_parts.append(page_text.strip())
        except Exception as exc:  # pragma: no cover - defensive
            # Fall through to the PyPDF2/PyPDF fallback below.
            text_parts = []
            pdfplumber_error = exc

    # Fallback extractor: PyPDF2 / PyPDF
    if not text_parts and HAS_PYPDF:
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(page_text.strip())
        except Exception as exc:  # pragma: no cover - defensive
            raise ValueError(f"Could not parse PDF text: {exc}") from exc

    if not text_parts and not HAS_PDFPLUMBER and not HAS_PYPDF:
        raise ValueError(
            "No PDF extraction library available. Install pdfplumber or pypdf."
        )

    extracted = "\n\n".join(text_parts).strip()
    if not extracted:
        raise ValueError(
            "No text could be extracted from the PDF. It may be a scanned/image "
            "document requiring OCR, which is not supported by this tool."
        )
    return extracted
