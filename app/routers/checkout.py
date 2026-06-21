import stripe
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.models.order import Order, OrderItem
from app.schemas.order import CheckoutCreate, CheckoutOut

router = APIRouter(prefix="/api/checkout", tags=["checkout"])

FREE_SHIPPING_THRESHOLD = 150
SHIPPING_COST = 8


@router.post("", response_model=CheckoutOut, status_code=201)
async def create_checkout(payload: CheckoutCreate, db: AsyncSession = Depends(get_db)):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe non configuré")

    stripe.api_key = settings.stripe_secret_key

    subtotal = sum(item.price * item.qty for item in payload.items)
    shipping = 0.0 if subtotal == 0 or subtotal >= FREE_SHIPPING_THRESHOLD else SHIPPING_COST
    total = subtotal + shipping

    order = Order(
        subtotal=subtotal,
        shipping=shipping,
        total=total,
        status="pending",
        customer=payload.customer,
        items=[OrderItem(**item.model_dump()) for item in payload.items],
    )
    db.add(order)
    await db.commit()
    await db.refresh(order, attribute_names=["items"])

    intent = stripe.PaymentIntent.create(
        amount=round(total * 100),
        currency="eur",
        metadata={"order_id": str(order.id)},
        automatic_payment_methods={"enabled": True},
    )

    order.payment_intent_id = intent.id
    await db.commit()

    return CheckoutOut(
        client_secret=intent.client_secret,
        order_id=order.id,
        subtotal=subtotal,
        shipping=shipping,
        total=total,
    )
