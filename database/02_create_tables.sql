/* =====================================================================
   02_create_tables.sql
   Creates all 13 tables of FoodDeliveryDB with primary keys, foreign
   keys, CHECK constraints, defaults and indexes.

   Run after: 01_create_database.sql
   Re-runnable: yes - it drops the tables first (children before parents).

   Conventions used throughout:
     - Every table has an INT IDENTITY primary key named <Entity>ID
       (except RestaurantCuisines, a pure link table).
     - Money is DECIMAL(10,2) in Indian Rupees (INR).
     - Date-times are DATETIME2(0) (precision to the second, no ms noise).
     - Yes/No flags are BIT (1 = yes, 0 = no).
     - Constraint names follow PK_/FK_/UQ_/CK_/DF_/IX_ prefixes so error
       messages tell you exactly which rule was broken.
   ===================================================================== */

USE FoodDeliveryDB;
GO

-- Filtered indexes (see IX_Orders_CouponID at the bottom) require these
-- settings. SSMS turns them on by default, but sqlcmd and some other tools
-- don't, so we set them explicitly to make the script work from anywhere.
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

/* ---------------------------------------------------------------------
   Drop existing tables in reverse dependency order.
   A child table (one with a FOREIGN KEY) must be dropped before the
   parent it points to, otherwise SQL Server refuses.
   --------------------------------------------------------------------- */
DROP TABLE IF EXISTS dbo.Ratings;
DROP TABLE IF EXISTS dbo.Payments;
DROP TABLE IF EXISTS dbo.OrderItems;
DROP TABLE IF EXISTS dbo.Orders;
DROP TABLE IF EXISTS dbo.Coupons;
DROP TABLE IF EXISTS dbo.DeliveryPartners;
DROP TABLE IF EXISTS dbo.Customers;
DROP TABLE IF EXISTS dbo.MenuItems;
DROP TABLE IF EXISTS dbo.RestaurantCuisines;
DROP TABLE IF EXISTS dbo.Restaurants;
DROP TABLE IF EXISTS dbo.Cuisines;
DROP TABLE IF EXISTS dbo.Areas;
DROP TABLE IF EXISTS dbo.Cities;
GO

/* =====================================================================
   LOCATION TABLES
   ===================================================================== */

CREATE TABLE dbo.Cities (
    CityID      INT IDENTITY(1,1) NOT NULL,
    CityName    NVARCHAR(50)      NOT NULL,
    State       NVARCHAR(50)      NOT NULL,
    LaunchDate  DATE              NOT NULL,   -- when the platform started operating here

    CONSTRAINT PK_Cities          PRIMARY KEY (CityID),
    CONSTRAINT UQ_Cities_CityName UNIQUE (CityName)
);
GO

CREATE TABLE dbo.Areas (
    AreaID      INT IDENTITY(1,1) NOT NULL,
    CityID      INT               NOT NULL,
    AreaName    NVARCHAR(100)     NOT NULL,
    Pincode     CHAR(6)           NOT NULL,

    CONSTRAINT PK_Areas          PRIMARY KEY (AreaID),
    CONSTRAINT FK_Areas_Cities   FOREIGN KEY (CityID) REFERENCES dbo.Cities (CityID),
    -- The same area name can exist in two cities, but not twice in one city.
    CONSTRAINT UQ_Areas_CityArea UNIQUE (CityID, AreaName),
    -- Indian PIN codes are exactly 6 digits and never start with 0.
    CONSTRAINT CK_Areas_Pincode  CHECK (Pincode LIKE '[1-9][0-9][0-9][0-9][0-9][0-9]')
);
GO

/* =====================================================================
   RESTAURANT TABLES
   ===================================================================== */

CREATE TABLE dbo.Cuisines (
    CuisineID   INT IDENTITY(1,1) NOT NULL,
    CuisineName NVARCHAR(50)      NOT NULL,

    CONSTRAINT PK_Cuisines             PRIMARY KEY (CuisineID),
    CONSTRAINT UQ_Cuisines_CuisineName UNIQUE (CuisineName)
);
GO

