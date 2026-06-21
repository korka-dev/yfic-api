from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.newsletter import NewsletterSubscriber
from app.schemas.newsletter import NewsletterCreate, NewsletterOut

router = APIRouter(prefix="/api/newsletter", tags=["newsletter"])


@router.post("", response_model=NewsletterOut, status_code=201)
async def subscribe(payload: NewsletterCreate, db: AsyncSession = Depends(get_db)):
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
