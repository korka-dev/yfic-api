from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.newsletter import NewsletterSubscriber
from app.schemas.newsletter import NewsletterCreate, NewsletterOut

router = APIRouter(prefix="/api/newsletter", tags=["newsletter"])
limiter = Limiter(key_func=get_remote_address)


@router.post("", response_model=NewsletterOut, status_code=201)
@limiter.limit("5/minute")
async def subscribe(request: Request, payload: NewsletterCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.email == payload.email)
    )
    found = existing.scalar_one_or_none()
    if found:
        return found

    sub = NewsletterSubscriber(email=payload.email)
    db.add(sub)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Already subscribed")
    await db.refresh(sub)
    return sub