CREATE TABLE dbo.Restaurants (
    RestaurantID     INT IDENTITY(1,1) NOT NULL,
    AreaID           INT               NOT NULL,
    RestaurantName   NVARCHAR(150)     NOT NULL,
    PriceRange       VARCHAR(10)       NOT NULL,
    AvgPrepTimeMins  SMALLINT          NOT NULL,
    IsPureVeg        BIT               NOT NULL CONSTRAINT DF_Restaurants_IsPureVeg DEFAULT (0),
    OnboardedDate    DATE              NOT NULL,
    IsActive         BIT               NOT NULL CONSTRAINT DF_Restaurants_IsActive  DEFAULT (1),

    CONSTRAINT PK_Restaurants            PRIMARY KEY (RestaurantID),
    CONSTRAINT FK_Restaurants_Areas      FOREIGN KEY (AreaID) REFERENCES dbo.Areas (AreaID),
    CONSTRAINT CK_Restaurants_PriceRange CHECK (PriceRange IN ('Budget', 'Mid', 'Premium')),
    CONSTRAINT CK_Restaurants_PrepTime   CHECK (AvgPrepTimeMins BETWEEN 5 AND 90)
);
GO

-- Many-to-many link: one restaurant serves many cuisines,
-- one cuisine is served by many restaurants.
CREATE TABLE dbo.RestaurantCuisines (
    RestaurantID INT NOT NULL,
    CuisineID    INT NOT NULL,

    -- Composite primary key = a restaurant can't list the same cuisine twice.
    CONSTRAINT PK_RestaurantCuisines             PRIMARY KEY (RestaurantID, CuisineID),
    CONSTRAINT FK_RestaurantCuisines_Restaurants FOREIGN KEY (RestaurantID) REFERENCES dbo.Restaurants (RestaurantID),
    CONSTRAINT FK_RestaurantCuisines_Cuisines    FOREIGN KEY (CuisineID)    REFERENCES dbo.Cuisines (CuisineID)
);
GO

CREATE TABLE dbo.MenuItems (
    MenuItemID   INT IDENTITY(1,1) NOT NULL,
    RestaurantID INT               NOT NULL,
    ItemName     NVARCHAR(150)     NOT NULL,
    Category     VARCHAR(20)       NOT NULL,
    Price        DECIMAL(10,2)     NOT NULL,   -- current menu price in INR
    IsVeg        BIT               NOT NULL,
    IsAvailable  BIT               NOT NULL CONSTRAINT DF_MenuItems_IsAvailable DEFAULT (1),

    CONSTRAINT PK_MenuItems             PRIMARY KEY (MenuItemID),
    CONSTRAINT FK_MenuItems_Restaurants FOREIGN KEY (RestaurantID) REFERENCES dbo.Restaurants (RestaurantID),
    CONSTRAINT CK_MenuItems_Category    CHECK (Category IN ('Starter', 'Main Course', 'Dessert', 'Beverage', 'Combo')),
    CONSTRAINT CK_MenuItems_Price       CHECK (Price > 0)
);
GO

/* =====================================================================
   PEOPLE TABLES
   ===================================================================== */

CREATE TABLE dbo.Customers (
    CustomerID      INT IDENTITY(1,1) NOT NULL,
    FullName        NVARCHAR(100)     NOT NULL,
    Email           VARCHAR(150)      NOT NULL,
    Phone           VARCHAR(15)       NOT NULL,
    AreaID          INT               NOT NULL,   -- home / default delivery area
    SignupDate      DATE              NOT NULL,
    IsPremiumMember BIT               NOT NULL CONSTRAINT DF_Customers_IsPremiumMember DEFAULT (0),

    CONSTRAINT PK_Customers       PRIMARY KEY (CustomerID),
    CONSTRAINT FK_Customers_Areas FOREIGN KEY (AreaID) REFERENCES dbo.Areas (AreaID),
    CONSTRAINT UQ_Customers_Email UNIQUE (Email)
);
GO

