from app.extensions import db


class WeightRecord(db.Model):
    __tablename__ = "weight_records"

    w_record_id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey("livestock.animal_id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    weight = db.Column(db.Float, nullable=False)

    animal = db.relationship("Livestock", back_populates="weight_records")
