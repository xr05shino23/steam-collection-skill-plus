---
name: steam-collection
description: 全自动把用户的 Steam 游戏库分类为 Steam 收藏集并写入 Steam 客户端。四步流程：①抓取游戏列表（多方法可选，含浏览器登录）②设计/预生成分类体系并预分类 ③联网逐款复核修正 ④生成收藏集并写入（写前确认）；已完成分类后库里新增游戏走增量模式（只分类新增部分）。当用户要求"给 Steam 库存分类/建收藏集/整理游戏库"，或说"又买了新游戏/库存更新了/更新收藏集/增量"时使用。
---

# Steam 游戏库收藏集分类

把用户的 Steam 游戏库整理成一套收藏集（Collections）并写回 Steam 客户端。整个流程分四步，
**每一步完成后必须停下向用户汇报并等确认，用户同意后才进入下一步**。

## 总览

```
步骤1  抓取游戏列表   -> steam_library.csv (appid,name,store_url,installed)
         ↓ 用户确认列表无误
步骤2  分类体系 + 预分类 -> categories.md + preclassification.csv
         ↓ 用户确认类目与预分类
步骤3  联网逐款复核   -> preclassification_reviewed.csv (可选但强烈推荐)
         ↓ 用户确认修正报告
步骤4  生成收藏集并写入 Steam -> steam_collections.json -> 云存储 (写前必须再次确认)
```

## 开工前：收集信息与已有材料

先向用户确认/收集（缺什么问什么，一次问完）：

1. **账号标识**：SteamID64 或 SteamID32 或社区自定义 URL（vanity）。三者有其一即可。
2. **已有材料**（用户可能提前提供，校正后可跳过对应步骤）：
   - 已导出的游戏列表 CSV → 校验格式（见下）后直接进入步骤2
   - 已定义的分类类目文档 → 校验编码无空位、兜底类在最后后直接进入预分类
   - 已完成的分类表 → 直接进入步骤4
   - **已完成过一轮全流程**（有分类总表，之后库里加了新游戏）→ 走**增量模式**（见下），
     只处理新增/移除/指定重分类的部分，不重跑四步
3. **环境与偏好**：本机是否装有 Steam 客户端（写入必需）；是否有代理及其地址；是否安装
   Python 3 + requests；步骤3 若跑全量复核，询问用户的时间/预算偏好与子代理并发限额
   （不确定则按默认策略运行中探测）。
4. **分类策略档位**：按 `references/options.md` **一次问完**——精细度（1 主 / 1主+≤2次 / 不限）、
   是否启用**属性维度 F**、是否做**泛化类收紧**、**复核深度**（不查/只查可疑/全量/双遍交叉）、
   预算与并发。给出的选择将决定步骤 2/3 的行为。

**CSV 格式约定**（UTF-8 with BOM，四列）：
`appid,name,store_url,installed`，installed 为 `true`/`false`。

**预提供文件的校验要点**：
- 游戏列表：appid 唯一且为数字；installed 列存在；行数与用户描述的库规模量级一致
- 分类表：编码（如 B07/C12/D42）在类目文档中都有定义；每款游戏至少一个 C 类型；A 状态仅分配给 installed=true 的行
- 校验失败时列出问题请用户修正或授权修正，不要静默跳过

## 步骤 1：抓取游戏列表

**安装状态与所有权要分开**：任何网络接口都不提供"已安装"状态；本地扫描 Steam 的
`appmanifest_*.acf` 是安装状态的唯一权威来源。所有权列表与安装列表取并集时，
以所有权为"库存里有什么"的基准。

方法按优先级组合（详见 `references/methods-library.md`）：

| 方法 | 凭据 | 适用 |
|---|---|---|
| L1 Web API GetOwnedGames | API key + 账号"游戏详情"公开 | 最稳定，一次调用全量 |
| L2 社区 games 页 | 匿名（详情公开）或 steamLoginSecure Cookie | 详情非公开时需 Cookie |
| L3 浏览器控制登录 | 用户手动登录一次 | **推荐的凭据获取方式**：Playwright 弹出系统 Edge/Chrome，用户登录（支持 Steam Guard），自动提取 Cookie 存本地配置 |
| L4 许可页审计 | Cookie | 可选：全集审计找漏项（只出报告不进列表） |
| 本地 manifest 扫描 | 无 | 安装状态 + 家庭共享残留检测 |

