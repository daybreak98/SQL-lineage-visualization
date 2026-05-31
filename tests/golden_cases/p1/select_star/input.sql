-- GC-P1-007: select_star
-- SELECT * 元数据驱动展开 - 验证 select * 展开为全部 5 个字段
-- 期望 status=success, 5 条 output column, 5 条 projection edge

select * from default.order_table
