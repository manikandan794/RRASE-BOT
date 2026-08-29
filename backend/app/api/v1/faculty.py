from app.api.v1.crud_factory import build_crud_router
from app.models.faculty import Faculty
from app.schemas.content import FacultyIn, FacultyOut

router = build_crud_router(
    model=Faculty, schema_in=FacultyIn, schema_out=FacultyOut,
    prefix="/faculty", tags=["faculty"],
)
