/*
 * 地图图层「实际控制区」（后端：backend/modules/layer_control_zones.py；数据：data/curated/control_zones.json）。
 * 范围画成虚线（不拦截点击，下面的政权多边形照常可点）；标签文字也不拦截点击，点「◇」可打开说明（日期来源、是否为大致范围）。
 */
(() => {
  "use strict";
  const COLOR = { holdout: "#1f5fbf", de_facto: "#8a5a00", occupied: "#b02a2a", armed_presence: "#6a3d9a", war_zone: "#d35400", unverified: "#5c564e", claim: "#d4b483" };
  let group = null, map = null;
  const fmt = (s) => (s ? s.replace(/^(-?\d+)-(\d+)-(\d+)$/, "$1年$2月$3日").replace(/^(-?\d+)-(\d+)$/, "$1年$2月").replace(/^(-?\d+)$/, "$1年") : "");

  WHA.registerLayer("control_zones", {
    init(m) {
      map = m;
      if (!map.getPane("zones")) { const p = map.createPane("zones"); p.style.zIndex = 450; p.style.pointerEvents = "none"; }
      group = L.layerGroup().addTo(map);
    },
    update(res) {
      group.clearLayers();
      for (const z of res.items || []) {
        const c = COLOR[z.kind] || "#333";
        const strat = document.body.classList.contains("strategy");
        const hot = z.kind === "occupied" || z.kind === "war_zone" || z.kind === "de_facto";
        const unnamed = z.kind === "unverified";
        const claim = z.kind === "claim";
        // 已经单独成多边形的区域不再铺一层深色，避免和底图颜色各说各话。声索样本几乎不填色。
        const fill = claim ? 0.04 : (unnamed ? 0.05 : (z.as_polity ? (strat ? 0.1 : 0.08) : (strat ? (hot ? 0.48 : 0.22) : 0.15)));
        L.geoJSON(z.geom, { pane: "zones", interactive: false,
          style: {
            color: c, weight: strat ? (hot && !z.as_polity ? 3 : 2.2) : 2,
            dashArray: claim || !strat || !hot || z.as_polity ? (strat ? "3 2" : "6 4") : null,
            fillColor: c, fillOpacity: fill,
          } }).addTo(group);
        const tip = `<b>${WHA.esc(z.name)}</b>${z.approx ? "（大致范围）" : ""}<br>${WHA.esc(z.kind_zh)} · 控制方：${WHA.esc(z.controller.zh)}` +
          `<br>${fmt(z.from) || "?"} – ${z.until ? fmt(z.until) : "至今"}` +
          (z.dates_note ? `<div style="max-width:320px;white-space:normal"><small>${WHA.esc(z.dates_note)}</small></div>` : "") +
          (z.note ? `<div style="max-width:320px;white-space:normal"><small>${WHA.esc(z.note)}</small></div>` : "") +
          `<small>来源：${z.sources.map((u) => `<a href="${WHA.esc(u)}" target="_blank" rel="noopener">${WHA.esc(decodeURIComponent(u.replace(/^https?:\/\//, "")).slice(0, 48))}</a>`).join("；")}</small>`;
        const icon = L.divIcon({ className: "zone-label", iconSize: null, iconAnchor: [-6, 8],   // 标签整体右移 6px，标签点本身留给下面的政权多边形
          html: `<span style="color:${strat ? "#f4efe6" : c};font-weight:600;font-size:12px;text-shadow:${strat ? "0 1px 2px #000,0 0 3px #000" : "0 0 3px #fff,0 0 3px #fff"};white-space:nowrap"><span class="zl-dot" style="color:${c}" title="点开说明">◇</span>${strat || unnamed ? "" : " " + WHA.esc(z.name) + (z.approx ? "<small>（大致范围）</small>" : "")}</span>` });
        L.marker([z.label[1], z.label[0]], { icon, keyboard: false, zIndexOffset: 800 }).bindPopup(tip, { maxWidth: 360 })
          // v0.6.1：点到标签（◇ 或文字）时，除弹出说明外也选中标签下方的政权，面板不再留空（1950 科威特）
          .on("click", () => WHA.selectAt(z.label[1], z.label[0])).addTo(group);
      }
    },
    clear() { group && group.clearLayers(); },
  });
})();
