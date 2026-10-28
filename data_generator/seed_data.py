"""
Fills FoodDeliveryDB with realistic, REPRODUCIBLE sample data.

Run from the repository root:
    python data_generator/seed_data.py

What it does, in order:
  1. Builds every row in Python memory (cities -> ... -> ratings).
  2. Connects with an ADMIN connection (your Windows login by default).
  3. In ONE transaction: deletes the old data (children first) and inserts
     the new data (parents first). If anything fails, nothing changes.
  4. Prints row counts and the "planted facts" (dates of the patterns).

Why build everything in memory first? Generating an order needs to know the
customer's previous orders, the restaurant's menu, which riders are active,
and so on. Keeping it all in Python lists makes that logic simple, and the
whole data set (~400k rows) easily fits in memory.

The patterns we plant on purpose are documented in PLANTED_INSIGHTS.md and
the knobs that control them live in config.py.
"""

import math
import os
import random
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pyodbc
from dotenv import load_dotenv
from faker import Faker

import config as cfg
import reference_data as ref

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

# ONE random generator for everything, created from a fixed seed.
# Never use the global `random.xxx()` functions in this file - always `rng`,
# otherwise the output would no longer be reproducible.
rng = random.Random(cfg.RANDOM_SEED)
fake = Faker("en_IN")
fake.seed_instance(cfg.RANDOM_SEED)

# Ratings must never be in the future relative to when the seed ran.
RUN_STARTED_AT = datetime.now().replace(microsecond=0)


# =====================================================================
# Small helpers
# =====================================================================

