"""
Static reference data for the generator: real cities and areas, cuisines,
dishes with realistic prices, name parts, reasons and review texts.

Kept separate from seed_data.py so the generation logic stays short and
readable. Everything here is plain Python lists/dicts - no randomness.
"""

from datetime import date

# ---------------------------------------------------------------------
# Cities and their real localities (AreaName, 6-digit PIN code).
# LaunchDate = None means "computed at run time" (the new city).
# ---------------------------------------------------------------------
CITIES = [
    # (CityName, State, LaunchDate, [(AreaName, Pincode), ...])
    ("Bengaluru", "Karnataka", date(2015, 3, 1), [
        ("Koramangala", "560034"), ("Indiranagar", "560038"), ("Whitefield", "560066"),
        ("HSR Layout", "560102"), ("Jayanagar", "560041"), ("Electronic City", "560100")]),
    ("Mumbai", "Maharashtra", date(2015, 6, 1), [
        ("Andheri West", "400053"), ("Bandra West", "400050"), ("Powai", "400076"),
        ("Lower Parel", "400013"), ("Colaba", "400005"), ("Malad West", "400064")]),
    ("Delhi", "Delhi", date(2015, 9, 1), [
        ("Connaught Place", "110001"), ("Hauz Khas", "110016"), ("Lajpat Nagar", "110024"),
        ("Rajouri Garden", "110027"), ("Dwarka", "110075"), ("Saket", "110017")]),
    ("Hyderabad", "Telangana", date(2016, 2, 1), [
        ("Banjara Hills", "500034"), ("Jubilee Hills", "500033"), ("Gachibowli", "500032"),
        ("Madhapur", "500081"), ("Kondapur", "500084"), ("Begumpet", "500016")]),
    ("Chennai", "Tamil Nadu", date(2016, 8, 1), [
        ("T. Nagar", "600017"), ("Adyar", "600020"), ("Anna Nagar", "600040"),
        ("Velachery", "600042"), ("Mylapore", "600004"), ("Sholinganallur", "600119")]),
    ("Pune", "Maharashtra", date(2017, 1, 15), [
        ("Koregaon Park", "411001"), ("Kothrud", "411038"), ("Viman Nagar", "411014"),
        ("Hinjewadi", "411057"), ("Baner", "411045"), ("Aundh", "411007")]),
    ("Kolkata", "West Bengal", date(2017, 7, 1), [
        ("Park Street", "700016"), ("Salt Lake", "700091"), ("New Town", "700156"),
        ("Ballygunge", "700019"), ("Gariahat", "700029"), ("Behala", "700034")]),
    ("Ahmedabad", "Gujarat", None, [
        ("Navrangpura", "380009"), ("Satellite", "380015"), ("Bodakdev", "380054"),
        ("Vastrapur", "380015"), ("Maninagar", "380008"), ("Prahlad Nagar", "380015")]),
]

# ---------------------------------------------------------------------
# Cuisines. Order matters: CuisineID = position + 1.
# ---------------------------------------------------------------------
CUISINES = [
    "North Indian", "South Indian", "Chinese", "Biryani", "Mughlai",
    "Street Food", "Pizza", "Burgers", "Desserts", "Cafe",
    "Bengali", "Gujarati", "Maharashtrian", "Kerala", "Healthy Food",
]

# Cuisines a pure-veg restaurant can have.
VEG_FRIENDLY_CUISINES = ["North Indian", "South Indian", "Street Food", "Pizza",
                         "Desserts", "Cafe", "Gujarati", "Healthy Food", "Chinese"]

# Cuisines that are always pure veg when they are a restaurant's main cuisine.
ALWAYS_VEG_CUISINES = ["Gujarati"]

