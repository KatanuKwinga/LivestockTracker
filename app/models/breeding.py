from app.extensions import db


class BreedingRecord(db.Model):
    __tablename__ = "breeding_record"

    b_record_id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey("livestock.animal_id"), nullable=False)  # dam
    sire_id = db.Column(db.Integer, db.ForeignKey("livestock.animal_id"), nullable=True)
    status = db.Column(db.Enum("EXPECTANT", "SUCCESSFUL BIRTH", "NO BIRTH"), nullable=False)
    expected_delivery_date = db.Column(db.Date, nullable=True)
    actual_delivery_date = db.Column(db.Date, nullable=True)
    num_stillborn = db.Column(db.Integer, default=0)

    dam = db.relationship("Livestock", foreign_keys=[animal_id], back_populates="dam_events")
    sire = db.relationship("Livestock", foreign_keys=[sire_id], back_populates="sire_events")

    # Surviving offspring that were given their own Livestock row and
    # linked back via livestock.b_record_id.
    offspring = db.relationship(
        "Livestock", foreign_keys="Livestock.b_record_id", back_populates="birth_event"
    )

    @property
    def num_born_alive(self):
        """Computed, not stored — the count of surviving offspring is
        just the length of the offspring relationship above. See the
        schema doc for why this is deliberately not a cached column."""
        return len(self.offspring)
