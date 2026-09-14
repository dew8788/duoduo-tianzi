/*!
 * 朵朵填字乐园 · 界面 (app.js)
 * ------------------------------------------------------------------
 * 交互模型：
 *   顶部一条要拼的字，其中空缺格用浅灰虚线标出，空格内显示「拼音」提示。
 *   下方一排候选字牌（正确字 + 干扰字，已打乱）。
 *   点一个空格（选中高亮）→ 点一个候选字：
 *      填对：锁进格子里、变绿、音效；
 *      填错：该格抖动变红、候选字不退（孩子随便点）。
 *   所有空格填对 → 小动物从底下跳出来欢呼撒花 + ✗✗，进入下一题。
 *
 * 6 档：动物二字 → 动物二字(带干扰) → 动物三字 → 动物四字 → 四字好词 → 成语
 */
(function () {
  'use strict';

  var E = window.PZEngine;
  if (!E) { alert('引擎加载失败'); return; }
  if (window.PZ_PUZZLES) E.setData(window.PZ_PUZZLES);

  /* ============================ 小工具 ============================ */

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function el(tag, cls) { var n = document.createElement(tag); if (cls) n.className = cls; return n; }
  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function pick(arr) { return arr[(Math.random() * arr.length) | 0]; }

  /* ============================ 存档 ============================ */

  var STORE_KEY = 'pz.save.v1';
  var store = {
    solved: {},           // "tier:item" → true
    settings: { sound: true, vibrate: true },
    lastTier: 0, lastItem: 0
  };

  function loadStore() {
    try {
      var raw = localStorage.getItem(STORE_KEY);
      if (!raw) return;
      var o = JSON.parse(raw);
      if (o && typeof o === 'object') {
        if (o.solved) store.solved = o.solved;
        if (o.settings) {
          if (typeof o.settings.sound === 'boolean') store.settings.sound = o.settings.sound;
          if (typeof o.settings.vibrate === 'boolean') store.settings.vibrate = o.settings.vibrate;
        }
        if (typeof o.lastTier === 'number') store.lastTier = o.lastTier;
        if (typeof o.lastItem === 'number') store.lastItem = o.lastItem;
      }
    } catch (e) {}
  }
  function saveStore() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(store)); } catch (e) {}
  }

  /* ============================ 音效 ============================ */

  var Sfx = {
    ctx: null,
    ensure: function () {
      if (!store.settings.sound) return null;
      if (!this.ctx) {
        var AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) return null;
        try { this.ctx = new AC(); } catch (e) { return null; }
      }
      if (this.ctx.state === 'suspended') { try { this.ctx.resume(); } catch (e) {} }
      return this.ctx;
    },
    tone: function (freq, dur, type, vol, delay) {
      var ctx = this.ensure();
      if (!ctx) return;
      try {
        var t0 = ctx.currentTime + (delay || 0);
        var osc = ctx.createOscillator(), g = ctx.createGain();
        osc.type = type || 'sine';
        osc.frequency.setValueAtTime(freq, t0);
        g.gain.setValueAtTime(0.0001, t0);
        g.gain.linearRampToValueAtTime(vol == null ? 0.07 : vol, t0 + 0.012);
        g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
        osc.connect(g); g.connect(ctx.destination);
        osc.start(t0); osc.stop(t0 + dur + 0.03);
      } catch (e) {}
    },
    tap: function () { this.tone(700, 0.05, 'sine', 0.035); },
    pick: function () { this.tone(540, 0.07, 'triangle', 0.05); },
    good: function () { this.tone(660, 0.09, 'triangle', 0.06); this.tone(990, 0.1, 'sine', 0.05, 0.07); },
    wrong: function () { this.tone(170, 0.16, 'square', 0.045); },
    win: function () { var s = [523, 659, 784, 1046]; for (var i = 0; i < s.length; i++) this.tone(s[i], 0.3, 'sine', 0.06, i * 0.08); }
  };

  function buzz(ms) {
    if (!store.settings.vibrate) return;
    if (navigator.vibrate) { try { navigator.vibrate(ms || 12); } catch (e) {} }
  }

  /* ============================ 一局状态 ============================ */

  var S = {
    screen: 'home',
    tier: 0,
    item: 0,
    data: null,           // 当前题 { w, py, b, em, hint }
    chars: [],            // 汉字数组
    slots: [],            // 空缺下标（升序）
    filled: {},           // slotIdx -> 已填字
    selSlot: null,        // 当前选中空缺（slotIdx 或 null）
    bank: [],             // [{id,char,answer}]
    done: false
  };

  function currentItem() { return E.getItem(S.tier, S.item); }
  function keyOf() { return S.tier + ':' + S.item; }

  function startLevel(tier, item) {
    var it = E.getItem(tier, item);
    if (!it) return;
    S.tier = tier; S.item = item; S.data = it;
    S.chars = it.w.split('');
    S.slots = it.b.slice();
    S.filled = {};
    var bank = E.buildBank(tier, item, (Date.now() & 0xffffffff));
    S.bank = bank ? bank.tiles : [];
    S.selSlot = null;
    S.done = false;
    store.lastTier = tier; store.lastItem = item;
    saveStore();
    render();
    show('game');
  }

  /* ============================ 渲染 ============================ */

  function render() {
    renderBoard();
    renderBank();
    renderMeta();
    updateTopbar();
    updateProgress();
  }

  function renderBoard() {
    var box = $('#board-cells');
    box.innerHTML = '';
    S.chars.forEach(function (ch, idx) {
      var isBlank = S.slots.indexOf(idx) >= 0;
      var cell = el('button', 'cell' + (isBlank ? ' blank' : ' pre'));
      cell.type = 'button';
      cell.dataset.idx = String(idx);

      if (!isBlank) {
        cell.textContent = ch;
        cell.addEventListener('click', () => onPreTap(idx));
      } else {
        var fill = S.filled[idx];
        if (fill) {
          cell.classList.add('has');
          cell.textContent = fill;
        } else {
          var py = (S.data.py && S.data.py[idx]) || '';
          cell.innerHTML = '<span class="py">' + esc(py) + '</span>';
        }
        if (S.selSlot === idx && !S.filled[idx]) cell.classList.add('sel');
        cell.addEventListener('click', function () { onBlankTap(idx); });
      }
      box.appendChild(cell);
    });
  }

  function renderBank() {
    var box = $('#bank');
    box.innerHTML = '';
    S.bank.forEach(function (tile) {
      var b = el('button', 'char-btn');
      b.type = 'button';
      b.textContent = tile.char;
      b.dataset.id = tile.id;
      b.addEventListener('click', function () { onCharTap(tile); });
      box.appendChild(b);
    });
  }

  function renderMeta() {
    var c = $('#clue');
    if (!c) return;
    var it = S.data;
    if (it.hint) c.innerHTML = '💡 ' + esc(it.hint);
    else {
      var shown = S.chars.map(function (ch, i) {
        return S.slots.indexOf(i) >= 0 ? '<span class="clue-pyb">' + esc(S.data.py[i] || '') + '</span>' : '<span class="clue-ch">' + esc(ch) + '</span>';
      }).join('');
      c.innerHTML = '把 拼音 填成 汉字：' + shown;
    }
  }

  function updateProgress() {
    var p = $('#progress-line');
    if (p) p.textContent = '第 ' + (S.tier + 1) + ' 档 · 第 ' + (S.item + 1) + '/' + E.itemCount(S.tier) + ' 题'
      + (store.solved[keyOf()] ? ' · ✓ 已拼对' : '');
  }

  function updateTopbar() {
    var t1 = $('#game-title'), t2 = $('#game-sub');
    if (t1) t1.textContent = '朵朵填字乐园';
    if (t2) t2.textContent = E.tierName(S.tier) + ' · 第 ' + (S.item + 1) + '/' + E.itemCount(S.tier) + ' 题';
  }

  /* ============================ 交互 ============================ */

  function onPreTap(idx) {
    if (S.done) return;
    // 已显示的字：点一下只给音效示意
    Sfx.pick();
    toast(S.chars[idx] + ' 是 " ' + (S.data.py[idx] || '') + '"');
  }

  function onBlankTap(idx) {
    if (S.done) return;
    if (!S.filled[idx]) { S.selSlot = idx; Sfx.pick(); renderBoard(); renderBank(); return; }
    // 已填格的格子：点它取消（退回候选）
    delete S.filled[idx];
    S.selSlot = idx;
    Sfx.pick();
    renderBoard(); renderBank();
  }

  function onCharTap(tile) {
    if (S.done) return;
    var idx = S.selSlot;
    if (idx == null) {
      Sfx.wrong();
      toast('先点一个空格，再选这个字');
      return;
    }
    if (S.filled[idx]) return;
    var correct = E.isCorrect(S.tier, S.item, idx, tile.char);
    if (correct) {
      S.filled[idx] = tile.char;
      S.selSlot = null;
      Sfx.good(); buzz(20);
      render();
      checkWin();
    } else {
      Sfx.wrong(); buzz(25);
      wrongFlash(idx);
    }
  }

  function wrongFlash(idx) {
    var cell = $('.cell.blank[data-idx="' + idx + '"]');
    if (!cell) return;
    cell.classList.add('wrong');
    setTimeout(function () { cell.classList.remove('wrong'); }, 430);
  }

  function checkWin() {
    var all = S.slots.every(function (i) { return S.filled[i]; });
    if (all) onWin();
  }

  function onWin() {
    S.done = true;
    store.solved[keyOf()] = true;
    saveStore();
    Sfx.win(); confetti();
    updateProgress();
    openModal(
      partyHTML(S.data.em) +
      '<h2>' + pick(['太棒了！', '拼对啦！', '你真聪明！', '好厉害！']) + '</h2>' +
      '<div class="answer-word">' + S.chars.map(function (c, i) {
        return '<span class="aw-cell' + (S.slots.indexOf(i) >= 0 ? ' done' : '') + '">' + esc(c) + '</span>';
      }).join('') + '</div>' +
      (S.data.hint ? '<p class="a-hint">' + esc(S.data.hint) + '</p>' : '') +
      '<div class="row">' +
      '<button class="btn btn-grey" data-action="home">回首页</button>' +
      '<button class="btn btn-green" data-action="next">下一题</button>' +
      '</div>',
      true
    );
  }

  /* ============================ 首页 / 选关 ============================ */

  function renderHome() {
    var solved = 0, total = 0;
    for (var t = 0; t < E.tierCount(); t++) for (var i = 0; i < E.itemCount(t); i++) {
      total++;
      if (store.solved[t + ':' + i]) solved++;
    }
    var p = $('#home-progress');
    if (p) p.textContent = '已拼对 ' + solved + ' / ' + total + ' 题';
  }

  function renderTiers() {
    var box = $('#tier-grid');
    box.innerHTML = '';
    for (var t = 0; t < E.tierCount(); t++) {
      var done = 0, n = E.itemCount(t);
      for (var i = 0; i < n; i++) if (store.solved[t + ':' + i]) done++;
      var all = done === n;
      var b = el('button', 'tier' + (all ? ' done' : ''));
      b.type = 'button';
      b.innerHTML =
        '<div class="t-no">第 ' + (t + 1) + ' 档</div>' +
        '<div class="t-name">' + esc(E.tierName(t)) + '</div>' +
        '<div class="t-meta">' + done + ' / ' + n + ' 题' + (all ? ' ✓' : '') + '</div>' +
        '<div class="t-bar"><i style="width:' + (done / n * 100).toFixed(0) + '%"></i></div>';
      (function (ti) {
        b.addEventListener('click', function () { S.tier = ti; S.item = 0; renderLevels(); show('levels'); });
      })(t);
      box.appendChild(b);
    }
  }

  function renderLevels() {
    var t = S.tier;
    $('#levels-title').textContent = E.tierName(t);
    $('#levels-sub').textContent = '已完成 ' + countSolved(t) + ' / ' + E.itemCount(t) + ' 题';
    var box = $('#level-grid');
    box.innerHTML = '';
    for (var i = 0; i < E.itemCount(t); i++) {
      var b = el('button', 'lv' + (store.solved[t + ':' + i] ? ' done' : ''));
      b.type = 'button';
      b.textContent = String(i + 1);
      (function (ti, ii) {
        b.addEventListener('click', function () {
          S.tier = ti; S.item = ii;
          startLevel(ti, ii);
        });
      })(t, i);
      box.appendChild(b);
    }
  }

  function countSolved(t) {
    var c = 0;
    for (var i = 0; i < E.itemCount(t); i++) if (store.solved[t + ':' + i]) c++;
    return c;
  }

  /* ============================ 弹窗 ============================ */

  function openModal(html, lock) {
    var root = $('#modal-root');
    root.innerHTML = '<div class="modal">' + html + '</div>';
    root.dataset.lock = lock ? '1' : '';
    root.classList.add('show');
    $$('[data-action]', root).forEach(function (b) {
      b.addEventListener('click', function () { handleAction(b.dataset.action); });
    });
  }
  function closeModal() {
    $('#modal-root').classList.remove('show');
    $('#modal-root').innerHTML = '';
  }
  function handleAction(a) {
    switch (a) {
      case 'home': closeModal(); show('home'); break;
      case 'next': {
        closeModal();
        var n = E.itemCount(S.tier);
        var ni = (S.item + 1) % n;
        if (ni === 0) { S.item = 0; show('levels'); }
        else startLevel(S.tier, ni);
        break;
      }
      default: closeModal();
    }
  }

  /* ============================ 庆祝动画 ============================ */

  var HEART_SVG = '<svg viewBox="0 0 24 24"><path d="M12 21S3.6 15.4 3.6 9.7A4.9 4.9 0 0 1 12 6.1a4.9 4.9 0 0 1 8.4 3.6C20.4 15.4 12 21 12 21z" fill="currentColor"/></svg>';
  var STAR_SVG = '<svg viewBox="0 0 24 24"><path d="M12 2.6l2.9 5.9 6.5.9-4.7 4.6 1.1 6.5-5.8-3.1-5.8 3.1 1.1-6.5L2.6 9.4l6.5-.9z" fill="currentColor"/></svg>';
  var SPARKS = [
    { x: -64, y: -80, d: 0.00, c: '#f0692e', h: true },
    { x: 60, y: -96, d: 0.24, c: '#4cc97c', h: false },
    { x: -44, y: -114, d: 0.46, c: '#ffc93c', h: true },
    { x: 48, y: -64, d: 0.68, c: '#3fb4e6', h: false },
    { x: -18, y: -126, d: 0.90, c: '#ff8fb1', h: true },
    { x: 22, y: -44, d: 1.12, c: '#e0a324', h: false }
  ];

  function partyHTML(emoji) {
    var sparks = SPARKS.map(function (sp) {
      return '<span class="spark" style="--tx:' + sp.x + 'px;--ty:' + sp.y + 'px;--d:' + sp.d +
        's;color:' + sp.c + '">' + (sp.h ? HEART_SVG : STAR_SVG) + '</span>';
    }).join('');
    return '<div class="party">' +
      '<div class="cheer">真棒！</div>' +
      sparks +
      '<div class="party-animal">' + esc(emoji) + '</div>' +
      '</div>';
  }

  /* ============================ 提示条 / 撒花 ============================ */

  var toastTimer;
  function toast(msg, ms) {
    var t = $('#toast');
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.classList.remove('show'); }, ms || 1900);
  }

  function confetti() {
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    var box = el('div', 'confetti');
    var colors = ['#f0692e', '#4cc97c', '#8fdcc6', '#6ba8d0', '#ffc93c', '#2e5aa8'];
    for (var i = 0; i < 50; i++) {
      var p = el('i');
      p.style.left = (Math.random() * 100) + 'vw';
      p.style.background = colors[(Math.random() * colors.length) | 0];
      p.style.animationDuration = (1.5 + Math.random() * 1.5) + 's';
      p.style.animationDelay = (Math.random() * 0.4) + 's';
      p.style.opacity = String(0.7 + Math.random() * 0.3);
      box.appendChild(p);
    }
    document.body.appendChild(box);
    setTimeout(function () { if (box.parentNode) box.parentNode.removeChild(box); }, 3600);
  }

  /* ============================ 事件绑定 ============================ */

  function bind() {
    $('#btn-main-start').addEventListener('click', function () {
      // 从上次玩到的地方继续
      if (store.solved[store.lastTier + ':' + store.lastItem]) {
        // 已拼过也继续这题让朵朵看着再玩一次也无妨
      }
      startLevel(store.lastTier, store.lastItem);
    });
    $('#btn-main-tiers').addEventListener('click', function () { renderTiers(); show('chapters'); });

    $$('[data-back]').forEach(function (b) {
      b.addEventListener('click', function () { show(b.dataset.back); });
    });

    $('#btn-levels-back').addEventListener('click', function () { show('chapters'); });
    $('#btn-game-back').addEventListener('click', function () { show('home'); });
    $('#btn-reload').addEventListener('click', function () { startLevel(S.tier, S.item); });
    $('#btn-prev').addEventListener('click', function () {
      var n = E.itemCount(S.tier);
      startLevel(S.tier, (S.item - 1 + n) % n);
    });
    $('#btn-next').addEventListener('click', function () { handleAction('next'); });

    $('#modal-root').addEventListener('click', function (e) {
      if (e.target === this && !this.dataset.lock) closeModal();
    });

    document.addEventListener('gesturestart', function (e) { e.preventDefault(); }, { passive: false });
    document.addEventListener('dblclick', function (e) { e.preventDefault(); }, { passive: false });
  }

  /* ============================ 屏幕切换 ============================ */

  function show(name) {
    S.screen = name;
    $$('.screen').forEach(function (s) { s.classList.toggle('active', s.id === 'screen-' + name); });
    if (name === 'home') renderHome();
    if (name === 'chapters') renderTiers();
    if (name === 'levels') renderLevels();
    if (name === 'game') render();
  }

  /* ============================ 调试接口 ============================ */

  function exposeDebug() {
    window.__PZ__ = {
      state: function () {
        return {
          screen: S.screen, tier: S.tier, item: S.item, done: S.done,
          chars: S.chars.slice(), slots: S.slots.slice(),
          filled: Object.assign({}, S.filled), selSlot: S.selSlot,
          bank: S.bank.map(function (t) { return { id: t.id, char: t.char, answer: t.answer }; })
        };
      },
      startTier: function (t) { S.tier = t; S.item = 0; renderTiers(); show('chapters'); },
      startLevel: startLevel,
      clickBlank: function (i) { onBlankTap(i); },
      clickChar: function (ch) {
        var tile = S.bank.filter(function (x) { return x.char === ch; })[0];
        if (tile) onCharTap(tile);
      },
      store: store
    };
  }

  /* ============================ 启动 ============================ */

  function registerSW() {
    if (!('serviceWorker' in navigator)) return;
    if (location.protocol !== 'http:' && location.protocol !== 'https:') return;
    navigator.serviceWorker.register('sw.js').catch(function (e) {
      if (window.console && console.warn) console.warn('[PZ] SW 注册失败：', e && e.message);
    });
  }

  function init() {
    loadStore();
    bind();
    renderHome();
    show('home');
    if (/[?&]debug\b/.test(location.search)) exposeDebug();
    registerSW();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();