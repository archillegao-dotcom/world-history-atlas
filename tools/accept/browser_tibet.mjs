/**
 * 甘丹颇章与声索样本：桌面和窄屏真实点击。
 * 用法：node tools/accept/browser_tibet.mjs
 */
import { createRequire } from "module";
const require = createRequire("/tmp/wha-shot/package.json");
const puppeteer = require("puppeteer-core");
const problems = [];
const browser = await puppeteer.launch({
  executablePath: "/usr/local/bin/google-chrome",
  headless: "new",
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const page = await browser.newPage();
page.setDefaultTimeout(40000);

async function open(w, h, hash) {
  await page.setViewport({ width: w, height: h, deviceScaleFactor: 1 });
  await page.goto("http://127.0.0.1:8792/?tib=" + Math.random().toString(36).slice(2) + hash, { waitUntil: "networkidle0", timeout: 90000 });
  await page.waitForFunction(() => window.WHA && window.WHA.selectAt, { timeout: 30000 });
  await page.waitForFunction(() => document.querySelector(".leaflet-overlay-pane path"), { timeout: 30000 });
}

async function jump(y, m, d) {
  await page.click("#yearIn", { clickCount: 3 });
  await page.type("#yearIn", String(y));
  await page.select("#monthIn", String(m));
  await page.select("#dayIn", String(d));
  await page.click("#goBtn");
  await page.waitForFunction((yy, mm, dd) => {
    const h = new URLSearchParams(location.hash.slice(1)).get("date") || "";
    return h === `${yy}-${String(mm).padStart(2, "0")}-${String(dd).padStart(2, "0")}`;
  }, { timeout: 25000 }, y, m, d);
  await new Promise((r) => setTimeout(r, 600));
}

async function clickMap(lat, lon, expectName) {
  await page.evaluate((lat, lon) => window.WHA.map.setView([lat, lon], window.WHA.map.getZoom(), { animate: false }), lat, lon);
  await new Promise((r) => setTimeout(r, 400));
  const pt = await page.evaluate((lat, lon) => {
    const q = window.WHA.map.latLngToContainerPoint([lat, lon]);
    const r = document.getElementById("map").getBoundingClientRect();
    return { x: q.x + r.left, y: q.y + r.top };
  }, lat, lon);
  await page.mouse.click(pt.x, pt.y);
  await page.waitForFunction((expectName) => {
    const h = new URLSearchParams(location.hash.slice(1)).get("name") || "";
    const n = document.querySelector("#polityName");
    const body = document.querySelector("#tabBody");
    return h.includes(expectName) && n && n.textContent.trim() && n.textContent.trim() !== "—" && body && !body.textContent.includes("加载中");
  }, { timeout: 25000 }, expectName);
  await new Promise((r) => setTimeout(r, 500));
}

async function tab(label) {
  const box = await page.evaluate((label) => {
    const b = [...document.querySelectorAll("#tabs button")].find((x) => x.textContent.includes(label));
    if (!b) return null;
    b.scrollIntoView({ block: "nearest", inline: "center" });
    const r = b.getBoundingClientRect();
    return { x: r.x + Math.min(r.width / 2, 40), y: r.y + Math.min(r.height / 2, 14) };
  }, label);
  if (!box) { problems.push("没有页签 " + label); return; }
  await page.mouse.click(box.x, box.y);
  await page.waitForFunction(() => {
    const body = document.querySelector("#tabBody");
    return body && !body.textContent.includes("加载中");
  }, { timeout: 20000 });
  await new Promise((r) => setTimeout(r, 300));
}

async function text() {
  return page.evaluate(() => ({
    name: document.querySelector("#polityName").innerText,
    meta: document.querySelector("#polityMeta").innerText,
    body: document.querySelector("#tabBody").innerText,
    flag: !!document.querySelector("#tabBody img.flag"),
    fill: (() => {
      const paths = [...document.querySelectorAll(".leaflet-overlay-pane path.leaflet-interactive")];
      const sel = paths.find((p) => (p.getAttribute("stroke") || "").toLowerCase() === "#e6d3a1");
      return sel ? (sel.getAttribute("fill") || "").toLowerCase() : "";
    })(),
  }));
}

const GRAY = "#7a7368";

function hueOf(fill) {
  const m = /hsl\(\s*([-\d.]+)/i.exec(fill || "");
  return m ? Number(m[1]) : null;
}

await open(1440, 900, "#date=1944-12-01&style=strategy&c=31.2,90.5&z=5");
await clickMap(29.65, 91.117, "Tibet");
await tab("领导人");
let t = await text();
const leaderCount = await page.evaluate(() => {
  const b = [...document.querySelectorAll("#tabs button")].find((x) => x.textContent.includes("领导人"));
  return b ? b.textContent.replace(/\s/g, "") : "";
});
if (!/领导人[1-9]/.test(leaderCount)) problems.push("1944 领导人计数仍是0 " + leaderCount);
if (!t.name.includes("甘丹颇章")) problems.push("1944 标题不是甘丹颇章 " + t.name);
if (!t.body.includes("达扎活佛") || !t.body.includes("尚未亲政") || !t.body.includes("实际掌权者") || !t.body.includes("摄政")) problems.push("1944 领导人名单不对");
if (t.body.includes("毛泽东") || t.body.includes("热振活佛") || t.body.includes("共治")) problems.push("1944 串了别人的职务或写成共治");
if (!t.meta.includes("大致")) problems.push("1944 精度没有写成大致 " + t.meta);
if (t.fill === GRAY) problems.push("1944 拉萨被涂成未核实灰");
const gandenHue = hueOf(t.fill);
const labels1944 = await page.evaluate(() => [...document.querySelectorAll(".strategy-label span")].map((s) => s.textContent));
if (!labels1944.includes("甘丹颇章")) problems.push("1944 地图没有标甘丹颇章 " + labels1944.join("|"));
if (labels1944.includes("西藏")) problems.push("1944 地图仍把这块标成西藏");
await page.screenshot({ path: "/opt/cursor/artifacts/tibet-desktop-1944-leaders.png" });
await clickMap(26.1, 89.8, "India");
const india = await text();
const indiaHue = hueOf(india.fill);
const hueGap = gandenHue == null || indiaHue == null ? 0 : Math.min(Math.abs(gandenHue - indiaHue), 360 - Math.abs(gandenHue - indiaHue));
if (hueGap < 40) problems.push("甘丹与邻接印度色相仍太近 " + gandenHue + " / " + indiaHue);
await clickMap(27.7, 85.32, "Nepal");
const nepal = await text();
const nepalHue = hueOf(nepal.fill);
const nepalGap = gandenHue == null || nepalHue == null ? 0 : Math.min(Math.abs(gandenHue - nepalHue), 360 - Math.abs(gandenHue - nepalHue));
if (nepalGap < 40) problems.push("甘丹与尼泊尔色相仍太近 " + gandenHue + " / " + nepalHue + " " + nepal.name);
await clickMap(29.65, 91.117, "Tibet");
await tab("领导人");
await tab("政权性质");
t = await text();
if (t.flag) problems.push("1944 显示了旗图");
if (!t.body.includes("启用日待考") || !t.body.includes("政教合一")) problems.push("1944 政体或旗帜说明缺失");
if (t.body.includes("绝对专制")) problems.push("1944 仍显示未注明时间的专制译名");

await jump(1951, 5, 23);
await page.evaluate(() => window.WHA.map.setView([31.2, 90.5], 5, { animate: false }));
await clickMap(29.65, 91.117, "Ganden Phodrang");
await tab("政权性质");
t = await text();
if (!t.name.includes("甘丹颇章")) problems.push("协议日标题变了 " + t.name);
if (!t.body.includes("不是1950年10月2日或1951年5月23日")) problems.push("协议日没有写明不是全区变色");
if (t.fill === GRAY) problems.push("协议日拉萨已是灰色");
if (t.body.includes("毛泽东")) problems.push("协议日出现毛泽东");
await page.screenshot({ path: "/opt/cursor/artifacts/tibet-desktop-1951-05-23-lhasa.png" });

await jump(1951, 10, 26);
await page.evaluate(() => window.WHA.map.setView([31.5, 92.5], 5, { animate: false }));
await clickMap(31.14, 97.17, "Chamdo");
await tab("政权性质");
t = await text();
if (!t.body.includes("昌都大致框") || !t.body.includes("不是辖境")) problems.push("10月26日昌都说明不对");
if (t.fill === GRAY) problems.push("昌都框被涂成未核实灰");
const chamdoFill = t.fill;
const labels1026 = await page.evaluate(() => [...document.querySelectorAll(".strategy-label span")].map((s) => s.textContent));
if (!labels1026.includes("昌都大致框")) problems.push("地图没有标昌都大致框 " + labels1026.join("|"));
await clickMap(29.65, 91.117, "unverified");
await tab("政权性质");
t = await text();
if (!t.name.includes("数据不足")) problems.push("10月26日拉萨没有标数据不足 " + t.name);
if (!t.body.includes("不是无人统治")) problems.push("10月26日没有写明不是无人统治");
if (t.fill !== GRAY) problems.push("10月26日拉萨不是灰色 " + t.fill);
if (t.fill && chamdoFill && t.fill === chamdoFill) problems.push("拉萨灰和昌都同色");
if (!t.body.includes("10月26日") || !t.body.includes("都不是全区变色")) problems.push("10月26日没有写明不是全区变色");
if (t.name.includes("中华人民共和国")) problems.push("灰色块标题变成了中华人民共和国");
const labelsGap = await page.evaluate(() => [...document.querySelectorAll(".strategy-label span")].map((s) => s.textContent));
if (!labelsGap.includes("数据不足")) problems.push("灰色块地图没有标数据不足 " + labelsGap.join("|"));
await page.screenshot({ path: "/opt/cursor/artifacts/tibet-desktop-1951-10-26-lhasa.png" });

await open(390, 844, "#date=2000-06-01&style=strategy&c=27.6,91.9&z=7");
await page.waitForFunction(() => document.querySelector(".leaflet-zones-pane path"), { timeout: 20000 });
await page.screenshot({ path: "/opt/cursor/artifacts/tibet-phone-2000-tawang-map.png" });
await clickMap(27.59, 91.86, "India");
t = await text();
if (!t.body.includes("中国声索") || !t.body.includes("实际控制看底图颜色") || !t.body.includes("不是实际边界")) problems.push("2000 达旺声索说明不对");
if (!t.body.includes("不是8月1日整个藏南")) problems.push("2000 达旺没有写明不是整个藏南易手");
const quote = await page.evaluate(() => {
  const el = document.querySelector("#tabBody .def");
  const claim = document.querySelector(".claim-box");
  const lum = (rgb) => {
    const m = String(rgb || "").match(/\d+/g);
    if (!m) return null;
    const [r, g, b] = m.map(Number);
    return (r * 299 + g * 587 + b * 114) / 1000;
  };
  const cs = el ? getComputedStyle(el) : null;
  return {
    def: !!el,
    gap: cs ? Math.abs(lum(cs.color) - lum(cs.backgroundColor)) : 0,
    bare: claim ? /https?:\/\//.test(claim.innerText) : true,
    link: !!(claim && claim.querySelector("a")),
  };
});
if (!quote.def) problems.push("2000 达旺没有政权说明引用");
if (quote.gap < 80) problems.push("2000 达旺引用对比不足 " + quote.gap);
if (quote.bare || !quote.link) problems.push("2000 达旺来源仍是裸网址");
const cover = await page.evaluate(() => {
  const box = document.querySelector(".claim-box") || document.querySelector(".mod-state .note");
  if (!box) return "no-claim";
  box.scrollIntoView({ block: "center" });
  const r = box.getBoundingClientRect();
  const x = Math.min(window.innerWidth - 8, Math.max(8, r.left + 24));
  const y = Math.min(window.innerHeight - 8, Math.max(8, r.top + 28));
  const hit = document.elementFromPoint(x, y);
  const key = document.querySelector("#mapKey");
  const covered = key && (key === hit || key.contains(hit));
  const cs = getComputedStyle(box);
  return { covered, font: cs.fontSize, shown: hit ? hit.closest("#panel") != null : false };
});
if (cover === "no-claim") problems.push("窄屏没有声索或说明");
else {
  if (cover.covered) problems.push("图例盖住声索说明");
  if (parseFloat(cover.font) < 14) problems.push("窄屏字号小于14 " + cover.font);
  if (!cover.shown) problems.push("窄屏点到的不是面板");
}
await page.screenshot({ path: "/opt/cursor/artifacts/tibet-phone-2000-tawang.png" });

await open(390, 844, "#date=1944-12-01&style=strategy&c=31.2,90.5&z=5");
await clickMap(29.65, 91.117, "Tibet");
await tab("领导人");
t = await text();
if (!t.body.includes("实际掌权者") || !t.body.includes("达扎活佛")) problems.push("窄屏领导人名单不对");
const phoneCount = await page.evaluate(() => {
  const b = [...document.querySelectorAll("#tabs button")].find((x) => x.textContent.includes("领导人"));
  return b ? b.textContent.replace(/\s/g, "") : "";
});
if (!/领导人[1-9]/.test(phoneCount)) problems.push("窄屏领导人计数仍是0 " + phoneCount);
await page.screenshot({ path: "/opt/cursor/artifacts/tibet-phone-1944-leaders.png" });

await browser.close();
if (problems.length) {
  console.log("FAIL");
  for (const p of problems) console.log(" -", p);
  process.exit(1);
}
console.log("PASS");
