"""Input and file validation helpers used across upload/import endpoints."""
import re

ALLOWED_UPLOAD_CONTENT_TYPES = {"application/pdf"}
ALLOWED_UPLOAD_EXTENSIONS = {".pdf"}


def is_allowed_upload(filename: str, content_type: str | None) -> bool:
    lower = filename.lower()
    ext_ok = any(lower.endswith(ext) for ext in ALLOWED_UPLOAD_EXTENSIONS)
    type_ok = content_type in ALLOWED_UPLOAD_CONTENT_TYPES if content_type else True
    return ext_ok and type_ok


def sanitize_filename(filename: str) -> str:
    base = filename.strip().replace("/", "_").replace("\\", "_")
    base = re.sub(r"[^A-Za-z0-9._\-]", "_", base)
    return base[:200] or "upload.pdf"


def is_reasonable_question(text: str) -> bool:
    text = text.strip()
    return 1 <= len(text) <= 2000
