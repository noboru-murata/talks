/* embed.js — デモをスライドに埋め込み，スライドの頁送りで場面を進める (2026-11-07)
 *
 * デモの側: ?embed を付けて開くと
 *   - 上の帯・下の帯・説明の文を隠し，図 (と右の欄) と場面の題だけにする (説明はスライドに書く)．
 *   - スライド (親) から {channel: 'oxq-demo', type: 'step', dir: 'next'|'prev'} を受けて一段進める．
 *     進めなかった (場面の範囲の端) ときは {type: 'edge', dir} を返し，親が次の頁へ移る．
 *   - {type: 'enter', at: 'start'|'end'} で範囲の最初 (前から来たとき) か最後 (後ろから戻ったとき) へ．
 *   - 図の中をクリックしたあとでも ← → は同じ動き (端なら親に頁送りを頼む)．
 * デモは window.demoSteps = {next(), prev(), start(), end()} を用意する (next / prev は進めたら true)．
 * スライドの側は deck-steps.js．
 */
(function () {
  var qp = new URLSearchParams(location.search);
  if (!qp.has('embed')) return;
  var CH = 'oxq-demo';
  document.documentElement.classList.add('embed');
  var st = document.createElement('style');
  st.textContent =
    'html.embed body { grid-template-rows: auto 1fr !important; background: var(--surface-1); }' +
    'html.embed header, html.embed footer, html.embed #prompt, html.embed #xpBtn { display: none !important; }' +
    'html.embed .intro { height: auto !important; padding: 4px 14px 2px !important; border-bottom: 0 !important; background: transparent !important; }' +
    'html.embed .intro h2 { font-size: 15px !important; color: var(--text-secondary); margin: 0 !important; }' +
    'html.embed .side { font-size: 12.5px; }';
  document.head.append(st);
  // 場面の題の欄が無いデモ (mds，atlas) には，上に一行の題の欄を足す．window.embedCaption(文) で書く
  if (!document.querySelector('.intro')) {
    st.textContent += 'html.embed .embed-cap { padding: 4px 14px 2px; font-size: 15px; font-weight: 600; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }';
    var cap = document.createElement('div'); cap.className = 'embed-cap';
    document.body.prepend(cap);
    window.embedCaption = function (t) { cap.textContent = t || ''; };
  }
  function api() { return window.demoSteps; }
  function send(m) { m.channel = CH; try { parent.postMessage(m, '*'); } catch (e) {} }
  function step(dir) {
    var a = api(); if (!a) return;
    var moved = dir === 'next' ? a.next() : a.prev();
    if (!moved) send({ type: 'edge', dir: dir });
  }
  addEventListener('message', function (e) {
    var d = e.data; if (!d || d.channel !== CH) return;
    var a = api(); if (!a) return;
    if (d.type === 'step') { send({ type: 'ack' }); step(d.dir); }
    else if (d.type === 'enter') { if (d.at === 'end') a.end(); else a.start(); }
  });
  // 図の中にキーの焦点があるとき: デモの keydown より先に受ける
  addEventListener('keydown', function (e) {
    if (e.target.closest && e.target.closest('input,select,textarea')) return;
    var k = e.key, dir = null;
    if (k === 'ArrowRight' || k === 'PageDown' || k === ' ') dir = 'next';
    else if (k === 'ArrowLeft' || k === 'PageUp') dir = 'prev';
    if (!dir) return;
    e.preventDefault(); e.stopImmediatePropagation();
    step(dir);
  }, true);
  addEventListener('load', function () { send({ type: 'ready' }); });
})();
