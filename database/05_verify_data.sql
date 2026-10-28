/* =====================================================================
   05_verify_data.sql
   Sanity checks after running:  python data_generator/seed_data.py

   Run in SSMS (any login, including sql_agent_reader). Each numbered
   query returns its own result grid. "EXPECT" tells you what good looks
   like. The patterns are explained in data_generator/PLANTED_INSIGHTS.md.

   These queries are also good T-SQL study material: GROUP BY, CASE,
   window functions (LAG, ROW_NUMBER), CTEs, DATEPART/DATEDIFF, NOT EXISTS.
   ===================================================================== */

USE FoodDeliveryDB;
GO
SET NOCOUNT ON;
GO

/* ---------------------------------------------------------------------
   1. Row counts per table
   EXPECT: ~8 / 48 / 15 / 300 / ~520 / 3,600 / 6,000 / 700 / 15 /
           ~80,000 / ~155,000 / ~80,000 (= Orders) / ~44,000
   --------------------------------------------------------------------- */
SELECT 'Cities' AS TableName, COUNT(*) AS RowCnt FROM dbo.Cities
UNION ALL SELECT 'Areas', COUNT(*) FROM dbo.Areas
UNION ALL SELECT 'Cuisines', COUNT(*) FROM dbo.Cuisines
UNION ALL SELECT 'Restaurants', COUNT(*) FROM dbo.Restaurants
UNION ALL SELECT 'RestaurantCuisines', COUNT(*) FROM dbo.RestaurantCuisines
UNION ALL SELECT 'MenuItems', COUNT(*) FROM dbo.MenuItems
UNION ALL SELECT 'Customers', COUNT(*) FROM dbo.Customers
UNION ALL SELECT 'DeliveryPartners', COUNT(*) FROM dbo.DeliveryPartners
UNION ALL SELECT 'Coupons', COUNT(*) FROM dbo.Coupons
UNION ALL SELECT 'Orders', COUNT(*) FROM dbo.Orders
UNION ALL SELECT 'OrderItems', COUNT(*) FROM dbo.OrderItems
UNION ALL SELECT 'Payments', COUNT(*) FROM dbo.Payments
UNION ALL SELECT 'Ratings', COUNT(*) FROM dbo.Ratings;

/* ---------------------------------------------------------------------
   2. Data integrity - EVERY number in this grid must be 0.
   --------------------------------------------------------------------- */
WITH ItemSums AS (
    SELECT oi.OrderID, SUM(oi.Quantity * oi.UnitPrice) AS ItemsAmount
    FROM dbo.OrderItems AS oi
    GROUP BY oi.OrderID
)
SELECT
    (SELECT COUNT(*) FROM dbo.Orders AS o JOIN ItemSums AS s ON s.OrderID = o.OrderID
      WHERE s.ItemsAmount <> o.ItemTotal)                                             AS ItemTotalMismatch,
    (SELECT COUNT(*) FROM dbo.Orders AS o
      WHERE NOT EXISTS (SELECT 1 FROM dbo.OrderItems AS oi WHERE oi.OrderID = o.OrderID)) AS OrdersWithoutItems,
    (SELECT COUNT(*) FROM dbo.Orders AS o
      WHERE NOT EXISTS (SELECT 1 FROM dbo.Payments AS p WHERE p.OrderID = o.OrderID))   AS OrdersWithoutPayment,
    (SELECT COUNT(*) FROM dbo.Orders WHERE CouponID IS NULL AND DiscountAmount > 0)     AS DiscountWithoutCoupon,
    (SELECT COUNT(*) FROM dbo.Ratings AS r JOIN dbo.Orders AS o ON o.OrderID = r.OrderID
      WHERE o.Status <> 'Delivered')                                                  AS RatingsOnUndelivered,
    (SELECT COUNT(*) FROM dbo.Orders AS o JOIN dbo.Payments AS p ON p.OrderID = o.OrderID
      WHERE o.Status = 'Delivered' AND (p.PaymentStatus <> 'Success' OR p.PaidAmount <> o.TotalAmount))
                                                                                      AS BadDeliveredPayments,
    (SELECT COUNT(*) FROM dbo.Orders AS o JOIN dbo.Payments AS p ON p.OrderID = o.OrderID
      WHERE o.Status = 'Cancelled' AND p.PaymentStatus = 'Success')                   AS CancelledButCharged,
    (SELECT COUNT(*) FROM dbo.Orders AS o JOIN dbo.Coupons AS c ON c.CouponID = o.CouponID
      WHERE CAST(o.OrderDateTime AS DATE) NOT BETWEEN c.ValidFrom AND c.ValidTo
         OR o.ItemTotal < c.MinOrderValue
         OR (c.MaxDiscount IS NOT NULL AND o.DiscountAmount > c.MaxDiscount))         AS CouponRuleBroken;

