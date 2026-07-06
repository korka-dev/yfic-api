import pytest

from app.core.config import settings


@pytest.mark.asyncio
async def test_cross_site_mutation_is_blocked(client):
    """Une mutation avec une Origin inconnue doit être rejetée (anti-CSRF)."""
    res = await client.post(
        "/api/contact",
        json={"name": "x", "email": "x@x.fr", "subject": "s", "message": "m"},
        headers={"Origin": "https://evil.example"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_allowed_origin_mutation_passes(client):
    """La même mutation depuis une origine autorisée doit passer."""
    original = settings.cors_origins
    settings.cors_origins = "https://www.yfic.shop"
    try:
        res = await client.post(
            "/api/contact",
            json={"name": "x", "email": "x@x.fr", "subject": "s", "message": "m"},
            headers={"Origin": "https://www.yfic.shop"},
        )
        assert res.status_code == 201
    finally:
        settings.cors_origins = original


@pytest.mark.asyncio
async def test_mutation_without_origin_passes(client):
    """Pas d'Origin = pas un navigateur (Stripe, curl) : on laisse passer."""
    res = await client.post(
        "/api/contact",
        json={"name": "x", "email": "x@x.fr", "subject": "s", "message": "m"},
    )
    assert res.status_code == 201


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(client):
    """Le chemin 'email inconnu' (hash factice anti-timing) répond bien 401."""
    res = await client.post(
        "/api/auth/login",
        json={"email": "inconnu@example.com", "password": "whatever"},
    )
    assert res.status_code == 401
