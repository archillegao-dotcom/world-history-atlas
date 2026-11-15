/*
 * 地图图层「主要城市」的前端绘制（后端模块：backend/modules/layer_cities.py）。
 * - 按缩放级别决定最多显示多少个城市（世界视图少、放大后多）；
 * - 按综合分数从高到低贪心放置，屏幕上与已放置标签重叠的跳过（避免文字挤在一起）；
 * - 当时的国家首都用红色 ★ 标出。
 */
(() => {
  "use strict";
  const MAX_BY_ZOOM = (z, strategy) => strategy
    ? (z < 3.2 ? 6 : z < 4.2 ? 10 : z < 5.2 ? 14 : z < 6.5 ? 36 : 80)
    : (z < 3.2 ? 14 : z < 4.2 ? 24 : z < 5.2 ? 48 : z < 6.5 ? 110 : 240);
  let group = null, data = [], map = null;

  function draw() {
    if (!map || !group) return;
    group.clearLayers();
    const b = map.getBounds().pad(0.05), z = map.getZoom();
    const strategy = document.body.classList.contains("strategy");
    const max = MAX_BY_ZOOM(z, strategy);
    const placed = [];
    // 首都优先。策略地图在放大到 5 级以前只留首都，避免和国名挤在一起。
    const list = data.filter((c) => b.contains([c.coord[1], c.coord[0]]) && (!strategy || z >= 5 || c.capital))
      .sort((a, c) => (c.score + (c.capital ? 80 : 0)) - (a.score + (a.capital ? 80 : 0)));
    let n = 0;
    for (const c of list) {
      if (n >= max) break;
      const p = map.latLngToContainerPoint([c.coord[1], c.coord[0]]);
      const nameOn = !strategy || z >= 5;
      const shown = !nameOn ? "" : (c.name || "");
      const w = shown ? shown.length * 13 + 16 : 16, h = 16;
      const box = [p.x - 8, p.y - h / 2, p.x + w, p.y + h / 2];
      const hit = (q) => !(box[2] < q[0] || box[0] > q[2] || box[3] < q[1] || box[1] > q[3]);
      if (placed.some(hit) || (WHA.polityLabelBoxes || []).some(hit)) continue;
      placed.push(box);
      n++;
      const icon = L.divIcon({
        className: "city-icon",
        html: `<span class="city-dot${c.capital ? " cap" : ""}">${c.capital ? "★" : ""}</span>${shown ? `<span class="city-name${c.capital ? " cap" : ""}">${WHA.esc(shown)}</span>` : ""}`,
        iconSize: null, iconAnchor: [5, 8],
      });
      const tip = `<b>${WHA.esc(c.name)}</b>${c.en && c.en !== c.name ? " " + WHA.esc(c.en) : ""}` +
        (c.capital ? "<br>★ 当时的国家首都" : "") +
        (c.hist.length ? `<br>当时官方名称：${c.hist.map(WHA.esc).join(" / ")}` : "") +
        (c.pop ? `<br>人口（Wikidata 最新）：${c.pop.toLocaleString()}` : "") +
        (c.inferred ? "<br><small>建立时间无记录，按已知最早存在证据显示</small>" : "") + "<br><small>点击：查看所在政权；Ctrl/⌘+点击：维基百科</small>";
      L.marker([c.coord[1], c.coord[0]], { icon, keyboard: false, zIndexOffset: c.capital ? 500 : 0 })
        .bindTooltip(tip, { direction: "top", offset: [0, -6] })
        // 点击城市：选中城市所在的政权（与点击多边形相同）；按住 Ctrl/⌘ 点击则打开维基百科
        .on("click", (e) => { if ((e.originalEvent?.ctrlKey || e.originalEvent?.metaKey) && c.wiki) window.open(c.wiki, "_blank"); else WHA.selectAt(c.coord[1], c.coord[0]); })
        .on("mouseover", (e) => WHA.hoverBeginAt && WHA.hoverBeginAt(c.coord[1], c.coord[0], e))
        .on("mouseout", () => WHA.hoverEnd && WHA.hoverEnd())
        .addTo(group);
    }
    WHA.cityLabelBoxes = placed;
    if (WHA.placePolityLabels) WHA.placePolityLabels();
  }

  WHA.registerLayer("cities", {
    init(m) { map = m; group = L.layerGroup().addTo(map); map.on("zoomend moveend", draw); },
    update(res) { data = res.items || []; draw(); },
    clear() { data = []; group && group.clearLayers(); },
  });
})();
