/**
 * 1937-12-10 南京修正后、1949-06-01 南京、1949-12-10 昆明。
 * 用法：node tools/accept/browser_roc_span4.mjs
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

async function openDate(date, lat, lon, zoom, needFront) {
  await page.goto(
    "http://127.0.0.1:8792/?" + Math.random().toString(36).slice(2) +
      `#date=${date}&c=${lat},${lon}&z=${zoom}&layers=roc_provinces&tab=roc_admin`,
    { waitUntil: "domcontentloaded", timeout: 120000 },
  );
  await page.waitForSelector(".leaflet-rocprov-pane path", { timeout: 90000 });
  await page.waitForFunction(() => document.querySelectorAll(".leaflet-rocprov-pane path").length > 10, { timeout: 30000 });
  if (needFront) {
    await page.waitForFunction(() => document.querySelectorAll(".roc-front").length > 0, { timeout: 30000 });
  }
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
  const text = await page.evaluate(() => document.querySelector("#tabBody").innerText);
  const name = await page.evaluate(() => document.querySelector("#polityName").textContent);
  return { text, name };
}

await openDate("1937-12-10", 32.1, 118.9, 7, true);
const a = await clickCity(32.06, 118.8);
if (!a.text.includes("江苏") || !a.text.includes("南京国民政府") || a.name.includes("大日本") || a.name.includes("日军")) {
  problems.push("1937 南京底图或省界不对 " + a.name + " " + a.text.slice(0, 240));
}
await page.screenshot({ path: OUT + "/roc-1937-12-10-nanjing.png" });

await openDate("1949-06-01", 32.1, 118.9, 6, true);
const b = await clickCity(32.06, 118.8);
if (!b.text.includes("江苏") || !b.text.includes("中国共产党")) {
  problems.push("1949-06-01 江苏不是中国共产党 " + b.text.slice(0, 240));
}
await page.screenshot({ path: OUT + "/roc-1949-06-01-nanjing.png" });

await openDate("1949-12-10", 25.0, 102.7, 6, false);
const c = await clickCity(25.0389, 102.7183);
if (!c.text.includes("云南") || !c.text.includes("中国共产党")) {
  problems.push("1949-12-10 云南不是中国共产党 " + c.text.slice(0, 240));
}
await page.screenshot({ path: OUT + "/roc-1949-12-10-kunming.png" });

console.log(problems.length ? "FAIL\n" + problems.join("\n") : "PASS");
await browser.close();
process.exit(problems.length ? 1 : 0);
