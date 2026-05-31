-- GC-P2-001: group_by_metric
-- GROUP BY + 聚合指标 - 验证口径报告能否识别结果粒度、指标公式和去重逻辑
-- 期望 semantics_report: status=success, result_grain=grain_type:group_by, metrics 包含 SUM

SELECT dept, SUM(salary) FROM emp GROUP BY dept
