/*
 * 民国省界图层和「省界与实控」面板。
 * 虚线不拦截点击，也不给政权填色。有实控记录时才标派系名称。
 */
(() => {
  "use strict";
  let group = null;
  let map = null;

  WHA.registerLayer("roc_provinces", {
    init(m) {
      map = m;
      if (!map.getPane("rocprov")) {
        const pane = map.createPane("rocprov");
        pane.style.zIndex = 432;
        pane.style.pointerEvents = "none";
      }
      group = L.layerGroup().addTo(map);
    },
    update(res) {
      group.clearLayers();
      const strat = document.body.classList.contains("strategy");
      const stroke = strat ? "#c9bfae" : "#5c564e";
      const ink = strat ? "#f4efe6" : "#8a5a00";
      const shadow = strat ? "0 1px 2px #000,0 0 3px #000" : "0 0 3px #fff,0 0 3px #fff";
      const tag = (text, color) => L.divIcon({
        className: "zone-label",
        iconSize: null,
        iconAnchor: [0, 0],
        html: `<span style="color:${color};font-weight:600;font-size:12px;text-shadow:${shadow};white-space:nowrap">${WHA.esc(text)}</span>`,
      });
      for (const row of res.items || []) {
        L.geoJSON(row.geom, {
          pane: "rocprov",
          interactive: false,
          style: { color: stroke, weight: strat ? 1.15 : 1.35, opacity: 0.9, dashArray: "6 4", fill: false, smoothFactor: 0 },
        }).addTo(group);
        if (!row.actual) continue;
        L.marker([row.label[1], row.label[0]], {
          pane: "rocprov", icon: tag(row.actual, ink), interactive: false, keyboard: false,
        }).addTo(group);
      }
      const frontColor = strat ? "#e2b15a" : "#9a3412";
      for (const line of res.fronts || []) {
        const latlngs = (line.line || []).map(([lon, lat]) => [lat, lon]);
        if (latlngs.length < 2) continue;
        L.polyline(latlngs, {
          pane: "rocprov", interactive: false, className: "roc-front",
          color: frontColor, weight: 3, opacity: 0.95, dashArray: "2 7",
        }).addTo(group);
        const mid = latlngs[Math.floor(latlngs.length / 2)];
        L.marker(mid, {
          pane: "rocprov", icon: tag(line.label || "大致", frontColor), interactive: false, keyboard: false,
        }).addTo(group);
      }
      const zoom = map && map.getZoom ? map.getZoom() : 4;
      for (const seat of res.seats || []) {
        L.circleMarker([seat.lat, seat.lon], {
          pane: "rocprov", interactive: false, className: "roc-seat",
          radius: 4, color: frontColor, weight: 1.5, fillColor: strat ? "#1a1612" : "#fffaf3", fillOpacity: 0.95,
        }).addTo(group);
        if (zoom < 6) continue;
        L.marker([seat.lat, seat.lon], {
          pane: "rocprov", icon: tag(seat.label || seat.name, frontColor), interactive: false, keyboard: false,
        }).addTo(group);
      }
    },
    clear() { group && group.clearLayers(); },
  });

  WHA.registerRenderer("roc_admin", (r) => {
    const box = document.createElement("div");
    box.className = "mod-roc_admin";
    const p = r.place || {};
    let html = "";
    if (r.date_note) html += `<div class="note">${WHA.esc(r.date_note)}</div>`;
    if (r.note) html += `<div class="note">${WHA.esc(r.note)}</div>`;
    const pending = p.status !== "draw";
    html += `<table class="kv">
      <tr><th>省名</th><td>${WHA.esc(pending ? "省界待考" : (p.name || "省界待考"))}</td></tr>
      <tr><th>建制</th><td>${WHA.esc(pending ? "—" : (p.kind || "—"))}</td></tr>
      <tr><th>名义所属</th><td>${WHA.esc(p.nominal || "—")}</td></tr>
      <tr><th>实际控制</th><td>${WHA.esc(p.actual || (pending ? "—" : "实控待考"))}</td></tr>
    </table>`;
    if (p.scheme) html += `<div class="s">${WHA.esc(p.scheme)}</div>`;
    if (p.note) html += `<div class="note">${WHA.esc(p.note)}</div>`;
    if (p.line_note && p.line_note !== p.note) html += `<div class="note">${WHA.esc(p.line_note)}</div>`;
    const links = (p.sources || []).map((url) => `<a href="${WHA.esc(url)}" target="_blank" rel="noopener">来源</a>`).join(" ");
    if (links) html += `<div class="l">${links}</div>`;
    const wars = r.wars || [];
    html += `<div class="s">内战</div>`;
    if (!wars.length) html += `<div class="note">这一天、这个省没有在画的内战。</div>`;
    for (const war of wars) {
      html += `<div class="s">${WHA.esc(war.name)}</div>`;
      html += `<div class="note">${WHA.esc(war.sides || "")} ${WHA.esc(war.from || "")} 至 ${WHA.esc(war.until || "待考")}。${WHA.esc(war.note || "")}</div>`;
    }
    const fronts = r.fronts || [];
    if (fronts.length) {
      html += `<div class="s">大致线</div>`;
      for (const line of fronts) {
        html += `<div class="note">${WHA.esc(line.label || "大致")}。${WHA.esc(line.kind || "")}。${WHA.esc(line.note || "")}</div>`;
      }
    }
    const seats = r.seats || [];
    if (seats.length) {
      html += `<div class="s">县城点（不是县界）</div>`;
      html += `<div class="note">${seats.map((s) => WHA.esc(s.label || s.name)).join("、")}。${WHA.esc(seats[0].note || "")}</div>`;
    }
    html += `<div class="source">省界：ENP-China / Virtual Shanghai（${WHA.esc(r.license || "CC0 1.0")}）。县城点：MCGD_Rep（${WHA.esc(r.county_license || "CC BY 4.0")}），不是县界。</div>`;
    box.innerHTML = html;
    return box;
  });
})();
