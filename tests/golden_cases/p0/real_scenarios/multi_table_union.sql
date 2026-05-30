-- RS-P0-003: multi_table_union (P1 准备)
-- 真实场景: 多表 UNION 场景
-- 模拟数仓中将多个同构分表合并查询
-- P1 范围: UNION ALL + 字段重命名 + 常量标记
-- P0 暂不要求 UNION 解析，此用例为 P1 做准备

select
    order_no,
    user_id,
    order_amt,
    'current' as data_source
from default.order_table
where dt = '2026-05-29'

union all

select
    order_no,
    user_id,
    order_amt,
    'history' as data_source
from default.order_table
where dt = '2026-05-28'
