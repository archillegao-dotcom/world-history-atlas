/**
 * 1937-12-10 南京、1944-11-15 桂柳、1948-11-15 淮海。
 * 用法：node tools/accept/browser_roc_span3.mjs
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
  await page.waitForFunction(() => document.querySelectorAll(".roc-front").length > 0, { timeout: 30000 });
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

await openDate("1937-12-10", 32.1, 118.9, 7);
const text1937 = await clickCity(32.06, 118.8);
if (!text1937.includes("南京") || !text1937.includes("不是城墙") || !text1937.includes("江苏") || !text1937.includes("南京国民政府")) {
  problems.push("1937 面板没有南京保卫战 " + text1937.slice(0, 500));
}
const labels1937 = await page.evaluate(() => [...document.querySelectorAll(".leaflet-rocprov-pane .zone-label")].map((n) => n.textContent));
if (!labels1937.some((t) => t.includes("南京"))) problems.push("1937 地图没有南京线 " + labels1937.join("|"));
await page.screenshot({ path: OUT + "/roc-1937-12-10-nanjing.png" });

await openDate("1944-11-15", 25.0, 109.6, 6);
const text1944 = await clickCity(25.347, 110.164);
if (!text1944.includes("桂柳") || !text1944.includes("不是省界") || !text1944.includes("桂系")) {
  problems.push("1944 面板没有桂柳 " + text1944.slice(0, 500));
}
const labels1944 = await page.evaluate(() => [...document.querySelectorAll(".leaflet-rocprov-pane .zone-label")].map((n) => n.textContent));
if (!labels1944.some((t) => t.includes("桂柳"))) problems.push("1944 地图没有桂柳线 " + labels1944.join("|"));
await page.screenshot({ path: OUT + "/roc-1944-11-15-guiliu.png" });

await openDate("1948-11-15", 33.6, 116.6, 6);
const text1948 = await clickCity(34.302, 117.257);
if (!text1948.includes("淮海") || !text1948.includes("不是省界") || !text1948.includes("实控待考")) {
  problems.push("1948 面板没有淮海 " + text1948.slice(0, 500));
}
const labels1948 = await page.evaluate(() => [...document.querySelectorAll(".leaflet-rocprov-pane .zone-label")].map((n) => n.textContent));
if (!labels1948.some((t) => t.includes("淮海"))) problems.push("1948 地图没有淮海线 " + labels1948.join("|"));
await page.screenshot({ path: OUT + "/roc-1948-11-15-huaihai.png" });

console.log(problems.length ? "FAIL\n" + problems.join("\n") : "PASS");
await browser.close();
process.exit(problems.length ? 1 : 0);
