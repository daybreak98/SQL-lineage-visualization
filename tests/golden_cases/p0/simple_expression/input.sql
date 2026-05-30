-- GC-P0-006: simple_expression
-- 简单表达式 - 验证算术表达式的依赖提取
-- 期望 status=success, expression 边 + alias 边

select order_amt * 0.1 as commission from default.order_table
