"""
PDF text extraction using pypdf. Kept isolated so swapping extraction
libraries later (e.g. adding OCR for scanned PDFs) touches one file.
"""
import logging

from pypdf import PdfReader

logger = logging.getLogger("rrase_college_ai.documents.pdf_extractor")


class PDFExtractionError(Exception):
    pass


def extract_text(file_path: str) -> tuple[str, int]:
    """Returns (full_text, page_count). Raises PDFExtractionError on any
    failure so callers can record it against the UploadedDocument row
    instead of crashing the upload request."""
    try:
        reader = PdfReader(file_path)
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:
                raise PDFExtractionError(f"PDF is password-protected: {exc}") from exc

        pages_text = []
        for page in reader.pages:
            try:
                pages_text.append(page.extract_text() or "")
            except Exception as exc:  # pragma: no cover - per-page defensive
                logger.warning("Failed extracting a page: %s", exc)
                pages_text.append("")

        full_text = "\n".join(pages_text).strip()
        if not full_text:
            raise PDFExtractionError(
                "No extractable text found (this may be a scanned/image-only PDF)."
            )
        return full_text, len(reader.pages)
    except PDFExtractionError:
        raise
    except Exception as exc:
        raise PDFExtractionError(str(exc)) from exc