# Local favourites: these cuisines are much more common in these cities.
CITY_CUISINE_BOOST = {
    "Bengaluru": {"South Indian": 3, "Cafe": 2, "Healthy Food": 2},
    "Mumbai": {"Street Food": 3, "Maharashtrian": 3},
    "Delhi": {"North Indian": 3, "Mughlai": 3, "Street Food": 2},
    "Hyderabad": {"Biryani": 5, "Mughlai": 2},
    "Chennai": {"South Indian": 4, "Kerala": 2},
    "Pune": {"Maharashtrian": 3, "Cafe": 2},
    "Kolkata": {"Bengali": 5, "Chinese": 2},
    "Ahmedabad": {"Gujarati": 5, "Street Food": 2},
}

# Cuisines that only appear where they are local.
LOCAL_ONLY_CUISINES = {
    "Bengali": ["Kolkata"],
    "Gujarati": ["Ahmedabad", "Mumbai", "Pune"],
    "Maharashtrian": ["Mumbai", "Pune"],
    "Kerala": ["Chennai", "Bengaluru"],
}

# ---------------------------------------------------------------------
# Dishes per cuisine: (ItemName, Category, IsVeg, base price INR, popularity)
# Base price = a Mid-range restaurant; Budget/Premium scale it.
# Popularity = how likely the dish is to be picked in an order.
# ---------------------------------------------------------------------
S, M, D, B, C = "Starter", "Main Course", "Dessert", "Beverage", "Combo"

