"""
Curated demo questions, tagged by persona and SQL concept.

Each question targets a pattern planted in the data (see
data_generator/PLANTED_INSIGHTS.md), so the answers are interesting and
predictable. `insight` tells the presenter what to point out.

scripts/run_demo_questions.py (Phase 5) runs all of them before the demo.
"""

CITY_MANAGER = "City Manager"
OPERATIONS = "Operations"
MARKETING = "Marketing"
PARTNERSHIPS = "Restaurant Partnerships"

PERSONAS = [CITY_MANAGER, OPERATIONS, MARKETING, PARTNERSHIPS]
CONCEPTS = ["GROUP BY", "JOINs", "LEFT JOIN / NOT EXISTS", "HAVING",
            "Window functions", "CTEs", "Date functions", "Self-join"]

EXAMPLES = [
    # --- City Manager -------------------------------------------------
    {"question": "Total orders and delivered revenue by city",
     "persona": CITY_MANAGER, "concepts": ["GROUP BY", "JOINs"],
     "insight": "Bengaluru and Mumbai lead; Ahmedabad (newest city) is smallest. Hyderabad's revenue is high for its order count (biryani)."},
    {"question": "Show Ahmedabad's monthly orders with month-over-month growth percentage",
     "persona": CITY_MANAGER, "concepts": ["Window functions", "CTEs", "Date functions"],
     "insight": "Launched in January; grows ~15-25% every month (LAG compares each month with the previous one)."},
    {"question": "Compare average daily orders on weekends vs weekdays",
     "persona": CITY_MANAGER, "concepts": ["Date functions", "CTEs"],
     "insight": "Weekends are ~35% busier than weekdays."},
    {"question": "Show Mumbai's total orders per month",
     "persona": CITY_MANAGER, "concepts": ["Date functions", "GROUP BY"],
     "insight": "Clear dip in July (monsoon) and a peak in the Diwali month (October)."},
    {"question": "Running total of delivered revenue by month for Bengaluru",
     "persona": CITY_MANAGER, "concepts": ["Window functions", "Date functions"],
     "insight": "SUM(...) OVER (ORDER BY month) builds a cumulative revenue curve."},

    # --- Operations ---------------------------------------------------
    {"question": "How many orders do we get in each hour of the day?",
     "persona": OPERATIONS, "concepts": ["Date functions", "GROUP BY"],
     "insight": "Lunch spike 12-14h, bigger dinner spike 20-21h, almost nothing 2-6h."},
    {"question": "Which 10 delivery partners have the highest average delivery time (minimum 20 deliveries), with their average delivery rating?",
     "persona": OPERATIONS, "concepts": ["HAVING", "JOINs"],
     "insight": "A group of consistently slow riders: 60+ minutes and ~2.3 stars vs ~41 minutes / ~4.1 stars normally."},
    {"question": "Average delivery time by distance band: 0-3 km, 3-6 km, 6-9 km and 9+ km",
     "persona": OPERATIONS, "concepts": ["GROUP BY", "Date functions"],
     "insight": "Delivery time rises steadily with distance."},
    {"question": "What are the top cancellation reasons for cancelled orders?",
     "persona": OPERATIONS, "concepts": ["GROUP BY"],
     "insight": "'Customer changed mind' and 'Restaurant took too long' lead."},
    {"question": "Which delivery partners have not delivered any order in the last 30 days, and are they still marked as active?",
     "persona": OPERATIONS, "concepts": ["LEFT JOIN / NOT EXISTS", "Date functions"],
     "insight": "~44 idle riders, all already marked inactive - a nice data-quality check (no active rider is idle)."},
    {"question": "What share of payments uses each payment method, and how many payments failed per method?",
     "persona": OPERATIONS, "concepts": ["GROUP BY", "Window functions"],
     "insight": "UPI ~55%; failed payments are mostly Card and NetBanking."},

    # --- Marketing ----------------------------------------------------
    {"question": "For each coupon, how many times was it used and what percentage of uses were on the customer's first order?",
     "persona": MARKETING, "concepts": ["Window functions", "CTEs", "LEFT JOIN / NOT EXISTS"],
     "insight": "WELCOME50 and FIRSTBITE are 100% first orders (ROW_NUMBER numbers each customer's orders)."},
    {"question": "For customers whose first order used a coupon, what percentage ordered again, by coupon?",
     "persona": MARKETING, "concepts": ["CTEs", "Window functions"],
     "insight": "MEGA60 brought one-time deal hunters: only ~33% repeat vs ~95% for other coupons."},
    {"question": "Which coupons have never been used?",
     "persona": MARKETING, "concepts": ["LEFT JOIN / NOT EXISTS"],
     "insight": "SUMMER25 - it expired before the data starts."},
    {"question": "How many customers have not ordered in the last 60 days, by city?",
     "persona": MARKETING, "concepts": ["CTEs", "Date functions", "JOINs"],
     "insight": "About 20% of customers who ever ordered have churned."},
    {"question": "Compare average orders per customer for premium vs regular members",
     "persona": MARKETING, "concepts": ["GROUP BY", "CTEs"],
     "insight": "Premium members order ~2.5x as often (~27 vs ~11 orders)."},
    {"question": "What percentage of payments are cash on delivery in each city?",
     "persona": MARKETING, "concepts": ["GROUP BY", "JOINs"],
     "insight": "COD is far higher in Kolkata (~29%) and Ahmedabad (~25%) than elsewhere (~12%)."},

    # --- Restaurant Partnerships ---------------------------------------
    {"question": "Which restaurants have the highest cancellation rate (minimum 100 orders), and what is their average food rating?",
     "persona": PARTNERSHIPS, "concepts": ["HAVING", "JOINs", "CTEs"],
     "insight": "Six problem restaurants: 20-26% cancellations AND ~2.2 star food ratings."},
    {"question": "Top 3 restaurants by delivered revenue in each city",
     "persona": PARTNERSHIPS, "concepts": ["Window functions", "CTEs", "JOINs"],
     "insight": "ROW_NUMBER() OVER (PARTITION BY city ...) picks the top 3 per city."},
    {"question": "What is the most popular cuisine in each city by number of orders?",
     "persona": PARTNERSHIPS, "concepts": ["Window functions", "CTEs", "JOINs"],
     "insight": "Local favourites: Biryani in Hyderabad, Bengali in Kolkata, Gujarati in Ahmedabad."},
    {"question": "Find restaurants with the same name in different cities (chain outlets)",
     "persona": PARTNERSHIPS, "concepts": ["Self-join", "JOINs"],
     "insight": "Joining Restaurants to itself finds chains like Biryani Junction and Dosa Express."},
    {"question": "Which pure-veg restaurants have an average food rating above 4.3 with at least 50 ratings?",
     "persona": PARTNERSHIPS, "concepts": ["HAVING", "JOINs"],
     "insight": "Highlights the best-rated vegetarian partners."},
]


def _group(key_values: list[str], belongs) -> list[dict]:
    return [{"group": key, "questions": [e for e in EXAMPLES if belongs(e, key)]} for key in key_values]


def get_examples() -> dict:
    """Same questions, grouped two ways (the UI can show either tab)."""
    return {
        "by_persona": _group(PERSONAS, lambda e, key: e["persona"] == key),
        "by_concept": _group(CONCEPTS, lambda e, key: key in e["concepts"]),
    }
