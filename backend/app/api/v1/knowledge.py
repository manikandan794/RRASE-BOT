"""
Website knowledge import + admin/principal review workflow, plus the
administrator rebuild-index operation.

Flow implemented here:
    POST /knowledge/website/import  -> crawls+cleans, saves PENDING rows.
                                        A page whose content is byte-for-
                                        byte identical to an already-
                                        APPROVED batch is skipped (no
                                        uncontrolled duplicate knowledge).
                                        A page whose content CHANGED since
                                        the last approved import creates a
                                        new PENDING "version" and records
                                        which batch it would supersede.
    GET  /knowledge/website/pending -> reviewer sees what was found
    POST /knowledge/website/{id}/review -> approve (indexes into RAG,
                                        marks the previous version as
                                        superseded/removed) or reject
    POST /knowledge/rebuild-index -> admin-only: wipe + re-embed every
                                        currently-APPROVED chunk from
                                        Postgres (source of truth)
"""
import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.database.session import get_db
from app.models.knowledge import ApprovalStatus, SourceType, WebsiteImportBatch
from app.models.role import RoleName
from app.models.user import User
from app.rag.indexer import index_text, remove_source_chunks, rebuild_index
from app.schemas.common import MessageResponse
from app.schemas.knowledge import ReviewDecision, WebsiteImportBatchOut
from app.services.audit_service import log_action
from app.services.website_import import WebsiteImportError, import_website

router = APIRouter(prefix="/knowledge/website", tags=["knowledge"])
# Separate router (different prefix) for the /knowledge/rebuild-index
# admin action, included alongside `router` in api/v1/router.py.
admin_router = APIRouter(prefix="/knowledge", tags=["knowledge"])
write_dep = require_roles(RoleName.ADMIN, RoleName.PRINCIPAL)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@router.post("/import", response_model=list[WebsiteImportBatchOut])
def trigger_import(db: Session = Depends(get_db), user: User = Depends(write_dep)):
    try:
        pages = import_website()
    except WebsiteImportError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    rows = []
    skipped_unchanged = 0
    for page in pages:
        content_hash = _hash_text(page["raw_text"])

        latest_approved = (
            db.query(WebsiteImportBatch)
            .filter(
                WebsiteImportBatch.page_url == page["page_url"],
                WebsiteImportBatch.status == ApprovalStatus.APPROVED,
            )
            .order_by(WebsiteImportBatch.created_at.desc())
            .first()
        )
        if latest_approved and latest_approved.content_hash == content_hash:
            # Unchanged since last approval - do not create uncontrolled
            # duplicate knowledge for a page that was already reviewed.
            skipped_unchanged += 1
            continue

        row = WebsiteImportBatch(
            source_url=page["page_url"], page_url=page["page_url"],
            title=page.get("title"), raw_text=page["raw_text"], content_hash=content_hash,
            status=ApprovalStatus.PENDING,
        )
        if latest_approved:
            # Content changed - this new pending row is a new version of an
            # existing approved page. It will supersede the old one only
            # once a human approves it (recorded on approval, not now).
            row.superseded_by = None
        db.add(row)
        rows.append(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    log_action(
        db, actor_id=user.id, action="knowledge.website_import",
        details=f"{len(rows)} new/changed page(s), {skipped_unchanged} unchanged skipped",
    )
    return rows


@router.get("/pending", response_model=list[WebsiteImportBatchOut])
def list_pending(db: Session = Depends(get_db), user: User = Depends(write_dep)):
    return (
        db.query(WebsiteImportBatch)
        .filter(WebsiteImportBatch.status == ApprovalStatus.PENDING)
        .all()
    )


@router.post("/{batch_id}/review", response_model=MessageResponse)
def review_batch(
    batch_id: str, decision: ReviewDecision, db: Session = Depends(get_db), user: User = Depends(write_dep)
):
    batch = db.get(WebsiteImportBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Not found.")

    batch.reviewed_by = user.id
    if decision.approve:
        batch.status = ApprovalStatus.APPROVED
        final_text = decision.edited_text or batch.raw_text
        index_text(
            db, final_text, source_type=SourceType.WEBSITE, source_id=batch.id,
            source_label=batch.title or batch.page_url,
        )

        # Supersede any previously-approved version of the same page so the
        # old, now-outdated chunks stop being retrievable, without deleting
        # the historical batch row itself (import history is preserved).
        previous = (
            db.query(WebsiteImportBatch)
            .filter(
                WebsiteImportBatch.page_url == batch.page_url,
                WebsiteImportBatch.status == ApprovalStatus.APPROVED,
                WebsiteImportBatch.id != batch.id,
            )
            .all()
        )
        for old in previous:
            remove_source_chunks(db, source_type=SourceType.WEBSITE, source_id=old.id)
            old.status = ApprovalStatus.ARCHIVED
            old.superseded_by = batch.id
    else:
        batch.status = ApprovalStatus.REJECTED
    db.commit()
    log_action(db, actor_id=user.id, action="knowledge.website_review", target=batch_id,
               details="approved" if decision.approve else "rejected")
    return MessageResponse(message="Reviewed.")


@admin_router.post("/rebuild-index", response_model=MessageResponse)
def rebuild_index_endpoint(db: Session = Depends(get_db), user: User = Depends(write_dep)):
    """Admin/Principal-only. See rag/indexer.rebuild_index for behaviour."""
    result = rebuild_index(db)
    log_action(db, actor_id=user.id, action="knowledge.rebuild_index", details=str(result))
    return MessageResponse(
        message=f"Rebuilt index: {result['re_embedded']}/{result['total_approved_chunks']} approved chunk(s) re-embedded."
    )