CREATE TABLE dbo.DeliveryPartners (
    PartnerID   INT IDENTITY(1,1) NOT NULL,
    FullName    NVARCHAR(100)     NOT NULL,
    CityID      INT               NOT NULL,
    VehicleType VARCHAR(10)       NOT NULL,
    JoinDate    DATE              NOT NULL,
    IsActive    BIT               NOT NULL CONSTRAINT DF_DeliveryPartners_IsActive DEFAULT (1),

    CONSTRAINT PK_DeliveryPartners             PRIMARY KEY (PartnerID),
    CONSTRAINT FK_DeliveryPartners_Cities      FOREIGN KEY (CityID) REFERENCES dbo.Cities (CityID),
    CONSTRAINT CK_DeliveryPartners_VehicleType CHECK (VehicleType IN ('Bike', 'Scooter', 'Bicycle', 'EV'))
);
GO

/* =====================================================================
   MARKETING TABLE
   ===================================================================== */

CREATE TABLE dbo.Coupons (
    CouponID      INT IDENTITY(1,1) NOT NULL,
    CouponCode    VARCHAR(20)       NOT NULL,
    DiscountType  VARCHAR(10)       NOT NULL,
    DiscountValue DECIMAL(10,2)     NOT NULL,   -- a percentage (e.g. 50 = 50%) OR a flat INR amount
    MaxDiscount   DECIMAL(10,2)     NULL,       -- cap in INR for Percent coupons; NULL = no cap
    MinOrderValue DECIMAL(10,2)     NOT NULL CONSTRAINT DF_Coupons_MinOrderValue DEFAULT (0),
    ValidFrom     DATE              NOT NULL,
    ValidTo       DATE              NOT NULL,
    IsNewUserOnly BIT               NOT NULL CONSTRAINT DF_Coupons_IsNewUserOnly DEFAULT (0),

    CONSTRAINT PK_Coupons              PRIMARY KEY (CouponID),
    CONSTRAINT UQ_Coupons_CouponCode   UNIQUE (CouponCode),
    CONSTRAINT CK_Coupons_DiscountType CHECK (DiscountType IN ('Percent', 'Flat')),
    -- A percentage discount can't be more than 100%.
    CONSTRAINT CK_Coupons_DiscountValue CHECK (DiscountValue > 0 AND (DiscountType = 'Flat' OR DiscountValue <= 100)),
    CONSTRAINT CK_Coupons_MinOrderValue CHECK (MinOrderValue >= 0),
    CONSTRAINT CK_Coupons_ValidDates    CHECK (ValidTo >= ValidFrom)
);
GO

/* =====================================================================
   TRANSACTION TABLES
   ===================================================================== */

