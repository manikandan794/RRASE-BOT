from app.api.v1.crud_factory import build_crud_router
from app.models.contact import Contact
from app.schemas.content import ContactIn, ContactOut

router = build_crud_router(
    model=Contact, schema_in=ContactIn, schema_out=ContactOut,
    prefix="/contacts", tags=["contacts"],
)
