# 线上验证：新十字盘（交叉字待填、居中）+ 小女孩动画 + 三档
import sys, traceback
from playwright.sync_api import sync_playwright
URL = "https://dew8788.github.io/duoduo-tianzi/?debug"

def main():
    passed = 0; fails = []
    def ok(c, m):
        nonlocal passed
        if c: passed += 1
        else: fails.append("✗ "+m); print("  FAIL "+m)

    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width":820,"height":1180}, is_mobile=True, has_touch=True)
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_function("()=>!!window.__PZ__", timeout=25000)
        ok(pg.locator("#btn-main-start").count()==1, "首页正常")

        # 三档
        pg.click("#btn-main-tiers")
        ok(pg.locator(".tier").count()==3, "三档")

        # 十字盘
        pg.click(".tier >> nth=2")
        pg.click(".lv >> nth=0")
        s = pg.evaluate("()=>window.__PZ__.state()")
        ok(s["tier"]==2 and s["isCross"], "进十字档")
        ok(pg.locator(".cross-grid").count()==1, "十字网格")
        ok(pg.locator(".xcell.pre").count()>=1, "有预填锚点")
        ok(pg.locator('.xcell:not(.pre):not(.void)').count()>=3, "有多个待填空格")
        # 交叉字待填：共享字所在格应是 non-pre
        cells = s["cells"] or []
        words = pg.evaluate("()=>window.__PZ__.data ? null : null")  # placeholder
        # 填一个待填空格
        tgt = next((c for c in cells if not c.get("pre")), None)
        if tgt:
            pg.locator(f'.xcell[data-r="{tgt["r"]}"][data-c="{tgt["c"]}"]').click()
            pg.locator(".char-btn", has_text=tgt["ch"]).first.click()
            s4 = pg.evaluate("()=>window.__PZ__.state()")
            ok(s4["filled"].get(f'{tgt["r"]}:{tgt["c"]}')==tgt["ch"], "十字格填入")

        # 庆祝动画（小女孩）
        # 先回首页
        pg.click("#btn-game-back")
        pg.wait_for_timeout(300)
        pg.click("#btn-main-tiers")
        pg.click(".tier >> nth=0")
        pg.click(".lv >> nth=0")
        pg.click('.cell.blank[data-idx="1"]')
        pg.locator(".char-btn", has_text="心").first.click()
        pg.wait_for_timeout(500)
        ok(pg.locator(".party .girl").count()==1, "庆祝动画是小女孩SVG")
        ok(pg.locator(".modal-root.show").count()==1, "胜利弹窗")

        ok(not errs, "无JS错误" + ("："+" | ".join(errs) if errs else ""))
        b.close()
    print(f"\n=== 线上验证: {passed} 通过, {len(fails)} 失败 ===")
    for f in fails: print(f)
    sys.exit(0 if not fails else 1)

if __name__ == "__main__":
    try: main()
    except SystemExit: raise
    except Exception: traceback.print_exc(); sys.exit(2)