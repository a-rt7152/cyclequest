"""
Simulated live GPS tracking - route-based, not random jitter.

Real bike-share GPS doesn't teleport around randomly - it moves along
streets at a roughly steady speed. So instead of nudging each cycle in
a random direction every tick, this module:

  1. Generates a fixed loop "route" for every cycle when the app starts
     (a handful of waypoints that form a loop around its home base).
  2. Moves each cycle along that route at a steady speed (with small,
     gradual speed variation - like a rider slowing at corners), looping
     back to the start when it completes the loop.
  3. Reports interpolated position + heading + current speed + distance
     travelled, ticking every second for smooth movement.

Cycles that are not currently on an active booking still "wander" the
loop slowly (as if staged around the depot) so the fleet map has some
life to it, but distance is only counted against a real booking.
"""
import math
import random
import threading
import time

_lock = threading.Lock()
_state = {}            # cycle_id -> simulation state dict
_active_bookings = {}  # cycle_id -> booking_id (set by app.py)
_booking_distance = {}  # booking_id -> cumulative km ridden

TICK_SECONDS = 1
EARTH_RADIUS_KM = 6371.0


def _make_loop_route(base_lat, base_lng, points=7, radius_km=0.9):
    """Build a rough loop of waypoints around a base point, like a
    delivery route through a neighbourhood rather than a random scatter.
    Radius and angle jitter per point so it doesn't look like a perfect
    circle."""
    route = []
    for i in range(points):
        angle = (2 * math.pi * i / points) + random.uniform(-0.25, 0.25)
        r = radius_km * random.uniform(0.55, 1.0)
        dlat = (r / EARTH_RADIUS_KM) * (180 / math.pi)
        dlng = (r / EARTH_RADIUS_KM) * (180 / math.pi) / math.cos(math.radians(base_lat))
        route.append((
            round(base_lat + dlat * math.sin(angle), 6),
            round(base_lng + dlng * math.cos(angle), 6),
        ))
    return route


def _haversine_km(p1, p2):
    lat1, lng1, lat2, lng2 = map(math.radians, [p1[0], p1[1], p2[0], p2[1]])
    dlat, dlng = lat2 - lat1, lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _bearing(p1, p2):
    lat1, lat2 = map(math.radians, [p1[0], p2[0]])
    dlng = math.radians(p2[1] - p1[1])
    y = math.sin(dlng) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlng)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def init_locations(cycles):
    with _lock:
        for cycle in cycles:
            route = _make_loop_route(cycle.base_lat, cycle.base_lng)
            _state[cycle.id] = {
                "route": route,
                "seg": 0,
                "progress_km": 0.0,       # distance travelled into current segment
                "target_speed": random.uniform(11, 17),   # km/h
                "speed": random.uniform(11, 17),
                "lat": route[0][0],
                "lng": route[0][1],
                "heading": 0.0,
            }


def register_new_cycle(cycle):
    with _lock:
        route = _make_loop_route(cycle.base_lat, cycle.base_lng)
        _state[cycle.id] = {
            "route": route, "seg": 0, "progress_km": 0.0,
            "target_speed": random.uniform(11, 17), "speed": random.uniform(11, 17),
            "lat": route[0][0], "lng": route[0][1], "heading": 0.0,
        }


def set_active_booking(cycle_id, booking_id):
    """Called by app.py when a booking starts/ends, so distance travelled
    can be attributed to the right booking instead of just the cycle."""
    with _lock:
        if booking_id is None:
            _active_bookings.pop(cycle_id, None)
        else:
            _active_bookings[cycle_id] = booking_id
            _booking_distance.setdefault(booking_id, 0.0)


def get_booking_distance(booking_id):
    with _lock:
        return round(_booking_distance.get(booking_id, 0.0), 2)


def get_route(cycle_id):
    with _lock:
        st = _state.get(cycle_id)
        return list(st["route"]) if st else []


def get_location(cycle_id):
    with _lock:
        st = _state.get(cycle_id)
        if not st:
            return None
        return {
            "lat": st["lat"],
            "lng": st["lng"],
            "heading": round(st["heading"], 1),
            "speed_kmh": round(st["speed"], 1),
        }


def get_all_locations():
    with _lock:
        return {cid: {"lat": s["lat"], "lng": s["lng"],
                      "heading": round(s["heading"], 1),
                      "speed_kmh": round(s["speed"], 1)}
                for cid, s in _state.items()}


def _advance(cycle_id, st, dt_hours):
    route = st["route"]
    n = len(route)

    # Speed drifts gently toward a slowly-changing target, instead of
    # jumping - this is what makes it feel like a real ride rather than
    # a teleporting dot.
    if random.random() < 0.02:
        st["target_speed"] = random.uniform(9, 19)
    st["speed"] += (st["target_speed"] - st["speed"]) * 0.05

    distance_this_tick = st["speed"] * dt_hours

    remaining = distance_this_tick
    while remaining > 0:
        a = route[st["seg"] % n]
        b = route[(st["seg"] + 1) % n]
        seg_len = _haversine_km(a, b) or 0.0001
        left_in_seg = seg_len - st["progress_km"]

        if remaining < left_in_seg:
            st["progress_km"] += remaining
            frac = st["progress_km"] / seg_len
            st["lat"] = a[0] + (b[0] - a[0]) * frac
            st["lng"] = a[1] + (b[1] - a[1]) * frac
            st["heading"] = _bearing(a, b)
            remaining = 0
        else:
            remaining -= left_in_seg
            st["seg"] = (st["seg"] + 1) % n
            st["progress_km"] = 0.0
            st["lat"], st["lng"] = b

    booking_id = _active_bookings.get(cycle_id)
    if booking_id is not None:
        _booking_distance[booking_id] = _booking_distance.get(booking_id, 0.0) + distance_this_tick


def _tick_loop():
    while True:
        time.sleep(TICK_SECONDS)
        dt_hours = TICK_SECONDS / 3600
        with _lock:
            for cycle_id, st in _state.items():
                _advance(cycle_id, st, dt_hours)


def start_background_simulation():
    thread = threading.Thread(target=_tick_loop, daemon=True)
    thread.start()
