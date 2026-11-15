/**
 * 1922-06-01 与 1930-06-01 的中国省界和实控面板。
 * 用法：node tools/accept/browser_batch_next7.mjs
 */
import { createRequire } from "module";
const require = createRequire("/tmp/wha-shot/package.json");
const puppeteer = require("puppeteer-core");

const problems = [];
const OUT = "/opt/cursor/artifacts";
const browser = await puppeteer.launch({
  executablePath: "/usr/local/bin/google-chrome",
  headless: "new",
  args: ["--no-sandbox", "--disable-dev-shm-usage", "--window-size=1440,900"],
  defaultViewport: { width: 1440, height: 900 },
});
const page = await browser.newPage();
page.setDefaultTimeout(40000);

async function mapPoint(lat, lon) {
  return page.evaluate(([lat, lon]) => {
    const r = document.getElementById("map").getBoundingClientRect();
    const p = WHA.map.latLngToContainerPoint([lat, lon]);
    return { x: r.left + p.x, y: r.top + p.y };
  }, [lat, lon]);
}

async function openDate(date) {
  await page.goto(
    "http://127.0.0.1:8792/?" + Math.random().toString(36).slice(2) +
      `#date=${date}&c=35,108&z=4&layers=roc_provinces&tab=roc_admin`,
    { waitUntil: "domcontentloaded", timeout: 120000 },
  );
  await page.waitForSelector(".leaflet-overlay-pane path", { timeout: 90000 });
  await page.waitForFunction(() => document.querySelectorAll(".leaflet-rocprov-pane path").length > 10, { timeout: 30000 });
}

async function clickCity(lat, lon) {
  const pt = await mapPoint(lat, lon);
  await page.mouse.click(pt.x, pt.y);
  await page.waitForFunction(() => {
    const body = document.querySelector("#tabBody");
    return body && body.innerText.includes("名义所属") && !body.innerText.includes("加载中");
  }, { timeout: 30000 });
  return page.evaluate(() => document.querySelector("#tabBody").innerText);
}

await openDate("1922-06-01");
const modern1922 = await page.evaluate(() => document.querySelectorAll(".leaflet-admin1-pane path").length);
if (modern1922 !== 0) problems.push("1922 仍画了今天的省界 " + modern1922);
const taiyuan1922 = await clickCity(37.8706, 112.5489);
if (!taiyuan1922.includes("山西") || !taiyuan1922.includes("晋系")) problems.push("1922 太原面板不是晋系 " + taiyuan1922.slice(0, 180));
await page.screenshot({ path: OUT + "/china-1922-06-01.png" });
const yinchuan = await clickCity(38.4872, 106.2309);
const yinchuanName = await page.evaluate(() => {
  const row = [...document.querySelectorAll("#tabBody tr")].find((tr) => (tr.innerText || "").startsWith("省名"));
  return row ? row.innerText : "";
});
if (!yinchuan.includes("省界待考") || !yinchuanName.includes("省界待考") || yinchuanName.includes("宁夏")) {
  problems.push("1922 银川没有标省界待考 " + yinchuanName + " " + yinchuan.slice(0, 160));
}

await openDate("1930-06-01");
const taiyuan1930 = await clickCity(37.8706, 112.5489);
if (!taiyuan1930.includes("晋系") || !taiyuan1930.includes("南京国民政府")) problems.push("1930 太原面板不对 " + taiyuan1930.slice(0, 180));
await page.screenshot({ path: OUT + "/china-1930-06-01.png" });
const nanjing = await clickCity(32.0603, 118.7969);
if (!nanjing.includes("南京国民政府")) problems.push("1930 南京面板不对 " + nanjing.slice(0, 180));

console.log(problems.length ? "FAIL\n" + problems.join("\n") : "PASS");
await browser.close();
process.exit(problems.length ? 1 : 0);
