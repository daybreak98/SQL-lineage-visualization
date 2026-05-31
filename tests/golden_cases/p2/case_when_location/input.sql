-- GC-M24-002: case_when_location
-- CASE WHEN 表达式定位 golden case
-- 期望: source_locations 包含 expression:scope:root:1:case (expression)

SELECT
  order_no,
  CASE WHEN status = 1 THEN 'ok' ELSE 'fail' END AS status_label
FROM default.order_table
