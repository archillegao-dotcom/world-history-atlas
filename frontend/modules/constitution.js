/*
 * 「宪法 / 基本法」页。点选政权后出现。没有列出某部文本，只说明本批没有这条记录。
 */
(function () {
  const { esc } = WHA;
  const line = (label, value) => value ? `<div class="d">${esc(label)}：${esc(value)}</div>` : "";
  WHA.registerRenderer("constitution", (r) => {
    const box = document.createElement("div");
    box.className = "mod-constitution";
    let html = `<div class="note cover">${esc(r.coverage || "本页只收录已核对的一部分。没有列出，不等于没有。")}</div>`;
    if (r.note) html += `<div class="note">${esc(r.note)}</div>`;
    for (const it of r.items || []) {
      html += `<div class="item" data-id="${esc(it.id)}">
        <div class="t">${esc(it.title)}${it.title_en ? `<span class="en">${esc(it.title_en)}</span>` : ""}
          <span class="badge">${esc(it.kind_zh || "类型待考")}</span></div>
        ${it.force_zh ? `<div class="d">效力：${esc(it.force_zh)}</div>` : ""}
        ${it.force_note ? `<div class="s">${esc(it.force_note)}</div>` : ""}
        ${line("通过", it.adopted)}
        ${line("公布", it.promulgated)}
        ${line("生效", it.effective)}
        ${it.effective_clause ? `<div class="d">生效表述：${esc(it.effective_clause)}</div>` : ""}
        ${it.effective_clause_orig ? `<div class="s">${esc(it.effective_clause_orig)}</div>` : ""}
        ${it.day_note ? `<div class="s">${esc(it.day_note)}</div>` : ""}
        ${line("废止", it.repealed)}
        ${it.summary ? `<div class="s">${esc(it.summary)}</div>` : ""}
        <div class="l">${(it.links || []).map((l) => `<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)}</a>`).join(" ")}</div>
        ${(it.parts || []).map((p) => `<div class="s"><b>${esc(p.title)}</b> <span class="badge">${esc(p.kind_zh || "")}</span>
          ${p.since_note ? `<br>${esc(p.since_note)}` : ""}
          ${p.effective ? `<br>列入 ${esc(p.effective)}` : ""}<br>${esc(p.summary || "")}</div>`).join("")}
      </div>`;
    }
    if (!(r.items || []).length) html += `<div class="empty">这一天没有列出文本。</div>`;
    html += `<div class="source">来源写在各条链接里。摘要是短句，不是条文。</div>`;
    box.innerHTML = html;
    return box;
  });
})();
