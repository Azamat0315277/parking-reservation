-- Create the user
CREATE USER reader WITH PASSWORD 'password';

-- Grant connect to the database
GRANT CONNECT ON DATABASE rag_db TO reader;

-- Grant usage ONLY on parking schema
GRANT USAGE ON SCHEMA parking TO reader;

-- Grant SELECT on all existing tables in parking schema
GRANT SELECT ON ALL TABLES IN SCHEMA parking TO reader;

-- Grant SELECT on future tables in parking schema
ALTER DEFAULT PRIVILEGES IN SCHEMA parking GRANT SELECT ON TABLES TO reader;

-- Revoke access to public schema
REVOKE ALL ON SCHEMA public FROM reader;

-- ============================================
-- PostgreSQL Writer User: parking_writer
-- Permissions: 
--   - Can see all tables in 'parking' schema
--   - Can INSERT only into 'parking_lots' table
--   - Cannot CREATE, ALTER, DROP anything
-- ============================================

-- 1. Create the user (change password in production!)
CREATE USER parking_writer WITH PASSWORD 'password';

-- 2. Revoke all default privileges (clean slate)
REVOKE ALL ON DATABASE rag_db FROM parking_writer;
REVOKE ALL ON SCHEMA public FROM parking_writer;

-- 3. Grant CONNECT to the database
GRANT CONNECT ON DATABASE rag_db TO parking_writer;

-- 4. Grant USAGE on parking schema (allows seeing the schema)
GRANT USAGE ON SCHEMA parking TO parking_writer;

-- 5. Grant SELECT on all tables in parking schema (read-only visibility)
GRANT SELECT ON ALL TABLES IN SCHEMA parking TO parking_writer;

-- 6. Grant INSERT and UPDATE on parking_lots table
GRANT INSERT ON parking.parking_lots TO parking_writer;
GRANT UPDATE (space_availability, reservation_start, reservation_end) ON parking.parking_lots TO parking_writer;

-- 7. Set default privileges for future tables in parking schema
ALTER DEFAULT PRIVILEGES IN SCHEMA parking
    GRANT SELECT ON TABLES TO parking_writer;

-- 8. Explicitly revoke any ability to create objects
REVOKE CREATE ON SCHEMA parking FROM parking_writer;
REVOKE CREATE ON SCHEMA public FROM parking_writer;