执行：`python scripts/fetch_library.py`（配置见 `scripts/local_config.template.json`）。
产出 `steam_library.csv` + diff 报告。

**汇报内容**：来源方法、总款数、已安装数、与用户预期的差异（如用户知道有某游戏但列表没有）。
**等待确认**。

## 步骤 2：分类体系设计 + 预分类

两条路线，问用户选哪条：

**A. 完全自定义**：用户直接给出类目。
**B. ABCDE 方法论预生成**（推荐，详见 `references/categories-guide.md`）：按抓到的列表统计
自动生成一套类目提案：
- A 状态（仅已安装，互斥）：正在玩/计划玩/长线常驻/暂时搁置
- B 系列：从列表中自动聚类名称前缀 + 知名系列，规模 ≥2 才立类
- C 类型：玩法类型（视觉小说/RPG/策略/…），一款可多选
- D 厂商：知名大厂单独成类，小厂/独立归入兜底类
- E 其他：工具软件/音频/视频等非游戏
- **D 厂商细化**：知名大厂（作品 ≥3 或全球知名）单独成类，其余进兜底类（如 D99）。
  兜底类别急着收尾——用 `references/vendor-region.md` 的方法再细化：**联网判厂商国别**
  （把中国厂商单列）＋**名厂逐个独立成类**，长尾才留在兜底。
- **编号规范**：兜底类（"其他"）编号必须是大类内最大号（如 D99），保证排序永远最后；
  中间编号保持连续无空位

预分类：优先用 Steam 元数据（`https://api.steampowered.com/api.steamcmd.net` 等源，
见 `references/methods-review.md` 的标签来源表）+ 名称关键词规则；
让 LLM 按元数据批量打码也可以（每批 25-50 款，输出统一 CSV）。
无法确定 C 类型的进入待确认表，不要留空。

产出：`categories.md`（类目定义文档）+ `preclassification.csv`。
**汇报**：类目数量与代表性成员、待确认数量。**等待确认**。

## 步骤 3：联网逐款复核（可选，强烈推荐）

规则/LLM 预分类的系统性问题是 Steam 商店标签泛滥（Simulation/Action 到处都是），
导致 C 类虚胖。复核方法按成本从低到高（详见 `references/methods-review.md`）：

- **M1 元数据 API**（steamcmd.net）：一次抓全库 store_tags/genres/dev/pub，作为复核底料
- **M2 SteamDB / 商店页 WebFetch**：对可疑款单点核实
- **M3 搜索引擎子代理**：按批次派子代理逐款 WebSearch 核实玩法后修正分类
  （批处理协议、格式校验见 `references/methods-review.md`）

**子代理数量按用户情况增减**（并发上限、预算、时间要求、服务商稳定性），探测方法与
调度参数决策表见 `references/methods-review.md`。默认策略：先双发探测上限，被拒即回落。

自定义类目/收紧口径时，先跑**类目体检**（`scripts/overlap_check.py`，见 `references/category-quality.md`），
只对高重叠泛化类做「准入+排除+锚点」收紧，别全类目一刀切。
追求高准确度时做**双遍交叉**：同批独立跑两遍 → `scripts/compare_passes.py` 比对 → 冲突三选一
（用户拍板/第三遍/多数表决）。merge 前必跑 `review_tools.py check` 查覆盖率/漏行。

复核后汇总为 `preclassification_reviewed.csv` + 变化报告。
**汇报**：复核覆盖数、修正数、变化样例、实际使用的并发与批次参数。**等待确认**。

## 步骤 4：生成收藏集并写入 Steam

1. 由分类表 + 类目定义生成 `steam_collections.json`
   （`python scripts/build_collections.py`，格式见 `references/write-guide.md`）
2. **写前确认（强制）**：向用户展示 —— 将移除多少个旧收藏集、写入多少个新收藏集、
   备份路径；并要求用户先完全退出 Steam（含托盘）。**用户明确同意后才执行写入**。
