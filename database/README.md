# Database scripts

These scripts build **FoodDeliveryDB**, the SQL Server database the SQL Agent queries.
Open each file in **SSMS** (connected with your Windows login as an administrator) and run it with **F5** (Execute). Run them in this order:

| # | Script | What it does | Phase |
|---|--------|--------------|-------|
| 1 | `01_create_database.sql` | Drops (if it exists) and creates `FoodDeliveryDB` | 1 |
| 2 | `02_create_tables.sql` | Creates the 13 tables with keys, constraints and indexes | 1 |
| 3 | `03_add_descriptions.sql` | Adds a plain-English description to every table and column | 1 |
| 4 | `04_create_readonly_user.sql` | Creates the read-only login `sql_agent_reader` | 1 |
| – | `python data_generator/seed_data.py` | Fills the tables with realistic data | 2 |
| 5 | `05_verify_data.sql` | Sanity-checks the data and the planted patterns | 2 |

> ⚠️ `01_create_database.sql` **deletes** any existing `FoodDeliveryDB` and all of its data.

---

## Before you start: enable mixed-mode authentication

The agent logs in with a **SQL login** (username + password), not your Windows account. A fresh SQL Server Express install often allows Windows logins only. To check and fix that:

1. In SSMS, right-click the **server** in Object Explorer and choose **Properties**, then **Security**.
2. Under *Server authentication*, select **SQL Server and Windows Authentication mode**, then click **OK**.
3. Restart the service: right-click the server and choose **Restart**. You can also use *SQL Server Configuration Manager*, then **SQL Server Services**, then **SQL Server (SQLEXPRESS)**, then **Restart**.

---

## Step-by-step with verification

### 1. `01_create_database.sql`
**Messages tab should show:** `FoodDeliveryDB created successfully.`
**Verify:** press F5 on Object Explorer, then expand **Databases**. You should see `FoodDeliveryDB`.

```sql
SELECT name, recovery_model_desc FROM sys.databases WHERE name = 'FoodDeliveryDB';
-- Expect 1 row: FoodDeliveryDB | SIMPLE
```

### 2. `02_create_tables.sql`
**Messages tab should show:** `All 13 tables, constraints and indexes created successfully.`
**Verify:**

```sql
USE FoodDeliveryDB;
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME;
-- Expect 13 rows: Areas, Cities, Coupons, Customers, Cuisines, DeliveryPartners,
-- MenuItems, OrderItems, Orders, Payments, Ratings, RestaurantCuisines, Restaurants

SELECT COUNT(*) AS ForeignKeys FROM sys.foreign_keys;        -- Expect 15
SELECT COUNT(*) AS CheckConstraints FROM sys.check_constraints; -- Expect 25
```

Optional: test that a constraint works. The following insert should **fail** with an error that mentions `CK_Restaurants_PriceRange`:

```sql
INSERT INTO dbo.Cities (CityName, State, LaunchDate) VALUES ('Test', 'Test', '2020-01-01');
INSERT INTO dbo.Areas (CityID, AreaName, Pincode) VALUES (SCOPE_IDENTITY(), 'Test', '560001');
INSERT INTO dbo.Restaurants (AreaID, RestaurantName, PriceRange, AvgPrepTimeMins, OnboardedDate)
VALUES (SCOPE_IDENTITY(), 'Test', 'Cheap', 20, '2020-01-01');   -- 'Cheap' is not allowed
-- Clean up afterwards:
DELETE FROM dbo.Areas; DELETE FROM dbo.Cities;
```

### 3. `03_add_descriptions.sql`
**Results grid should be EMPTY.** The script ends with a query that lists anything still missing a description.
**Messages tab should show:** `Descriptions added...`
**Verify:** you can read the descriptions back like this:

```sql
SELECT OBJECT_NAME(major_id) AS TableName,
       COL_NAME(major_id, minor_id) AS ColumnName,   -- NULL = the table itself
       CAST(value AS NVARCHAR(400)) AS Description
FROM sys.extended_properties
WHERE name = 'MS_Description'
ORDER BY TableName, minor_id;
-- Expect 94 rows (13 tables + 81 columns)
```

In SSMS you can also right-click a table, choose **Design**, click a column, and see its *Description* property.

### 4. `04_create_readonly_user.sql`
1. **First** replace `<<REPLACE_WITH_STRONG_PASSWORD>>` with a real password. Use the same one later in `.env`. Don't commit the file with your real password in it.
2. Run it.

**Results grid should show:** `CanSelect = 1, CanInsert = 0, CanUpdate = 0, CanDelete = 0`.

**Verify by logging in as the agent.** In SSMS, choose **File**, then **Connect Object Explorer…**, and enter:
- Authentication: **SQL Server Authentication**
- Login: `sql_agent_reader`, Password: *(yours)*
- Options, then Connection Properties: tick **Trust server certificate**

Open a new query on that connection and run:

```sql
USE FoodDeliveryDB;
SELECT TOP 5 * FROM dbo.Cities;                       -- works (empty until Phase 2)
INSERT INTO dbo.Cuisines (CuisineName) VALUES ('X');   -- FAILS: "The INSERT permission was denied..."
DROP TABLE dbo.Ratings;                                -- FAILS: permission denied
```

If you see `Login failed for user 'sql_agent_reader'`, mixed-mode authentication is not enabled yet. See the section at the top.
