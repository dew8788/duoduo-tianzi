# -*- coding: utf-8 -*-
"""测试：随机生长块状网格 + 尺寸约束（含叠字成语，显式 index）"""
import json, random

data = json.load(open("src/puzzles_data.json", encoding="utf-8"))
ws = [it["w"] for it in data["haoci"]] + [it["w"] for it in data["duizhan"]]
ws = list(dict.fromkeys(w for w in ws if len(w) == 4))  # 含叠字

def bounds(g):
    rs = [r for r, _ in g]; cs = [c for _, c in g]
    return min(rs), max(rs), min(cs), max(cs)

def fits(g, maxrows, maxcols):
    if not g:
        return True
    minr, maxr, minc, maxc = bounds(g)
    return (maxr - minr + 1) <= maxrows and (maxc - minc + 1) <= maxcols

def place(grid, word, r0, c0, d):
    g = dict(grid)
    for k, ch in enumerate(word):
        r = r0 if d == 'h' else r0 + k
        c = c0 + k if d == 'h' else c0
        if (r, c) in g and g[(r, c)] != ch:
            return None
        g[(r, c)] = ch
    return g

def try_extend(grid, words, used, maxrows=5, maxcols=5):
    cells = list(grid.items())
    random.shuffle(cells)
    for (r, c), ch in cells:
        for w in words:
            if w in used:
                continue
            # 显式 index：叠字时试所有位置
            idxs = [i for i, x in enumerate(w) if x == ch]
            random.shuffle(idxs)
            for i in idxs:
                # 横
                g2 = place(grid, w, r, c - i, 'h')
                if g2 is not None and fits(g2, maxrows, maxcols):
                    return g2, w, 'h', (r, c - i)
                # 竖
                g2 = place(grid, w, r - i, c, 'v')
                if g2 is not None and fits(g2, maxrows, maxcols):
                    return g2, w, 'v', (r - i, c)
    return None

def build(seed, words, max_words, maxrows=5, maxcols=5):
    grid = place({}, seed, 0, 0, 'h')
    used = {seed}
    while len(used) < max_words:
        ext = try_extend(grid, words, used, maxrows, maxcols)
        if ext is None:
            break
        grid, w, d, pos = ext
        used.add(w)
    return grid, list(used)

def render(grid):
    if not grid: return '(empty)'
    minr, maxr, minc, maxc = bounds(grid)
    out = []
    for r in range(minr, maxr + 1):
        row = []
        for c in range(minc, maxc + 1):
            row.append(grid.get((r, c), '.'))
        out.append(' '.join(row))
    return '\n'.join(out)

random.seed(11)
samples = {}
for i in range(200):
    seed = random.choice(ws)
    g, used = build(seed, ws, random.choice([3, 4, 4]))
    n = len(used)
    if n >= 3 and n not in samples:
        samples[n] = (g, used)
        print(f"=== {n} 词 {used} ===")
        print(render(g))
        print()
        if len(samples) >= 5:
            break
print("样本词数", sorted(samples.keys()))
