"""编辑器辅助 API 控制器（M21 Completion + Hover）。"""

from fastapi import APIRouter

from app.domain.contracts import (
    CompletionRequest,
    CompletionResponse,
    HoverRequest,
    HoverResponse,
)
from app.repositories.metadata_repository import MetadataRepository
from app.services.completion_service import CompletionService
from app.services.hover_service import HoverService

router = APIRouter(prefix="/api/editor", tags=["editor"])


def _get_repo() -> MetadataRepository:
    return MetadataRepository()


@router.post("/completion", response_model=CompletionResponse)
async def completion(request: CompletionRequest):
    """返回光标处的自动补全候选（表名、字段名、关键字）。"""
    repo = _get_repo()
    try:
        service = CompletionService(repo)
        candidates = service.get_completions(
            sql=request.sql,
            cursor_line=request.cursor_line,
            cursor_col=request.cursor_col,
            dialect=request.dialect,
            metadata_version=request.metadata_version,
        )
        return CompletionResponse(candidates=candidates)
    finally:
        repo.close()


@router.post("/hover", response_model=HoverResponse)
async def hover(request: HoverRequest):
    """返回光标处标识符的 hover 信息（注释、类型、来源）。"""
    repo = _get_repo()
    try:
        service = HoverService(repo)
        info = service.get_hover(
            sql=request.sql,
            cursor_line=request.cursor_line,
            cursor_col=request.cursor_col,
            dialect=request.dialect,
            metadata_version=request.metadata_version,
        )
        return HoverResponse(hover=info)
    finally:
        repo.close()
