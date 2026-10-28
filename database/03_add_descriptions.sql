/* =====================================================================
   03_add_descriptions.sql
   Adds a plain-English description (the MS_Description extended property)
   to EVERY table and EVERY column.

   WHY THIS MATTERS: the SQL Agent reads these descriptions live and sends
   them to the LLM together with the table/column names. Column names alone
   are ambiguous ("Status" of what? "Amount" in which currency? Is 1 good or
   bad?). Good descriptions are the single cheapest way to get better SQL.

   Run after: 02_create_tables.sql
   Re-runnable: yes - existing descriptions are updated, not duplicated.
   ===================================================================== */

USE FoodDeliveryDB;
GO

/* ---------------------------------------------------------------------
   Helper: dbo.usp_SetDescription
   A small helper procedure that exists only while this script runs -
   it is dropped again at the end, so it never becomes part of the schema.

   sp_addextendedproperty fails if the property already exists, and
   sp_updateextendedproperty fails if it doesn't, so this helper picks the
   right one. That's what makes the script safe to run more than once.

   @Column = NULL  -> describes the table itself.
   --------------------------------------------------------------------- */
DROP PROCEDURE IF EXISTS dbo.usp_SetDescription;
GO

CREATE PROCEDURE dbo.usp_SetDescription
    @Table       SYSNAME,
    @Column      SYSNAME = NULL,
    @Description NVARCHAR(1000)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @Exists BIT = CASE WHEN EXISTS (
        SELECT 1
        FROM sys.extended_properties AS ep
        WHERE ep.name     = N'MS_Description'
          AND ep.class    = 1                                   -- 1 = object or column
          AND ep.major_id = OBJECT_ID(N'dbo.' + @Table)
          AND ep.minor_id = ISNULL(COLUMNPROPERTY(OBJECT_ID(N'dbo.' + @Table), @Column, 'ColumnId'), 0)
    ) THEN 1 ELSE 0 END;

    IF @Column IS NULL
    BEGIN
        IF @Exists = 1
            EXEC sp_updateextendedproperty @name = N'MS_Description', @value = @Description,
                 @level0type = N'SCHEMA', @level0name = N'dbo',
                 @level1type = N'TABLE',  @level1name = @Table;
        ELSE
            EXEC sp_addextendedproperty    @name = N'MS_Description', @value = @Description,
                 @level0type = N'SCHEMA', @level0name = N'dbo',
                 @level1type = N'TABLE',  @level1name = @Table;
    END
    ELSE
    BEGIN
        IF @Exists = 1
            EXEC sp_updateextendedproperty @name = N'MS_Description', @value = @Description,
                 @level0type = N'SCHEMA', @level0name = N'dbo',
                 @level1type = N'TABLE',  @level1name = @Table,
                 @level2type = N'COLUMN', @level2name = @Column;
        ELSE
            EXEC sp_addextendedproperty    @name = N'MS_Description', @value = @Description,
                 @level0type = N'SCHEMA', @level0name = N'dbo',
                 @level1type = N'TABLE',  @level1name = @Table,
                 @level2type = N'COLUMN', @level2name = @Column;
    END
END;
GO

/* =====================================================================
   Cities
   ===================================================================== */
EXEC dbo.usp_SetDescription 'Cities', NULL,         N'Indian cities where the food delivery platform operates. One row per city.';
EXEC dbo.usp_SetDescription 'Cities', 'CityID',     N'Unique ID of the city (primary key).';
EXEC dbo.usp_SetDescription 'Cities', 'CityName',   N'Name of the city, e.g. Bengaluru, Mumbai, Delhi, Hyderabad, Chennai, Pune, Kolkata, Ahmedabad. Unique.';
EXEC dbo.usp_SetDescription 'Cities', 'State',      N'Indian state the city belongs to, e.g. Karnataka, Maharashtra.';
EXEC dbo.usp_SetDescription 'Cities', 'LaunchDate', N'Date the platform started operating in this city. Cities with a recent LaunchDate are newer markets.';

/* =====================================================================
   Areas
   ===================================================================== */
