"""Integration tests for MetadataRepository (R01)."""

import os
import pytest

from app.repositories.metadata_repository import MetadataRepository


@pytest.fixture
def repo():
    """Create a repository backed by an in-memory SQLite database."""
    r = MetadataRepository(db_path=":memory:")
    yield r


# ------------------------------------------------------------------
# metadata_versions
# ------------------------------------------------------------------

def test_create_metadata_version(repo):
    vid = repo.create_metadata_version("v1.0", source_name="test")
    assert isinstance(vid, int)
    assert vid > 0

    row = repo.get_metadata_version("v1.0")
    assert row is not None
    assert row["version"] == "v1.0"
    assert row["source_name"] == "test"


def test_get_latest_metadata_version(repo):
    repo.create_metadata_version("v1.0")
    repo.create_metadata_version("v2.0")
    row = repo.get_metadata_version("latest")
    assert row["version"] == "v2.0"


def test_list_metadata_versions(repo):
    repo.create_metadata_version("v1.0")
    repo.create_metadata_version("v2.0")
    repo.create_metadata_version("v3.0")
    versions = repo.list_metadata_versions()
    assert len(versions) == 3
    # Most recent first
    assert versions[0]["version"] == "v3.0"


# ------------------------------------------------------------------
# catalog_tables
# ------------------------------------------------------------------

def test_upsert_and_get_table(repo):
    repo.create_metadata_version("v1.0")
    tid = repo.upsert_table(
        metadata_version="v1.0",
        catalog="default",
        schema="default",
        table_name="order_table",
        normalized_name="order_table",
        comment="订单表",
    )
    assert isinstance(tid, int)
    assert tid > 0

    tables = repo.get_tables(metadata_version="v1.0")
    assert len(tables) == 1
    assert tables[0]["table_name"] == "order_table"
    assert tables[0]["comment"] == "订单表"


def test_unique_table_constraint(repo):
    """Verify that the UNIQUE constraint on catalog_tables prevents duplicates."""
    repo.create_metadata_version("v1.0")

    tid1 = repo.upsert_table(
        metadata_version="v1.0",
        catalog="default",
        schema="default",
        table_name="order_table",
        normalized_name="order_table",
    )
    # Upsert the same table again should return the same id (or a valid id)
    tid2 = repo.upsert_table(
        metadata_version="v1.0",
        catalog="default",
        schema="default",
        table_name="order_table_v2",
        normalized_name="order_table",  # same normalized name
    )
    assert tid2 > 0

    # Should only have one row due to INSERT OR REPLACE
    tables = repo.get_tables(metadata_version="v1.0")
    assert len(tables) == 1


def test_get_table_by_name(repo):
    repo.create_metadata_version("v1.0")
    repo.upsert_table(
        metadata_version="v1.0",
        catalog="default",
        schema="default",
        table_name="order_table",
        normalized_name="order_table",
    )
    row = repo.get_table_by_name(
        metadata_version="v1.0",
        catalog="default",
        schema="default",
        table_name="order_table",
    )
    assert row is not None
    assert row["table_name"] == "order_table"


def test_get_table_by_name_not_found(repo):
    repo.create_metadata_version("v1.0")
    row = repo.get_table_by_name(
        metadata_version="v1.0",
        catalog="default",
        schema="default",
        table_name="nonexistent",
    )
    assert row is None


def test_get_tables_with_keyword(repo):
    repo.create_metadata_version("v1.0")
    repo.upsert_table("v1.0", "default", "default", "order_table", "order_table")
    repo.upsert_table("v1.0", "default", "default", "user_table", "user_table")

    results = repo.get_tables("v1.0", keyword="order")
    assert len(results) == 1
    assert results[0]["table_name"] == "order_table"


# ------------------------------------------------------------------
# catalog_columns
# ------------------------------------------------------------------

