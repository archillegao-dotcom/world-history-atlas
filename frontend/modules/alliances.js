/*
 * 「阵营地图」图层：按所选日期的同盟/阵营成员资格给国家着色。
 * 用户在左下角的图例里勾选要显示的阵营（默认勾选当时最知名的两个）；点阵营名称打开阵营面板。
 * 一个国家同时属于多个已勾选阵营时，按图例顺序取第一个的颜色，边框加粗（悬停提示里列出全部）。
 */
(function () {
  const { esc } = WHA;
  const COLORS = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b", "#e377c2", "#17becf", "#bcbd22", "#7f7f7f"];
  let box = null, data = null;
  const chosen = new Set();      // 用户勾选的阵营 QID
  let touched = false;           // 用户是否手动改过勾选

  function paint() {
    if (!data) return;
    const sel = data.alliances.filter((a) => chosen.has(a.id));
    WHA.state.blocs = sel.map((a) => a.id); WHA.updateHash();
    const color = {}; sel.forEach((a, i) => (color[a.id] = COLORS[i % COLORS.length]));
    const sets = sel.map((a) => [a, new Set(a.members)]);
    WHA.setFillOverride((f) => {
      const c = data.polity_states[String(f.properties.fid)] || [];
      const hit = sets.filter(([, s]) => c.some((q) => s.has(q)));
      if (!hit.length) return { fillColor: "#e9e6df", fillOpacity: 0.55 };
      return { fillColor: color[hit[0][0].id], fillOpacity: 0.7, weight: hit.length > 1 ? 2 : 0.6 };
    }, "alliances");
    // 图例
    const list = data.alliances.slice(0, 60);
    box.innerHTML = `<b>阵营地图</b> <small>${esc(WHA.dateZh())}</small>
      <div class="note">勾选要显示的阵营；点名称查看详情。只列出 Wikidata 中有起止时间、且当时至少有 2 个成员的阵营（${data.alliances.length} 个）。</div>
      <div class="alist">${list.map((a) => `<label><input type="checkbox" data-id="${esc(a.id)}" ${chosen.has(a.id) ? "checked" : ""}>
        <span class="sw" style="background:${color[a.id] || "transparent"}"></span><a href="#" data-bloc="${esc(a.id)}">${esc(a.name)}</a> <small>${a.members.length}国${a.no_end ? ' · <span title="Wikidata 没有记录解散时间">无解散记录</span>' : ""}</small></label>`).join("") || '<div class="empty">这一日期没有记录的阵营。</div>'}</div>`;
    box.querySelectorAll("input").forEach((el) => (el.onchange = () => { touched = true; el.checked ? chosen.add(el.dataset.id) : chosen.delete(el.dataset.id); paint(); }));
    box.querySelectorAll("[data-bloc]").forEach((el) => (el.onclick = (e) => { e.preventDefault(); WHA.showBloc(el.dataset.bloc); }));
  }

  WHA.registerLayer("alliances", {
    init(map) {
      const Ctl = L.Control.extend({ onAdd() { box = L.DomUtil.create("div", "alliance-legend hidden"); L.DomEvent.disableClickPropagation(box); L.DomEvent.disableScrollPropagation(box); return box; } });
      new Ctl({ position: "topleft" }).addTo(map);
    },
    update(res) {
      data = res;
      data.alliances.sort((a, b) => b.sl - a.sl);
      const ids = new Set(data.alliances.map((a) => a.id));
      for (const id of [...chosen]) if (!ids.has(id)) chosen.delete(id);
      // URL 参数 #...&blocs=Q1,Q2 可指定勾选（便于分享/截图）
      const h = WHA.initialHash.get("blocs");
      if (h && !touched) { chosen.clear(); h.split(",").forEach((q) => ids.has(q) && chosen.add(q)); }
      else if (!chosen.size && !touched) data.alliances.slice(0, 2).forEach((a) => chosen.add(a.id));
      box.classList.remove("hidden");
      paint();
    },
    clear() { data = null; if (box) box.classList.add("hidden"); WHA.setFillOverride(null, "alliances"); },
  });
})();
