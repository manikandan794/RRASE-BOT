from app.api.v1.crud_factory import build_crud_router
from app.models.notice import Notice
from app.schemas.content import NoticeIn, NoticeOut

router = build_crud_router(
    model=Notice, schema_in=NoticeIn, schema_out=NoticeOut,
    prefix="/notices", tags=["notices"],
)
