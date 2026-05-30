-- GC-P0-003: unknown_table
-- 未知表 - 验证表名在元数据中缺失时产生 UNKNOWN_TABLE 诊断
-- 期望 status=failed, UNKNOWN_TABLE 诊断

select order_no from default.missing_table
