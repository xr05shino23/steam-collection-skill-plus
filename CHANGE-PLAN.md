# CHANGE-PLAN：steam-collection-skill 优化改动清单

> 分支：`feature/category-quality-flexibility`
> 依据：2026-10-01 对 602 款真实库跑完全流程（跨两个会话窗口）的实战记录。
> 目标：让用户在「分类精细度、维度、复核深度、成本」上有**明确的选择**，并让长会话可无损接续、分类质量可衡量。

## 实现状态（2026-10-01）

| 项 | 状态 | 落地 |
|---|---|---|
| P0 会话接续 | ✅ 已实现 | `references/handoff.md`、`scripts/handoff.py` |
| P1 类型+属性双维度 | ✅ 已实现 | `categories-guide.md`（F 特性）、`build_collections.py` |
| P1 类目体检 | ✅ 已实现 | `references/category-quality.md`、`scripts/overlap_check.py` |
| P2 分类策略档位 | ✅ 已实现 | `references/options.md`、`SKILL.md` 步骤0 |
| P2 复核质量 | ✅ 已实现 | `scripts/compare_passes.py`、`review_tools.py check`、`methods-review.md` |
| P3 带权标签 | ✅ 已实现（文档+约定） | `methods-review.md` |
| P3 文档/坑清单 | ✅ 已实现 | `pitfalls.md`（分类质量 + 会话工程） |
| P2 厂商国别细分 | ✅ 已实现 | `references/vendor-region.md`、`scripts/vendor_region.py` |

两个提交：`7c8ffc9`（厂商+接续+体检/属性）、`6bef8e4`（档位+复核质量+文档）。

---

## 0. 背景：本次实战暴露的问题（都带数据）

| # | 问题 | 实战证据 |
|---|---|---|
| 1 | **C 类预分类几乎不可用** | 复核前 225 款里 C 类型完全正确的仅 **17 款（7.6%）**；复核后保守 **90%+**。格式准确率 100% |
| 2 | **泛化类互相吸收、虚胖** | 每款平均挂 **3.7 个** C 类；C10+C11 重叠 0.33、C06+C07 0.25、C01+C19 0.34 |
| 3 | **属性被当成类型** | `C19 多人合作` 与动作重叠 0.34，跟任何类都沾边；迁成 `F01 特性-多人合作` 后重叠消失 |
| 4 | **主观口径反复、易漂移** | C02/C13 收紧跑了 3 遍，两遍严格口径仍有 **46/408（11%）分歧**；放宽口径又引入误判（Viridi 被加 C02） |
| 5 | **子代理输出不可信** | 列错位（Banana 把「留休闲」写成「留冒险」）、漏行（batch_019 少 1 款） |
| 6 | **长上下文导致思维循环** | 上半场 303 条消息后开始原地打转，被迫换窗口；靠 `HANDOFF.md` 才接上 |
| 7 | **标签被当"有/无"** | Steam 标签本有序（相关性），却未按权重取；本地化标签（增量=Incremental、挂机游戏=Idle）差点漏判 |
| 8 | **写入风险** | 原 `write_steam.py` 会删系统 `favorite/hidden`；`userdata` 目录名应为 SteamID32 |

**收紧后的效果（证明方法有效）**：平均 C 类 **3.7 → 2.34**；挂 4–5 类的游戏 359 → 77 款；C10+C11 0.33→0.24、C06+C07 消失。

---

## 1. 改动总览

| 优先级 | 改动 | 新增文件 | 修改文件 |
|---|---|---|---|
| **P0** | 状态外置 / 会话接续机制 | `references/handoff.md`、`scripts/handoff.py` | `SKILL.md` |
| **P1** | 类型 + 属性双维度 | — | `categories-guide.md`、`build_collections.py`、`SKILL.md`、`README.md` |
| **P1** | 类目体检（重叠矩阵） | `references/category-quality.md`、`scripts/overlap_check.py` | `SKILL.md` 步骤2/3 |
| **P2** | 分类策略档位（用户选择） | `references/options.md` | `SKILL.md`、`README.md` |
| **P2** | 「准入+排除+锚点」模板 | （并入 `category-quality.md`） | `categories-guide.md` |
| **P2** | 复核质量：一致性校验/双遍/置信度 | `scripts/compare_passes.py` | `review_tools.py`、`methods-review.md` |
| **P2** | 厂商国别细分（D99 不再"垃圾桶"） | `references/vendor-region.md`、`scripts/vendor_region.py` | `categories-guide.md`、`build_collections.py` |
| **P3** | 带权标签 | — | `methods-review.md`、`incremental.py` |
| **P3** | 文档 / 坑清单增补 | — | `pitfalls.md`、`categories-guide.md` |

---

## 2. 详细改动

### P0 · 状态外置与「换窗口无损接续」

**目标**：长任务不再因上下文过长而思维循环；新窗口读一个文件即可接续。

