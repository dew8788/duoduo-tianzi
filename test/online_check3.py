# 线上验证：H形大块网格 + 单十字并存 + 交叉字待填
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

        # H形（前30个是3词H形）
        pg.evaluate("()=>window.__PZ__.startLevel(2, 4)")
        pg.wait_for_timeout(400)
        s = pg.evaluate("()=>window.__PZ__.state()")
        ok(s["tier"]==2 and s["isCross"], "进十字档")
        ok(len(s["cells"]) >= 8, "H形大块网格格子数(>=8): "+str(len(s["cells"])))
        # 交叉字待填（共享字所在格 pre=False）
        cells = s["cells"] or []
        pre_cells = [c for c in cells if c.get("pre")]
        ok(len(pre_cells)==3, "H形有3个锚点(每词首字)，实际"+str(len(pre_cells)))
        ok(pg.locator('.xcell:not(.pre):not(.void)').count()>=4, "有多个待填空格")

        # 单十字（第31个起是2词）
        pg.evaluate("()=>window.__PZ__.startLevel(2, 31)")
        pg.wait_for_timeout(400)
        s2 = pg.evaluate("()=>window.__PZ__.state()")
        ok(len(s2["cells"]) >= 5, "单十字格子数(>=5): "+str(len(s2["cells"])))

        ok(not errs, "无JS错误" + ("："+" | ".join(errs) if errs else ""))
        b.close()
    print(f"\n=== 线上验证: {passed} 通过, {len(fails)} 失败 ===")
    for f in fails: print(f)
    sys.exit(0 if not fails else 1)

if __name__ == "__main__":
    try: main()
    except SystemExit: raise
    except Exception: traceback.print_exc(); sys.exit(2)