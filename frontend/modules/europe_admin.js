/*
 * 欧洲历史一级行政区。虚线不拦截点击，也不给政权填色。
 * 用和民国省界同一套虚线，不另换策略地图的配色。
 */
(() => {
  "use strict";
  let group = null;

  WHA.registerLayer("europe_admin", {
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
          style: { color: stroke, weight: strat ? 1.05 : 1.2, opacity: 0.85, dashArray: "2 3", fill: false, smoothFactor: 0 },
        }).addTo(group);
      }
    },
    clear() { group && group.clearLayers(); },
  });
})();