DISHES = {
    "North Indian": [
        ("Paneer Butter Masala", M, True, 260, 4), ("Dal Makhani", M, True, 220, 3),
        ("Butter Chicken", M, False, 320, 5), ("Chicken Tikka", S, False, 290, 3),
        ("Paneer Tikka", S, True, 250, 3), ("Chole Bhature", M, True, 180, 3),
        ("Butter Naan", M, True, 50, 4), ("Kadai Paneer", M, True, 250, 2),
        ("Rajma Chawal", M, True, 170, 2), ("Tandoori Roti", M, True, 25, 3),
        ("Veg Thali", C, True, 249, 2), ("Chicken Thali", C, False, 329, 2),
        ("Gulab Jamun (2 pcs)", D, True, 80, 2), ("Sweet Lassi", B, True, 90, 2),
    ],
    "South Indian": [
        ("Masala Dosa", M, True, 120, 5), ("Idli Vada", M, True, 90, 4),
        ("Plain Dosa", M, True, 90, 2), ("Rava Dosa", M, True, 130, 2),
        ("Onion Uttapam", M, True, 130, 2), ("Medu Vada", S, True, 70, 3),
        ("Ven Pongal", M, True, 110, 2), ("Filter Coffee", B, True, 50, 4),
        ("Mini Tiffin Combo", C, True, 180, 3), ("Kesari Bath", D, True, 70, 2),
        ("Mysore Masala Dosa", M, True, 140, 3), ("Curd Rice", M, True, 120, 2),
        ("Chicken Chettinad", M, False, 290, 2),
    ],
    "Chinese": [
        ("Veg Hakka Noodles", M, True, 180, 4), ("Chicken Hakka Noodles", M, False, 210, 4),
        ("Veg Manchurian", S, True, 190, 3), ("Chilli Chicken", S, False, 240, 4),
        ("Chicken Fried Rice", M, False, 210, 3), ("Veg Fried Rice", M, True, 180, 3),
        ("Schezwan Noodles", M, True, 190, 2), ("Chilli Paneer", S, True, 230, 3),
        ("Veg Spring Rolls", S, True, 160, 2), ("Hot and Sour Soup", S, True, 120, 2),
        ("Chicken Manchow Soup", S, False, 140, 2), ("Honey Chilli Potato", S, True, 170, 3),
        ("Darsaan with Ice Cream", D, True, 140, 1),
    ],
    "Biryani": [
        ("Chicken Dum Biryani", M, False, 280, 8), ("Mutton Biryani", M, False, 380, 4),
        ("Veg Biryani", M, True, 220, 2), ("Egg Biryani", M, False, 220, 2),
        ("Paneer Biryani", M, True, 240, 2), ("Chicken 65", S, False, 230, 4),
        ("Mirchi Ka Salan", M, True, 90, 1), ("Double Ka Meetha", D, True, 110, 2),
        ("Biryani Family Pack", C, False, 799, 2), ("Chicken Biryani Combo", C, False, 349, 3),
        ("Apollo Fish", S, False, 290, 2), ("Phirni", D, True, 100, 1),
    ],
    "Mughlai": [
        ("Mutton Rogan Josh", M, False, 380, 3), ("Chicken Changezi", M, False, 340, 2),
        ("Mutton Seekh Kebab", S, False, 320, 3), ("Galouti Kebab", S, False, 350, 3),
        ("Chicken Korma", M, False, 320, 2), ("Shahi Paneer", M, True, 260, 3),
        ("Rumali Roti", M, True, 35, 3), ("Sheermal", M, True, 60, 1),
        ("Shahi Tukda", D, True, 140, 2), ("Firni", D, True, 110, 1),
        ("Mughlai Paratha", M, False, 180, 2), ("Nihari with Khamiri Roti", C, False, 420, 2),
    ],
    "Street Food": [
        ("Pav Bhaji", M, True, 140, 5), ("Vada Pav", S, True, 40, 4),
        ("Pani Puri", S, True, 60, 3), ("Samosa Chaat", S, True, 80, 3),
        ("Dahi Puri", S, True, 80, 2), ("Aloo Tikki Chaat", S, True, 90, 2),
        ("Chole Kulche", M, True, 120, 2), ("Masala Chai", B, True, 30, 3),
        ("Bhel Puri", S, True, 70, 2), ("Egg Roll", M, False, 110, 2),
        ("Chicken Kathi Roll", M, False, 150, 3), ("Paneer Kathi Roll", M, True, 140, 3),
    ],
    "Pizza": [
        ("Margherita Pizza", M, True, 249, 5), ("Farmhouse Pizza", M, True, 399, 3),
        ("Pepperoni Pizza", M, False, 449, 3), ("Chicken Tikka Pizza", M, False, 429, 3),
        ("Paneer Makhani Pizza", M, True, 399, 3), ("Garlic Breadsticks", S, True, 129, 3),
        ("Cheesy Garlic Bread", S, True, 159, 2), ("Pasta Alfredo", M, True, 279, 2),
        ("Pasta Arrabbiata", M, True, 259, 2), ("Choco Lava Cake", D, True, 109, 3),
        ("Pizza and Soft Drink Combo", C, True, 349, 2), ("Cold Coffee", B, True, 140, 1),
    ],
    "Burgers": [
        ("Classic Veg Burger", M, True, 129, 3), ("Aloo Tikki Burger", M, True, 79, 4),
        ("Crispy Chicken Burger", M, False, 179, 5), ("Double Chicken Burger", M, False, 249, 2),
        ("Paneer Burger", M, True, 159, 2), ("French Fries", S, True, 99, 4),
        ("Peri Peri Fries", S, True, 119, 3), ("Chicken Nuggets", S, False, 149, 3),
        ("Burger Meal Combo", C, False, 299, 3), ("Chocolate Shake", B, True, 149, 2),
        ("Oreo Shake", B, True, 159, 2),
    ],
    "Desserts": [
        ("Gulab Jamun (2 pcs)", D, True, 80, 3), ("Rasmalai", D, True, 120, 3),
        ("Chocolate Brownie", D, True, 120, 3), ("Death by Chocolate", D, True, 220, 2),
        ("Malai Kulfi", D, True, 90, 2), ("Gajar Ka Halwa", D, True, 130, 2),
        ("Jalebi with Rabri", D, True, 120, 2), ("Red Velvet Pastry", D, True, 140, 2),
        ("Ice Cream Sundae", D, True, 180, 2), ("Rabri Falooda", B, True, 160, 2),
        ("Dessert Sampler Box", C, True, 399, 1),
    ],
    "Cafe": [
        ("Cappuccino", B, True, 150, 3), ("Cold Coffee", B, True, 160, 4),
        ("Masala Chai", B, True, 50, 2), ("Iced Tea", B, True, 140, 2),
        ("Veg Club Sandwich", M, True, 180, 3), ("Chicken Club Sandwich", M, False, 220, 3),
        ("Grilled Cheese Sandwich", M, True, 160, 2), ("Blueberry Muffin", D, True, 120, 2),
        ("Butter Croissant", S, True, 130, 2), ("Chicken Wrap", M, False, 210, 2),
        ("Nachos with Salsa", S, True, 190, 2), ("Coffee and Sandwich Combo", C, True, 279, 2),
    ],
    "Bengali": [
        ("Kosha Mangsho", M, False, 360, 4), ("Shorshe Ilish", M, False, 450, 3),
        ("Chingri Malai Curry", M, False, 420, 3), ("Luchi Alur Dom", M, True, 140, 3),
        ("Mochar Ghonto", M, True, 170, 1), ("Fish Fry", S, False, 180, 3),
        ("Kolkata Chicken Biryani", M, False, 290, 4), ("Mishti Doi", D, True, 70, 3),
        ("Rosogolla (2 pcs)", D, True, 60, 2), ("Sandesh", D, True, 70, 1),
        ("Begun Bhaja", S, True, 80, 1), ("Bengali Fish Thali", C, False, 349, 2),
    ],
    "Gujarati": [
        ("Gujarati Thali", C, True, 299, 5), ("Khaman Dhokla", S, True, 80, 4),
        ("Khandvi", S, True, 90, 2), ("Undhiyu", M, True, 220, 2),
        ("Sev Tameta", M, True, 150, 2), ("Methi Thepla", M, True, 90, 3),
        ("Fafda Jalebi", S, True, 100, 3), ("Dal Dhokli", M, True, 160, 2),
        ("Khichdi Kadhi", M, True, 170, 2), ("Shrikhand", D, True, 110, 2),
        ("Basundi", D, True, 120, 1), ("Masala Chaas", B, True, 40, 3),
    ],
    "Maharashtrian": [
        ("Misal Pav", M, True, 110, 5), ("Vada Pav", S, True, 35, 4),
        ("Kanda Poha", M, True, 60, 3), ("Sabudana Khichdi", M, True, 90, 2),
        ("Kolhapuri Chicken", M, False, 300, 3), ("Chicken Sukka", M, False, 290, 2),
        ("Bharli Vangi", M, True, 170, 1), ("Thalipeeth", M, True, 100, 2),
        ("Puran Poli", D, True, 90, 2), ("Ukadiche Modak", D, True, 120, 2),
        ("Kokum Sharbat", B, True, 60, 2), ("Maharashtrian Veg Thali", C, True, 249, 2),
        ("Malvani Fish Thali", C, False, 399, 2),
    ],
    "Kerala": [
        ("Appam with Veg Stew", M, True, 170, 3), ("Kerala Parotta", M, True, 40, 4),
        ("Kerala Chicken Curry", M, False, 280, 4), ("Mutton Pepper Fry", M, False, 330, 2),
        ("Malabar Fish Curry", M, False, 320, 3), ("Karimeen Pollichathu", M, False, 420, 1),
        ("Puttu Kadala", M, True, 130, 2), ("Avial", M, True, 150, 1),
        ("Kerala Sadya", C, True, 299, 2), ("Banana Chips", S, True, 70, 1),
        ("Palada Payasam", D, True, 110, 2), ("Thalassery Chicken Biryani", M, False, 290, 4),
    ],
    "Healthy Food": [
        ("Quinoa Salad", M, True, 260, 2), ("Grilled Chicken Salad", M, False, 299, 3),
        ("Paneer Protein Bowl", M, True, 279, 3), ("Chicken Protein Bowl", M, False, 319, 3),
        ("Avocado Toast", S, True, 249, 2), ("Greek Yogurt Parfait", D, True, 199, 2),
        ("Detox Green Juice", B, True, 169, 2), ("Fresh Fruit Bowl", D, True, 149, 2),
        ("Millet Khichdi", M, True, 199, 2), ("Sprouts Chaat", S, True, 129, 2),
        ("Oats Banana Smoothie", B, True, 179, 2), ("Egg White Omelette", M, False, 179, 2),
    ],
}

