from pydantic import BaseModel, ConfigDict, Field


class LocalizedText(BaseModel):
    fr: str
    en: str


class ProductColor(BaseModel):
    name: LocalizedText
    hex: str


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: LocalizedText
    category: str
    price: float
    compare_at: float | None = None
    is_new: bool
    featured: bool
    colors: list[ProductColor]
    sizes: list[str]
    stock: int
    delivery_delay: str | None = None
    images: list[str]
    image: str
    image2: str
    tone: str
    description: LocalizedText
    materials: LocalizedText
    order: int


class ProductCreate(BaseModel):
    name: LocalizedText
    category: str
    price: float
    stock: int = 0
    delivery_delay: str | None = None
    compare_at: float | None = None
    is_new: bool = False
    featured: bool = False
    colors: list[ProductColor] = []
    sizes: list[str] = []
    images: list[str] = Field(min_length=1)
    tone: str = "#cccccc"
    description: LocalizedText = LocalizedText(fr="", en="")
    materials: LocalizedText = LocalizedText(fr="", en="")


class ProductUpdate(BaseModel):
    name: LocalizedText | None = None
    category: str | None = None
    price: float | None = None
    stock: int | None = None
    delivery_delay: str | None = None
    compare_at: float | None = None
    is_new: bool | None = None
    featured: bool | None = None
    colors: list[ProductColor] | None = None
    sizes: list[str] | None = None
    images: list[str] | None = None
    tone: str | None = None
    description: LocalizedText | None = None
    materials: LocalizedText | None = None
