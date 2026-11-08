/*
 * 「领导人」「政权性质」两个面板模块的前端渲染，以及共用的详情窗口：
 *   WHA.showPerson(qid)  人物页面（维基百科摘要、照片、生卒、担任职务、链接）
 *   WHA.showOffice(qid)  机构卡片（职位与所领导机构的维基百科摘要、历任者）
 *   WHA.showBloc(qid)    阵营面板（成立/解散、成员加入/退出、领导人物）
 * 所有内容都来自后端接口，后端数据来自 Wikidata / 维基百科，并在每张卡片底部注明来源。
 */
(function () {
  const { esc } = WHA;
  const link = (l) => `<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)}</a>`;
  const span = (a, b) => (a || b ? `${esc(a || "?")} – ${esc(b || "")}` : "");
  // 人物 / 职位 / 阵营的可点击链接
  const bare = (s) => /^Q\d+(@Q\d+)?$/.test(s || "");
  const vis = (name, fallback) => (!name || bare(name) ? fallback : name);
  const P = (p) => p ? `<a href="#" class="wl" data-person="${esc(p.id)}">${esc(vis(p.name, "姓名未记录"))}</a>` : "";
  const O = (o) => `<a href="#" class="wl" data-office="${esc(o.id)}">${esc(vis(o.name, "职位名称未记录"))}</a>`;
  const B = (b) => `<a href="#" class="wl" data-bloc="${esc(b.id)}">${esc(vis(b.name, "暂无通用译名"))}</a>`;
  const T = (t) => `<a href="#" class="wl" data-treaty="${esc(t.id)}">${esc(vis(t.name, "暂无通用译名"))}</a>`;

  function wire(root) {
    root.querySelectorAll("[data-person]").forEach((a) => (a.onclick = (e) => { e.preventDefault(); WHA.showPerson(a.dataset.person); }));
    root.querySelectorAll("[data-office]").forEach((a) => (a.onclick = (e) => { e.preventDefault(); WHA.showOffice(a.dataset.office); }));
    root.querySelectorAll("[data-bloc]").forEach((a) => (a.onclick = (e) => { e.preventDefault(); WHA.showBloc(a.dataset.bloc); }));
    root.querySelectorAll("[data-treaty]").forEach((a) => (a.onclick = (e) => { e.preventDefault(); WHA.showTreaty(a.dataset.treaty); }));
  }
  const summaryHtml = (s, label) => s ? `<div class="wsum">${s.thumb ? `<img src="${esc(s.thumb)}" alt="">` : ""}
      <p>${esc(s.extract)}</p>${s.mt && s.orig ? `<details class="s"><summary>英文原文</summary>${esc(s.orig)}</details>` : ""}<div class="src">${s.mt ? "机器翻译（Argos Translate，离线）自" : "摘要来源："}<a href="${esc(s.url)}" target="_blank" rel="noopener">${s.lang === "zh" ? "中文维基百科" : "English Wikipedia"}「${esc(s.title)}」</a>（CC BY-SA）</div></div>`
    : `<div class="note">${label || "没有取得维基百科摘要（可能离线，或该条目没有维基百科页面）。"}</div>`;

  // 候选政权切换（地图区域可能对应多个 Wikidata 政权，例如同名的不同时期政权）
  function altSelector(r) {
    if (!r.alternatives || r.alternatives.length < 2) return r.state ? `<div class="s">对应 Wikidata 政权：<a href="https://www.wikidata.org/wiki/${esc(r.state.id)}" target="_blank">${esc(vis(r.state.name, "暂无通用译名"))}</a>${r.state.desc ? `（${esc(r.state.desc)}）` : ""}</div>` : "";
    return `<div class="s">对应 Wikidata 政权：<select class="altsel">${r.alternatives.map((a) => `<option value="${esc(a.id)}" ${r.state && a.id === r.state.id ? "selected" : ""}>${esc(vis(a.name, "暂无通用译名"))}（${esc(a.method_zh)}）</option>`).join("")}</select></div>`;
  }
  function wireAlt(box) {
    const sel = box.querySelector(".altsel");
    if (sel) sel.onchange = () => { WHA.state.stateSel = sel.value; WHA.refreshPanel(); };
  }

  WHA.registerRenderer("leaders", (r, m) => {
    const box = document.createElement("div");
    box.className = "mod-state";
    let h = altSelector(r);
    if (r.territory) {
      const t = r.territory;
      h += `<div class="terr-box"><b>特殊地位：${esc(t.type)}</b>${t.sovereign ? `（主权国：${esc(t.sovereign)}）` : ""}<div class="s">${esc(t.explain)}
        <a href="${esc(t.url)}" target="_blank" rel="noopener">说明来源</a></div>` +
        (t.geom_note ? `<div class="s">${esc(t.geom_note)}</div>` : "") +
        (t.history?.length ? `<div class="s">地位变化（Wikidata）：${t.history.map((x) => `${esc(x.name)} ${span(x.from, x.to)}`).join("；")}</div>` : "") + `</div>`;
    }
    if (r.claim) h += `<div class="claim-box"><b>声索与实控</b><div class="s">${esc(r.claim)}</div></div>`;
    if (r.curated_offices?.length) h += `<h4>核对过的职务</h4>` + r.curated_offices.map((x) => `<div class="item"><div class="t">${esc(x.role)}：${esc(x.name)}</div><div class="d">${esc(x.span)}</div><div class="s">${esc(x.note)}</div><div class="src"><a href="${esc(x.src)}" target="_blank" rel="noopener">来源</a></div></div>`).join("");
    if (r.state_note) h += `<div class="note">${esc(r.state_note)}</div>`;
    if (r.merged?.length) h += `<div class="note">同一国家在 Wikidata 中还有以下条目（同名或当时首都相同），其记录一并显示：${r.merged.map((x) => esc(x.name)).join("、")}</div>`;
    // 空位期 / 共治 / 摄政 / 权臣 / 对立君主：该时期实际掌权的人（按本官列出，带角色标签）
    const IP = (p) => p.known ? P(p) : (p.id ? `<a href="https://www.wikidata.org/wiki/${esc(p.id)}" target="_blank" rel="noopener">${esc(p.name)}</a>` : esc(p.name));
    const IL = (l) => `<div class="d"><span class="itag">${esc(l.tag)}</span> ${IP(l.person)}：${esc(l.office)}${l.from || l.to ? ` <small>（${l.from ? esc(l.from) + "起" : ""}${l.to ? (l.from ? "，" : "") + "至" + esc(l.to) : ""}）</small>` : ""}${l.note ? `<div class="s">${esc(l.note)}</div>` : ""}</div>`;
    if (r.interregna?.length) h += r.interregna.map((c) => `<div class="item inter-box"><h4>实际掌权者 · ${esc(c.kind)}</h4><div class="t">${esc(c.title)}</div>
      ${c.nominal ? `<div class="s">名义上的君主：${esc(c.nominal)}</div>` : ""}${c.leaders.map(IL).join("")}
      <div class="note">${esc(c.note)}</div>
      ${c.alt ? `<div class="inter-alt"><b>${esc(c.alt.title)}</b>${c.alt.leaders.map(IL).join("")}<div class="note">${esc(c.alt.note)}</div></div>` : ""}
      <div class="src">来源：${c.src.map((u) => u.startsWith("http") ? `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(decodeURIComponent(u.split("/wiki/")[1] || u).replace(/_/g, " "))}</a>` : esc(u)).join("；")}</div></div>`).join("");
    if (r.regents?.length) h += `<h4>摄政 / 辅政</h4>` + r.regents.map((x) => `<div class="s">${P(x.person)}：${esc(x.role)} <small><a href="${esc((x.src || "").split("（")[0])}" target="_blank" rel="noopener">来源</a></small></div>`).join("");
    if (r.eras?.length) h += `<h4>年号</h4>` + r.eras.map((e) => `<span class="chip" title="${esc(e.ruler ? e.ruler + " 的年号" : "")}">${esc(e.name)} <small>${span(e.from, e.to)}</small></span>`).join(" ") +
      (r.eras.some((e) => e.src) ? `<div class="src">年号：<a href="https://en.wikipedia.org/wiki/List_of_Chinese_era_names" target="_blank" rel="noopener">English Wikipedia「List of Chinese era names」</a></div>` : "");
    if (r.heads?.length) {
      h += `<h4>元首与政府首脑</h4>` + r.heads.map((x) => `<div class="item"><div class="t">${esc(x.role)}：${P(x.person)}${x.src ? ` <small>（条目：${esc(x.src)}）</small>` : ""}</div>
        <div class="d">任期 ${span(x.from, x.to)}${x.to ? "" : "（未记录卸任时间）"}${x.note ? `（${esc(x.note)}）` : ""}</div>${x.person?.desc ? `<div class="s">${esc(x.person.desc)}</div>` : ""}</div>`).join("");
    }
    if (r.offices?.length) {
      h += `<h4>君主与重要职位（点职位看机构介绍）</h4>` + r.offices.map((o) => `<div class="item"><div class="t">${O(o.office)}${o.virtual && o.juris ? ` <small>（${esc(o.juris)}）</small>` : (o.src ? ` <small>（条目：${esc(o.src)}）</small>` : "")}</div>
        ${o.holders.map((x) => `<div class="d">${P(x.person)} · ${span(x.from, x.to)}${x.to ? (x.to_note ? `<small>（卸任时间取自${esc(x.to_note)}）</small>` : "") : "（未记录卸任时间）"}</div>` +
          (x.legend ? `<div class="note">${esc(x.legend)}</div>` : "")).join("")}</div>`).join("");
    }
    if (!r.heads?.length && !r.offices?.length && !r.interregna?.length && !r.curated_offices?.length) h += `<div class="empty">没有找到所选日期的任职记录。</div>`;
    if (r.undated_offices?.length) h += `<h4>任期未记录的职位</h4><div class="note">以下职位在 Wikidata 中有任职者，但多数没有记录任期，无法判断所选日期谁在任（点开可看历任者）：</div>` +
      r.undated_offices.map((o) => `<span class="chip">${O(o)} <small>${o.n}人</small></span>`).join(" ");
    h += r.note ? `<div class="note">${esc(r.note)}</div>` : "";
    h += `<div class="source">来源：${esc(m.source)}</div>`;
    box.innerHTML = h;
    wire(box); wireAlt(box);
    return box;
  });

  WHA.registerRenderer("regime", (r, m) => {
    const box = document.createElement("div");
    box.className = "mod-state";
    let h = altSelector(r);
    const s = r.state;
    if (r.geom_note) h += `<div class="note">${esc(r.geom_note)}</div>`;
    if (r.claim) h += `<div class="claim-box"><b>声索与实控</b><div class="s">${esc(r.claim)}</div></div>`;
    if (s) {
      h += `<div class="regime-head">${s.flag ? `<img class="flag" src="${esc(s.flag)}" alt="国旗">` : ""}<div><b>${esc(s.name)}</b>${s.en && s.en !== s.name ? ` <span class="en">${esc(s.en)}</span>` : ""}
        <div class="d">存在：${span(s.from, s.to) || "未记录"}</div>
        ${r.chain?.now?.length ? `<div class="d regime-now">所选日期的政权：<b>${r.chain.now.map(esc).join("；")}</b></div>` : ""}
        <div class="d flag-note">${s.flag ? (s.flag_dated ? "国旗：所选日期有效（Wikidata P41 起止限定" + (s.flag_note ? "；" + esc(s.flag_note) : "") + "）" : "国旗：Wikidata 未注明使用时间") : "国旗：" + esc(s.flag_note || "未记录")}</div></div></div>`;
      if (r.chain?.rows?.length) {
        h += `<details class="regime-chain"${r.chain.now.length ? " open" : ""}><summary>${esc(r.chain.country)}政权更替（1800 年至今，含并立政权）</summary><table class="kv chain">` +
          r.chain.rows.map((x) => `<tr class="${x.current ? "cur" : ""}"><th>${esc(x.from)}${x.to ? " – " + esc(x.to) : " 至今"}</th><td>${x.current ? "▶ " : ""}<a href="${esc(x.src)}" target="_blank" rel="noopener">${esc(x.zh)}</a>${x.parallel ? ' <span class="badge country">并立</span>' : ""}${x.note ? `<small>（${esc(x.note)}）</small>` : ""}</td></tr>`).join("") +
          `</table><div class="src">日期来源：各行链接的英文维基百科条目</div></details>`;
      }
      if (r.definition) h += `<div class="def">${esc(r.definition)}<div class="src">——<a href="${esc(r.definition_src.url)}" target="_blank" rel="noopener">${r.definition_src.lang === "zh" ? "中文维基百科" : "English Wikipedia"}「${esc(r.definition_src.title)}」</a>首句</div></div>`;
      const terms = (l) => l.map((x) => `<a href="https://www.wikidata.org/wiki/${esc(x.id)}" target="_blank">${esc(x.name)}</a>`).join("、");
      h += `<table class="kv">
        <tr><th>政体</th><td>${r.gov_note ? esc(r.gov_note) : (r.gov_from ? `<small>（取自「${esc(r.gov_from)}」条目）</small>` : "") + (r.gov.length ? terms(r.gov) : r.gov_undated.length ? terms(r.gov_undated) + ' <span class="badge country" title="Wikidata 未注明适用时间">未注明时间</span>' : "—")}</td></tr>
        <tr><th>执政党</th><td>${r.parties.length ? r.parties.map((x) => `${esc(x.party)}（${esc(x.role)} ${P(x.person)} 所属${x.dated ? "" : '，<span class="badge country">未注明时间</span>'}）`).join("<br>") : "—"}</td></tr>
        <tr><th>意识形态</th><td>${r.ideology_from && r.ideology.length ? `<small>（取自「${esc(r.ideology_from)}」条目）</small>` : ""}${r.ideology.length ? terms(r.ideology) : "—"}</td></tr>
        <tr><th>首都</th><td>${r.capital.length ? r.capital.map(esc).join("、") : "—"}</td></tr>
        <tr><th>所属阵营</th><td>${r.blocs.length ? r.blocs.map(B).join("、") : "—"}</td></tr></table>`;
      const links = [{ label: "Wikidata", url: `https://www.wikidata.org/wiki/${s.id}` }];
      if (s.zhwiki) links.push({ label: "中文维基", url: `https://zh.wikipedia.org/wiki/${encodeURIComponent(s.zhwiki)}` });
      if (s.enwiki) links.push({ label: "English Wikipedia", url: `https://en.wikipedia.org/wiki/${encodeURIComponent(s.enwiki.replace(/ /g, "_"))}` });
      h += `<div class="l">${links.map(link).join("")}</div>`;
    }
    h += r.note ? `<div class="note">${esc(r.note)}</div>` : "";
    h += `<div class="source">来源：${esc(m.source)}</div>`;
    box.innerHTML = h;
    wire(box); wireAlt(box);
    return box;
  });

  // 「国家精神」：当时生效的同盟与条约卡片
  WHA.registerRenderer("spirits", (r, m) => {
    const box = document.createElement("div");
    box.className = "mod-state";
    let h = altSelector(r);
    if (r.matched?.length) h += `<div class="s">按以下政权查找签署记录：${r.matched.map((x) => esc(x.name)).join("、")}</div>`;
    const card = (c) => `<div class="spirit k-${esc(c.kind)}" data-treaty="${esc(c.id)}"><div><span class="k">${esc(c.kind)}</span><b>${esc(c.name)}</b></div>
      <div class="d">${esc(c.from)}${c.to ? " – " + esc(c.to) : ""} · ${c.n_parties} 方${c.via && r.matched.length > 1 ? ` · 经「${esc(c.via)}」` : ""}</div>
      <div class="d">${c.parties.slice(0, 5).map(esc).join("、")}${c.n_parties > 5 ? " 等" : ""}</div>
      ${c.status_zh ? `<div class="d">${esc(c.status_zh)}</div>` : ""}${c.role ? `<div class="d">${esc(c.role)}</div>` : ""}</div>`;
    if (r.blocs?.length) h += `<h4>同盟 / 阵营</h4><div class="spirit-cards">${r.blocs.map((b) => `<div class="spirit k-同盟" data-bloc="${esc(b.id)}"><div><span class="k">同盟</span><b>${esc(b.name)}</b></div><div class="d">当时 ${b.n} 个成员${b.no_end ? " · 无解散记录" : ""}</div></div>`).join("")}</div>`;
    if (r.pending?.length) h += `<h4>已签署，尚未生效</h4><div class="spirit-cards">${r.pending.map(card).join("")}</div>`;
    if (r.unratified?.length) h += `<h4>已签署，未批准，不作为生效条约</h4><div class="spirit-cards">${r.unratified.map(card).join("")}</div>`;
    if (r.implemented?.length) h += `<h4>已签署并公布实施，没有议会批准</h4><div class="spirit-cards">${r.implemented.map(card).join("")}</div>`;
    if (r.dated?.length) h += `<h4>有效期内的条约（${r.n_dated}）</h4><div class="spirit-cards">${r.dated.map(card).join("")}</div>`;
    if (r.open?.length) h += `<h4>已签订、未记录终止（${r.n_open}${r.n_open > r.open.length ? `，显示 ${r.open.length}` : ""}）</h4><div class="spirit-cards">${r.open.map(card).join("")}</div>`;
    if (!r.total) h += `<div class="empty">Wikidata 中没有找到这一时期该政权签署的条约。</div>`;
    h += r.note ? `<div class="note">${esc(r.note)}</div>` : "";
    h += `<div class="source">来源：${esc(m.source)}</div>`;
    box.innerHTML = h;
    box.querySelectorAll(".spirit[data-treaty]").forEach((el) => (el.onclick = () => WHA.showTreaty(el.dataset.treaty)));
    box.querySelectorAll(".spirit[data-bloc]").forEach((el) => (el.onclick = () => WHA.showBloc(el.dataset.bloc)));
    wireAlt(box);
    return box;
  });

  async function show(url, fn) {
    const body = WHA.openDetail('<div class="empty">加载中…</div>');
    try { body.innerHTML = fn(await WHA.api(url)); wire(body); }
    catch (e) { body.innerHTML = `<div class="empty">加载失败：${esc(e.message)}</div>`; }
  }

  WHA.showPerson = (id) => show(`/api/person/${id}`, (p) => `
    <div class="person">${p.img ? `<img class="portrait" src="${esc(p.img)}" alt="">` : ""}
      <h2>${esc(vis(p.name, "姓名未记录"))}</h2>${p.en && p.en !== p.name ? `<div class="en">${esc(p.en)}</div>` : ""}
      <div class="d">${esc(p.born || "?")} – ${esc(p.died || "")}</div>${p.desc ? `<div class="s">${esc(p.desc)}</div>` : ""}</div>
    ${summaryHtml(p.summary)}
    ${p.party?.length ? `<h4>所属政党</h4>${p.party.map((x) => `<div>${esc(x.name)} ${span(x.from, x.to)}</div>`).join("")}` : ""}
    ${p.positions?.length ? `<h4>担任职务（Wikidata P39）</h4><div class="poslist">${p.positions.map((x) => `<div>${esc(x.name)} <span class="d">${span(x.from, x.to)}</span></div>`).join("")}</div>` : p.online ? "" : '<div class="note">离线：无法获取担任职务列表。</div>'}
    <div class="l">${p.links.map(link).join("")}</div><div class="source">来源：Wikidata（CC0）、维基百科（CC BY-SA）</div>`);

  WHA.showOffice = (id) => show(`/api/office/${id}`, (o) => `
    <h2>${esc(vis(o.name, "职位名称未记录"))}</h2>${o.en && o.en !== o.name ? `<div class="en">${esc(o.en)}</div>` : ""}${o.desc ? `<div class="s">${esc(o.desc)}</div>` : ""}
    <div class="s">管辖：${o.juris.map((x) => esc(x.name)).join("、")}</div>
    ${summaryHtml(o.summary)}
    ${o.orgs.map((g) => `<h4>所领导的机构：${esc(g.name)}</h4>${summaryHtml(g.summary)}`).join("")}
    <h4>历任者（Wikidata 记录 ${o.holders.length} 人次）</h4><div class="poslist">${o.holders.map((x) => `<div>${P(x.person)} <span class="d">${span(x.from, x.to)}</span></div>`).join("")}</div>
    <div class="l">${o.links.map(link).join("")}</div><div class="source">来源：Wikidata（P39 / P1001 / P2389，CC0）、维基百科（CC BY-SA）</div>`);

  WHA.showBloc = (id) => show(`/api/alliance/${id}?date=${WHA.dateParam()}`, (a) => `
    <h2>${esc(vis(a.name, "暂无通用译名"))}</h2>${a.en && a.en !== a.name ? `<div class="en">${esc(a.en)}</div>` : ""}${a.desc ? `<div class="s">${esc(a.desc)}</div>` : ""}
    <div class="d">成立：${esc(a.from || "未记录")} · 解散：${esc(a.to || (a.from ? "未记录（或仍存在）" : "未记录"))}</div>
    ${summaryHtml(a.summary)}
    ${a.leaders.length ? `<h4>领导 / 核心人物（Wikidata 有记录者）</h4>${a.leaders.map((x) => `<div>${esc(x.role)}：${P(x.person)} <span class="d">${span(x.from, x.to)}</span></div>`).join("")}` : '<div class="note">Wikidata 没有记录该阵营的领导人（不作推测）。</div>'}
    <h4>成员（${a.members.length}；加粗 = ${esc(WHA.dateZh())} 时为成员）</h4>
    <table class="kv">${a.members.map((x) => `<tr><td>${x.active ? `<b>${esc(x.name)}</b>` : esc(x.name)}</td><td class="d">${x.periods.map((p) => (p.from || p.to ? `加入 ${esc(p.from || "?")}${p.to ? " · 退出 " + esc(p.to) : ""}` : "未记录加入/退出时间") + ` <small title="数据来源">（${esc(p.via)}）</small>`).join("<br>")}</td></tr>`).join("")}</table>
    ${a.treaties?.length ? `<h4>相关条约</h4>${a.treaties.map(T).join("、")}${a.curated ? '<div class="note">Wikidata 中这个同盟条目与上述条约之间没有链接；关联依据为英文维基百科条目，成员取自条约在 Wikidata 中的签署方/参与方。</div>' : ""}` : ""}
    <div class="l">${a.links.map(link).join("")}</div><div class="source">来源：Wikidata（P527 / P710 / P1891 / P463 及 P580/P582 限定，CC0）、维基百科（CC BY-SA）</div>`);

  WHA.showTreaty = (id) => show(`/api/treaty/${id}`, (t) => `
    <h2>${esc(vis(t.name, "暂无通用译名"))}</h2>${t.en && t.en !== t.name ? `<div class="en">${esc(t.en)}</div>` : ""}${t.desc ? `<div class="s">${esc(t.desc)}</div>` : ""}
    <div class="s">类型：${t.types.map(esc).join("、") || "—"}</div>
    <table class="kv"><tr><th>签订</th><td>${esc(t.signed || "未记录")}</td></tr><tr><th>生效</th><td>${esc(t.effective || "未记录")}</td></tr>
      ${t.status_zh ? `<tr><th>效力</th><td>${esc(t.status_zh)}</td></tr>` : ""}${t.fix_note ? `<tr><th>核对</th><td>${esc(t.fix_note)}</td></tr>` : ""}
      ${t.start ? `<tr><th>开始</th><td>${esc(t.start)}</td></tr>` : ""}<tr><th>终止</th><td>${esc(t.end || "未记录")}</td></tr>
      <tr><th>签订地点</th><td>${esc((t.location || []).map((x) => x.name).join("、") || "未记录")}</td></tr>
      ${t.countries?.length ? `<tr><th>所属国家</th><td>${esc(t.countries.join("、"))}</td></tr>` : ""}</table>
    ${t.name_mt ? '<div class="note">条约名称为机器翻译的「译名」（Wikidata 与维基百科都没有中文名称）。</div>' : ""}
    ${summaryHtml(t.summary)}
    <h4>签署方 / 参与方（${t.parties.length}${t.others ? `；另有 ${t.others} 个签署人或无法对应到政权的签署方` : ""}）</h4>
    <table class="kv">${t.parties.map((p) => `<tr><td>${esc(p.name)}</td><td class="d">${esc(p.via)}${p.rep ? `：${P(p.rep)}` : ""}</td></tr>`).join("") || "<tr><td>Wikidata 没有记录能对应到政权的签署方</td></tr>"}</table>
    <div class="l">${t.links.map(link).join("")}</div>${t.has_text ? "" : '<div class="note">没有找到条约原文链接（维基文库 / Wikidata P953）。</div>'}
    <div class="source">来源：Wikidata（CC0）、维基百科（CC BY-SA）、维基文库</div>`);
})();
