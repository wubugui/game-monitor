/* 游戏项目监控 — static SPA over data/*.json (built by scripts/build_site.py) */
(function () {
  const $app = document.getElementById('app');
  const cache = {};
  const get = (u) => cache[u] || (cache[u] = fetch(u, { cache: 'no-cache' }).then(r => { if (!r.ok) throw new Error(u + ' ' + r.status); return r.json(); }));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const annotateAdded = (s) => {
    if (!s || !/<!--\s*added:(\d{4}-\d{2}-\d{2}|meta)\s*-->/i.test(s)) return s || '';
    const parts = s.split(/<!--\s*added:(\d{4}-\d{2}-\d{2}|meta)\s*-->/i);
    let out = parts[0];
    for (let i = 1; i < parts.length; i += 2) {
      const d = parts[i], body = parts[i + 1] || '';
      if (d === 'meta') { out += `\n\n${body}`; continue; }
      out += `\n\n<div class="added-block" data-added="${d}">\n\n${body}\n\n</div>\n\n`;
    }
    return out;
  };
  const md = (s) => DOMPurify.sanitize(marked.parse(annotateAdded(s) || '', { gfm: true, breaks: false }), { ADD_ATTR: ['target', 'data-added'] });
  const highlightDiff = (root, meta) => {
    if (!root || !meta) return;
    const latest = meta.latest_report_date || meta.data_date;
    const baselineOnly = !!meta.baseline_only;
    root.querySelectorAll('[data-added]').forEach(n => {
      const d = n.getAttribute('data-added');
      if (baselineOnly || d !== latest) {
        if (baselineOnly) {
          n.classList.add('added-baseline');
          if (![...n.childNodes].some(c => c.classList && c.classList.contains('badge'))) {
            n.insertAdjacentHTML('afterbegin', '<span class="badge baseline-tag">初始</span>');
          }
        }
        return;
      }
      n.classList.add('added-new');
      if (![...n.childNodes].some(c => c.classList && c.classList.contains('badge'))) {
        n.insertAdjacentHTML('afterbegin', '<span class="badge new">NEW</span>');
      }
    });
  };
  const WD = ['日', '一', '二', '三', '四', '五', '六'];
  const fmtDate = (d) => { if (!d) return ''; const t = new Date(d + 'T00:00:00'); return isNaN(t) ? d : `${t.getMonth() + 1}月${t.getDate()}日 周${WD[t.getDay()]}`; };
  const today = () => { const t = new Date(); return t.toISOString().slice(0, 10); };
  const daysAgo = (d) => { if (!d) return ''; const n = Math.round((new Date(today()) - new Date(d)) / 864e5); return n <= 0 ? '今天' : n === 1 ? '昨天' : n < 30 ? n + ' 天前' : d; };

  const SRC = (p) => p.disc_platform ? `<span class="badge src" title="${esc(p.discovery || '')}">${esc(p.disc_platform)}</span>` : '';
  function card(p, latest) {
    const cv = p.cover ? `<div class="cv" style="background-image:url('${esc(p.cover)}')">` : `<div class="cv none">◆`;
    return `<a class="card" href="#/project/${encodeURIComponent(p.id)}">${cv}${p.competitor ? '<span class="badge comp">⚠️ 竞品</span>' : ''}${p.missing_images ? '<span class="badge comp" style="background:#c00;color:#fff">缺图</span>' : ''}</div>
      <div class="body"><div class="nm">${esc(p.name)}</div>
      <div class="tags"><span class="badge st" title="${p.status_inferred ? '根据描述推测' : ''}">${esc(p.status)}${p.status_inferred ? '?' : ''}</span><span class="badge">${esc(p.dev_type)}</span>${SRC(p)}${(p.genre_tags || []).slice(0, 2).map(g => `<span class="badge">${esc(g)}</span>`).join('')}${latest && p.updated === latest ? '<span class="badge new">新</span>' : ''}</div>
      <div class="sm">${esc(p.genre)}${p.summary ? ' · ' + esc(p.summary) : ''}</div>
      <div class="ft"><span>更新 ${esc(p.updated || '—')}</span><span>${esc(p.source || '')}</span></div></div></a>`;
  }
  const grid = (ps, latest) => ps.length ? `<div class="grid">${ps.map(p => card(p, latest)).join('')}</div>` : '<div class="empty">暂无项目</div>';

  function setNav(k) { document.querySelectorAll('[data-nav]').forEach(a => a.classList.toggle('on', a.dataset.nav === k)); }

  function todayRow(u) {
    const cv = u.cover
      ? `<div class="tu-cv" style="background-image:url('${esc(u.cover)}')"></div>`
      : `<div class="tu-cv none">◆</div>`;
    const kind = u.kind === 'new'
      ? '<span class="badge new">新增</span>'
      : '<span class="badge upd">更新</span>';
    const comp = u.competitor ? '<span class="badge comp">⚠️ 竞品</span>' : '';
    return `<a class="tu-item" href="#/project/${encodeURIComponent(u.id)}">${cv}
      <div class="tu-body"><div class="tu-top">${kind}${comp}${SRC(u)}<span class="tu-nm">${esc(u.name)}</span></div>
      <div class="tu-note">${esc(u.note || '')}</div>
      <div class="tu-meta">${esc(u.genre || '')}${u.status ? ' · ' + esc(u.status) : ''}</div></div></a>`;
  }

  // ---------------- home
  async function home() {
    setNav('home');
    const [meta, reports, projects] = await Promise.all([get('data/meta.json'), get('data/reports.json'), get('data/projects.json')]);
    const latest = reports[0];
    const today = meta.today_updates || [];
    const todayNew = meta.today_new != null ? meta.today_new : today.filter(x => x.kind === 'new').length;
    const todayUpd = meta.today_updated != null ? meta.today_updated : today.filter(x => x.kind === 'updated').length;
    let h = `<h1>游戏项目监控</h1><div class="sub">B 站 + X + 小红书 · 竞品、独立开发者与中型厂商 · 数据截至 ${esc(meta.data_date || '—')}</div>
    <div class="stats"><div class="stat"><b>${meta.project_count}</b><span>跟踪项目</span></div><div class="stat"><b>${meta.competitor_count}</b><span>⚠️ 竞品</span></div><div class="stat"><b>${todayNew + todayUpd}</b><span>今日新增/更新</span></div><div class="stat"><b>${meta.report_count}</b><span>历史日报</span></div></div>`;

    // 「今日更新」 — only NEW / UPDATED that day; older games live in 项目库
    const dayLabel = meta.latest_report_date || meta.data_date || '';
    h += `<div class="sec-h"><h2>今日更新</h2><a href="#/projects">完整项目库 →</a></div>`;
    if (meta.today_banner) h += `<div class="today-banner">${esc(meta.today_banner)}</div>`;
    if (!today.length) {
      h += `<div class="empty">今天没有新增或更新的游戏。${meta.baseline_only ? '（初始基线日：全部项目见项目库）' : ''}往日档案请打开项目库浏览。</div>`;
    } else {
      const comps = today.filter(x => x.competitor);
      const others = today.filter(x => !x.competitor);
      h += `<div class="sub" style="margin-bottom:10px">${esc(dayLabel)}${dayLabel ? ' · ' + fmtDate(dayLabel) : ''} · 新增 ${todayNew} · 更新 ${todayUpd}（竞品优先）</div>`;
      if (comps.length) {
        h += `<div class="tu-label">⚠️ 竞品（${comps.length}）</div><div class="tu-list">${comps.map(todayRow).join('')}</div>`;
      }
      if (others.length) {
        h += `<div class="tu-label">其他（${others.length}）</div><div class="tu-list">${others.map(todayRow).join('')}</div>`;
      }
    }
    h += `<div class="home-links"><a class="btn" href="#/projects">全部项目库</a><a class="btn" href="#/projects?comp=1">⚠️ 竞品专区</a><a class="btn" href="#/reports">日报归档</a></div>`;

    if (latest) {
      h += `<div class="sec-h"><h2>最新日报</h2><a href="#/reports">全部日报 →</a></div>
      <div class="hero"><div class="sub">${esc(latest.date)} · ${fmtDate(latest.date)}</div><h3 style="margin:4px 0 8px"><a href="#/report/${esc(latest.id)}">${esc(latest.title)}</a></h3>
      <div>${esc(latest.summary)}</div>${latest.sections && latest.sections.length ? `<div class="tags" style="margin-top:10px">${latest.sections.map(s => `<span class="badge">${esc(s)}</span>`).join('')}</div>` : ''}
      ${latest.images && latest.images.length ? `<div class="imgs">${latest.images.map(i => `<img loading="lazy" src="${esc(i)}" alt="">`).join('')}</div>` : ''}
      <div style="margin-top:12px"><a class="btn" href="#/report/${esc(latest.id)}">阅读全文</a></div></div>`;
    } else {
      h += `<div class="sec-h"><h2>最新日报</h2></div><div class="empty">还没有日报，第一份生成后会显示在这里。</div>`;
    }
    if (reports.length > 1) h += `<div class="sec-h"><h2>往期日报</h2><a href="#/reports">归档 →</a></div>${archList(reports.slice(1, 6))}`;
    $app.innerHTML = h;
  }

  // ---------------- reports archive
  function archList(rs) {
    return `<div class="arch-list">${rs.map(r => `<a class="arch-item" href="#/report/${esc(r.id)}">
      <div class="th" style="${r.images && r.images[0] ? `background-image:url('${esc(r.images[0])}')` : ''}"></div>
      <div><div class="sub">${esc(r.date)} · ${fmtDate(r.date)} · ${r.image_count || 0} 张图</div><div class="t">${esc(r.title)}</div><div class="sub">${esc((r.summary || '').slice(0, 110))}</div></div></a>`).join('')}</div>`;
  }
  async function reportsPage() {
    setNav('reports');
    const reports = await get('data/reports.json');
    let h = `<h1>日报归档</h1><div class="sub">共 ${reports.length} 份，全部永久保留，最新在前。</div>`;
    if (!reports.length) h += '<div class="empty" style="margin-top:20px">还没有日报</div>';
    const byMonth = {};
    reports.forEach(r => (byMonth[r.date.slice(0, 7)] = byMonth[r.date.slice(0, 7)] || []).push(r));
    Object.keys(byMonth).sort().reverse().forEach(m => { h += `<div class="arch-month">${m.replace('-', ' 年 ')} 月 · ${byMonth[m].length} 份</div>${archList(byMonth[m])}`; });
    $app.innerHTML = h;
  }
  async function reportPage(id) {
    setNav('reports');
    const [meta, reports, r] = await Promise.all([get('data/meta.json'), get('data/reports.json'), get('data/report/' + id + '.json')]);
    const i = reports.findIndex(x => x.id === id);
    const newer = reports[i - 1], older = reports[i + 1];
    const pager = `<div class="pager">${older ? `<a class="btn" href="#/report/${esc(older.id)}">← ${esc(older.date)}</a>` : '<span></span>'}<a class="btn" href="#/reports">归档</a>${newer ? `<a class="btn" href="#/report/${esc(newer.id)}">${esc(newer.date)} →</a>` : '<span></span>'}</div>`;
    const body = document.createElement('div'); body.className = 'md'; body.innerHTML = md(r.md);
    const heads = [...body.querySelectorAll('h2,h3')]; heads.forEach((hh, k) => hh.id = 's' + k);
    const toc = heads.map((hh, k) => `<a href="javascript:void 0" data-sec="s${k}" style="padding-left:${hh.tagName === 'H3' ? 12 : 0}px">${esc(hh.textContent)}</a>`).join('');
    const tracked = r.projects && r.projects.length ? `<h2>本期涉及的项目（${r.projects.length}）</h2><div class="chips">${r.projects.map(p => `<a class="card chip" href="#/project/${encodeURIComponent(p.id)}"><div class="cv${p.cover ? '' : ' none'}" style="${p.cover ? `background-image:url('${esc(p.cover)}')` : ''}">${p.cover ? '' : '◆'}${p.competitor ? '<span class="badge comp">⚠️</span>' : ''}</div><div class="body"><div class="nm">${esc(p.name)}</div></div></a>`).join('')}</div>` : '';
    $app.innerHTML = `${pager}<div class="sub">${esc(r.date)} · ${fmtDate(r.date)}</div>
      <div class="report-wrap"><nav class="toc">${toc}</nav><article id="rbody"></article></div>${tracked}${pager}`;
    const art = document.getElementById('rbody');
    if (!/^#\s/m.test(r.md)) art.insertAdjacentHTML('afterbegin', `<h1>${esc(r.title)}</h1>`);
    art.appendChild(body);
    highlightDiff(art, meta);
    $app.querySelectorAll('[data-sec]').forEach(a => a.onclick = () => document.getElementById(a.dataset.sec).scrollIntoView({ behavior: 'smooth' }));
  }

  // ---------------- projects db
  async function projectsPage(q) {
    const comp = q.get('comp') === '1';
    setNav(comp ? 'comp' : 'projects');
    const [meta, projects] = await Promise.all([get('data/meta.json'), get('data/projects.json')]);
    const opt = (arr, v, all) => `<option value="">${all}</option>` + arr.map(x => `<option ${x === v ? 'selected' : ''}>${esc(x)}</option>`).join('');
    $app.innerHTML = `<h1>${comp ? '⚠️ 竞品专区' : '项目库'}</h1><div class="sub">每个被跟踪的项目，点卡片看完整档案和全部更新时间线。</div>
    <div class="filters">
      <input type="search" id="f-q" placeholder="搜索名称、类型、开发者、备注…" value="${esc(q.get('q') || '')}">
      <label><input type="checkbox" id="f-comp" ${comp ? 'checked' : ''}>只看竞品</label>
      <select id="f-genre">${opt(meta.genres, q.get('genre'), '全部类型')}</select>
      <select id="f-dev">${opt(meta.dev_types, q.get('dev'), '全部开发者')}</select>
      <select id="f-src">${opt(meta.disc_platforms || [], q.get('src'), '全部发现来源')}</select>
      <select id="f-status">${opt(meta.statuses, q.get('status'), '全部状态')}</select>
      <select id="f-sort"><option value="updated">按最近更新</option><option value="found" ${q.get('sort') === 'found' ? 'selected' : ''}>按发现日期</option><option value="name" ${q.get('sort') === 'name' ? 'selected' : ''}>按名称</option></select>
    </div><div class="count" id="f-count"></div><div id="f-grid"></div>`;
    const els = ['q', 'comp', 'genre', 'dev', 'src', 'status', 'sort'].reduce((o, k) => (o[k] = document.getElementById('f-' + k), o), {});
    function apply(push) {
      const s = { q: els.q.value.trim(), comp: els.comp.checked ? '1' : '', genre: els.genre.value, dev: els.dev.value, src: els.src.value, status: els.status.value, sort: els.sort.value === 'updated' ? '' : els.sort.value };
      const words = s.q.toLowerCase().split(/\s+/).filter(Boolean);
      let ps = projects.filter(p => (!s.comp || p.competitor) && (!s.genre || (p.genre_tags || []).includes(s.genre)) && (!s.dev || p.dev_type === s.dev) && (!s.src || p.disc_platform === s.src) && (!s.status || p.status === s.status) &&
        words.every(w => [p.name, p.genre, p.developer, p.note, p.summary, p.status, p.discovery, (p.genre_tags || []).join(' ')].join(' ').toLowerCase().includes(w)));
      const key = s.sort || 'updated';
      ps = ps.slice().sort((a, b) => key === 'name' ? a.name.localeCompare(b.name, 'zh') : (b[key] || '').localeCompare(a[key] || '') || (b.updated || '').localeCompare(a.updated || ''));
      document.getElementById('f-count').textContent = `${ps.length} / ${projects.length} 个项目`;
      document.getElementById('f-grid').innerHTML = grid(ps, meta.data_date);
      if (push) {
        const u = new URLSearchParams(); Object.entries(s).forEach(([k, v]) => v && u.set(k, v));
        const nh = '#/projects' + (u.toString() ? '?' + u : '');
        if (location.hash !== nh) { skip = true; history.replaceState(null, '', nh); }
        setNav(s.comp ? 'comp' : 'projects');
      }
    }
    Object.values(els).forEach(e => e.addEventListener(e.tagName === 'INPUT' && e.type === 'search' ? 'input' : 'change', () => apply(true)));
    apply(false);
  }

  async function projectPage(id) {
    setNav('projects');
    const [meta, p] = await Promise.all([get('data/meta.json'), get('data/project/' + id + '.json')]);
    const kv = [['类型', p.genre], ['开发者', p.developer + (p.dev_type && !String(p.developer).startsWith(p.dev_type) ? `（${p.dev_type}）` : '')], ['状态', p.status + (p.status_inferred ? '（根据描述推测）' : '')], ['平台', p.platform], ['发售', p.release], ['发现来源', (p.disc_platform ? '〔' + p.disc_platform + '〕' : '') + (p.discovery || '')], ['发现日期', p.found], ['最后更新', p.updated], ['来源', p.source], ['链接', p.link ? `<a href="${esc(p.link)}" target="_blank" rel="noopener">${esc(p.link)}</a>` : '']]
      .filter(x => x[1]).map(([k, v]) => `<dt>${k}</dt><dd>${k === '链接' ? v : esc(v)}</dd>`).join('');
    const tl = (p.history || []).map(e => `<div class="tl-item ${e.kind}"><div class="tl-date">${esc(e.date)}<span class="sub">${fmtDate(e.date)} · ${e.kind === 'found' ? '首次发现' : esc(e.title || (e.kind === 'report' ? '日报提及' : '更新'))}${e.report ? ` · <a href="#/report/${esc(e.report)}">看当天日报</a>` : ''}</span></div>
      ${e.md ? `<div class="tl-card md">${md(e.md)}</div>` : ''}</div>`).join('');
    $app.innerHTML = `<div class="pager" style="margin-top:0"><a class="btn" href="javascript:history.back()">← 返回</a><span></span></div>
    <div class="proj-head">${p.cover ? `<img class="cover" src="${esc(p.cover)}" alt="">` : '<div class="card"><div class="cv none">◆</div></div>'}
    <div><h1>${esc(p.name)} ${p.competitor ? '<span class="badge comp">⚠️ 竞品</span>' : ''}${p.missing_images ? '<span class="badge comp" style="background:#c00;color:#fff">缺图</span>' : ''}</h1>
    <div class="tags">${(p.genre_tags || []).map(g => `<a class="badge" href="#/projects?genre=${encodeURIComponent(g)}">${esc(g)}</a>`).join('')}</div>
    <dl class="kv">${kv}</dl>${p.note ? `<div class="sub">备注：${esc(p.note)}</div>` : ''}</div></div>
    ${p.intro ? `<h2>档案</h2><div class="md">${md(p.intro)}</div>` : ''}
    ${p.images && p.images.length ? `<h2>画面</h2><div class="gallery">${p.images.map(i => `<img loading="lazy" src="${esc(i)}" alt="">`).join('')}</div>` : ''}
    <h2>更新时间线（${(p.history || []).length}）</h2>${tl ? `<div class="tl">${tl}</div>` : '<div class="empty">暂无记录</div>'}`;
    highlightDiff($app, meta);
  }

  // ---------------- router
  let skip = false;
  async function route() {
    if (skip) { skip = false; return; }
    const h = location.hash.replace(/^#/, '') || '/';
    const [path, qs] = h.split('?');
    const q = new URLSearchParams(qs || '');
    const seg = path.split('/').filter(Boolean).map(decodeURIComponent);
    try {
      if (!seg.length) await home();
      else if (seg[0] === 'reports') await reportsPage();
      else if (seg[0] === 'report' && seg[1]) await reportPage(seg[1]);
      else if (seg[0] === 'projects') await projectsPage(q);
      else if (seg[0] === 'project' && seg[1]) await projectPage(seg[1]);
      else await home();
    } catch (e) { $app.innerHTML = `<div class="empty">加载失败：${esc(e.message)}</div>`; }
    if (!/^\/projects/.test(path)) window.scrollTo(0, 0);
  }
  window.addEventListener('hashchange', route);
  route();
  get('data/meta.json').then(m => document.getElementById('foot-meta').textContent = `${m.project_count} 个项目 · ${m.report_count} 份日报 · 数据截至 ${m.data_date || '—'}`).catch(() => { });

  // lightbox for any image
  const lb = document.getElementById('lightbox');
  document.addEventListener('click', e => {
    const t = e.target;
    if (t.tagName === 'IMG' && !t.closest('#lightbox') && !t.closest('a')) { lb.querySelector('img').src = t.src; lb.hidden = false; }
  });
  lb.addEventListener('click', () => lb.hidden = true);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') lb.hidden = true; });
})();
