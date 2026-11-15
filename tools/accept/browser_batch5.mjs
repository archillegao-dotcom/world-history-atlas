/**
 * 第五批浏览器检查：国名落在该多边形内、没有省略号、改日期不重置视角、普通地图仍可切回。
 * 用法：node tools/accept/browser_batch5.mjs
 * 需要本机 Chrome 与已启动的 8792。这是无头浏览器，不是手点。
 */
import { createRequire } from "module";
import { mkdirSync, writeFileSync } from "fs";
const require = createRequire("/tmp/wha-shot/package.json");
const puppeteer = require("puppeteer-core");
mkdirSync("logs", { recursive: true });
const browser = await puppeteer.launch({
  executablePath: "/usr/local/bin/google-chrome",
  headless: "new",
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const page = await browser.newPage();
const problems = [];
async function open(w, h, hash) {
  await page.setViewport({ width: w, height: h, deviceScaleFactor: 1 });
  await page.goto("http://127.0.0.1:8792/?b5=" + Math.random().toString(36).slice(2) + hash, { waitUntil: "networkidle0", timeout: 90000 });
  await page.waitForFunction(() => document.body.classList.contains("strategy") && document.querySelectorAll("#map .strategy-label span").length > 0, { timeout: 30000 });
  await new Promise((r) => setTimeout(r, 500));
}
function labels() {
  return page.evaluate(() => [...document.querySelectorAll("#map .strategy-label span")].map((s) => ({
    t: s.textContent, title: s.getAttribute("title") || "", lat: +s.dataset.lat, lng: +s.dataset.lng,
  })));
}
await open(1440, 900, "#date=1944-12-01&style=strategy&c=48,8&z=4");
const eu = await labels();
const soviet = eu.find((x) => x.t === "苏联" || x.title === "苏联");
if (!soviet) problems.push("欧洲画面没有苏联");
else if (soviet.lng < 20) problems.push("苏联仍在经度 " + soviet.lng);
const ell = eu.filter((x) => (x.t || "").includes("…"));
if (ell.length) problems.push("欧洲仍有省略号 " + ell.map((x) => x.t).join(","));
const before = await page.evaluate(() => { const c = window.WHA.map.getCenter(); return { z: window.WHA.map.getZoom(), lat: c.lat, lng: c.lng }; });
await page.select("#monthIn", "6");
await new Promise((r) => setTimeout(r, 1200));
const after = await page.evaluate(() => { const c = window.WHA.map.getCenter(); return { z: window.WHA.map.getZoom(), lat: c.lat, lng: c.lng }; });
if (Math.abs(before.z - after.z) > 0.01 || Math.abs(before.lat - after.lat) > 0.05 || Math.abs(before.lng - after.lng) > 0.05) problems.push("改日期重置了视角");
await page.click("#styleBtn");
await new Promise((r) => setTimeout(r, 300));
const normal = await page.evaluate(() => !document.body.classList.contains("strategy") && document.querySelector("#styleBtn").textContent.includes("策略"));
if (!normal) problems.push("普通地图切不回去");
await open(390, 844, "#date=1944-12-01&style=strategy&c=32,114&z=4");
const narrow = await page.evaluate(() => ({
  scroll: document.documentElement.scrollWidth, w: window.innerWidth,
  mapH: document.querySelector("#map").getBoundingClientRect().height,
  barH: document.querySelector("#topbar").getBoundingClientRect().height,
  attr: document.querySelector(".leaflet-control-attribution").textContent,
}));
if (narrow.scroll > narrow.w + 1) problems.push("窄屏横向溢出 " + narrow.scroll);
if (!narrow.attr.includes("historical-basemaps") || !narrow.attr.includes("Wikidata")) problems.push("署名不完整");
const asia = await labels();
const jp = asia.find((x) => x.t === "大日本帝国");
if (jp && jp.lng < 122) problems.push("大日本帝国标到经度 " + jp.lng);
writeFileSync("logs/browser_batch5.json", JSON.stringify({ problems, soviet, narrow, eu: eu.map((x) => x.t), asia: asia.map((x) => x.t) }, null, 2));
console.log(JSON.stringify({ problems, soviet, narrow: { mapH: narrow.mapH, barH: narrow.barH } }));
await browser.close();
process.exit(problems.length ? 1 : 0);