- 新增 `references/handoff.md`：约定 `HANDOFF.md` 的结构（当前阶段 / 待办 / 已确认决策 / 口径版本 / 关键文件 / 备份与回滚路径 / 严禁事项）。
- 新增 `scripts/handoff.py`：扫描 `step*/` 与 `step2/backup/`，自动生成/更新 `HANDOFF.md`（幂等、带时间戳）。
- `SKILL.md`：每个步骤收尾时调用一次 handoff 生成；明确「上下文接近上限时先落盘再换窗口」。

**验收**：任意时刻 `python scripts/handoff.py` 能产出一份文档，新会话仅读它即可知道下一步。

### P1 · 类目模型：类型 + 属性双维度

**目标**：属性（合作/VR/手柄/成就…）不再污染类型。

- `categories-guide.md`：新增维度定义。
  - 维度用字母：A 状态 / B 系列 / **C 类型（玩法）** / D 厂商 / E 其他 / **F 特性（属性）**。
  - 判别：描述「怎么玩」→ C；描述「能不能一起玩/怎么玩得舒服」→ F。
- `build_collections.py`：`FIELD` 支持任意维度字母（已在本分支支持 `F -> F_tags`）。
- `preclassification.csv`：增加 `F_tags` 列（默认空）。
- 用户可选是否生成 F 收藏集；不选则 F 列留空、不影响其他维度。

**验收**：示例库里「多人合作」只出现在 `F01 特性-多人合作`，不在任何 C 类。

### P1 · 类目体检（收紧前必做）

**目标**：用数据指出「哪两个类在互相吸收」，驱动定向收紧，而非全量重跑。

- 新增 `scripts/overlap_check.py`：算任意两 C 类的 Jaccard、每款类数分布，产出 `step2/overlap_matrix.md`，并对 `J > 0.25` 的对告警。
- 新增 `references/category-quality.md`：体检指标（重叠率、类数分布、可解释性）+ 何时收紧的判据。
- `SKILL.md` 步骤 2/3 之间插入「类目体检」节点：把体检结果给用户，由其点名要收紧的类。

**验收**：对示例库输出 top 重叠对，能复现 C10+C11/C06+C07 等告警。

### P2 · 分类策略档位（把选择交给用户）

**目标**：用户按偏好/预算选档，agent 照执行。

- 新增 `references/options.md`，定义可选开关：

  | 维度 | 选项 |
  |---|---|
  | 精细度 | 精简（每款 1 主类型）/ 标准（1 主 + ≤2 次）/ 宽松（多选不限） |
  | 属性收藏集 | 开 / 关（要哪些 F 类） |
  | 泛化类收紧 | 开（准入+排除）/ 关 |
  | 复核深度 | 不复核 / 只查可疑款 / 全量 / 全量双遍交叉 |
  | 预算与并发 | 低/中/高（映射批次大小与并发，内置探测） |

- `SKILL.md` 开工前信息收集处增加「分类策略」一节；`README.md` 加一张对照表帮用户选。

**验收**：用户能一次性说出档位，agent 据此调整步骤 2/3 行为。

### P2 · 「准入 + 排除 + 锚点」类目模板

**目标**：把主观边界写成可执行定义，减少子代理分歧。

- `categories-guide.md` 模板升级为每类三件套：
  ```
  - C13 类型-休闲
    准入: 轻量、低门槛、以休闲为主
    排除: 以战斗/竞技/生存/大RPG为主
    锚点: 留=胡闹厨房/Beat Saber；去=求生之路
  ```
- 锚点样例建议每类 3–5 个，作为子代理的 few-shot。

**验收**：同批用「仅准入」与「准入+排除+锚点」各跑一遍，分歧率下降。

### P2 · 复核质量增强

**目标**：抓出子代理的格式错误与口径分歧。

- `review_tools.py` 校验器新增：
  - 编码白名单、列数、**缺行检测**（对比批次清单）；
  - **「依据 ↔ 结论」一致性自检**（自动发现列错位，如本次 Banana）。
- 新增 `scripts/compare_passes.py`：两遍独立复核逐款比对，产出 `disagreements.csv` + 报告。
- `methods-review.md`：加入「双遍交叉 + 冲突处理三选一（第三遍裁决 / 用户拍板 / 多数表决）」与「置信度列 + 待确认表」。
- 可选：**金标准回归集**（30–50 款标准答案），每次改口径后回归验证。

**验收**：对本次数据跑校验器能复现「漏 1 行」与「列错位」两类告警。

### P2 · 厂商国别细分（D99 优化）

**目标**：D99（其他/独立/小厂/待确认）不再混入可辨识厂商；把中国厂商单列，长尾兜底更干净。

**实战证据**：D99 = 414 款却有 **422 个去重工作室**（277 个只出现 1 次）——按厂商立类没意义，但**按国别聚合**有意义。联网判定后 **87 个中国厂商** → **77 款**并入 `D21 厂商-中国厂商`（D21 15→92，D99 414→337）。

