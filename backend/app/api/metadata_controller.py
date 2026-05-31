"""Metadata JSON 导入控制器。

提供 /api/metadata/import/preview、/api/metadata/import/commit、
/api/metadata/tables、/api/metadata/columns 四个端点。
"""

from fastapi import APIRouter, HTTPException, Query

from app.domain.contracts import (
    ImportMode,
    MetadataImportRequest,
    MetadataImportResult,
)
from app.repositories.metadata_repository import MetadataRepository
from app.services.metadata_import_service import MetadataImportService

router = APIRouter(prefix="/api/metadata", tags=["metadata"])


# ------------------------------------------------------------------
# 依赖注入工厂
# ------------------------------------------------------------------

def _get_service() -> MetadataImportService:
    """创建 MetadataImportService 实例（注入 MetadataRepository）。"""
    repo = MetadataRepository()
    return MetadataImportService(repo)


# ------------------------------------------------------------------
# POST /api/metadata/import/preview
# ------------------------------------------------------------------

@router.post("/import/preview", response_model=MetadataImportResult)
async def import_preview(request: MetadataImportRequest):
    """JSON 元数据导入预览，不写库。

    校验 JSON 结构合法性，返回变更预览（added/updated/unchanged）
    和结构化 diagnostics。
    """
    service = _get_service()
    try:
        result = service.preview(request.payload)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "METADATA_IMPORT_INVALID_JSON",
                "message": f"JSON 解析失败: {e}",
            },
        ) from e


# ------------------------------------------------------------------
# POST /api/metadata/import/commit
# ------------------------------------------------------------------

@router.post("/import/commit", response_model=MetadataImportResult)
async def import_commit(request: MetadataImportRequest):
    """JSON 元数据导入提交，事务写入。

    将校验通过的元数据写入 SQLite，失败时自动回滚。
    """
    service = _get_service()
    try:
        result = service.commit(request.payload)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "METADATA_IMPORT_COMMIT_FAILED",
                "message": f"导入提交异常: {e}",
            },
        ) from e


# ------------------------------------------------------------------
# GET /api/metadata/tables
# ------------------------------------------------------------------

@router.get("/tables", response_model=dict)
async def list_tables(
    keyword: str = Query(default="", description="表名搜索关键词"),
    catalog: str = Query(default="default", description="Catalog 名称"),
    schema: str = Query(default="default", description="Schema 名称"),
    limit: int = Query(default=20, ge=1, le=200, description="返回数量上限"),
):
    """查询已导入的表列表。

    支持按 keyword/catalog/schema 过滤，默认返回最新 metadata_version 的数据。
    """
    repo = MetadataRepository()
    tables = repo.get_tables(
        metadata_version="latest",
        catalog=catalog,
        schema=schema,
        keyword=keyword if keyword else None,
        limit=limit,
    )
    return {"tables": tables, "total": len(tables)}


# ------------------------------------------------------------------
# GET /api/metadata/columns
# ------------------------------------------------------------------

@router.get("/columns", response_model=dict)
async def list_columns(
    catalog: str = Query(default="default", description="Catalog 名称"),
    schema: str = Query(default="default", description="Schema 名称"),
    table: str = Query(default="", description="表名（可选，不传则返回所有表字段）"),
    keyword: str = Query(default="", description="字段名搜索关键词"),
    limit: int = Query(default=50, ge=1, le=500, description="返回数量上限"),
):
    """查询已导入的字段列表。

    可按 catalog/schema/table/keyword 过滤。
    """
    repo = MetadataRepository()
    columns = repo.get_columns_by_table_name(
        metadata_version="latest",
        catalog=catalog,
        schema=schema,
        table=table,
        keyword=keyword if keyword else None,
        limit=limit,
    )
    return {"columns": columns, "total": len(columns)}
