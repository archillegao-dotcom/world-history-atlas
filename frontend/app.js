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
  // 注意：静态名称表只用于「从属于」等附注；多边形本身的名称以按日期解析的结果（snapNames）为准，
  // 解析不到当时存在的政权时显示底图原名并标为「文化/地区」，不套用后世政权名（例如史前不显示「古埃及」）
  // v0.6.1：只显示中文名（原名在面板副标题「底图名称」里小字显示）；没有中文名的标「暂无通用译名」
  const pname = (n) => (!n ? "未命名区域" : zhNames[n]?.zh ? zhNames[n].zh : /[\u4e00-\u9fff]/.test(n) ? n : `${n}（暂无通用译名）`);
  // 按快照解析的中文名（来自当时存在的 Wikidata 政权）优先；没有时退回静态名称表
  const snapNames = {};
  const pnameF = (p) => {
    const z = p && snapNames[state.snap]?.[String(p.fid)];
    if (!p?.NAME && !p?.NAME_ZH) return "未命名区域";
    if (z?.zh) return z.zh;   // 标题只用中文；底图原名（英文）放在下方说明行
    if (p.NAME_ZH && p.TERRITORY) return `${p.NAME_ZH}（${p.NAME}）`;
    const t = z?.title || p.NAME;   // 底图原名的中文译名（没有时为「原名（暂无通用译名）」）
    if (z?.kind === "split") return `${t}（已分裂为 ${z.parts.join("、")} 等；边界到下一张快照才更新）`;
    return `${t}（${z?.kind === "culture" ? "文化/地区" : "未对应到当时存在的政权"}）`;
  };
  const qidF = (p) => (p && snapNames[state.snap]?.[String(p.fid)]?.qid) || null;
  // v0.6.2：颜色按解析出的政权 QID（同一政权的 CShapes 主体、Stanford 按月多边形、底图补块同色，如 1940 年苏联不再两种颜色）；
  // 底图标明从属于别国的多边形（SUBJECTO 与 NAME 不同，如殖民地）仍用宗主国的颜色
  const colorKey = (p, n) => (p?.SUBJECTO && p.SUBJECTO !== p.NAME ? p.SUBJECTO : null) || qidF(p) || p?.SUBJECTO || n;
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
    map: null,   // 测试用：Playwright 通过 WHA.map 把经纬度换成屏幕坐标
    // 按坐标选中所在的政权多边形（城市标记、小国标记点击时用）
    selectAt: async (lat, lon) => {
      const r = await api(`/api/locate?date=${dateParam(state.date)}&lat=${lat}&lon=${lon}`).catch(() => null);
      if (r && r.polity && r.snapshot === state.snap) selectPolity(r.polity.fid);
    },
    openDetail: (html) => { $("detailBody").innerHTML = html; $("detail").classList.remove("hidden"); $("detailBody").scrollTop = 0; return $("detailBody"); },
  };
  const panelMods = () => state.meta.modules.filter((m) => (m.kind || "panel") === "panel");
  const layerMods = () => state.meta.modules.filter((m) => m.kind === "layer");

  // ---------------------------------------------------------------- 地图
  const phone0 = window.matchMedia("(max-width: 720px)").matches;
  // 打开时地图更大：桌面约看到欧洲到东亚，窄屏先给一块可读的区域。缩小和「全世界」仍在。日期变化不改这里的视角。
  const map = L.map("map", { worldCopyJump: true, minZoom: 2, maxZoom: 8, zoomSnap: 0.5, attributionControl: true })
    .setView(phone0 ? [36, 48] : [32, 55], phone0 ? 3 : 3.5);
  WHA.map = map;
  map.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>');
  map.attributionControl.addAttribution('边界：<a href="https://github.com/aourednik/historical-basemaps" target="_blank">historical-basemaps</a> (GPL-3.0) · 事件/人物：<a href="https://www.wikidata.org" target="_blank">Wikidata</a> (CC0)');
  if (!map.getPane("hillshade")) {
    const hp = map.createPane("hillshade");
    hp.style.zIndex = 405;
    hp.style.pointerEvents = "none";
    hp.classList.add("hillshade-pane");
  }
  // Natural Earth 1:50m Shaded Relief，公有领域。水面临时去掉，只把陆地起伏叠在政权颜色上。不是历史国界。
  L.imageOverlay("assets/ne50m_hillshade.png?v=2", [[-78, -180], [78, 180]], {
    pane: "hillshade", opacity: 0.92, interactive: false, className: "hillshade-img",
  }).addTo(map);
  let layer = null;
  const markers = L.layerGroup().addTo(map);
  const geoCache = {};

  const hue = (s) => { let h = 0; for (const c of s || "") h = (h * 31 + c.charCodeAt(0)) >>> 0; return h % 360; };
  const strategyOn = () => document.body.classList.contains("strategy");
  // 填色按「当日解析出的政权」（同一政权的多个多边形同色，如 1125 年后的辽朝故地与金朝控制区）；殖民地仍按宗主国
  const styleFor = (f, selected) => {
    const n = f.properties.NAME;
    const strat = strategyOn();
    const base = strat ? {
      color: selected ? "#e6d3a1" : "#12100e", weight: selected ? 2.4 : 1.75, opacity: 1,
      fillColor: n ? `hsl(${hue(colorKey(f.properties, n))}, 24%, ${selected ? 42 : 34}%)` : "#3c433c",
      fillOpacity: 0.97,
    } : {
      color: selected ? "#8a1c00" : "#6b5a48", weight: selected ? 2.5 : 0.6, opacity: 0.9,
      fillColor: n ? `hsl(${hue(colorKey(f.properties, n))}, 45%, ${selected ? 62 : 74}%)` : "#ddd6c8",
      fillOpacity: selected ? 0.85 : 0.75,
    };
    // 图层模块（如「阵营地图」）可以通过 WHA.setFillOverride(fn) 改写多边形填色
    let o = null;
    for (const fn of Object.values(fillOverrides)) { const x = fn(f); if (x) o = { ...(o || {}), ...x }; }
    const out = o ? { ...base, ...o, ...(selected ? { color: strat ? "#e6d3a1" : "#8a1c00", weight: strat ? 2.4 : 2.5 } : {}) } : base;
    if (strat && !selected) out.weight = Math.max(out.weight || 0, 1.75);
    // 近似多边形之间的空隙：灰色虚线，不套用政权色，避免看起来像已经核定的国界
    if (f.properties.TERR_CAT === "unverified") {
      return {
        color: selected ? (strat ? "#e6d3a1" : "#8a1c00") : "#3a342c",
        weight: selected ? 2.4 : (strat ? 1.5 : 1.1),
        dashArray: "4 3", opacity: 1,
        fillColor: strat ? "#7a7368" : "#d2c6b2",
        fillOpacity: strat ? 0.78 : 0.72,
      };
    }
    return out;
  };
  // 多个图层可同时改写填色：按注册顺序叠加（后注册的覆盖前面的同名样式）
  const fillOverrides = {};

  // 悬停满 5 秒才查经济。离开、换政权、拖动、缩放、改日期、关图层都取消计时和未返回的请求。
  const ECON_HOVER_MS = 5000;
  let hoverSeq = 0, hoverTimer = null, hoverFid = null, hoverAbort = null, hoverTouch = null;
  function hoverEnd() {
    hoverSeq++;
    hoverFid = null;
    hoverTouch = null;
    if (hoverTimer) { clearTimeout(hoverTimer); hoverTimer = null; }
    if (hoverAbort) { hoverAbort.abort(); hoverAbort = null; }
    const box = $("econHover");
    if (box) box.classList.remove("on");
  }
  function hoverBegin(feature, ev) {
    const fid = feature?.properties?.fid;
    if (fid == null) return;
    const oe = ev && (ev.originalEvent || ev);
    if (hoverFid === fid && hoverTimer) {
      if (oe && oe.pointerType && oe.pointerType !== "mouse") hoverTouch = hoverTouch || { x: oe.clientX, y: oe.clientY };
      return;
    }
    hoverEnd();
    hoverFid = fid;
    if (oe && oe.pointerType && oe.pointerType !== "mouse") hoverTouch = { x: oe.clientX, y: oe.clientY };
    const seq = hoverSeq;
    hoverTimer = setTimeout(() => {
      hoverTimer = null;
      if (seq !== hoverSeq) return;
      hoverFire(feature, ev, seq);
    }, ECON_HOVER_MS);
  }
  function fmtEcon(v, unit) {
    if (v == null || Number.isNaN(v)) return "暂无数据";
    const a = Math.abs(v);
    if (unit === "人") return a >= 1e8 ? (v / 1e8).toFixed(2) + " 亿人" : a >= 1e4 ? (v / 1e4).toFixed(a >= 1e6 ? 0 : 1) + " 万人" : Math.round(v) + " 人";
    if (unit === "美元" || unit === "国际元") {
      const u = unit === "美元" ? " 美元" : " 国际元";
      return a >= 1e12 ? (v / 1e12).toFixed(2) + " 万亿" + u : a >= 1e8 ? (v / 1e8).toFixed(1) + " 亿" + u : Math.round(v).toLocaleString("zh-CN") + u;
    }
    return String(Math.round(v * 10) / 10) + (unit ? " " + unit : "");
  }
  function placeHover(ev) {
    const oe = ev && (ev.originalEvent || ev);
    const box = $("econHover");
    if (!oe || !box || oe.clientX == null) return;
    const w = 340, h = box.offsetHeight || 150;
    let x = oe.clientX + 16, y = oe.clientY + 18;
    if (x + w > window.innerWidth - 8) x = Math.max(8, oe.clientX - w - 12);
    if (y + h > window.innerHeight - 8) y = Math.max(8, oe.clientY - h - 12);
    const ctl = $("layerCtl");
    if (ctl) {
      const r = ctl.getBoundingClientRect();
      if (x < r.right + 6 && x + w > r.left && y < r.bottom + 6 && y + h > r.top) y = Math.min(window.innerHeight - h - 8, r.bottom + 8);
    }
    const bar = $("topbar");
    if (bar) {
      const r = bar.getBoundingClientRect();
      if (y < r.bottom + 4) y = r.bottom + 6;
    }
    box.style.left = x + "px";
    box.style.top = y + "px";
  }
  function renderHover(feature, data) {
    const regime = esc(pnameF(feature.properties));
    const head = `<b>经济数字</b><div class="eh-year">地图上的政权：${regime}。下面不是这个政权自己的统计。</div>`;
    const foot = `<div class="eh-note">${esc(data.note || "来源只在这里写一次。只有数据表里正好有所选年份才给出全年数字。")}</div>`;
    if (!data.countries || !data.countries.length) {
      return head + `<div class="eh-empty">暂无数据</div>` + foot;
    }
    const blocks = data.countries.map((c) => {
      const share = c.share < 0.999 ? `，约占此区域 ${Math.round(c.share * 100)}%` : "";
      const title = `<div class="eh-cty">现代国家「${esc(c.name)}」范围的序列（${esc(c.iso)}）${share}</div>`;
      if (!c.values || !c.values.length) return title + `<div class="eh-empty">暂无数据</div>`;
      return title + c.values.map((v) => `<div class="eh-row">${esc(v.zh)}：${fmtEcon(v.v, v.unit)} · ${esc(String(v.year))} 年</div>`).join("");
    }).join("");
    return head + blocks + foot;
  }
  function hoverFire(feature, ev, seq) {
    const box = $("econHover");
    if (!box) return;
    placeHover(ev);
    box.innerHTML = `<b>${esc(pnameF(feature.properties))}</b><div class="eh-wait">正在查 ${esc(String(state.date.y))} 年的经济数字…</div>`;
    box.classList.add("on");
    const ac = new AbortController();
    hoverAbort = ac;
    const url = `/api/econ_hover?date=${encodeURIComponent(dateParam(state.date))}&snap=${encodeURIComponent(state.snap)}&fid=${feature.properties.fid}`;
    fetch(url, { signal: ac.signal }).then((r) => { if (!r.ok) throw new Error("http " + r.status); return r.json(); }).then((data) => {
      if (seq !== hoverSeq) return;
      box.innerHTML = renderHover(feature, data);
      placeHover(ev);
    }).catch((e) => {
      if (e.name === "AbortError" || seq !== hoverSeq) return;
      box.innerHTML = `<b>${esc(pnameF(feature.properties))}</b><div class="eh-empty">暂无数据</div>`;
    });
  }
  function hoverBeginAt(lat, lon, ev) {
    const key = `at:${Number(lat).toFixed(2)},${Number(lon).toFixed(2)}`;
    const oe = ev && (ev.originalEvent || ev);
    if (hoverFid === key && hoverTimer) return;
    hoverEnd();
    hoverFid = key;
    if (oe && oe.pointerType && oe.pointerType !== "mouse") hoverTouch = { x: oe.clientX, y: oe.clientY };
    const seq = hoverSeq;
    hoverTimer = setTimeout(() => {
      hoverTimer = null;
      if (seq !== hoverSeq) return;
      const box = $("econHover");
      if (!box) return;
      placeHover(ev);
      box.innerHTML = `<div class="eh-wait">正在查 ${esc(String(state.date.y))} 年的经济数字…</div>`;
      box.classList.add("on");
      const ac = new AbortController();
      hoverAbort = ac;
      fetch(`/api/locate?date=${encodeURIComponent(dateParam(state.date))}&lat=${lat}&lon=${lon}`, { signal: ac.signal })
        .then((r) => { if (!r.ok) throw new Error("http " + r.status); return r.json(); })
        .then((loc) => {
          if (seq !== hoverSeq) return null;
          const p = loc && loc.polity;
          if (!p || loc.snapshot !== state.snap) {
            box.innerHTML = `<div class="eh-empty">暂无数据</div>`;
            return null;
          }
          const f = featByFid(state.snap, p.fid) || { properties: p };
          return fetch(`/api/econ_hover?date=${encodeURIComponent(dateParam(state.date))}&snap=${encodeURIComponent(state.snap)}&fid=${p.fid}`, { signal: ac.signal })
            .then((r) => { if (!r.ok) throw new Error("http " + r.status); return r.json(); })
            .then((data) => ({ f, data }));
        })
        .then((got) => {
          if (!got || seq !== hoverSeq) return;
          box.innerHTML = renderHover(got.f, got.data);
          placeHover(ev);
        })
        .catch((e) => {
          if (e.name === "AbortError" || seq !== hoverSeq) return;
          box.innerHTML = `<div class="eh-empty">暂无数据</div>`;
        });
    }, ECON_HOVER_MS);
  }
  WHA.hoverBeginAt = hoverBeginAt;
  WHA.hoverEnd = hoverEnd;

  function bindHover(target, feature) {
    target.on("mouseover", (e) => hoverBegin(feature, e));
    target.on("mouseout", hoverEnd);
    target.on("pointerdown", (e) => {
      const t = e.originalEvent && e.originalEvent.pointerType;
      if (t && t !== "mouse") hoverBegin(feature, e);
    });
    target.on("pointerup pointercancel", (e) => {
      const t = e.originalEvent && e.originalEvent.pointerType;
      if (t && t !== "mouse") hoverEnd();
    });
  }

  let labelLayer = null, adminLayer = null, adminSeq = 0, adminTimer = null;
  // 地图上的短名都是核对过的叫法。括号里的地位说明可以略去，因为全名留在提示里。没有核对过的长名整段显示，不用省略号。
  const SHORT_NAME = {
    "法兰西共和国临时政府": "法国临时政府",
    "法兰西共和国临时政府/盟军控制区（法国）": "法国临时政府",
    "意大利王国/盟军控制区（意大利社会共和国）": "意王国/盟军",
    "英军托管下的利比亚": "利比亚（英管）",
    "苏军控制区（匈牙利）": "苏占匈牙利",
    "苏军收复区（原东方总督辖区）": "苏军收复区",
    "苏军与波兰民族解放委员会控制区（原波兰总督府）": "苏军·波兰",
    "南斯拉夫民族解放运动/苏军控制区（克罗地亚独立国）": "苏军·克罗地亚",
    "南斯拉夫民族解放运动/苏军控制区（塞尔维亚（德军军事管理区））": "苏军·塞尔维亚",
    "南斯拉夫民族解放运动/苏军控制区（黑山（意大利军政府））": "苏军·黑山",
    "第二次世界大战中的法属印度支那": "法属印度支那",
    "挪威（苏军解放的芬马克）": "芬马克（苏军）",
    "印度尼西亚日据时期": "印尼（日据）",
    "蒙疆联合自治政府": "蒙疆",
    "日军军事占领区（桂柳会战）": "桂柳（日军）",
    "空隙（未核实）（Unverified gap）": "空隙（未核实）",
  };
  function shortPolity(name) {
    const s = String(name || "");
    if (SHORT_NAME[s]) return SHORT_NAME[s];
    const m = s.match(/^([^（(]{2,8})[（(].*(殖民地|保护国|托管地|属地|占领区|解放区|军政府)/);
    if (m) return m[1];
    return s;
  }
  // 全名放不进范围时，去掉正式名称末尾的地位词。不是另造简称。全名仍在提示里。
  function tighterName(shown) {
    const s = String(shown || "");
    const prot = s.match(/^(.{2,14})保护国$/);
    if (prot) return prot[1];
    const king = s.match(/^(.{2,8})(王国|共和国)$/);
    if (king) return king[1];
    return s;
  }
  let labelProbe = null;
  function measureLabel(text) {
    if (!labelProbe) {
      const hold = document.createElement("div");
      hold.className = "leaflet-div-icon strategy-label label-probe";
      hold.style.cssText = "position:absolute;left:-9999px;top:0;visibility:hidden;pointer-events:none";
      labelProbe = document.createElement("span");
      hold.appendChild(labelProbe);
      document.body.appendChild(hold);
    }
    labelProbe.textContent = text;
    const r = labelProbe.getBoundingClientRect();
    return { w: Math.ceil(r.width), h: Math.ceil(r.height) };
  }
  function ringHas(lat, lng, ring) {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const yi = ring[i].lat, xi = ring[i].lng, yj = ring[j].lat, xj = ring[j].lng;
      if (Math.abs(xi - xj) > 80) continue;
      if ((yi > lat) !== (yj > lat)) {
        const x = xi + (xj - xi) * (lat - yi) / ((yj - yi) || 1e-12);
        if (lng < x) inside = !inside;
      }
    }
    return inside;
  }
  function polygonsOf(layer) {
    const ll = layer.getLatLngs?.();
    if (!ll || !ll.length) return [];
    if (typeof ll[0].lat === "number") return [{ outer: ll, holes: [] }];
    if (ll[0][0] && typeof ll[0][0].lat === "number") return [{ outer: ll[0], holes: ll.slice(1) }];
    return ll.filter((poly) => poly && poly[0] && poly[0][0] && typeof poly[0][0].lat === "number")
      .map((poly) => ({ outer: poly[0], holes: poly.slice(1) }));
  }
  function insidePoly(lat, lng, poly) {
    return ringHas(lat, lng, poly.outer) && !poly.holes.some((h) => h && h.length > 2 && ringHas(lat, lng, h));
  }
  // 名称候选点：当前画面里、多边形内部的几段，不用外接矩形中心。
  function interiorCandidates(outer, holes, view) {
    let minLat = 90, maxLat = -90, minLng = 180, maxLng = -180;
    for (const p of outer) {
      if (p.lat < minLat) minLat = p.lat;
      if (p.lat > maxLat) maxLat = p.lat;
      if (p.lng < minLng) minLng = p.lng;
      if (p.lng > maxLng) maxLng = p.lng;
    }
    const south = Math.max(minLat, view.getSouth()), north = Math.min(maxLat, view.getNorth());
    const west = Math.max(minLng, view.getWest()), east = Math.min(maxLng, view.getEast());
    if (!(south < north) || !(west < east)) return [];
    const out = [];
    const lines = 7;
    for (let i = 0; i < lines; i++) {
      const lat = south + (north - south) * (i + 0.5) / lines;
      const xs = [];
      for (let a = 0, b = outer.length - 1; a < outer.length; b = a++) {
        const y1 = outer[b].lat, y2 = outer[a].lat;
        if (Math.abs(outer[a].lng - outer[b].lng) > 80) continue;
        if ((y1 > lat) === (y2 > lat)) continue;
        xs.push(outer[b].lng + (outer[a].lng - outer[b].lng) * (lat - y1) / (y2 - y1));
      }
      xs.sort((p, q) => p - q);
      for (let k = 0; k + 1 < xs.length; k += 2) {
        const a0 = Math.max(xs[k], west), a1 = Math.min(xs[k + 1], east);
        const span = a1 - a0;
        if (span < 0.2) continue;
        for (const t of [0.35, 0.5, 0.65]) {
          const lng = a0 + (a1 - a0) * t;
          if (holes.some((h) => h && h.length > 2 && ringHas(lat, lng, h))) continue;
          out.push({ c: L.latLng(lat, lng), span });
        }
      }
    }
    out.sort((a, b) => b.span - a.span);
    return out.slice(0, 12);
  }
  function boxesOverlap(a, b) {
    return !(a[2] < b[0] || a[0] > b[2] || a[3] < b[1] || a[1] > b[3]);
  }
  function placeLabels() {
    if (!labelLayer) {
      if (!map.getPane("labels")) {
        const p = map.createPane("labels");
        p.style.zIndex = 620;
        p.style.pointerEvents = "none";
      }
      labelLayer = L.layerGroup().addTo(map);
    }
    labelLayer.clearLayers();
    if (!strategyOn() || !layer) return;
    const el = map.getContainer();
    const sz0 = map.getSize();
    if ((el.clientWidth !== sz0.x || el.clientHeight !== sz0.y) && !map._whaSizing) {
      map._whaSizing = true;
      map.invalidateSize({ pan: false, animate: false });
      map._whaSizing = false;
    }
    if (map._whaSizing) return;
    map._whaSizing = true;
    const z = map.getZoom();
    const view = map.getBounds();
    const sz = { x: el.clientWidth, y: el.clientHeight };
    const narrow = sz.x <= 720;
    const inset = { l: 8, r: 8, t: narrow ? 18 : 14, b: 10 };
    const items = [];
    layer.eachLayer((l) => {
      const b = l.getBounds?.();
      if (!b || !b.isValid() || !view.intersects(b)) return;
      const p = l.feature.properties;
      const polys = polygonsOf(l);
      let cands = [];
      let span = 0;
      if (p.LABEL_X != null && p.LABEL_Y != null) {
        const ll = L.latLng(p.LABEL_Y, p.LABEL_X);
        if (view.contains(ll) && polys.some((poly) => insidePoly(ll.lat, ll.lng, poly))) cands.push({ c: ll, span: 2 });
      }
      for (const poly of polys) {
        for (const hit of interiorCandidates(poly.outer, poly.holes, view)) {
          cands.push(hit);
          if (hit.span > span) span = hit.span;
        }
      }
      cands.sort((a, b) => b.span - a.span);
      cands = cands.slice(0, 16);
      if (!cands.length || span < 0.25) return;
      const cat = p.TERR_CAT || "";
      const tier = cat === "unverified" || cat.startsWith("zone_") ? 2 : (p.TERRITORY ? 1 : 0);
      items.push({ span, name: pnameF(p), zone: p.NAME_ZH || "", terr: !!p.TERRITORY, tier, polys, cands });
    });
    // 占领区若解析成宗主国国名，会和本土抢同一个标签，国名就会标到占领区上。这种区域改用自己的名称。
    const mains = new Set(items.filter((it) => !it.terr).map((it) => it.name));
    for (const it of items) {
      if (it.terr && it.zone && it.zone !== it.name && mains.has(it.name)) {
        it.title = `${it.zone}（${it.name}）`;
        it.name = it.zone;
      } else it.title = it.name;
    }
    items.sort((a, b) => a.tier - b.tier || b.span - a.span);
    const taken = [];
    const used = new Set();
    let extra = 0;
    const extraMax = z < 3.2 ? 6 : 14;
    const gap = 5;
    function boxOf(pt, dim) {
      return [pt.x - dim.w / 2, pt.y - dim.h / 2, pt.x + dim.w / 2, pt.y + dim.h / 2];
    }
    function inView(box) {
      return box[0] >= inset.l && box[1] >= inset.t && box[2] <= sz.x - inset.r && box[3] <= sz.y - inset.b;
    }
    function crowded(box) {
      const b = [box[0] - gap, box[1] - gap, box[2] + gap, box[3] + gap];
      return taken.some((q) => boxesOverlap(b, q));
    }
    function owns(it, ll) {
      return it.polys.some((poly) => insidePoly(ll.lat, ll.lng, poly));
    }
    function inOther(it, ll) {
      for (const other of items) {
        if (other !== it && owns(other, ll)) return true;
      }
      return false;
    }
    // 字心必须在本多边形里。两端可以落在海上，不能落进别国。
    function insideOwn(box, it) {
      const midY = (box[1] + box[3]) / 2;
      const lls = [[(box[0] + box[2]) / 2, midY], [box[0] + 2, midY], [box[2] - 2, midY]]
        .map(([x, y]) => map.containerPointToLatLng(L.point(x, y)));
      if (!owns(it, lls[0])) return false;
      return lls.every((ll) => owns(it, ll) || !inOther(it, ll));
    }
    function bestFit(it, shown) {
      const dim = measureLabel(shown);
      if (dim.w < 8 || dim.h < 8) return null;
      const minX = inset.l + dim.w / 2, maxX = sz.x - inset.r - dim.w / 2;
      const minY = inset.t + dim.h / 2, maxY = sz.y - inset.b - dim.h / 2;
      if (minX > maxX || minY > maxY) return null;
      let best = null;
      for (const cand of it.cands) {
        const raw = map.latLngToContainerPoint(cand.c);
        const pt = L.point(Math.max(minX, Math.min(maxX, raw.x)), Math.max(minY, Math.min(maxY, raw.y)));
        const box = boxOf(pt, dim);
        if (!inView(box) || crowded(box) || !insideOwn(box, it)) continue;
        const edge = Math.min(box[0] - inset.l, sz.x - inset.r - box[2], box[1] - inset.t, sz.y - inset.b - box[3]);
        const score = edge * 3 + cand.span;
        if (!best || score > best.score) best = { pt, box, score };
      }
      return best;
    }
    for (const it of items) {
      if (used.has(it.name)) continue;
      if (it.name === "未命名区域") continue;
      if (it.tier > 0 && extra >= extraMax) continue;
      const preferred = shortPolity(it.name);
      const names = [preferred];
      const tight = tighterName(preferred);
      if (tight !== preferred) names.push(tight);
      let placed = null, shown = preferred;
      for (const name of names) {
        const fit = bestFit(it, name);
        if (fit) { placed = fit; shown = name; break; }
      }
      if (!placed) continue;
      if (it.tier > 0) extra++;
      taken.push(placed.box);
      used.add(it.name);
      const at = map.containerPointToLatLng(placed.pt);
      const icon = L.divIcon({
        className: "polity-label strategy-label", iconSize: null, iconAnchor: [0, 0],
        html: `<span data-lat="${at.lat.toFixed(3)}" data-lng="${at.lng.toFixed(3)}" title="${esc(it.title || it.name)}">${esc(shown)}</span>`,
      });
      L.marker(map.containerPointToLatLng(placed.pt), { icon, pane: "labels", interactive: false, keyboard: false }).addTo(labelLayer);
    }
    WHA.polityLabelBoxes = taken;
    map._whaSizing = false;
  }
  WHA.placePolityLabels = placeLabels;
  function scheduleAdmin1() { clearTimeout(adminTimer); adminTimer = setTimeout(loadAdmin1, 240); }
  async function loadAdmin1() {
    if (!adminLayer) {
      if (!map.getPane("admin1")) {
        const p = map.createPane("admin1");
        p.style.zIndex = 430;
        p.style.pointerEvents = "none";
      }
      adminLayer = L.geoJSON(null, {
        pane: "admin1", interactive: false,
        style: { color: "#c9bfae", weight: 0.65, opacity: 0.42, fill: false },
      }).addTo(map);
    }
    if (!strategyOn() || map.getZoom() < 5) { adminLayer.clearLayers(); return; }
    const b = map.getBounds();
    const seq = ++adminSeq;
    const url = `/api/admin1_ref?west=${b.getWest()}&south=${b.getSouth()}&east=${b.getEast()}&north=${b.getNorth()}&zoom=${map.getZoom()}`;
    const gj = await api(url).catch(() => null);
    if (seq !== adminSeq || !strategyOn() || map.getZoom() < 5) return;
    adminLayer.clearLayers();
    if (gj && gj.features) adminLayer.addData(gj);
  }
  map.on("movestart zoomstart", hoverEnd);
  map.getContainer().addEventListener("pointermove", (e) => {
    if (!hoverTouch || !hoverTimer || e.pointerType === "mouse") return;
    if (Math.hypot(e.clientX - hoverTouch.x, e.clientY - hoverTouch.y) > 12) hoverEnd();
  });
  function syncTiny() {
    const pane = map.getPane("tiny");
    if (pane) pane.style.display = (!strategyOn() || map.getZoom() >= 5) ? "" : "none";
  }
  map.on("moveend zoomend", () => { placeLabels(); scheduleAdmin1(); syncTiny(); });

  let tinyLayer = null;
  // 快速连续换日期时，较早发出的请求可能后返回：只画最后一次请求的快照，否则旧快照的多边形会盖在地图上、点击选中错误的政权
  let snapSeq = 0;
  async function loadSnapshot(snap) {
    hoverEnd();
    const my = ++snapSeq;
    if (!geoCache[snap]) geoCache[snap] = await api(`/api/basemap/${snap}`);
    await loadNames(snap);
    if (my !== snapSeq) return false;
    const gj = geoCache[snap];
    if (layer) map.removeLayer(layer);
    layer = L.geoJSON(gj, {
      style: (f) => styleFor(f, state.fid === f.properties.fid && !state.world),
      onEachFeature: (f, l) => {
        const p = f.properties;
        l.bindTooltip(() => esc(pnameF(p)) + (p.SUBJECTO && p.SUBJECTO !== p.NAME ? `<br><small>从属于：${esc(pnameN(p.SUBJECTO))}</small>` : "") +
          Object.values(WHA.tooltipExtra).map((fn) => fn(p) || "").join(""), { sticky: true });
        // 点到没有对应政权的底图多边形（文化/地区）时，按坐标解析：小岛的底图多边形可能压在殖民地分区之上（如 1950 年圣基茨属英属背风群岛）
        bindHover(l, f);
        l.on("click", async (e) => {
          if (snapNames[state.snap]?.[String(p.fid)]?.qid) return selectPolity(p.fid);
          const r = await api(`/api/locate?date=${dateParam(state.date)}&lat=${e.latlng.lat}&lon=${e.latlng.lng}`).catch(() => null);
          selectPolity(r && r.polity && r.snapshot === state.snap ? r.polity.fid : p.fid);
        });
      },
    }).addTo(map);
    layer._whaSnap = snap;
    // 整组放到其他图层下面。FeatureGroup.bringToBack() 会逐个移到最底层，把要素顺序整个颠倒，
    // 使先画的大国多边形盖住后加的实际控制区/领地多边形（如 1944 年桂林点到中华民国）：倒序逐个移动以保持原顺序。
    const ls = layer.getLayers();
    for (let i = ls.length - 1; i >= 0; i--) if (ls[i].bringToBack) ls[i].bringToBack();
    // 微型国家/小岛：多边形在世界尺度下只有几个像素，另加最小尺寸的可点击圆点（与多边形同一选中逻辑）
    if (tinyLayer) map.removeLayer(tinyLayer);
    tinyLayer = L.layerGroup();
    // 圆点放在单独的图层面板（z-index 650，高于城市点 600 与控制区标签），世界尺度下点击优先选中微型国家（梵蒂冈不再点到意大利/罗马城点，澳门不再点到香港）；
    // 面积小的后画（在上面）
    if (!map.getPane("tiny")) map.createPane("tiny").style.zIndex = 650;
    const tinyList = [];
    layer.eachLayer((l) => {
      const b = l.getBounds?.();
      if (!b || !b.isValid()) return;
      const p = l.feature.properties;
      if (b.getEast() - b.getWest() > 1.2 || b.getNorth() - b.getSouth() > 1.2) return;
      const c = p.LABEL_X != null ? [p.LABEL_Y, p.LABEL_X] : b.getCenter();
      const mk = L.circleMarker(c, { pane: "tiny", radius: strategyOn() ? 6 : 5, weight: 1.5, color: "#555", fillColor: styleFor(l.feature, false).fillColor || "#ddd", fillOpacity: 0.9, className: "tiny-polity" });
      mk.bindTooltip(() => esc(pnameF(p)), { sticky: true });
      bindHover(mk, l.feature);
      // 按坐标解析（与点地图同一路径）：小岛的底图多边形可能被实际控制区/殖民地分区覆盖（如 1950 年多米尼克属英属向风群岛）
      mk.on("click", async (e) => {
        L.DomEvent.stopPropagation(e);
        const ll = mk.getLatLng();
        const r = await api(`/api/locate?date=${dateParam(state.date)}&lat=${ll.lat}&lon=${ll.lng}`).catch(() => null);
        selectPolity(r && r.polity && r.snapshot === state.snap ? r.polity.fid : p.fid);
      });
      mk.feature = l.feature;
      tinyList.push([(b.getEast() - b.getWest()) * (b.getNorth() - b.getSouth()), mk]);
    });
    tinyList.sort((a, b) => b[0] - a[0]).forEach(([, mk]) => tinyLayer.addLayer(mk));
    tinyLayer.addTo(map);
    syncTiny();
    placeLabels();
    scheduleAdmin1();
  }

  // 多边形名称按所选日期解析（同一张快照内朝代/政权也会变化，如 900 年快照内唐→后梁）
  let namesKey = null;
  async function loadNames(snap) {
    const key = `${snap}|${state.date.y}|${state.date.m}`;
    if (key === namesKey) return;
    namesKey = key;
    snapNames[snap] = await api(`/api/snapshot_names/${snap}?date=${dateParam(state.date)}`).catch(() => ({}));
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

  let dateSeq = 0;
  async function setDate(dt, { refreshPanel = true } = {}) {
    hoverEnd();
    const mySeq = ++dateSeq;
    state.date = dt;
    fillDateControls();
    const s = await api(`/api/snapshot?date=${dateParam(dt)}`);
    if (mySeq !== dateSeq) return;   // 已经换成更新的日期
    if (s.snapshot !== state.snap || !layer || layer._whaSnap !== s.snapshot) {
      // 换快照后原来的政权 fid 不再有效：用政权名称在新快照中找同名政权，找不到就关闭面板
      const oldName = state.fid != null && geoCache[state.snap] ? featByFid(state.snap, state.fid)?.properties.NAME : null;
      state.snap = s.snapshot;
      state.base = s.base;
      state.next = s.next;
      await loadSnapshot(s.snapshot);
      if (mySeq !== dateSeq) return;
      if (oldName) {
        const f = geoCache[state.snap].features.find((x) => x.properties.NAME === oldName);
        state.fid = f ? f.properties.fid : null;
        if (!f && !state.world) closePanel();
        restyle();
      }
    }
    state.next = s.next;
    state.base = s.base;
    state.transitions = s.transitions || [];
    await loadNames(state.snap);
    restyle();   // 同一快照内政权可能随日期变化（填色按解析出的政权）
    updateEraNote();
    updateHash();
    if (refreshPanel && (state.fid != null || state.world)) refreshPanelData();
    scheduleLayers();
  }

  // ---------------------------------------------------------------- 地图图层（模块）
  let layerTimer = null, layerSeq = 0;
  // 自动打开的图层：俄乌战争前线在 2014-02-20 以后、乌克兰在视野内时自动显示（用户手动关过则不再自动打开）
  const AUTO_LAYERS = [{ id: "war_fronts", from: [2014, 2, 20], bbox: [22.0, 44.0, 40.5, 52.5] }];
  const layerUser = {};
  function autoLayers() {
    if (!map) return;
    const b = map.getBounds();
    for (const a of AUTO_LAYERS) {
      if (layerUser[a.id] || !layers[a.id]) continue;
      const d = state.date, k = d.y * 10000 + (d.m || 7) * 100 + (d.d || 1), k0 = a.from[0] * 10000 + a.from[1] * 100 + a.from[2];
      const inView = b.getWest() < a.bbox[2] && b.getEast() > a.bbox[0] && b.getSouth() < a.bbox[3] && b.getNorth() > a.bbox[1];
      const want = k >= k0 && inView;
      if (want !== !!layerOn[a.id]) {
        layerOn[a.id] = want;
        const el = document.querySelector(`#layerCtl input[data-id="${a.id}"]`);
        if (el) el.checked = want;
        if (!want) layers[a.id].clear();
      }
    }
  }
  function scheduleLayers() { autoLayers(); clearTimeout(layerTimer); layerTimer = setTimeout(updateLayers, state.playing ? 50 : 200); }
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
    box.classList.add("collapsed");
    box.innerHTML = `<button type="button" id="layerToggle" aria-expanded="false">图层</button><div class="layer-body">` + layerMods().map((m) => `<label title="${esc(m.description)}"><input type="checkbox" data-id="${m.id}" ${layerOn[m.id] ? "checked" : ""}> ${esc(m.title)}</label>`).join("") + `</div>`;
    box.querySelector("#layerToggle").addEventListener("click", () => {
      const closed = box.classList.toggle("collapsed");
      box.querySelector("#layerToggle").setAttribute("aria-expanded", closed ? "false" : "true");
    });
    box.querySelectorAll("input").forEach((el) => el.addEventListener("change", () => { hoverEnd(); layerOn[el.dataset.id] = el.checked; layerUser[el.dataset.id] = true; updateLayers(); updateHash(); }));
    if (want != null) for (const m of layerMods()) layerUser[m.id] = true;   // URL 指定了图层：不自动开关
    map.on("moveend", () => { const before = JSON.stringify(layerOn); autoLayers(); if (JSON.stringify(layerOn) !== before) updateLayers(); });
  }

  const featByFid = (snap, fid) => geoCache[snap]?.features.find((f) => f.properties.fid === fid);

  function updateEraNote() {
    const y = state.date.y;
    const base = state.base ?? state.snap;
    const snapMeta = state.meta.snapshots.find((x) => x.year === base) || {};
    const nxt = state.next != null ? `，下一张：${yearZh(state.next)}` : "";
    let html = snapMeta.label && snapMeta.label.startsWith("现代")
      ? `<b>边界：${esc(snapMeta.label)}</b>，用于 2011 年至今（边界变化以 Natural Earth 版本为准，争议地区按其“事实控制”画法）。`
      : `<b>边界快照：${yearZh(base)}</b>${nxt}。地图显示不晚于所选日期的最近一张快照` +
        (state.transitions?.length ? `，并按真实日期叠加了 ${state.transitions.length} 项过渡修正（<a href="#" id="transList">查看</a>）。` : "；两张快照之间没有记录到的变化不会显示。");
    if (y < -3000) html = `<b>史前时期（文字出现以前）</b>：地图上是 historical-basemaps 对考古文化与人群分布的粗略复原，不是国家边界（名称标为「文化/地区」）；快照非常稀疏（当前：${yearZh(base)}${state.next != null ? "，下一张：" + yearZh(state.next) : ""}）。Wikidata 中此时期几乎没有精确到年的事件和人物。`;
    else if (y < -500) html += "<br>上古时期：许多日期是估计值，人物生卒年常常只精确到世纪。";
    if (state.date.m && state.date.d) html += "<br>已精确到日：事件列表会把<b>当天</b>发生的事件排在最前（仅限 Wikidata 记录到日的事件）。";
    if (strategyOn()) html += "<br>策略地图是自绘的深色分区。国名写在该日可见范围里面，全名在提示里。放大后的浅线是现代一级行政区参考线，不是历史省界。淡色起伏是 Natural Earth 晕渲（公有领域），只表示现代自然地形，不是历史国界。不是 TNO 官方地图。";
    const note = $("eraNote");
    const open = note.classList.contains("open");
    note.innerHTML = `<button type="button" id="eraToggle" aria-expanded="${open ? "true" : "false"}">${open ? "收起说明" : "边界说明"}</button>` + (open ? `<div class="era-body">${html}</div>` : "");
    $("eraToggle").onclick = () => { note.classList.toggle("open"); updateEraNote(); };
    const tl = $("transList");
    if (tl) tl.onclick = (e) => { e.preventDefault(); WHA.openDetail("边界过渡修正", `<ul>${state.transitions.map((t) => `<li>${esc(t)}</li>`).join("")}</ul><p class="note">修正规则：Wikidata 中精确到月/日的成立（P571）与解散（P576）日期落在两张快照之间时，从该日期起用下一张快照中对应的范围；特殊地位领土用 Natural Earth 1:10m 范围。</p>`); };
  }

  // ---------------------------------------------------------------- 侧边栏
  function restyle() {
    if (layer) layer.eachLayer((l) => l.setStyle && l.setStyle(styleFor(l.feature, state.fid === l.feature.properties.fid && !state.world)));
    if (tinyLayer) tinyLayer.eachLayer((m) => {
      const sel = state.fid === m.feature.properties.fid && !state.world;
      m.setStyle({ fillColor: styleFor(m.feature, false).fillColor || "#ddd", color: sel ? (strategyOn() ? "#e6d3a1" : "#8a1c00") : (strategyOn() ? "#f4efe6" : "#555"), weight: sel ? 2.5 : 1.5 });
      m.setRadius(strategyOn() ? 5 : 5);
    });
    syncTiny();
    placeLabels();
  }
  function applyStrategy(on) {
    document.body.classList.toggle("strategy", !!on);
    const btn = $("styleBtn");
    if (btn) { btn.textContent = on ? "普通地图" : "策略地图"; btn.setAttribute("aria-pressed", on ? "true" : "false"); }
    if (on && !map._whaStratAttr) map._whaStratAttr = map.attributionControl.addAttribution('策略地图为软件自绘。细线：<a href="https://www.naturalearthdata.com/" target="_blank">Natural Earth</a> 现代一级行政区参考线（公有领域），不是历史省界。地形：同一来源的 1:50m 晕渲（公有领域），只表示现代自然起伏');
    restyle();
    updateEraNote();
    if (WHA.updateLayers) WHA.updateLayers();
    scheduleAdmin1();
  }
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
      `${dateZh(state.date)} · 边界快照 ${yearZh(state.base ?? state.snap)}${String(state.snap).includes("@") ? "（含过渡修正）" : ""}` +
      (p?.NAME && (snapNames[state.snap]?.[String(p.fid)]?.zh || snapNames[state.snap]?.[String(p.fid)]?.title) ? ` · <span class="basename" title="边界数据中该多边形的原名">底图名称：${esc(p.NAME)}</span>` : "") +
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
      // 标题用所选日期解析到的 Wikidata 政权中文名（比按快照年份的名称更准确，如 1948 年 6 月的「中华民国」）；
      // 政权模块一返回就更新，不等其他模块（事件、人物等可能要几秒）
      const rs = m.id === "regime" ? results.regime?.state : null;
      if (seq === reqSeq && rs && p && rs.name) $("polityName").textContent = rs.name;
    }));
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
        <li>策略地图只改画法。放大后的细线是现代一级行政区参考线（Natural Earth，公有领域），不是历史省界。历史省界没有绘制。淡色起伏是同一来源的 1:50m 晕渲，只表示现代陆地地形，没有海底深浅。</li>
        <li>鼠标停在一个政权上满 5 秒，才显示该年经济数字。只有数据表里正好有这一年才给出数值，否则为「暂无数据」。</li>
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
    if (h.get("style") === "strategy") applyStrategy(true);

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
    $("styleBtn").onclick = () => applyStrategy(!strategyOn());
    $("mapKeyBtn").onclick = () => {
      const on = $("mapKey").classList.toggle("open");
      $("mapKeyBtn").setAttribute("aria-expanded", on ? "true" : "false");
      $("mapKeyBtn").textContent = on ? "收起图例" : "图例";
    };
    $("detailClose").onclick = () => $("detail").classList.add("hidden");
    $("detail").onclick = (e) => { if (e.target.id === "detail") $("detail").classList.add("hidden"); };
    $("aboutClose").onclick = () => $("about").classList.add("hidden");
    $("about").onclick = (e) => { if (e.target.id === "about") $("about").classList.add("hidden"); };
  }
  init().catch((e) => { document.body.insertAdjacentHTML("afterbegin", `<div style="background:#c00;color:#fff;padding:8px">启动失败：${esc(e.message)}</div>`); });
})();
