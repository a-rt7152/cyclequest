"""
Cycle Quest - a cycle rental app with real accounts, real bookings,
and simulated live GPS tracking for every cycle.

Run with:  python app.py
Then open: http://127.0.0.1:5000
"""
import os
import re
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

from models import db, User, Cycle, Booking
from seed_data import CYCLES
import tracking

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'cyclequest.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("CYCLEQUEST_SECRET_KEY", "dev-secret-key-change-me")

db.init_app(app)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --------------------------------------------------------------------------
# Auth helpers
# --------------------------------------------------------------------------
def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapper


def current_user():
    uid = session.get("user_id")
    return User.query.get(uid) if uid else None


@app.context_processor
def inject_user():
    return dict(current_user=current_user())


# --------------------------------------------------------------------------
# Public pages
# --------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("fullName", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phoneNumber", "").strip()
        gender = request.form.get("gender", "Prefer not to say")
        password = request.form.get("password", "")
        confirm = request.form.get("confirmPassword", "")

        errors = []
        if not full_name or not username or not email or not phone or not password:
            errors.append("Please fill in every field.")
        if not EMAIL_RE.match(email):
            errors.append("That email address doesn't look valid.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords don't match.")
        if User.query.filter_by(username=username).first():
            errors.append("That username is already taken.")
        if User.query.filter_by(email=email).first():
            errors.append("An account with that email already exists.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html", form=request.form)

        user = User(full_name=full_name, username=username, email=email,
                    phone=phone, gender=gender)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Account created! You can log in now.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", form={})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()

        if user and user.check_password(password):
            session["user_id"] = user.id
            session["just_logged_in"] = True
            return redirect(url_for("home"))

        flash("Incorrect username or password.", "error")
        return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You've been logged out.", "success")
    return redirect(url_for("index"))


# --------------------------------------------------------------------------
# Core app
# --------------------------------------------------------------------------
@app.route("/home")
@login_required
def home():
    show_welcome = session.pop("just_logged_in", False)
    categories = [
        dict(key="leisure", title="Leisure Rides", image="leisure/leisure2.jpg"),
        dict(key="adventure", title="Adventure Rides", image="adventure/adv1.jpg"),
        dict(key="kids", title="Kids Rides", image="kids/kids1.jpg"),
    ]
    for c in categories:
        c["available"] = sum(
            cyc.available_units() for cyc in Cycle.query.filter_by(category=c["key"]).all()
        )
    return render_template("home.html", categories=categories, show_welcome=show_welcome)


@app.route("/category/<cat_key>")
@login_required
def category(cat_key):
    if cat_key not in ("leisure", "adventure", "kids"):
        return redirect(url_for("home"))

    sort = request.args.get("sort", "")
    query = Cycle.query.filter_by(category=cat_key)
    if sort == "price_asc":
        query = query.order_by(Cycle.price_per_hour.asc())
    elif sort == "price_desc":
        query = query.order_by(Cycle.price_per_hour.desc())
    elif sort == "rating":
        query = query.order_by(Cycle.rating.desc())

    cycles = query.all()
    titles = {"leisure": "Leisure Rides", "adventure": "Adventure Rides", "kids": "Kids Rides"}
    return render_template("category.html", cycles=cycles, cat_key=cat_key,
                            title=titles[cat_key], sort=sort)


@app.route("/api/cycle-coords/<cat_key>")
@login_required
def api_cycle_coords(cat_key):
    """Base coordinates for every cycle in a category, used client-side
    for the 'cycles near me' distance sort (browser geolocation)."""
    cycles = Cycle.query.filter_by(category=cat_key).all()
    return jsonify([
        {"id": c.id, "lat": c.base_lat, "lng": c.base_lng} for c in cycles
    ])


@app.route("/book/<int:cycle_id>", methods=["POST"])
@login_required
def book_cycle(cycle_id):
    cycle = Cycle.query.get_or_404(cycle_id)

    if cycle.available_units() <= 0:
        flash(f"Sorry, all {cycle.name} cycles are booked right now.", "error")
        return redirect(url_for("category", cat_key=cycle.category))

    try:
        hours = max(1, min(12, int(request.form.get("hours", 1))))
    except ValueError:
        hours = 1

    booking = Booking(
        user_id=current_user().id,
        cycle_id=cycle.id,
        status="pending_payment",
        hours=hours,
        total_price=hours * cycle.price_per_hour,
    )
    db.session.add(booking)
    db.session.commit()

    return redirect(url_for("payment", booking_id=booking.id))