# Generic extras any restaurant may add so most menus have a drink/dessert.
EXTRA_BEVERAGES = [("Fresh Lime Soda", B, True, 90, 2), ("Soft Drink (300 ml)", B, True, 60, 3),
                   ("Masala Chaas", B, True, 50, 2), ("Mineral Water (1 L)", B, True, 30, 1)]
EXTRA_DESSERTS = [("Gulab Jamun (2 pcs)", D, True, 80, 2), ("Vanilla Ice Cream", D, True, 90, 1)]

# Price multipliers by restaurant segment.
PRICE_RANGE_MULTIPLIER = {"Budget": 0.75, "Mid": 1.0, "Premium": 1.6}
PRICE_RANGE_WEIGHTS = {"Budget": 40, "Mid": 45, "Premium": 15}

# ---------------------------------------------------------------------
# Restaurant names = prefix + cuisine-specific suffix (all fictional).
# ---------------------------------------------------------------------
NAME_PREFIXES = [
    "Spice", "Saffron", "Zaika", "Swaad", "Masala", "Royal", "Urban", "Desi",
    "Namma", "Apna", "Golden", "Green Leaf", "Annapoorna", "Shree", "Sagar",
    "Moti", "Chowpatty", "Rasika", "Aangan", "Nawab", "Tadka", "Jhakaas",
    "Coastal", "Heritage", "Mehfil", "Rang", "Utsav", "Kesar", "Sitara", "Tulsi",
    "Bombay", "Madras", "Calcutta", "Lucknowi", "Amritsari", "Mysore", "Malabar",
    "Sharma's", "Reddy's", "Iyer's", "Patel's", "Ghosh's", "Kulkarni's", "Khan's",
]

