/*
 * 「外交 / 国际组织」。顶栏按钮打开这一天还在的组织。
 * 点选国家后，国家面板列出该政权在这些组织里的资格。
 */
(function () {
  const { esc } = WHA;
  const link = (l) => `<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)}</a>`;

  function head(o) {
    return `<h2>${esc(o.zh)}</h2>${o.en ? `<div class="en">${esc(o.en)}</div>` : ""}
      <div class="s">${esc(o.type_zh || "")}${o.view_status ? ` · ${esc(o.view_status)}` : ""}</div>
      <table class="kv">
        <tr><th>成立或开始</th><td>${esc(o.from || "未记录")}</td></tr>
        ${o.signed && o.signed !== o.from ? `<tr><th>签署</th><td>${esc(o.signed)}</td></tr>` : ""}
        ${o.effective ? `<tr><th>生效</th><td>${esc(o.effective)}</td></tr>` : ""}
        <tr><th>停止</th><td>${esc(o.until || "未记录（或仍存在）")}</td></tr>
        <tr><th>所在地</th><td>${esc(o.headquarters || "未记录")}</td></tr>
      </table>
      ${o.summary ? `<div class="s">${esc(o.summary)}</div>` : ""}
      ${o.incomplete ? `<div class="note">名单不完整</div>` : ""}
      ${o.date_note ? `<div class="note">${esc(o.date_note)}</div>` : ""}`;
  }

  function tree(o) {
    const nodes = o.organs || [];
    if (!nodes.length) return "";
    const groups = [];
    nodes.forEach((n) => {
      let g = groups.find((x) => x.kind === n.kind_zh);
      if (!g) {
        g = { kind: n.kind_zh || "", nodes: [] };
        groups.push(g);
      }
      g.nodes.push(n);
    });
    let html = `<div id="diplomacyTree"><h4>这一天的机构</h4>`;
    const hasSpec = nodes.some((n) => n.kind === "specialized");
    html += hasSpec
      ? `<div class="note">主要机关按宪章。专门机构以关系协定相连，不是下属。没有写上的专门机构，这一批还没有逐个收录。</div>`
      : `<div class="note">主要机关按盟约。相关机构不是下属。这一天没有录入决议或判例时，写无记录。</div>`;
    for (const g of groups) {
      html += `<div class="s">${esc(g.kind)}</div>`;
      for (const n of g.nodes) {
        const acts = n.acts || [];
        html += `<div class="item" data-node="${esc(n.id)}">
          <div class="t">${esc(n.zh)} <span class="badge">${esc(n.kind_zh || "")}</span></div>
          <div class="d">${esc(n.from || "")}${n.until ? " 至 " + esc(n.until) : ""}</div>
          <div class="s">${esc(n.summary || "")}</div>
          <div class="s">当日决议或判例：${acts.length ? acts.map((a) => esc(a.zh)).join("；") : "无记录"}</div>
        </div>`;
      }
    }
    html += `</div>`;
    return html;
  }

  function memberTable(rows) {
    if (!rows || !rows.length) return `<div class="note">这一天没有写入会员。</div>`;
    return `<table class="kv"><tr><th>政权</th><th>这一天的资格</th></tr>${rows.map((p) =>
      `<tr><td>${esc(p.name)}</td><td>${esc(p.status)}${p.note ? `<div class="s">${esc(p.note)}</div>` : ""}</td></tr>`
    ).join("")}</table>`;
  }

  WHA.showDiplomacy = () => {
    const body = WHA.openDetail('<div class="empty">加载中…</div>');
    const date = WHA.dateParam();
    WHA.api(`/api/diplomacy?date=${encodeURIComponent(date)}`).then((r) => {
      let html = `<h2>外交 / 国际组织</h2><div class="s">${esc(WHA.dateZh())}</div>`;
      if (r.date_note) html += `<div class="note">${esc(r.date_note)}</div>`;
      html += `<div class="note">只列出这一批核对过、而且这一天还在的组织。点名称看资格。名单不完整的不补写其余会员。</div>`;
      if (!(r.orgs || []).length) html += `<div class="empty">这一天没有列出还在的组织。</div>`;
      for (const o of r.orgs || []) {
        html += `<div class="item" data-org="${esc(o.id)}">
          <div class="t">${esc(o.zh)} <span class="badge">${esc(o.type_zh || "")}</span></div>
          <div class="d">${esc(o.view_status || "")}</div>
          <div class="s">${esc(o.headquarters || "")}</div>
          ${o.incomplete ? `<div class="s">名单不完整</div>` : ""}
        </div>`;
      }
      body.innerHTML = html;
      body.querySelectorAll("[data-org]").forEach((el) => {
        el.onclick = () => WHA.showOrg(el.dataset.org);
      });
    }).catch((e) => {
      body.innerHTML = `<div class="empty">加载失败：${esc(e.message)}</div>`;
    });
  };

  WHA.showOrg = (id) => {
    const body = WHA.openDetail('<div class="empty">加载中…</div>');
    const date = WHA.dateParam();
    WHA.api(`/api/diplomacy/${encodeURIComponent(id)}?date=${encodeURIComponent(date)}`).then((o) => {
      let html = head(o);
      html += tree(o);
      if (o.list_note) html += `<div class="note">${esc(o.list_note)}</div>`;
      const skip = {"尚未加入": 1, "按年名单尚未加入": 1, "加入日未核": 1};
      const shown = (o.members || []).filter((p) => !skip[p.status]);
      html += `<h4>这一天的资格（${o.active_count != null ? o.active_count : shown.length}）</h4>`;
      html += memberTable(shown);
      html += `<div class="l">${(o.sources || []).map(link).join("")}</div>`;
      html += `<div class="source">来源写在上面的链接里。没有链接的句子不当作已经核对。</div>`;
      body.innerHTML = html;
    }).catch((e) => {
      body.innerHTML = `<div class="empty">加载失败：${esc(e.message)}</div>`;
    });
  };

  WHA.registerRenderer("diplomacy", (r) => {
    const box = document.createElement("div");
    box.className = "mod-diplomacy";
    let html = "";
    if (r.date_note) html += `<div class="note">${esc(r.date_note)}</div>`;
    if (r.coverage) html += `<div class="note">${esc(r.coverage)}</div>`;
    if (r.note) html += `<div class="note">${esc(r.note)}</div>`;
    if (r.kind === "state") {
      for (const it of r.items || []) {
        html += `<div class="item" data-org="${esc(it.id)}">
          <div class="t">${esc(it.zh)} <span class="badge">${esc(it.type_zh || "")}</span></div>
          <div class="d">${esc(it.qualification || "")}</div>
          ${it.member && it.member.name ? `<div class="s">${esc(it.member.name)}</div>` : ""}
          ${it.incomplete ? `<div class="s">名单不完整</div>` : ""}
        </div>`;
      }
      if (!(r.items || []).length) html += `<div class="empty">这一天没有写到资格。</div>`;
    } else {
      for (const it of r.items || []) {
        html += `<div class="item" data-org="${esc(it.id)}">
          <div class="t">${esc(it.zh)} <span class="badge">${esc(it.type_zh || "")}</span></div>
          <div class="d">${esc(it.view_status || "")}</div>
          ${it.incomplete ? `<div class="s">名单不完整</div>` : ""}
        </div>`;
      }
      if (!(r.items || []).length) html += `<div class="empty">这一天没有列出还在的组织。</div>`;
    }
    html += `<div class="source">点一条打开。来源在打开的那一页。</div>`;
    box.innerHTML = html;
    box.querySelectorAll("[data-org]").forEach((el) => {
      el.onclick = () => WHA.showOrg(el.dataset.org);
    });
    return box;
  });
})();
