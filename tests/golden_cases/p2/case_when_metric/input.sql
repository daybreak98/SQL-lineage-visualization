-- GC-P2-001: case_when_metric
-- CASE WHEN 表达式血缘 - 验证条件分支和值依赖提取
-- 期望: expression 节点包含 CASE WHEN，source columns 包含 status

SELECT
  order_no,
  CASE WHEN status = 1 THEN 'ok' ELSE 'fail' END AS status_label
FROM default.order_table
