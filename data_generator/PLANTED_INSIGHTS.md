# Planted insights

The sample data is random, but **not** uniformly random. The patterns below were planted on purpose so that demo questions have interesting, explainable answers. Each pattern lists:

- **What** was planted, and the setting in [`config.py`](config.py) that controls it.
- **Ask** gives a plain-English question that should surface it.
- **Expect** describes the shape of a correct answer.

The numbers come from a seed run on **2026-10-28**, which covered data from 2025-10-01 to 2026-10-27. Data always ends *yesterday*. If you seed on another day the dates shift, but the shapes stay the same. The seed script prints the exact dates for your run under **"Planted facts for this run"**. To check every pattern at once in SSMS, run [`database/05_verify_data.sql`](../database/05_verify_data.sql).

---

## 1. Peak hours: lunch and a bigger dinner rush

**What:** orders follow a half-hour demand curve (`HALF_HOUR_WEIGHTS`): a lunch spike from 12:00 to 14:30, a bigger dinner spike from 19:30 to 22:30, and almost nothing from 02:00 to 07:00.

**Ask:** *"How many orders do we get in each hour of the day?"* or *"What are our peak ordering hours?"*

**Expect:** 24 rows. Hours 20 and 21 are highest (~11k each), hours 12–13 are the second hump (~7.5k), and hours 2–5 are under 200.

## 2. Weekends are about 35% busier

**What:** `WEEKEND_MULTIPLIER = 1.35` applies to Saturdays and Sundays.

**Ask:** *"Compare average daily orders on weekends vs weekdays."*

**Expect:** Weekend ≈ 252 orders per day, Weekday ≈ 187 orders per day, so the ratio is about 1.35.

## 3. Bengaluru and Mumbai lead; Ahmedabad grows fast

**What:** `CITY_ORDER_WEIGHTS` makes Bengaluru and Mumbai the biggest cities. **Ahmedabad** launched 3 months into the data (`Cities.LaunchDate` = 2026-01-01). It started at 15% of its eventual volume and grows about 22% a month (`NEW_CITY_*` settings).

**Ask:**
- *"Total orders and revenue by city."*
- *"Show Ahmedabad's monthly orders and month-over-month growth."* (a good window-function / LAG demo)
- *"Which city launched most recently?"*

**Expect:** Bengaluru (~18.1k) > Mumbai (~15.8k) > Delhi > Hyderabad > Chennai > Pune > Kolkata > Ahmedabad (~1.8k). Ahmedabad's monthly orders rise steadily: 34 → 64 → 102 → … → 379, with growth between +15% and +25% in most months.

**Bonus:** Hyderabad has fewer orders than Delhi but nearly the same revenue as Mumbai. Its average order value is the highest, because of biryani family packs and other expensive biryani dishes.

## 4. Diwali festive spike

**What:** the month that contains Diwali gets ×1.15, and the 12 days before Diwali get ×1.45 (`DIWALI_DATES`, `FESTIVE_*`). In this run that's **October 2025**, with Diwali on 21 Oct 2025.

**Ask:** *"Show total orders per month."* or *"Which month had the most orders?"*

**Expect:** October 2025 ≈ 7,600 orders against ~5,500–6,700 in other months, so it's the clear peak. A `DIWALI25` coupon was also active only in that window.

## 5. Mumbai monsoon dip

**What:** in **July**, Mumbai orders drop to ~62% of normal and deliveries take ~25% longer (`MONSOON_*`).

**Ask:** *"Show Mumbai's monthly orders."* or *"How did July compare with other months in Mumbai?"* or *"Average delivery time in Mumbai by month."*

**Expect:** Mumbai July 2026 ≈ 806 orders against ~1,150–1,300 in other months. Delivery times are noticeably higher in July.

## 6. Cancellations, failures, and a few bad restaurants

**What:**
- About 6.7% of orders are Cancelled and about 2% Failed. Reasons are in `Orders.CancellationReason`; "Customer changed mind" and "Restaurant took too long" are the top cancellation reasons, and "Payment failed" is the top failure reason.
- **6 problem restaurants** have about a 20–26% cancellation rate **and** an average food rating around 2.1–2.4, against roughly 6% and 4.1 for everyone else (`PROBLEM_RESTAURANT_*`).

**Ask:**
- *"What percentage of orders were delivered, cancelled and failed?"*
- *"Top cancellation reasons."*
- *"Which restaurants have the highest cancellation rate (minimum 100 orders) and what is their average food rating?"* (a good HAVING demo)

**Expect (this run):** Apna Pizza Co. (Bengaluru), Royal Cafe (Delhi), Coastal Cafe, Lucknowi Rasthal and Kesar Oven Story Kitchen (all Mumbai), and Nawab Cafe (Bengaluru). The next-worst restaurant drops to about an 11% cancellation rate with a 4.0+ food rating, so the problem group stands out clearly.