NAME_SUFFIXES = {
    "North Indian": ["Dhaba", "Rasoi", "Tandoor House", "Punjabi Kitchen", "Da Dhaba"],
    "South Indian": ["Tiffins", "Dosa Corner", "Bhavan", "Idli House", "Udupi Kitchen"],
    "Chinese": ["Wok", "Dragon", "Chopsticks", "Noodle Bar", "Chinese Corner"],
    "Biryani": ["Biryani House", "Biryani Point", "Dum Pukht", "Biryani Darbar"],
    "Mughlai": ["Darbar", "Kebab Corner", "Mughlai Kitchen", "Nawabi Rasoi"],
    "Street Food": ["Chaat Bhandar", "Street Bites", "Pav Bhaji Centre", "Rolls Junction"],
    "Pizza": ["Pizzeria", "Pizza Co.", "Slice House", "Oven Story Kitchen"],
    "Burgers": ["Burger Shack", "Grill House", "Burger Lab", "Patty Point"],
    "Desserts": ["Sweets", "Mithai Mahal", "Dessert Bar", "Sweet Tooth"],
    "Cafe": ["Cafe", "Coffee House", "Brew Room", "Bistro"],
    "Bengali": ["Bhojohori", "Bangali Rannaghar", "Pice Hotel", "Ranna Bati"],
    "Gujarati": ["Thali House", "Bhojanalay", "Farsan Mart", "Rasthal"],
    "Maharashtrian": ["Misal House", "Khanaval", "Malvani Kitchen", "Upahar Griha"],
    "Kerala": ["Kerala Kitchen", "Malabar Cafe", "Thattukada", "Sadya House"],
    "Healthy Food": ["Salad Co.", "Fit Bowl", "Green Kitchen", "Protein Bar"],
}

