# -*- coding: utf-8 -*-
"""
组装 src/puzzles.js。
  档0 四字好词 / 档1 成语挑战：来自 puzzles_data.json
  档2 十字成语（crossword）：两种块状形状
    A 单十字（2词）：一横一竖交叉
    B H形/双横一竖（3词）：竖成语穿两条横成语，形成"工"字块
交叉字一律待填（crossword 核心）；每条成语预填第一个非共享字作锚点。
run: python tools/build_final.py
"""
import json, os, random
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'src', 'puzzles_data.json')
OUT = os.path.join(HERE, '..', 'src', 'puzzles.js')


def load():
    with open(DATA, encoding='utf-8') as f:
        return json.load(f)


def build_pymap(data):
    m = {}
    for it in data['haoci'] + data['duizhan']:
        for i, ch in enumerate(it['w']):
            m.setdefault(ch, it['py'][i])
    return m


def clean_words(data):
    ws = [it['w'] for it in data['haoci']] + [it['w'] for it in data['duizhan']]
    return list(dict.fromkeys(w for w in ws if len(w) == 4))


def clean_words_nodup(data):
    ws = clean_words(data)
    return [w for w in ws if len(set(w)) == 4]


def norm_cells(cells, cols):
    minr = min(c['r'] for c in cells)
    if minr < 0:
        for c in cells:
            c['r'] -= minr
    seen = {}
    for c in cells:
        key = (c['r'], c['c'])
        if key in seen:
            seen[key]['pre'] = seen[key]['pre'] or c['pre']
            continue
        seen[key] = c
    cells = list(seen.values())
    rows = max(c['r'] for c in cells) + 1
    maxc = max(c['c'] for c in cells) + 1
    cols = max(cols, maxc)
    return {"cells": cells, "rows": rows, "cols": cols}


def cell(r, c, ch, pymap, pre):
    return {"r": r, "c": c, "ch": ch, "py": pymap.get(ch, ""), "pre": pre}


# ---------- 形状 A：单十字 ----------
def shape_plus(a, b, pymap):
    sh = next((c for c in a if c in b), None)
    if not sh:
        return None
    ia, ib = a.index(sh), b.index(sh)
    cells = []
    anchor_a = next((c for c in range(4) if c != ia), 0)
    for c, ch in enumerate(a):
        cells.append(cell(0, c, ch, pymap, c == anchor_a))
    anchor_b = next((i for i in range(4) if i != ib), 0)
    s = -ib
    for i, ch in enumerate(b):
        if i == ib:
            continue
        cells.append(cell(s + i, ia, ch, pymap, i == anchor_b))
    return norm_cells(cells, 4)


# ---------- 形状 B：H形（双横一竖） ----------
def shape_h(a, c, b, pymap):
    """竖 b 穿两条横 a(上)、c(下)。返回 cells 或 None。
    要求：a[ia]==b[ka]，c[ia]==b[kc]，kc>ka（横 c 在横 a 下方）。"""
    shared_ab = set(a) & set(b)
    shared_cb = set(c) & set(b)
    if not shared_ab or not shared_cb:
        return None
    for ia in (1, 2, 0, 3):  # 优先中间列，交叉点居中
        if a[ia] not in shared_ab or c[ia] not in shared_cb:
            continue
        # b 中与 a[ia] 相等的字、与 c[ia] 相等的字
        ka = b.index(a[ia])
        kc = b.index(c[ia])
        if kc <= ka:
            continue  # 保证横 c 在下方
        cells = []
        # 横 a 在第 0 行
        anchor_a = next((k for k in range(4) if k != ia), 0)
        for k, ch in enumerate(a):
            cells.append(cell(0, k, ch, pymap, k == anchor_a))
        # 竖 b 在 col ia，第 k 字在 (k - ka, ia)
        anchor_b = next((k for k in range(4) if k != ka and k != kc), 0)
        for k, ch in enumerate(b):
            if k == ka or k == kc:
                continue
            cells.append(cell(k - ka, ia, ch, pymap, k == anchor_b))
        # 横 c 在第 (kc-ka) 行
        c_row = kc - ka
        anchor_c = next((k for k in range(4) if k != ia), 0)
        for k, ch in enumerate(c):
            cells.append(cell(c_row, k, ch, pymap, k == anchor_c))
        return norm_cells(cells, 4)
    return None


# ---------- 生成 ----------
def build_cross(data, pymap):
    ws = clean_words(data)          # 含叠字，横成语用
    ws_nodup = clean_words_nodup(data)  # 竖成语用（无叠字避免歧义）

    # 收集 H 形组合（3词）：竖 b 无叠字，穿两条横 a(上)、c(下)，gap>=2
    # 按竖成语 b 分组，轮流取，保证竖成语多样
    h_groups = defaultdict(list)
    for b in ws_nodup:
        for a in ws:
            for c in ws:
                if a == b or c == b or a == c:
                    continue
                sa, sb, sc = set(a), set(b), set(c)
                if not (sa & sb) or not (sc & sb):
                    continue
                for ia in (1, 2, 0, 3):
                    if a[ia] not in sb or c[ia] not in sb:
                        continue
                    ka = b.index(a[ia]); kc = b.index(c[ia])
                    if kc - ka >= 2:
                        h_groups[b].append((a, b, c, ia, kc - ka))
                        break
    # 每个竖成语内部打乱
    random.seed(42)
    for b in h_groups:
        random.shuffle(h_groups[b])
    # 竖成语按"能组的组合数"排序，轮流取
    b_keys = sorted(h_groups.keys(), key=lambda b: -len(h_groups[b]))
    h_combos = []
    round_i = 0
    while len(h_combos) < 35:
        progress = False
        for b in b_keys:
            grp = h_groups[b]
            k = round_i % len(grp)
            a, bb, c, ia, gap = grp[k]
            if (a, bb, c) in {(x[0], x[1], x[2]) for x in h_combos}:
                continue
            h_combos.append((a, bb, c, ia, gap))
            progress = True
            if len(h_combos) >= 35:
                break
        round_i += 1
        if not progress:
            break

    # 单十字组合（无叠字，交叉居中）
    plus_combos = []
    for a in ws_nodup:
        for b in ws_nodup:
            if a == b:
                continue
            sh = next((c for c in a if c in b), None)
            if sh and a.index(sh) in (1, 2):
                plus_combos.append((a, b))
    random.shuffle(plus_combos)

    items = []
    hi = pi = 0
    while len(items) < 50:
        # 前 30 个用 H 形（大块），后 20 个用单十字
        if len(items) < 30 and hi < len(h_combos):
            a, b, c, ia, gap = h_combos[hi]
            hi += 1
            lay = shape_h(a, c, b, pymap)
            if not lay:
                continue
            words = [a, b, c]
        elif pi < len(plus_combos):
            a, b = plus_combos[pi]
            pi += 1
            lay = shape_plus(a, b, pymap)
            if not lay:
                continue
            words = [a, b]
        else:
            break
        items.append({
            "name": "十·" + str(len(items) + 1),
            "words": words,
            "rows": lay["rows"],
            "cols": lay["cols"],
            "cells": lay["cells"],
            "hint": "横竖都是成语，交叉的字两边都要用",
        })
    return items


def norm(items, em):
    return [{"w": it['w'], "py": it['py'], "b": [1], "em": em, "hint": it['hint']} for it in items]


def main():
    data = load()
    pymap = build_pymap(data)
    cross_items = build_cross(data, pymap)
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