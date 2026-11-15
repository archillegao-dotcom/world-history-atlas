/**
 * 2020-06-01 克里米亚：战争前线填色是实控，虚线是乌克兰声索，面板分三行。
 * 用法：node tools/accept/browser_batch_next2.mjs
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
await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
await page.goto("http://127.0.0.1:8792/?" + Math.random().toString(36).slice(2) +
  "#date=2020-06-01&style=strategy&layers=status_layers,war_fronts&c=45.05,33.15&z=7",
  { waitUntil: "networkidle0", timeout: 120000 });
await page.waitForFunction(() => window.WHA && window.WHA.selectAt, { timeout: 30000 });
await page.evaluate(() => WHA.selectAt(44.95, 34.1));
await page.waitForFunction(() => {
  const t = document.querySelector("#polityMeta")?.innerText || "";
  return t.includes("实际控制") && t.includes("主权声索") && t.includes("国际承认") && t.includes("乌克兰") && t.includes("68/262");
}, { timeout: 30000 });
const text = await page.evaluate(() => ({
  meta: document.querySelector("#polityMeta").innerText,
  name: document.querySelector("#polityName").innerText,
  body: document.body.innerText,
}));
if (!text.name.includes("俄罗斯")) problems.push("面板标题不是俄罗斯：" + text.name);
if (!text.meta.includes("俄罗斯")) problems.push("实控行没有俄罗斯");
if (text.meta.includes("ES-11/4")) problems.push("2020 年面板混入了 2022 年的决议");
if (!text.body.includes("乌克兰主权声索")) problems.push("地图上没有乌克兰声索标注");
await page.screenshot({ path: OUT + "/crimea-2020-06-01.png" });
console.log(problems.length ? "FAIL\n" + problems.join("\n") : "PASS");
await browser.close();
process.exit(problems.length ? 1 : 0);