/* ---------------------------------------------------------------------
   3. Orders by hour of day
   EXPECT: lunch spike 12-14, bigger dinner spike 19-22, near zero 02-06.
   --------------------------------------------------------------------- */
SELECT DATEPART(HOUR, o.OrderDateTime) AS HourOfDay,
       COUNT(*)                         AS Orders
FROM dbo.Orders AS o
GROUP BY DATEPART(HOUR, o.OrderDateTime)
ORDER BY HourOfDay;

/* ---------------------------------------------------------------------
   4. Weekend vs weekday (average orders per day)
   EXPECT: weekend roughly 35% higher than weekday.
   DATENAME is used instead of DATEPART(WEEKDAY) because the latter
   depends on the server's DATEFIRST setting.
   --------------------------------------------------------------------- */
WITH Daily AS (
    SELECT CAST(o.OrderDateTime AS DATE) AS OrderDate, COUNT(*) AS Orders
    FROM dbo.Orders AS o
    GROUP BY CAST(o.OrderDateTime AS DATE)
)
SELECT CASE WHEN DATENAME(WEEKDAY, d.OrderDate) IN ('Saturday', 'Sunday') THEN 'Weekend' ELSE 'Weekday' END AS DayType,
       COUNT(*)            AS Days,
       AVG(d.Orders * 1.0) AS AvgOrdersPerDay
FROM Daily AS d
GROUP BY CASE WHEN DATENAME(WEEKDAY, d.OrderDate) IN ('Saturday', 'Sunday') THEN 'Weekend' ELSE 'Weekday' END;

/* ---------------------------------------------------------------------
   5. Orders and revenue by city
   EXPECT: Bengaluru and Mumbai on top, Ahmedabad (new city) last.
   --------------------------------------------------------------------- */
SELECT ci.CityName,
       COUNT(*)                                                   AS Orders,
       SUM(CASE WHEN o.Status = 'Delivered' THEN o.TotalAmount END) AS DeliveredRevenueINR
FROM dbo.Orders      AS o
JOIN dbo.Restaurants AS r  ON r.RestaurantID = o.RestaurantID
JOIN dbo.Areas       AS a  ON a.AreaID = r.AreaID
JOIN dbo.Cities      AS ci ON ci.CityID = a.CityID
GROUP BY ci.CityName
ORDER BY Orders DESC;

/* ---------------------------------------------------------------------
   6. Monthly orders: whole platform, Mumbai and Ahmedabad (+ MoM growth)
   EXPECT: platform spike in the Diwali month (Oct 2025 for a run in Oct 2026);
           Mumbai dip in July; Ahmedabad growing ~15-25% every month.
   --------------------------------------------------------------------- */
WITH Monthly AS (
    SELECT FORMAT(o.OrderDateTime, 'yyyy-MM') AS OrderMonth,
           COUNT(*)                                                 AS AllOrders,
           SUM(CASE WHEN ci.CityName = 'Mumbai'    THEN 1 ELSE 0 END) AS MumbaiOrders,
           SUM(CASE WHEN ci.CityName = 'Ahmedabad' THEN 1 ELSE 0 END) AS AhmedabadOrders
    FROM dbo.Orders      AS o
    JOIN dbo.Restaurants AS r  ON r.RestaurantID = o.RestaurantID
    JOIN dbo.Areas       AS a  ON a.AreaID = r.AreaID
    JOIN dbo.Cities      AS ci ON ci.CityID = a.CityID
    GROUP BY FORMAT(o.OrderDateTime, 'yyyy-MM')
)
SELECT m.OrderMonth, m.AllOrders, m.MumbaiOrders, m.AhmedabadOrders,
       CAST(100.0 * (m.AhmedabadOrders - LAG(m.AhmedabadOrders) OVER (ORDER BY m.OrderMonth))
            / NULLIF(LAG(m.AhmedabadOrders) OVER (ORDER BY m.OrderMonth), 0) AS DECIMAL(6,1)) AS AhmedabadMoMGrowthPct
FROM Monthly AS m
ORDER BY m.OrderMonth;

/* ---------------------------------------------------------------------
   7. Order status mix and cancellation reasons
   EXPECT: ~91% Delivered, ~7% Cancelled, ~2% Failed.
   --------------------------------------------------------------------- */
SELECT o.Status,
       COUNT(*)                                          AS Orders,
       CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS DECIMAL(5,2)) AS PctOfOrders
FROM dbo.Orders AS o
GROUP BY o.Status;

