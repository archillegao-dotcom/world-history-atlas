/**
 * 1915-12-25 昆明、1922-05-13 粤汉铁路、1932-02-04 沪宁和沪杭。
 * 用法：node tools/accept/browser_roc_beiyang2.mjs
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

async function openDate(date, lat, lon, zoom) {
  await page.goto(
    "http://127.0.0.1:8792/?" + Math.random().toString(36).slice(2) +
      `#date=${date}&c=${lat},${lon}&z=${zoom}&layers=roc_provinces&tab=roc_admin`,
    { waitUntil: "domcontentloaded", timeout: 120000 },
  );
  await page.waitForSelector(".leaflet-rocprov-pane path", { timeout: 90000 });
  await page.waitForFunction(() => document.querySelectorAll(".leaflet-rocprov-pane path").length > 10, { timeout: 30000 });
}

async function clickCity(lat, lon) {
  const pt = await page.evaluate(([lat, lon]) => {
    const r = document.getElementById("map").getBoundingClientRect();
    const p = WHA.map.latLngToContainerPoint([lat, lon]);
    return { x: r.left + p.x, y: r.top + p.y };
  }, [lat, lon]);
  await page.mouse.click(pt.x, pt.y);
  await page.waitForFunction(() => {
    const body = document.querySelector("#tabBody");
    return body && body.innerText.includes("名义所属") && !body.innerText.includes("加载中");
  }, { timeout: 30000 });
  return page.evaluate(() => document.querySelector("#tabBody").innerText);
}

await openDate("1915-12-25", 25.07, 102.7, 6);
const text1915 = await clickCity(25.067, 102.695);
if (!text1915.includes("护国") || !text1915.includes("不是县界") || !text1915.includes("实控待考")) {
  problems.push("1915 面板没有护国县城 " + text1915.slice(0, 280));
}
const fronts1915 = await page.evaluate(() => document.querySelectorAll(".roc-front").length);
const seats1915 = await page.evaluate(() => document.querySelectorAll(".roc-seat").length);
if (fronts1915 !== 0) problems.push("1915 不该有战线 " + fronts1915);
if (seats1915 < 1) problems.push("1915 没有昆明点 " + seats1915);
await page.screenshot({ path: OUT + "/roc-1915-12-25-kunming.png" });

await openDate("1922-05-13", 24.9, 113.9, 6);
const text1922 = await clickCity(25.214, 114.3);
if (!text1922.includes("粤汉") || !text1922.includes("不是县界") || !text1922.includes("实控待考")) {
  problems.push("1922 面板没有粤汉走廊 " + text1922.slice(0, 280));
}
const fronts1922 = await page.evaluate(() => document.querySelectorAll(".roc-front").length);
if (fronts1922 < 1) problems.push("1922 没有大致线 " + fronts1922);
await page.screenshot({ path: OUT + "/roc-1922-05-13-yuehan.png" });

await openDate("1932-02-04", 31.25, 121.05, 7);
const text1932 = await clickCity(31.233, 121.477);
if (!text1932.includes("沪宁") || !text1932.includes("不是县界") || !text1932.includes("南京国民政府")) {
  problems.push("1932 面板没有沪宁 " + text1932.slice(0, 280));
}
const fronts1932 = await page.evaluate(() => document.querySelectorAll(".roc-front").length);
if (fronts1932 < 2) problems.push("1932 铁路不够 " + fronts1932);
await page.screenshot({ path: OUT + "/roc-1932-02-04-shanghai.png" });

console.log(problems.length ? "FAIL\n" + problems.join("\n") : "PASS");
await browser.close();
process.exit(problems.length ? 1 : 0);
