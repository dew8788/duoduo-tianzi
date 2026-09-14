# 朵朵填字乐园

给朵朵做的识字小游戏（7 岁识字期）· 看图拼字、填成语。

- 顶上一行要拼的字，空缺格用**拼音**提示（孩子照着拼音认字）
- 下方一排候选字（含打乱的正解 + 干扰字），点空格 → 点候选字填入
- 全对 → 小动物跳出来欢呼撒花
- **3 档难度，每档 50 题**：
  1. **四字好词**（一心一意、五颜六色…常见好词）
  2. **成语大挑战**（守株待兔、画蛇添足…成语典故）
  3. **十字成语**（Crossword：两个成语横竖交叉，共用一个字，如「一心一意」×「三心二意」共享「心」）

## 玩法

点一个空格（选中高亮）→ 点下方候选字：
- 填对：锁进格子、变绿、好听音效
- 填错：格子轻轻抖动变红，候选字不退，随便重试
- 想改：点已填的格子可取消

## 题库来源

- 成语 + 拼音 + 释义：整理自《中学生多用成语词典》（四川教育出版社 1991），经 MinerU OCR 提取、人工核对拼音声调后精选适合孩子的 150 题（好词 50 + 成语 50 + 十字 50）。
- 十字成语盘：由 `tools/build_final.py` 自动搜索「共享同一字」的成语对拼成。

## 技术

- 纯 HTML/CSS/JS 单文件构建，零依赖
- `build.mjs` 把题库 + 引擎 + 界面内联成 `dist/index.html`
- Service Worker：离线缓存应用外壳，装到主屏断网也能玩
- 引擎 Node 可测（`test/engine.test.cjs`），Playwright 模拟 iPad 竖屏/横屏、手机做界面测试

## 本地

```bash
node tools/make-icons.mjs   # 生成图标（首次/改动后）
node test/engine.test.cjs   # 引擎测试
node build.mjs              # 打包到 dist/
node tools/serve.mjs        # 本机预览
python test/ui_smoke.py     # 界面冒烟测试
python test/offline_test.py # 离线测试
```

## 重新生成题库

```bash
python tools/build_final.py   # 读取 src/puzzles_data.json，重生成 src/puzzles.js
```

## 发布

推到 `main` 由 `.github/workflows/pages.yml` 自动构建部署到 GitHub Pages。
仓库只需开启一次：Settings → Pages → Source 选「GitHub Actions」。