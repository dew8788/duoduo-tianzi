# -*- coding: utf-8 -*-
"""测试：块状 crossword 网格生长算法（独立验证，先不碰 build_final.py）"""
import json, random

data = json.load(open("src/puzzles_data.json", encoding="utf-8"))
ws = [it["w"] for it in data["haoci"]] + [it["w"] for it in data["duizhan"]]
ws = list(dict.fromkeys(w for w in ws if len(w) == 4 and len(set(w)) == 4))  # 无叠字
print("无叠字词数", len(ws))

def shared_char(a, b):
    for c in a:
        if c in b:
            return c
    return None

def place(grid, word, r0, c0, d):
    """把 word 放进 grid；d='h'横 或 'v'竖。返回新grid或None(冲突)。"""
    g = dict(grid)
    for k, ch in enumerate(word):
        r = r0 if d == 'h' else r0 + k
        c = c0 + k if d == 'h' else c0
        if (r, c) in g and g[(r, c)] != ch:
            return None
        g[(r, c)] = ch
    return g

def try_extend(grid, words, used):
    """尝试在已有格子上挂一条新成语（横或竖），返回 (新grid, 新word, 方向, 位置) 或 None。"""
    cells = list(grid.items())
    random.shuffle(cells)
    for (r, c), ch in cells:
        for w in words:
            if w in used:
                continue
            if ch not in w:
                continue
            i = w.index(ch)
            # 横挂：w 的第 i 字对齐 (r,c)
            g2 = place(grid, w, r, c - i, 'h')
            if g2 is not None:
                return g2, w, 'h', (r, c - i)
            # 竖挂：w 的第 i 字对齐 (r,c)
            g2 = place(grid, w, r - i, c, 'v')
            if g2 is not None:
                return g2, w, 'v', (r - i, c)
    return None

def build_one(seed, words, max_words):
    grid = place({}, seed, 0, 0, 'h')
    used = {seed}
    placed = [(seed, 'h', (0, 0))]
    while len(used) < max_words:
        ext = try_extend(grid, words, used)
        if ext is None:
            break
        grid, w, d, pos = ext
        used.add(w)
        placed.append((w, d, pos))
    return grid, placed

def render(grid):
    rs = [r for r, _ in grid]; cs = [c for _, c in grid]
    minr, maxr = min(rs), max(rs); minc, maxc = min(cs), max(cs)
    out = []
    for r in range(minr, maxr + 1):
        row = []
        for c in range(minc, maxc + 1):
            row.append(grid.get((r, c), '.'))
        out.append(' '.join(row))
    return '\n'.join(out)

# 生成几个 3-4 词样本
random.seed(7)
seen_sizes = {}
for i in range(40):
    seed = random.choice(ws)
    grid, placed = build_one(seed, ws, random.choice([3, 4]))
    n = len(placed)
    key = n
    if key not in seen_sizes:
        seen_sizes[key] = (grid, placed, seed)
        print(f"=== {n} 词，种子 {seed} ===")
        print(render(grid))
        print("词:", [p[0] for p in placed], "方向:", [p[1] for p in placed])
        print()
        if len(seen_sizes) >= 4:
            break

print("能生成的词数分布:", sorted(seen_sizes.keys()))