CREATE TABLE dbo.Orders (
    OrderID            INT IDENTITY(1,1) NOT NULL,
    CustomerID         INT               NOT NULL,
    RestaurantID       INT               NOT NULL,
    PartnerID          INT               NULL,       -- NULL if cancelled before a rider was assigned
    CouponID           INT               NULL,       -- NULL if no coupon was applied
    OrderDateTime      DATETIME2(0)      NOT NULL,
    Status             VARCHAR(10)       NOT NULL,
    CancellationReason NVARCHAR(200)     NULL,       -- reason for Cancelled AND Failed orders
    ItemTotal          DECIMAL(10,2)     NOT NULL,   -- SUM(Quantity * UnitPrice) of the order's items
    DeliveryFee        DECIMAL(10,2)     NOT NULL CONSTRAINT DF_Orders_DeliveryFee    DEFAULT (0),
    DiscountAmount     DECIMAL(10,2)     NOT NULL CONSTRAINT DF_Orders_DiscountAmount DEFAULT (0),
    TotalAmount        DECIMAL(10,2)     NOT NULL,   -- what the customer pays
    DeliveryDistanceKm DECIMAL(5,2)      NOT NULL,
    PickupDateTime     DATETIME2(0)      NULL,       -- when the rider collected the food
    DeliveredDateTime  DATETIME2(0)      NULL,       -- when the food reached the customer

    CONSTRAINT PK_Orders                  PRIMARY KEY (OrderID),
    CONSTRAINT FK_Orders_Customers        FOREIGN KEY (CustomerID)   REFERENCES dbo.Customers (CustomerID),
    CONSTRAINT FK_Orders_Restaurants      FOREIGN KEY (RestaurantID) REFERENCES dbo.Restaurants (RestaurantID),
    CONSTRAINT FK_Orders_DeliveryPartners FOREIGN KEY (PartnerID)    REFERENCES dbo.DeliveryPartners (PartnerID),
    CONSTRAINT FK_Orders_Coupons          FOREIGN KEY (CouponID)     REFERENCES dbo.Coupons (CouponID),

    CONSTRAINT CK_Orders_Status   CHECK (Status IN ('Delivered', 'Cancelled', 'Failed')),
    CONSTRAINT CK_Orders_Amounts  CHECK (ItemTotal > 0 AND DeliveryFee >= 0
                                         AND DiscountAmount >= 0 AND DiscountAmount <= ItemTotal),
    -- The bill must always add up. Putting this rule in the database means
    -- the agent (and humans) can trust TotalAmount without recomputing it.
    CONSTRAINT CK_Orders_TotalMath CHECK (TotalAmount = ItemTotal + DeliveryFee - DiscountAmount),
    CONSTRAINT CK_Orders_Distance  CHECK (DeliveryDistanceKm > 0 AND DeliveryDistanceKm <= 30),

    -- Timeline must move forward: Order -> Pickup -> Delivered.
    CONSTRAINT CK_Orders_PickupAfterOrder     CHECK (PickupDateTime IS NULL OR PickupDateTime > OrderDateTime),
    CONSTRAINT CK_Orders_DeliveredAfterPickup CHECK (DeliveredDateTime IS NULL
                                                     OR (PickupDateTime IS NOT NULL AND DeliveredDateTime > PickupDateTime)),

    -- A Delivered order must have a rider and both timestamps, and no reason.
    CONSTRAINT CK_Orders_DeliveredComplete CHECK (Status <> 'Delivered'
                                                  OR (PartnerID IS NOT NULL
                                                      AND PickupDateTime IS NOT NULL
                                                      AND DeliveredDateTime IS NOT NULL
                                                      AND CancellationReason IS NULL)),
    -- A Cancelled/Failed order must explain why, and was never delivered.
    CONSTRAINT CK_Orders_NotDeliveredReason CHECK (Status = 'Delivered'
                                                   OR (CancellationReason IS NOT NULL AND DeliveredDateTime IS NULL))
);
GO

CREATE TABLE dbo.OrderItems (
    OrderItemID INT IDENTITY(1,1) NOT NULL,
    OrderID     INT               NOT NULL,
    MenuItemID  INT               NOT NULL,
    Quantity    SMALLINT          NOT NULL,
    -- Price at the moment of ordering. Stored separately from MenuItems.Price
    -- because menu prices change over time but old bills must not.
    UnitPrice   DECIMAL(10,2)     NOT NULL,

    CONSTRAINT PK_OrderItems           PRIMARY KEY (OrderItemID),
    CONSTRAINT FK_OrderItems_Orders    FOREIGN KEY (OrderID)    REFERENCES dbo.Orders (OrderID),
    CONSTRAINT FK_OrderItems_MenuItems FOREIGN KEY (MenuItemID) REFERENCES dbo.MenuItems (MenuItemID),
    -- Same dish twice in one order is stored as Quantity = 2, not two rows.
    CONSTRAINT UQ_OrderItems_OrderMenu UNIQUE (OrderID, MenuItemID),
    CONSTRAINT CK_OrderItems_Quantity  CHECK (Quantity BETWEEN 1 AND 20),
    CONSTRAINT CK_OrderItems_UnitPrice CHECK (UnitPrice > 0)
);
GO