@app.route("/payment/<int:booking_id>", methods=["GET", "POST"])
@login_required
def payment(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user().id:
        flash("That booking doesn't belong to your account.", "error")
        return redirect(url_for("home"))

    if booking.status != "pending_payment":
        return redirect(url_for("bookings"))

    if request.method == "POST":
        # This is a simulated payment gateway (like the original project
        # intended) - no real card processing happens. But unlike the
        # original, confirming payment here actually finalizes a real
        # booking in the database instead of just redirecting.
        booking.status = "active"
        booking.started_at = datetime.utcnow()
        db.session.commit()
        tracking.set_active_booking(booking.cycle_id, booking.id)
        return redirect(url_for("payment_success", booking_id=booking.id))

    return render_template("payment.html", booking=booking)


@app.route("/payment-success/<int:booking_id>")
@login_required
def payment_success(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user().id:
        return redirect(url_for("home"))
    return render_template("pay_success.html", booking=booking)


@app.route("/bookings")
@login_required
def bookings():
    my_bookings = (
        Booking.query.filter_by(user_id=current_user().id)
        .order_by(Booking.created_at.desc())
        .all()
    )
    return render_template("bookings.html", bookings=my_bookings)


@app.route("/cancel/<int:booking_id>", methods=["POST"])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user().id:
        flash("That booking doesn't belong to your account.", "error")
        return redirect(url_for("bookings"))

    if booking.status in ("active", "pending_payment"):
        was_active = booking.status == "active"
        booking.status = "cancelled"
        booking.ended_at = datetime.utcnow()
        db.session.commit()
        if was_active:
            tracking.set_active_booking(booking.cycle_id, None)
        flash("Booking cancelled.", "success")

    return redirect(url_for("bookings"))


@app.route("/end-ride/<int:booking_id>", methods=["POST"])
@login_required
def end_ride(booking_id):
    """Rider taps 'End ride' when they're done - locks in the real
    distance travelled (from the live GPS simulation) onto the booking
    and frees the cycle back up."""
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user().id:
        flash("That booking doesn't belong to your account.", "error")
        return redirect(url_for("bookings"))

    if booking.status == "active":
        booking.distance_km = tracking.get_booking_distance(booking.id)
        booking.status = "completed"
        booking.ended_at = datetime.utcnow()
        db.session.commit()
        tracking.set_active_booking(booking.cycle_id, None)
        flash(f"Ride ended - you covered {booking.distance_km} km. Mind leaving a rating?", "success")

    return redirect(url_for("bookings"))


@app.route("/rate/<int:booking_id>", methods=["POST"])
@login_required
def rate_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user().id:
        flash("That booking doesn't belong to your account.", "error")
        return redirect(url_for("bookings"))

    if booking.status == "completed" and booking.rider_rating is None:
        try:
            stars = int(request.form.get("stars", 0))
        except ValueError:
            stars = 0
        if 1 <= stars <= 5:
            booking.rider_rating = stars
            booking.rider_review = request.form.get("review", "").strip()[:300]
            db.session.commit()
            flash("Thanks for the rating!", "success")
        else:
            flash("Pick a star rating between 1 and 5.", "error")

    return redirect(url_for("bookings"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    my_bookings = Booking.query.filter_by(user_id=user.id).all()
    completed = [b for b in my_bookings if b.status == "completed"]

    total_rides = len(completed)
    total_hours = sum(b.hours for b in completed)
    total_distance = round(sum(b.distance_km for b in completed), 2)
    total_spent = sum(b.total_price for b in completed)

    category_counts = {}
    for b in completed:
        category_counts[b.cycle.category] = category_counts.get(b.cycle.category, 0) + 1
    favorite_category = max(category_counts, key=category_counts.get) if category_counts else None

    active_now = Booking.query.filter_by(user_id=user.id, status="active").count()

    return render_template(
        "dashboard.html",
        total_rides=total_rides,
        total_hours=total_hours,
        total_distance=total_distance,
        total_spent=total_spent,
        favorite_category=favorite_category,
        active_now=active_now,
    )


@app.route("/track/<int:cycle_id>")
@login_required
def track(cycle_id):
    cycle = Cycle.query.get_or_404(cycle_id)
    my_active_booking = Booking.query.filter_by(
        cycle_id=cycle_id, user_id=current_user().id, status="active"
    ).first()
    return render_template("track.html", cycle=cycle, booking=my_active_booking)


@app.route("/fleet-map")
@login_required
def fleet_map():
    """Live map of every cycle currently out on the road."""
    active_bookings = Booking.query.filter_by(status="active").all()
    cycle_ids = [b.cycle_id for b in active_bookings]
    cycles = Cycle.query.filter(Cycle.id.in_(cycle_ids)).all() if cycle_ids else []
    return render_template("fleet_map.html", cycles=cycles)


# --------------------------------------------------------------------------
# JSON API - polled by the live tracking map
# --------------------------------------------------------------------------
@app.route("/api/location/<int:cycle_id>")
@login_required
def api_location(cycle_id):
    loc = tracking.get_location(cycle_id)
    if not loc:
        return jsonify({"error": "not found"}), 404
    return jsonify(loc)


@app.route("/api/locations")
@login_required
def api_locations():
    return jsonify(tracking.get_all_locations())


@app.route("/api/route/<int:cycle_id>")
@login_required
def api_route(cycle_id):
    return jsonify(tracking.get_route(cycle_id))


@app.route("/api/booking-distance/<int:booking_id>")
@login_required
def api_booking_distance(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user().id:
        return jsonify({"error": "forbidden"}), 403
    return jsonify({"distance_km": tracking.get_booking_distance(booking_id),
                     "elapsed_minutes": round(booking.elapsed_minutes(), 1),
                     "paid_minutes": booking.paid_minutes(),
                     "overdue": booking.is_overdue()})


# --------------------------------------------------------------------------
# Startup: create tables + seed cycles once, then start the GPS simulator
# --------------------------------------------------------------------------
def bootstrap():
    with app.app_context():
        db.create_all()
        if Cycle.query.count() == 0:
            for data in CYCLES:
                db.session.add(Cycle(**data))
            db.session.commit()
            print(f"Seeded {len(CYCLES)} cycles into the database.")

        tracking.init_locations(Cycle.query.all())

        # If the app was restarted while a ride was active, re-attach
        # that booking to the tracker so its distance keeps accumulating.
        for b in Booking.query.filter_by(status="active").all():
            tracking.set_active_booking(b.cycle_id, b.id)

        tracking.start_background_simulation()


bootstrap()

if __name__ == "__main__":
    app.run(debug=True)
