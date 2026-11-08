/*
 * 「宪法」页。只有后端标明 shown 时，标签才会出现。
 */
(function () {
  const { esc } = WHA;
  const line = (label, value) => value ? `<div class="d">${esc(label)}：${esc(value)}</div>` : "";
  WHA.registerRenderer("constitution", (r) => {
    const box = document.createElement("div");
    box.className = "mod-constitution";
    if (!r.shown) {
      box.innerHTML = `<div class="note">${esc(r.note || "当前整理范围没有收录这个政权。")}</div>`;
      return box;
    }
    let html = r.note ? `<div class="note">${esc(r.note)}</div>` : "";
    for (const it of r.items || []) {
      html += `<div class="item" data-id="${esc(it.id)}">
        <div class="t">${esc(it.title)}${it.title_en ? `<span class="en">${esc(it.title_en)}</span>` : ""}
          <span class="badge">${esc(it.kind_zh || "类型待考")}</span></div>
        ${line("通过", it.adopted)}
        ${line("公布", it.promulgated)}
        ${line("生效", it.effective)}
        ${line("废止", it.repealed)}
        ${it.summary ? `<div class="s">${esc(it.summary)}</div>` : ""}
        <div class="l">${(it.links || []).map((l) => `<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)}</a>`).join(" ")}</div>
        ${(it.parts || []).map((p) => `<div class="s"><b>${esc(p.title)}</b> <span class="badge">${esc(p.kind_zh || "")}</span>
          ${p.effective ? ` · 列入 ${esc(p.effective)}` : ""}<br>${esc(p.summary || "")}</div>`).join("")}
      </div>`;
    }
    html += `<div class="source">来源写在各条链接里。摘要是短句，不是条文。</div>`;
    box.innerHTML = html;
    return box;
  });
})();
