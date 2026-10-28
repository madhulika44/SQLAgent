"""
Settings for the sample-data generator: volumes, date range and the
"knobs" that control each planted pattern.

Everything you might want to tweak lives here, so seed_data.py only
contains logic. Change a number, re-run the seed, and the data changes
accordingly (but always reproducibly, thanks to RANDOM_SEED).
"""

from datetime import date, timedelta

# ---------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------
# Same seed + same run date  ->  exactly the same data, row for row.
RANDOM_SEED = 42

# ---------------------------------------------------------------------
# Date range
# ---------------------------------------------------------------------
# Data ends YESTERDAY so every day in the data set is a complete day
# (no half-filled "today"), and re-running on the same day gives
# identical data.
END_DATE = date.today() - timedelta(days=1)

# Start on the 1st of the month, 12 months back. That gives 12 full
# months plus the current month-to-date, so "month over month" questions
# compare whole months.
START_DATE = date(END_DATE.year - 1, END_DATE.month, 1)

# ---------------------------------------------------------------------
# Volumes (approximate targets)
# ---------------------------------------------------------------------
TARGET_ORDERS = 80_000
NUM_CUSTOMERS = 6_000
NUM_DELIVERY_PARTNERS = 700
NUM_RESTAURANTS = 300
MENU_ITEMS_PER_RESTAURANT = 12

# How many rows to send to SQL Server per round trip.
INSERT_BATCH_SIZE = 5_000

# ---------------------------------------------------------------------
# City mix: relative share of orders (and of restaurants/customers/riders).
# Bengaluru and Mumbai are the biggest markets.
# ---------------------------------------------------------------------
CITY_ORDER_WEIGHTS = {
    "Bengaluru": 0.22,
    "Mumbai": 0.20,
    "Delhi": 0.16,
    "Hyderabad": 0.13,
    "Chennai": 0.10,
    "Pune": 0.09,
    "Kolkata": 0.07,
    "Ahmedabad": 0.07,   # the weight it grows TOWARDS after launch (see below)
}

# ---------------------------------------------------------------------
# Planted pattern: new city with strong month-over-month growth
# ---------------------------------------------------------------------
NEW_CITY = "Ahmedabad"
NEW_CITY_LAUNCH_MONTHS_AFTER_START = 3   # launches 3 months into the data range
NEW_CITY_START_LEVEL = 0.15              # month 0 runs at 15% of its full weight...
NEW_CITY_MONTHLY_GROWTH = 1.22           # ...and grows ~22% every month after
NEW_CITY_CUSTOMER_SHARE = 0.03           # it has fewer customers than older cities

# ---------------------------------------------------------------------
# Planted pattern: weekly and seasonal demand
# ---------------------------------------------------------------------
WEEKEND_MULTIPLIER = 1.35        # Saturday/Sunday vs a weekday

# Relative order volume for each 30-minute slot of the day (48 slots).
# Lunch spike 12:00-14:30, bigger dinner spike 19:30-22:30, dead 02:00-07:00.
HALF_HOUR_WEIGHTS = [
    2.0, 1.5,    # 00:00, 00:30
    1.0, 0.6,    # 01
    0.2, 0.15,   # 02
    0.1, 0.1,    # 03
    0.1, 0.1,    # 04
    0.1, 0.15,   # 05
    0.2, 0.3,    # 06
    0.6, 0.9,    # 07
    1.5, 1.9,    # 08  (breakfast)
    2.0, 1.8,    # 09
    1.6, 1.8,    # 10
    2.6, 4.0,    # 11
    8.0, 9.0,    # 12  <- lunch
    9.0, 8.5,    # 13
    7.0, 4.0,    # 14  (lunch ends 14:30)
    2.6, 2.3,    # 15
    2.3, 2.6,    # 16
    3.0, 3.5,    # 17
    4.0, 4.6,    # 18
    6.0, 10.5,   # 19  <- dinner starts 19:30
    12.5, 13.5,  # 20
    13.0, 12.0,  # 21
    10.0, 6.0,   # 22  (dinner ends 22:30)
    4.0, 3.0,    # 23
]
MONTHLY_GROWTH_TREND = 0.015     # whole platform grows ~1.5% per month