SELECT o.Status, o.CancellationReason, COUNT(*) AS Orders
FROM dbo.Orders AS o
WHERE o.Status <> 'Delivered'
GROUP BY o.Status, o.CancellationReason
ORDER BY o.Status, Orders DESC;

/* ---------------------------------------------------------------------
   8. Problem restaurants: high cancellation rate AND low food rating
   EXPECT: ~6 restaurants with 20-30% cancellations and avg food rating < 2.6
           (normal restaurants: ~6% and ~4.1).
   --------------------------------------------------------------------- */
WITH RestaurantStats AS (
    SELECT o.RestaurantID,
           COUNT(*)                                                      AS Orders,
           100.0 * SUM(CASE WHEN o.Status = 'Cancelled' THEN 1 ELSE 0 END) / COUNT(*) AS CancelPct
    FROM dbo.Orders AS o
    GROUP BY o.RestaurantID
    HAVING COUNT(*) >= 100
)
SELECT TOP 10
       r.RestaurantName, ci.CityName, rs.Orders,
       CAST(rs.CancelPct AS DECIMAL(5,1))                         AS CancelPct,
       CAST(AVG(rt.FoodRating * 1.0) AS DECIMAL(3,2))             AS AvgFoodRating
FROM RestaurantStats  AS rs
JOIN dbo.Restaurants  AS r  ON r.RestaurantID = rs.RestaurantID
JOIN dbo.Areas        AS a  ON a.AreaID = r.AreaID
JOIN dbo.Cities       AS ci ON ci.CityID = a.CityID
JOIN dbo.Orders       AS o  ON o.RestaurantID = rs.RestaurantID
JOIN dbo.Ratings      AS rt ON rt.OrderID = o.OrderID
GROUP BY r.RestaurantName, ci.CityName, rs.Orders, rs.CancelPct
ORDER BY rs.CancelPct DESC;

/* ---------------------------------------------------------------------
   9. Delivery: slow partners, and time vs distance
   EXPECT: ~35 riders averaging 60+ minutes with delivery rating < 2.6;
           everyone else ~40 minutes and ~4.1. Delivery time rises with distance.
   --------------------------------------------------------------------- */
SELECT TOP 40
       dp.PartnerID, dp.FullName, ci.CityName, dp.VehicleType,
       COUNT(*)                                                                  AS Deliveries,
       AVG(DATEDIFF(MINUTE, o.OrderDateTime, o.DeliveredDateTime))               AS AvgDeliveryMins,
       CAST(AVG(rt.DeliveryRating * 1.0) AS DECIMAL(3,2))                        AS AvgDeliveryRating
FROM dbo.Orders           AS o
JOIN dbo.DeliveryPartners AS dp ON dp.PartnerID = o.PartnerID
JOIN dbo.Cities           AS ci ON ci.CityID = dp.CityID
LEFT JOIN dbo.Ratings     AS rt ON rt.OrderID = o.OrderID
WHERE o.Status = 'Delivered'
GROUP BY dp.PartnerID, dp.FullName, ci.CityName, dp.VehicleType
HAVING COUNT(*) >= 20
ORDER BY AvgDeliveryMins DESC;

SELECT CASE WHEN o.DeliveryDistanceKm < 3  THEN '1) 0-3 km'
            WHEN o.DeliveryDistanceKm < 6  THEN '2) 3-6 km'
            WHEN o.DeliveryDistanceKm < 9  THEN '3) 6-9 km'
            ELSE '4) 9+ km' END                                      AS DistanceBand,
       COUNT(*)                                                       AS Deliveries,
       AVG(DATEDIFF(MINUTE, o.PickupDateTime, o.DeliveredDateTime))   AS AvgRideMins
FROM dbo.Orders AS o
WHERE o.Status = 'Delivered'
GROUP BY CASE WHEN o.DeliveryDistanceKm < 3  THEN '1) 0-3 km'
              WHEN o.DeliveryDistanceKm < 6  THEN '2) 3-6 km'
              WHEN o.DeliveryDistanceKm < 9  THEN '3) 6-9 km'
              ELSE '4) 9+ km' END
ORDER BY DistanceBand;

/* ---------------------------------------------------------------------
   10. Coupons: usage, first-order share and repeat behaviour
   EXPECT: WELCOME50 / FIRSTBITE ~100% first orders; SUMMER25 never used.
           Customers acquired with MEGA60 repeat far less (~30%) than
           others (~95%).
   --------------------------------------------------------------------- */
