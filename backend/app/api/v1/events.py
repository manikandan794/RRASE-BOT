from app.api.v1.crud_factory import build_crud_router
from app.models.event import Event
from app.schemas.content import EventIn, EventOut

router = build_crud_router(
    model=Event, schema_in=EventIn, schema_out=EventOut,
    prefix="/events", tags=["events"],
)
