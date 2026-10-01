# 更新日志

## v1.2.0 (2026-10-01)

增强版（fork）。在 v1.1.0 基础上增强「分类质量与灵活性」，新增家庭共享抓取，并修复写入相关 bug。

### 新增
- **家庭共享库抓取（L5）**：`fetch_library.py` 支持 `--family`（`--login` 时自动），
  经登录态接口 `IFamilyGroupsService` 纳入家庭组共享游戏；输出 CSV 增加 `source` 列（own/shared）。
- **类目体检**：`overlap_check.py` 计算同一维度内两两类目的 Jaccard 重叠并告警；
  新增 `references/category-quality.md`（何时收紧 + 准入/排除/锚点方法与成效）。
- **分类策略档位**：`references/options.md`（精细度 / 属性维度 / 属性类目归位 / 泛化类收紧 / 复核深度 / 预算）。
- **类型 + 属性双维度**：新增 F 特性维度（`build_collections.py` 支持 `F -> F_tags`）。
- **厂商维度细化**：`vendor_region.py` + `references/vendor-region.md`——联网判厂商国别
  （中国厂商单列）、名厂逐个独立成类，兜底类不再是大杂烩。
- **会话接续**：`handoff.py` + `references/handoff.md`，状态外置，长任务换窗口可续。
- **复核质量**：`compare_passes.py`（双遍独立复核逐款比对）；`review_tools.py check`（覆盖率/漏行校验）。
- **总表生成**：`gen_report.py`（人类可读分类总表）。

### 修复
- `write_steam.py`：userdata 目录名改用 **SteamID32**（原用 SteamID64 导致找不到目标文件、无法写入）；
  并**保护系统收藏集** `favorite`/`hidden`（原会误删）。
- `fetch_library.py`：`--licenses` 未接线（补调用 + 空值保护）。
- `gen_report.py`：去掉硬编码绝对路径。
- 文档域名笔误等。

### 文档
- `README.md` 重写为完整项目介绍；`pitfalls.md` 增补「分类质量」与「会话工程」实战经验。

### 致谢
基于 **Smirk1921/steam-collection-skill**（MIT），保留原作者版权声明。

## v1.1.0 (2026-09-29)

增量模式：已完成分类后，库里新增游戏只分类新增部分，不再重跑全流程。

- 新增 `scripts/incremental.py`：detect（新增/移除/安装变化/强制重分类 diff）→
  fetch-info（增量抓元数据，缓存续传 + 标签 ID→名称映射自动抓取）→
  prepare（子代理批次切分，协议与步骤3一致）→ merge（复用格式修复规则）→
  apply（备份后合并总表、同步 installed 列、自动清空已卸载款 A 状态、--prune 可选清理）
- 新增 `references/incremental-guide.md`：增量协议、A 状态处理（新装款必须问用户）、
  移除款默认保留策略、汇报模板
- SKILL.md 新增增量模式章节与触发描述；pitfalls 新增增量常见问题
- 以分类总表为唯一已分类基准，不引入独立 state 文件；重复运行幂等

## v1.0.0 (2026-09-26)

首个公开版本。

- 四步流程：抓取游戏列表 → 分类体系与预分类 → 联网逐款复核 → 生成收藏集并写入 Steam
- 抓取方法库：Web API / 社区页(匿名或 Cookie) / 浏览器控制登录 / 许可页审计 / 本地安装扫描
- ABCDE 类目方法论与按列表预生成；编号规范（兜底类最大号、主编号连续）
- 复核标签来源四级递进（steamcmd API → 官方 API → SteamDB/商店页 → 搜索引擎子代理）
- 子代理并发/批次参数化（按用户配额与预算调整），幂等续跑与结果格式自动修复
- 写入协议：Steam 运行守卫 + 双备份 + 原子写入 + 写前强制确认
- 附新手纯文本说明（使用说明-新手版.txt）与实战踩坑清单（references/pitfalls.md）
