# Import every model here so that (a) `from app.models import X` works
# from anywhere, and (b) SQLAlchemy's metadata sees all tables when
# Flask-Migrate autogenerates migrations. A model that exists but is never
# imported is invisible to `flask db migrate` — a common source of
# "why isn't my table being created" bugs.

from app.models.user import User, Farmer, Worker
from app.models.livestock import Livestock
from app.models.breeding import BreedingRecord
from app.models.weight import WeightRecord
from app.models.health import HealthRecord
from app.models.mortality import MortalityRecord
from app.models.commercial import CommercialInfo
from app.models.production import ProductionData

__all__ = [
    "User",
    "Farmer",
    "Worker",
    "Livestock",
    "BreedingRecord",
    "WeightRecord",
    "HealthRecord",
    "MortalityRecord",
    "CommercialInfo",
    "ProductionData",
]
