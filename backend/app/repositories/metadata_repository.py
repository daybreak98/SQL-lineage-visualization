"""MetadataRepository: CRUD operations for SQLite metadata store.

Provides transactional-safe operations on the five core metadata tables:
metadata_versions, catalog_tables, catalog_columns, import_jobs, import_errors.
"""

import os
import sqlite3
from datetime import datetime, timezone


class MetadataRepository:
    """Repository for managing metadata in SQLite.

    All write operations are wrapped in transactions. The caller is responsible
    for calling commit() or rollback() as appropriate.
    """

    def __init__(self, db_path: str = "data/lineage.db"):
        self._db_path = db_path
        self._ensure_db_dir()
        self._conn = sqlite3.connect(
            db_path, check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_db()

    def _ensure_db_dir(self) -> None:
        """Ensure the directory for the database file exists."""
        db_dir = os.path.dirname(os.path.abspath(self._db_path))
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def _init_db(self) -> None:
        """Execute migration SQL to create tables if they don't exist."""
        migrations_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "db", "migrations"
        )
        if not os.path.isdir(migrations_dir):
            return

        migration_files = sorted(
            f for f in os.listdir(migrations_dir) if f.endswith(".sql")
        )
        for filename in migration_files:
            filepath = os.path.join(migrations_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                sql = f.read()
            self._conn.executescript(sql)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Transaction helpers
    # ------------------------------------------------------------------

    def begin_transaction(self) -> None:
        """Begin an explicit transaction."""
        self._conn.execute("BEGIN")

    def commit(self) -> None:
        """Commit the current transaction."""
        self._conn.commit()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        self._conn.rollback()

    # ------------------------------------------------------------------
    # metadata_versions
    # ------------------------------------------------------------------

    def create_metadata_version(
        self, version: str, source_name: str | None = None
    ) -> int:
        """Create a new metadata version entry.

        Returns the auto-incremented id of the new version.
        """
        created_at = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            "INSERT INTO metadata_versions (version, created_at, source_name) "
            "VALUES (?, ?, ?)",
            (version, created_at, source_name),
        )
        return cursor.lastrowid

    def get_metadata_version(self, version: str = "latest") -> dict | None:
        """Get a metadata version by version string.

        If version is 'latest', returns the most recently created version.
        """
        if version == "latest":
            row = self._conn.execute(
                "SELECT * FROM metadata_versions ORDER BY id DESC LIMIT 1"
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT * FROM metadata_versions WHERE version = ?",
                (version,),
            ).fetchone()

        if row is None:
            return None
        return dict(row)

    def list_metadata_versions(self) -> list[dict]:
        """List all metadata versions, ordered by creation time descending."""
        rows = self._conn.execute(
            "SELECT * FROM metadata_versions ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # catalog_tables
    # ------------------------------------------------------------------

    def upsert_table(
        self,
        metadata_version: str,
        catalog: str = "default",
        schema: str = "default",
        table_name: str = "",
        normalized_name: str = "",
        comment: str | None = None,
    ) -> int:
        """Insert or update a table in the catalog.

        Uses INSERT OR REPLACE to handle the UNIQUE constraint on
        (metadata_version, catalog, schema_name, normalized_table_name).

        Returns the row id of the inserted/updated table.
        """
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT OR REPLACE INTO catalog_tables "
            "(metadata_version, catalog, schema_name, table_name, "
            "normalized_table_name, comment, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, "
            "COALESCE((SELECT created_at FROM catalog_tables WHERE "
            "  metadata_version=? AND catalog=? AND schema_name=? "
            "  AND normalized_table_name=?), ?), ?)",
            (
                metadata_version, catalog, schema, table_name,
                normalized_name, comment,
                metadata_version, catalog, schema, normalized_name, now, now,
            ),
        )
        row = self._conn.execute(
            "SELECT id FROM catalog_tables WHERE "
            "metadata_version=? AND catalog=? AND schema_name=? "
            "AND normalized_table_name=?",
            (metadata_version, catalog, schema, normalized_name),
        ).fetchone()
        return row["id"]

    def get_tables(
        self,
        metadata_version: str = "latest",
        catalog: str | None = None,
        schema: str | None = None,
        keyword: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Search tables with optional filters."""
        mv_row = self.get_metadata_version(metadata_version)
        if mv_row is None:
            return []
        effective_version = mv_row["version"]

        conditions = ["metadata_version = ?"]
        params: list = [effective_version]

        if catalog:
            conditions.append("catalog = ?")
            params.append(catalog)
        if schema:
            conditions.append("schema_name = ?")
            params.append(schema)
        if keyword:
            conditions.append("normalized_table_name LIKE ?")
            params.append(f"%{keyword}%")

        where = " AND ".join(conditions)
        rows = self._conn.execute(
            f"SELECT * FROM catalog_tables WHERE {where} ORDER BY table_name "
            f"LIMIT ?",
            params + [limit],
        ).fetchall()
        return [dict(r) for r in rows]

    def get_table_by_name(
        self,
        metadata_version: str = "latest",
        catalog: str = "default",
        schema: str = "default",
        table_name: str = "",
    ) -> dict | None:
        """Look up a single table by its fully-qualified name."""
        mv_row = self.get_metadata_version(metadata_version)
        if mv_row is None:
            return None
        effective_version = mv_row["version"]

        row = self._conn.execute(
            "SELECT * FROM catalog_tables WHERE "
            "metadata_version=? AND catalog=? AND schema_name=? "
            "AND normalized_table_name=?",
            (effective_version, catalog, schema, table_name.lower()),
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    # ------------------------------------------------------------------
    # catalog_columns
    # ------------------------------------------------------------------

    def upsert_columns(
        self,
        table_id: int,
        metadata_version: str,
        columns: list[dict],
    ) -> list[int]:
        """Upsert columns for a given table.

        Each column dict should have keys: column_name, normalized_column_name,
        data_type, comment, ordinal, is_partition.

        Uses INSERT OR REPLACE to handle UNIQUE(table_id, normalized_column_name).

        Returns a list of inserted column ids.
        """
        column_ids = []
        for col in columns:
            self._conn.execute(
                "INSERT OR REPLACE INTO catalog_columns "
                "(table_id, metadata_version, column_name, "
                "normalized_column_name, data_type, "
                "comment, ordinal, is_partition) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    table_id,
                    metadata_version,
                    col.get("column_name", ""),
                    col.get("normalized_column_name", col.get("column_name", "").lower()),
                    col.get("data_type", "unknown"),
                    col.get("comment"),
                    col.get("ordinal"),
                    int(col.get("is_partition", False)),
                ),
            )
            row = self._conn.execute(
                "SELECT id FROM catalog_columns WHERE "
                "metadata_version=? AND table_id=? AND normalized_column_name=?",
                (
                    metadata_version,
                    table_id,
                    col.get("normalized_column_name", col.get("column_name", "").lower()),
                ),
            ).fetchone()
            column_ids.append(row["id"])
        return column_ids

    def get_columns(
        self,
        table_id: int,
        metadata_version: str = "latest",
        keyword: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get columns for a table, optionally filtered by keyword."""
        conditions = ["cc.table_id = ?"]
        params: list = [table_id]

        if keyword:
            conditions.append("cc.normalized_column_name LIKE ?")
            params.append(f"%{keyword}%")

        where = " AND ".join(conditions)
        rows = self._conn.execute(
            f"SELECT cc.* FROM catalog_columns cc "
            f"WHERE {where} ORDER BY cc.ordinal LIMIT ?",
            params + [limit],
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # metadata_context
    # ------------------------------------------------------------------

    def get_metadata_context(
        self,
        metadata_version: str = "latest",
        default_catalog: str = "default",
        default_schema: str = "default",
    ) -> dict:
        """Build a metadata context dictionary for a given version.

        Returns a dict with keys: metadata_version, case_sensitive,
        default_catalog, default_schema, tables, columns_by_table.
        """
        mv_row = self.get_metadata_version(metadata_version)
        if mv_row is None:
            return {
                "metadata_version": "",
                "case_sensitive": False,
                "default_catalog": default_catalog,
                "default_schema": default_schema,
                "tables": [],
                "columns_by_table": {},
            }
        effective_version = mv_row["version"]

        tables = self._conn.execute(
            "SELECT * FROM catalog_tables WHERE metadata_version=?",
            (effective_version,),
        ).fetchall()

        table_list = [dict(t) for t in tables]
        columns_by_table: dict[int, list[dict]] = {}
        for t in table_list:
            cols = self._conn.execute(
                "SELECT * FROM catalog_columns WHERE table_id=? ORDER BY ordinal",
                (t["id"],),
            ).fetchall()
            columns_by_table[t["id"]] = [dict(c) for c in cols]

        return {
            "metadata_version": effective_version,
            "case_sensitive": False,
            "default_catalog": default_catalog,
            "default_schema": default_schema,
            "tables": table_list,
            "columns_by_table": columns_by_table,
        }
