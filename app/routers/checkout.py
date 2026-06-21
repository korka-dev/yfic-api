import stripe
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.schemas.order import CheckoutCreate, CheckoutOut

router = APIRouter(prefix="/api/checkout", tags=["checkout"])

FREE_SHIPPING_THRESHOLD = 150
SHIPPING_COST = 8


@router.post("", response_model=CheckoutOut, status_code=201)
async def create_checkout(payload: CheckoutCreate, db: AsyncSession = Depends(get_db)):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe non configuré")

    stripe.api_key = settings.stripe_secret_key

    # Validate prices against DB — never trust client-provided prices
    product_ids = [item.product_id for item in payload.items]
    result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
    db_products = {p.id: p for p in result.scalars().all()}

    order_items = []
    subtotal = 0.0
    for item in payload.items:
        db_product = db_products.get(item.product_id)
        if not db_product:
            raise HTTPException(status_code=400, detail=f"Produit introuvable : {item.product_id}")
        real_price = db_product.price
        subtotal += real_price * item.qty
        order_items.append(OrderItem(
            product_id=item.product_id,
            slug=item.slug,
            name=item.name,
            price=real_price,
            image=item.image,
            size=item.size,
            color=item.color,
            qty=item.qty,
        ))

    shipping = 0.0 if subtotal == 0 or subtotal >= FREE_SHIPPING_THRESHOLD else SHIPPING_COST
    total = subtotal + shipping

    order = Order(
        subtotal=subtotal,
        shipping=shipping,
        total=total,
        status="pending",
        customer=payload.customer,
        items=order_items,
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
