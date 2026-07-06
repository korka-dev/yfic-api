import resend
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.deps import require_admin
from app.db.database import get_db
from app.models.order import Order
from app.models.user import User
from app.services.email import send_admin_order_notification, send_order_confirmation

router = APIRouter(prefix="/webhook", tags=["webhooks"])


@router.get("/test-email")
async def test_email(current_user: User = Depends(require_admin)):
    if not settings.resend_api_key:
        return {"error": "RESEND_API_KEY manquant"}
    resend.api_key = settings.resend_api_key
    try:
        result = resend.Emails.send({
            "from": f"{settings.store_name} <{settings.store_email}>",
            "to": [settings.admin_email],
            "subject": "Test email YFIC",
            "html": "<p>Si tu reçois ce mail, Resend fonctionne correctement.</p>",
        })
        return {"ok": True, "id": result.get("id")}
    except Exception:
        return {"error": "Échec de l'envoi"}


@router.post("/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe non configuré")

    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="STRIPE_WEBHOOK_SECRET manquant — configurez-le dans Vercel env vars")

    stripe.api_key = settings.stripe_secret_key
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Payload invalide")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Signature invalide")

    if event["type"] == "payment_intent.succeeded":
        pi = event["data"]["object"]
        order_id = pi.get("metadata", {}).get("order_id")
        if order_id:
            result = await db.execute(
                select(Order)
                .options(selectinload(Order.items))
                .where(Order.id == int(order_id))
            )
            order = result.scalar_one_or_none()
            if order and order.status == "pending":
                order.status = "confirmed"
                await db.commit()
                await db.refresh(order, attribute_names=["items"])
                await send_order_confirmation(order)        # → client
                await send_admin_order_notification(order)  # → admin

    return {"received": True}
