import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cached, invalidate
from app.core.deps import require_admin
from app.db.database import get_db
from app.models.product import Product
from app.models.user import User
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate

router = APIRouter(prefix="/api/products", tags=["products"])


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or uuid.uuid4().hex[:8]

CACHE_TTL = 60
PUBLIC_CACHE_HEADER = "public, max-age=30, stale-while-revalidate=60"


@router.get("", response_model=list[ProductOut])
async def list_products(
    response: Response,
    category: str | None = Query(default=None),
    featured: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    response.headers["Cache-Control"] = PUBLIC_CACHE_HEADER

    async def load():
        stmt = select(Product)
        if category and category != "all":
            stmt = stmt.where(Product.category == category)
        if featured is not None:
            stmt = stmt.where(Product.featured == featured)
        stmt = stmt.order_by(Product.order)
        result = await db.execute(stmt)
        return [ProductOut.model_validate(p) for p in result.scalars().all()]

    return await cached(f"products:{category}:{featured}", CACHE_TTL, load)


@router.get("/{slug}", response_model=ProductOut)
async def get_product(slug: str, response: Response, db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = PUBLIC_CACHE_HEADER

    async def load():
        result = await db.execute(select(Product).where(Product.slug == slug))
        product = result.scalar_one_or_none()
        if not product:
            return None
        return ProductOut.model_validate(product)

    product = await cached(f"product:{slug}", CACHE_TTL, load)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/{slug}/related", response_model=list[ProductOut])
async def get_related(
    slug: str,
    response: Response,
    limit: int = Query(4, ge=1, le=20),  # borné pour éviter l'abus (L1)
    db: AsyncSession = Depends(get_db),
):
    response.headers["Cache-Control"] = PUBLIC_CACHE_HEADER

    async def load():
        result = await db.execute(select(Product).where(Product.slug == slug))
        product = result.scalar_one_or_none()
        if not product:
            return None

        same_cat = await db.execute(
            select(Product)
            .where(Product.category == product.category, Product.id != product.id)
            .order_by(Product.order)
        )
        others = await db.execute(
            select(Product)
            .where(Product.category != product.category)
            .order_by(Product.order)
        )
        related = list(same_cat.scalars().all()) + list(others.scalars().all())
        return [ProductOut.model_validate(p) for p in related]

    related = await cached(f"related:{slug}:{limit}", CACHE_TTL, load)
    if related is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return related[:limit]


@router.post("", response_model=ProductOut, status_code=201)
async def create_product(
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),  # admin uniquement (H1)
):
    base_slug = slugify(payload.name.fr)
    slug = base_slug
    suffix = 1
    while (await db.execute(select(Product).where(Product.slug == slug))).scalar_one_or_none():
        suffix += 1
        slug = f"{base_slug}-{suffix}"

    max_order = await db.scalar(select(func.max(Product.order)))
    data = payload.model_dump()
    images = data.pop("images")
    image = images[0]
    image2 = images[1] if len(images) > 1 else images[0]

    product = Product(
        id=uuid.uuid4().hex[:12],
        slug=slug,
        image=image,
        image2=image2,
        images=images,
        order=(max_order or 0) + 1,
        **data,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    invalidate()
    return product


@router.patch("/by-id/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: str,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),  # admin uniquement (H1)
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    updates = payload.model_dump(exclude_unset=True)
    images = updates.pop("images", None)
    if images is not None:
        updates["images"] = images
        updates["image"] = images[0] if images else product.image
        updates["image2"] = images[1] if len(images) > 1 else updates["image"]

    for field, value in updates.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    invalidate()
    return product


@router.delete("/by-id/{product_id}", status_code=204)
async def delete_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),  # admin uniquement (H1)
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.delete(product)
    await db.commit()
    invalidate()
