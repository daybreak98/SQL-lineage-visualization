"""FastAPI application entry point for SQL Lineage Workbench."""

import os
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health_controller import router as health_router
from app.api.metadata_controller import router as metadata_router
from app.api.sql_controller import router as sql_router


def _get_db_path() -> str:
    """Resolve the SQLite database path, ensuring the data directory exists."""
    db_path = os.environ.get("LINEAGE_DB_PATH", "data/lineage.db")
    db_dir = os.path.dirname(os.path.abspath(db_path))
    os.makedirs(db_dir, exist_ok=True)
    return db_path


def _run_migrations(db_path: str) -> None:
    """Execute SQL migration files to initialize the database schema."""
    migrations_dir = os.path.join(os.path.dirname(__file__), "db", "migrations")
    if not os.path.isdir(migrations_dir):
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        migration_files = sorted(
            f for f in os.listdir(migrations_dir) if f.endswith(".sql")
        )
        for filename in migration_files:
            filepath = os.path.join(migrations_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                sql = f.read()
            conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: run migrations on startup."""
    db_path = _get_db_path()
    _run_migrations(db_path)
    yield


app = FastAPI(
    title="SQL Lineage Workbench",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: allow local frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router, prefix="/api")
app.include_router(metadata_router)
app.include_router(sql_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
