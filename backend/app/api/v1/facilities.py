from app.api.v1.crud_factory import build_crud_router
from app.models.facility import Facility
from app.schemas.content import FacilityIn, FacilityOut

router = build_crud_router(
    model=Facility, schema_in=FacilityIn, schema_out=FacilityOut,
    prefix="/facilities", tags=["facilities"],
)
