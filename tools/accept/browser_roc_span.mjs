/**
 * 1926-10-10 北伐三路、1930-09-01 中原大战、1935-06-01 长征。
 * 用法：node tools/accept/browser_roc_span.mjs
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

await openDate("1926-10-10", 27.2, 115.2, 5);
const text1926 = await clickCity(30.524, 114.276);
if (!text1926.includes("北伐") || !text1926.includes("两湖") || !text1926.includes("不是县界")) {
  problems.push("1926 面板没有三路 " + text1926.slice(0, 360));
}
const labels1926 = await page.evaluate(() => [...document.querySelectorAll(".leaflet-rocprov-pane .zone-label")].map((n) => n.textContent));
for (const word of ["两湖", "江西", "福建"]) {
  if (!labels1926.some((t) => t.includes(word))) problems.push("1926 地图没有 " + word);
}
await page.screenshot({ path: OUT + "/roc-1926-10-10-beifa.png" });

await openDate("1930-09-01", 35.0, 115.4, 6);
const text1930 = await clickCity(34.745, 113.67);
if (!text1930.includes("中原") || !text1930.includes("陇海") || !text1930.includes("平汉") || !text1930.includes("津浦")) {
  problems.push("1930 面板没有三条铁路 " + text1930.slice(0, 360));
}
if (text1930.includes("桂军入湘")) problems.push("1930-09 不该还有桂军入湘");
await page.screenshot({ path: OUT + "/roc-1930-09-01-zhongyuan.png" });

await openDate("1935-06-01", 30.5, 108.0, 4);
const text1935 = await clickCity(27.698, 106.902);
if (!text1935.includes("长征") || !text1935.includes("不是辖境")) {
  problems.push("1935 面板没有长征 " + text1935.slice(0, 360));
}
const labels1935 = await page.evaluate(() => [...document.querySelectorAll(".leaflet-rocprov-pane .zone-label")].map((n) => n.textContent));
if (!labels1935.some((t) => t.includes("长征"))) problems.push("1935 地图没有长征");
await page.screenshot({ path: OUT + "/roc-1935-06-01-longmarch.png" });

console.log(problems.length ? "FAIL\n" + problems.join("\n") : "PASS");
await browser.close();
process.exit(problems.length ? 1 : 0);