CREATE TABLE dbo.Payments (
    PaymentID       INT IDENTITY(1,1) NOT NULL,
    OrderID         INT               NOT NULL,
    PaymentMethod   VARCHAR(15)       NOT NULL,
    PaymentStatus   VARCHAR(10)       NOT NULL,
    PaidAmount      DECIMAL(10,2)     NOT NULL,
    PaymentDateTime DATETIME2(0)      NOT NULL,

    CONSTRAINT PK_Payments        PRIMARY KEY (PaymentID),
    CONSTRAINT FK_Payments_Orders FOREIGN KEY (OrderID) REFERENCES dbo.Orders (OrderID),
    -- Exactly one payment record per order (1:1 relationship).
    CONSTRAINT UQ_Payments_OrderID       UNIQUE (OrderID),
    CONSTRAINT CK_Payments_PaymentMethod CHECK (PaymentMethod IN ('UPI', 'Card', 'Wallet', 'COD', 'NetBanking')),
    CONSTRAINT CK_Payments_PaymentStatus CHECK (PaymentStatus IN ('Success', 'Failed', 'Refunded')),
    CONSTRAINT CK_Payments_PaidAmount    CHECK (PaidAmount >= 0)
);
GO

CREATE TABLE dbo.Ratings (
    RatingID       INT IDENTITY(1,1) NOT NULL,
    OrderID        INT               NOT NULL,
    FoodRating     TINYINT           NOT NULL,
    DeliveryRating TINYINT           NOT NULL,
    ReviewText     NVARCHAR(500)     NULL,
    RatedDateTime  DATETIME2(0)      NOT NULL,

    CONSTRAINT PK_Ratings        PRIMARY KEY (RatingID),
    CONSTRAINT FK_Ratings_Orders FOREIGN KEY (OrderID) REFERENCES dbo.Orders (OrderID),
    -- A customer can rate an order at most once.
    CONSTRAINT UQ_Ratings_OrderID        UNIQUE (OrderID),
    CONSTRAINT CK_Ratings_FoodRating     CHECK (FoodRating BETWEEN 1 AND 5),
    CONSTRAINT CK_Ratings_DeliveryRating CHECK (DeliveryRating BETWEEN 1 AND 5)
);
GO

/* =====================================================================
   INDEXES
   SQL Server automatically indexes PRIMARY KEY and UNIQUE columns, but
   NOT foreign key columns. We add indexes on the columns that business
   questions filter, join or group by most often.
   ===================================================================== */

-- Foreign-key columns (speed up JOINs).
CREATE INDEX IX_Areas_CityID               ON dbo.Areas (CityID);
CREATE INDEX IX_Restaurants_AreaID         ON dbo.Restaurants (AreaID);
CREATE INDEX IX_RestaurantCuisines_Cuisine ON dbo.RestaurantCuisines (CuisineID);
CREATE INDEX IX_MenuItems_RestaurantID     ON dbo.MenuItems (RestaurantID);
CREATE INDEX IX_Customers_AreaID           ON dbo.Customers (AreaID);
CREATE INDEX IX_DeliveryPartners_CityID    ON dbo.DeliveryPartners (CityID);
CREATE INDEX IX_OrderItems_OrderID         ON dbo.OrderItems (OrderID);
CREATE INDEX IX_OrderItems_MenuItemID      ON dbo.OrderItems (MenuItemID);

-- Orders is the biggest table and the centre of almost every question.
-- "Orders/revenue by day, month, hour" -> date range scans.
CREATE INDEX IX_Orders_OrderDateTime
    ON dbo.Orders (OrderDateTime)
    INCLUDE (Status, TotalAmount, RestaurantID, CustomerID);

-- "Customer's first/last order", churn, repeat behaviour.
CREATE INDEX IX_Orders_Customer_Date ON dbo.Orders (CustomerID, OrderDateTime);

-- "Cancellation rate per restaurant", restaurant revenue.
CREATE INDEX IX_Orders_Restaurant_Status ON dbo.Orders (RestaurantID, Status);

-- Delivery partner performance.
CREATE INDEX IX_Orders_PartnerID ON dbo.Orders (PartnerID);

-- Coupon analysis. Filtered index: most orders have no coupon,
-- so we only index the rows where one was used (smaller, faster).
CREATE INDEX IX_Orders_CouponID ON dbo.Orders (CouponID) WHERE CouponID IS NOT NULL;
GO

PRINT 'All 13 tables, constraints and indexes created successfully.';
GO
