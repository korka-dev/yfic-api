import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.ratelimit import limiter
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

_cors_kwargs: dict = {
    "allow_origins": settings.cors_origin_list,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if not settings.is_production:
    # Autorise tous les ports localhost uniquement en développement (L3)
    _cors_kwargs["allow_origin_regex"] = r"http://localhost:\d+"

app.add_middleware(CORSMiddleware, **_cors_kwargs)

_LOCALHOST_ORIGIN = re.compile(r"^http://localhost:\d+$")


@app.middleware("http")
async def block_cross_site_mutations(request: Request, call_next):
    """Anti-CSRF : le cookie est SameSite=None en production, donc envoyé sur
    toute requête cross-site. Les POST multipart/form-data partent sans preflight
    CORS — on rejette donc toute mutation dont l'Origin n'est pas autorisée.
    Les requêtes sans Origin (Stripe, curl, server-to-server) passent : le CSRF
    est un problème de navigateur, et un navigateur envoie toujours Origin."""
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin and origin not in settings.cors_origin_list:
            if settings.is_production or not _LOCALHOST_ORIGIN.match(origin):
                return JSONResponse(status_code=403, content={"detail": "Origine non autorisée"})
    return await call_next(request)

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
