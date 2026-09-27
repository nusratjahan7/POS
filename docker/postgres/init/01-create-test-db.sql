-- Runs once, on first container start, after the default database is created.
-- The second database isolates the automated test suite from development data.
CREATE DATABASE pos_test OWNER pos;