**改动（两块）**：

**① 国别判定（联网，不靠名字）**
- 新增 `scripts/vendor_region.py`：抽取兜底类里的**去重工作室**（开发商+发行商），切批联网判国别，产出 `studio_region.json`（一次建表、增量复用）。
- 新增 `references/vendor-region.md`：判定准则。
  - 地区码 `CN / JP / KR / EUUS / OTHER`；
  - **必须联网核实**，严禁凭名字中英/拼音判断（`AsicxArt`、`Hunter Studio` 实为中国）；
  - **港澳台算 CN**；**中国团队注册海外仍算 CN**（依据注明）；以**开发工作室来源**为准；
  - 排除占位/非厂商字符串（如"本游戏已经下架退市"）。
- 命中 CN → 并入 `D21 厂商-中国厂商`。

**② 名厂逐个独立成类**
- 阈值：**成员 ≥2 且「全球知名」** → 独立成一类（知名大厂不受 ≥3 限制）；
- **发行商也算**，可独立成类；
- 逐个独立，编号从兜底类前插入（本次 `D23`–`D52`，共 30 个）；**兜底类编号不变（`D99`）**；
- **长尾 / 不著名工作室留在 `D99`**；
- 同一游戏开发与发行分属两家时，可同时进两类（D 多值），如 `D31 Rocksteady;D35 WB Games`。

**其他**
- `categories-guide.md`：把「国别判定 + 名厂拆分」纳入 D 维度预生成。
- `build_collections.py`：无须改动（沿用 D 多值）。
- **非目标**：收藏集在客户端的**折叠状态**属 Steam 本机 UI（`localconfig.vdf`），**不由本 skill 写入**（用户自理）。

**验收**：对示例库，D99 里可辨识中国厂商进 `D21`；名厂逐个独立成类（本次 30 个）；长尾仍留 `D99`；`studio_region.json` 覆盖所有去重工作室。

---

### P3 · 带权标签

**目标**：减少「沾边就加」。

- `methods-review.md`：标签按**顺序/占比**取（如只认前 5 个标签，或占比阈值），而非有/无。
- `incremental.py`：标签映射补齐中英对照（增量=Incremental、挂机游戏=Idle 等）。

**验收**：同一批预分类，虚胖类数下降。

### P3 · 文档与坑清单

- `pitfalls.md` 增补：子代理「依据与列矛盾」、泛化类互吸、VN/轻战斗口径歧义、**只收紧高重叠泛化类（勿全类目一刀切）**、`userdata`= SteamID32。
- `categories-guide.md` 增补「泛化类识别」与「属性维度」。

---

## 3. 涉及文件汇总

**新增**
```
references/handoff.md
references/category-quality.md
references/options.md
references/vendor-region.md
scripts/handoff.py
scripts/overlap_check.py
scripts/compare_passes.py
scripts/vendor_region.py
```

**修改**
```
SKILL.md              （步骤衔接：体检节点、档位、handoff、属性维度）
README.md             （档位对照表、属性维度说明）
references/categories-guide.md   （F 维度、准入+排除+锚点模板、泛化类识别）
references/methods-review.md     （双遍交叉、置信度、带权标签、一致性校验）
references/pitfalls.md           （新增坑）
scripts/build_collections.py     （多维度 FIELD；本分支已含 F 支持）
scripts/review_tools.py          （校验器增强）
scripts/incremental.py           （标签中英映射）
```

---

## 4. 实施顺序建议

1. **P0 接续机制**（解决最痛的长会话问题，且独立）
2. **P1 属性维度 + 类目体检**（本分支已起步：`build_collections.py` 支持 F）
3. **P2 档位 + 准入/排除模板 + 复核质量**
4. **P3 带权标签 + 文档**

每项都可独立提交；建议一项一 commit，便于回滚与 review。

---

## 5. 附：本次实战数据（供文档引用）

- 库规模：602 款（自有 331 + 家庭共享 271；已安装 8），家庭组 Anon Tokyo 6/6。
- 步骤1 抓取：社区页 306 → 家庭库接口 759 → 过滤后 602（剔除 171 工具 + 7 软件 + 9 测试服）。
- 步骤2：ABCDE 生成 106 类目（后补 C23 → 107）。
- 步骤3：25 批全量复核；子代理并发上限实测 2；batch_020 卡 12 分钟被重派；C 类型修正 541/602。
- 步骤2→3 准确率：C 类型复核前完全正确 7.6%，复核后估计 90%+。
- 本轮优化后：C02 278→207、C13 227→127、C19→F01；泛化类 C01 236→154、C06 106→46、C07 91→44、C08 128→83、C10 93→46、C11 79→62、C20 56→35；每款 C 数 3.7→2.34。
- 写入：104 收藏集 / 602 款；保留系统 favorite/hidden；双备份。
