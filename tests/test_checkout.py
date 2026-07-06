from types import SimpleNamespace

import pytest

from app.core.config import settings


class FakePaymentIntent:
    id = "pi_fake_123"
    client_secret = "pi_fake_123_secret"

    @classmethod
    def create(cls, **kwargs):
        cls.last_kwargs = kwargs
        return SimpleNamespace(id=cls.id, client_secret=cls.client_secret)


@pytest.mark.asyncio
async def test_checkout_ignores_client_supplied_price(client, db_session, make_product, monkeypatch):
    """Le prix envoyé par le client ne doit jamais être utilisé — seul le prix en DB compte (C1)."""
    product = make_product(id="prod-1", price=49.0)
    db_session.add(product)
    await db_session.commit()

    monkeypatch.setattr("app.routers.checkout.stripe.PaymentIntent", FakePaymentIntent)

    payload = {
        "items": [
            {
                "product_id": "prod-1",
                "slug": "slug-prod-1",
                "name": "Robe",
                "price": 1.0,  # prix falsifié côté client
                "image": "https://example.com/a.jpg",
                "size": "M",
                "color": "Noir",
                "qty": 2,
            }
        ],
        "customer": {"name": "Jane", "email": "jane@example.com"},
        "shipping_mode": "domicile",
    }

    res = await client.post("/api/checkout", json=payload)

    assert res.status_code == 201
    body = res.json()
    # 2 x 49.0 = 98.0, pas 2 x 1.0
    assert body["subtotal"] == 98.0
    assert body["client_secret"] == "pi_fake_123_secret"
    assert body["order_id"] > 0

    # Le montant envoyé à Stripe doit lui aussi refléter le prix DB (+ frais de port)
    assert FakePaymentIntent.last_kwargs["amount"] == round((98.0 + body["shipping"]) * 100)


@pytest.mark.asyncio
async def test_checkout_unknown_product_returns_400(client, monkeypatch):
    monkeypatch.setattr("app.routers.checkout.stripe.PaymentIntent", FakePaymentIntent)

    payload = {
        "items": [
            {
                "product_id": "does-not-exist",
                "slug": "x",
                "name": "x",
                "price": 10.0,
                "image": "x",
                "size": "M",
                "color": "Noir",
                "qty": 1,
            }
        ],
        "shipping_mode": "domicile",
    }

    res = await client.post("/api/checkout", json=payload)

    assert res.status_code == 400
    assert "introuvable" in res.json()["detail"]


@pytest.mark.asyncio
async def test_checkout_rejects_non_positive_qty(client, db_session, make_product, monkeypatch):
    """Une quantité négative ou nulle ne doit jamais passer la validation (audit #1)."""
    product = make_product(id="prod-1", price=49.0)
    db_session.add(product)
    await db_session.commit()

    monkeypatch.setattr("app.routers.checkout.stripe.PaymentIntent", FakePaymentIntent)

    for bad_qty in (-3, 0, 101):
        payload = {
            "items": [
                {
                    "product_id": "prod-1",
                    "slug": "slug-prod-1",
                    "name": "Robe",
                    "price": 49.0,
                    "image": "https://example.com/a.jpg",
                    "size": "M",
                    "color": "Noir",
                    "qty": bad_qty,
                }
            ],
            "shipping_mode": "domicile",
        }
        res = await client.post("/api/checkout", json=payload)
        assert res.status_code == 422, f"qty={bad_qty} aurait dû être rejetée"


@pytest.mark.asyncio
async def test_checkout_insufficient_stock_returns_400(client, db_session, make_product, monkeypatch):
    """Impossible de commander plus que le stock disponible (audit #3)."""
    product = make_product(id="prod-1", price=49.0)
    product.stock = 1
    db_session.add(product)
    await db_session.commit()

    monkeypatch.setattr("app.routers.checkout.stripe.PaymentIntent", FakePaymentIntent)

    payload = {
        "items": [
            {
                "product_id": "prod-1",
                "slug": "slug-prod-1",
                "name": "Robe",
                "price": 49.0,
                "image": "https://example.com/a.jpg",
                "size": "M",
                "color": "Noir",
                "qty": 2,
            }
        ],
        "shipping_mode": "domicile",
    }

    res = await client.post("/api/checkout", json=payload)

    assert res.status_code == 400
    assert "Stock insuffisant" in res.json()["detail"]


@pytest.mark.asyncio
async def test_checkout_without_stripe_configured_returns_503(client):
    original = settings.stripe_secret_key
    settings.stripe_secret_key = ""
    try:
        # items non vide requis : la validation Pydantic (422) passe avant le handler
        payload = {
            "items": [
                {
                    "product_id": "p1",
                    "slug": "s",
                    "name": "n",
                    "price": 1.0,
                    "image": "i",
                    "size": "M",
                    "color": "Noir",
                    "qty": 1,
                }
            ],
            "shipping_mode": "domicile",
        }
        res = await client.post("/api/checkout", json=payload)
        assert res.status_code == 503
    finally:
        settings.stripe_secret_key = original


@pytest.mark.asyncio
async def test_checkout_rejects_empty_items_and_bad_customer(client):
    """items vide ou customer malformé → 422 (audit : payload borné et typé)."""
    res = await client.post("/api/checkout", json={"items": [], "shipping_mode": "domicile"})
    assert res.status_code == 422

    item = {
        "product_id": "p1", "slug": "s", "name": "n", "price": 1.0,
        "image": "i", "size": "M", "color": "Noir", "qty": 1,
    }
    res = await client.post(
        "/api/checkout",
        json={"items": [item], "customer": {"name": "Jane", "email": "pas-un-email"}},
    )
    assert res.status_code == 422
