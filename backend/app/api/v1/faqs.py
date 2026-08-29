from app.api.v1.crud_factory import build_crud_router
from app.models.faq import FAQ
from app.schemas.content import FAQIn, FAQOut

router = build_crud_router(
    model=FAQ, schema_in=FAQIn, schema_out=FAQOut,
    prefix="/faqs", tags=["faqs"],
)