def money(value) -> Decimal:
    """Round to 2 decimal places as a Decimal (never float) so the
    database CHECK `TotalAmount = ItemTotal + DeliveryFee - DiscountAmount`
    holds exactly. Floats would give errors like 0.1 + 0.2 = 0.30000000000000004."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def menu_price(raw: float) -> Decimal:
    """Turn a raw price into a 'menu-looking' price: 249, 199, 85..."""
    if raw < 60:
        return money(max(20, round(raw / 5) * 5))
    return money(round(raw / 10) * 10 - 1)


def random_date(start: date, end: date) -> date:
    """Uniform random date between start and end (inclusive)."""
    if end <= start:
        return start
    return start + timedelta(days=rng.randint(0, (end - start).days))


def add_months(d: date, months: int) -> date:
    """First day of the month `months` after d's month."""
    month_index = d.year * 12 + (d.month - 1) + months
    return date(month_index // 12, month_index % 12 + 1, 1)


def month_number(d: date) -> int:
    """Months since START_DATE (0 for the first month of data)."""
    return (d.year - cfg.START_DATE.year) * 12 + d.month - cfg.START_DATE.month


def pick(items, weights):
    """Pick one item using relative weights."""
    return rng.choices(items, weights=weights, k=1)[0]


def allocate(total: int, weights: dict) -> dict:
    """Split `total` into whole numbers proportional to `weights`
    (largest-remainder method, so the parts always add up to `total`)."""
    weight_sum = sum(weights.values())
    exact = {key: total * w / weight_sum for key, w in weights.items()}
    counts = {key: math.floor(v) for key, v in exact.items()}
    leftover = total - sum(counts.values())
    for key in sorted(exact, key=lambda k: exact[k] - counts[k], reverse=True)[:leftover]:
        counts[key] += 1
    return counts


def is_lunch_peak(t: datetime) -> bool:
    return (12, 0) <= (t.hour, t.minute) < (14, 30)


def is_dinner_peak(t: datetime) -> bool:
    return (19, 30) <= (t.hour, t.minute) < (22, 30)


# =====================================================================
# In-memory model objects (only the fields the generator needs)
# =====================================================================

@dataclass
class City:
    id: int
    name: str
    state: str
    launch_date: date
    areas: list = field(default_factory=list)


@dataclass
class Area:
    id: int
    city: City
    name: str
    pincode: str


@dataclass
class MenuItem:
    id: int
    restaurant_id: int
    name: str
    category: str
    price: Decimal
    is_veg: bool
    is_available: bool
    pick_weight: float     # how likely it is to be ordered


@dataclass
class Restaurant:
    id: int
    area: Area
    name: str
    price_range: str
    prep_mins: int
    is_pure_veg: bool
    onboarded: date
    is_active: bool
    cuisines: list
    popularity: float
    last_order_date: date = None   # set for delisted restaurants
    is_problem: bool = False       # planted: high cancellations, low ratings
    menu: list = field(default_factory=list)

    def is_open_on(self, day: date) -> bool:
        return self.onboarded <= day and (self.last_order_date is None or day <= self.last_order_date)


@dataclass
class Customer:
    id: int
    name: str
    email: str
    phone: str
    area: Area
    signup: date
    is_premium: bool
    order_weight: float          # relative ordering frequency
    active_to: date              # last day they may order (churned customers stop early)
    is_deal_hunter: bool = False


@dataclass
class Partner:
    id: int
    name: str
    city: City
    vehicle: str
    join_date: date
    left_date: date            # None = still active
    is_slow: bool
    speed_factor: float

    def works_on(self, day: date) -> bool:
        return self.join_date <= day and (self.left_date is None or day <= self.left_date)


@dataclass
class Coupon:
    id: int
    code: str
    discount_type: str
    value: Decimal
    max_discount: Decimal
    min_order: Decimal
    valid_from: date
    valid_to: date
    new_user_only: bool
    rule: str = None           # extra generator-only rule: weekend / lunch / premium
    pick_weight: float = 1.0


# =====================================================================
# 1. Cities and areas
# =====================================================================

def build_cities() -> list:
    new_city_launch = add_months(cfg.START_DATE, cfg.NEW_CITY_LAUNCH_MONTHS_AFTER_START)
    cities, area_id = [], 0
    for city_id, (name, state, launch, area_list) in enumerate(ref.CITIES, start=1):
        city = City(city_id, name, state, launch or new_city_launch)
        for area_name, pincode in area_list:
            area_id += 1
            city.areas.append(Area(area_id, city, area_name, pincode))
        cities.append(city)
    return cities


# =====================================================================
# 2. Restaurants, their cuisines and menus
# =====================================================================

def choose_cuisines(city: City, pure_veg_bias: float):
    """Pick a main cuisine (local favourites more likely) plus 0-2 extras.
    Returns (cuisine list, is_pure_veg)."""
    def allowed(cuisine):
        cities_allowed = ref.LOCAL_ONLY_CUISINES.get(cuisine)
        return cities_allowed is None or city.name in cities_allowed

    options = [c for c in ref.CUISINES if allowed(c)]
    boosts = ref.CITY_CUISINE_BOOST.get(city.name, {})
    main = pick(options, [boosts.get(c, 1) for c in options])

    is_pure_veg = main in ref.ALWAYS_VEG_CUISINES or (
        main in ref.VEG_FRIENDLY_CUISINES and rng.random() < pure_veg_bias)

    extra_options = [c for c in options if c != main
                     and (not is_pure_veg or c in ref.VEG_FRIENDLY_CUISINES)]
    extra_count = pick([0, 1, 2], [40, 40, 20])
    return [main] + rng.sample(extra_options, extra_count), is_pure_veg


def unique_restaurant_name(main_cuisine: str, area: Area, used: set) -> str:
    for _ in range(30):
        name = f"{rng.choice(ref.NAME_PREFIXES)} {rng.choice(ref.NAME_SUFFIXES[main_cuisine])}"
        if name not in used:
            return name
    return f"{name} {area.name}"   # extremely rare fallback


def build_menu(restaurant: Restaurant, first_id: int) -> list:
    """~12 dishes: mostly from the main cuisine, some from the extra
    cuisines, then a drink/dessert if the menu still needs one."""
    def veg_ok(dish):
        return dish[2] or not restaurant.is_pure_veg

    main, extras = restaurant.cuisines[0], restaurant.cuisines[1:]
    main_dishes = [d for d in ref.DISHES[main] if veg_ok(d)]
    chosen = rng.sample(main_dishes, min(len(main_dishes), rng.randint(7, 9)))
    for cuisine in extras:
        extra_dishes = [d for d in ref.DISHES[cuisine] if veg_ok(d) and d[0] not in {c[0] for c in chosen}]
        chosen += rng.sample(extra_dishes, min(len(extra_dishes), 2))
    filler = [d for d in ref.EXTRA_BEVERAGES + ref.EXTRA_DESSERTS if d[0] not in {c[0] for c in chosen}]
    rng.shuffle(filler)
    while len(chosen) < cfg.MENU_ITEMS_PER_RESTAURANT and filler:
        chosen.append(filler.pop())
    chosen = chosen[:cfg.MENU_ITEMS_PER_RESTAURANT]

    category_weight = {"Main Course": 3.0, "Combo": 2.5, "Starter": 1.6, "Beverage": 1.0, "Dessert": 0.9}
    multiplier = ref.PRICE_RANGE_MULTIPLIER[restaurant.price_range]
    menu = []
    for offset, (name, category, is_veg, base_price, popularity) in enumerate(chosen):
        menu.append(MenuItem(
            id=first_id + offset,
            restaurant_id=restaurant.id,
            name=name,
            category=category,
            price=menu_price(base_price * multiplier * rng.uniform(0.9, 1.12)),
            is_veg=is_veg,
            is_available=rng.random() > 0.05,
            pick_weight=popularity * category_weight[category],
        ))
    return menu


def build_restaurants(cities: list) -> list:
    counts = allocate(cfg.NUM_RESTAURANTS, cfg.CITY_ORDER_WEIGHTS)

    # Spread each fictional chain's outlets over different cities.
    chain_outlets = {city.name: [] for city in cities}
    for chain_name, cuisine, outlets in ref.CHAINS:
        for city in rng.sample(cities, outlets):
            chain_outlets[city.name].append((chain_name, cuisine))

    restaurants, menu_id = [], 1
    for city in cities:
        used_names = set()
        pure_veg_bias = 0.45 if city.name == cfg.NEW_CITY else 0.18
        for i in range(counts[city.name]):
            area = rng.choice(city.areas)
            if i < len(chain_outlets[city.name]):
                name, main = chain_outlets[city.name][i]
                cuisines, is_pure_veg = [main], False
            else:
                cuisines, is_pure_veg = choose_cuisines(city, pure_veg_bias)
                name = unique_restaurant_name(cuisines[0], area, used_names)
            used_names.add(name)

            if city.name == cfg.NEW_CITY:
                onboarded = random_date(city.launch_date - timedelta(days=45),
                                        city.launch_date + timedelta(days=150))
            elif rng.random() < 0.85:
                onboarded = random_date(max(city.launch_date, date(2018, 1, 1)),
                                        cfg.START_DATE - timedelta(days=1))
            else:
                onboarded = random_date(cfg.START_DATE, cfg.END_DATE - timedelta(days=30))

            restaurant = Restaurant(
                id=len(restaurants) + 1,
                area=area,
                name=name,
                price_range=pick(list(ref.PRICE_RANGE_WEIGHTS), list(ref.PRICE_RANGE_WEIGHTS.values())),
                prep_mins=rng.randint(10, 22) + (5 if cuisines[0] in ("Biryani", "Mughlai") else 0),
                is_pure_veg=is_pure_veg,
                onboarded=onboarded,
                is_active=True,
                cuisines=cuisines,
                popularity=rng.lognormvariate(0, 0.6),
            )

            # ~4% of restaurants were delisted during the year.
            if rng.random() < 0.04:
                last_day = random_date(cfg.START_DATE + timedelta(days=120), cfg.END_DATE - timedelta(days=45))
                if last_day > onboarded + timedelta(days=30):
                    restaurant.is_active = False
                    restaurant.last_order_date = last_day

            restaurant.menu = build_menu(restaurant, menu_id)
            menu_id += len(restaurant.menu)
            restaurants.append(restaurant)

    # PLANTED: a handful of slow, badly-run restaurants in the big cities.
    candidates = [r for r in restaurants
                  if r.is_active and r.onboarded < cfg.START_DATE and not any(r.name == c[0] for c in ref.CHAINS)
                  and r.area.city.name in ("Bengaluru", "Mumbai", "Delhi", "Hyderabad")]
    for r in rng.sample(candidates, cfg.PROBLEM_RESTAURANT_COUNT):
        r.is_problem = True
        r.prep_mins = rng.randint(40, 55)
        r.popularity = max(r.popularity, 1.2)   # busy enough to show up in rankings
    return restaurants


# =====================================================================
# 3. Customers
# =====================================================================

def make_email(full_name: str, used: set) -> str:
    base = ".".join(part.lower() for part in full_name.replace("'", "").split())
    while True:
        email = f"{base}{rng.randint(1, 9999)}@{rng.choice(ref.EMAIL_DOMAINS)}"
        if email not in used:
            used.add(email)
            return email


def make_phone() -> str:
    """10-digit Indian mobile number (starts with 6, 7, 8 or 9)."""
    return f"{rng.choice('6789')}{rng.randint(0, 999_999_999):09d}"


def clean_name(raw: str) -> str:
    """Faker sometimes adds titles like 'Dr.'; drop them."""
    parts = [p for p in raw.split() if p.rstrip(".") not in ("Dr", "Mr", "Mrs", "Ms", "Miss")]
    return " ".join(parts)


def build_customers(cities: list) -> list:
    weights = dict(cfg.CITY_ORDER_WEIGHTS)
    weights[cfg.NEW_CITY] = cfg.NEW_CITY_CUSTOMER_SHARE
    counts = allocate(cfg.NUM_CUSTOMERS, weights)

    mega_start = cfg.START_DATE + timedelta(days=cfg.MEGA_CAMPAIGN_START_DAY)
    mega_end = mega_start + timedelta(days=cfg.MEGA_CAMPAIGN_LENGTH_DAYS - 1)
    churn_latest = cfg.END_DATE - timedelta(days=cfg.CHURN_INACTIVE_DAYS + 1)

    customers, used_emails = [], set()
    for city in cities:
        for _ in range(counts[city.name]):
            name = clean_name(fake.name())
            is_deal_hunter = city.name != cfg.NEW_CITY and rng.random() < cfg.DEAL_HUNTER_SHARE

            if is_deal_hunter:
                # PLANTED: signs up during the MEGA60 campaign, gone shortly after.
                signup = random_date(mega_start, mega_end - timedelta(days=7))
            elif city.name == cfg.NEW_CITY:
                # Sign-ups accelerate after launch (sqrt skews towards later dates).
                span = (cfg.END_DATE - city.launch_date).days
                signup = city.launch_date - timedelta(days=7) + timedelta(days=int(span * math.sqrt(rng.random())))
            elif rng.random() < 0.55:
                signup = random_date(max(city.launch_date, date(2019, 1, 1)), cfg.START_DATE - timedelta(days=1))
            else:
                signup = random_date(cfg.START_DATE, cfg.END_DATE - timedelta(days=14))

            is_premium = not is_deal_hunter and rng.random() < cfg.PREMIUM_SHARE
            order_weight = min(2.5, max(0.5, rng.lognormvariate(0, 0.35)))
            if is_premium:
                order_weight *= cfg.PREMIUM_ORDER_MULTIPLIER

            active_to = cfg.END_DATE
            if is_deal_hunter:
                active_to = signup + timedelta(days=cfg.DEAL_HUNTER_ACTIVE_DAYS)
            elif rng.random() < cfg.CHURN_SHARE:
                # PLANTED churn: stops ordering at some point before the last 60 days.
                earliest = max(signup, cfg.START_DATE) + timedelta(days=30)
                if earliest < churn_latest:
                    active_to = random_date(earliest, churn_latest)

            customers.append(Customer(
                id=len(customers) + 1,
                name=name,
                email=make_email(name, used_emails),
                phone=make_phone(),
                area=rng.choice(city.areas),
                signup=signup,
                is_premium=is_premium,
                order_weight=order_weight,
                active_to=active_to,
                is_deal_hunter=is_deal_hunter,
            ))
    return customers


# =====================================================================
# 4. Delivery partners
# =====================================================================

def build_partners(cities: list) -> list:
    weights = dict(cfg.CITY_ORDER_WEIGHTS)
    weights[cfg.NEW_CITY] *= 0.6   # smaller fleet in the new city
    counts = allocate(cfg.NUM_DELIVERY_PARTNERS, weights)

    partners = []
    for city in cities:
        for i in range(counts[city.name]):
            if city.name == cfg.NEW_CITY:
                # The first riders are hired just before launch, the rest over time.
                if i < 8:
                    join = random_date(city.launch_date - timedelta(days=20), city.launch_date - timedelta(days=1))
                else:
                    join = random_date(city.launch_date, cfg.END_DATE - timedelta(days=20))
            elif rng.random() < 0.7:
                join = random_date(date(2019, 1, 1), cfg.START_DATE - timedelta(days=1))
            else:
                join = random_date(cfg.START_DATE, cfg.END_DATE - timedelta(days=20))

            left = None
            if rng.random() < cfg.INACTIVE_PARTNER_SHARE:
                earliest = max(join, cfg.START_DATE) + timedelta(days=30)
                if earliest < cfg.END_DATE - timedelta(days=20):
                    left = random_date(earliest, cfg.END_DATE - timedelta(days=20))

            vehicle = pick(ref.VEHICLE_TYPES, ref.VEHICLE_WEIGHTS)
            is_slow = rng.random() < cfg.SLOW_PARTNER_SHARE
            speed = ref.VEHICLE_SPEED_FACTOR[vehicle] * (cfg.SLOW_PARTNER_SPEED_FACTOR if is_slow else 1.0)
            partners.append(Partner(len(partners) + 1, clean_name(fake.name()), city, vehicle,
                                    join, left, is_slow, speed))
    return partners


# =====================================================================
# 5. Coupons
# =====================================================================

def first_date_in_range(candidates) -> date:
    return next((d for d in candidates if cfg.START_DATE <= d <= cfg.END_DATE), None)


def build_coupons() -> list:
    start, end = cfg.START_DATE, cfg.END_DATE
    always_from, always_to = start - timedelta(days=400), end + timedelta(days=180)

    diwali = first_date_in_range(cfg.DIWALI_DATES) or next(d for d in cfg.DIWALI_DATES if d > end)
    new_year = first_date_in_range(date(y, 1, 1) for y in (start.year, start.year + 1))
    monsoon = first_date_in_range(date(y, cfg.MONSOON_MONTH, 1) for y in (start.year, start.year + 1))
    mega_from = start + timedelta(days=cfg.MEGA_CAMPAIGN_START_DAY)
    mega_to = mega_from + timedelta(days=cfg.MEGA_CAMPAIGN_LENGTH_DAYS - 1)

    # (code, type, value, max discount, min order, from, to, new-user-only, rule, pick weight)
    specs = [
        ("WELCOME50", "Percent", 50, 100, 149, always_from, always_to, True, None, 3),
        ("FIRSTBITE", "Flat", 75, None, 199, always_from, always_to, True, None, 2),
        ("WEEKEND100", "Flat", 100, None, 499, always_from, always_to, False, "weekend", 4),
        ("SAVE20", "Percent", 20, 80, 199, always_from, always_to, False, None, 3),
        ("FEAST150", "Flat", 150, None, 799, always_from, always_to, False, None, 2),
        ("PARTY25", "Percent", 25, 150, 999, always_from, always_to, False, None, 1),
        ("MEGA60", "Percent", 60, 120, 159, mega_from, mega_to, False, None, 6),
        (f"DIWALI{diwali.year % 100}", "Percent", 30, 150, 299,
         diwali - timedelta(days=14), diwali + timedelta(days=3), False, None, 14),
        ("MONSOON40", "Percent", 40, 80, 249, monsoon, monsoon + timedelta(days=61), False, None, 4),
        ("LUNCH60", "Flat", 60, None, 249, always_from, always_to, False, "lunch", 2),
        ("PREMIUM15", "Percent", 15, 75, 0, always_from, always_to, False, "premium", 5),
        ("FLAT50", "Flat", 50, None, 249, always_from, always_to, False, None, 3),
        ("TRYNEW30", "Percent", 30, 90, 299, always_from, always_to, False, None, 1),
        (f"NEWYEAR{new_year.year % 100}", "Flat", 125, None, 499,
         new_year - timedelta(days=1), new_year, False, None, 10),
        # Expired before our data starts -> never used (good LEFT JOIN demo).
        ("SUMMER25", "Percent", 25, 100, 349, start - timedelta(days=200), start - timedelta(days=100), False, None, 1),
    ]
    return [Coupon(i, code, kind, money(value), money(cap) if cap else None, money(min_order),
                   valid_from, valid_to, new_only, rule, weight)
            for i, (code, kind, value, cap, min_order, valid_from, valid_to, new_only, rule, weight)
            in enumerate(specs, start=1)]


# =====================================================================
# 6. Orders - step A: WHEN and WHO
# =====================================================================

def day_multiplier(day: date) -> float:
    """Platform-wide demand for a given day: weekends, growth, Diwali."""
    m = cfg.WEEKEND_MULTIPLIER if day.weekday() >= 5 else 1.0
    m *= 1 + cfg.MONTHLY_GROWTH_TREND * month_number(day)
    for diwali in cfg.DIWALI_DATES:
        if (day.year, day.month) == (diwali.year, diwali.month):
            m *= cfg.FESTIVE_MONTH_MULTIPLIER
        if diwali - timedelta(days=cfg.FESTIVE_PEAK_DAYS_BEFORE) <= day <= diwali + timedelta(days=1):
            m *= cfg.FESTIVE_PEAK_MULTIPLIER
    return m


def city_multiplier(city: City, day: date) -> float:
    """City share of demand on a day: base weight, Mumbai monsoon, new-city ramp-up."""
    m = cfg.CITY_ORDER_WEIGHTS[city.name]
    if city.name == cfg.MONSOON_CITY and day.month == cfg.MONSOON_MONTH:
        m *= cfg.MONSOON_ORDER_MULTIPLIER
    if city.name == cfg.NEW_CITY:
        if day < city.launch_date:
            return 0.0
        months_live = month_number(day) - month_number(city.launch_date)
        m *= min(1.0, cfg.NEW_CITY_START_LEVEL * cfg.NEW_CITY_MONTHLY_GROWTH ** months_live)
    return m


def random_time_on(day: date) -> datetime:
    """A time of day drawn from the half-hour demand curve (lunch/dinner peaks)."""
    slot = pick(range(48), cfg.HALF_HOUR_WEIGHTS)
    seconds = slot * 1800 + rng.randint(0, 1799)
    return datetime(day.year, day.month, day.day) + timedelta(seconds=seconds)


def build_order_skeletons(cities: list, customers: list) -> list:
    """Decide how many orders each city gets each day, and which customers place them.
    Returns a chronologically sorted list of (order_datetime, customer)."""
    days = [cfg.START_DATE + timedelta(days=i) for i in range((cfg.END_DATE - cfg.START_DATE).days + 1)]
    expected = {(day, city.id): day_multiplier(day) * city_multiplier(city, day) for day in days for city in cities}
    scale = cfg.TARGET_ORDERS / sum(expected.values())   # makes the total ~TARGET_ORDERS

    # Deal hunters don't follow the normal "order now and then" behaviour;
    # they get a few explicit orders below instead.
    regulars = [c for c in customers if not c.is_deal_hunter]
    customers_by_city = {city.id: [c for c in regulars if c.area.city.id == city.id] for city in cities}
    skeletons = []
    for day in days:
        for city in cities:
            n = round(expected[(day, city.id)] * scale * rng.uniform(0.9, 1.1))
            eligible = [c for c in customers_by_city[city.id] if c.signup <= day <= c.active_to]
            if n == 0 or not eligible:
                continue
            for customer in rng.choices(eligible, weights=[c.order_weight for c in eligible], k=n):
                skeletons.append((random_time_on(day), customer))

    # PLANTED: deal hunters order 1-3 times right after signing up, then never again.
    counts = list(cfg.DEAL_HUNTER_ORDER_COUNTS)
    for customer in (c for c in customers if c.is_deal_hunter):
        for _ in range(pick(counts, list(cfg.DEAL_HUNTER_ORDER_COUNTS.values()))):
            skeletons.append((random_time_on(random_date(customer.signup, customer.active_to)), customer))

    skeletons.sort(key=lambda s: (s[0], s[1].id))   # OrderID will follow time order
    return skeletons


# =====================================================================
# 6. Orders - step B: WHAT happened to each order
# =====================================================================

def coupon_is_usable(coupon: Coupon, customer: Customer, when: datetime, item_total: Decimal) -> bool:
    if not (coupon.valid_from <= when.date() <= coupon.valid_to) or item_total < coupon.min_order:
        return False
    if coupon.rule == "weekend":
        return when.weekday() >= 5
    if coupon.rule == "lunch":
        return (11, 30) <= (when.hour, when.minute) < (15, 0)
    if coupon.rule == "premium":
        return customer.is_premium
    return True


def choose_coupon(coupons, customer, is_first_order, when, item_total):
    usable = [c for c in coupons if coupon_is_usable(c, customer, when, item_total)]
    mega = next((c for c in usable if c.code == "MEGA60"), None)

    # PLANTED: deal hunters almost always use MEGA60 while it runs.
    if customer.is_deal_hunter and mega and rng.random() < cfg.DEAL_HUNTER_MEGA_RATE:
        return mega

    # PLANTED: WELCOME-type coupons are for (and used on) first orders.
    if is_first_order:
        welcome = [c for c in usable if c.new_user_only]
        if welcome and rng.random() < cfg.FIRST_ORDER_WELCOME_RATE:
            return pick(welcome, [c.pick_weight for c in welcome])

    rate = cfg.COUPON_USE_RATE_PREMIUM if customer.is_premium else cfg.COUPON_USE_RATE
    regular = [c for c in usable if not c.new_user_only]
    if regular and rng.random() < rate:
        return pick(regular, [c.pick_weight for c in regular])
    return None


def discount_for(coupon: Coupon, item_total: Decimal) -> Decimal:
    if coupon is None:
        return money(0)
    if coupon.discount_type == "Percent":
        discount = money(item_total * coupon.value / 100)
        if coupon.max_discount is not None:
            discount = min(discount, coupon.max_discount)
    else:
        discount = coupon.value
    return min(discount, item_total)   # a discount can never exceed the food bill


def delivery_fee_for(customer: Customer, distance_km: Decimal) -> Decimal:
    if customer.is_premium:
        return money(0)        # premium perk: free delivery
    if distance_km < 3:
        return money(25)
    if distance_km < 7:
        return money(39)
    return money(59)


def choose_order_items(restaurant: Restaurant, when: datetime):
    """1-4 different dishes with quantities. Returns [(MenuItem, qty, unit_price)]."""
    line_count = pick([1, 2, 3, 4], [40, 35, 18, 7])
    menu = list(restaurant.menu)
    lines = []
    price_hike_date = cfg.START_DATE + timedelta(days=cfg.MENU_PRICE_HIKE_DAYS_AFTER_START)
    for _ in range(min(line_count, len(menu))):
        item = pick(menu, [m.pick_weight for m in menu])
        menu.remove(item)
        qty = pick([1, 2, 3], [80, 15, 5])
        unit_price = item.price
        if when.date() < price_hike_date:
            unit_price = money(item.price / Decimal(str(1 + cfg.MENU_PRICE_HIKE)))
        lines.append((item, qty, unit_price))
    return lines


def choose_restaurant(customer, restaurants_by_area, restaurants_by_city, day):
    """60% of the time the customer orders from their own neighbourhood."""
    nearby = [r for r in restaurants_by_area.get(customer.area.id, []) if r.is_open_on(day)]
    if nearby and rng.random() < 0.6:
        pool = nearby
    else:
        pool = [r for r in restaurants_by_city[customer.area.city.id] if r.is_open_on(day)]
    if not pool:
        return None
    return pick(pool, [r.popularity for r in pool])


def choose_partner(partners_by_city, city: City, day: date):
    working = [p for p in partners_by_city[city.id] if p.works_on(day)]
    return rng.choice(working) if working else None


def food_rating(restaurant: Restaurant) -> int:
    if restaurant.is_problem:                       # PLANTED: bad food
        return pick([1, 2, 3, 4, 5], [30, 32, 23, 10, 5])
    return pick([1, 2, 3, 4, 5], [3, 4, 13, 35, 45])


def delivery_rating(partner: Partner, total_minutes: float) -> int:
    if partner.is_slow:                             # PLANTED: slow riders get low ratings
        return pick([1, 2, 3, 4, 5], [25, 35, 25, 10, 5])
    if total_minutes > 55:
        return pick([1, 2, 3, 4, 5], [8, 15, 30, 30, 17])
    return pick([1, 2, 3, 4, 5], [2, 3, 10, 35, 50])


def review_text(food: int, delivery: int):
    if rng.random() >= cfg.REVIEW_TEXT_SHARE:
        return None
    if food <= 2:
        return rng.choice(ref.REVIEWS_BAD_FOOD)
    if delivery <= 2:
        return rng.choice(ref.REVIEWS_BAD_DELIVERY)
    if food >= 4 and delivery >= 4:
        return rng.choice(ref.REVIEWS_GOOD)
    return rng.choice(ref.REVIEWS_OK)


def build_orders(skeletons, restaurants, partners, coupons):
    """Walk through the orders in time order and fill in every detail.
    Going in time order lets us know whether this is a customer's FIRST order."""
    restaurants_by_area, restaurants_by_city, partners_by_city = {}, {}, {}
    for r in restaurants:
        restaurants_by_area.setdefault(r.area.id, []).append(r)
        restaurants_by_city.setdefault(r.area.city.id, []).append(r)
    for p in partners:
        partners_by_city.setdefault(p.city.id, []).append(p)

    cancel_reasons = [r[0] for r in ref.CANCELLATION_REASONS]
    fail_reasons = [r[0] for r in ref.FAILURE_REASONS]
    fail_picked_up = {r[0]: r[2] for r in ref.FAILURE_REASONS}

    orders, order_items, payments, ratings = [], [], [], []
    orders_so_far = {}            # customer id -> number of earlier orders
    order_item_id = 0

    for when, customer in skeletons:
        day, city = when.date(), customer.area.city
        restaurant = choose_restaurant(customer, restaurants_by_area, restaurants_by_city, day)
        if restaurant is None:
            continue
        order_id = len(orders) + 1
        is_first_order = orders_so_far.get(customer.id, 0) == 0
        orders_so_far[customer.id] = orders_so_far.get(customer.id, 0) + 1

        # --- Items and money -------------------------------------------------
        lines = choose_order_items(restaurant, when)
        item_total = sum((unit_price * qty for _, qty, unit_price in lines), Decimal("0.00"))
        coupon = choose_coupon(coupons, customer, is_first_order, when, item_total)
        discount = discount_for(coupon, item_total)

        same_area = restaurant.area.id == customer.area.id
        distance = money(rng.uniform(0.6, 4.5) if same_area else rng.uniform(3.0, 14.0))
        delivery_fee = delivery_fee_for(customer, distance)
        total = item_total + delivery_fee - discount

        # --- Payment method and outcome -------------------------------------
        method = pick(ref.PAYMENT_METHODS, ref.CITY_PAYMENT_WEIGHTS.get(city.name, ref.DEFAULT_PAYMENT_WEIGHTS))
        cancel_rate = cfg.PROBLEM_RESTAURANT_CANCEL_RATE if restaurant.is_problem else cfg.CANCEL_RATE
        if method == "COD":
            cancel_rate *= cfg.CANCEL_RATE_COD_FACTOR
        roll = rng.random()
        status = "Cancelled" if roll < cancel_rate else "Failed" if roll < cancel_rate + cfg.FAIL_RATE else "Delivered"

        reason, partner, pickup, delivered = None, None, None, None
        if status == "Cancelled":
            column = 2 if restaurant.is_problem else 1
            reason = pick(cancel_reasons, [r[column] for r in ref.CANCELLATION_REASONS])
            if reason != "Delivery partner not assigned" and rng.random() < 0.35:
                partner = choose_partner(partners_by_city, city, day)
        elif status == "Failed":
            reason = pick(fail_reasons, [r[1] for r in ref.FAILURE_REASONS])
            if reason == "Payment failed":
                method = pick(ref.PAYMENT_METHODS, ref.FAILED_PAYMENT_WEIGHTS)   # PLANTED
            if fail_picked_up[reason]:
                partner = choose_partner(partners_by_city, city, day)

        # --- Timeline: order -> pickup -> delivered --------------------------
        needs_pickup = status == "Delivered" or (status == "Failed" and fail_picked_up[reason])
        if status == "Delivered":
            partner = choose_partner(partners_by_city, city, day)
            if partner is None:          # no rider working that day -> order failed
                status, reason, needs_pickup = "Failed", "Delivery address not serviceable", False
        if needs_pickup and partner is not None:
            busy = 1.1 if (is_lunch_peak(when) or is_dinner_peak(when)) else 1.0
            prep = restaurant.prep_mins * rng.uniform(0.75, 1.35) * busy + rng.uniform(1, 6)
            pickup = when + timedelta(seconds=int(prep * 60))
            if status == "Delivered":
                # PLANTED: travel time grows with distance; slow riders, rain and traffic add more.
                travel = (3 + float(distance) * 2.8) * partner.speed_factor * busy * rng.uniform(0.85, 1.2)
                if city.name == cfg.MONSOON_CITY and day.month == cfg.MONSOON_MONTH:
                    travel *= cfg.MONSOON_TRAVEL_MULTIPLIER
                delivered = pickup + timedelta(seconds=int(travel * 60))

        orders.append((order_id, customer.id, restaurant.id, partner.id if partner else None,
                       coupon.id if coupon else None, when, status, reason, item_total, delivery_fee,
                       discount, total, distance, pickup, delivered))

        for item, qty, unit_price in lines:
            order_item_id += 1
            order_items.append((order_item_id, order_id, item.id, qty, unit_price))

        # --- Payment row (exactly one per order) -----------------------------
        paid_at = when + timedelta(seconds=rng.randint(5, 90))
        if status == "Delivered":
            pay_status, paid = "Success", total
            if method == "COD":
                paid_at = delivered         # cash is collected at the door
        elif reason == "Payment failed" or method == "COD":
            pay_status, paid = "Failed", money(0)   # no money was ever collected
        else:
            pay_status, paid = "Refunded", total    # prepaid, then returned
        payments.append((order_id, order_id, method, pay_status, paid, paid_at))

        # --- Rating (some delivered orders only) -----------------------------
        if status == "Delivered" and rng.random() < cfg.RATING_SHARE:
            rated_at = min(delivered + timedelta(minutes=rng.randint(10, 36 * 60)), RUN_STARTED_AT)
            if rated_at > delivered:
                food = food_rating(restaurant)
                delivery = delivery_rating(partner, (delivered - when).total_seconds() / 60)
                ratings.append((len(ratings) + 1, order_id, food, delivery, review_text(food, delivery), rated_at))

    return orders, order_items, payments, ratings


# =====================================================================
# Database
# =====================================================================

def get_admin_connection():
    """Admin connection for seeding only. The agent itself NEVER uses this -
    it connects with the read-only login."""
    parts = [
        f"DRIVER={{{os.getenv('DB_DRIVER', 'ODBC Driver 18 for SQL Server')}}}",
        f"SERVER={os.getenv('DB_SERVER', 'localhost')}",
        f"DATABASE={os.getenv('DB_NAME', 'FoodDeliveryDB')}",
        f"TrustServerCertificate={os.getenv('DB_TRUST_SERVER_CERTIFICATE', 'yes')}",
    ]
    if os.getenv("DB_ADMIN_TRUSTED_CONNECTION", "yes").lower() == "yes":
        parts.append("Trusted_Connection=yes")
    else:
        parts += [f"UID={os.getenv('DB_ADMIN_USER')}", f"PWD={os.getenv('DB_ADMIN_PASSWORD')}"]
    # autocommit=False -> everything below is one transaction.
    return pyodbc.connect(";".join(parts), autocommit=False)


# Insert order: parents before children (foreign keys).
TABLES = [
    ("Cities", ["CityID", "CityName", "State", "LaunchDate"], True),
    ("Areas", ["AreaID", "CityID", "AreaName", "Pincode"], True),
    ("Cuisines", ["CuisineID", "CuisineName"], True),
    ("Restaurants", ["RestaurantID", "AreaID", "RestaurantName", "PriceRange", "AvgPrepTimeMins",
                     "IsPureVeg", "OnboardedDate", "IsActive"], True),
    ("RestaurantCuisines", ["RestaurantID", "CuisineID"], False),
    ("MenuItems", ["MenuItemID", "RestaurantID", "ItemName", "Category", "Price", "IsVeg", "IsAvailable"], True),
    ("Customers", ["CustomerID", "FullName", "Email", "Phone", "AreaID", "SignupDate", "IsPremiumMember"], True),
    ("DeliveryPartners", ["PartnerID", "FullName", "CityID", "VehicleType", "JoinDate", "IsActive"], True),
    ("Coupons", ["CouponID", "CouponCode", "DiscountType", "DiscountValue", "MaxDiscount", "MinOrderValue",
                 "ValidFrom", "ValidTo", "IsNewUserOnly"], True),
    ("Orders", ["OrderID", "CustomerID", "RestaurantID", "PartnerID", "CouponID", "OrderDateTime", "Status",
                "CancellationReason", "ItemTotal", "DeliveryFee", "DiscountAmount", "TotalAmount",
                "DeliveryDistanceKm", "PickupDateTime", "DeliveredDateTime"], True),
    ("OrderItems", ["OrderItemID", "OrderID", "MenuItemID", "Quantity", "UnitPrice"], True),
    ("Payments", ["PaymentID", "OrderID", "PaymentMethod", "PaymentStatus", "PaidAmount", "PaymentDateTime"], True),
    ("Ratings", ["RatingID", "OrderID", "FoodRating", "DeliveryRating", "ReviewText", "RatedDateTime"], True),
]


def clear_tables(cursor):
    """Delete children before parents, otherwise foreign keys block the delete."""
    for table, _, _ in reversed(TABLES):
        cursor.execute(f"DELETE FROM dbo.{table};")
        print(f"   cleared {table}")


def insert_rows(cursor, table, columns, rows, has_identity):
    """Bulk insert with fast_executemany (sends many rows per round trip).

    We supply the IDs ourselves (IDENTITY_INSERT ON) so that the IDs are the
    same on every run and the Python code already knows them - no need to
    read generated IDs back from the database."""
    placeholders = ", ".join("?" for _ in columns)
    sql = f"INSERT INTO dbo.{table} ({', '.join(columns)}) VALUES ({placeholders})"
    if has_identity:
        cursor.execute(f"SET IDENTITY_INSERT dbo.{table} ON;")
    for start in range(0, len(rows), cfg.INSERT_BATCH_SIZE):
        cursor.executemany(sql, rows[start:start + cfg.INSERT_BATCH_SIZE])
    if has_identity:
        cursor.execute(f"SET IDENTITY_INSERT dbo.{table} OFF;")


# =====================================================================
# Main
# =====================================================================

def build_all_rows():
    """Generate every table's rows in memory. Returns {table name: [row tuples]}."""
    step = time.perf_counter()

    def done(label, count):
        nonlocal step
        print(f"   {label:<34}{count:>8,}  ({time.perf_counter() - step:.1f}s)")
        step = time.perf_counter()

    cities = build_cities()
    areas = [a for c in cities for a in c.areas]
    done("cities / areas", len(areas))
    restaurants = build_restaurants(cities)
    done("restaurants (with menus)", len(restaurants))
    customers = build_customers(cities)
    done("customers", len(customers))
    partners = build_partners(cities)
    done("delivery partners", len(partners))
    coupons = build_coupons()
    done("coupons", len(coupons))
    skeletons = build_order_skeletons(cities, customers)
    done("order timestamps + customers", len(skeletons))
    orders, order_items, payments, ratings = build_orders(skeletons, restaurants, partners, coupons)
    done("order details", len(orders))

    cuisine_id = {name: i for i, name in enumerate(ref.CUISINES, start=1)}
    rows = {
        "Cities": [(c.id, c.name, c.state, c.launch_date) for c in cities],
        "Areas": [(a.id, a.city.id, a.name, a.pincode) for a in areas],
        "Cuisines": [(i, name) for name, i in cuisine_id.items()],
        "Restaurants": [(r.id, r.area.id, r.name, r.price_range, r.prep_mins, r.is_pure_veg, r.onboarded, r.is_active)
                        for r in restaurants],
        "RestaurantCuisines": [(r.id, cuisine_id[c]) for r in restaurants for c in r.cuisines],
        "MenuItems": [(m.id, m.restaurant_id, m.name, m.category, m.price, m.is_veg, m.is_available)
                      for r in restaurants for m in r.menu],
        "Customers": [(c.id, c.name, c.email, c.phone, c.area.id, c.signup, c.is_premium) for c in customers],
        "DeliveryPartners": [(p.id, p.name, p.city.id, p.vehicle, p.join_date, p.left_date is None) for p in partners],
        "Coupons": [(c.id, c.code, c.discount_type, c.value, c.max_discount, c.min_order,
                     c.valid_from, c.valid_to, c.new_user_only) for c in coupons],
        "Orders": orders,
        "OrderItems": order_items,
        "Payments": payments,
        "Ratings": ratings,
    }
    return rows, cities, restaurants, partners, coupons


def print_planted_facts(cities, restaurants, partners, coupons):
    """The concrete dates/names behind the planted patterns for THIS run."""
    new_city = next(c for c in cities if c.name == cfg.NEW_CITY)
    diwali = first_date_in_range(cfg.DIWALI_DATES)
    mega = next(c for c in coupons if c.code == "MEGA60")
    monsoon = next(c for c in coupons if c.code == "MONSOON40")
    print("\nPlanted facts for this run (see PLANTED_INSIGHTS.md):")
    print(f"   Data range            : {cfg.START_DATE} to {cfg.END_DATE}")
    print(f"   New city              : {new_city.name}, launched {new_city.launch_date}")
    print(f"   Diwali month          : {diwali:%B %Y} (Diwali on {diwali})" if diwali else "   Diwali: not in range")
    print(f"   Mumbai monsoon dip    : {monsoon.valid_from:%B %Y}")
    print(f"   MEGA60 campaign       : {mega.valid_from} to {mega.valid_to}")
    print("   Problem restaurants   : " + ", ".join(f"{r.name} (ID {r.id}, {r.area.city.name})"
                                                   for r in restaurants if r.is_problem))
    slow = [p for p in partners if p.is_slow]
    print(f"   Slow delivery partners: {len(slow)} riders, e.g. IDs " + ", ".join(str(p.id) for p in slow[:8]))


def main():
    started = time.perf_counter()
    print(f"Generating data (seed={cfg.RANDOM_SEED}, {cfg.START_DATE} to {cfg.END_DATE})...")
    rows, cities, restaurants, partners, coupons = build_all_rows()

    print("\nConnecting to SQL Server (admin connection)...")
    conn = get_admin_connection()
    cursor = conn.cursor()
    cursor.fast_executemany = True
    try:
        print("Clearing existing data...")
        clear_tables(cursor)
        print("Inserting...")
        for table, columns, has_identity in TABLES:
            t = time.perf_counter()
            insert_rows(cursor, table, columns, rows[table], has_identity)
            print(f"   {table:<20}{len(rows[table]):>8,} rows  ({time.perf_counter() - t:.1f}s)")
        conn.commit()
    except Exception:
        conn.rollback()   # leave the database exactly as it was
        print("\nSomething went wrong - all changes were rolled back.")
        raise

    print("\nFinal row counts in the database:")
    for table, _, _ in TABLES:
        count = cursor.execute(f"SELECT COUNT(*) FROM dbo.{table};").fetchone()[0]
        print(f"   {table:<20}{count:>8,}")
    conn.close()

    print_planted_facts(cities, restaurants, partners, coupons)
    print(f"\nDone in {time.perf_counter() - started:.0f}s.")


if __name__ == "__main__":
    main()
