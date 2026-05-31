"""SQL 解析与格式化 API 控制器（R03 / M08）。"""

from fastapi import APIRouter

from app.domain.contracts import (
    AnalysisResult,
    AnalysisStatus,
    AnalyzeSqlRequest,
    FormatSqlRequest,
    FormatSqlResponse,
)
from app.services.analysis_orchestrator import AnalysisOrchestrator
from app.services.sql_parse_service import SqlParseService

router = APIRouter(prefix="/api/sql", tags=["sql"])
service = SqlParseService()


@router.post("/format", response_model=FormatSqlResponse)
async def format_sql(request: FormatSqlRequest):
    """格式化 SQL。"""
    formatted, diagnostics = service.format(request.sql, request.dialect)
    if formatted is None:
        return FormatSqlResponse(
            status=AnalysisStatus.failed,
            dialect=request.dialect,
            formatted_sql=None,
            diagnostics=diagnostics,
        )
    return FormatSqlResponse(
        status=AnalysisStatus.success,
        dialect=request.dialect,
        formatted_sql=formatted,
        diagnostics=diagnostics,
    )


@router.post("/analyze", response_model=AnalysisResult)
async def analyze_sql(request: AnalyzeSqlRequest):
    """分析 SQL，返回正式 P0 AnalysisResult。"""
    orchestrator = AnalysisOrchestrator()
    return orchestrator.analyze(request)
