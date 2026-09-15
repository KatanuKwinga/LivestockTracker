from datetime import date
from app.extensions import db


class Livestock(db.Model):
    __tablename__ = "livestock"

    animal_id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey("farmers.farmer_id"), nullable=False)
    species = db.Column(db.Enum("CATTLE", "CHICKEN", "GOAT", "SHEEP"), nullable=False)
    gender = db.Column(db.Enum("MALE", "FEMALE"), nullable=False)
    breed = db.Column(db.String(50), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text, nullable=True)

    # This FK points at a table defined later in breeding.py, and that
    # table's dam/sire columns point back at this one — a genuine circular
    # reference between the two tables. use_alter=True tells Alembic to
    # create both tables first and add this constraint as a separate ALTER
    # afterward, instead of trying (and failing) to satisfy both at once.
    b_record_id = db.Column(
        db.Integer,
        db.ForeignKey("breeding_record.b_record_id", use_alter=True, name="fk_livestock_breeding_event"),
        nullable=True,
    )

    farmer = db.relationship("Farmer", back_populates="livestock")
    birth_event = db.relationship(
        "BreedingRecord", foreign_keys=[b_record_id], back_populates="offspring"
    )

    weight_records = db.relationship("WeightRecord", back_populates="animal", cascade="all, delete-orphan")
    health_records = db.relationship("HealthRecord", back_populates="animal", cascade="all, delete-orphan")
    commercial_records = db.relationship("CommercialInfo", back_populates="animal", cascade="all, delete-orphan")
    production_records = db.relationship("ProductionData", back_populates="animal", cascade="all, delete-orphan")
    mortality_record = db.relationship("MortalityRecord", back_populates="animal", uselist=False, cascade="all, delete-orphan")

    # Breeding events where this animal was the dam or the sire.
    dam_events = db.relationship(
        "BreedingRecord", foreign_keys="BreedingRecord.animal_id", back_populates="dam"
    )
    sire_events = db.relationship(
        "BreedingRecord", foreign_keys="BreedingRecord.sire_id", back_populates="sire"
    )

    @property
    def age(self):
        """Computed from date_of_birth on every access, so it can never go
        stale the way a stored 'age' column would. Your diagram has 'age'
        as a stored INT column — this keeps that attribute name available
        in code without persisting a value that silently rots."""
        if not self.date_of_birth:
            return None
        today = date.today()
        years = today.year - self.date_of_birth.year
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            years -= 1
        return years
