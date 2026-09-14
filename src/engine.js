/*!
 * 朵朵填字乐园 · 引擎 (纯逻辑，可在 Node 里测试)
 * ---------------------------------------------------------------
 * 职责：
 *   1. 数据完整性校验（字数与拼音数一致、空缺下标越界、重复字等）
 *   2. 从题库 + 干扰字生成一局的候选字牌（正解 + 干扰）
 *   3. 判定某格填写是否正确
 *   4. 提供可复现的洗牌（seeded shuffle，测试友好）
 *
 * 对外暴露 window.PZEngine。Node 下通过 module.exports 导出（引擎测试用）。
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.PZEngine = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var TOTAL_TIERS = 6;
  var INTERFERENCE_POOL = '一二三四五六七八九十千万百小猫小狗兔马象鱼蛙蛇狼鹤鸡鸭鹅猴猪牛羊耳口手足牙发个头脸身心手眼哭笑跑跳欢喜爱玩乐学认读吃喝睡觉黑黑白红黄蓝绿青紫金木水火土石山田日月星空云雨雪风雷风扇门车船飞机骑滑爬滚开花树草果瓜梨桃肉菜饭汤包圆方长高矮大小多少上下左右中前面前后各双多美丑香甜可爱好玩朋友好你不我他她我们它们这只那这那吗呢了吧呀喔哦好棒厉害认真专心仔细开心高兴快乐幸福平安健康努力加油别着急慢慢来'.split('');

  /* ============================ 工具 ============================ */

  function clone(o) { return JSON.parse(JSON.stringify(o)); }

  function arrayFromIndex(n) {
    var a = new Array(n);
    for (var i = 0; i < n; i++) a[i] = i;
    return a;
  }

  // 可复现洗牌（mulberry32），固定 seed 时结果稳定，便于测试
  function shuffled(arr, seed) {
    var a = arr.slice();
    var s = seed >>> 0 || 1;
    function next() {
      s |= 0; s = (s + 0x6D2B79F5) | 0;
      var t = Math.imul(s ^ (s >>> 15), 1 | s);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    }
    for (var i = a.length - 1; i > 0; i--) {
      var j = (next() * (i + 1)) | 0;
      var tmp = a[i]; a[i] = a[j]; a[j] = tmp;
    }
    return a;
  }

  function firstIndexOf(str, ch) {
    return String(str).indexOf(ch);
  }

  /* ============================ 题库装载 ============================ */

  var DATA = null;

  function setData(raw) {
    if (!raw || !Array.isArray(raw)) { DATA = null; return; }
    // 只保留第一层结构，逐题做深拷贝，引擎测试不改源数据
    DATA = clone(raw);
    TOTAL_TIERS = DATA.length;
    return DATA;
  }

  function data() { return DATA; }
  function tierCount() { return DATA ? DATA.length : 0; }
  function tierName(t) { return DATA && DATA[t] ? (DATA[t].name || '第 ' + (t + 1) + ' 关') : ''; }
  function itemCount(t) { return DATA && DATA[t] ? DATA[t].items.length : 0; }
  function getItem(t, i) { return DATA && DATA[t] && DATA[t].items[i] ? DATA[t].items[i] : null; }

  /* ============================ 校验 ============================ */

  // 返回 { ok, errors:[...] }
  function validate() {
    var errors = [];
    if (!DATA) { errors.push('题库未加载'); return { ok: false, errors: errors }; }
    DATA.forEach(function (tier, t) {
      if (!tier.name) errors.push('第 ' + (t + 1) + ' 档没写名字');
      if (!Array.isArray(tier.items) || !tier.items.length) { errors.push('第 ' + (t + 1) + ' 档没有题目'); return; }
      tier.items.forEach(function (it, i) {
        var title = '第' + (t + 1) + '档第' + (i + 1) + '题「' + it.w + '」';
        if (!it.w || !it.w.length) { errors.push(title + ' 没有汉字'); return; }
        if (!it.py) { errors.push(title + ' 没有拼音'); }
        else if (it.py.length !== it.w.length) errors.push(title + ' 拼音长度不匹配(' + it.py.length + '/请与字长' + it.w.length + ')');
        if (!Array.isArray(it.b) || !it.b.length) { errors.push(title + ' 没有空缺格'); }
        else {
          var seen = {};
          it.b.forEach(function (idx) {
            if (typeof idx !== 'number' || idx < 0 || idx >= it.w.length) errors.push(title + ' 空缺下标越界:' + idx);
            else {
              if (seen[idx]) errors.push(title + ' 空缺下标重复:' + idx);
              seen[idx] = 1;
            }
          });
        }
      });
    });
    return { ok: !errors.length, errors: errors };
  }

  /* ============================ 候选字生成 ============================ */

  // 返回 { tiles: [{id, ch}], answers: { slotIdx: 正确字 } }
  function buildBank(t, i, seed) {
    if (!DATA || !DATA[t]) return null;
    var it = DATA[t].items[i];
    if (!it) return null;
    var distract = DATA[t].distract | 0;

    var chars = it.w.split('');
    var answers = {};                 // slotIdx -> 正确字
    it.b.forEach(function (idx) { answers[idx] = chars[idx]; });

    // 正解字牌（每位空缺一张，可能重复叠字）
    var tiles = it.b.map(function (idx, k) {
      return { id: 'ans-' + t + '-' + i + '-' + k, char: chars[idx], slot: idx, answer: true };
    });

    // 干扰字：从常用字池里挑 distract 个，且不含本题任何已用字
    var used = {};
    chars.forEach(function (c) { used[c] = 1; });
    var pool = INTERFERENCE_POOL.slice();
    var distCharPool = [];
    for (var p = 0; p < pool.length && distCharPool.length < 60; p++) {
      if (!used[pool[p]]) distCharPool.push(pool[p]);
    }
    var selected = [];
    var i2 = 0;
    while (selected.length < distract && i2 < distCharPool.length) {
      var c = distCharPool[(i2 * 7 + 3) % distCharPool.length];
      if (selected.indexOf(c) < 0) selected.push(c);
      i2++;
    }
    selected.forEach(function (c, k) {
      tiles.push({ id: 'd-' + t + '-' + i + '-' + k, char: c, answer: false });
    });

    // 洗牌打乱，可复现
    var shuffledIdx = shuffled(arrayFromIndex(tiles.length), seed);
    var out = shuffledIdx.map(function (k) { return tiles[k]; });

    return { tiles: out, answers: answers };
  }

  /* ============================ 判定 ============================ */

  function isCorrect(t, i, slotIdx, char) {
    if (!DATA) return false;
    var it = DATA[t].items[i];
    if (!it) return false;
    var resolve = it.w.charAt(slotIdx);
    return String(resolve) === String(char);
  }

  return {
    validate: validate,
    setData: setData,
    data: data,
    tierCount: tierCount,
    tierName: tierName,
    itemCount: itemCount,
    getItem: getItem,
    buildBank: buildBank,
    isCorrect: isCorrect,
    TOTAL_TIERS: 6,
    shuffled: shuffled
  };
});