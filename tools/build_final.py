# -*- coding: utf-8 -*-
"""
组装 src/puzzles.js。
  档0 四字好词 / 档1 成语挑战：来自 puzzles_data.json
  档2 十字成语：多条成语纵横交叉，交叉字待填（crossword 的核心）
三种网格形状轮换：
  A 单十字（2词）   B 梳子（1横+2竖，3词）   C 双横阶梯（2横+1竖，3词）
填空规则：每条成语首字预填作锚点，其余（含交叉字）待填，空格显示拼音。
run: python tools/build_final.py
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'src', 'puzzles_data.json')
DICT = os.path.join(HERE, '..', 'docs', 'extracted_entries.json')
OUT = os.path.join(HERE, '..', 'src', 'puzzles.js')


def load():
    with open(DATA, encoding='utf-8') as f:
        return json.load(f)


def load_dict():
    if not os.path.exists(DICT):
        return []
    with open(DICT, encoding='utf-8') as f:
        return json.load(f)


def build_pymap(data, dict_entries):
    m = {}
    for it in data['haoci'] + data['duizhan']:
        for i, ch in enumerate(it['w']):
            m.setdefault(ch, it['py'][i])
    for e in dict_entries:
        for i, ch in enumerate(e['w']):
            if i < len(e['py']):
                m.setdefault(ch, e['py'][i])
    return m


# ---------- 找共享字成语对（复用） ----------
def shared_char(a, b):
    for c in a:
        if c in b:
            return c
    return None


def all_words(data, dict_entries):
    # 只用人工核对过的干净词，不用词典 OCR 脏词
    ws = [it['w'] for it in data['haoci']] + [it['w'] for it in data['duizhan']]
    return list(dict.fromkeys(w for w in ws if len(w) == 4))


# ============ 三种形状的布局器 ============
# 每个盘返回 cells = [{r,c,ch,py,pre}]，pre=True 表示预填锚点

def shape_plus(a, b, pymap):
    """A: 单十字。横 a 在第0行；竖 b 穿过 a 的共享字。
    锚点 = 每条成语的第一个"非共享"字；交叉字(共享字)永远待填。"""
    sh = shared_char(a, b)
    if not sh:
        return None
    ia, ib = a.index(sh), b.index(sh)
    cells = []
    # 横 a 的锚点：第一个非共享字
    anchor_a = next((c for c in range(len(a)) if c != ia), 0)
    for c, ch in enumerate(a):
        cells.append({"r": 0, "c": c, "ch": ch, "py": pymap.get(ch, ""),
                      "pre": (c == anchor_a)})
    # 竖 b 的锚点：第一个非共享字
    anchor_b = next((i for i in range(len(b)) if i != ib), 0)
    s = -ib
    for i, ch in enumerate(b):
        if i == ib:
            continue
        cells.append({"r": s + i, "c": ia, "ch": ch, "py": pymap.get(ch, ""),
                      "pre": (i == anchor_b)})
    return norm_cells(cells, len(a))


def shape_comb(a, b1, b2, pymap):
    """B: 梳子。横 a 在中间行；两条竖 b1、b2 分别从 a 的两个不同字向下伸。"""
    sh1, sh2 = shared_char(a, b1), shared_char(a, b2)
    if not sh1 or not sh2 or sh1 == sh2:
        return None
    ia1, ia2 = a.index(sh1), a.index(sh2)
    ib1, ib2 = b1.index(sh1), b2.index(sh2)
    cells = []
    # 横 a 放在第 1 行（留出上方的空间）
    for c, ch in enumerate(a):
        cells.append({"r": 1, "c": c, "ch": ch, "py": pymap.get(ch, ""), "pre": (c == 0)})
    # 竖 b1（向下，共享字对齐到 r=1）
    s1 = 1 - ib1
    for i, ch in enumerate(b1):
        if i == ib1:
            continue
        cells.append({"r": s1 + i, "c": ia1, "ch": ch, "py": pymap.get(ch, ""),
                      "pre": (i == 0)})
    # 竖 b2
    s2 = 1 - ib2
    for i, ch in enumerate(b2):
        if i == ib2:
            continue
        cells.append({"r": s2 + i, "c": ia2, "ch": ch, "py": pymap.get(ch, ""),
                      "pre": (i == 0)})
    return norm_cells(cells, len(a))


def shape_stair(a, b, c, pymap):
    """C: 双横阶梯。横 a 在第0行，横 b 在第2行；竖 c 穿过 a 与 b 各共享一字。"""
    sh_a = shared_char(a, c)
    sh_b = shared_char(b, c)
    if not sh_a or not sh_b or sh_a == sh_b:
        return None
    ia = a.index(sh_a); ic_a = c.index(sh_a)
    ib = b.index(sh_b); ic_b = c.index(sh_b)
    cells = []
    # 横 a（第0行）
    for ci, ch in enumerate(a):
        cells.append({"r": 0, "c": ci, "ch": ch, "py": pymap.get(ch, ""), "pre": (ci == 0)})
    # 横 b（第2行）
    for ci, ch in enumerate(b):
        cells.append({"r": 2, "c": ci, "ch": ch, "py": pymap.get(ch, ""), "pre": (ci == 0)})
    # 竖 c：穿过 a 的 ia 列 和 b 的 ib 列——两条横错位，竖 c 必须同列
    # 这里约束 a/b 的共享字列必须相同，否则做不成一根竖线；先放共享列=ia
    if ia != ib:
        return None
    # 竖 c 从上方伸到下方，覆盖 a(0,ia) 与 b(2,ia)
    # c 中 sh_a 与 sh_b 是不同字，位置 ic_a, ic_b；要求 |ic_b-ic_a|==2 对齐到 r0 与 r2
    if abs(ic_b - ic_a) != 2:
        return None
    s = 0 - ic_a
    for i, ch in enumerate(c):
        if i == ic_a or i == ic_b:
            continue
        cells.append({"r": s + i, "c": ia, "ch": ch, "py": pymap.get(ch, ""),
                      "pre": (i == 0)})
    return norm_cells(cells, max(len(a), len(b)))


def norm_cells(cells, cols):
    # 平移到非负坐标，去重
    minr = min(c["r"] for c in cells)
    if minr < 0:
        for c in cells:
            c["r"] -= minr
    seen = {}
    for c in cells:
        key = (c["r"], c["c"])
        if key in seen:
            # 已有（交叉格），保留（pre 取 or）
            seen[key]["pre"] = seen[key]["pre"] or c["pre"]
            continue
        seen[key] = c
    cells = list(seen.values())
    rows = max(c["r"] for c in cells) + 1
    maxc = max(c["c"] for c in cells) + 1
    cols = max(cols, maxc)
    return {"cells": cells, "rows": rows, "cols": cols}


# ============ 生成 50 盘：单十字，共享字居中，交叉字待填 ============
def make_cross_boards(data, dict_entries, pymap):
    ws = all_words(data, dict_entries)
    from collections import defaultdict
    groups = defaultdict(list)   # shared -> [(a,b)]
    for a in ws:
        for b in ws:
            if a == b:
                continue
            sh = shared_char(a, b)
            if not sh:
                continue
            ia = a.index(sh)
            ib = b.index(sh)
            # 只要求"横成语"的共享字在中间（第2或第3字），交叉点居中成十字；
            # 竖成语只要穿过横成语即可（ib 不限）。
            if ia not in (1, 2):
                continue
            groups[sh].append((a, b))
    chars = sorted(groups.keys(), key=lambda c: -len(groups[c]))
    items = []
    seen = set()
    round_i = 0
    need = 50
    while len(items) < need:
        progress = False
        for sh in chars:
            grp = groups[sh]
            if not grp:
                continue
            k = round_i % len(grp)
            a, b = grp[k]
            key = tuple(sorted((a, b)))
            if key in seen:
                continue
            seen.add(key)
            lay = shape_plus(a, b, pymap)
            if not lay:
                continue
            items.append({
                "name": "十·" + str(len(items) + 1),
                "words": [a, b],
                "rows": lay["rows"],
                "cols": lay["cols"],
                "cells": lay["cells"],
                "hint": "横竖都是成语，交叉的字两边都要用",
            })
            progress = True
            if len(items) >= need:
                break
        round_i += 1
        if not progress:
            break
    return items


def norm(items, em):
    return [{"w": it['w'], "py": it['py'], "b": [1], "em": em, "hint": it['hint']} for it in items]


def main():
    data = load()
    dict_entries = load_dict()
    pymap = build_pymap(data, dict_entries)
    cross_items = make_cross_boards(data, dict_entries, pymap)

    out = [
        {"name": "四字好词", "distract": 2, "items": norm(data['haoci'], '🧡')},
        {"name": "成语大挑战", "distract": 3, "items": norm(data['duizhan'], '🧿')},
        {"name": "十字成语", "kind": "cross", "distract": 2, "items": cross_items},
    ]
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write("window.PZ_PUZZLES = " + json.dumps(out, ensure_ascii=False, indent=1) + ";\n")
    print("好词", len(data['haoci']), "成语", len(data['duizhan']), "十字", len(cross_items))


if __name__ == "__main__":
    main()