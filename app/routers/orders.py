from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.db.database import get_db
from app.models.user import User

# Le routeur d'ordres publics a été supprimé :
# - POST /api/orders acceptait des prix arbitraires sans validation DB (C1)
# - Le flux de paiement réel passe par POST /api/checkout (validé contre la DB + Stripe)
# - La gestion admin des commandes est dans /api/dashboard/orders

router = APIRouter(prefix="/api/orders", tags=["orders"])
