"""MetadataImportService: JSON 元数据导入预览与提交。

依赖 MetadataRepository 和 contracts.py 中的 Pydantic 模型，
不绕过 Repository 直连 SQLite。

.. note::

    **schema vs schema_name 映射**
    import service 层（以及对外 API/Pydantic 契约）统一使用 ``schema``，
    MetadataRepository 内部自动映射到 DDL 的 ``schema_name`` 列。
    调用方无需关心这一内部映射。
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from app.domain.contracts import (
    Diagnostic,
    DiagnosticCode,
    DiagnosticLevel,
    ImportChangeType,
    ImportStatus,
    MetadataImportChange,
    MetadataImportPayload,
    MetadataImportResult,
    MetadataObjectRef,
)


class MetadataImportService:
    """JSON 元数据导入服务。

    提供 preview（只读校验）和 commit（事务写入）两个核心操作。
    """

    def __init__(self, repo):
        """注入 MetadataRepository 实例。"""
        self.repo = repo

    # ------------------------------------------------------------------
    # preview
    # ------------------------------------------------------------------

    def preview(self, payload: MetadataImportPayload) -> MetadataImportResult:
        """校验 JSON 载荷，计算变更预览，不写入数据库。

        Returns:
            MetadataImportResult with status=preview_ready，
            changes 列表包含 added/updated/unchanged 分类，
            diagnostics 包含校验过程中发现的问题。
        """
        diagnostics: list[Diagnostic] = []
        changes: list[MetadataImportChange] = []

        # 1. 校验 schema_version
        if payload.schema_version != "1.0":
            diagnostics.append(
                Diagnostic(
                    diagnostic_id=f"diag:{uuid.uuid4().hex[:12]}",
                    code=DiagnosticCode.METADATA_IMPORT_SCHEMA_UNSUPPORTED,
                    level=DiagnosticLevel.error,
                    message=f"不支持的 schema_version: {payload.schema_version}，仅支持 '1.0'",
                    suggestion="请使用 schema_version='1.0' 的 JSON 格式",
                    details={"schema_version": payload.schema_version},
                )
            )
            return MetadataImportResult(
                status=ImportStatus.preview_ready,
                metadata_version=payload.metadata_version,
                changes=[],
                diagnostics=diagnostics,
                summary={"tables": len(payload.tables), "errors": 1},
            )

        # 2. 获取已有元数据（用于 diff 计算）
        existing_mv = self.repo.get_metadata_version(payload.metadata_version)
        existing_tables: dict[str, dict] = {}
        existing_columns: dict[str, set[str]] = {}
        if existing_mv is not None:
            tables = self.repo.get_tables(
                metadata_version=payload.metadata_version, limit=9999
            )
            for t in tables:
                key = f"{t['catalog']}.{t['schema_name']}.{t['normalized_table_name']}"
                existing_tables[key] = dict(t)
                cols = self.repo.get_columns(
                    table_id=t["id"],
                    metadata_version=payload.metadata_version,
                    limit=9999,
                )
                existing_columns[key] = {
                    c["normalized_column_name"] for c in cols
                }

        # 3. 遍历每张表
        error_count = 0
        warning_count = 0
        info_count = 0
        total_columns = 0

        for t_idx, table in enumerate(payload.tables):
            table_catalog = table.catalog or payload.default_catalog
            table_schema = table.schema or payload.default_schema
            table_name_key = (
                f"{table_catalog}.{table_schema}."
                f"{table.name.lower() if not payload.case_sensitive else table.name}"
            )

            # 3a. 表级校验
            table_diags = self._validate_table(table, t_idx)
            diagnostics.extend(table_diags)
            for d in table_diags:
                if d.level == DiagnosticLevel.error:
                    error_count += 1

            if table_diags and any(
                d.level == DiagnosticLevel.error for d in table_diags
            ):
                # 表级错误（如空表名、空列），跳过字段校验
                continue

            # 3b. 字段级校验（重复字段名、复杂类型、缺失 ordinal）
            col_diags = self._validate_columns(table, t_idx)
            diagnostics.extend(col_diags)
            for d in col_diags:
                if d.level == DiagnosticLevel.error:
                    error_count += 1
                elif d.level == DiagnosticLevel.warning:
                    warning_count += 1
                elif d.level == DiagnosticLevel.info:
                    info_count += 1

            total_columns += len(table.columns)

            # 3c. diff 计算（added / updated / unchanged）
            if existing_mv is None:
                # 全新版本，全部是 added
                changes.append(
                    MetadataImportChange(
                        change_type=ImportChangeType.added,
                        object_type="table",
                        object_ref=MetadataObjectRef(
                            catalog=table_catalog,
                            schema=table_schema,
                            table=table.name,
                        ),
                        after={"columns": len(table.columns)},
                        message=f"新增表 {table.name}",
                    )
                )
                continue

            if table_name_key in existing_tables:
                existing_col_set = existing_columns.get(table_name_key, set())
                new_col_names = {
                    col.name.lower() if not payload.case_sensitive else col.name
                    for col in table.columns
                }

                if new_col_names == existing_col_set:
                    changes.append(
                        MetadataImportChange(
                            change_type=ImportChangeType.unchanged,
                            object_type="table",
                            object_ref=MetadataObjectRef(
                                catalog=table_catalog,
                                schema=table_schema,
                                table=table.name,
                            ),
                            message=f"表 {table.name} 无变化",
                        )
                    )
                else:
                    added_cols = new_col_names - existing_col_set
                    removed_hint = f" (现有字段: {sorted(existing_col_set)})"
                    changes.append(
                        MetadataImportChange(
                            change_type=ImportChangeType.updated,
                            object_type="table",
                            object_ref=MetadataObjectRef(
                                catalog=table_catalog,
                                schema=table_schema,
                                table=table.name,
                            ),
                            before={"columns": len(existing_col_set)},
                            after={"columns": len(new_col_names)},
                            message=(
                                f"表 {table.name} 有变更: "
                                f"新增 {len(added_cols)} 个字段"
                                f"{removed_hint if len(added_cols) > 0 else ''}"
                            ),
                        )
                    )
            else:
                changes.append(
                    MetadataImportChange(
                        change_type=ImportChangeType.added,
                        object_type="table",
                        object_ref=MetadataObjectRef(
                            catalog=table_catalog,
                            schema=table_schema,
                            table=table.name,
                        ),
                        after={"columns": len(table.columns)},
                        message=f"新增表 {table.name}",
                    )
                )

        return MetadataImportResult(
            status=ImportStatus.preview_ready,
            import_batch_id=None,
            metadata_version=payload.metadata_version,
            changes=changes,
            diagnostics=diagnostics,
            summary={
                "tables": len(payload.tables),
                "total_columns": total_columns,
                "added": sum(1 for c in changes if c.change_type == ImportChangeType.added),
                "updated": sum(1 for c in changes if c.change_type == ImportChangeType.updated),
                "unchanged": sum(1 for c in changes if c.change_type == ImportChangeType.unchanged),
                "errors": error_count,
                "warnings": warning_count,
                "info": info_count,
            },
        )

    # ------------------------------------------------------------------
    # commit
    # ------------------------------------------------------------------

    def commit(self, payload: MetadataImportPayload) -> MetadataImportResult:
        """事务写入元数据，失败时回滚并记录错误。

        Returns:
            MetadataImportResult with status=committed 或 failed。
        """
        # 先跑 preview 拿到校验结果
        preview_result = self.preview(payload)

        # 如果有 schema_version 等阻断性错误，直接返回 preview 结果
        if any(
            d.code == DiagnosticCode.METADATA_IMPORT_SCHEMA_UNSUPPORTED
            for d in preview_result.diagnostics
            if d.level == DiagnosticLevel.error
        ):
            return MetadataImportResult(
                status=ImportStatus.failed,
                metadata_version=payload.metadata_version,
                diagnostics=preview_result.diagnostics,
                summary={"tables": len(payload.tables), "errors": 1},
            )

        # 开始事务
        self.repo.begin_transaction()
        job_id = None

        try:
            # 1. 确保 metadata_version 存在
            existing_mv = self.repo.get_metadata_version(payload.metadata_version)
            if existing_mv is None:
                self.repo.create_metadata_version(
                    payload.metadata_version,
                    source_name=payload.source_name,
                )

            # 2. 创建导入任务
            job_id = self.repo.create_import_job(payload.metadata_version)

            total_columns = 0
            error_count = 0
            commit_diagnostics: list[Diagnostic] = list(preview_result.diagnostics)

            # 3. 逐表导入
            for t_idx, table in enumerate(payload.tables):
                table_catalog = table.catalog or payload.default_catalog
                table_schema = table.schema or payload.default_schema

                # 跳过表级错误（已在 preview 中标记）
                if not table.name.strip():
                    error_count += 1
                    self.repo.record_import_error(
                        job_id, t_idx, -1,
                        DiagnosticCode.METADATA_IMPORT_EMPTY_TABLE_NAME.value,
                        f"表索引 {t_idx} 名称为空",
                    )
                    continue

                if not table.columns:
                    error_count += 1
                    self.repo.record_import_error(
                        job_id, t_idx, -1,
                        DiagnosticCode.METADATA_IMPORT_EMPTY_COLUMNS.value,
                        f"表 {table.name} 的 columns 为空",
                    )
                    continue

                # 计算归一化表名
                normalized_name = (
                    table.name if payload.case_sensitive else table.name.lower()
                )

                # 若表已存在，先删除旧列以避免 FOREIGN KEY 约束冲突。
                # INSERT OR REPLACE 会先 DELETE 旧行，若仍有子列引用旧 table_id
                # 则 foreign_keys=ON 会阻止 DELETE。
                existing_table = self.repo.get_table_by_name(
                    metadata_version=payload.metadata_version,
                    catalog=table_catalog,
                    schema=table_schema,
                    table_name=normalized_name,
                )
                if existing_table is not None:
                    self.repo.delete_columns_by_table_id(existing_table["id"])

                # upsert table
                try:
                    table_id = self.repo.upsert_table(
                        metadata_version=payload.metadata_version,
                        catalog=table_catalog,
                        schema=table_schema,
                        table_name=table.name,
                        normalized_name=normalized_name,
                        comment=table.comment,
                    )
                except Exception as e:
                    error_count += 1
                    self.repo.record_import_error(
                        job_id, t_idx, -1,
                        DiagnosticCode.METADATA_IMPORT_COMMIT_FAILED.value,
                        f"写入表 {table.name} 失败: {e}",
                    )
                    raise  # 触发回滚

                # upsert columns
                columns_data = []
                for c_idx, col in enumerate(table.columns):
                    normalized_col = (
                        col.name if payload.case_sensitive else col.name.lower()
                    )
                    columns_data.append({
                        "column_name": col.name,
                        "normalized_column_name": normalized_col,
                        "data_type": col.data_type,
                        "comment": col.comment,
                        "ordinal": col.ordinal,
                        "is_partition": col.is_partition,
                    })

                try:
                    self.repo.upsert_columns(
                        table_id, payload.metadata_version, columns_data
                    )
                    total_columns += len(columns_data)
                except Exception as e:
                    error_count += 1
                    self.repo.record_import_error(
                        job_id, t_idx, -1,
                        DiagnosticCode.METADATA_IMPORT_COMMIT_FAILED.value,
                        f"写入表 {table.name} 的列失败: {e}",
                    )
                    raise  # 触发回滚

            # 4. 修复 table_count
            self.repo.update_table_count(payload.metadata_version)

            # 5. 更新导入任务状态
            self.repo.update_import_job_status(
                job_id=job_id,
                status="completed",
                total_tables=len(payload.tables),
                total_columns=total_columns,
                error_count=error_count,
            )

            # 6. 提交事务
            self.repo.commit()

            return MetadataImportResult(
                status=ImportStatus.committed,
                import_batch_id=str(job_id),
                metadata_version=payload.metadata_version,
                changes=preview_result.changes,
                diagnostics=commit_diagnostics,
                summary={
                    "tables": len(payload.tables),
                    "total_columns": total_columns,
                    "added": sum(1 for c in preview_result.changes if c.change_type == ImportChangeType.added),
                    "updated": sum(1 for c in preview_result.changes if c.change_type == ImportChangeType.updated),
                    "unchanged": sum(1 for c in preview_result.changes if c.change_type == ImportChangeType.unchanged),
                    "errors": error_count,
                },
            )

        except Exception as exc:
            # 事务回滚
            self.repo.rollback()

            # 如果 job_id 已创建，更新其状态为 failed
            if job_id is not None:
                try:
                    # 在回滚后的新连接上无法更新 job 状态，
                    # 但 import_jobs 表在 transaction 内，回滚后该 insert 也被回滚。
                    # 因此这里不额外处理。
                    pass
                except Exception:
                    pass

            return MetadataImportResult(
                status=ImportStatus.failed,
                metadata_version=payload.metadata_version,
                diagnostics=[
                    Diagnostic(
                        diagnostic_id=f"diag:{uuid.uuid4().hex[:12]}",
                        code=DiagnosticCode.METADATA_IMPORT_COMMIT_FAILED,
                        level=DiagnosticLevel.error,
                        message=f"导入提交失败，事务已回滚: {exc}",
                        suggestion="请检查数据完整性后重试",
                        details={"error": str(exc)},
                    )
                ],
                summary={"tables": len(payload.tables), "errors": 1},
            )

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_table(table: Any, t_idx: int) -> list[Diagnostic]:
        """校验单张表的元数据（名称、列列表）。"""
        diags: list[Diagnostic] = []

        # 表名不能为空
        if not table.name or not table.name.strip():
            diags.append(
                Diagnostic(
                    diagnostic_id=f"diag:{uuid.uuid4().hex[:12]}",
                    code=DiagnosticCode.METADATA_IMPORT_EMPTY_TABLE_NAME,
                    level=DiagnosticLevel.error,
                    message=f"表索引 {t_idx} 的名称为空",
                    suggestion="请为每张表提供有效的 name 字段",
                    details={"table_index": t_idx},
                )
            )

        # columns 不能为空
        if not table.columns or len(table.columns) == 0:
            diags.append(
                Diagnostic(
                    diagnostic_id=f"diag:{uuid.uuid4().hex[:12]}",
                    code=DiagnosticCode.METADATA_IMPORT_EMPTY_COLUMNS,
                    level=DiagnosticLevel.error,
                    message=f"表 {table.name or f'索引{t_idx}'} 的 columns 为空",
                    suggestion="请为每张表提供至少一个字段定义",
                    details={"table_index": t_idx, "table_name": table.name or ""},
                )
            )

        return diags

    @staticmethod
    def _validate_columns(table: Any, t_idx: int) -> list[Diagnostic]:
        """校验表中所有字段（重复名、复杂类型、缺失 ordinal）。"""
        diags: list[Diagnostic] = []
        seen_names: set[str] = set()

        for c_idx, col in enumerate(table.columns):
            col_name = col.name
            col_name_lower = col_name.lower() if col_name else ""

            # 重复字段名
            if col_name_lower in seen_names:
                diags.append(
                    Diagnostic(
                        diagnostic_id=f"diag:{uuid.uuid4().hex[:12]}",
                        code=DiagnosticCode.METADATA_IMPORT_DUPLICATE_COLUMN,
                        level=DiagnosticLevel.error,
                        message=(
                            f"表 {table.name} 中存在重复字段名: "
                            f"'{col_name}' (字段索引 {c_idx})"
                        ),
                        suggestion="请确保同一张表内字段名唯一",
                        details={
                            "table_index": t_idx,
                            "column_index": c_idx,
                            "column_name": col_name,
                        },
                    )
                )
            seen_names.add(col_name_lower)

            # 复杂类型检测
            complex_pattern = re.compile(
                r"^(map<|array<|struct<|decimal\(\d+,\s*\d+\)|"
                r"varchar\(\d+\)|char\(\d+\)|numeric\(\d+,\d+\))",
                re.IGNORECASE,
            )
            if col.data_type and complex_pattern.match(col.data_type.strip()):
                diags.append(
                    Diagnostic(
                        diagnostic_id=f"diag:{uuid.uuid4().hex[:12]}",
                        code=DiagnosticCode.METADATA_IMPORT_COMPLEX_TYPE,
                        level=DiagnosticLevel.info,
                        message=(
                            f"表 {table.name} 字段 '{col_name}' 使用复杂类型: "
                            f"{col.data_type}"
                        ),
                        suggestion="复杂类型已透传存储，请确认后端消费方可正确解析",
                        details={
                            "table_index": t_idx,
                            "column_index": c_idx,
                            "column_name": col_name,
                            "data_type": col.data_type,
                        },
                    )
                )

            # ordinal 为 NULL
            if col.ordinal is None:
                diags.append(
                    Diagnostic(
                        diagnostic_id=f"diag:{uuid.uuid4().hex[:12]}",
                        code=DiagnosticCode.METADATA_IMPORT_MISSING_ORDINAL,
                        level=DiagnosticLevel.warning,
                        message=(
                            f"表 {table.name} 字段 '{col_name}' 缺少 ordinal"
                        ),
                        suggestion="建议为每个字段提供唯一序号，以便排序展示",
                        details={
                            "table_index": t_idx,
                            "column_index": c_idx,
                            "column_name": col_name,
                        },
                    )
                )

        return diags
