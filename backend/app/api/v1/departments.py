from app.api.v1.crud_factory import build_crud_router
from app.models.department import Department
from app.schemas.content import DepartmentIn, DepartmentOut

router = build_crud_router(
    model=Department, schema_in=DepartmentIn, schema_out=DepartmentOut,
    prefix="/departments", tags=["departments"],
)