def test_upsert_and_get_columns(repo):
    repo.create_metadata_version("v1.0")
    tid = repo.upsert_table(
        metadata_version="v1.0",
        table_name="order_table",
        normalized_name="order_table",
    )

    cols = [
        {
            "column_name": "order_no",
            "normalized_column_name": "order_no",
            "data_type": "string",
            "comment": "订单号",
            "ordinal": 1,
            "is_partition": False,
        },
        {
            "column_name": "user_id",
            "normalized_column_name": "user_id",
            "data_type": "string",
            "comment": "用户ID",
            "ordinal": 2,
            "is_partition": False,
        },
    ]
    col_ids = repo.upsert_columns(tid, "v1.0", cols)
    assert len(col_ids) == 2
    assert all(isinstance(cid, int) and cid > 0 for cid in col_ids)

    columns = repo.get_columns(tid, "v1.0")
    assert len(columns) == 2
    assert columns[0]["column_name"] == "order_no"
    assert columns[1]["column_name"] == "user_id"


def test_unique_column_constraint(repo):
    """Verify that the UNIQUE constraint on catalog_columns prevents duplicates."""
    repo.create_metadata_version("v1.0")
    tid = repo.upsert_table(
        metadata_version="v1.0",
        table_name="order_table",
        normalized_name="order_table",
    )

    col = {
        "column_name": "order_no",
        "normalized_column_name": "order_no",
        "data_type": "string",
        "ordinal": 1,
        "is_partition": False,
    }
    repo.upsert_columns(tid, "v1.0", [col])
    # Upsert again with same normalized name (INSERT OR REPLACE)
    col2 = {
        "column_name": "order_no_v2",
        "normalized_column_name": "order_no",
        "data_type": "string",
        "ordinal": 1,
        "is_partition": False,
    }
    repo.upsert_columns(tid, "v1.0", [col2])

    columns = repo.get_columns(tid, "v1.0")
    assert len(columns) == 1  # Only one row after REPLACE


# ------------------------------------------------------------------
# metadata_context
# ------------------------------------------------------------------

def test_get_metadata_context(repo):
    repo.create_metadata_version("v1.0")
    tid = repo.upsert_table(
        metadata_version="v1.0",
        table_name="order_table",
        normalized_name="order_table",
    )
    repo.upsert_columns(
        tid, "v1.0",
        [
            {"column_name": "order_no", "normalized_column_name": "order_no",
             "data_type": "string", "ordinal": 1, "is_partition": False}
        ],
    )

    ctx = repo.get_metadata_context("v1.0")
    assert ctx["metadata_version"] == "v1.0"
    assert isinstance(ctx["case_sensitive"], bool)
    assert ctx["default_catalog"] == "default"
    assert ctx["default_schema"] == "default"
    assert len(ctx["tables"]) == 1
    assert len(ctx["columns_by_table"]) == 1


def test_get_metadata_context_no_version(repo):
    """When no metadata version exists, context should return empty."""
    ctx = repo.get_metadata_context("v1.0")
    assert ctx["metadata_version"] == ""
    assert ctx["tables"] == []


# ------------------------------------------------------------------
# case sensitivity
# ------------------------------------------------------------------

def test_case_sensitivity(repo):
    """Verify that case-insensitive lookups work via normalized names."""
    repo.create_metadata_version("v1.0")
    repo.upsert_table(
        metadata_version="v1.0",
        catalog="default",
        schema="default",
        table_name="Order_Table",
        normalized_name="order_table",
    )

    # Lookup by lowercased name
    row = repo.get_table_by_name(
        metadata_version="v1.0",
        table_name="order_table",
    )
    assert row is not None

    # Lookup by original name (if we stored it lowercase in normalized)
    # This should work because get_table_by_name lowercases the input
    row2 = repo.get_table_by_name(
        metadata_version="v1.0",
        table_name="ORDER_TABLE",
    )
    assert row2 is not None


# ------------------------------------------------------------------
# migration idempotency
# ------------------------------------------------------------------

def test_migration_idempotent(repo):
    """Verify that _init_db can be called multiple times without error."""
    # First call: repo is already initialized via fixture
    # Second call: should not raise
    repo._init_db()

    # Verify tables still exist
    tables = repo._conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = {r["name"] for r in tables}
    assert "metadata_versions" in table_names
    assert "catalog_tables" in table_names
    assert "catalog_columns" in table_names
    assert "import_jobs" in table_names
    assert "import_errors" in table_names
