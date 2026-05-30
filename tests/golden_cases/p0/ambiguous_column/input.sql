-- GC-P0-005: ambiguous_column
-- 字段歧义 - 验证 JOIN 场景下多表共有字段的歧义检测
-- 期望 status=partial, AMBIGUOUS_COLUMN 诊断
-- 说明: user_id 同时存在于 order_table 和 user_table

select user_id from default.order_table a join default.user_table b on a.user_id = b.user_id
