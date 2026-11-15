/*
 * 实际控制 / 主权声索 / 国际承认。
 * 填色只用这一层已有的占领色、事实控制色。声索是虚线，不改策略地图的陆地配色。
 * 不拦截点击。
 */
(() => {
  "use strict";
  const COLOR = { occupied: "#c0392b", de_facto: "#8a5a00", claim: "#d4b483" };
  let group = null, map = null;

  WHA.registerLayer("status_layers", {
    init(m) {
      map = m;
      if (!map.getPane("statusFill")) { const p = map.createPane("statusFill"); p.style.zIndex = 455; p.style.pointerEvents = "none"; }
      if (!map.getPane("statusClaim")) { const p = map.createPane("statusClaim"); p.style.zIndex = 470; p.style.pointerEvents = "none"; }
      group = L.layerGroup().addTo(map);
    },
    update(res) {
      group.clearLayers();
      const strat = document.body.classList.contains("strategy");
      for (const z of res.items || []) {
        const c = COLOR[z.color_kind] || COLOR.claim;
        const dash = z.draw === "dash";
        L.geoJSON(z.geom, {
          pane: dash ? "statusClaim" : "statusFill",
          interactive: false,
          style: {
            color: c,
            weight: dash ? 2.4 : 1.6,
            dashArray: dash ? "7 5" : null,
            fillColor: c,
            fillOpacity: dash ? 0.08 : (strat ? 0.4 : 0.28),
          },
        }).addTo(group);
        if (!z.probe) continue;
        const icon = L.divIcon({
          className: "zone-label",
          iconSize: null,
          iconAnchor: [0, 0],
          html: `<span style="color:${strat ? "#f4efe6" : c};font-weight:600;font-size:12px;text-shadow:${strat ? "0 1px 2px #000,0 0 3px #000" : "0 0 3px #fff,0 0 3px #fff"};white-space:nowrap">${WHA.esc(z.label)}</span>`,
        });
        L.marker([z.probe[1], z.probe[0]], { icon, interactive: false, keyboard: false, zIndexOffset: 830 }).addTo(group);
      }
    },
    clear() { group && group.clearLayers(); },
  });
})();
