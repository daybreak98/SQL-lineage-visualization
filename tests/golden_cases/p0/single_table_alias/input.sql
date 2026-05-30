-- GC-P0-002: single_table_alias
-- 字段别名 - 验证 AS 重命名的字段链路
-- 期望 status=success, 1条 alias 边

select order_no as order_id from default.order_table
