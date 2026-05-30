-- GC-P0-004: unknown_column
-- 未知字段 - 验证已知表中不存在某字段时产生 UNKNOWN_COLUMN 诊断
-- 期望 status=partial, UNKNOWN_COLUMN 诊断, order_no 正常解析

select order_no, missing_col from default.order_table
