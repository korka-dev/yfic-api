from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routers import auth, categories, checkout, contact, dashboard, newsletter, orders, products, uploads, webhooks

app = FastAPI(title="YFIC API", version="1.0.0")

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
