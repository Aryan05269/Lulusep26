"""
generate_data.py
----------------
Creates a SYNTHETIC (made-up) sales dataset for a LuLu-style hypermarket chain
in the UAE and saves it as  lulu_sales_data.csv

Nothing here is real LuLu data. The numbers are invented, but they follow
realistic patterns so the dashboard has something interesting to show:
  * Fresh and Grocery = cheap items, many units, many transactions
  * Electronics and Furniture = expensive items, few units
  * Dubai and Abu Dhabi get more transactions than smaller emirates
  * Sales rise during Ramadan, DSF, White Friday and Back to School
  * UAE weekend is Saturday + Sunday, so weekends are busier

Run it with:   python generate_data.py
Change N_ROWS or SEED below to create a different dataset.
"""

import numpy as np
import pandas as pd

N_ROWS = 1000          # how many transactions to create
SEED = 42              # same seed = same dataset every time (reproducible)
START_DATE = "2025-10-01"
END_DATE = "2026-09-30"

rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# 1. Emirates and stores
#    weight = share of transactions (bigger emirates get more)
#    Store names are illustrative, not an official store list.
# ---------------------------------------------------------------------------
EMIRATES = {
    "Dubai":          {"weight": 0.32, "stores": {"Al Barsha": "Hypermarket", "Al Qusais": "Hypermarket", "Silicon Oasis": "Supermarket", "JLT": "Express"}},
    "Abu Dhabi":      {"weight": 0.30, "stores": {"Al Wahda": "Hypermarket", "Mushrif": "Hypermarket", "Khalifa City": "Supermarket", "Al Reem": "Express"}},
    "Sharjah":        {"weight": 0.18, "stores": {"Al Nahda": "Hypermarket", "Muwaileh": "Supermarket", "Al Majaz": "Express"}},
    "Ajman":          {"weight": 0.07, "stores": {"Al Jurf": "Hypermarket", "Al Nuaimiya": "Express"}},
    "Ras Al Khaimah": {"weight": 0.06, "stores": {"Al Nakheel": "Hypermarket", "Al Hamra": "Supermarket"}},
    "Fujairah":       {"weight": 0.04, "stores": {"Fujairah City": "Hypermarket"}},
    "Umm Al Quwain":  {"weight": 0.03, "stores": {"UAQ Central": "Supermarket"}},
}

# ---------------------------------------------------------------------------
# 2. Categories and sub-categories
#    weight  = share of transactions
#    margin  = profit margin at full price (before any discount)
#    units   = (min, max) units bought in one transaction
#    price   = (min, max) unit price in AED for each sub-category
#    private = chance the item is a LuLu own-brand (private label) product
# ---------------------------------------------------------------------------
CATEGORIES = {
    "Fresh": {
        "weight": 0.26, "margin": (0.18, 0.28), "units": (1, 12), "private": 0.40,
        "subs": {"Fruits & Vegetables": (3, 25), "Meat & Poultry": (18, 60), "Seafood": (20, 75),
                 "Bakery": (3, 20), "Dairy & Eggs": (4, 30)},
    },
    "Grocery": {
        "weight": 0.28, "margin": (0.12, 0.20), "units": (1, 10), "private": 0.35,
        "subs": {"Rice & Grains": (15, 90), "Beverages": (3, 25), "Snacks": (4, 20),
                 "Cooking Oil & Ghee": (12, 60), "Household Cleaning": (8, 45)},
    },
    "Fashion": {
        "weight": 0.14, "margin": (0.35, 0.50), "units": (1, 4), "private": 0.25,
        "subs": {"Men's Wear": (40, 250), "Women's Wear": (45, 320), "Kids' Wear": (25, 150),
                 "Footwear": (50, 350), "Accessories": (20, 180)},
    },
    "Home Decor": {
        "weight": 0.11, "margin": (0.30, 0.45), "units": (1, 4), "private": 0.30,
        "subs": {"Lighting": (40, 400), "Wall Art": (30, 300), "Bedding & Linen": (60, 450),
                 "Kitchenware": (20, 250), "Rugs & Carpets": (80, 600)},
    },
    "Electronics": {
        "weight": 0.12, "margin": (0.14, 0.22), "units": (1, 2), "private": 0.05,
        "subs": {"Mobile Phones": (400, 4500), "Laptops": (1500, 6000), "Televisions": (800, 5000),
                 "Small Appliances": (60, 700), "Audio & Accessories": (40, 900)},
    },
    "Furniture": {
        "weight": 0.09, "margin": (0.25, 0.38), "units": (1, 2), "private": 0.20,
        "subs": {"Sofas": (1200, 5500), "Beds & Mattresses": (900, 4800), "Dining Sets": (800, 4000),
                 "Office Chairs": (250, 1500), "Storage & Wardrobes": (400, 3000)},
    },
}

