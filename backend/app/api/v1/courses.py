from app.api.v1.crud_factory import build_crud_router
from app.models.course import Course
from app.schemas.content import CourseIn, CourseOut

router = build_crud_router(
    model=Course, schema_in=CourseIn, schema_out=CourseOut,
    prefix="/courses", tags=["courses"],
)
