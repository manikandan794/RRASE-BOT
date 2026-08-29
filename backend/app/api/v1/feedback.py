from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_optional_user, require_roles
from app.database.session import get_db
from app.models.faculty import Faculty
from app.models.feedback import Feedback, UnansweredQuestion
from app.models.role import RoleName
from app.models.user import User
from app.schemas.chat import (
    FeedbackIn,
    UnansweredQuestionOut,
    UnansweredQuestionResolve,
    UnansweredQuestionTriage,
)
from app.schemas.common import MessageResponse
from app.services.audit_service import log_action

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=MessageResponse)
def submit_feedback(
    payload: FeedbackIn, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)
):
    db.add(Feedback(
        message_id=payload.message_id, user_id=user.id if user else None,
        rating=payload.rating, comment=payload.comment,
    ))
    db.commit()
    return MessageResponse(message="Thanks for your feedback.")


@router.get("/unanswered-questions", response_model=list[UnansweredQuestionOut])
def list_unanswered(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleName.ADMIN, RoleName.PRINCIPAL, RoleName.FACULTY)),
):
    query = db.query(UnansweredQuestion).filter(UnansweredQuestion.resolved.is_(False))

    roles = {ur.role.name for ur in user.user_roles}
    if RoleName.FACULTY in roles and not roles.intersection({RoleName.ADMIN, RoleName.PRINCIPAL}):
        # Faculty-only accounts must never see college-wide unanswered
        # questions - only ones an admin/principal has routed to their own
        # department. department_id is derived server-side from the
        # faculty profile, never trusted from the request.
        profile = db.query(Faculty).filter(Faculty.user_id == user.id).first()
        dept_id = profile.department_id if profile else "__none__"
        query = query.filter(UnansweredQuestion.department_id == dept_id)

    return query.order_by(UnansweredQuestion.times_asked.desc()).all()


@router.post(
    "/unanswered-questions/{question_id}/route", response_model=MessageResponse,
    dependencies=[Depends(require_roles(RoleName.ADMIN, RoleName.PRINCIPAL))],
)
def route_unanswered(
    question_id: str, payload: UnansweredQuestionTriage, db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Admin/Principal-only: assign an unanswered question to a department
    so that department's faculty can see and help resolve it."""
    item = db.get(UnansweredQuestion, question_id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found.")
    item.department_id = payload.department_id
    db.commit()
    log_action(db, actor_id=user.id, action="unanswered.route", target=question_id,
               details=f"department_id={payload.department_id}")
    return MessageResponse(message="Routed.")


@router.post("/unanswered-questions/{question_id}/resolve", response_model=MessageResponse)
def resolve_unanswered(
    question_id: str, payload: UnansweredQuestionResolve, db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleName.ADMIN, RoleName.PRINCIPAL, RoleName.FACULTY)),
):
    item = db.get(UnansweredQuestion, question_id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found.")

    roles = {ur.role.name for ur in user.user_roles}
    if RoleName.FACULTY in roles and not roles.intersection({RoleName.ADMIN, RoleName.PRINCIPAL}):
        profile = db.query(Faculty).filter(Faculty.user_id == user.id).first()
        dept_id = profile.department_id if profile else None
        if item.department_id is None or item.department_id != dept_id:
            raise HTTPException(status_code=403, detail="Not routed to your department.")

    item.resolved = True
    item.resolution = payload.resolution
    item.resolved_by = user.id
    db.commit()
    log_action(db, actor_id=user.id, action="unanswered.resolve", target=question_id)
    return MessageResponse(message="Marked resolved.")
