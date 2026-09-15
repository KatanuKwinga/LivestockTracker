from app.extensions import db


class HealthRecord(db.Model):
    __tablename__ = "health_records"

    h_record_id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey("livestock.animal_id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    disease = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    treatment = db.Column(db.String(100), nullable=True)
    dosage = db.Column(db.String(50), nullable=True)

    animal = db.relationship("Livestock", back_populates="health_records")
