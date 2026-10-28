/* =====================================================================
   04_create_readonly_user.sql
   Creates the SQL login + database user that the SQL Agent connects with.

   WHY: this is guardrail #3 (the last line of defence). Even if a bad
   query somehow got past the prompt rules AND the sqlglot validator, this
   login is physically unable to change data or the schema.

   BEFORE RUNNING:
     1. Replace <<REPLACE_WITH_STRONG_PASSWORD>> below with a real password
        (at least 8 characters, upper + lower case, a digit and a symbol).
        Put the SAME password in your .env file as DB_READONLY_PASSWORD.
        Do NOT commit the edited file with your real password.
     2. SQL Server must allow "SQL Server and Windows Authentication mode"
        (mixed mode). See database/README.md for how to enable it.

   Run after: 03_add_descriptions.sql
   Re-runnable: yes - the user and login are dropped and recreated.
   ===================================================================== */

USE master;
GO

/* ---------------------------------------------------------------------
   1. Server-level LOGIN (lets you connect to the SQL Server instance)
   --------------------------------------------------------------------- */

-- Drop the database user first, otherwise the login can't be dropped cleanly.
IF DB_ID(N'FoodDeliveryDB') IS NOT NULL
   AND EXISTS (SELECT 1 FROM FoodDeliveryDB.sys.database_principals WHERE name = N'sql_agent_reader')
BEGIN
    EXEC (N'USE FoodDeliveryDB; DROP USER sql_agent_reader;');
END
GO

IF EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'sql_agent_reader')
    DROP LOGIN sql_agent_reader;
GO

CREATE LOGIN sql_agent_reader
    WITH PASSWORD         = N'Madhulika',
         DEFAULT_DATABASE = FoodDeliveryDB,
         CHECK_POLICY     = ON,    -- enforce the Windows password policy
         CHECK_EXPIRATION = OFF;   -- a service account shouldn't expire mid-demo
GO

/* ---------------------------------------------------------------------
   2. Database USER (lets the login inside FoodDeliveryDB)
   --------------------------------------------------------------------- */
USE FoodDeliveryDB;
GO

CREATE USER sql_agent_reader FOR LOGIN sql_agent_reader WITH DEFAULT_SCHEMA = dbo;
GO

-- db_datareader = SELECT on every table in the database. Nothing more.
ALTER ROLE db_datareader ADD MEMBER sql_agent_reader;
GO

-- Lets the agent read table/column metadata, foreign keys and the
-- MS_Description extended properties so it can describe the schema to the LLM.
-- This is read-only metadata access; it does NOT allow changing anything.
GRANT VIEW DEFINITION TO sql_agent_reader;
GO

/* ---------------------------------------------------------------------
   3. Explicit DENYs (belt and braces)
   db_datareader alone already can't write, but a DENY always wins over
   any GRANT - so even if someone later adds this user to another role by
   mistake (e.g. db_datawriter), these actions stay blocked.
   --------------------------------------------------------------------- */
DENY INSERT, UPDATE, DELETE, ALTER, EXECUTE TO sql_agent_reader;
GO

-- Also block creating new objects (tables, views, procedures, functions).
DENY CREATE TABLE, CREATE VIEW, CREATE PROCEDURE, CREATE FUNCTION TO sql_agent_reader;
GO

PRINT 'Login and user sql_agent_reader created with read-only access.';
GO

/* ---------------------------------------------------------------------
   4. Quick self-test - impersonate the new user and check permissions.
   --------------------------------------------------------------------- */
EXECUTE AS USER = N'sql_agent_reader';

    -- Expect: SELECT = 1, INSERT/UPDATE/DELETE = 0
    SELECT
        HAS_PERMS_BY_NAME(N'dbo.Orders', N'OBJECT', N'SELECT') AS CanSelect,
        HAS_PERMS_BY_NAME(N'dbo.Orders', N'OBJECT', N'INSERT') AS CanInsert,
        HAS_PERMS_BY_NAME(N'dbo.Orders', N'OBJECT', N'UPDATE') AS CanUpdate,
        HAS_PERMS_BY_NAME(N'dbo.Orders', N'OBJECT', N'DELETE') AS CanDelete;

REVERT;
GO
