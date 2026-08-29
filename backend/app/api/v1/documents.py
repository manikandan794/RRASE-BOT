"""
PDF upload -> extraction -> chunking -> admin/principal review -> approval
-> embedding.

CRITICAL FIX #1: uploading a document (and even extracting/chunking its
text) NEVER makes it retrievable by the chatbot on its own. Chunks are
staged as PENDING; only an explicit call to /documents/{id}/review with
approve=true embeds them and flips the document (and its chunks) to
APPROVED. Rejecting removes the staged chunks entirely.

Faculty may upload documents scoped to their own department (never a
department_id they supply - it is derived server-side from their faculty
profile); admins/principals may upload college-wide or department
documents and review anything.
"""
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.config import get_settings
from app.database.session import get_db
from app.documents.pdf_extractor import PDFExtractionError, extract_text
from app.models.faculty import Faculty
from app.models.knowledge import ApprovalStatus, SourceType, UploadedDocument
from app.models.role import RoleName
from app.models.user import User
from app.rag.indexer import approve_source_chunks, reject_source_chunks, remove_source_chunks, stage_chunks
from app.schemas.knowledge import ReviewDecision, UploadedDocumentOut
from app.services.audit_service import log_action
from app.utils.validators import is_allowed_upload, sanitize_filename

router = APIRouter(prefix="/documents", tags=["documents"])
review_dep = require_roles(RoleName.ADMIN, RoleName.PRINCIPAL)


def _uploader_department_id(db: Session, user: User) -> str | None:
    """Faculty uploads are tagged with the uploader's OWN department only -
    never a value the client could supply. Admins/principals have no
    faculty profile, so their uploads default to college-wide (None)."""
    profile = db.query(Faculty).filter(Faculty.user_id == user.id).first()
    return profile.department_id if profile else None


@router.post("/upload", response_model=UploadedDocumentOut)
def upload_document(
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleName.ADMIN, RoleName.PRINCIPAL, RoleName.FACULTY)),
):
    settings = get_settings()
    if not is_allowed_upload(file.filename or "", file.content_type):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_name = sanitize_filename(file.filename or "upload.pdf")

    contents = file.file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit.")

    doc = UploadedDocument(
        filename=safe_name, stored_path="", content_type=file.content_type,
        size_bytes=len(contents), uploaded_by=user.id, status=ApprovalStatus.PENDING,
        department_id=_uploader_department_id(db, user),
    )
    db.add(doc)
    db.flush()

    stored_path = os.path.join(settings.UPLOAD_DIR, f"{doc.id}_{safe_name}")
    with open(stored_path, "wb") as f:
        f.write(contents)
    doc.stored_path = stored_path
    db.commit()

    try:
        text, page_count = extract_text(stored_path)
        doc.extracted_pages = page_count
        # Stage only - do NOT embed/approve here. An admin/principal must
        # explicitly review and approve via /documents/{id}/review before
        # this content becomes retrievable by the chatbot.
        stage_chunks(db, text, source_type=SourceType.DOCUMENT, source_id=doc.id, source_label=doc.filename)
        doc.status = ApprovalStatus.PENDING
    except PDFExtractionError as exc:
        doc.status = ApprovalStatus.REJECTED
        doc.error = str(exc)

    db.commit()
    db.refresh(doc)
    log_action(db, actor_id=user.id, action="document.upload", target=doc.id)
    return doc


@router.get("", response_model=list[UploadedDocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleName.ADMIN, RoleName.PRINCIPAL, RoleName.FACULTY)),
):
    query = db.query(UploadedDocument)
    roles = {ur.role.name for ur in user.user_roles}
    if RoleName.FACULTY in roles and not roles.intersection({RoleName.ADMIN, RoleName.PRINCIPAL}):
        # Faculty-only accounts see just their own department's documents -
        # never trust a department filter from the client, derive it here.
        dept_id = _uploader_department_id(db, user)
        query = query.filter(UploadedDocument.department_id == dept_id)
    return query.order_by(UploadedDocument.created_at.desc()).all()


@router.post("/{document_id}/review", response_model=UploadedDocumentOut)
def review_document(
    document_id: str, decision: ReviewDecision, db: Session = Depends(get_db), user: User = Depends(review_dep)
):
    """Admin/Principal-only. Approving embeds the staged (PENDING) chunks
    into the vector store and marks the document APPROVED. Rejecting
    deletes the staged chunks - none of that content was ever retrievable."""
    doc = db.get(UploadedDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Not found.")
    if doc.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Document is not pending review (status={doc.status}).")

    doc.reviewed_by = user.id
    if decision.approve:
        embedded = approve_source_chunks(db, SourceType.DOCUMENT, doc.id)
        doc.status = ApprovalStatus.APPROVED
        if embedded == 0:
            doc.error = (
                "Approved, but no embedding backend was reachable; chunks remain "
                "unembedded. Re-run review once Ollama/Gemini is configured."
            )
    else:
        reject_source_chunks(db, SourceType.DOCUMENT, doc.id)
        doc.status = ApprovalStatus.REJECTED

    db.commit()
    db.refresh(doc)
    log_action(db, actor_id=user.id, action="document.review", target=document_id,
               details="approved" if decision.approve else "rejected")
    return doc


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db), user: User = Depends(review_dep)):
    doc = db.get(UploadedDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Not found.")
    remove_source_chunks(db, source_type=SourceType.DOCUMENT, source_id=doc.id)
    if doc.stored_path and os.path.exists(doc.stored_path):
        os.remove(doc.stored_path)
    db.delete(doc)
    db.commit()
    log_action(db, actor_id=user.id, action="document.delete", target=document_id)
    return {"message": "Document deleted."}
