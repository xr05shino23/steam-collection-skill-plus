# -*- coding: utf-8 -*-
"""步骤4: 生成 Steam 收藏集 JSON。通用版: 类目定义来自 categories.json (不含任何预置类目)。

输入:
  step2/categories.json   类目定义数组: [{"code":"C06","name":"C06 模拟经营","group":"C",
                            "installedOnly":false,"exclusive":false}, ...] (由 agent 依 categories.md 生成)
  step2/preclassification.csv  分类表 (appid,name,installed,A_status,B_series,C_types,D_vendors,E_other,...)
输出:
  step4/steam_collections.json   -> 供 write_steam.py 写入
用法: python build_collections.py [--table 路径] [--defs 路径]
"""
import csv, json, os, base64, hashlib, time, sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)

def P(*p): return os.path.join(ROOT, *p)

def arg_val(flag, default=None):
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv): return sys.argv[i + 1]
    return default

def make_id(code, salt):
    d = hashlib.sha1(("%s:%s" % (salt, code)).encode("utf-8")).digest()[:9]
    return "uc-" + base64.b64encode(d).decode("ascii")

def main():
    salt = os.environ.get("COLLECTION_ID_SALT", "")
    cfgf = os.path.join(BASE, "local_config.json")
    if not salt and os.path.exists(cfgf):
        try: salt = json.load(open(cfgf, encoding="utf-8")).get("collection_id_salt", "")
        except Exception: pass
    assert salt, "缺少 collection_id_salt (local_config.json 或环境变量 COLLECTION_ID_SALT)"
    table = arg_val("--table", P("step2", "preclassification.csv"))
    defs_f = arg_val("--defs", P("step2", "categories.json"))
    rows = list(csv.DictReader(open(table, encoding="utf-8-sig")))
    defs = json.load(open(defs_f, encoding="utf-8"))
    by_appid = {r["appid"]: r for r in rows}
    FIELD = {"A": "A_status", "B": "B_series", "C": "C_types", "D": "D_vendors", "E": "E_other", "F": "F_tags"}
    order = [d["code"] for d in defs]
    # 兜底类 (编码数字为 99 结尾) 强制排各大类最后
    order.sort(key=lambda c: (c[0], 1 if c[1:].startswith("99") else 0, c))
    members = {c: [] for c in order}
    for r in rows:
        for c in order:
            if c in (r.get(FIELD[c[0]]) or "").split(";"):
                members[c].append(int(r["appid"]))
    ts = int(time.time())
    entries, out_defs, summary = [], [], []
    for c in order:
        mem = sorted(set(members[c]))
        if not mem: continue
        d = next(x for x in defs if x["code"] == c)
        cid = make_id(c, salt); key = "user-collections." + cid
        val = json.dumps({"id": cid, "name": d["name"], "added": mem, "removed": []},
                         ensure_ascii=False, separators=(",", ":"))
        entries.append([key, {"key": key, "timestamp": ts, "value": val, "version": "2658",
                              "conflictResolutionMethod": "custom", "strMethodId": "union-collections"}])
        out_defs.append({"id": cid, "code": c, "name": d["name"], "group": c[0], "count": len(mem),
                         "installedOnly": d.get("installedOnly", c[0] == "A"),
                         "exclusive": d.get("exclusive", c[0] == "A")})
        summary.append((d["name"], len(mem)))
    outd = P("step4"); os.makedirs(outd, exist_ok=True)
    json.dump(entries, open(os.path.join(outd, "steam_collections.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(out_defs, open(os.path.join(outd, "collection_definitions.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("收藏集: %d | 游戏表: %d 行" % (len(entries), len(rows)))
    for n, k in summary: print("  %-40s %4d" % (n, k))
    print("下一步: 向用户展示写前确认清单 (见 references/write-guide.md), 确认后运行 write_steam.py")

if __name__ == "__main__":
    main()
