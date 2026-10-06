/*
 * share.js — 让每个计算器结果可被分享、可被引用。
 *
 * 把当前输入编码进 URL 的 hash（#salary=75000&pct=6...），
 * 打开链接时自动还原并重新计算，并提供「复制链接」按钮。
 *
 * 为什么用 hash 而不是 query string（?a=1）：
 *   URL fragment 不会发送给服务器，搜索引擎不会把它当成新页面，
 *   因此不会产生成千上万个重复内容的 URL（那会稀释权重、拖慢收录）。
 *   这是刻意的设计选择，不要改成 ? 参数。
 *
 * 由 build.py 内联注入，不产生额外 HTTP 请求。
 */
(function () {
  var results = document.getElementById('results');
  if (!results) return;

  /* ---- 1. 收集需要序列化的字段（结果区之前的所有带 id 控件）---- */
  var fields = [];
  var all = document.querySelectorAll('input[id], select[id]');
  for (var i = 0; i < all.length; i++) {
    if (results.contains(all[i])) continue;   // 结果区内的不算输入
    fields.push(all[i]);
  }
  if (!fields.length) return;

  function read() {
    var p = new URLSearchParams();
    for (var i = 0; i < fields.length; i++) {
      var el = fields[i];
      p.set(el.id, el.value);
    }
    return p;
  }

  function apply(params) {
    var touched = false;
    for (var i = 0; i < fields.length; i++) {
      var el = fields[i];
      if (!params.has(el.id)) continue;
      var v = params.get(el.id);
      if (v === null || v === el.value) continue;
      if (el.tagName === 'SELECT') {
        // 只接受该 select 真实存在的选项，避免脏参数
        var ok = false, opts = el.options;
        for (var j = 0; j < opts.length; j++) { if (opts[j].value === v) { ok = true; break; } }
        if (!ok) continue;
      }
      // 数值字段只接受数字。浏览器对 type=number 会自行拒绝脏值，
      // 但不能依赖它——脏值一旦进入计算就会产出 NaN 结果。
      if (el.tagName === 'INPUT' && el.type === 'number') {
        if (v !== '' && !isFinite(Number(v))) continue;
      }
      el.value = v;
      touched = true;
    }
    if (!touched) return;
    // 触发页面原有的计算逻辑（每个页面都把 calc 绑在 input/change 上）
    for (var k = 0; k < fields.length; k++) {
      try {
        fields[k].dispatchEvent(new Event('input', { bubbles: true }));
        fields[k].dispatchEvent(new Event('change', { bubbles: true }));
      } catch (e) { /* 老浏览器忽略 */ }
    }
  }

  /* ---- 2. 打开带参数的链接时还原 ---- */
  function fromHash() {
    var h = location.hash.replace(/^#/, '');
    if (!h) return;
    apply(new URLSearchParams(h));
  }
  fromHash();
  window.addEventListener('hashchange', fromHash);

  /* ---- 3. 输入变化时同步 hash（replaceState，不污染前进/后退）---- */
  var timer = null;
  function syncHash() {
    if (timer) clearTimeout(timer);
    timer = setTimeout(function () {
      var s = read().toString();
      var url = location.pathname + (s ? '#' + s : '');
      try { history.replaceState(null, '', url); } catch (e) { location.hash = s; }
    }, 250);
  }
  for (var m = 0; m < fields.length; m++) {
    fields[m].addEventListener('input', syncHash);
    fields[m].addEventListener('change', syncHash);
  }

  /* ---- 4. 复制按钮 ---- */
  var bar = document.createElement('div');
  bar.className = 'sharebar';

  var label = document.createElement('span');
  label.className = 'sharelabel';
  label.textContent = 'Share this calculation';
  bar.appendChild(label);

  var btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'sharebtn';
  btn.textContent = 'Copy link';
  bar.appendChild(btn);

  var hint = document.createElement('span');
  hint.className = 'sharehint';
  bar.appendChild(hint);

  function link() {
    return location.origin + location.pathname + '#' + read().toString();
  }

  function flash(msg, good) {
    hint.textContent = msg;
    hint.className = 'sharehint' + (good ? ' ok' : '');
    setTimeout(function () { hint.textContent = ''; }, 2600);
  }

  btn.addEventListener('click', function () {
    var url = link();
    function fallback() {
      var ta = document.createElement('textarea');
      ta.value = url;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
      document.body.removeChild(ta);
      flash(ok ? 'Link copied' : url, ok);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(function () {
        flash('Link copied — paste it anywhere');
      }, fallback);
    } else {
      fallback();
    }
  });

  // 挂到结果区末尾
  results.appendChild(bar);
})();
