# 线上验证：三档结构 + 十字盘渲染/游玩 + SW
import sys, traceback
from playwright.sync_api import sync_playwright
URL = "https://dew8788.github.io/duoduo-tianzi/?debug"

def main():
    passed = 0
    fails = []
    def ok(c, m):
        nonlocal passed
        if c: passed += 1
        else:
            fails.append("✗ " + m); print("  FAIL " + m)

    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width":820,"height":1180}, is_mobile=True, has_touch=True)
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_function("()=>!!window.__PZ__", timeout=20000)
        ok(pg.locator("#btn-main-start").count()==1, "线上首页有开始按钮")

        # 三档结构
        pg.click("#btn-main-tiers")
        ok(pg.locator(".tier").count()==3, "线上有 3 档")
        names = pg.evaluate("()=>Array.from(document.querySelectorAll('.tier .t-name')).map(e=>e.textContent)")
        ok(names == ["四字好词","成语大挑战","十字成语"], "三档名称正确: "+str(names))

        # 档0 玩一题
        pg.click(".tier >> nth=0")
        pg.click(".lv >> nth=0")
        s = pg.evaluate("()=>window.__PZ__.state()")
        ok(s["tier"]==0 and "".join(s["chars"])=="一心一意", "档0第1题'一心一意'")
        pg.click('.cell.blank[data-idx="1"]')
        pg.locator(".char-btn", has_text="心").first.click()
        s2 = pg.evaluate("()=>window.__PZ__.state()")
        ok(s2["done"] is True, "档0第1题拼对")
        pg.click("button[data-action='home']")
        pg.wait_for_timeout(300)

        # 档2 十字盘
        pg.click("#btn-main-tiers")
        pg.click(".tier >> nth=2")
        pg.click(".lv >> nth=0")
        s = pg.evaluate("()=>window.__PZ__.state()")
        ok(s["tier"]==2 and s["isCross"] is True, "进入十字档")
        ok(pg.locator(".cross-grid").count()==1, "十字网格渲染")
        ok(pg.locator(".xcell.pre").count()==1, "共享字预填格存在")
        ok(pg.locator('.xcell:not(.pre):not(.void)').count()>=4, "待填空格存在")
        cells = s["cells"] or []
        tgt = next((c for c in cells if not c.get("pre")), None)
        if tgt:
            pg.locator(f'.xcell[data-r="{tgt["r"]}"][data-c="{tgt["c"]}"]').click()
            pg.locator(".char-btn", has_text=tgt["ch"]).first.click()
            s4 = pg.evaluate("()=>window.__PZ__.state()")
            ok(s4["filled"].get(f'{tgt["r"]}:{tgt["c"]}')==tgt["ch"], "线上十字格填入正确")

        # SW
        sw = pg.evaluate("""()=>new Promise(r=>{if(!('serviceWorker' in navigator))return r('no');const t=setTimeout(()=>r('timeout'),15000);navigator.serviceWorker.ready.then(x=>{clearTimeout(t);r(x.active?'active':'none')})})""")
        ok("active" in sw, "线上 SW 激活 ("+sw+")")
        ok(not errs, "无 JS 错误" + ("："+ " | ".join(errs) if errs else ""))
        b.close()
    print(f"\n=== 线上验证: {passed} 通过, {len(fails)} 失败 ===")
    for f in fails: print(f)
    sys.exit(0 if not fails else 1)

if __name__ == "__main__":
    try: main()
    except SystemExit: raise
    except Exception: traceback.print_exc(); sys.exit(2)