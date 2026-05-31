-- GC-P1-001: source_location_basic
-- 验证 SourceLocation 基础精准提取的 Golden Case
-- 覆盖: SELECT 字段、FROM 表、表别名、WHERE 字段、GROUP BY 字段、ORDER BY 字段
-- 期望: source_locations 数组非空，包含 exact 和 unavailable 类型

SELECT o.order_no AS ord_num, u.user_name
FROM order_table o
JOIN user_table u ON o.user_id = u.user_id
WHERE o.status = 1
GROUP BY o.order_no, u.user_name
ORDER BY o.order_no DESC
