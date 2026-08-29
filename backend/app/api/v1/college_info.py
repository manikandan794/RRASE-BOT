from app.api.v1.crud_factory import build_crud_router
from app.models.college import CollegeInfo
from app.schemas.content import CollegeInfoIn, CollegeInfoOut

router = build_crud_router(
    model=CollegeInfo, schema_in=CollegeInfoIn, schema_out=CollegeInfoOut,
    prefix="/college-info", tags=["college-info"], id_field="key",
)
