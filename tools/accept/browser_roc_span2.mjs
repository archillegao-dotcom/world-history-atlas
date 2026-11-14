/**
 * 1931-11-19 东北进占、1938-10-01 武汉前线、1936-10-09 会宁。
 * 用法：node tools/accept/browser_roc_span2.mjs
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

await openDate("1931-11-19", 44.2, 125.2, 5);
const text1931 = await clickCity(41.794, 123.447);
if (!text1931.includes("九一八") || !text1931.includes("不是县界") || !text1931.includes("辽宁") || !text1931.includes("实控待考")) {
  problems.push("1931 面板没有进占线 " + text1931.slice(0, 400));
}
const labels1931 = await page.evaluate(() => [...document.querySelectorAll(".leaflet-rocprov-pane .zone-label")].map((n) => n.textContent));
if (!labels1931.some((t) => t.includes("沈阳") || t.includes("龙江"))) problems.push("1931 地图没有东北线 " + labels1931.join("|"));
await page.screenshot({ path: OUT + "/roc-1931-11-19-dongbei.png" });

await openDate("1938-10-01", 31.2, 114.6, 6);
const text1938 = await clickCity(30.524, 114.276);
if (!text1938.includes("武汉") || !text1938.includes("不是省界")) {
  problems.push("1938 面板没有武汉前线 " + text1938.slice(0, 400));
}
const labels1938 = await page.evaluate(() => [...document.querySelectorAll(".leaflet-rocprov-pane .zone-label")].map((n) => n.textContent));
if (!labels1938.some((t) => t.includes("武汉"))) problems.push("1938 地图没有武汉线");
await page.screenshot({ path: OUT + "/roc-1938-10-01-wuhan.png" });

await openDate("1936-10-09", 34.8, 104.8, 6);
const text1936 = await clickCity(35.696, 104.859);
if (!text1936.includes("会宁") || !text1936.includes("红四")) {
  problems.push("1936 面板没有会宁 " + text1936.slice(0, 400));
}
await page.screenshot({ path: OUT + "/roc-1936-10-09-huining.png" });

console.log(problems.length ? "FAIL\n" + problems.join("\n") : "PASS");
await browser.close();
process.exit(problems.length ? 1 : 0);