# ---------------------------------------------------------------------------
# 3. Festive / promotion seasons (approximate dates for 2025-26)
#    boost = how much busier each day in the season is (1.5 = 50% busier)
#    focus = categories that get an extra push during that season
# ---------------------------------------------------------------------------
SEASONS = {
    "White Friday":   {"start": "2025-11-20", "end": "2025-11-30", "boost": 1.6, "focus": ["Electronics", "Fashion", "Home Decor"]},
    "DSF":            {"start": "2025-12-12", "end": "2026-01-25", "boost": 1.3, "focus": ["Fashion", "Electronics", "Furniture"]},
    "Ramadan":        {"start": "2026-02-18", "end": "2026-03-19", "boost": 1.5, "focus": ["Fresh", "Grocery", "Home Decor"]},
    "Back to School": {"start": "2026-08-15", "end": "2026-09-10", "boost": 1.3, "focus": ["Fashion", "Electronics"]},
}

# Typical discount range (%) for each promotion type
DISCOUNT_RANGE = {
    "No Promotion": (0, 5), "Weekend Deal": (5, 15), "Ramadan": (10, 25),
    "DSF": (15, 40), "White Friday": (20, 50), "Back to School": (10, 30),
}


def pick(options, weights, size=None):
    """Randomly choose from options using weights (weights are normalised to sum to 1)."""
    w = np.array(weights, dtype=float)
    return rng.choice(options, p=w / w.sum(), size=size)


def season_on(day):
    """Return the season name if the day falls inside one, else None."""
    for name, s in SEASONS.items():
        if pd.Timestamp(s["start"]) <= day <= pd.Timestamp(s["end"]):
            return name
    return None


# ---------------------------------------------------------------------------
# 4. Pick a date for every transaction
#    Each day gets a "busyness" weight: weekends, seasons and summer change it.
# ---------------------------------------------------------------------------
days = pd.date_range(START_DATE, END_DATE, freq="D")
day_weights = []
for d in days:
    w = 1.0
    if d.dayofweek >= 5:            # 5 = Saturday, 6 = Sunday (UAE weekend)
        w *= 1.25
    if d.month in (6, 7):           # summer: many residents travel abroad
        w *= 0.80
    s = season_on(d)
    if s:
        w *= SEASONS[s]["boost"]
    day_weights.append(w)

dates = pick(days, day_weights, size=N_ROWS)

# Hour of the day: quiet mornings, busy evenings
hours = np.arange(8, 24)
hour_weights = [2, 3, 4, 5, 5, 4, 4, 5, 6, 7, 9, 10, 10, 8, 5, 3]

# ---------------------------------------------------------------------------
# 5. Build each transaction row
# ---------------------------------------------------------------------------
rows = []
cat_names = list(CATEGORIES)
emirate_names = list(EMIRATES)

