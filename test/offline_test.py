# 离线能力测试：在线载入 → SW 激活+缓存预热 → 断网重载仍可用
import sys, traceback
from playwright.sync_api import sync_playwright
BASE = "http://127.0.0.1:8081/index.html?debug"

def main():
    passed = 0
    def ok(c, m):
        nonlocal passed
        if not c:
            raise AssertionError("✗ " + m)
        passed += 1
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width":820,"height":1180}, is_mobile=True, has_touch=True)
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))

        # 1) 在线载入
        pg.goto(BASE, wait_until="networkidle")
        pg.wait_for_function("()=>!!window.__PZ__", timeout=8000)
        # 等待 SW 激活 + 缓存预热
        pg.wait_for_function("() => navigator.serviceWorker && navigator.serviceWorker.ready", timeout=15000)
        pg.wait_for_timeout(1500)
        # 检查缓存条目
        entries = pg.evaluate("""async () => {
          const keys = await caches.keys();
          if (!keys.length) return 0;
          const c = await caches.open(keys[0]);
          const reqs = await c.keys();
          return reqs.length;
        }""")
        ok(entries >= 4, f"缓存预热后有>=4个条目，实际{entries}")

        # 2) 断网重载：拦截所有请求
        ctx.route("**/*", lambda route: route.abort())
        try:
            pg.reload(wait_until="domcontentloaded", timeout=10000)
        except Exception:
            pass
        pg.wait_for_timeout(1200)
        # 断网后页面是否可用 & 能进游戏
        has_app = pg.evaluate("()=> !!document.querySelector('#btn-main-start')")
        ok(has_app, "断网重载后页面骨架仍在（走的 SW 缓存）")
        has_pz = pg.evaluate("()=> !!window.__PZ__")
        ok(has_pz, "断网后 JS 仍执行（__PZ__ 存在）")
        if has_pz:
            pg.click("#btn-main-start")
            s = pg.evaluate("()=>window.__PZ__.state()")
            ok(s["screen"] == "game", "断网也能进游戏画面")
        ok(not errs, "无页面 JS 错误，实际 " + " | ".join(errs))

        b.close()
    print(f"\n✓ 离线测试通过（{passed} 项断言）")

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        traceback.print_exc()
        sys.exit(2)