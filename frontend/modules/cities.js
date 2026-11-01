/*
 * 地图图层「主要城市」的前端绘制（后端模块：backend/modules/layer_cities.py）。
 * - 按缩放级别决定最多显示多少个城市（世界视图少、放大后多）；
 * - 按综合分数从高到低贪心放置，屏幕上与已放置标签重叠的跳过（避免文字挤在一起）；
 * - 当时的国家首都用红色 ★ 标出。
 */
(() => {
  "use strict";
  const MAX_BY_ZOOM = (z) => (z < 2.75 ? 35 : z < 3.5 ? 80 : z < 4.5 ? 170 : z < 5.5 ? 380 : 900);
  let group = null, data = [], map = null;

  function draw() {
    if (!map || !group) return;
    group.clearLayers();
    const b = map.getBounds().pad(0.05), z = map.getZoom(), max = MAX_BY_ZOOM(z);
    const placed = [];
    // 首都优先一些，其次按分数
    const list = data.filter((c) => b.contains([c.coord[1], c.coord[0]]))
      .sort((a, c) => (c.score + (c.capital ? 40 : 0)) - (a.score + (a.capital ? 40 : 0)));
    let n = 0;
    for (const c of list) {
      if (n >= max) break;
      const p = map.latLngToContainerPoint([c.coord[1], c.coord[0]]);
      const w = (c.name || "").length * 12 + 16, h = 16;
      const box = [p.x - 4, p.y - h / 2, p.x + w, p.y + h / 2];
      if (placed.some((q) => !(box[2] < q[0] || box[0] > q[2] || box[3] < q[1] || box[1] > q[3]))) continue;
      placed.push(box);
      n++;
      const icon = L.divIcon({
        className: "city-icon",
        html: `<span class="city-dot${c.capital ? " cap" : ""}">${c.capital ? "★" : ""}</span><span class="city-name${c.capital ? " cap" : ""}">${WHA.esc(c.name)}</span>`,
        iconSize: null, iconAnchor: [5, 8],
      });
      const tip = `<b>${WHA.esc(c.name)}</b>${c.en && c.en !== c.name ? " " + WHA.esc(c.en) : ""}` +
        (c.capital ? "<br>★ 当时的国家首都" : "") +
        (c.hist.length ? `<br>当时官方名称：${c.hist.map(WHA.esc).join(" / ")}` : "") +
        (c.pop ? `<br>人口（Wikidata 最新）：${c.pop.toLocaleString()}` : "") +
        (c.inferred ? "<br><small>建立时间无记录，按已知最早存在证据显示</small>" : "");
      L.marker([c.coord[1], c.coord[0]], { icon, keyboard: false, zIndexOffset: c.capital ? 500 : 0 })
        .bindTooltip(tip, { direction: "top", offset: [0, -6] })
        .on("click", () => c.wiki && window.open(c.wiki, "_blank"))
        .addTo(group);
    }
  }

  WHA.registerLayer("cities", {
    init(m) { map = m; group = L.layerGroup().addTo(map); map.on("zoomend moveend", draw); },
    update(res) { data = res.items || []; draw(); },
    clear() { data = []; group && group.clearLayers(); },
  });
})();
