/*
 * 「经济与资源」：
 *   - 图层 economy：按现代国界（Natural Earth）分级设色，指标可选（Maddison 2023 / 世界银行 WDI）。
 *     历史边界的填色暂时变透明，只保留边界线（仍可点击），以免把现代国家的数值误读成当时政权的数值。
 *   - 图层 resources：矿山 / 油田 / 天然气田点位（Wikidata）。
 *   - 面板 econ（民生经济）：重叠的现代国家、指标表（来源 + 数值年份 + 插值标注）与趋势小图。
 */
(function () {
  const { esc } = WHA;
  const PAL = ["#fff5d6", "#fde2a5", "#fbc373", "#f59d4a", "#e46f34", "#c4442a", "#8f2421"];
  const NODATA = "#d9d6cf";

  // ---------------------------------------------------------------- 数字格式
  function fmt(v, unit) {
    if (v == null) return "无数据";
    const a = Math.abs(v);
    if (unit === "人") return a >= 1e8 ? (v / 1e8).toFixed(2) + " 亿人" : a >= 1e4 ? (v / 1e4).toFixed(a >= 1e6 ? 0 : 1) + " 万人" : Math.round(v) + " 人";
    if (unit === "美元" || unit === "国际元") {
      const u = unit === "美元" ? " 美元" : " 国际元";
      return a >= 1e12 ? (v / 1e12).toFixed(2) + " 万亿" + u : a >= 1e8 ? (v / 1e8).toFixed(1) + " 亿" + u : Math.round(v).toLocaleString("zh-CN") + u;
    }
    if (unit === "%") return v.toFixed(1) + "%";
    if (unit === "岁") return v.toFixed(1) + " 岁";
    return String(Math.round(v * 10) / 10);
  }
  const note = (r) => r.interp ? `<span class="badge country" title="两数据点之间线性插值">插值（${r.interp[0]}–${r.interp[1]}年之间）</span>`
    : r.carried ? `<span class="badge country" title="所选年份没有数据，沿用最近一年">最近数据：${r.year}年</span>` : `${r.year}年`;

  // ---------------------------------------------------------------- 经济分级图层
  let ne = null, econLayer = null, legend = null, last = null, mapRef = null;
  const ind = () => WHA.state.econInd || WHA.initialHash.get("ind") || "mpd_gdppc";
  const classOf = (v, br) => { let i = 0; while (i < br.length && v >= br[i]) i++; return i; };

  WHA.registerLayer("economy", {
    query: () => `&ind=${encodeURIComponent(ind())}`,
    init(map) {
      mapRef = map;
      map.createPane("econ").style.zIndex = 350;   // 在历史边界（overlayPane 400）之下
      const Ctl = L.Control.extend({ onAdd() { legend = L.DomUtil.create("div", "alliance-legend econ-legend hidden"); L.DomEvent.disableClickPropagation(legend); L.DomEvent.disableScrollPropagation(legend); return legend; } });
      new Ctl({ position: "topleft" }).addTo(map);
    },
    async update(res) {
      last = res;
      WHA.state.econInd = res.indicator;
      if (!ne) ne = await WHA.api("/api/basemap/2011");
      const style = (f) => {
        const iso = res.ne_iso[String(f.properties.fid)];
        const r = iso && res.values[iso];
        return { pane: "econ", stroke: true, color: "#999", weight: r && (r.interp || r.carried || r.agg) ? 1 : 0.3, dashArray: r && (r.interp || r.carried || r.agg) ? "3 3" : null,
                 fillColor: r ? PAL[classOf(r.v, res.breaks)] : NODATA, fillOpacity: 0.9 };
      };
      if (!econLayer) econLayer = L.geoJSON(ne, { pane: "econ", interactive: false, style }).addTo(mapRef);
      else { if (!mapRef.hasLayer(econLayer)) econLayer.addTo(mapRef); econLayer.setStyle(style); }
      // 历史边界：透明填充 + 深色细线
      WHA.setFillOverride(() => ({ fillOpacity: 0.01, color: "#3b3027", weight: 0.9 }), "economy");
      WHA.tooltipExtra.economy = (p) => {
        const ov = (res.overlap[String(p.fid)] || [])[0];
        if (!ov) return "";
        const r = res.values[ov[0]];
        return `<br><small>${esc(res.meta.zh)}：${r ? fmt(r.v, res.meta.unit) : "无数据"}（现代国家 ${esc(res.names[ov[0]] || ov[0])}${ov[1] < 0.99 ? `，占此区域 ${Math.round(ov[1] * 100)}%` : ""}${r?.interp ? "，插值" : r?.carried ? `，${r.year}年数据` : ""}）</small>`;
      };
      const br = res.breaks, u = res.meta.unit;
      const nInterp = Object.values(res.values).filter((r) => r.interp || r.carried || r.agg).length;
      legend.innerHTML = `<b>经济</b> <small>${WHA.state.date.y < 0 ? "公元前" + -WHA.state.date.y : WHA.state.date.y}年</small>
        <div><select class="econsel">${res.indicators.map((x) => `<option value="${esc(x.id)}" ${x.id === res.indicator ? "selected" : ""}>${esc(x.zh)}</option>`).join("")}</select></div>
        <div class="note"><b>按现代国界统计</b>：历史时期的数值是「今天这个国家范围内」的估计，不是当时政权的数值。虚线边框 = 插值或沿用最近数据（${nInterp} 国）。</div>
        ${res.total ? PAL.map((c, i) => `<div><span class="sw" style="background:${c}"></span>${i === 0 ? "&lt; " + fmt(br[0], u) : i === PAL.length - 1 ? "≥ " + fmt(br[i - 1], u) : fmt(br[i - 1], u) + " – " + fmt(br[i], u)}</div>`).join("") : ""}
        <div><span class="sw" style="background:${NODATA}"></span>无数据（${res.total} 国有数据）</div>
        <div class="note">来源：<a href="${esc(res.source.url)}" target="_blank" rel="noopener">${esc(res.source.label)}</a></div>`;
      legend.classList.remove("hidden");
      legend.querySelector(".econsel").onchange = (e) => { WHA.state.econInd = e.target.value; WHA.updateLayers(); WHA.updateHash(); };
    },
    clear() {
      if (econLayer && mapRef) mapRef.removeLayer(econLayer);
      if (legend) legend.classList.add("hidden");
      delete WHA.tooltipExtra.economy;
      WHA.setFillOverride(null, "economy");
    },
  });

  // ---------------------------------------------------------------- 资源点图层
  const KCOL = { mine: "#6b4f2a", oil: "#111111", gas: "#2b6cb0" };
  let resGroup = null, resLegend = null;
  WHA.registerLayer("resources", {
    init(map) {
      mapRef = mapRef || map;
      resGroup = L.layerGroup();
      const Ctl = L.Control.extend({ onAdd() { resLegend = L.DomUtil.create("div", "alliance-legend hidden"); return resLegend; } });
      new Ctl({ position: "bottomright" }).addTo(map);
    },
    update(res) {
      resGroup.clearLayers();
      const rend = L.canvas({ padding: 0.3 });
      const cnt = { mine: 0, oil: 0, gas: 0 };
      for (const r of res.items) {
        cnt[r.k]++;
        const links = [`<a href="https://www.wikidata.org/wiki/${r.id}" target="_blank">Wikidata</a>`];
        if (r.zw) links.push(`<a href="https://zh.wikipedia.org/wiki/${encodeURIComponent(r.zw)}" target="_blank">中文维基</a>`);
        if (r.ew) links.push(`<a href="https://en.wikipedia.org/wiki/${encodeURIComponent(r.ew.replace(/ /g, "_"))}" target="_blank">English Wikipedia</a>`);
        L.circleMarker([r.c[1], r.c[0]], { renderer: rend, radius: r.k === "mine" ? 3.5 : 4.5, color: "#fff", weight: 0.8, fillColor: KCOL[r.k], fillOpacity: 0.9 })
          .bindPopup(`<b>${esc(r.n || r.id)}</b><br>${esc(res.kinds[r.k])}${r.p.length ? "：" + r.p.map(esc).join("、") : ""}<br>
            ${r.f ? `开始：${esc(r.f)}` : "开采时间未记录"}${r.t ? ` · 关闭：${esc(r.t)}` : ""}<br>${links.join(" · ")}<br><small>来源：Wikidata</small>`)
          .addTo(resGroup);
      }
      if (!mapRef.hasLayer(resGroup)) resGroup.addTo(mapRef);
      resLegend.innerHTML = `<b>资源</b>（Wikidata，${res.total} 处）<br>` + Object.entries(res.kinds).map(([k, z]) => `<span class="sw" style="background:${KCOL[k]};border-radius:50%"></span>${esc(z)} ${cnt[k]}`).join("<br>") + `<div class="note">${esc(res.note)}</div>`;
      resLegend.classList.remove("hidden");
    },
    clear() { if (resGroup && mapRef) mapRef.removeLayer(resGroup); if (resLegend) resLegend.classList.add("hidden"); },
  });

  // ---------------------------------------------------------------- 趋势小图（SVG 折线，标出所选年份）
  function chart(series, year, title, unit) {
    const pts = (series || []).filter((p) => p[1] != null);
    if (pts.length < 2) return "";
    const W = 360, H = 90, P = 4;
    const x0 = pts[0][0], x1 = Math.max(pts[pts.length - 1][0], year);
    const ys = pts.map((p) => p[1]); const y0 = Math.min(...ys), y1 = Math.max(...ys);
    const sx = (x) => P + ((x - x0) / (x1 - x0 || 1)) * (W - 2 * P), sy = (y) => H - P - ((y - y0) / (y1 - y0 || 1)) * (H - 2 * P);
    // 相邻数据点相隔 > 100 年时断开折线（不在大间隔上画出假想的连续变化）
    let d = "";
    pts.forEach((p, i) => { d += (i === 0 || p[0] - pts[i - 1][0] > 100 ? "M" : "L") + sx(p[0]).toFixed(1) + "," + sy(p[1]).toFixed(1); });
    const dots = pts.length < 40 ? pts.map((p) => `<circle cx="${sx(p[0]).toFixed(1)}" cy="${sy(p[1]).toFixed(1)}" r="1.8" fill="#8a1c00"/>`).join("") : "";
    const inRange = year >= x0 && year <= x1;
    return `<div class="chart"><div class="ct">${esc(title)}：${fmt(y0, unit)} – ${fmt(y1, unit)}（${x0}–${pts[pts.length - 1][0]}年）</div>
      <svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}"><rect x="0" y="0" width="${W}" height="${H}" fill="#faf6ee"/>
      ${inRange ? `<line x1="${sx(year)}" x2="${sx(year)}" y1="0" y2="${H}" stroke="#c4442a" stroke-dasharray="3 2"/>` : ""}
      <path d="${d}" fill="none" stroke="#8a1c00" stroke-width="1.5"/>${dots}</svg></div>`;
  }

  WHA.registerRenderer("econ", (r, m) => {
    const box = document.createElement("div");
    box.className = "mod-state";
    let h = `<div class="note">${r.note.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")}</div>`;
    if (!r.countries?.length) h += `<div class="empty">这个区域没有与之重叠的现代国家数据。</div>`;
    for (const c of r.countries || []) {
      h += `<h4>${esc(c.name)}${c.share != null ? ` <small>（占此区域面积 ${Math.round(c.share * 100)}%）</small>` : ""}</h4>`;
      const rows = c.rows.filter((x) => x.v != null);
      h += rows.length ? `<table class="kv">${rows.map((x) => `<tr><th style="width:auto">${esc(x.zh)}</th><td><b>${fmt(x.v, x.unit)}</b>${x.agg ? ` <span class="badge country">${esc(x.agg)}</span>` : ""}<br><small>${note(x)} · <a href="${esc(x.src.url)}" target="_blank" rel="noopener">${esc(x.src.label)}</a></small></td></tr>`).join("")}</table>`
        : `<div class="empty">${r.year} 年没有数据（Maddison 对 1820 年以前多数国家只有少数基准年；世界银行数据从 1960 年起）。</div>`;
      h += chart(c.trend.gdppc, r.year, "人均 GDP（Maddison）", "国际元") + chart(c.trend.pop, r.year, "人口（Maddison）", "人") + chart(c.trend.life, r.year, "预期寿命（世界银行）", "岁");
    }
    h += `<div class="source">来源：${esc(m.source)}</div>`;
    box.innerHTML = h;
    return box;
  });
})();
