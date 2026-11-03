-- Creates the application database and the test database (idempotent).
-- Run in SSMS or:  sqlcmd -S localhost\BANG -E -i scripts\create_db.sql
-- Tables are created by Alembic (cd backend; alembic upgrade head), not by this script.

IF DB_ID(N'DevTeamAI') IS NULL
    CREATE DATABASE [DevTeamAI];
GO

IF DB_ID(N'DevTeamAI_Test') IS NULL
    CREATE DATABASE [DevTeamAI_Test];
GO

-- Optional: dedicated SQL login (only when DB_TRUSTED_CONNECTION=false).
-- Replace the password, then uncomment.
-- CREATE LOGIN [devteam_app] WITH PASSWORD = N'<strong-password>', CHECK_POLICY = ON;
-- USE [DevTeamAI];      CREATE USER [devteam_app] FOR LOGIN [devteam_app]; ALTER ROLE db_owner ADD MEMBER [devteam_app];
-- USE [DevTeamAI_Test]; CREATE USER [devteam_app] FOR LOGIN [devteam_app]; ALTER ROLE db_owner ADD MEMBER [devteam_app];
-- GO
