# -*- coding: utf-8 -*-
"""组装 src/puzzles.js。档0/档1 来自 puzzles_data.json，档2 十字成语自动拼。"""
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


def find_crosses(words, need):
    """找共享字成语对，凑够 need 个十字盘；按共享字轮流取，保证共享字/词多样化。"""
    from collections import defaultdict
    ws = list(dict.fromkeys(w for w in words if len(w) == 4))
    groups = defaultdict(list)   # shared char -> [(a,b)]
    for a in ws:
        for b in ws:
            if a == b:
                continue
            shared = next((c for c in a if c in b), None)
            if shared:
                groups[shared].append((a, b))
    chars = sorted(groups.keys())
    out = []
    seen = set()
    round_i = 0
    while len(out) < need:
        progress = False
        for sh in chars:
            grp = groups[sh]
            idx = round_i % len(grp)
            a, b = grp[idx]
            if (a, b) in seen:
                continue
            seen.add((a, b))
            out.append({"a": a, "b": b, "shared": sh,
                        "ia": a.index(sh), "ib": b.index(sh)})
            progress = True
            if len(out) >= need:
                break
        round_i += 1
        if not progress:
            break
    return out


def make_cross_boards(pairs, pymap):
    items = []
    for idx, cw in enumerate(pairs):
        ia, ib = cw["ia"], cw["ib"]
        s = -ib  # 竖起点行对齐共享字 (0, ia)
        cells = []
        for c, ch in enumerate(cw["a"]):
            cells.append({"r": 0, "c": c, "ch": ch, "py": pymap.get(ch, ""), "pre": (c == ia)})
        for i, ch in enumerate(cw["b"]):
            if i == ib:
                continue
            cells.append({"r": s + i, "c": ia, "ch": ch, "py": pymap.get(ch, "")})
        minr = min(c["r"] for c in cells)
        if minr < 0:
            for c in cells:
                c["r"] -= minr
        rows = max(c["r"] for c in cells) + 1
        cols = len(cw["a"])
        items.append({
            "name": "十·" + str(idx + 1),
            "words": [cw["a"], cw["b"]],
            "shared": cw["shared"],
            "rows": rows, "cols": cols,
            "cells": cells,
            "hint": "横「" + cw["a"] + "」，竖「" + cw["b"] + "」交叉",
        })
    return items


def norm(items, em):
    return [{"w": it['w'], "py": it['py'], "b": [1], "em": em, "hint": it['hint']} for it in items]


def main2():
    data = load()
    dict_entries = load_dict()
    pymap = build_pymap(data, dict_entries)

    allwords = [it['w'] for it in data['haoci']] + [it['w'] for it in data['duizhan']]
    allwords += [e['w'] for e in dict_entries]
    pairs = find_crosses(allwords, 50)

    out = [
        {"name": "四字好词", "distract": 2, "items": norm(data['haoci'], '🧡')},
        {"name": "成语大挑战", "distract": 3, "items": norm(data['duizhan'], '🧿')},
        {"name": "十字成语", "kind": "cross", "distract": 2,
         "items": make_cross_boards(pairs, pymap)},
    ]
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write("window.PZ_PUZZLES = " + json.dumps(out, ensure_ascii=False, indent=1) + ";\n")
    print("好词", len(data['haoci']), "成语", len(data['duizhan']), "十字", len(out[2]['items']))


if __name__ == "__main__":
    main2()