# Diwali dates. The month that contains Diwali gets a festive boost, with
# the biggest spike in the days leading up to it.
DIWALI_DATES = [date(2024, 11, 1), date(2025, 10, 21), date(2026, 11, 8),
                date(2027, 10, 29), date(2028, 10, 17)]
FESTIVE_MONTH_MULTIPLIER = 1.15  # whole Diwali month
FESTIVE_PEAK_MULTIPLIER = 1.45   # Diwali-12 days .. Diwali+1 day
FESTIVE_PEAK_DAYS_BEFORE = 12

# Mumbai monsoon: July orders drop and deliveries are slower.
MONSOON_CITY = "Mumbai"
MONSOON_MONTH = 7
MONSOON_ORDER_MULTIPLIER = 0.62
MONSOON_TRAVEL_MULTIPLIER = 1.25

# ---------------------------------------------------------------------
# Planted pattern: order outcome mix
# ---------------------------------------------------------------------
CANCEL_RATE = 0.068              # normal restaurants
CANCEL_RATE_COD_FACTOR = 0.30    # COD orders get cancelled less often
FAIL_RATE = 0.02
PROBLEM_RESTAURANT_COUNT = 6     # high cancellations + low food ratings
PROBLEM_RESTAURANT_CANCEL_RATE = 0.26

# ---------------------------------------------------------------------
# Planted pattern: delivery partners
# ---------------------------------------------------------------------
SLOW_PARTNER_SHARE = 0.05        # ~5% of riders are consistently slow
SLOW_PARTNER_SPEED_FACTOR = 2.3  # their travel takes ~2.3x longer
INACTIVE_PARTNER_SHARE = 0.08

# ---------------------------------------------------------------------
# Planted pattern: customers
# ---------------------------------------------------------------------
PREMIUM_SHARE = 0.15
PREMIUM_ORDER_MULTIPLIER = 2.3   # premium members order ~2.3x as often
CHURN_SHARE = 0.04               # customers who stop ordering (plus deal hunters + natural inactivity -> ~20%)
CHURN_INACTIVE_DAYS = 60         # "churned" = no order in the last 60 days
DEAL_HUNTER_SHARE = 0.08         # sign up for MEGA60, then disappear
DEAL_HUNTER_ORDER_COUNTS = {1: 70, 2: 20, 3: 10}   # how many orders a deal hunter places (weights)
DEAL_HUNTER_ACTIVE_DAYS = 14     # ...all within this many days of signing up

# ---------------------------------------------------------------------
# Coupons
# ---------------------------------------------------------------------
FIRST_ORDER_WELCOME_RATE = 0.65  # first orders that use a WELCOME-type coupon
COUPON_USE_RATE = 0.20           # other orders that use a coupon
COUPON_USE_RATE_PREMIUM = 0.28
DEAL_HUNTER_MEGA_RATE = 0.85
MEGA_CAMPAIGN_START_DAY = 120    # MEGA60 runs from START_DATE + 120 days...
MEGA_CAMPAIGN_LENGTH_DAYS = 90   # ...for 90 days

# ---------------------------------------------------------------------
# Menu prices: restaurants raised prices ~5% partway through the year,
# so older OrderItems.UnitPrice values are lower than MenuItems.Price.
# ---------------------------------------------------------------------
MENU_PRICE_HIKE_DAYS_AFTER_START = 180
MENU_PRICE_HIKE = 0.05

# ---------------------------------------------------------------------
# Ratings
# ---------------------------------------------------------------------
RATING_SHARE = 0.60              # share of delivered orders that get rated
REVIEW_TEXT_SHARE = 0.35         # share of ratings that include written text
