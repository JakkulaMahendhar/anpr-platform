-- Runs once, when the database volume is first created.
-- TimescaleDB: time-series storage for plate readings (hypertables, retention).
-- pg_trgm: fast fuzzy / partial plate search (e.g. "TS09%" or OCR near-misses).
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
