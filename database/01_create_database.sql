/* =====================================================================
   01_create_database.sql
   Creates the FoodDeliveryDB database for the SQL Agent demo.

   !!! WARNING !!!
   If a database named FoodDeliveryDB already exists, this script DROPS it
   and ALL of its data. Every open connection to it is forcibly closed.
   Only run this on your local demo machine.

   Run as: a sysadmin login (e.g. your Windows login in SSMS).
   ===================================================================== */

USE master;
GO

IF DB_ID(N'FoodDeliveryDB') IS NOT NULL
BEGIN
    PRINT 'FoodDeliveryDB exists - dropping it (all data will be lost)...';

    -- SINGLE_USER + ROLLBACK IMMEDIATE kicks out other sessions
    -- (e.g. an open SSMS query window), otherwise DROP DATABASE would fail.
    ALTER DATABASE FoodDeliveryDB SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE FoodDeliveryDB;
END
GO

CREATE DATABASE FoodDeliveryDB;
GO

-- SIMPLE recovery: we don't need point-in-time restore for a demo, and it
-- stops the transaction log from growing huge while we bulk-insert ~80k orders.
ALTER DATABASE FoodDeliveryDB SET RECOVERY SIMPLE;
GO

PRINT 'FoodDeliveryDB created successfully.';
GO
