/**
 * 1808-07-01 华沙和 2022-03-15 库皮扬斯克的点选截图。不是整套界面回归。
 * 用法：node tools/accept/browser_war_gaps.mjs
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

async function open(hash) {
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
  await page.goto("http://127.0.0.1:8792/?gaps=" + Math.random().toString(36).slice(2) + hash, { waitUntil: "networkidle0", timeout: 90000 });
  await page.waitForFunction(() => window.WHA && window.WHA.map, { timeout: 30000 });
  await page.waitForFunction(() => document.querySelector(".leaflet-overlay-pane path, .leaflet-fronts-pane path"), { timeout: 30000 });
}

async function mapPoint(lat, lon) {
  return page.evaluate((lat, lon) => {
    const r = document.getElementById("map").getBoundingClientRect();
    const p = window.WHA.map.latLngToContainerPoint([lat, lon]);
    return { x: r.left + p.x, y: r.top + p.y };
  }, lat, lon);
}

const OUT = "/opt/cursor/artifacts";

await open("#date=1808-07-01&c=52.23,21.01&z=6");
const warsaw = await mapPoint(52.23, 21.01);
await page.mouse.click(warsaw.x, warsaw.y);
await page.waitForFunction(() => (document.querySelector("#polityName") || {}).textContent?.includes("华沙公国"), { timeout: 20000 });
await page.waitForFunction(() => {
  const body = document.querySelector("#tabBody");
  return body && !body.textContent.includes("加载中") && body.textContent.includes("华沙");
}, { timeout: 20000 });
const warsawText = await page.evaluate(() => document.querySelector("#polityName").textContent + "\n" + document.querySelector("#tabBody").textContent);
if (/Q\d{2,}/.test(warsawText)) problems.push("华沙标题里有裸编号 " + warsawText);
await page.screenshot({ path: OUT + "/warsaw-1808-07-01.png" });

await open("#date=2022-03-15&style=strategy&c=49.71,37.61&z=8");
await page.waitForFunction(() => {
  const box = document.querySelector(".war-legend");
  return box && !box.classList.contains("hidden") && box.innerText.includes("库皮扬斯克");
}, { timeout: 20000 });
const kup = await mapPoint(49.71, 37.61);
await page.mouse.click(kup.x, kup.y);
await page.waitForFunction(() => {
  const n = document.querySelector("#polityName");
  return n && n.textContent && n.textContent.length > 1;
}, { timeout: 20000 });
const legend = await page.evaluate(() => document.querySelector(".war-legend").innerText);
if (!legend.includes("大致范围")) problems.push("库皮扬斯克补充块没有标大致范围");
if (!legend.includes("19")) problems.push("图例没有这块的面积 " + legend.slice(0, 180));
await page.screenshot({ path: OUT + "/kupiansk-2022-03-15.png" });

await browser.close();
if (problems.length) {
  console.log("FAIL");
  for (const p of problems) console.log(" -", p);
  process.exit(1);
}
console.log("PASS");
