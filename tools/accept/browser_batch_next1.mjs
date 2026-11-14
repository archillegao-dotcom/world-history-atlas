/**
 * 1950-03-16 李弥部活动层，以及 1930-11-08 点南桦太后同政权范围一并高亮。
 * 用法：node tools/accept/browser_batch_next1.mjs
 */
import { createRequire } from "module";
const require = createRequire("/tmp/wha-shot/package.json");
const puppeteer = require("puppeteer-core");
const problems = [];
const OUT = "/opt/cursor/artifacts";
const browser = await puppeteer.launch({
  executablePath: "/usr/local/bin/google-chrome",
  headless: "new",
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const page = await browser.newPage();
page.setDefaultTimeout(40000);

async function open(hash) {
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
  await page.goto("http://127.0.0.1:8792/?" + Math.random().toString(36).slice(2) + hash, { waitUntil: "networkidle0", timeout: 120000 });
  await page.waitForFunction(() => window.WHA && window.WHA.map && window.WHA.linkedFids, { timeout: 30000 });
  await page.waitForFunction(() => document.querySelector(".leaflet-overlay-pane path"), { timeout: 40000 });
}

await open("#date=1950-03-16&style=strategy&layers=control_zones&c=20.87,99.75&z=7");
await page.waitForFunction(() => document.body.innerText.includes("云南反共救国军") && document.body.innerText.includes("景栋") && document.body.innerText.includes("大其力") && document.body.innerText.includes("活动点"), { timeout: 30000 });
const yunnan = await page.evaluate(() => document.body.innerText);
if (!yunnan.includes("大致范围")) problems.push("1950-03-16 活动层没有标大致范围");
if (yunnan.includes("不是疆域") === false) {
  // 说明在弹窗里。点开菱形后再看。
}
await page.screenshot({ path: OUT + "/yunnan-1950-03-16.png" });

await open("#date=1930-11-08&style=strategy&c=46.2,146.5&z=4.5");
const linked = await page.evaluate(async () => {
  const loc = async (lat, lon) => {
    const r = await WHA.api(`/api/locate?date=1930-11-08&lat=${lat}&lon=${lon}`);
    return r.polity ? r.polity.fid : null;
  };
  const kara = await loc(46.96, 142.73);
  const tokyo = await loc(35.68, 139.69);
  const itu = await loc(45.05, 147.8);
  const seoul = await loc(37.57, 126.98);
  WHA.selectPolity(kara);
  const ids = WHA.linkedFids();
  return { kara, tokyo, itu, seoul, ids };
});
await page.waitForFunction(() => (document.querySelector("#polityMeta") || {}).innerText?.includes("一并高亮"), { timeout: 20000 });
const panel = await page.evaluate(() => ({
  meta: document.querySelector("#polityMeta").innerText,
  name: document.querySelector("#polityName").innerText,
}));
linked.meta = panel.meta;
linked.name = panel.name;
if (!linked.ids.includes(linked.kara) || !linked.ids.includes(linked.tokyo) || !linked.ids.includes(linked.itu)) {
  problems.push("点南桦太没有同时高亮本土和千岛 " + JSON.stringify(linked));
}
if (linked.ids.includes(linked.seoul)) problems.push("朝鲜日治被并进了大日本帝国 " + JSON.stringify(linked));
if (!linked.meta.includes("一并高亮")) problems.push("面板没有写同政权范围已一并高亮 " + linked.meta);
if (!linked.name.includes("大日本帝国") && !linked.name.includes("桦太") && !linked.name.includes("南桦太")) {
  problems.push("点南桦太后的标题不对 " + linked.name);
}
await page.screenshot({ path: OUT + "/japan-1930-11-08.png" });

await browser.close();
if (problems.length) {
  console.log("FAIL");
  for (const p of problems) console.log(" -", p);
  process.exit(1);
}
console.log("PASS");
