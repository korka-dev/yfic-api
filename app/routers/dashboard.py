from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.contact import ContactMessage
from app.models.newsletter import NewsletterSubscriber
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.schemas.contact import ContactOut
from app.schemas.newsletter import NewsletterOut
from app.schemas.order import OrderOut, OrderStatusUpdate

router = APIRouter(
    prefix="/api/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_user)]
)


@router.get("/summary")
async def summary(db: AsyncSession = Depends(get_db)):
    product_count = await db.scalar(select(func.count(Product.id)))
    order_count = await db.scalar(select(func.count(Order.id)))
    delivered_count = await db.scalar(
        select(func.count(Order.id)).where(Order.status == "delivered")
    )
    cancelled_count = await db.scalar(
        select(func.count(Order.id)).where(Order.status == "cancelled")
    )
    pending_count = await db.scalar(
        select(func.count(Order.id)).where(Order.status == "pending")
    )
    contact_count = await db.scalar(select(func.count(ContactMessage.id)))
    newsletter_count = await db.scalar(select(func.count(NewsletterSubscriber.id)))
    revenue = await db.scalar(select(func.coalesce(func.sum(Order.total), 0)))
    return {
        "products": product_count,
        "orders": order_count,
        "delivered_orders": delivered_count,
        "cancelled_orders": cancelled_count,
        "pending_orders": pending_count,
        "contact_messages": contact_count,
        "newsletter_subscribers": newsletter_count,
        "revenue": float(revenue or 0),
    }


@router.get("/orders", response_model=list[OrderOut])
async def list_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc())
    )
    return result.scalars().all()


@router.patch("/orders/{order_id}", response_model=OrderOut)
async def update_order_status(
    order_id: int, payload: OrderStatusUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = payload.status
    await db.commit()
    await db.refresh(order, attribute_names=["items"])
    return order


@router.get("/contact-messages", response_model=list[ContactOut])
async def list_contact_messages(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContactMessage).order_by(ContactMessage.created_at.desc()))
    return result.scalars().all()


@router.get("/newsletter-subscribers", response_model=list[NewsletterOut])
async def list_newsletter_subscribers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NewsletterSubscriber).order_by(NewsletterSubscriber.created_at.desc())
    )
    return result.scalars().all()
