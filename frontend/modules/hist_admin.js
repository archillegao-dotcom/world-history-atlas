/*
 * 欧洲、中国以外的历史区划。
 * 虚线不填色，不拦截点击，也不改政权颜色。
 */
(() => {
  "use strict";
  let group = null;
  let map = null;

  WHA.registerLayer("hist_div", {
    init(m) {
      map = m;
      if (!map.getPane("histdiv")) {
        const pane = map.createPane("histdiv");
        pane.style.zIndex = 430;
        pane.style.pointerEvents = "none";
      }
      group = L.layerGroup().addTo(map);
    },
    update(res) {
      group.clearLayers();
      const strat = document.body.classList.contains("strategy");
      const stroke = strat ? "#c9bfae" : "#3f6f8f";
      const ink = strat ? "#f4efe6" : "#1f4e6b";
      const shadow = strat ? "0 1px 2px #000,0 0 3px #000" : "0 0 3px #fff,0 0 3px #fff";
      for (const row of res.items || []) {
        L.geoJSON(row.geom, {
          pane: "histdiv",
          interactive: false,
          style: { color: stroke, weight: strat ? 1.05 : 1.2, opacity: 0.85, dashArray: "4 3", fill: false, smoothFactor: 1.2 },
        }).addTo(group);
      }
      const zoom = map && map.getZoom ? map.getZoom() : 4;
      if (zoom < 5) return;
      let labeled = 0;
      for (const row of res.items || []) {
        if (labeled >= 60 || !row.label) continue;
        labeled += 1;
        const icon = L.divIcon({
          className: "zone-label",
          iconSize: null,
          iconAnchor: [0, 0],
          html: `<span style="color:${ink};font-weight:600;font-size:11px;text-shadow:${shadow};white-space:nowrap">${WHA.esc(row.name)}</span>`,
        });
        L.marker([row.label[1], row.label[0]], {
          pane: "histdiv", icon, interactive: false, keyboard: false,
        }).addTo(group);
      }
    },
    clear() { group && group.clearLayers(); },
  });

  WHA.registerRenderer("hist_div_panel", (r) => {
    const box = document.createElement("div");
    box.className = "mod-hist_div";
    const p = r.place || {};
    let html = "";
    if (r.date_note) html += `<div class="note">${WHA.esc(r.date_note)}</div>`;
    const pending = p.status !== "draw";
    html += `<table class="kv">
      <tr><th>区划</th><td>${WHA.esc(pending ? "区划待考" : (p.name || "区划待考"))}</td></tr>
      <tr><th>类别</th><td>${WHA.esc(pending ? "—" : (p.kind || "—"))}</td></tr>
      <tr><th>起</th><td>${WHA.esc(pending ? "—" : (p.raw_start || p.from || "—"))}</td></tr>
      <tr><th>止</th><td>${WHA.esc(pending ? "—" : (p.raw_end || p.until || "—"))}</td></tr>
    </table>`;
    if (p.date_note) html += `<div class="note">${WHA.esc(p.date_note)}</div>`;
    if (p.note) html += `<div class="note">${WHA.esc(p.note)}</div>`;
    if (p.precision) html += `<div class="note">${WHA.esc(p.precision)}</div>`;
    if (p.source_url) html += `<div class="l"><a href="${WHA.esc(p.source_url)}" target="_blank" rel="noopener">OpenHistoricalMap</a></div>`;
    const counts = r.counts || {};
    const drawn = Object.values(counts).reduce((a, b) => a + b, 0);
    html += `<div class="s">这一天画出的区划</div><div class="note">${drawn} 块。没有数字的地区不是没有历史，是没有合法几何。</div>`;
    html += `<div class="source">来源：OpenHistoricalMap（${WHA.esc(r.license || "CC0 1.0")}）。不使用今天的行政区填空档。</div>`;
    box.innerHTML = html;
    return box;
  });
})();
