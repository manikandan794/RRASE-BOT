"""
Faculty self-service, department-scoped endpoints (CRITICAL FIX #3).

Every route here resolves the acting faculty member's department via
`get_current_faculty_profile` - a server-side lookup of the Faculty row
linked to the logged-in user's account. A faculty member's own
department_id is NEVER accepted as input from the client; every
department-owned record (FAQ, Notice, Document, ...) is filtered and
written against this server-derived value only, so a faculty member can
never read or modify another department's data by supplying a different
department_id in the request body or query string.

Faculty CANNOT: rename their department, change their department's HOD,
touch another department, manage users, or reach any admin/principal-only
route - those still require RoleName.ADMIN / RoleName.PRINCIPAL via the
existing `require_roles` dependency on the other routers.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_faculty_profile
from app.database.session import get_db
from app.models.department import Department
from app.models.faculty import Faculty
from app.models.faq import FAQ
from app.models.notice import Notice
from app.schemas.content import (
    DepartmentDescriptionUpdate,
    DepartmentOut,
    FAQIn,
    FAQOut,
    NoticeIn,
    NoticeOut,
)
from app.services.audit_service import log_action

router = APIRouter(prefix="/faculty/me", tags=["faculty-portal"])


def _own_department(db: Session, profile: Faculty) -> Department:
    if not profile.department_id:
        raise HTTPException(status_code=400, detail="Your faculty profile has no department assigned yet.")
    department = db.get(Department, profile.department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Assigned department no longer exists.")
    return department


@router.get("/department", response_model=DepartmentOut)
def get_my_department(db: Session = Depends(get_db), profile: Faculty = Depends(get_current_faculty_profile)):
    return _own_department(db, profile)


@router.put("/department", response_model=DepartmentOut)
def update_my_department_description(
    payload: DepartmentDescriptionUpdate,
    db: Session = Depends(get_db),
    profile: Faculty = Depends(get_current_faculty_profile),
):
    """Faculty may edit only the description of their own department -
    name, short_code, and hod_name stay admin/principal-only (see
    api/v1/departments.py)."""
    department = _own_department(db, profile)
    department.description = payload.description
    db.commit()
    db.refresh(department)
    log_action(db, actor_id=profile.user_id, action="faculty.department.update", target=department.id)
    return department


def _assert_owns_department(record_department_id: str | None, profile: Faculty) -> None:
    if record_department_id != profile.department_id:
        raise HTTPException(status_code=403, detail="You may only manage records for your own department.")


@router.get("/faqs", response_model=list[FAQOut])
def list_my_faqs(db: Session = Depends(get_db), profile: Faculty = Depends(get_current_faculty_profile)):
    _own_department(db, profile)
    return db.query(FAQ).filter(FAQ.department_id == profile.department_id).all()


@router.post("/faqs", response_model=FAQOut, status_code=201)
def create_my_faq(
    payload: FAQIn, db: Session = Depends(get_db), profile: Faculty = Depends(get_current_faculty_profile)
):
    _own_department(db, profile)
    faq = FAQ(
        department_id=profile.department_id,  # server-derived, ignores payload.department_id
        question=payload.question, answer=payload.answer,
        category=payload.category, is_published=payload.is_published,
    )
    db.add(faq)
    db.commit()
    db.refresh(faq)
    log_action(db, actor_id=profile.user_id, action="faculty.faq.create", target=faq.id)
    return faq


@router.put("/faqs/{faq_id}", response_model=FAQOut)
def update_my_faq(
    faq_id: str, payload: FAQIn, db: Session = Depends(get_db),
    profile: Faculty = Depends(get_current_faculty_profile),
):
    faq = db.get(FAQ, faq_id)
    if not faq:
        raise HTTPException(status_code=404, detail="Not found.")
    _assert_owns_department(faq.department_id, profile)
    faq.question, faq.answer, faq.category, faq.is_published = (
        payload.question, payload.answer, payload.category, payload.is_published
    )
    db.commit()
    db.refresh(faq)
    log_action(db, actor_id=profile.user_id, action="faculty.faq.update", target=faq_id)
    return faq


@router.delete("/faqs/{faq_id}", status_code=204)
def delete_my_faq(
    faq_id: str, db: Session = Depends(get_db), profile: Faculty = Depends(get_current_faculty_profile)
):
    faq = db.get(FAQ, faq_id)
    if not faq:
        raise HTTPException(status_code=404, detail="Not found.")
    _assert_owns_department(faq.department_id, profile)
    db.delete(faq)
    db.commit()
    log_action(db, actor_id=profile.user_id, action="faculty.faq.delete", target=faq_id)
    return None


@router.get("/notices", response_model=list[NoticeOut])
def list_my_notices(db: Session = Depends(get_db), profile: Faculty = Depends(get_current_faculty_profile)):
    _own_department(db, profile)
    return db.query(Notice).filter(Notice.department_id == profile.department_id).all()


@router.post("/notices", response_model=NoticeOut, status_code=201)
def create_my_notice(
    payload: NoticeIn, db: Session = Depends(get_db), profile: Faculty = Depends(get_current_faculty_profile)
):
    _own_department(db, profile)
    notice = Notice(
        department_id=profile.department_id,  # server-derived, ignores payload.department_id
        title=payload.title, body=payload.body, is_published=payload.is_published,
        published_at=payload.published_at, expires_at=payload.expires_at,
    )
    db.add(notice)
    db.commit()
    db.refresh(notice)
    log_action(db, actor_id=profile.user_id, action="faculty.notice.create", target=notice.id)
    return notice


@router.put("/notices/{notice_id}", response_model=NoticeOut)
def update_my_notice(
    notice_id: str, payload: NoticeIn, db: Session = Depends(get_db),
    profile: Faculty = Depends(get_current_faculty_profile),
):
    notice = db.get(Notice, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Not found.")
    _assert_owns_department(notice.department_id, profile)
    notice.title, notice.body, notice.is_published = payload.title, payload.body, payload.is_published
    notice.published_at, notice.expires_at = payload.published_at, payload.expires_at
    db.commit()
    db.refresh(notice)
    log_action(db, actor_id=profile.user_id, action="faculty.notice.update", target=notice_id)
    return notice


@router.delete("/notices/{notice_id}", status_code=204)
def delete_my_notice(
    notice_id: str, db: Session = Depends(get_db), profile: Faculty = Depends(get_current_faculty_profile)
):
    notice = db.get(Notice, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Not found.")
    _assert_owns_department(notice.department_id, profile)
    db.delete(notice)
    db.commit()
    log_action(db, actor_id=profile.user_id, action="faculty.notice.delete", target=notice_id)
    return None
