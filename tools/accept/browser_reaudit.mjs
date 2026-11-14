/**
 * 2026-11-08 综合复验的代表性浏览器冒烟。不是全套历史验收。
 * 用法：node tools/accept/browser_reaudit.mjs
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
  await page.goto("http://127.0.0.1:8792/?reaudit=" + Math.random().toString(36).slice(2) + hash, { waitUntil: "networkidle0", timeout: 90000 });
  await page.waitForFunction(() => window.WHA && window.WHA.map, { timeout: 30000 });
  await page.waitForFunction(() => document.querySelector(".leaflet-overlay-pane path"), { timeout: 30000 });
}

async function mapPoint(lat, lon) {
  return page.evaluate((lat, lon) => {
    const r = document.getElementById("map").getBoundingClientRect();
    const p = window.WHA.map.latLngToContainerPoint([lat, lon]);
    return { x: r.left + p.x, y: r.top + p.y, iw: window.innerWidth, sw: document.documentElement.scrollWidth };
  }, lat, lon);
}

async function tab(label) {
  const box = await page.evaluate((label) => {
    const b = [...document.querySelectorAll("#tabs button")].find((x) => x.textContent.includes(label));
    if (!b) return null;
    const r = b.getBoundingClientRect();
    return { x: r.x + Math.min(r.width / 2, 36), y: r.y + Math.min(r.height / 2, 14), text: b.textContent.replace(/\s/g, "") };
  }, label);
  if (!box) { problems.push("没有页签 " + label); return ""; }
  await page.mouse.click(box.x, box.y);
  await page.waitForFunction(() => {
    const body = document.querySelector("#tabBody");
    return body && !body.textContent.includes("加载中");
  }, { timeout: 20000 });
  await new Promise((r) => setTimeout(r, 300));
  return box.text;
}

const OUT = "/opt/cursor/artifacts";

await open(1440, 900, "#date=1944-12-01&style=strategy&c=48,8&z=4");
await page.click("#eraToggle");
await new Promise((r) => setTimeout(r, 200));
let style = await page.evaluate(() => ({
  strategy: document.body.classList.contains("strategy"),
  btn: document.getElementById("styleBtn").innerText,
  note: document.getElementById("eraNote").innerText,
}));
if (!style.strategy || style.btn !== "普通地图") problems.push("打开时不是策略地图 " + style.btn);
if (!style.note.includes("不是历史省界") || !style.note.includes("不是 TNO")) problems.push("策略说明没有写明不是历史省界或不是 TNO " + style.note.slice(0, 120));
await page.screenshot({ path: OUT + "/reaudit-desktop-1944-strategy.png" });

await page.click("#styleBtn");
await new Promise((r) => setTimeout(r, 500));
style = await page.evaluate(() => ({
  strategy: document.body.classList.contains("strategy"),
  btn: document.getElementById("styleBtn").innerText,
}));
if (style.strategy || !style.btn.includes("策略")) problems.push("没有切回普通地图 " + style.btn);
await page.screenshot({ path: OUT + "/reaudit-desktop-1944-normal.png" });
await page.click("#styleBtn");
await new Promise((r) => setTimeout(r, 400));

const z0 = await page.evaluate(() => window.WHA.map.getZoom());
await page.evaluate(() => window.WHA.map.setView([24.5, 110.5], 6, { animate: false }));
await new Promise((r) => setTimeout(r, 800));
await page.waitForFunction(() => document.querySelectorAll(".leaflet-rocprov-pane path").length > 0, { timeout: 20000 }).catch(() => null);
const zoomed = await page.evaluate(() => ({
  z: window.WHA.map.getZoom(),
  n: document.querySelectorAll(".leaflet-admin1-pane path").length,
  hist: document.querySelectorAll(".leaflet-rocprov-pane path").length,
}));
if (!(zoomed.z > z0)) problems.push("放大没有提高缩放 " + z0 + " -> " + zoomed.z);
if (zoomed.n !== 0) problems.push("放大后仍画了今天的省界 " + zoomed.n);
if (zoomed.hist < 1) problems.push("1944年桂林没有民国省界 " + zoomed.hist);
await page.screenshot({ path: OUT + "/reaudit-desktop-zoom-admin.png" });

await open(390, 844, "#date=1944-12-01&style=strategy&c=32,114&z=4");
const narrow = await page.evaluate(() => ({
  overflow: document.documentElement.scrollWidth > window.innerWidth + 2,
  sw: document.documentElement.scrollWidth,
  iw: window.innerWidth,
}));
if (narrow.overflow) problems.push("窄屏横向溢出 " + narrow.sw + "/" + narrow.iw);
await page.screenshot({ path: OUT + "/reaudit-phone-1944-asia.png" });

await page.$eval("#yearIn", (el) => { el.value = "1950"; });
await page.select("#monthIn", "6");
await page.select("#dayIn", "1");
await page.click("#goBtn");
await page.waitForFunction(() => (location.hash || "").includes("1950-06-01"), { timeout: 20000 });
await page.screenshot({ path: OUT + "/reaudit-phone-date-1950.png" });

await open(1440, 900, "#date=2000-06-01&c=47,2.5&z=5.5");
await page.mouse.move(20, 20);
await new Promise((r) => setTimeout(r, 200));
const paris = await mapPoint(47.0, 2.5);
await page.mouse.move(paris.x, paris.y);
await new Promise((r) => setTimeout(r, 1500));
await page.mouse.move(20, 20);
await new Promise((r) => setTimeout(r, 4000));
const cancelled = await page.evaluate(() => document.getElementById("econHover").classList.contains("on"));
if (cancelled) problems.push("移开后未满 5 秒仍出现经济浮窗");
await page.screenshot({ path: OUT + "/reaudit-hover-cancelled.png" });

await page.mouse.move(paris.x, paris.y);
const t0 = Date.now();
await page.waitForFunction(() => document.getElementById("econHover").classList.contains("on"), { timeout: 8000 });
const elapsed = Date.now() - t0;
if (elapsed < 4500) problems.push("经济浮窗早于约 5 秒 " + elapsed);
await page.waitForFunction(() => /Maddison|暂无数据/.test(document.getElementById("econHover").innerText || ""), { timeout: 8000 });
await page.screenshot({ path: OUT + "/reaudit-hover-shown.png" });
await page.mouse.move(20, 20);
await new Promise((r) => setTimeout(r, 300));
const left = await page.evaluate(() => document.getElementById("econHover").classList.contains("on"));
if (left) problems.push("指针离开后经济浮窗还在");

await page.mouse.move(paris.x, paris.y);
await new Promise((r) => setTimeout(r, 800));
await page.click("#goBtn");
await new Promise((r) => setTimeout(r, 4500));
const afterJump = await page.evaluate(() => document.getElementById("econHover").classList.contains("on"));
if (afterJump) problems.push("改日期没有取消未完成的经济悬停");

await open(1440, 900, "#date=1944-12-01&style=strategy&c=48.8,2.3&z=6");
const pt = await mapPoint(48.86, 2.35);
await page.mouse.click(pt.x, pt.y);
await page.waitForFunction(() => {
  const n = document.querySelector("#polityName");
  return n && n.textContent.includes("临时政府");
}, { timeout: 20000 });
await page.waitForFunction(() => [...document.querySelectorAll("#tabs button")].some((b) => b.textContent.includes("宪法")), { timeout: 20000 });
const constLabel = await tab("宪法");
await page.waitForFunction(() => {
  const body = document.querySelector("#tabBody");
  return body && !body.textContent.includes("加载中");
}, { timeout: 20000 });
const constBody = await page.evaluate(() => document.querySelector("#tabBody").innerText);
if (!constBody.includes("法令")) problems.push("1944 巴黎宪法页没有当月文本 " + constBody.slice(0, 80));
await page.screenshot({ path: OUT + "/reaudit-desktop-1944-paris-constitution.png" });

await open(1440, 900, "#date=1944-12-01&style=strategy&c=31.2,90.5&z=5");
const lh = await mapPoint(29.65, 91.117);
await page.mouse.click(lh.x, lh.y);
await page.waitForFunction(() => (document.querySelector("#polityName") || {}).textContent?.includes("甘丹"), { timeout: 20000 });
await tab("领导人");
const leaders = await page.evaluate(() => {
  const b = [...document.querySelectorAll("#tabs button")].find((x) => x.textContent.includes("领导人"));
  return { count: b ? b.textContent.replace(/\s/g, "") : "", body: document.querySelector("#tabBody").innerText };
});
if (!/领导人[1-9]/.test(leaders.count)) problems.push("1944 拉萨领导人计数仍是 0 " + leaders.count);
if (!leaders.body.includes("摄政") || !leaders.body.includes("达扎")) problems.push("1944 拉萨领导人名单不对");
await page.screenshot({ path: OUT + "/reaudit-desktop-1944-lhasa-leaders.png" });

await browser.close();
if (problems.length) {
  console.log("FAIL");
  for (const p of problems) console.log(" -", p);
  process.exit(1);
}
console.log("PASS");
