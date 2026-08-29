from pydantic import BaseModel


class UploadedDocumentOut(BaseModel):
    id: str
    filename: str
    content_type: str | None
    size_bytes: int | None
    status: str
    department_id: str | None = None
    extracted_pages: int | None
    reviewed_by: str | None = None
    error: str | None

    model_config = {"from_attributes": True}


class WebsiteImportBatchOut(BaseModel):
    id: str
    source_url: str
    page_url: str
    title: str | None
    raw_text: str
    status: str
    superseded_by: str | None = None

    model_config = {"from_attributes": True}


class ReviewDecision(BaseModel):
    approve: bool
    edited_text: str | None = None  # allow the reviewer to clean text further before approving
