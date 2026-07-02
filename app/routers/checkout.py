import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.schemas.order import CheckoutCreate, CheckoutOut

router = APIRouter(prefix="/api/checkout", tags=["checkout"])
limiter = Limiter(key_func=get_remote_address)

# Tiers: (max_qty_inclusive, price)
_RATES = {
    "point_relais": [(1, 4.90), (3, 6.90), (9999, 8.90)],
    "domicile":     [(1, 6.90), (3, 8.90), (9999, 11.90)],
    "express":      [(1, 9.90), (3, 12.90), (9999, 14.90)],
}
_FREE_AT = {"point_relais": 70.0, "domicile": 100.0, "express": None}
_EXPRESS_REDUCED_AT = 130.0
_EXPRESS_REDUCED_PRICE = 5.90


def _compute_shipping(total_qty: int, subtotal: float, mode: str) -> float:
    mode = mode if mode in _RATES else "domicile"
    free_at = _FREE_AT.get(mode)
    if free_at is not None and subtotal >= free_at:
        return 0.0
    if mode == "express" and subtotal >= _EXPRESS_REDUCED_AT:
        return _EXPRESS_REDUCED_PRICE
    for max_qty, price in _RATES[mode]:
        if total_qty <= max_qty:
            return price
    return _RATES[mode][-1][1]


@router.post("", response_model=CheckoutOut, status_code=201)
@limiter.limit("15/minute")  # évite la création de masse de PaymentIntents Stripe (M1)
async def create_checkout(
    request: Request,
    payload: CheckoutCreate,
    db: AsyncSession = Depends(get_db),
):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe non configuré")

    stripe.api_key = settings.stripe_secret_key

    # Validation des prix contre la DB — ne jamais faire confiance aux prix du client
    product_ids = [item.product_id for item in payload.items]
    result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
    db_products = {p.id: p for p in result.scalars().all()}

    order_items = []
    subtotal = 0.0
    total_qty = 0
    for item in payload.items:
        db_product = db_products.get(item.product_id)
        if not db_product:
            raise HTTPException(status_code=400, detail=f"Produit introuvable : {item.product_id}")
        real_price = db_product.price
        subtotal += real_price * item.qty
        total_qty += item.qty
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

    shipping = 0.0 if subtotal == 0 else _compute_shipping(
        total_qty, subtotal, payload.shipping_mode
    )
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
