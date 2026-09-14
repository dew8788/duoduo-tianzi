/* 朵朵填字乐园 · 引擎测试（node test/engine.test.cjs） */
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

// 从 puzzles.js 里取 window.PZ_PUZZELS 全局
const puzzlesSrc = fs.readFileSync(path.join(__dirname, '..', 'src', 'puzzles.js'), 'utf8');
const holder = {};
new Function('window', puzzlesSrc)(holder);
const data = holder.PZ_PUZZLES;

// 加载引擎（模块导出形式）
delete require.cache[require.resolve('../src/engine.js')];
const E = require('../src/engine.js');

let passed = 0;
function ok(cond, msg) {
  if (!cond) throw new Error('✗ ' + msg);
  passed++;
}

// ---------------------------------------------------------------
ok(Array.isArray(data) && data.length >= 4, '题库应有至少 4 档');
ok(E, '引擎应能加载');

E.setData(data);

// 1. 数据完整性
{
  const r = E.validate();
  ok(r.ok === true, '题库校验应通过，实际错误：' + r.errors.join(' | '));
}

// 2. 各档计数与名称
ok(E.tierCount() === data.length, '档数一致');
for (let t = 0; t < data.length; t++) {
  ok(typeof E.tierName(t) === 'string' && E.tierName(t).length > 0, '第' + (t + 1) + '档有名字');
  ok(E.itemCount(t) >= 3, '第' + (t + 1) + '档题目不少于3题');
}

// 3. 候选字生成：正解不越界、干扰字不含题内字、答案可解
for (let t = 0; t < data.length; t++) {
  const n = E.itemCount(t);
  for (let i = 0; i < n; i++) {
    const bank = E.buildBank(t, i, 1);
    ok(bank && bank.tiles && bank.tiles.length >= 1, '第' + (t + 1) + '档第' + (i + 1) + '题能出候选字');
    const item = data[t].items[i];
    // 干扰字不能出现在答案里
    const answerSet = {};
    item.b.forEach(idx => { answerSet[item.w[idx]] = 1; });
    const distractors = bank.tiles.filter(x => !x.answer);
    for (const d of distractors) {
      // 干扰字不能等于任何一个正确答案
      if (item.b.some(k => item.w[k] === d.char)) {
        throw new Error('干扰字冲突: 第' + (t + 1) + '档第' + (i + 1) + '题 ' + d.char);
      }
    }
    // 正确答案能解出（每位空缺都能匹配）
    for (const key of Object.keys(bank.answers)) {
      const slot = Number(key);
      ok(E.isCorrect(t, i, slot, item.w[slot]), '空缺' + slot + '正确答案可匹配');
    }
  }
}

// 4. 叠字题（出现重复正确答案）洗牌后正解键应存在且可解
//   例如 一心一意 (b:[0]) 只有一个空缺，不影响；找一道 b 里含相同字的多字
//   验证答案对象给出的 slot→正确字 覆盖所有空缺
for (let t = 0; t < data.length; t++) {
  const n = E.itemCount(t);
  for (let i = 0; i < n; i++) {
    const it = data[t].items[i];
    const bank = E.buildBank(t, i, 7);
    for (const idx of it.b) {
      ok(bank.answers[idx] === it.w[idx], '空缺' + idx + '答案一致');
    }
  }
}

// 5. seeded shuffle 确定性
const a = E.shuffled([1, 2, 3, 4, 5], 42).join(',');
const b = E.shuffled([1, 2, 3, 4, 5], 42).join(',');
ok(a === b, '同 seed 洗牌结果一致');

console.log('\n✓ 引擎测试全部通过（' + passed + ' 项断言）');