## 7. Consistently slow delivery partners

**What:** about 4–5% of riders (27 in this run) travel about 2.3× slower and get low delivery ratings (`SLOW_PARTNER_*`). Bicycle riders are also a bit slower, but they're rated normally.

**Ask:** *"Which delivery partners have the highest average delivery time (minimum 20 deliveries), with their average delivery rating?"*

**Expect:** a group of riders averaging 59–78 minutes with ratings of 1.9–2.6. Then there's a clear gap: the next riders are at about 48–53 minutes with ratings around 4.0, and they're mostly on bicycles. The platform-wide average is about 41 minutes.

## 8. Delivery time grows with distance

**What:** ride time is roughly 3 minutes plus 2.8 minutes per km, multiplied by rider speed and peak-hour traffic. The timeline is always `OrderDateTime < PickupDateTime < DeliveredDateTime`, and the database enforces this with CHECK constraints.

**Ask:** *"Average delivery time by distance band (0–3, 3–6, 6–9, 9+ km)."*

**Expect:** a steady rise. Average ride time (pickup to door) is about 9, 16, 28 and 41 minutes for the four bands.

## 9. WELCOME coupons on first orders; MEGA60 brings one-time deal hunters

**What:**
- `WELCOME50` and `FIRSTBITE` have `IsNewUserOnly = 1` and are used only on a customer's first order.
- **MEGA60** ran as a 3-month campaign (2026-01-29 to 2026-04-28 in this run). It attracted "deal hunters" who order one to three times and then disappear (`DEAL_HUNTER_*`).
- `SUMMER25` expired before the data starts, so it was **never used**.

**Ask:**
- *"For each coupon, how many times was it used and what share of uses were on the customer's first order?"* (a ROW_NUMBER demo)
- *"For customers whose first order used a coupon, what percentage ordered again, by coupon?"*
- *"Which coupons have never been used?"* (a LEFT JOIN / NOT EXISTS demo)

**Expect:**
- WELCOME50 (~1.8k uses) and FIRSTBITE (~1.1k uses) are 100% first orders. Other coupons are around 2%.
- Customers acquired with MEGA60 have a **~33% repeat rate and ~2 orders each**. Customers acquired with WELCOME50 or with no coupon repeat about 93–96% of the time, with ~14 orders each.
- The never-used query returns SUMMER25 only.

## 10. Churn and premium members

**What:** about 20% of customers who ever ordered have **no order in the last 60 days**. Premium members (`IsPremiumMember = 1`, ~15%) order about 2.5× as often, rarely churn, and get free delivery (`DeliveryFee = 0`).

**Ask:**
- *"How many customers have not ordered in the last 60 days?"*
- *"Compare average orders per customer for premium vs regular members."*
- *"Average delivery fee for premium vs regular customers."*

**Expect:** about 21–22% churned overall. Premium members average ~27.6 orders and ~6% churn, against ~11.3 orders and ~25% churn for regular customers. The premium delivery fee is 0.

## 11. Payments: UPI dominates, COD by city, card and net-banking failures

**What:**
- UPI is about 55% of payments.
- COD is much higher in **Kolkata (~29%)** and **Ahmedabad (~25%)**, against ~12% elsewhere.
- Orders that failed because of payment were mostly Card or NetBanking (`FAILED_PAYMENT_WEIGHTS`).
- Delivered orders always have `PaymentStatus = 'Success'`.
- Cancelled orders are `Refunded` if prepaid, or `Failed` (no money collected) if COD.

**Ask:** *"Payment method share."*, *"Failed payments by payment method."* or *"COD share by city."*

**Expect:**
- Method share: UPI 55.5%, then COD and Card at about 14% each, NetBanking 8%, Wallet 8%.
- Failed payments: Card (~550) and NetBanking (~380) together are the majority, and UPI has the lowest failure **rate** (~0.4%).
- COD share: Kolkata and Ahmedabad lead.

## 12. Data consistency you can rely on (and demo)

**What:** these rules hold for every row, and most of them are also CHECK constraints in the database:
- `ItemTotal = SUM(Quantity * UnitPrice)` for the order's items.
- `TotalAmount = ItemTotal + DeliveryFee - DiscountAmount`.
- The discount never exceeds the coupon's `MaxDiscount` or the `ItemTotal`, and the coupon was valid on the order date with `MinOrderValue` met.
- Ratings exist only for Delivered orders (about 60% of them).

**Bonus pattern:** menu prices rose by about 5% six months into the data, so `OrderItems.UnitPrice` for older orders is lower than today's `MenuItems.Price`. Ask: *"Compare the average price paid for Masala Dosa per month."*

**Ask:** *"Check whether any order's ItemTotal doesn't match the sum of its order items."*

**Expect:** 0 rows. This is a nice way to show data quality.
