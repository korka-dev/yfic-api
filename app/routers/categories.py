import re

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cached, invalidate
from app.core.deps import require_admin
from app.db.database import get_db
from app.models.category_cover import CategoryCover
from app.models.product import Product
from app.models.user import User

router = APIRouter(prefix="/api/categories", tags=["categories"])

CACHE_TTL = 60

CATEGORY_COVERS_DEFAULT = {
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


async def _resolve_covers(db: AsyncSession, rows: list) -> list:
    db_covers_result = await db.execute(select(CategoryCover))
    db_covers = {
        row.key: {"cover": row.cover, "tone": row.tone}
        for row in db_covers_result.scalars()
    }

    categories = []
    for key, count in rows:
        if key in db_covers and db_covers[key]["cover"]:
            meta = db_covers[key]
        elif key in CATEGORY_COVERS_DEFAULT:
            meta = CATEGORY_COVERS_DEFAULT[key]
        else:
            rep = await db.execute(
                select(Product).where(Product.category == key).order_by(Product.order).limit(1)
            )
            product = rep.scalar_one_or_none()
            meta = {
                "cover": product.image if product else "",
                "tone": product.tone if product else DEFAULT_TONE,
            }
        categories.append({"key": key, "count": count, **meta})

    return categories


@router.get("")
async def list_categories(response: Response, db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"

    async def load():
        result = await db.execute(
            select(Product.category, func.count(Product.id)).group_by(Product.category)
        )
        rows = result.all()
        categories = await _resolve_covers(db, rows)
        categories.sort(key=lambda c: -c["count"])
        return categories

    return await cached("categories", CACHE_TTL, load)


@router.get("/covers")
async def list_covers(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),  # cohérent (L6)
):
    # Product categories with counts
    result = await db.execute(
        select(Product.category, func.count(Product.id)).group_by(Product.category)
    )
    product_rows = result.all()
    product_keys = {r[0] for r in product_rows}

    # Also include CategoryCover entries that have no products yet
    covers_result = await db.execute(select(CategoryCover))
    standalone = [(c.key, 0) for c in covers_result.scalars() if c.key not in product_keys]

    all_rows = list(product_rows) + standalone
    categories = await _resolve_covers(db, all_rows)
    categories.sort(key=lambda c: c["key"])
    return categories


class CoverUpdate(BaseModel):
    cover: str
    tone: str = "#cccccc"


class CategoryCreate(BaseModel):
    key: str
    cover: str = ""
    tone: str = "#cccccc"


@router.post("", status_code=201)
async def create_category(
    payload: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),  # cohérent avec les autres routes (L6)
):

    key = re.sub(r"[^a-z0-9]+", "-", payload.key.lower().strip()).strip("-")
    if not key:
        raise HTTPException(status_code=400, detail="Nom de collection invalide")

    existing = await db.get(CategoryCover, key)
    if existing:
        raise HTTPException(status_code=409, detail="Cette collection existe déjà")

    db.add(CategoryCover(key=key, cover=payload.cover, tone=payload.tone))
    await db.commit()
    invalidate("categories")

    return {"key": key, "count": 0, "cover": payload.cover, "tone": payload.tone}


@router.patch("/{key}/cover")
async def update_category_cover(
    key: str,
    payload: CoverUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),  # cohérent (L6)
):

    existing = await db.get(CategoryCover, key)
    if existing:
        existing.cover = payload.cover
        existing.tone = payload.tone
    else:
        db.add(CategoryCover(key=key, cover=payload.cover, tone=payload.tone))

    await db.commit()
    invalidate("categories")

    return {"key": key, "cover": payload.cover, "tone": payload.tone}


@router.delete("/{key}")
async def delete_category(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),  # cohérent (L6)
):

    result = await db.execute(
        select(func.count(Product.id)).where(Product.category == key)
    )
    count = result.scalar()
    if count and count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Supprimez d'abord les {count} produit(s) de cette collection.",
        )

    existing = await db.get(CategoryCover, key)
    if existing:
        await db.delete(existing)
        await db.commit()

    invalidate("categories")
    return {"ok": True}
