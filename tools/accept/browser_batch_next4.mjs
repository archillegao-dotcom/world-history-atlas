/**
 * 1929-02-11 拉特兰条约显示意大利王国并标注继承。
 * 1970-03-05 不扩散条约摘要不出现 1995；1995-05-12 出现。
 * 用法：node tools/accept/browser_batch_next4.mjs
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

async function openTreaty(date, id) {
  await page.goto(
    "http://127.0.0.1:8792/?" + Math.random().toString(36).slice(2) +
      `#date=${date}&treaty=${encodeURIComponent(id)}&c=41.9,12.48&z=5`,
    { waitUntil: "networkidle0", timeout: 120000 },
  );
  await page.waitForFunction(() => (document.querySelector("#detailBody")?.innerText || "").length > 40, { timeout: 30000 });
  return page.evaluate(() => document.querySelector("#detailBody").innerText);
}

const lateran = await openTreaty("1929-02-11", "Q193270");
if (!lateran.includes("意大利王国（后来由意大利继承）")) problems.push("拉特兰弹窗没有继承标注");
if (/\n意大利（/.test(lateran) || lateran.includes("意大利（签署")) problems.push("拉特兰弹窗仍把共和国列成签署方");
await page.screenshot({ path: OUT + "/lateran-1929-02-11.png" });

const npt = await openTreaty("1970-03-05", "Q186444");
if (npt.includes("1995")) problems.push("1970 年不扩散条约弹窗出现 1995");
await page.screenshot({ path: OUT + "/npt-1970-03-05.png" });

const nptLater = await openTreaty("1995-05-12", "Q186444");
if (!nptLater.includes("1995")) problems.push("1995 年不扩散条约弹窗没有延期");

console.log(problems.length ? "FAIL\n" + problems.join("\n") : "PASS");
await browser.close();
process.exit(problems.length ? 1 : 0);
