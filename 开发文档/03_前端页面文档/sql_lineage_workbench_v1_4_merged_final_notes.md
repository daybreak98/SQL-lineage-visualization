# SQL Lineage Workbench v1.4 Merged Final Page

本次更新基于 v1.4 merged final spec，保留 v1.3 P0-Core 主链路，不扩展低频功能。

## 已实现

1. Analyze 成功后默认进入 `subquery_dependency`，不默认字段级复杂全图。
2. 选择 default output 后进入 `current_field_path`。
3. Full Graph Preview 只能用户主动点击进入。
4. 子查询 / CTE / Output / Table / Expression / Unknown 节点视觉分类增强。
5. 节点状态优先级按 selected > error > current_path > search_hit > warning > stale > hover > dimmed > normal 实现。
6. TopBar 去除 SQL Focus / Graph Focus / Max Canvas 等重复布局控制。
7. More 中保留 Reset split ratio / Reset workspace layout / Full Graph Preview 低频入口。
8. Canvas 顶部仍保持 SearchBar 40px + Toolbar 36px，不增加第三层常驻控件。
9. DetailPanel compact 保持三行摘要，不默认展示复杂 Tabs。
10. Drawer 增加 RenderMode / Node Taxonomy / Snapshots / M1-M7 回归入口。

## 建议测试

- Analyze 后确认默认为子查询依赖图。
- 点击 Output Capsule 选择 `order_cnt`，确认进入字段路径。
- 点击 Clear，确认回到子查询依赖图。
- 点击 Full Preview，确认只在用户主动触发时进入。
- 修改 SQL 后确认 dirty / stale / Re-analyze。
- 输入 `broken_parse` 后 Analyze 模拟 failed。
- 输入 `unknown_col` 后 Analyze 模拟 partial 和 Unknown 节点。
