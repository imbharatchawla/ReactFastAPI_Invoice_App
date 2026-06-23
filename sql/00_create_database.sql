-- Run as a PostgreSQL superuser if you want to create DB/user manually.
-- psql -U postgres -f sql/00_create_database.sql
CREATE USER invoice_user WITH PASSWORD 'invoice_pass';
CREATE DATABASE invoice_rbac_db OWNER invoice_user;
GRANT ALL PRIVILEGES ON DATABASE invoice_rbac_db TO invoice_user;
