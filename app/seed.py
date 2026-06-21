import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.database import Base, async_session, engine
from app.models.product import Product
from app.models.user import User
from app.seed_data import PRODUCTS


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        existing = await db.execute(select(Product.id))
        existing_ids = {row[0] for row in existing.all()}

        new_products = [Product(**p) for p in PRODUCTS if p["id"] not in existing_ids]
        if new_products:
            db.add_all(new_products)
            await db.commit()
            print(f"Inserted {len(new_products)} products.")
        else:
            print("No new products to insert.")

        all_users = (await db.execute(select(User))).scalars().all()
        for user in all_users:
            if user.email != settings.admin_email:
                await db.delete(user)
        await db.commit()

        existing_admin = await db.execute(
            select(User).where(User.email == settings.admin_email)
        )
        admin = existing_admin.scalar_one_or_none()
        if admin:
            admin.hashed_password = hash_password(settings.admin_password)
            admin.is_admin = True
            await db.commit()
            print(f"Updated admin user {settings.admin_email}.")
        else:
            db.add(
                User(
                    email=settings.admin_email,
                    hashed_password=hash_password(settings.admin_password),
                    is_admin=True,
                )
            )
            await db.commit()
            print(f"Created admin user {settings.admin_email}.")


if __name__ == "__main__":
    asyncio.run(seed())