EXEC dbo.usp_SetDescription 'Areas', NULL,       N'Neighbourhoods / localities inside a city (e.g. Koramangala in Bengaluru, Andheri West in Mumbai). Restaurants and customers are located in an area. To get the city of anything, join through Areas to Cities.';
EXEC dbo.usp_SetDescription 'Areas', 'AreaID',   N'Unique ID of the area (primary key).';
EXEC dbo.usp_SetDescription 'Areas', 'CityID',   N'City this area belongs to. Foreign key to Cities.CityID.';
EXEC dbo.usp_SetDescription 'Areas', 'AreaName', N'Name of the locality, e.g. Koramangala, Whitefield, Indiranagar, Bandra West. Unique within a city.';
EXEC dbo.usp_SetDescription 'Areas', 'Pincode',  N'6-digit Indian postal PIN code of the area, stored as text (e.g. ''560034'').';

/* =====================================================================
   Cuisines
   ===================================================================== */
EXEC dbo.usp_SetDescription 'Cuisines', NULL,          N'Types of cuisine a restaurant can serve, e.g. North Indian, South Indian, Chinese, Biryani, Pizza. Linked to restaurants via RestaurantCuisines.';
EXEC dbo.usp_SetDescription 'Cuisines', 'CuisineID',   N'Unique ID of the cuisine (primary key).';
EXEC dbo.usp_SetDescription 'Cuisines', 'CuisineName', N'Name of the cuisine, e.g. North Indian, South Indian, Chinese, Biryani, Pizza, Desserts. Unique.';

/* =====================================================================
   Restaurants
   ===================================================================== */
EXEC dbo.usp_SetDescription 'Restaurants', NULL,              N'Restaurant partners listed on the platform. Each restaurant is in one area (and therefore one city). A restaurant''s cuisines are in RestaurantCuisines; its dishes are in MenuItems.';
EXEC dbo.usp_SetDescription 'Restaurants', 'RestaurantID',    N'Unique ID of the restaurant (primary key).';
EXEC dbo.usp_SetDescription 'Restaurants', 'AreaID',          N'Area where the restaurant is located. Foreign key to Areas.AreaID (join Areas then Cities to get the city).';
EXEC dbo.usp_SetDescription 'Restaurants', 'RestaurantName',  N'Display name of the restaurant. Not unique: chains can have outlets in several areas.';
EXEC dbo.usp_SetDescription 'Restaurants', 'PriceRange',      N'Price segment of the restaurant. Allowed values: Budget, Mid, Premium.';
EXEC dbo.usp_SetDescription 'Restaurants', 'AvgPrepTimeMins', N'Average time in minutes the kitchen takes to prepare an order (5 to 90).';
EXEC dbo.usp_SetDescription 'Restaurants', 'IsPureVeg',       N'1 = pure vegetarian restaurant (serves no meat or egg), 0 = serves non-veg items too.';
EXEC dbo.usp_SetDescription 'Restaurants', 'OnboardedDate',   N'Date the restaurant joined the platform.';
EXEC dbo.usp_SetDescription 'Restaurants', 'IsActive',        N'1 = currently accepting orders on the platform, 0 = delisted / closed.';

/* =====================================================================
   RestaurantCuisines
   ===================================================================== */
EXEC dbo.usp_SetDescription 'RestaurantCuisines', NULL,           N'Link table (many-to-many) between Restaurants and Cuisines. One row means "this restaurant serves this cuisine". A restaurant usually has 1 to 3 cuisines.';
EXEC dbo.usp_SetDescription 'RestaurantCuisines', 'RestaurantID', N'The restaurant. Foreign key to Restaurants.RestaurantID. Part of the composite primary key.';
EXEC dbo.usp_SetDescription 'RestaurantCuisines', 'CuisineID',    N'The cuisine served. Foreign key to Cuisines.CuisineID. Part of the composite primary key.';

/* =====================================================================
   MenuItems
   ===================================================================== */
EXEC dbo.usp_SetDescription 'MenuItems', NULL,           N'Dishes on each restaurant''s menu, with their CURRENT price. For what a customer actually paid, use OrderItems.UnitPrice instead.';
EXEC dbo.usp_SetDescription 'MenuItems', 'MenuItemID',   N'Unique ID of the menu item (primary key).';
EXEC dbo.usp_SetDescription 'MenuItems', 'RestaurantID', N'Restaurant that sells this item. Foreign key to Restaurants.RestaurantID.';
EXEC dbo.usp_SetDescription 'MenuItems', 'ItemName',     N'Name of the dish, e.g. Chicken Biryani, Masala Dosa, Paneer Butter Masala.';
EXEC dbo.usp_SetDescription 'MenuItems', 'Category',     N'Menu section. Allowed values: Starter, Main Course, Dessert, Beverage, Combo.';
EXEC dbo.usp_SetDescription 'MenuItems', 'Price',        N'Current menu price of one unit, in INR (Indian Rupees).';
EXEC dbo.usp_SetDescription 'MenuItems', 'IsVeg',        N'1 = vegetarian dish, 0 = non-vegetarian (contains meat, fish or egg).';
EXEC dbo.usp_SetDescription 'MenuItems', 'IsAvailable',  N'1 = can be ordered right now, 0 = temporarily unavailable / out of stock.';

