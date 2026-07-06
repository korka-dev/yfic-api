from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ratelimit import limiter
from app.db.database import get_db
from app.models.contact import ContactMessage
from app.schemas.contact import ContactCreate, ContactOut

router = APIRouter(prefix="/api/contact", tags=["contact"])


@router.post("", response_model=ContactOut, status_code=201)
@limiter.limit("5/minute")
async def create_contact_message(request: Request, payload: ContactCreate, db: AsyncSession = Depends(get_db)):
    msg = ContactMessage(**payload.model_dump())
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg
