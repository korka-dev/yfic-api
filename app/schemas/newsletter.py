from pydantic import BaseModel, EmailStr


class NewsletterCreate(BaseModel):
    email: EmailStr


class NewsletterOut(NewsletterCreate):
    id: int

    class Config:
        from_attributes = True