/* =====================================================================
   Customers
   ===================================================================== */
EXEC dbo.usp_SetDescription 'Customers', NULL,              N'People who order food on the platform. A customer''s city is found via Customers.AreaID -> Areas -> Cities. A customer who signed up but never ordered has no rows in Orders.';
EXEC dbo.usp_SetDescription 'Customers', 'CustomerID',      N'Unique ID of the customer (primary key).';
EXEC dbo.usp_SetDescription 'Customers', 'FullName',        N'Customer''s full name.';
EXEC dbo.usp_SetDescription 'Customers', 'Email',           N'Customer''s email address. Unique.';
EXEC dbo.usp_SetDescription 'Customers', 'Phone',           N'Customer''s 10-digit Indian mobile number.';
EXEC dbo.usp_SetDescription 'Customers', 'AreaID',          N'Customer''s home / default delivery area. Foreign key to Areas.AreaID. Orders are delivered to this area.';
EXEC dbo.usp_SetDescription 'Customers', 'SignupDate',      N'Date the customer created their account.';
EXEC dbo.usp_SetDescription 'Customers', 'IsPremiumMember', N'1 = paid premium subscription member (gets free/cheaper delivery), 0 = regular customer.';

/* =====================================================================
   DeliveryPartners
   ===================================================================== */
EXEC dbo.usp_SetDescription 'DeliveryPartners', NULL,          N'Delivery riders who pick up food from restaurants and deliver it to customers. Each rider works in one city. Their performance is measured from Orders (PickupDateTime, DeliveredDateTime) and Ratings.DeliveryRating.';
EXEC dbo.usp_SetDescription 'DeliveryPartners', 'PartnerID',   N'Unique ID of the delivery partner (primary key).';
EXEC dbo.usp_SetDescription 'DeliveryPartners', 'FullName',    N'Delivery partner''s full name.';
EXEC dbo.usp_SetDescription 'DeliveryPartners', 'CityID',      N'City the partner works in. Foreign key to Cities.CityID.';
EXEC dbo.usp_SetDescription 'DeliveryPartners', 'VehicleType', N'Vehicle used for deliveries. Allowed values: Bike, Scooter, Bicycle, EV (electric vehicle).';
EXEC dbo.usp_SetDescription 'DeliveryPartners', 'JoinDate',    N'Date the partner started delivering on the platform.';
EXEC dbo.usp_SetDescription 'DeliveryPartners', 'IsActive',    N'1 = currently active rider, 0 = has left / deactivated.';

/* =====================================================================
   Coupons
   ===================================================================== */
EXEC dbo.usp_SetDescription 'Coupons', NULL,            N'Discount coupon codes run by the marketing team, e.g. WELCOME50, WEEKEND100. Orders that used a coupon have Orders.CouponID set.';
EXEC dbo.usp_SetDescription 'Coupons', 'CouponID',      N'Unique ID of the coupon (primary key).';
EXEC dbo.usp_SetDescription 'Coupons', 'CouponCode',    N'Code the customer types at checkout, e.g. WELCOME50, WEEKEND100. Unique, upper case.';
EXEC dbo.usp_SetDescription 'Coupons', 'DiscountType',  N'How the discount is calculated. Allowed values: Percent (a percentage of the item total) or Flat (a fixed INR amount).';
EXEC dbo.usp_SetDescription 'Coupons', 'DiscountValue', N'Size of the discount: a percentage (e.g. 50 means 50%) when DiscountType = Percent, or an amount in INR when DiscountType = Flat.';
EXEC dbo.usp_SetDescription 'Coupons', 'MaxDiscount',   N'Maximum discount in INR for Percent coupons (e.g. 50% off up to INR 100). NULL means no cap.';
EXEC dbo.usp_SetDescription 'Coupons', 'MinOrderValue', N'Minimum item total in INR required to use the coupon. 0 means no minimum.';
EXEC dbo.usp_SetDescription 'Coupons', 'ValidFrom',     N'First date the coupon can be used (inclusive).';
EXEC dbo.usp_SetDescription 'Coupons', 'ValidTo',       N'Last date the coupon can be used (inclusive).';
EXEC dbo.usp_SetDescription 'Coupons', 'IsNewUserOnly', N'1 = only valid on a customer''s first order (new-user acquisition coupon), 0 = any customer.';

