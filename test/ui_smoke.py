# 朵朵填字乐园 · UI 冒烟测试（Playwright）
# 覆盖：首页 / 档0好词填空 / 错误反馈 / 档2十字成语网格
import sys, traceback
from playwright.sync_api import sync_playwright

BASE = None
VIEWPORTS = [("iPad竖屏", 820, 1180), ("iPad横屏", 1180, 820), ("手机", 390, 844)]

def state(pg):
    return pg.evaluate("() => window.__PZ__ ? window.__PZ__.state() : null")

def main():
    global BASE
    BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8081/index.html?debug"
    passed = 0
    fails = []
    def ok(cond, msg):
        nonlocal passed
        if not cond:
            fails.append("✗ " + msg)
            print("  FAIL " + msg)
        else:
            passed += 1

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, W, H in VIEWPORTS:
            print(f"[{name} {W}x{H}]")
            ctx = browser.new_context(viewport={"width": W, "height": H},
                                      is_mobile=True, has_touch=True)
            page = ctx.new_page()
            page.goto(BASE, wait_until="networkidle")
            page.wait_for_function("() => !!window.__PZ__", timeout=8000)

            ok(page.locator("#btn-main-start").count() == 1, "首页有'开始拼字'")
            ok(page.locator("#btn-main-tiers").count() == 1, "首页有'挑选关卡'")
            ok(state(page)["screen"] == "home", "默认在首页")

            # --- 档0第1题：一心一意，空 [1]=心 ---
            page.click("#btn-main-start")
            s = state(page)
            ok(s["screen"] == "game", "点开始进入游戏")
            ok(s["tier"] == 0 and s["item"] == 0, "进入第1档第1题")
            ok("".join(s["chars"]) == "一心一意", "第一题是'一心一意'")
            ok(sorted(s["slots"]) == [1], "空缺[1]")
            ok(len(s["bank"]) >= 1, "有候选字")
            ok("心" in [t["char"] for t in s["bank"]], "候选含正确字'心'")

            blank = page.locator('.cell.blank[data-idx="1"]')
            ok(blank.count() == 1, "有 1 个空白格")
            py_txt = blank.inner_text()
            ok(py_txt.strip() != "" and "心" not in py_txt, "空白格显示拼音提示(非答案)")

            blank.click()
            page.locator(".char-btn", has_text="心").first.click()
            s2 = state(page)
            ok(s2["filled"].get("1") == "心", "空格填入'心'")
            ok(s2["done"] is True, "拼对触发 done")
            ok(page.locator(".modal-root.show").count() == 1, "胜利弹窗出现")
            page.click("button[data-action='home']")
            page.wait_for_timeout(300)
            ok(state(page)["screen"] == "home", "回首页")

            # --- 错误反馈：档0第2题 ---
            page.click("#btn-main-tiers")
            page.click(".tier >> nth=0")
            page.click(".lv >> nth=1")
            s = state(page)
            ok(s["tier"] == 0 and s["item"] == 1, "进入档0第2题")
            ok("".join(s["chars"]) == "三心二意", "第2题是'三心二意'")
            # 空 [1]=心
            blank2 = page.locator('.cell.blank[data-idx="1"]')
            blank2.click()
            wrong = [t["char"] for t in s["bank"] if t["char"] != "心"]
            if wrong:
                page.locator(".char-btn", has_text=wrong[0]).first.click()
                page.wait_for_timeout(600)
                s = state(page)
                ok(s["filled"].get("1") is None or s["filled"].get("1") != "心",
                   "填错不会写入'心'")
            page.locator(".char-btn", has_text="心").first.click()
            s3 = state(page)
            ok(s3["filled"].get("1") == "心", "第二次填对'心'")
            ok(s3["done"] is True, "第2题成功")
            # 关掉胜利弹窗回首页
            page.click("button[data-action='home']")
            page.wait_for_timeout(300)

            # --- 档2十字成语：渲染网格 + 填一个空格 ---
            page.click("#btn-main-tiers")
            page.click(".tier >> nth=2")
            page.click(".lv >> nth=0")
            s = state(page)
            ok(s["tier"] == 2, "进入十字档")
            ok(page.locator(".cross-grid").count() == 1, "十字网格渲染")
            ok(page.locator(".xcell").count() >= 5, "十字格数量合理")
            # 有预填格(pre)和待填空格
            ok(page.locator(".xcell.pre").count() >= 1, "有共享字预填格")
            blank_x = page.locator(".xcell:not(.pre):not(.void)")
            ok(blank_x.count() >= 1, "有待填空格")
            # 填一个空格：用引擎拿到第一个空格正确字
            cells = s.get("cells") or []
            target = next((c for c in cells if not c.get("pre")), None)
            if target:
                rr, cc = target["r"], target["c"]
                page.locator(f'.xcell[data-r="{rr}"][data-c="{cc}"]').click()
                page.locator(".char-btn", has_text=target["ch"]).first.click()
                s4 = state(page)
                ok(s4["filled"].get(f"{rr}:{cc}") == target["ch"], "十字格填入正确字")

            page.close(); ctx.close()
        browser.close()

    print(f"\n=== 结果: {passed} 断言通过, {len(fails)} 失败 ===")
    for msg in fails:
        print(msg)
    sys.exit(0 if not fails else 1)

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        traceback.print_exc()
        print("测试异常：", e)
        sys.exit(2)