3. `python scripts/write_steam.py`（内置 Steam 运行守卫 + 双备份 + 原子写入 + JSON 二次校验）
4. 写入成功后提示用户启动 Steam 查看效果，并告知回滚方法（备份文件覆盖回原位）。
   **汇报**并等用户确认生效。

## 增量模式：已分类过，库里加了新游戏

适用：`step2/preclassification.csv` 已存在且基本完整，之后买了/领了新游戏、退款移除了
游戏、或需要修正个别游戏。不重跑四步，只处理与总表的差异。
详细协议见 `references/incremental-guide.md`，产出放 `step5/`。

1. `python scripts/fetch_library.py` 刷新列表（diff 报告即新增/移除/安装变化）
2. `python scripts/incremental.py detect [appid ...]` → `step5/diff_report.txt`；
   位置参数可强制重分类指定款（待确认的/用户点名的）
3. **新装游戏的 A 状态必须问用户**（或按 categories.md 默认档填写）——A 是用户个人状态
4. `python scripts/incremental.py fetch-info` 增量抓元数据（缓存续传，含标签 ID→名称映射）
5. 分类新增款：量少（≤10 款）主会话逐款搜索直接分；量多走 `prepare` → 子代理
   （协议同步骤3）→ `merge`
6. 汇报新增/移除/A 状态/待确认 → 用户确认后 `incremental.py apply [--prune]` 合并总表
   （自动同步 installed 列、清空已卸载款的 A、备份后写入）
7. 重跑 `build_collections.py` → 写前确认 → `write_steam.py`（与步骤4相同）

## 通用守则

- 每步产出物放独立子目录（`step1/` `step2/` …），保持工作区整洁
- 凭据（Cookie/API key）只存本地配置文件，绝不写进任何产出物或汇报文本
- 一切写入类操作（覆盖用户文件、写 Steam）之前必须先备份并向用户确认
- 网络抓取带重试与退避；失败时给出可操作的下一步提示而不是静默失败
- 遇到本 skill 未覆盖的情况，查 `references/pitfalls.md` 的已知问题清单
- **长会话防打转**：每个步骤收尾调用 `python scripts/handoff.py --write --note "..."` 更新 `HANDOFF.md`
  （结构见 `references/handoff.md`）；**上下文接近上限、开始重复时**，先落盘再建议用户开新窗口接续

## 文件结构

```
steam-collection-skill/
  SKILL.md                     本文件 (agent 执行入口)
  README.md                    人类用户使用说明 (技术向速览)
  使用说明-新手版.txt           人类用户使用说明 (零基础手把手, 纯文本)
  references/
    methods-library.md         步骤1 各抓取方法详述（含浏览器控制）
    categories-guide.md        步骤2 ABCDE 类目方法论与预生成流程
    methods-review.md          步骤3 标签来源与子代理批处理协议
    write-guide.md             步骤4 云存储格式与写入协议
    incremental-guide.md       增量模式：新增游戏只分类新增部分
    vendor-region.md           厂商兜底类细化：联网判国别 + 名厂独立成类
    handoff.md                 会话接续：状态外置与 HANDOFF 协议
    category-quality.md        类目体检：重叠矩阵 + 准入/排除 + 锚点
    options.md                 分类策略档位（精细度/属性/收紧/复核深度/预算）
    pitfalls.md                实战踩坑清单（遇到异常先查这里）
  scripts/
    local_config.template.json 配置模板（使用前复制为 local_config.json 并填写）
    fetch_library.py           步骤1 抓取（含 --login 浏览器登录）
    build_collections.py       步骤4 收藏集 JSON 生成
    write_steam.py             步骤4 写入（守卫/备份/原子写）
    review_tools.py            步骤3 批次切分/汇总/回写工具
    vendor_region.py           厂商兜底类细化（prepare/merge/classify/split）
    handoff.py                 生成/刷新 HANDOFF.md 骨架
    overlap_check.py           类目体检：两两类目重叠矩阵
    compare_passes.py          双遍复核比对：逐款找不一致
    incremental.py             增量模式 detect/fetch-info/prepare/merge/apply
```
