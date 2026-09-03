"""
Starter data for the cycle fleet.
Each cycle gets its own base GPS point scattered around a city center
so the live tracking map has cycles spread out realistically instead
of stacked on one spot.
"""
import random

CITY_CENTER = (13.0827, 80.2707)  # Chennai - used only as a demo map center


def _scattered_point():
    lat = CITY_CENTER[0] + random.uniform(-0.02, 0.02)
    lng = CITY_CENTER[1] + random.uniform(-0.02, 0.02)
    return round(lat, 6), round(lng, 6)


CYCLES = []

# ---- Adventure cycles (kept the original descriptions/prices, they were fine) ----
_adventure = [
    ("Trailblazer Rocky", 80, 4.7, "A perfect choice for adventure and rough terrain.", "adv1.jpg"),
    ("Endurance Pro", 90, 4.5, "Ideal for long-distance rides with great stability.", "adv2.jpg"),
    ("Hillcrest Climber", 100, 4.3, "Built for steep hills and rugged paths.", "adv3.jpg"),
    ("Extreme Trailhawk", 90, 5.0, "Best for extreme adventure and endurance trails.", "adv4.jpg"),
    ("Mountain Grip X", 90, 4.8, "Perfect for mountain biking with superior grip.", "adv5.jpg"),
    ("Speedster Trail", 100, 4.2, "Lightweight frame, great for speed on rough trails.", "adv6.jpg"),
    ("Rockrider Stable", 120, 3.9, "Built for stability, ideal for rocky and bumpy rides.", "adv7.jpg"),
    ("Pro Terrain Elite", 140, 4.4, "Premium cycle for professional riders, unmatched performance.", "adv8.jpg"),
    ("Beginner's Trailmate", 60, 4.6, "Affordable and reliable, perfect for beginners on tough terrains.", "adv9.jpg"),
]
for name, price, rating, desc, img in _adventure:
    lat, lng = _scattered_point()
    CYCLES.append(dict(name=name, category="adventure", price_per_hour=price, rating=rating,
                        description=desc, image_file=f"adventure/{img}", total_units=5,
                        base_lat=lat, base_lng=lng))

# ---- Leisure cycles ----
_leisure = [
    ("City Cruiser Breeze", 40, 4.6, "Smooth, comfortable ride around the park or campus.", "leisure1.jpg"),
    ("Sofia Ladybird", 45, 4.8, "Stylish and easy-going, great for a casual evening ride.", "leisure2.jpg"),
    ("Park Roller Classic", 35, 4.3, "Simple and steady - ideal for a relaxed weekend ride.", "leisure3.jpg"),
    ("Boulevard Glide", 50, 4.5, "Extra cushioned seat, built for long comfortable rides.", "leisure4.jpg"),
    ("Sunset Wanderer", 40, 4.4, "Lightweight cruiser, perfect for evening rides by the coast.", "leisure5.jpg"),
    ("Campus Commuter", 35, 4.7, "Reliable everyday cycle, great for short city commutes.", "leisure6.jpg"),
]
for name, price, rating, desc, img in _leisure:
    lat, lng = _scattered_point()
    CYCLES.append(dict(name=name, category="leisure", price_per_hour=price, rating=rating,
                        description=desc, image_file=f"leisure/{img}", total_units=6,
                        base_lat=lat, base_lng=lng))

# ---- Kids cycles ----
_kids = [
    ("Lil' Explorer", 25, 4.9, "Training wheels included - great for first-time riders.", "kids1.jpg"),
    ("Junior Speedster", 25, 4.6, "Bright, fun design with an easy-grip handlebar.", "kids2.jpg"),
    ("Rainbow Rider", 20, 4.7, "Lightweight frame sized for younger kids.", "kids3.jpg"),
    ("Little Champ", 25, 4.5, "Sturdy build with a comfortable padded seat.", "kids4.jpg"),
]
for name, price, rating, desc, img in _kids:
    lat, lng = _scattered_point()
    CYCLES.append(dict(name=name, category="kids", price_per_hour=price, rating=rating,
                        description=desc, image_file=f"kids/{img}", total_units=4,
                        base_lat=lat, base_lng=lng))
