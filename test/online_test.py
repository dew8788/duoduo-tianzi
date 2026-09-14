# 线上验证：加载布局 + 借一轮游戏 + SW/离线
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
        pg.goto(URL, wait_until="domcontentloaded")
        pg.wait_for_function("()=>!!window.__PZ__", timeout=15000)
        # 清除既有 SW 与缓存，确保读到最新发布（不是上一版 SW 的缓存优先）
        pg.evaluate("""async ()=>{ const ks=await caches.keys(); await Promise.all(ks.map(k=>caches.delete(k)));
          const regs=await navigator.serviceWorker.getRegistrations(); await Promise.all(regs.map(r=>r.unregister())); }""")
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_function("()=>!!window.__PZ__", timeout=15000)
        ok(pg.title().startswith("朵朵填字"), "标题含'朵朵填字'，实际 title=" + pg.title())
        ok(pg.locator("#btn-main-start").count() == 1, "线上首页有'开始拼字'")
        ok(pg.evaluate("()=>{const l=document.querySelector('.logo');return l? l.textContent.indexOf('朵')>=0 : false;}"), "Logo 含'朵'")

        # 借对一题（小猫）
        pg.click("#btn-main-start")
        s = pg.evaluate("()=>window.__PZ__.state()")
        ok(s["screen"]=="game" and "".join(s["chars"])=="小猫", "线上进入第一题'小猫'")
        ok(len(s["bank"])>=1, "有候选字")
        pg.click('.cell.blank[data-idx="1"]')
        pg.locator(".char-btn", has_text="猫").first.click()
        s2 = pg.evaluate("()=>window.__PZ__.state()")
        ok(s2["done"] is True, "线上拼对触发 done")
        ok(pg.locator(".modal-root.show").count()==1, "胜利弹窗出现")
        ok(pg.locator(".party-animal").count()==1, "庆祝动画里有小动物")

        # 关闭弹窗回家
        pg.click("button[data-action='home']")
        ok(pg.evaluate("()=>window.__PZ__.state().screen")=="home", "回首页成功")

        # Service Worker 状态
        # Service Worker 状态
        sw_state = pg.evaluate("""() => new Promise(res=>{
          if(!('serviceWorker' in navigator)){res('no-sw');return;}
          const t=setTimeout(()=>res('timeout'),20000);
          navigator.serviceWorker.ready.then(reg=>{clearTimeout(t);
            res(reg.active? 'active-'+reg.active.state : 'no-active');});
        })""")
        ok("active" in sw_state, "SW 已激活 (" + sw_state + ")")
        # 预热是后台异步的，轮询等缓存条目稳定到 >=4（最多 15s）
        entries = 0
        for _ in range(30):
            entries = pg.evaluate("""async ()=>{ const ks=await caches.keys(); if(!ks.length)return 0; const c=await caches.open(ks[0]); return (await c.keys()).length; }""")
            if entries >= 4: break
            pg.wait_for_timeout(500)
        ok(entries>=4, f"缓存已预热({entries}个资源)")

        ok(not errs, "无页面JS错误" + ("："+" | ".join(errs) if errs else ""))
        b.close()
    print(f"\n=== 线上验证: {passed} 通过, {len(fails)} 失败 ===")
    for f in fails: print(f)
    sys.exit(0 if not fails else 1)

if __name__ == "__main__":
    try: main()
    except SystemExit: raise
    except Exception as e: traceback.print_exc(); sys.exit(2)