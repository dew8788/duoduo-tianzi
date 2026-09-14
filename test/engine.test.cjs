/* 朵朵填字乐园 · 引擎测试（node test/engine.test.cjs） */
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

// 加载题库（window.PZ_PUZZELS）
const puzzlesSrc = fs.readFileSync(path.join(__dirname, '..', 'src', 'puzzles.js'), 'utf8');
const holder = {};
new Function('window', puzzlesSrc)(holder);
const data = holder.PZ_PUZZLES;

// 加载引擎
const E = require('../src/engine.js');

let passed = 0;
function ok(cond, msg) {
  if (!cond) throw new Error('✗ ' + msg);
  passed++;
}

// 基本
ok(Array.isArray(data) && data.length >= 3, '应有至少 3 档');
ok(E, '引擎可加载');
E.setData(data);

// 档验证
ok(E.tierCount() === data.length, '档数一致');

data.forEach(function (tier, t) {
  ok(typeof E.tierName(t) === 'string' && E.tierName(t).length > 0, '档' + (t + 1) + '有名字');
  ok(E.itemCount(t) >= 1, '档' + (t + 1) + '非空');
});

// —— 档0/档1：普通成语 —— 
for (let t = 0; t < Math.min(2, data.length); t++) {
  const tier = data[t];
  ok(tier.kind !== 'cross', '档' + (t + 1) + ' 是普通档');
  ok(tier.items.length >= 50, '档' + (t + 1) + ' 至少 50 题，实际 ' + tier.items.length);
  tier.items.forEach(function (it, i) {
    assert.strictEqual(it.w.length, 4, '档' + t + '题' + i + ' 四字');
    assert.strictEqual(it.py.length, 4, '档' + t + '题' + i + ' 拼音4');
    // 拼音带声调：含非 ascii 元音 或 带音标记（ü 在多云）
    for (const p of it.py) {
      ok(/[āáǎàēéěèīíǐìōóǒòūúǔùüǖǘǚǜ]/.test(p), '拼音带声调: ' + it.w + ' /' + p);
    }
    // b 合法 & 可解
    for (const k of it.b) {
      ok(k >= 0 && k < 4, '空缺下标合法');
      ok(E.isCorrect(t, i, k, it.w[k]), '空缺' + k + '可匹配');
    }
    // buildBank 干扰不含正解
    const bank = E.buildBank(t, i, 3);
    for (const d of bank.tiles.filter(x => !x.answer)) {
      ok(!it.w.includes(d.char), '干扰字不与正解重复: ' + d.char);
    }
  });
}

// —— 档3（或最后一档）：十字成语 ——
const crossTier = data.find(t => t.kind === 'cross');
ok(!!crossTier, '存在十字档');
if (crossTier) {
  const t = data.indexOf(crossTier);
  ok(crossTier.items.length >= 4, '十字档至少4盘');
  for (let i = 0; i < crossTier.items.length; i++) {
    const it = crossTier.items[i];
    ok(it.rows > 0 && it.cols > 0, '盘尺寸');
    // 非 pre 的格都应有正解（buildCrossBank 给的答案都在 blank 里）
    const bank = E.buildCrossBank(t, i, 5);
    ok(bank && bank.tiles.length >= 1, '盘' + i + '有候选字');
    // 空白格是否全部可填对
    const blanks = it.cells.filter(c => !c.pre);
    const filled = {};
    blanks.forEach(b => { filled[b.r + ':' + b.c] = b.ch; });
    ok(E.crossDone(t, i, filled), '盘' + i + '填全体可判为成功');
    // 单一格判定
    if (blanks.length) {
      const b0 = blanks[0];
      ok(E.isCrossCorrect(t, i, b0.r, b0.c, b0.ch), '盘' + i + '单格判定正确');
      ok(!E.isCrossCorrect(t, i, b0.r, b0.c, '的'), '盘' + i + '单格判错位');
    }
  }
}

// seeded shuffle
ok(E.shuffled([1,2,3,4,5],42).join(',') === E.shuffled([1,2,3,4,5],42).join(','), 'shuffle确定');

console.log('\n✓ 引擎测试全部通过（' + passed + ' 项断言）');