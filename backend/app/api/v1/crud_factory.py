"""
Generic CRUD router factory.

Every "management" module required by the spec (Department, Faculty,
Course, FAQ, Notice, Event, Facility, Contact, College Info) follows the
identical shape: public/authenticated read, admin+principal-only write.
Rather than duplicate that boilerplate eight times, each module builds its
router here and only supplies its model/schema - keeping behaviour
consistent and easy to audit.
"""
from typing import Type

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.database.session import get_db
from app.models.role import RoleName
from app.models.user import User
from app.services.audit_service import log_action


def build_crud_router(
    *,
    model,
    schema_in: Type[BaseModel],
    schema_out: Type[BaseModel],
    prefix: str,
    tags: list[str],
    id_field: str = "id",
    id_type=str,
    writable_roles: tuple[str, ...] = (RoleName.ADMIN, RoleName.PRINCIPAL),
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=tags)
    write_dep = require_roles(*writable_roles)

    @router.get("", response_model=list[schema_out])
    def list_items(db: Session = Depends(get_db)):
        return db.query(model).all()

    @router.get("/{item_id}", response_model=schema_out)
    def get_item(item_id: id_type, db: Session = Depends(get_db)):
        item = db.get(model, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Not found.")
        return item

    @router.post("", response_model=schema_out, status_code=status.HTTP_201_CREATED)
    def create_item(
        payload: schema_in, db: Session = Depends(get_db), user: User = Depends(write_dep)
    ):
        item = model(**payload.model_dump())
        db.add(item)
        db.commit()
        db.refresh(item)
        log_action(db, actor_id=user.id, action=f"{prefix}.create", target=str(getattr(item, id_field)))
        return item

    @router.put("/{item_id}", response_model=schema_out)
    def update_item(
        item_id: id_type, payload: schema_in, db: Session = Depends(get_db),
        user: User = Depends(write_dep),
    ):
        item = db.get(model, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Not found.")
        for field, value in payload.model_dump().items():
            setattr(item, field, value)
        db.commit()
        db.refresh(item)
        log_action(db, actor_id=user.id, action=f"{prefix}.update", target=str(item_id))
        return item

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_item(item_id: id_type, db: Session = Depends(get_db), user: User = Depends(write_dep)):
        item = db.get(model, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Not found.")
        db.delete(item)
        db.commit()
        log_action(db, actor_id=user.id, action=f"{prefix}.delete", target=str(item_id))
        return None

    return router
