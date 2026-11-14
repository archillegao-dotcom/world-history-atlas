/*
 * 民国省界图层和「省界与实控」面板。
 * 虚线不拦截点击，也不给政权填色。有实控记录时才标派系名称。
 */
(() => {
  "use strict";
  let group = null;

  WHA.registerLayer("roc_provinces", {
    init(map) {
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
      for (const row of res.items || []) {
        L.geoJSON(row.geom, {
          pane: "rocprov",
          interactive: false,
          style: { color: stroke, weight: strat ? 1.15 : 1.35, opacity: 0.9, dashArray: "6 4", fill: false },
        }).addTo(group);
        if (!row.actual) continue;
        const icon = L.divIcon({
          className: "zone-label",
          iconSize: null,
          iconAnchor: [0, 0],
          html: `<span style="color:${strat ? "#f4efe6" : "#8a5a00"};font-weight:600;font-size:12px;text-shadow:${strat ? "0 1px 2px #000,0 0 3px #000" : "0 0 3px #fff,0 0 3px #fff"};white-space:nowrap">${WHA.esc(row.actual)}</span>`,
        });
        L.marker([row.label[1], row.label[0]], { pane: "rocprov", icon, interactive: false, keyboard: false }).addTo(group);
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
    html += `<div class="source">几何：ENP-China / Virtual Shanghai（${WHA.esc(r.license || "CC0 1.0")}）。建制和实控的出处在上面。</div>`;
    box.innerHTML = html;
    return box;
  });
})();
