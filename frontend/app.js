/*
 * 世界历史地图 — 前端主程序（纯原生 JS + 本地 Leaflet，无构建步骤）
 *
 * 结构：
 *  - 时间：state.date = {y, m, d}，y 为历史纪年（-1 = 公元前1年，无0年），m/d 为 0 表示不指定。
 *  - 时间轴：非线性分段映射（史前压缩、近代拉伸），见 SEGMENTS。
 *  - 地图：按日期取「不晚于该日期的最近边界快照」，GeoJSON 由后端 /api/basemap/{snap} 提供。
 *  - 侧边栏：标签页来自后端 /api/modules（模块注册表），每个模块默认用通用列表渲染器；
 *            模块若声明 frontend: "modules/xxx.js"，则动态加载该脚本，脚本调用
 *            WHA.registerRenderer(moduleId, fn) 注册自定义渲染函数。
 */
(() => {
  "use strict";

  // ---------------------------------------------------------------- 工具
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const toAstro = (y) => (y < 0 ? y + 1 : y);          // 历史纪年 -> 天文纪年
  const fromAstro = (a) => (a <= 0 ? a - 1 : a);       // 天文纪年 -> 历史纪年
  const yearZh = (y) => (y < 0 ? `公元前${-y}年` : `${y}年`);
  const dateZh = (dt) => yearZh(dt.y) + (dt.m ? `${dt.m}月` : "") + (dt.m && dt.d ? `${dt.d}日` : "");
  const dateParam = (dt) => `${dt.y}` + (dt.m ? `-${String(dt.m).padStart(2, "0")}` : "") + (dt.m && dt.d ? `-${String(dt.d).padStart(2, "0")}` : "");
  const api = async (path) => { const r = await fetch(path); if (!r.ok) throw new Error(await r.text()); return r.json(); };
  const isLeap = (y) => { const a = toAstro(y); return (a % 4 === 0 && a % 100 !== 0) || a % 400 === 0; };
  const daysIn = (y, m) => (m ? [31, isLeap(y) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1] : 31);

  // 时间轴分段：[天文年起, 天文年止, 滑块起, 滑块止]
  const NOW = new Date().getFullYear();
  const SEGMENTS = [
    [-122999, -10000, 0, 700],
    [-10000, -3000, 700, 1500],
    [-3000, 0, 1500, 3500],
    [0, 1500, 3500, 6900],
    [1500, NOW, 6900, 10000],
  ];
  const sliderToYear = (v) => {
    for (const [a0, a1, s0, s1] of SEGMENTS) if (v <= s1) return fromAstro(Math.round(a0 + ((v - s0) / (s1 - s0)) * (a1 - a0)));
    return NOW;
  };
  const yearToSlider = (y) => {
    const a = toAstro(y);
    for (const [a0, a1, s0, s1] of SEGMENTS) if (a <= a1) return s0 + ((Math.max(a, a0) - a0) / (a1 - a0)) * (s1 - s0);
    return 10000;
  };
  // 播放步长（年）：越早越粗
  const playStep = (y) => (y < -10000 ? 500 : y < -3000 ? 100 : y < 0 ? 10 : y < 1500 ? 5 : 1);

  // ---------------------------------------------------------------- 状态
  let zhNames = {};
  // 政权显示名：有可靠中文名时「中文（English）」，否则英文原名
  const pname = (n) => (!n ? "未命名区域" : zhNames[n]?.zh ? `${zhNames[n].zh}（${n}）` : n);
  // 按快照解析的中文名（来自当时存在的 Wikidata 政权）优先；没有时退回静态名称表
  const snapNames = {};
  const pnameF = (p) => {
    const z = p && snapNames[state.snap]?.[String(p.fid)];
    return !p?.NAME ? "未命名区域" : z ? (z.zh === p.NAME ? z.zh : `${z.zh}（${p.NAME}）`) : pname(p.NAME);
  };
  const qidF = (p) => (p && snapNames[state.snap]?.[String(p.fid)]?.qid) || zhNames[p?.NAME]?.qid;
  const pnameN = (n) => { const f = geoCache[state.snap]?.features.find((x) => x.properties.NAME === n); return f ? pnameF(f.properties) : pname(n); };
  const state = { date: { y: 1789, m: 7, d: 14 }, snap: null, next: null, fid: null, world: false, tab: null, playing: null, meta: null };
  const renderers = {};
  const layers = {};       // 已注册的地图图层（前端部分）
  const layerOn = {};      // 图层开关
  // 给模块脚本使用的公共接口（详见 README「如何添加模块」）
  window.WHA = {
    registerRenderer: (id, fn) => (renderers[id] = fn), registerLayer: (id, impl) => (layers[id] = impl), state, esc,
    api: (u) => api(u), dateParam: (d) => dateParam(d || state.date), dateZh: (d) => dateZh(d || state.date),
    setFillOverride: (fn, id = "default") => { if (fn) fillOverrides[id] = fn; else delete fillOverrides[id]; restyle(); },
    restyle: () => restyle(),
    tooltipExtra: {},   // 图层可在政权悬停提示后追加内容：WHA.tooltipExtra[id] = (props) => html 或 ""
    refreshPanel: () => refreshPanelData(), setDate: (d) => setDate(d),
    openDetail: (html) => { $("detailBody").innerHTML = html; $("detail").classList.remove("hidden"); $("detailBody").scrollTop = 0; return $("detailBody"); },
  };
  const panelMods = () => state.meta.modules.filter((m) => (m.kind || "panel") === "panel");
  const layerMods = () => state.meta.modules.filter((m) => m.kind === "layer");

  // ---------------------------------------------------------------- 地图
  const map = L.map("map", { worldCopyJump: true, minZoom: 2, maxZoom: 8, zoomSnap: 0.5, attributionControl: true }).setView([30, 20], 2.5);
  map.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>');
  map.attributionControl.addAttribution('边界：<a href="https://github.com/aourednik/historical-basemaps" target="_blank">historical-basemaps</a> (GPL-3.0) · 事件/人物：<a href="https://www.wikidata.org" target="_blank">Wikidata</a> (CC0)');
  let layer = null;
  const markers = L.layerGroup().addTo(map);
  const geoCache = {};

  const hue = (s) => { let h = 0; for (const c of s || "") h = (h * 31 + c.charCodeAt(0)) >>> 0; return h % 360; };
  const styleFor = (f, selected) => {
    const n = f.properties.NAME;
    const base = {
      color: selected ? "#8a1c00" : "#6b5a48", weight: selected ? 2.5 : 0.6, opacity: 0.9,
      fillColor: n ? `hsl(${hue(f.properties.SUBJECTO || n)}, 45%, ${selected ? 62 : 74}%)` : "#ddd6c8",
      fillOpacity: selected ? 0.85 : 0.75,
    };
    // 图层模块（如「阵营地图」）可以通过 WHA.setFillOverride(fn) 改写多边形填色
    let o = null;
    for (const fn of Object.values(fillOverrides)) { const x = fn(f); if (x) o = { ...(o || {}), ...x }; }
    return o ? { ...base, ...o, ...(selected ? { color: "#8a1c00", weight: 2.5 } : {}) } : base;
  };
  // 多个图层可同时改写填色：按注册顺序叠加（后注册的覆盖前面的同名样式）
  const fillOverrides = {};

  async function loadSnapshot(snap) {
    if (!geoCache[snap]) [geoCache[snap], snapNames[snap]] = await Promise.all([api(`/api/basemap/${snap}`), api(`/api/snapshot_names/${snap}`).catch(() => ({}))]);
    const gj = geoCache[snap];
    if (layer) map.removeLayer(layer);
    layer = L.geoJSON(gj, {
      style: (f) => styleFor(f, state.fid === f.properties.fid && !state.world),
      onEachFeature: (f, l) => {
        const p = f.properties;
        l.bindTooltip(() => esc(pnameF(p)) + (p.SUBJECTO && p.SUBJECTO !== p.NAME ? `<br><small>从属于：${esc(pnameN(p.SUBJECTO))}</small>` : "") +
          Object.values(WHA.tooltipExtra).map((fn) => fn(p) || "").join(""), { sticky: true });
        l.on("click", () => selectPolity(p.fid));
      },
    }).addTo(map);
    layer.bringToBack();
  }

  // ---------------------------------------------------------------- 日期控件
  function fillDateControls() {
    const dt = state.date;
    $("isBC").checked = dt.y < 0;
    $("yearIn").value = Math.abs(dt.y);
    const mi = $("monthIn");
    if (!mi.options.length) {
      mi.add(new Option("（月）", 0));
      for (let m = 1; m <= 12; m++) mi.add(new Option(`${m}月`, m));
    }
    mi.value = dt.m;
    const di = $("dayIn");
    di.innerHTML = "";
    di.add(new Option("（日）", 0));
    if (dt.m) for (let d = 1; d <= daysIn(dt.y, dt.m); d++) di.add(new Option(`${d}日`, d));
    di.value = dt.d;
    di.disabled = !dt.m;
    $("slider").value = yearToSlider(dt.y);
    $("dateLabel").textContent = dateZh(dt);
  }
  function readDateControls() {
    let y = parseInt($("yearIn").value, 10) || 1;
    y = Math.min(Math.max(y, 1), 123000);
    if ($("isBC").checked) y = -y;
    if (y > NOW) y = NOW;
    const m = parseInt($("monthIn").value, 10) || 0;
    let d = m ? parseInt($("dayIn").value, 10) || 0 : 0;
    if (d > daysIn(y, m)) d = daysIn(y, m);
    return { y, m, d };
  }

  async function setDate(dt, { refreshPanel = true } = {}) {
    state.date = dt;
    fillDateControls();
    const s = await api(`/api/snapshot?date=${dateParam(dt)}`);
    if (s.snapshot !== state.snap) {
      // 换快照后原来的政权 fid 不再有效：用政权名称在新快照中找同名政权，找不到就关闭面板
      const oldName = state.fid != null && geoCache[state.snap] ? featByFid(state.snap, state.fid)?.properties.NAME : null;
      state.snap = s.snapshot;
      state.next = s.next;
      await loadSnapshot(s.snapshot);
      if (oldName) {
        const f = geoCache[state.snap].features.find((x) => x.properties.NAME === oldName);
        state.fid = f ? f.properties.fid : null;
        if (!f && !state.world) closePanel();
        restyle();
      }
    }
    state.next = s.next;
    updateEraNote();
    updateHash();
    if (refreshPanel && (state.fid != null || state.world)) refreshPanelData();
    scheduleLayers();
  }

  // ---------------------------------------------------------------- 地图图层（模块）
  let layerTimer = null, layerSeq = 0;
  function scheduleLayers() { clearTimeout(layerTimer); layerTimer = setTimeout(updateLayers, state.playing ? 50 : 200); }
  async function updateLayers() {
    const seq = ++layerSeq;
    for (const m of layerMods()) {
      const impl = layers[m.id];
      if (!impl) continue;
      if (!layerOn[m.id]) { impl.clear(); continue; }
      try {
        // 图层可提供额外查询参数（如经济图层的 ind=指标）：impl.query() 返回 "&ind=..." 形式
        const res = await api(`/api/layers/${m.id}?date=${dateParam(state.date)}${impl.query ? impl.query() : ""}`);
        if (seq === layerSeq) impl.update(res, state);
      } catch (e) { console.warn("layer", m.id, e); }
    }
  }
  function buildLayerControl() {
    const box = document.createElement("div");
    box.id = "layerCtl";
    document.querySelector("main").appendChild(box);
    // URL 参数 #...&layers=cities,alliances 可指定打开哪些图层（便于分享/截图）
    const want = WHA.initialHash.get("layers");
    const on = want != null ? new Set(want.split(",")) : null;
    for (const m of layerMods()) { layerOn[m.id] = on ? on.has(m.id) : !!m.default_on; layers[m.id]?.init?.(map); }
    box.innerHTML = "图层：" + layerMods().map((m) => `<label title="${esc(m.description)}"><input type="checkbox" data-id="${m.id}" ${layerOn[m.id] ? "checked" : ""}> ${esc(m.title)}</label>`).join("");
    box.querySelectorAll("input").forEach((el) => el.addEventListener("change", () => { layerOn[el.dataset.id] = el.checked; updateLayers(); updateHash(); }));
  }

  const featByFid = (snap, fid) => geoCache[snap]?.features.find((f) => f.properties.fid === fid);

  function updateEraNote() {
    const y = state.date.y;
    const snapMeta = state.meta.snapshots.find((x) => x.year === state.snap) || {};
    const nxt = state.next != null ? `，下一张：${yearZh(state.next)}` : "";
    let html = snapMeta.label && snapMeta.label.startsWith("现代")
      ? `<b>边界：${esc(snapMeta.label)}</b>，用于 2011 年至今（边界变化以 Natural Earth 版本为准，争议地区按其“事实控制”画法）。`
      : `<b>边界快照：${yearZh(state.snap)}</b>${nxt}。地图显示不晚于所选日期的最近一张快照，两张快照之间的变化不会显示。`;
    if (y < -3000) html = `<b>史前时期（文字出现以前）</b>：地图上是 historical-basemaps 对考古文化与人群分布的粗略复原，不是国家边界；快照非常稀疏（当前：${yearZh(state.snap)}${state.next != null ? "，下一张：" + yearZh(state.next) : ""}）。Wikidata 中此时期几乎没有精确到年的事件和人物。`;
    else if (y < -500) html += "<br>上古时期：许多日期是估计值，人物生卒年常常只精确到世纪。";
    if (state.date.m && state.date.d) html += "<br>已精确到日：事件列表会把<b>当天</b>发生的事件排在最前（仅限 Wikidata 记录到日的事件）。";
    $("eraNote").innerHTML = html;
  }

  // ---------------------------------------------------------------- 侧边栏
  function restyle() { if (layer) layer.eachLayer((l) => l.setStyle(styleFor(l.feature, state.fid === l.feature.properties.fid && !state.world))); }
  function closePanel() { $("panel").classList.add("hidden"); state.fid = null; state.world = false; markers.clearLayers(); restyle(); updateHash(); }

  function selectPolity(fid) {
    state.fid = fid; state.world = false; state.stateSel = null;
    restyle();
    $("panel").classList.remove("hidden");
    refreshPanelData();
    updateHash();
  }

  let reqSeq = 0;
  const results = {};
  async function refreshPanelData() {
    const seq = ++reqSeq;
    const f = state.world ? null : featByFid(state.snap, state.fid);
    const p = f?.properties;
    $("polityName").textContent = state.world ? "全世界" : pnameF(p);
    $("polityMeta").innerHTML = state.world ? `${dateZh(state.date)} 前后 · 全球范围` :
      `${dateZh(state.date)} · 边界快照 ${yearZh(state.snap)}` +
      (p?.SUBJECTO && p.SUBJECTO !== p.NAME ? `<br>从属于：${esc(pnameN(p.SUBJECTO))}` : "") +
      (p?.PARTOF && p.PARTOF !== p.NAME && p.PARTOF !== p.SUBJECTO ? ` · 属于：${esc(pnameN(p.PARTOF))}` : "") +
      (qidF(p) ? ` · <a href="https://www.wikidata.org/wiki/${qidF(p)}" target="_blank">Wikidata</a>` : "") +
      (p?.BORDERPRECISION ? `<br>边界精度：${{ 1: "大致（1/3）", 2: "中等（2/3）", 3: "较精确（3/3）" }[p.BORDERPRECISION] || p.BORDERPRECISION}` : "");
    const mods = panelMods();
    if (!state.tab || !mods.find((m) => m.id === state.tab)) state.tab = mods[0]?.id;
    renderTabs();
    $("tabBody").innerHTML = '<div class="empty">加载中…</div>';
    const q = `date=${dateParam(state.date)}&snap=${state.snap}` + (state.world ? "" : `&fid=${state.fid}`) + (state.stateSel ? `&state=${state.stateSel}` : "");
    await Promise.all(mods.map(async (m) => {
      try { results[m.id] = await api(`/api/modules/${m.id}?${q}`); } catch (e) { results[m.id] = { items: [], total: 0, note: "出错：" + e.message }; }
      if (seq === reqSeq) { renderTabs(); if (m.id === state.tab) renderBody(); }
    }));
    // 标题用所选日期解析到的 Wikidata 政权中文名（比按快照年份的名称更准确，如 1948 年 6 月的「中华民国」）
    const rs = results.regime?.state;
    if (seq === reqSeq && rs && p && rs.name && rs.name !== p.NAME) $("polityName").textContent = `${rs.name}（${p.NAME}）`;
  }

  function renderTabs() {
    $("tabs").innerHTML = "";
    for (const m of panelMods()) {
      const b = document.createElement("button");
      const r = results[m.id];
      b.innerHTML = esc(m.title) + (r ? `<span class="count">${r.total}</span>` : "");
      b.title = m.description;
      b.className = m.id === state.tab ? "active" : "";
      b.onclick = () => { state.tab = m.id; renderTabs(); renderBody(); updateHash(); };
      $("tabs").appendChild(b);
    }
  }

  function renderBody() {
    const m = state.meta.modules.find((x) => x.id === state.tab);
    const r = results[state.tab];
    if (!m || !r) return;
    const fn = renderers[m.id] || defaultRenderer;
    $("tabBody").innerHTML = "";
    $("tabBody").appendChild(fn(r, m));
    drawMarkers(r.items);
  }

  // 通用列表渲染器：适用于所有返回统一 Item 格式的模块
  function defaultRenderer(r, m) {
    const box = document.createElement("div");
    box.className = `mod-${m.id}`;
    let html = r.note ? `<div class="note">${esc(r.note)}${r.total > r.items.length ? `；共 ${r.total} 条，显示前 ${r.items.length} 条` : ""}</div>` : "";
    if (!r.items.length) html += `<div class="empty">在当前数据中没有找到这一时期、这一地区的${esc(m.title)}记录。<br>注意：越早的年代、非欧洲地区，Wikidata 的覆盖越少；没有记录 ≠ 没有发生。</div>`;
    for (const it of r.items) {
      html += `<div class="item" data-id="${esc(it.id)}">
        <div class="t">${esc(it.title)}${it.title_en && it.title_en !== it.title ? `<span class="en">${esc(it.title_en)}</span>` : ""}
          ${it.match === "coord" ? '<span class="badge" title="坐标落在该政权范围内">坐标</span>' : it.match === "country" ? '<span class="badge country" title="按国家/国籍名称匹配">国籍</span>' : ""}</div>
        <div class="d">${esc(it.date)}</div>
        ${it.subtitle ? `<div class="s">${esc(it.subtitle)}</div>` : ""}
        <div class="l">${it.links.map((l) => `<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)}</a>`).join("")}</div>
      </div>`;
    }
    html += `<div class="source">来源：${esc(m.source)}</div>`;
    box.innerHTML = html;
    box.querySelectorAll(".item").forEach((el) => el.addEventListener("click", (ev) => {
      if (ev.target.tagName === "A") return;
      const it = r.items.find((x) => x.id === el.dataset.id);
      if (it?.coord) { map.flyTo([it.coord[1], it.coord[0]], Math.max(map.getZoom(), 5), { duration: 0.6 }); markerById[it.id]?.openPopup(); }
    }));
    return box;
  }

  let markerById = {};
  function drawMarkers(items) {
    markers.clearLayers();
    markerById = {};
    for (const it of items) {
      if (!it.coord) continue;
      const mk = L.circleMarker([it.coord[1], it.coord[0]], { radius: 5, color: "#8a1c00", weight: 1.5, fillColor: "#ffcc66", fillOpacity: 0.95 })
        .bindPopup(`<b>${esc(it.title)}</b><br>${esc(it.date)}`);
      mk.addTo(markers);
      markerById[it.id] = mk;
    }
  }

  // ---------------------------------------------------------------- 播放
  function stepDate(dir) {
    const dt = { ...state.date };
    if (dt.m && dt.d) { // 日级：前后一天（前公历简化处理）
      dt.d += dir;
      if (dt.d < 1) { dt.m -= 1; if (dt.m < 1) { dt.m = 12; dt.y = dt.y - 1 === 0 ? -1 : dt.y - 1; } dt.d = daysIn(dt.y, dt.m); }
      else if (dt.d > daysIn(dt.y, dt.m)) { dt.d = 1; dt.m += 1; if (dt.m > 12) { dt.m = 1; dt.y = dt.y + 1 === 0 ? 1 : dt.y + 1; } }
    } else {
      dt.y = fromAstro(toAstro(dt.y) + dir * playStep(dt.y));
    }
    dt.y = Math.max(Math.min(dt.y, NOW), -123000);
    return dt;
  }
  function togglePlay() {
    if (state.playing) { clearInterval(state.playing); state.playing = null; $("playBtn").textContent = "▶ 播放"; $("playBtn").classList.remove("playing"); return; }
    $("playBtn").textContent = "⏸ 暂停"; $("playBtn").classList.add("playing");
    let busy = false;
    state.playing = setInterval(async () => {
      if (busy) return; busy = true;
      const dt = stepDate(1);
      // 播放时只按年推进（清除月日），面板只在停止时刷新，避免请求过多
      if (!(state.date.m && state.date.d)) { dt.m = 0; dt.d = 0; }
      await setDate(dt, { refreshPanel: false });
      if (dt.y >= NOW) togglePlay();
      busy = false;
    }, parseInt($("speedIn").value, 10));
  }

  // ---------------------------------------------------------------- URL hash（可分享/截图）：#date=1789-07-14&name=France&tab=events
  function updateHash() {
    const p = new URLSearchParams({ date: dateParam(state.date) });
    const f = state.fid != null ? featByFid(state.snap, state.fid) : null;
    if (state.world) p.set("world", "1"); else if (f?.properties.NAME) p.set("name", f.properties.NAME);
    if (state.tab) p.set("tab", state.tab);
    p.set("layers", Object.keys(layerOn).filter((k) => layerOn[k]).join(","));
    if (layerOn.alliances && state.blocs?.length) p.set("blocs", state.blocs.join(","));
    if (layerOn.economy && state.econInd) p.set("ind", state.econInd);
    history.replaceState(null, "", "#" + p.toString());
  }

  // ---------------------------------------------------------------- 刻度与说明
  function drawTicks() {
    const marks = [-100000, -10000, -3000, -2000, -1000, 1, 500, 1000, 1500, 1800, 1900, 2000];
    $("ticks").innerHTML = marks.map((y) => `<span style="left:${yearToSlider(y) / 100}%">${y < 0 ? "前" + -y : y}</span>`).join("");
  }
  function renderAbout() {
    const m = state.meta;
    const snaps = m.snapshots.map((s) => yearZh(s.year)).join("、");
    $("aboutBody").innerHTML = `
      <p>本应用只使用公开的真实数据，不编造任何事件、人物或日期。</p>
      <h3>数据来源</h3><ul>${m.sources.map((s) => `<li><a href="${esc(s.url)}" target="_blank">${esc(s.name)}</a>（${esc(s.license)}）— ${esc(s.use)}</li>`).join("")}</ul>
      <h3>内容模块</h3><table><tr><th>模块</th><th>条目数</th><th>说明</th></tr>
      ${m.modules.map((x) => `<tr><td>${esc(x.title)}${x.kind === "layer" ? "（图层）" : ""}</td><td>${x.stats.records ?? "—"}</td><td>${esc(x.description)}</td></tr>`).join("")}</table>
      <h3>边界快照（共 ${m.snapshots.length} 张）</h3><p style="font-size:12.5px">${snaps}</p>
      <h3>精度与局限</h3><ul>
        <li>边界只在这些快照年份更新；所选日期使用不晚于它的最近一张快照。</li>
        <li>人物按<b>出生地坐标</b>是否落在所点击政权的多边形内来归属（没有坐标时按国籍名称）；人物后来可能在别处生活。</li>
        <li>事件按事件坐标（或事件地点的坐标）归属；只有国家信息的事件用该国首都坐标近似。</li>
        <li>日级精度只适用于 Wikidata 记录到日的事件；古代多数日期只到年或世纪。</li>
        <li>Wikidata 对欧洲、近现代的覆盖远多于其他地区和古代；“没有记录”不代表“没有发生”。</li>
      </ul>`;
  }

  // ---------------------------------------------------------------- 每日新闻自动更新状态
  async function pollStatus() {
    try {
      const s = await api("/api/live/status");
      $("updateStatus").textContent = s.last_day ? `每日新闻已更新至 ${s.last_day}` + (s.running ? "（更新中…）" : "") + (s.error ? "（上次更新失败，稍后重试）" : "") : "";
      $("updateStatus").title = `自动更新：${s.enabled ? `每 ${s.interval_minutes} 分钟` : "已关闭"}；上次检查：${s.last_check || "—"}`;
    } catch (e) { /* 忽略 */ }
    setTimeout(pollStatus, 60000);
  }

  // ---------------------------------------------------------------- 初始化
  async function init() {
    WHA.initialHash = new URLSearchParams(location.hash.slice(1));   // 启动时的 URL 参数（之后 URL 会随状态改写）
    WHA.updateHash = () => updateHash();
    WHA.updateLayers = () => updateLayers();
    state.meta = await api("/api/meta");
    zhNames = await api("/api/polity_names").catch(() => ({}));
    // 动态加载模块的自定义前端脚本（若有）
    const loaded = new Set();
    for (const m of state.meta.modules) if (m.frontend && !loaded.has(m.frontend) && loaded.add(m.frontend)) await new Promise((ok) => { const s = document.createElement("script"); s.src = m.frontend; s.onload = s.onerror = ok; document.head.appendChild(s); });
    drawTicks();
    renderAbout();
    buildLayerControl();
    pollStatus();
    const h = WHA.initialHash;
    const t = new Date();
    let dt = { y: t.getFullYear(), m: t.getMonth() + 1, d: t.getDate() };  // 默认：今天
    if (h.get("date")) { const mm = h.get("date").match(/^(-?\d+)(?:-(\d+))?(?:-(\d+))?$/); if (mm) dt = { y: +mm[1] || -1, m: +(mm[2] || 0), d: +(mm[3] || 0) }; }
    if (h.get("tab")) state.tab = h.get("tab");
    await setDate(dt);
    if (h.get("world")) { state.world = true; $("panel").classList.remove("hidden"); refreshPanelData(); }
    else if (h.get("name")) {
      // 同名区域可能有多块（如殖民地也叫 United Kingdom）：取范围最大的一块
      const ring = (r) => Math.abs(r.reduce((a, p, i) => { const q = r[(i + 1) % r.length]; return a + p[0] * q[1] - q[0] * p[1]; }, 0)) / 2;
      const area = (x) => { const g = x.geometry; const polys = g.type === "Polygon" ? [g.coordinates] : g.coordinates; return polys.reduce((a, pl) => a + ring(pl[0]), 0); };
      const f = geoCache[state.snap].features.filter((x) => x.properties.NAME === h.get("name")).sort((a, b) => area(b) - area(a))[0];
      if (f) { selectPolity(f.properties.fid); map.fitBounds(L.geoJSON(f).getBounds(), { maxZoom: 5, paddingBottomRight: [440, 0] }); }
    }

    // 可选：#...&person=Q…/office=Q…/bloc=Q… 直接打开详情窗口
    if (h.get("person") && WHA.showPerson) WHA.showPerson(h.get("person"));
    if (h.get("office") && WHA.showOffice) WHA.showOffice(h.get("office"));
    if (h.get("bloc") && WHA.showBloc) WHA.showBloc(h.get("bloc"));
    if (h.get("treaty") && WHA.showTreaty) WHA.showTreaty(h.get("treaty"));
    // 可选视图参数：#...&c=纬度,经度&z=缩放（便于分享/截图）
    if (h.get("c")) { const [la, lo] = h.get("c").split(",").map(Number); map.setView([la, lo], +(h.get("z") || 4)); }

    // 事件绑定
    $("slider").addEventListener("input", () => { $("dateLabel").textContent = yearZh(sliderToYear(+$("slider").value)); });
    $("slider").addEventListener("change", () => setDate({ y: sliderToYear(+$("slider").value), m: 0, d: 0 }));
    $("goBtn").onclick = () => setDate(readDateControls());
    $("yearIn").addEventListener("keydown", (e) => { if (e.key === "Enter") setDate(readDateControls()); });
    $("monthIn").onchange = () => { state.date = readDateControls(); fillDateControls(); setDate(readDateControls()); };
    $("dayIn").onchange = () => setDate(readDateControls());
    $("isBC").onchange = () => setDate(readDateControls());
    $("prevBtn").onclick = () => setDate(stepDate(-1));
    $("nextBtn").onclick = () => setDate(stepDate(1));
    $("playBtn").onclick = togglePlay;
    $("todayBtn").onclick = () => { const t = new Date(); setDate({ y: t.getFullYear(), m: t.getMonth() + 1, d: t.getDate() }); };
    $("worldBtn").onclick = () => { state.world = true; state.fid = null; restyle(); $("panel").classList.remove("hidden"); refreshPanelData(); updateHash(); };
    $("closePanel").onclick = closePanel;
    $("aboutBtn").onclick = () => $("about").classList.remove("hidden");
    $("detailClose").onclick = () => $("detail").classList.add("hidden");
    $("detail").onclick = (e) => { if (e.target.id === "detail") $("detail").classList.add("hidden"); };
    $("aboutClose").onclick = () => $("about").classList.add("hidden");
    $("about").onclick = (e) => { if (e.target.id === "about") $("about").classList.add("hidden"); };
  }
  init().catch((e) => { document.body.insertAdjacentHTML("afterbegin", `<div style="background:#c00;color:#fff;padding:8px">启动失败：${esc(e.message)}</div>`); });
})();
