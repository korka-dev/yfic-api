import stripe
import pytest

from app.models.order import Order, OrderItem


async def _make_pending_order(db_session) -> Order:
    order = Order(
        subtotal=98.0,
        shipping=6.9,
        total=104.9,
        status="pending",
        customer={"name": "Jane", "email": "jane@example.com"},
        items=[
            OrderItem(
                product_id="prod-1",
                slug="slug-prod-1",
                name="Robe",
                price=49.0,
                image="https://example.com/a.jpg",
                size="M",
                color="Noir",
                qty=2,
            )
        ],
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    return order


@pytest.mark.asyncio
async def test_webhook_confirms_pending_order(client, db_session, monkeypatch):
    order = await _make_pending_order(db_session)

    fake_event = {
        "type": "payment_intent.succeeded",
        "data": {"object": {"metadata": {"order_id": str(order.id)}}},
    }
    monkeypatch.setattr(
        "app.routers.webhooks.stripe.Webhook.construct_event",
        lambda payload, sig_header, secret: fake_event,
    )

    sent = {"confirmation": False, "admin": False}

    async def fake_confirmation(order):
        sent["confirmation"] = True

    async def fake_admin(order):
        sent["admin"] = True

    monkeypatch.setattr("app.routers.webhooks.send_order_confirmation", fake_confirmation)
    monkeypatch.setattr("app.routers.webhooks.send_admin_order_notification", fake_admin)

    res = await client.post(
        "/webhook/stripe", content=b"{}", headers={"stripe-signature": "whatever"}
    )

    assert res.status_code == 200
    assert res.json() == {"received": True}
    assert sent["confirmation"] is True
    assert sent["admin"] is True

    # La session de test garde `order` dans son identity map (expire_on_commit=False) ;
    # la commande a été modifiée par une autre session (celle du handler webhook),
    # donc il faut explicitement l'expirer avant de relire sa valeur en DB.
    db_session.expire(order)
    await db_session.refresh(order)
    assert order.status == "confirmed"


@pytest.mark.asyncio
async def test_webhook_does_not_reconfirm_already_confirmed_order(client, db_session, monkeypatch):
    order = await _make_pending_order(db_session)
    order.status = "confirmed"
    await db_session.commit()

    fake_event = {
        "type": "payment_intent.succeeded",
        "data": {"object": {"metadata": {"order_id": str(order.id)}}},
    }
    monkeypatch.setattr(
        "app.routers.webhooks.stripe.Webhook.construct_event",
        lambda payload, sig_header, secret: fake_event,
    )

    calls = {"count": 0}

    async def fake_confirmation(order):
        calls["count"] += 1

    monkeypatch.setattr("app.routers.webhooks.send_order_confirmation", fake_confirmation)
    monkeypatch.setattr("app.routers.webhooks.send_admin_order_notification", fake_confirmation)

    res = await client.post(
        "/webhook/stripe", content=b"{}", headers={"stripe-signature": "whatever"}
    )

    assert res.status_code == 200
    # Un webhook rejoué ne doit pas renvoyer les e-mails une seconde fois
    assert calls["count"] == 0


@pytest.mark.asyncio
async def test_webhook_invalid_signature_returns_400(client, monkeypatch):
    def raise_sig_error(payload, sig_header, secret):
        raise stripe.error.SignatureVerificationError("bad sig", sig_header)

    monkeypatch.setattr("app.routers.webhooks.stripe.Webhook.construct_event", raise_sig_error)

    res = await client.post(
        "/webhook/stripe", content=b"{}", headers={"stripe-signature": "bad"}
    )

    assert res.status_code == 400


@pytest.mark.asyncio
async def test_test_email_requires_admin(client):
    """/webhook/test-email ne doit plus être public (audit #2)."""
    res = await client.get("/webhook/test-email")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_webhook_without_secret_returns_503(client):
    from app.core.config import settings

    original = settings.stripe_webhook_secret
    settings.stripe_webhook_secret = ""
    try:
        res = await client.post(
            "/webhook/stripe", content=b"{}", headers={"stripe-signature": "x"}
        )
        assert res.status_code == 503
    finally:
        settings.stripe_webhook_secret = original
