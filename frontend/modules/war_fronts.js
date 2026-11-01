/*
 * 地图图层「战争前线」（后端：backend/modules/layer_war_fronts.py；数据：data/war_fronts/）。
 * 占领/控制区为实色红，灰色区为灰色；左上角说明框显示数据日期、面积、数据来源。不拦截点击（下面的政权多边形照常可点）。
 */
(() => {
  "use strict";
  const COLOR = { occupied: "#c0392b", contested: "#7f8c8d" };
  let group = null, box = null;
  const esc = (s) => WHA.esc(s == null ? "" : String(s));
  const num = (x) => (x == null ? "—" : Math.round(x).toLocaleString("zh-CN"));

  WHA.registerLayer("war_fronts", {
    init(map) {
      if (!map.getPane("fronts")) { const p = map.createPane("fronts"); p.style.zIndex = 440; p.style.pointerEvents = "none"; }
      group = L.layerGroup().addTo(map);
      const Ctl = L.Control.extend({ onAdd() { box = L.DomUtil.create("div", "alliance-legend war-legend hidden"); L.DomEvent.disableClickPropagation(box); L.DomEvent.disableScrollPropagation(box); return box; } });
      new Ctl({ position: "topleft" }).addTo(map);
    },
    update(res) {
      group.clearLayers();
      const wars = res.items || [];
      for (const w of wars) for (const z of w.items) {
        L.geoJSON(z.geom, { pane: "fronts", interactive: false,
          style: { color: COLOR[z.kind] || "#333", weight: z.kind === "occupied" ? 1.2 : 0.6, fillColor: COLOR[z.kind] || "#333",
                   fillOpacity: z.kind === "occupied" ? 0.45 : 0.35, dashArray: z.approx ? "5 3" : null } }).addTo(group);
      }
      if (!wars.length) { box.innerHTML = `<b>战争前线</b><div class="note">${esc(res.note)}</div>`; box.classList.remove("hidden"); return; }
      box.innerHTML = wars.map((w) => {
        const rows = w.items.map((z) => `<div><span class="sw" style="background:${COLOR[z.kind]};opacity:.7"></span> ${esc(z.name_zh)}${z.approx ? "（大致范围）" : ""}` +
          (z.area_km2 != null ? `：${num(z.area_km2)} km²` : "") +
          (z.delta_km2 != null && Math.abs(z.delta_km2) >= 0.5 ? ` <small>（较 ${esc(z.prev_from)} ${z.delta_km2 > 0 ? "+" : ""}${num(z.delta_km2)}）</small>` : "") +
          (z.dates_note ? `<div class="note">${esc(z.dates_note)}</div>` : "") + `</div>`).join("");
        const z0 = w.items.find((z) => z.snapshot_time) || w.items[0];
        const ds = Object.values(w.datasets).map((d) => `<a href="${esc(d.url)}" target="_blank" rel="noopener">${esc(d.name)}</a>（${esc(d.license)}）${d.note ? "：" + esc(d.note) : ""}`).join("<br>");
        return `<b>${esc(w.war.name_zh)}</b>` + (z0 && z0.snapshot_time ? `<div class="note">快照：${esc(z0.snapshot_time)}` +
          (z0.sources && z0.sources[0] ? ` · <a href="${esc(z0.sources[0])}" target="_blank" rel="noopener">原始地图</a>` : "") + `</div>` : "") +
          (w.beyond_data ? `<div class="note" style="color:#b00">所选日期晚于数据截止日 ${esc(w.war.data_until)}，显示的是最后一次数据。</div>` : "") +
          rows + `<div class="note">来源：${ds}</div>`;
      }).join("<hr>");
      box.classList.remove("hidden");
    },
    clear() { group && group.clearLayers(); if (box) box.classList.add("hidden"); },
  });
})();