/* =====================================================================
   Orders
   ===================================================================== */
EXEC dbo.usp_SetDescription 'Orders', NULL,                 N'One row per food order placed by a customer at a restaurant. The central fact table. Revenue questions normally count only Status = ''Delivered'' orders. The items are in OrderItems, the payment in Payments (1 per order), and the rating in Ratings (0 or 1 per order).';
EXEC dbo.usp_SetDescription 'Orders', 'OrderID',            N'Unique ID of the order (primary key).';
EXEC dbo.usp_SetDescription 'Orders', 'CustomerID',         N'Customer who placed the order. Foreign key to Customers.CustomerID.';
EXEC dbo.usp_SetDescription 'Orders', 'RestaurantID',       N'Restaurant the order was placed at. Foreign key to Restaurants.RestaurantID. The order''s city is the restaurant''s city (Restaurants -> Areas -> Cities).';
EXEC dbo.usp_SetDescription 'Orders', 'PartnerID',          N'Delivery partner assigned to the order. Foreign key to DeliveryPartners.PartnerID. NULL if the order was cancelled before a rider was assigned. Always set for Delivered orders.';
EXEC dbo.usp_SetDescription 'Orders', 'CouponID',           N'Coupon applied to the order. Foreign key to Coupons.CouponID. NULL means no coupon was used.';
EXEC dbo.usp_SetDescription 'Orders', 'OrderDateTime',      N'Date and time the customer placed the order (local Indian time, IST). Use this for "orders per day / month / hour" questions.';
EXEC dbo.usp_SetDescription 'Orders', 'Status',             N'Final order status. Allowed values: Delivered (completed successfully), Cancelled (cancelled by customer or restaurant), Failed (payment or delivery failed).';
EXEC dbo.usp_SetDescription 'Orders', 'CancellationReason', N'Why the order was not delivered, e.g. ''Restaurant took too long'', ''Item out of stock'', ''Payment failed''. Filled for Cancelled and Failed orders; NULL for Delivered orders.';
EXEC dbo.usp_SetDescription 'Orders', 'ItemTotal',          N'Sum of the food items in INR before fees and discounts. Equals SUM(OrderItems.Quantity * OrderItems.UnitPrice) for this order.';
EXEC dbo.usp_SetDescription 'Orders', 'DeliveryFee',        N'Delivery charge in INR paid by the customer. Often 0 for premium members.';
EXEC dbo.usp_SetDescription 'Orders', 'DiscountAmount',     N'Coupon discount in INR deducted from the bill. 0 if no coupon was used.';
EXEC dbo.usp_SetDescription 'Orders', 'TotalAmount',        N'Final bill in INR paid by the customer. Always equals ItemTotal + DeliveryFee - DiscountAmount. Use this column for revenue / GMV.';
EXEC dbo.usp_SetDescription 'Orders', 'DeliveryDistanceKm', N'Distance in kilometres from the restaurant to the customer.';
EXEC dbo.usp_SetDescription 'Orders', 'PickupDateTime',     N'Date and time the delivery partner picked up the food from the restaurant. NULL if never picked up. Food preparation time = DATEDIFF(MINUTE, OrderDateTime, PickupDateTime).';
EXEC dbo.usp_SetDescription 'Orders', 'DeliveredDateTime',  N'Date and time the food reached the customer. Only set for Delivered orders. Total delivery time in minutes = DATEDIFF(MINUTE, OrderDateTime, DeliveredDateTime); rider travel time = DATEDIFF(MINUTE, PickupDateTime, DeliveredDateTime).';

/* =====================================================================
   OrderItems
   ===================================================================== */
EXEC dbo.usp_SetDescription 'OrderItems', NULL,          N'Line items of each order: which dishes were ordered and how many. An order has 1 to 4 line items. Use this table for "most ordered dish" questions.';
EXEC dbo.usp_SetDescription 'OrderItems', 'OrderItemID', N'Unique ID of the order line (primary key).';
EXEC dbo.usp_SetDescription 'OrderItems', 'OrderID',     N'Order this line belongs to. Foreign key to Orders.OrderID.';
EXEC dbo.usp_SetDescription 'OrderItems', 'MenuItemID',  N'Dish that was ordered. Foreign key to MenuItems.MenuItemID.';
EXEC dbo.usp_SetDescription 'OrderItems', 'Quantity',    N'Number of units of this dish in the order (1 to 20).';
EXEC dbo.usp_SetDescription 'OrderItems', 'UnitPrice',   N'Price of one unit in INR at the time of ordering. Line amount = Quantity * UnitPrice.';

