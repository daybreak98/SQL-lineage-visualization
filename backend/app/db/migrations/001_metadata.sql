-- 001: Core metadata tables for SQL lineage workbench
-- Creates the five core tables: metadata_versions, catalog_tables,
-- catalog_columns, import_jobs, import_errors.

CREATE TABLE IF NOT EXISTS metadata_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    source_name TEXT,
    table_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS catalog_tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metadata_version TEXT NOT NULL,
    catalog TEXT NOT NULL DEFAULT 'default',
    schema_name TEXT NOT NULL DEFAULT 'default',
    table_name TEXT NOT NULL,
    normalized_table_name TEXT NOT NULL,
    comment TEXT,
    source_type TEXT DEFAULT 'manual',
    quality_status TEXT DEFAULT 'ok',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(metadata_version, catalog, schema_name, normalized_table_name)
);

CREATE INDEX IF NOT EXISTS idx_ct_metadata
    ON catalog_tables(metadata_version);

CREATE INDEX IF NOT EXISTS idx_ct_normalized
    ON catalog_tables(metadata_version, normalized_table_name);

CREATE TABLE IF NOT EXISTS catalog_columns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id INTEGER NOT NULL,
    metadata_version TEXT NOT NULL,
    column_name TEXT NOT NULL,
    normalized_column_name TEXT NOT NULL,
    data_type TEXT DEFAULT 'unknown',
    comment TEXT,
    ordinal INTEGER,
    is_partition INTEGER DEFAULT 0,
    quality_status TEXT DEFAULT 'ok',
    FOREIGN KEY (table_id) REFERENCES catalog_tables(id),
    UNIQUE(metadata_version, table_id, normalized_column_name)
);

CREATE INDEX IF NOT EXISTS idx_cc_table
    ON catalog_columns(table_id);

CREATE INDEX IF NOT EXISTS idx_cc_metadata
    ON catalog_columns(table_id, normalized_column_name);

CREATE TABLE IF NOT EXISTS import_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metadata_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    started_at TEXT NOT NULL,
    completed_at TEXT,
    total_tables INTEGER,
    total_columns INTEGER,
    error_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS import_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER,
    table_index INTEGER,
    column_index INTEGER,
    error_code TEXT NOT NULL,
    error_message TEXT,
    FOREIGN KEY (job_id) REFERENCES import_jobs(id)
);
