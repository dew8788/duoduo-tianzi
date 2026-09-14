# 朵朵填字乐园 · UI 冒烟测试（Playwright）
# 用无头 Chromium，按 iPad 竖屏 / 横屏 / 手机 三种尺寸真实点击。
# 用法：python test/ui_smoke.py [BASE_URL]
import sys, traceback, platform
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

            # --- 第 1 题：小猫，空缺 [1] ---
            page.click("#btn-main-start")
            s = state(page)
            ok(s["screen"] == "game", "点开始进入游戏")
            ok(s["tier"] == 0 and s["item"] == 0, "进入第1档第1题")
            ok("".join(s["chars"]) == "小猫", "第一题是'小猫'")
            ok(sorted(s["slots"]) == [1], "小猫空缺[1]")
            ok(len(s["bank"]) >= 1, "有候选字")
            ok("猫" in [t["char"] for t in s["bank"]], "候选含正确字'猫'")

            blank = page.locator('.cell.blank[data-idx="1"]')
            ok(blank.count() == 1, "有 1 个空白格")
            # 空格应显示拼音
            py_txt = blank.inner_text()
            ok("猫" not in py_txt and py_txt.strip() != "", "空白格显示拼音提示(非答案)")

            blank.click()
            page.locator(".char-btn", has_text="猫").first.click()
            s2 = state(page)
            ok(s2["filled"].get("1") == "猫", "空格填入'猫'")
            ok(s2["done"] is True, "拼对触发 done")
            ok(page.locator(".modal-root.show").count() == 1, "胜利弹窗出现")
            # 答案字块逐个拼出的内容即为 '小猫'（inner_text 会给小块间插换行，改用 text content 拼）
            aw = page.evaluate("() => Array.from(document.querySelectorAll('.answer-word .aw-cell')).map(e=>e.textContent).join('')")
            ok(aw == "小猫", f"弹窗答案字块拼出'小猫'，实际'{aw}'")
            page.click("button[data-action='home']")
            ok(state(page)["screen"] == "home", "回首页")

            # --- 错误反馈：进第 2 题，先填错--- ---
            page.click("#btn-main-tiers")
            page.click(".tier >> nth=0")       # 进 chapters 里第1档
            page.click(".lv >> nth=1")         # 第 2 题
            s = state(page)
            ok("".join(s["chars"]) == "小狗", "第2题是'小狗'")
            ok(s["item"] == 1, "进入第2题")
            blank2 = page.locator('.cell.blank[data-idx="1"]')
            blank2.click()
            wrong = [t["char"] for t in s["bank"] if t["char"] != "狗"]
            # 若干扰字存在，填一个错的
            if wrong:
                page.locator(".char-btn", has_text=wrong[0]).first.click()
                page.wait_for_timeout(600)
                s = state(page)
                ok(s["filled"].get("1") is None or s["filled"].get("1") != "狗",
                   "填错不会写入'狗'")
            # 再正确填 '狗'
            page.locator(".char-btn", has_text="狗").first.click()
            s3 = state(page)
            ok(s3["filled"].get("1") == "狗", "第二次填对'狗'")
            ok(s3["done"] is True, "第2题成功")

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