/* =====================================================================
   Payments
   ===================================================================== */
EXEC dbo.usp_SetDescription 'Payments', NULL,              N'Payment record for each order (exactly one per order). Delivered orders have Success payments; Cancelled orders have Refunded or Failed payments.';
EXEC dbo.usp_SetDescription 'Payments', 'PaymentID',       N'Unique ID of the payment (primary key).';
EXEC dbo.usp_SetDescription 'Payments', 'OrderID',         N'Order being paid for. Foreign key to Orders.OrderID. Unique (one payment per order).';
EXEC dbo.usp_SetDescription 'Payments', 'PaymentMethod',   N'How the customer paid. Allowed values: UPI, Card, Wallet, COD (cash on delivery), NetBanking.';
EXEC dbo.usp_SetDescription 'Payments', 'PaymentStatus',   N'Outcome of the payment. Allowed values: Success (money received), Failed (payment did not go through), Refunded (money returned to customer, e.g. after cancellation).';
EXEC dbo.usp_SetDescription 'Payments', 'PaidAmount',      N'Amount in INR charged to the customer. Equals Orders.TotalAmount when successful or refunded; 0 when the payment failed.';
EXEC dbo.usp_SetDescription 'Payments', 'PaymentDateTime', N'Date and time the payment was attempted.';

/* =====================================================================
   Ratings
   ===================================================================== */
EXEC dbo.usp_SetDescription 'Ratings', NULL,             N'Customer ratings for delivered orders (at most one per order; not every order is rated). Use FoodRating to judge restaurants and DeliveryRating to judge delivery partners.';
EXEC dbo.usp_SetDescription 'Ratings', 'RatingID',       N'Unique ID of the rating (primary key).';
EXEC dbo.usp_SetDescription 'Ratings', 'OrderID',        N'Order being rated. Foreign key to Orders.OrderID. Unique (one rating per order).';
EXEC dbo.usp_SetDescription 'Ratings', 'FoodRating',     N'Customer''s rating of the food, from 1 (very poor) to 5 (excellent). Reflects the restaurant.';
EXEC dbo.usp_SetDescription 'Ratings', 'DeliveryRating', N'Customer''s rating of the delivery, from 1 (very poor) to 5 (excellent). Reflects the delivery partner.';
EXEC dbo.usp_SetDescription 'Ratings', 'ReviewText',     N'Optional written review by the customer. NULL if they only gave star ratings.';
EXEC dbo.usp_SetDescription 'Ratings', 'RatedDateTime',  N'Date and time the customer submitted the rating (after delivery).';
GO

/* ---------------------------------------------------------------------
   Safety net: list any table or column still missing a description.
   This query should return ZERO rows.
   --------------------------------------------------------------------- */
SELECT c.TABLE_NAME, c.COLUMN_NAME AS MissingDescriptionFor
FROM INFORMATION_SCHEMA.COLUMNS AS c
LEFT JOIN sys.extended_properties AS ep
       ON ep.major_id = OBJECT_ID(c.TABLE_SCHEMA + '.' + c.TABLE_NAME)
      AND ep.minor_id = COLUMNPROPERTY(OBJECT_ID(c.TABLE_SCHEMA + '.' + c.TABLE_NAME), c.COLUMN_NAME, 'ColumnId')
      AND ep.name     = 'MS_Description'
WHERE ep.major_id IS NULL
UNION ALL
SELECT t.TABLE_NAME, '(table itself)'
FROM INFORMATION_SCHEMA.TABLES AS t
LEFT JOIN sys.extended_properties AS ep
       ON ep.major_id = OBJECT_ID(t.TABLE_SCHEMA + '.' + t.TABLE_NAME)
      AND ep.minor_id = 0
      AND ep.name     = 'MS_Description'
WHERE t.TABLE_TYPE = 'BASE TABLE'
  AND ep.major_id IS NULL;
GO

DROP PROCEDURE IF EXISTS dbo.usp_SetDescription;
GO

PRINT 'Descriptions added. The result grid above should be EMPTY (no missing descriptions).';
GO