# Fictional chains with outlets in several cities: (name, main cuisine, number of outlets)
CHAINS = [
    ("Biryani Junction", "Biryani", 6),
    ("Dosa Express", "South Indian", 5),
    ("Pizza Planet", "Pizza", 5),
    ("Burger Barn", "Burgers", 4),
    ("Wok This Way", "Chinese", 4),
    ("Chai & Co", "Cafe", 4),
]

# ---------------------------------------------------------------------
# Order outcomes
# ---------------------------------------------------------------------
# (reason, weight for normal restaurants, weight for problem restaurants)
CANCELLATION_REASONS = [
    ("Restaurant took too long", 18, 45),
    ("Item out of stock", 12, 30),
    ("Customer changed mind", 22, 5),
    ("Ordered by mistake", 14, 3),
    ("Restaurant closed", 8, 10),
    ("Delivery partner not assigned", 10, 3),
    ("Wrong address entered", 10, 2),
    ("Expected delivery time too long", 6, 2),
]

# (reason, weight, rider was assigned and picked up the food?)
FAILURE_REASONS = [
    ("Payment failed", 72, False),
    ("Customer unreachable", 12, True),
    ("Rider vehicle breakdown", 8, True),
    ("Delivery address not serviceable", 8, False),
]

# ---------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------
PAYMENT_METHODS = ["UPI", "Card", "Wallet", "COD", "NetBanking"]
DEFAULT_PAYMENT_WEIGHTS = [58, 14, 8, 12, 8]
CITY_PAYMENT_WEIGHTS = {             # COD is more popular in some cities
    "Kolkata": [45, 12, 6, 29, 8],
    "Ahmedabad": [50, 12, 6, 25, 7],
    "Delhi": [53, 14, 8, 18, 7],
}
# Method mix for orders whose payment FAILED (cards and net banking fail most).
FAILED_PAYMENT_WEIGHTS = [17, 45, 5, 0, 33]

# ---------------------------------------------------------------------
# Delivery partners
# ---------------------------------------------------------------------
VEHICLE_TYPES = ["Bike", "Scooter", "Bicycle", "EV"]
VEHICLE_WEIGHTS = [50, 30, 8, 12]
VEHICLE_SPEED_FACTOR = {"Bike": 1.0, "Scooter": 1.05, "Bicycle": 1.35, "EV": 1.0}

# ---------------------------------------------------------------------
# Review texts by sentiment
# ---------------------------------------------------------------------
REVIEWS_GOOD = [
    "Food was hot and delicious!", "Loved it, will order again.",
    "Quick delivery and great taste.", "Generous portions, value for money.",
    "Packaging was neat and the food was fresh.", "Tasted just like home-made food.",
    "Best order this month!", "Perfectly spiced, exactly how I like it.",
]
REVIEWS_OK = [
    "Decent food, nothing special.", "Okay experience overall.",
    "Food was fine but a bit pricey.", "Good taste, portion could be bigger.",
]
REVIEWS_BAD_FOOD = [
    "Food was cold and bland.", "Too oily and not fresh.",
    "Portion size was very small for the price.", "An item was missing from my order.",
    "Way too salty, could not finish it.", "Stale food, very disappointed.",
]
REVIEWS_BAD_DELIVERY = [
    "Delivery took forever.", "Rider was very late and did not pick up calls.",
    "Food arrived spilled.", "Rider could not find my address.",
    "Food was great but delivery was painfully slow.",
]

EMAIL_DOMAINS = ["gmail.com", "gmail.com", "gmail.com", "yahoo.co.in", "outlook.com", "rediffmail.com"]