WITH NumberedOrders AS (
    SELECT o.OrderID, o.CustomerID, o.CouponID,
           ROW_NUMBER() OVER (PARTITION BY o.CustomerID ORDER BY o.OrderDateTime, o.OrderID) AS OrderNumber
    FROM dbo.Orders AS o
)
SELECT c.CouponCode, c.IsNewUserOnly,
       COUNT(n.OrderID)                                                        AS TimesUsed,
       CAST(100.0 * SUM(CASE WHEN n.OrderNumber = 1 THEN 1 ELSE 0 END)
            / NULLIF(COUNT(n.OrderID), 0) AS DECIMAL(5,1))                      AS PctOnFirstOrder
FROM dbo.Coupons AS c
LEFT JOIN NumberedOrders AS n ON n.CouponID = c.CouponID
GROUP BY c.CouponCode, c.IsNewUserOnly
ORDER BY TimesUsed DESC;

WITH NumberedOrders AS (
    SELECT o.CustomerID, o.CouponID,
           ROW_NUMBER() OVER (PARTITION BY o.CustomerID ORDER BY o.OrderDateTime, o.OrderID) AS OrderNumber,
           COUNT(*)     OVER (PARTITION BY o.CustomerID)                                     AS TotalOrders
    FROM dbo.Orders AS o
)
SELECT ISNULL(c.CouponCode, '(no coupon)')                                  AS FirstOrderCoupon,
       COUNT(*)                                                             AS Customers,
       CAST(100.0 * SUM(CASE WHEN n.TotalOrders > 1 THEN 1 ELSE 0 END) / COUNT(*) AS DECIMAL(5,1)) AS RepeatPct,
       AVG(n.TotalOrders * 1.0)                                             AS AvgOrdersPerCustomer
FROM NumberedOrders   AS n
LEFT JOIN dbo.Coupons AS c ON c.CouponID = n.CouponID
WHERE n.OrderNumber = 1
GROUP BY ISNULL(c.CouponCode, '(no coupon)')
ORDER BY Customers DESC;

/* ---------------------------------------------------------------------
   11. Churn and premium members
   EXPECT: ~20% of customers who ever ordered have no order in the last
           60 days; premium members order ~2.5x as often as regulars.
   --------------------------------------------------------------------- */
WITH CustomerActivity AS (
    SELECT o.CustomerID, MAX(o.OrderDateTime) AS LastOrder, COUNT(*) AS Orders
    FROM dbo.Orders AS o
    GROUP BY o.CustomerID
)
SELECT CASE WHEN cu.IsPremiumMember = 1 THEN 'Premium' ELSE 'Regular' END AS Segment,
       COUNT(*)                                                           AS CustomersWhoOrdered,
       AVG(ca.Orders * 1.0)                                               AS AvgOrdersPerCustomer,
       CAST(100.0 * SUM(CASE WHEN ca.LastOrder < DATEADD(DAY, -60, CAST(GETDATE() AS DATE)) THEN 1 ELSE 0 END)
            / COUNT(*) AS DECIMAL(5,1))                                   AS ChurnedPct
FROM CustomerActivity AS ca
JOIN dbo.Customers    AS cu ON cu.CustomerID = ca.CustomerID
GROUP BY ROLLUP (CASE WHEN cu.IsPremiumMember = 1 THEN 'Premium' ELSE 'Regular' END);
-- The row where Segment is NULL is the overall total (that's what ROLLUP adds).

/* ---------------------------------------------------------------------
   12. Payments: method mix, failures, COD by city
   EXPECT: UPI dominant (~55%); failed payments mostly Card + NetBanking;
           COD highest in Kolkata and Ahmedabad.
   --------------------------------------------------------------------- */
SELECT p.PaymentMethod,
       COUNT(*)                                                        AS Payments,
       CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS DECIMAL(5,1))  AS PctOfPayments,
       SUM(CASE WHEN p.PaymentStatus = 'Failed' THEN 1 ELSE 0 END)     AS FailedPayments
FROM dbo.Payments AS p
GROUP BY p.PaymentMethod
ORDER BY Payments DESC;

SELECT ci.CityName,
       CAST(100.0 * SUM(CASE WHEN p.PaymentMethod = 'COD' THEN 1 ELSE 0 END) / COUNT(*) AS DECIMAL(5,1)) AS CODPct
FROM dbo.Payments    AS p
JOIN dbo.Orders      AS o  ON o.OrderID = p.OrderID
JOIN dbo.Restaurants AS r  ON r.RestaurantID = o.RestaurantID
JOIN dbo.Areas       AS a  ON a.AreaID = r.AreaID
JOIN dbo.Cities      AS ci ON ci.CityID = a.CityID
GROUP BY ci.CityName
ORDER BY CODPct DESC;
GO
