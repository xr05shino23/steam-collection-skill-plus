# -*- coding: utf-8 -*-
"""会话接续：生成/刷新 HANDOFF.md 骨架（事实区自动，决策区留人补）。

用法:
  python scripts/handoff.py                       # 打印骨架到终端
  python scripts/handoff.py --write               # 写入 HANDOFF.md（默认仓库根）
  python scripts/handoff.py --write --note "..."  # 追加一条更新记录
  python scripts/handoff.py --file path.md --write

说明: 事实区用 <!-- AUTO:BEGIN --> / <!-- AUTO:END --> 包裹；重复运行只刷新该块，
      人工写的「决策 / 下一步 / 更新记录」原样保留。首次写入生成完整模板。
"""
import argparse, glob, json, os, subprocess, time

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
BEGIN, END = "<!-- AUTO:BEGIN -->", "<!-- AUTO:END -->"


def sh(args):
    try:
        r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=15)
        return (r.stdout or "").strip()
    except Exception:
        return ""


def count_lines(p):
    try:
        with open(p, encoding="utf-8-sig") as f:
            return sum(1 for _ in f) - 1
    except Exception:
        return None


def json_len(p):
    try:
        return len(json.load(open(p, encoding="utf-8")))
    except Exception:
        return None


def latest(dirp, n=3):
    if not os.path.isdir(dirp):
        return []
    fs = sorted((os.path.getmtime(os.path.join(dirp, f)), f) for f in os.listdir(dirp))
    return [f for _, f in fs[-n:]][::-1]


def facts():
    L = ["生成时间：%s" % time.strftime("%Y-%m-%d %H:%M:%S"), ""]
    L.append("**工作区**：`%s`" % ROOT)
    br = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    rm = sh(["git", "remote", "get-url", "origin"])
    if br:
        L.append("- git 分支：`%s`%s" % (br, ("  |  远端：`%s`" % rm) if rm else ""))
    L.append("")
    L.append("**阶段产物**")
    for d in ("step1", "step2", "step3", "step4", "step5"):
        p = os.path.join(ROOT, d)
        if os.path.isdir(p):
            n = sum(len(fs) for _, _, fs in os.walk(p))
            L.append("- `%s/`：%d 个文件" % (d, n))
    cats = json_len(os.path.join(ROOT, "step2", "categories.json"))
    prec = count_lines(os.path.join(ROOT, "step2", "preclassification.csv"))
    coll = json_len(os.path.join(ROOT, "step4", "steam_collections.json"))
    if cats is not None:
        L.append("- 类目定义：%d 项" % cats)
    if prec is not None:
        L.append("- 分类表：%d 款游戏" % prec)
    if coll is not None:
        L.append("- 收藏集：%d 个" % coll)
    L.append("")
    L.append("**最近备份**")
    for d in ("step2/backup", "step4/backup"):
        recent = latest(os.path.join(ROOT, d))
        if recent:
            L.append("- `%s/`：%s" % (d, "、".join(recent)))
    return "\n".join(L)


TEMPLATE = """# 交接文档（HANDOFF）

> 新窗口请先读本文件，即可无损接续任务。协议见 `references/handoff.md`。

## 一句话状态

（待补全：现在到哪一步 / 下一步 / 有无"严禁"事项）

{BEGIN}
{auto}
{END}

## 关键文件

| 文件 | 说明 |
|---|---|
| （待补全） | |

## 已确认的决策

1. （待补全）

## 下一步（新窗口从这里继续）

1. （待补全）

## 注意事项 / 已知坑

- 凭据只存本地 `scripts/local_config.json`，勿提交；
- 写入 Steam 前必须完全退出 Steam，脚本有守卫 + 双备份；
- `userdata` 目录名是 **SteamID32**，不是 SteamID64。

## 更新记录

{notes}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--note", default="")
    ap.add_argument("--file", default=os.path.join(ROOT, "HANDOFF.md"))
    a = ap.parse_args()

    auto = facts()
    if a.note:
        auto_note = "- [%s] %s" % (time.strftime("%Y-%m-%d %H:%M"), a.note)
    else:
        auto_note = ""

    if not a.write:
        print(TEMPLATE.replace("{BEGIN}", BEGIN).replace("{END}", END).replace("{auto}", auto).replace("{notes}", auto_note))
        return

    if os.path.exists(a.file):
        s = open(a.file, encoding="utf-8").read()
        if BEGIN in s and END in s:
            pre, mid, post = s.split(BEGIN, 1)[0], s.split(BEGIN, 1)[1].split(END, 1)[0], s.split(END, 1)[1]
            s = pre + BEGIN + "\n" + auto + "\n" + END + post
            if a.note:
                s = s.rstrip() + "\n" + auto_note + "\n"
        else:
            open(a.file + ".bak", "w", encoding="utf-8").write(s)  # 保底备份
            s = TEMPLATE.replace("{BEGIN}", BEGIN).replace("{END}", END).replace("{auto}", auto).replace("{notes}", auto_note)
    else:
        s = TEMPLATE.replace("{BEGIN}", BEGIN).replace("{END}", END).replace("{auto}", auto).replace("{notes}", auto_note)
    open(a.file, "w", encoding="utf-8").write(s)
    print("已写入", a.file)


if __name__ == "__main__":
    main()
