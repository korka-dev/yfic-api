from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.order import Order, OrderItem
from app.schemas.order import OrderCreate, OrderOut

router = APIRouter(prefix="/api/orders", tags=["orders"])

FREE_SHIPPING_THRESHOLD = 150
SHIPPING_COST = 8


@router.post("", response_model=OrderOut, status_code=201)
async def create_order(payload: OrderCreate, db: AsyncSession = Depends(get_db)):
    subtotal = sum(item.price * item.qty for item in payload.items)
    shipping = 0.0 if subtotal == 0 or subtotal >= FREE_SHIPPING_THRESHOLD else SHIPPING_COST
    total = subtotal + shipping

    order = Order(
        subtotal=subtotal,
        shipping=shipping,
        total=total,
        customer=payload.customer,
        items=[OrderItem(**item.model_dump()) for item in payload.items],
    )
    db.add(order)
    await db.commit()
    await db.refresh(order, attribute_names=["items"])
    return order
