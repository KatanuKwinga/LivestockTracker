from app.extensions import db


class MortalityRecord(db.Model):
    # Your diagram names this table "mortalty_record" (typo). Fixed here —
    # say the word if you'd rather I match the typo exactly for consistency
    # with the submitted ERD.
    __tablename__ = "mortality_records"

    m_record_id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey("livestock.animal_id"), unique=True, nullable=False)
    date_of_death = db.Column(db.Date, nullable=False)
    age_at_death = db.Column(db.Integer, nullable=True)
    cause_of_death = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)

    animal = db.relationship("Livestock", back_populates="mortality_record")
