# 线上断网测试：在线加载→清SW→重载并预热→拦截全部请求→断网重载仍可玩
from playwright.sync_api import sync_playwright
URL = "https://dew8788.github.io/duoduo-tianzi/?debug"

def main():
    passed = []
    def ok(c, m):
        if c: passed.append(m); print("  OK", m)
        else: raise AssertionError("✗ " + m)
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width":820,"height":1180}, is_mobile=True, has_touch=True)
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))

        # 1) 第一次加载，把 SW 弄干净，再加载一次让 SW 注册+激活+预热
        pg.goto(URL, wait_until="domcontentloaded")
        pg.wait_for_function("()=>!!window.__PZ__", timeout=20000)
        pg.evaluate("""async ()=>{ const ks=await caches.keys(); await Promise.all(ks.map(k=>caches.delete(k)));
          const regs=await navigator.serviceWorker.getRegistrations(); await Promise.all(regs.map(r=>r.unregister())); }""")
        # 再次硬加载，注册 SW 并等激活
        pg.goto(URL, wait_until="networkidle")
        pg.wait_for_function("""async ()=> { if(!navigator.serviceWorker) return false;
          try{ const r= await navigator.serviceWorker.ready; return !!r.active; }catch(e){ return false; } }""", timeout=25000)
        # 等预热轮
        entries = 0
        for _ in range(40):
            entries = pg.evaluate("""async ()=>{ const ks=await caches.keys(); if(!ks.length)return 0; const c=await caches.open(ks[0]); return (await c.keys()).length; }""")
            if entries >= 4: break
            pg.wait_for_timeout(500)
        ok(entries >= 4, f"首次在线安装：SW 激活且缓存 {entries} 个资源")

        # 2) 断网：拦截所有请求
        ctx.route("**/*", lambda route: route.abort())
        pg.reload(wait_until="domcontentloaded")  # 可能拦截部分，任意
        pg.wait_for_timeout(1500)
        has_home = pg.evaluate("()=> !!document.querySelector('#btn-main-start')")
        ok(has_home, "断网重载后首页仍能打开（应用外壳来自 SW 缓存）")
        has_pz = pg.evaluate("()=>!!window.__PZ__")
        ok(has_pz, "断网后 JS 正常执行")
        if has_pz:
            pg.click("#btn-main-start")
            s = pg.evaluate("()=>window.__PZ__.state()")
            ok(s["screen"]=="game" and "".join(s["chars"])=="小猫", "断网也能进到游戏画面（小猫）")
            ok(page_has_charbtns := pg.locator(".char-btn").count()>=1, "断网后有候选字")
        ok(not errs, "断网过程无页面JS错误" + ("："+ " | ".join(errs) if errs else ""))
        b.close()
    print(f"\n✓ 线上断网测试通过（{len(passed)} 项）")

if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(e)
        raise SystemExit(1)
    except Exception:
        import traceback; traceback.print_exc(); raise SystemExit(2)