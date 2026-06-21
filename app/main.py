from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(key_func=get_remote_address)
from app.db.database import Base, engine
from app.routers import auth, categories, checkout, contact, dashboard, newsletter, orders, products, uploads, webhooks

# Import all models so Base.metadata knows about them
import app.models.category_cover  # noqa: F401
import app.models.contact  # noqa: F401
import app.models.newsletter  # noqa: F401
import app.models.order  # noqa: F401
import app.models.product  # noqa: F401
import app.models.user  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="YFIC API", version="1.0.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(GZipMiddleware, minimum_size=500)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=STATIC_DIR / "uploads"), name="uploads")

app.include_router(products.router)
app.include_router(categories.router)
app.include_router(contact.router)
app.include_router(newsletter.router)
app.include_router(orders.router)
app.include_router(checkout.router)
app.include_router(webhooks.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(uploads.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
