from datetime import datetime
from typing import Literal

from pydantic import BaseModel

OrderStatus = Literal["pending", "confirmed", "delivered", "cancelled"]


class OrderItemIn(BaseModel):
    product_id: str
    slug: str
    name: str
    price: float
    image: str
    size: str
    color: str
    qty: int


class OrderItemOut(OrderItemIn):
    id: int

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    items: list[OrderItemIn]
    customer: dict | None = None


class OrderOut(BaseModel):
    id: int
    subtotal: float
    shipping: float
    total: float
    status: OrderStatus
    payment_intent_id: str | None = None
    customer: dict | None = None
    created_at: datetime
    items: list[OrderItemOut]

    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class CheckoutCreate(BaseModel):
    items: list[OrderItemIn]
    customer: dict | None = None
    shipping_mode: str = "domicile"


class CheckoutOut(BaseModel):
    client_secret: str
    order_id: int
    subtotal: float
    shipping: float
    total: float
