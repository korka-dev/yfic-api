from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cached
from app.db.database import get_db
from app.models.product import Product

router = APIRouter(prefix="/api/categories", tags=["categories"])

CACHE_TTL = 60

CATEGORY_COVERS = {
    "femme": {
        "cover": "https://images.unsplash.com/photo-1595777457583-95e059d581b8?auto=format&fit=crop&w=1000&q=80",
        "tone": "#b07a53",
    },
    "homme": {
        "cover": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=1000&q=80",
        "tone": "#5a5a43",
    },
    "accessoires": {
        "cover": "https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&w=1000&q=80",
        "tone": "#9a5f33",
    },
}


DEFAULT_TONE = "#cccccc"


@router.get("")
async def list_categories(response: Response, db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"

    async def load():
        result = await db.execute(
            select(Product.category, func.count(Product.id)).group_by(Product.category)
        )
        rows = result.all()

        categories = []
        for key, count in rows:
            meta = CATEGORY_COVERS.get(key)
            if meta is None:
                rep = await db.execute(
                    select(Product).where(Product.category == key).order_by(Product.order).limit(1)
                )
                product = rep.scalar_one_or_none()
                meta = {
                    "cover": product.image if product else "",
                    "tone": product.tone if product else DEFAULT_TONE,
                }
            categories.append({"key": key, "count": count, **meta})

        categories.sort(key=lambda c: -c["count"])
        return categories

    return await cached("categories", CACHE_TTL, load)
