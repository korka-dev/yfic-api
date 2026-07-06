import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.database import Base, get_db
from app.main import app

# Base sqlite en mémoire, partagée entre toutes les connexions du test (StaticPool)
# — évite de toucher la vraie base Neon pendant les tests.
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def _prepare_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _override_get_db():
    async with TestSession() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture
async def db_session():
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    # Stripe doit être "configuré" pour que les routes ne renvoient pas 503 ;
    # les appels réseau réels sont monkeypatchés dans chaque test.
    settings.stripe_secret_key = "sk_test_fake"
    settings.stripe_webhook_secret = "whsec_fake"
    settings.resend_api_key = ""  # désactive l'envoi d'e-mails réel dans les tests

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def make_product():
    from app.models.product import Product

    def _make(id="prod-1", price=49.0, category="femme"):
        return Product(
            id=id,
            slug=f"slug-{id}",
            name={"fr": "Robe", "en": "Dress"},
            category=category,
            price=price,
            compare_at=None,
            is_new=False,
            featured=False,
            colors=[{"name": {"fr": "Noir", "en": "Black"}, "hex": "#000"}],
            sizes=["S", "M"],
            stock=10,
            delivery_delay=None,
            images=[],
            image="https://example.com/a.jpg",
            image2="https://example.com/b.jpg",
            tone="#cccccc",
            description={"fr": "", "en": ""},
            materials={"fr": "", "en": ""},
            order=0,
        )

    return _make
