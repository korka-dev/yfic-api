from sqlalchemy import Boolean, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[dict] = mapped_column(JSON)  # {fr, en}
    category: Mapped[str] = mapped_column(String, index=True)
    price: Mapped[float] = mapped_column(Float)
    compare_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_new: Mapped[bool] = mapped_column(Boolean, default=False)
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    colors: Mapped[list] = mapped_column(JSON)  # [{name: {fr, en}, hex}]
    sizes: Mapped[list] = mapped_column(JSON)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    delivery_delay: Mapped[str | None] = mapped_column(String, nullable=True)
    images: Mapped[list] = mapped_column(JSON, default=list)  # [url, ...]
    image: Mapped[str] = mapped_column(String)
    image2: Mapped[str] = mapped_column(String)
    tone: Mapped[str] = mapped_column(String)
    description: Mapped[dict] = mapped_column(JSON)  # {fr, en}
    materials: Mapped[dict] = mapped_column(JSON)  # {fr, en}
    order: Mapped[int] = mapped_column(Integer, default=0)
