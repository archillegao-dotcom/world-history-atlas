/**
 * 1920-07-18 京奉走廊、1924-10-19 山海关一带、1925-06-01 县城待考。
 * 用法：node tools/accept/browser_roc_beiyang.mjs
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

await openDate("1920-07-18", 39.45, 116.9, 7);
const text1920 = await clickCity(39.9042, 116.4074);
if (!text1920.includes("直皖") || !text1920.includes("不是县界") || !text1920.includes("京奉")) {
  problems.push("1920 面板没有走廊说明 " + text1920.slice(0, 240));
}
const fronts1920 = await page.evaluate(() => document.querySelectorAll(".roc-front").length);
const seats1920 = await page.evaluate(() => document.querySelectorAll(".roc-seat").length);
if (fronts1920 < 1) problems.push("1920 没有大致线 " + fronts1920);
if (seats1920 < 4) problems.push("1920 县城点太少 " + seats1920);
await page.screenshot({ path: OUT + "/roc-1920-07-18-jingfeng.png" });

await openDate("1924-10-19", 39.7, 118.5, 6);
const text1924 = await clickCity(39.9042, 116.4074);
if (!text1924.includes("直奉") || !text1924.includes("大致")) {
  problems.push("1924 面板没有直奉大致线 " + text1924.slice(0, 240));
}
const fronts1924 = await page.evaluate(() => document.querySelectorAll(".roc-front").length);
if (fronts1924 < 1) problems.push("1924 没有大致线 " + fronts1924);
await page.screenshot({ path: OUT + "/roc-1924-10-19-jingfeng.png" });

await openDate("1925-06-01", 31.2, 121.2, 7);
const text1925 = await clickCity(31.23, 121.48);
if (!text1925.includes("待考") || !text1925.includes("不是县界")) {
  problems.push("1925 面板没有待考县城 " + text1925.slice(0, 240));
}
if (text1925.includes("孙传芳")) problems.push("1925 把上海写成了孙传芳");
const fronts1925 = await page.evaluate(() => document.querySelectorAll(".roc-front").length);
const seats1925 = await page.evaluate(() => document.querySelectorAll(".roc-seat").length);
if (fronts1925 !== 0) problems.push("1925 还留着战线 " + fronts1925);
if (seats1925 < 3) problems.push("1925 县城点太少 " + seats1925);
await page.screenshot({ path: OUT + "/roc-1925-06-01-counties.png" });

console.log(problems.length ? "FAIL\n" + problems.join("\n") : "PASS");
await browser.close();
process.exit(problems.length ? 1 : 0);
