"""Metadata query facade used by NameResolver."""

from __future__ import annotations

from app.repositories.metadata_repository import MetadataRepository


class MetadataService:
    def __init__(self, repo: MetadataRepository):
        self.repo = repo

    def effective_version(self, metadata_version: str = "latest") -> str:
        row = self.repo.get_metadata_version(metadata_version)
        return row["version"] if row is not None else metadata_version

    def get_table(
        self,
        *,
        metadata_version: str,
        catalog: str,
        schema: str,
        table: str,
    ) -> dict | None:
        return self.repo.get_table_by_name(
            metadata_version=metadata_version,
            catalog=catalog,
            schema=schema,
            table_name=table,
        )

    def get_columns(self, table: dict, *, metadata_version: str) -> list[dict]:
        return self.repo.get_columns(
            table_id=table["id"],
            metadata_version=metadata_version,
            limit=9999,
        )
