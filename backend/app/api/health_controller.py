"""Health check controller."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint for frontend connectivity validation."""
    return {
        "status": "ok",
        "service": "sql-lineage-workbench",
        "version": "0.1.0",
    }