for date in dates:
    date = pd.Timestamp(date)
    season = season_on(date)
    is_weekend = date.dayofweek >= 5

    # --- Where? ---
    emirate = pick(emirate_names, [EMIRATES[e]["weight"] for e in emirate_names])
    store_area = pick(list(EMIRATES[emirate]["stores"]), [1] * len(EMIRATES[emirate]["stores"]))
    store_format = EMIRATES[emirate]["stores"][store_area]

    # --- What? (seasons push their focus categories) ---
    cat_w = [CATEGORIES[c]["weight"] * (1.8 if season and c in SEASONS[season]["focus"] else 1.0)
             for c in cat_names]
    # Express stores are small: mostly fresh and grocery
    if store_format == "Express":
        cat_w = [w * (2.5 if c in ("Fresh", "Grocery") else 0.3) for c, w in zip(cat_names, cat_w)]
    category = pick(cat_names, cat_w)
    cat = CATEGORIES[category]
    sub_category = pick(list(cat["subs"]), [1] * len(cat["subs"]))
    brand_type = "LuLu Private Label" if rng.random() < cat["private"] else "National Brand"

    # --- Promotion and discount ---
    if season and rng.random() < 0.65:
        promotion = season
    elif is_weekend and rng.random() < 0.35:
        promotion = "Weekend Deal"
    else:
        promotion = "No Promotion"   # (not "None": pandas would read that as an empty cell)
    lo, hi = DISCOUNT_RANGE[promotion]
    discount_pct = 0.0 if (promotion == "No Promotion" and rng.random() < 0.7) else rng.uniform(lo, hi)
    # Some categories are never discounted as deeply (thin margins or perishable)
    discount_pct = round(discount_pct * {"Fresh": 0.5, "Grocery": 0.8, "Electronics": 0.6}.get(category, 1.0), 1)

    # --- How much? ---
    p_lo, p_hi = cat["subs"][sub_category]
    unit_price = round(rng.uniform(p_lo, p_hi), 2)
    u_lo, u_hi = cat["units"]
    units = int(rng.integers(u_lo, u_hi + 1))
    if promotion != "No Promotion" and u_hi > 2 and rng.random() < 0.4:
        units += 1                    # promotions tempt people to buy one more

    margin = rng.uniform(*cat["margin"])
    gross = round(units * unit_price, 2)
    net = round(gross * (1 - discount_pct / 100), 2)
    cost = round(gross * (1 - margin), 2)          # cost does not change with discount
    profit = round(net - cost, 2)                  # deep discounts can make this negative

    # --- Channel and payment ---
    online_share = 0.35 if category in ("Electronics", "Furniture", "Fashion") else 0.18
    channel = pick(["In-store", "Online", "Click & Collect"], [1 - online_share, online_share * 0.65, online_share * 0.35])
    bnpl = 0.25 if category in ("Electronics", "Furniture") else 0.04
    payment = pick(["Card", "Cash", "Digital Wallet", "Buy Now Pay Later"], [0.45, 0.22, 0.25, bnpl])
    if channel != "In-store" and payment == "Cash":
        payment = "Card"              # keep it simple: online orders are paid electronically

    # --- Who? ---
    age_group = pick(["18-24", "25-34", "35-44", "45-54", "55+"], [0.14, 0.33, 0.28, 0.16, 0.09])
    gender = pick(["Male", "Female"], [0.58, 0.42])
    loyalty = "Yes" if rng.random() < 0.55 else "No"
    rating = int(pick([1, 2, 3, 4, 5], [0.04, 0.07, 0.18, 0.40, 0.31]))

    timestamp = date + pd.Timedelta(hours=int(pick(hours, hour_weights)),
                                    minutes=int(rng.integers(0, 60)),
                                    seconds=int(rng.integers(0, 60)))

    rows.append({
        "Timestamp": timestamp,
        "Date": timestamp.date(),
        "Month": timestamp.strftime("%Y-%m"),
        "Day_of_Week": timestamp.day_name(),
        "Is_Weekend": "Yes" if is_weekend else "No",
        "Emirate": emirate,
        "Store_Name": f"LuLu {store_area}",
        "Store_Format": store_format,
        "Category": category,
        "Sub_Category": sub_category,
        "Brand_Type": brand_type,
        "Units_Sold": units,
        "Unit_Price_AED": unit_price,
        "Discount_Pct": discount_pct,
        "Gross_Sales_AED": gross,
        "Net_Sales_AED": net,
        "Cost_AED": cost,
        "Profit_AED": profit,
        "Sales_Channel": channel,
        "Payment_Method": payment,
        "Promotion": promotion,
        "Age_Group": age_group,
        "Gender": gender,
        "Loyalty_Member": loyalty,
        "Customer_Rating": rating,
    })

# ---------------------------------------------------------------------------
# 6. Sort by time (oldest first) and give each row an ID
#    Sorting by time also makes it easy to "replay" the data as a live stream later.
# ---------------------------------------------------------------------------
df = pd.DataFrame(rows).sort_values("Timestamp").reset_index(drop=True)
df.insert(0, "Transaction_ID", [f"TXN-{i:05d}" for i in range(1, len(df) + 1)])

df.to_csv("lulu_sales_data.csv", index=False)
print(f"Saved lulu_sales_data.csv with {len(df)} rows and {df.shape[1]} columns")
