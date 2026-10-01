# 厂商兜底类细化：国别判定 + 名厂独立成类

厂商维度（D）的兜底类（如 `D99 厂商-其他/独立/小厂/待确认`）容易变成"垃圾桶"：
名厂、中国厂商、长尾独立工作室全塞在一起，失去筛选价值。本文给出两件可复用的处理：

1. **国别判定**：把兜底类里的**中国厂商**拎出来，归入「中国厂商」类；
2. **名厂独立成类**：把兜底类里**知名厂商**逐个独立成类，长尾留在兜底。

> 关键原则：**必须联网核实厂商来源，严禁凭名字判断**。
> 很多中国团队用英文/拼音名（`AsicxArt`=四川成都、`Hunter Studio`=广州），
> 反而一些看着像中国的名字是海外的。地区字段（`supported_languages`）也没用——
> 简体中文本地化太普遍，示例库里 D99 有 330/414 都支持简中，无法区分。

---

## 一、抽取「去重工作室」，而不是逐款游戏

兜底类往往成员多但工作室高度长尾（示例：414 款 = 422 个去重工作室，277 个只出现 1 款）。
**按游戏查很贵，按工作室查一次建表、终身复用**，增量新游戏直接查表。

抽取来源：元数据里的 `developer` 与 `publisher`（开发 + 发行），去重。

```bash
python scripts/vendor_region.py prepare --fallback D99 --size 45
# -> step3/vendors/studios.csv + batches/batch_NNN.txt（每行：序号 | 名称 | 角色 | 关联游戏数 | 示例）
```

## 二、联网判国别（子代理批处理）

用 `references/methods-review.md` 的子代理协议，但**输出只用序号**（工作室名常含英文逗号，写名字会破坏 CSV）：

```
序号,地区,依据
```

- 地区码：`CN` / `JP` / `KR` / `EUUS`（欧美澳新）/ `OTHER`
- `CN` = 中国大陆 **+ 港澳台**；**中国团队/中国人创立、注册海外** → 仍 `CN`，依据注明
- 以**开发工作室来源**为准；发行商按其**公司来源**判
- 查不到 → `OTHER`，依据写 `【存疑】`
- 知名大厂凭常识；**疑似中国/亚洲独立小厂必须 WebSearch**（每个最多 1 次）

```bash
python scripts/vendor_region.py merge            # 预览
python scripts/vendor_region.py merge --apply    # 产出 studio_region.json 并把 CN 并入目标类
```

产物 `step3/vendors/studio_region.json`（`工作室 -> {region, reason}`），此后增量直接复用：
`vendor_region.py classify --meta parsed_meta.csv` 可据表直接回填，无需再联网。

## 三、名厂逐个独立成类

**阈值：成员 ≥2 且「全球知名」**（知名大厂不受 ≥3 限制）。**发行商也可独立成类。**

给一份厂商清单（JSON），脚本会：新增 D 类定义、更新匹配规则、把对应游戏从兜底类迁出。
同一游戏开发与发行分属两家时可同时进两类（D 多值），例如 `D31 Rocksteady;D35 WB Games`。

```json
[
  {"code": "D23", "name": "厂商-Rockstar",   "pattern": "Rockstar"},
  {"code": "D24", "name": "厂商-Freebird Games", "pattern": "Freebird Games"}
]
```

```bash
python scripts/vendor_region.py split --list vendors.json --fallback D99
python scripts/vendor_region.py split --list vendors.json --fallback D99 --apply
```

编号规则：新类编号从**兜底类之前**连续插入（`D23`、`D24`…），**兜底类编号不变**（仍是 `D99`），
保证任何排序下兜底类都在最后（见 `categories-guide.md` 编号规范）。

## 四、排除项

- 占位/非厂商字符串（如 `本游戏已经下架退市`、`-`、`N/A`）**不得**当作厂商。
- 折叠状态：收藏集在客户端的折叠属 Steam **本机 UI**（`localconfig.vdf` 的 `mapCollapsedState`），
  与本流程无关，不由 skill 写入。

## 五、验收

- 兜底类里可辨识的中国厂商全部进入「中国厂商」类；
- 名厂逐个独立成类；长尾仍留兜底；
- `studio_region.json` 覆盖所有去重工作室，增量可直接复用。
