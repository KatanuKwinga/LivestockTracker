from app.extensions import db


class CommercialInfo(db.Model):
    __tablename__ = "commercial_info"

    transaction_id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey("livestock.animal_id"), nullable=False)
    transaction_type = db.Column(db.Enum("BUY", "SELL"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    other_party = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(100), nullable=True)

    animal = db.relationship("Livestock", back_populates="commercial_records")
