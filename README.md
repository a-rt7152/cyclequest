# Cycle Quest

A cycle rental app with real accounts, a real bookings database, and **simulated live GPS tracking** for every cycle currently on a ride.

This started as a static front-end college project (HTML/CSS pages with no real backend — the "login" accepted any password, "booking" always showed the same one cycle, and payment just redirected pages without saving anything). It's been rebuilt from scratch with a working Flask backend.

## Features

- **Real authentication** — passwords are hashed with Werkzeug, accounts are stored in a database, duplicate usernames/emails are rejected
- **Real cycle inventory** — 19 cycles across Leisure / Adventure / Kids categories, each with a price, rating, description, and a live-updating availability count
- **Real bookings** — booking a cycle checks actual availability, creates a database record, and reduces the available count for everyone else until it's cancelled
- **Simulated live GPS tracking** — every cycle has a position that a background thread nudges every few seconds, shown on an interactive Leaflet map (`/track/<cycle_id>` for one cycle, `/fleet-map` for every cycle currently rented out)
- **Simulated payment step** — no real card processing (this is a student project, not a payment provider), but confirming it actually finalizes the booking in the database, unlike the original
- Sort cycles by price or rating, cancel bookings, view booking history

## Tech stack

- **Backend:** Python, Flask, Flask-SQLAlchemy
- **Database:** SQLite (single file, zero setup)
- **Frontend:** Server-rendered Jinja2 templates, vanilla JS for the live map polling
- **Map:** Leaflet.js + OpenStreetMap tiles

## Running it locally

```bash
# 1. Clone the repo
git clone https://github.com/<your-username>/cyclequest.git
cd cyclequest

# 2. Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run it
python app.py
```

Open **http://127.0.0.1:5000** in your browser. The database and cycle fleet are created automatically the first time you run it — no manual DB setup needed.

## Project structure

```
cyclequest/
├── app.py            # Flask app + all routes
├── models.py         # User / Cycle / Booking database models
├── seed_data.py       # Starter fleet of 19 cycles
├── tracking.py        # Background thread simulating live GPS movement
├── requirements.txt
├── static/
│   ├── css/style.css
│   └── images/         # Cycle photos, organized by category
└── templates/          # Jinja2 HTML templates
```

## How the live tracking works

There's no real hardware GPS on these cycles (it's a student project), so `tracking.py` simulates one: a background thread nudges every cycle's latitude/longitude by a small random step every 3 seconds, occasionally changing heading like a rider turning a corner. The frontend polls `/api/location/<cycle_id>` (or `/api/locations` for the whole fleet) every 3 seconds and moves the map marker. This is the same basic approach real bike-share apps use, just without the actual hardware.

## What changed from the original project

| Before | Now |
|---|---|
| Login accepted any username/password | Real accounts, hashed passwords, validation |
| Booking page always showed one hardcoded cycle | Booking pulls live availability from the database |
| Payment just redirected to a "success" page | Payment step actually finalizes a database record |
| No live tracking despite being in the project brief | Real simulated GPS + live map |
| Cycle images looked squished/inconsistent | Standardized, cleanly cropped thumbnails |
| Unused Flask/MySQL script, disconnected from the site | Replaced with a working Flask + SQLite backend actually wired to every page |


## Contributors 

This started as a group college project. Credit where it's due: - [priya-1234-cell](https://github.com/priya-1234-cell) - [a-rt7152](https://github.com/a-rt7152) Save the file when you're done.
