"""
Database models for Cycle Quest.
Using Flask-SQLAlchemy with SQLite so the whole project runs with
zero external database setup - just `python app.py`.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    gender = db.Column(db.String(20), default="Prefer not to say")
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship("Booking", backref="user", lazy=True)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


class Cycle(db.Model):
    __tablename__ = "cycles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    category = db.Column(db.String(20), nullable=False)  # leisure / adventure / kids
    price_per_hour = db.Column(db.Integer, nullable=False)
    rating = db.Column(db.Float, nullable=False, default=4.5)
    description = db.Column(db.String(255), nullable=False)
    image_file = db.Column(db.String(120), nullable=False)
    total_units = db.Column(db.Integer, nullable=False, default=5)

    # "home base" coordinates - used as the center point the cycle's
    # live GPS marker wanders around while it isn't rented.
    base_lat = db.Column(db.Float, nullable=False, default=13.0827)
    base_lng = db.Column(db.Float, nullable=False, default=80.2707)

    bookings = db.relationship("Booking", backref="cycle", lazy=True)

    def active_booking_count(self):
        return Booking.query.filter_by(cycle_id=self.id, status="active").count()

    def available_units(self):
        return max(self.total_units - self.active_booking_count(), 0)

    def completed_ratings(self):
        return [b.rider_rating for b in self.bookings
                if b.status == "completed" and b.rider_rating is not None]

    def average_rating(self):
        """Real ratings left by riders, falling back to the seed rating
        until the first review comes in."""
        ratings = self.completed_ratings()
        if not ratings:
            return self.rating
        return round(sum(ratings) / len(ratings), 1)

    def review_count(self):
        return len(self.completed_ratings())

    def star_display(self):
        full = int(round(self.average_rating()))
        return "★" * full + "☆" * (5 - full)


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    cycle_id = db.Column(db.Integer, db.ForeignKey("cycles.id"), nullable=False)

    # pending_payment -> active -> completed
    #                          \-> cancelled
    status = db.Column(db.String(20), nullable=False, default="pending_payment")

    hours = db.Column(db.Integer, nullable=False, default=1)
    total_price = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    ended_at = db.Column(db.DateTime, nullable=True)

    # Live/final distance covered during this ride, in kilometers.
    # Filled in from the GPS simulation while the ride is active.
    distance_km = db.Column(db.Float, nullable=False, default=0.0)

    # Post-ride feedback - left once, after the ride is completed.
    rider_rating = db.Column(db.Integer, nullable=True)   # 1-5
    rider_review = db.Column(db.String(300), nullable=True)

    def elapsed_minutes(self):
        if not self.started_at:
            return 0
        end = self.ended_at or datetime.utcnow()
        return (end - self.started_at).total_seconds() / 60

    def paid_minutes(self):
        return self.hours * 60

    def is_overdue(self):
        return self.status == "active" and self.elapsed_minutes() > self.paid_minutes()
