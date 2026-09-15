from app.extensions import db


class ProductionData(db.Model):
    __tablename__ = "production_data"

    product_id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey("livestock.animal_id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    item = db.Column(db.String(100), nullable=False)

    # 'yield' is a reserved keyword in Python (used in generators), so it
    # can't be a Python attribute name. The db.Column('yield', ...) first
    # argument keeps the actual database column named "yield" to match
    # your diagram exactly; the Python-side attribute is yield_amount.
    yield_amount = db.Column("yield", db.Float, nullable=False)
    metric = db.Column(db.String(10), nullable=False)

    animal = db.relationship("Livestock", back_populates="production_records")
