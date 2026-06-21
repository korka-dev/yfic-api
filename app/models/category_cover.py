from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class CategoryCover(Base):
    __tablename__ = "category_covers"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    cover: Mapped[str] = mapped_column(String, default="")
    tone: Mapped[str] = mapped_column(String, default="#cccccc")
