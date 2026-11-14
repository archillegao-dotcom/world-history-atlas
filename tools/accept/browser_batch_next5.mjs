/**
 * 1935-06-01 国际联盟面板，1972-06-01 联合国面板。
 * 用法：node tools/accept/browser_batch_next5.mjs
 */
import { createRequire } from "module";
const require = createRequire("/tmp/wha-shot/package.json");
const puppeteer = require("puppeteer-core");
function prepareShot() {
  const bar = document.querySelector("#topbar");
  const line = document.querySelector("#timeline");
  if (bar) bar.style.visibility = "hidden";
  if (line) line.style.visibility = "hidden";
  const modal = document.querySelector("#detail");
  if (modal) {
    modal.style.alignItems = "flex-start";
    modal.style.paddingTop = "12px";
  }
  const b = document.querySelector("#detailBody");
  b.style.maxHeight = "none";
  b.style.overflow = "visible";
}

const problems = [];
const OUT = "/opt/cursor/artifacts";

const browser = await puppeteer.launch({
  executablePath: "/usr/local/bin/google-chrome",
  headless: "new",
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const page = await browser.newPage();
page.setDefaultTimeout(40000);
await page.setViewport({ width: 1100, height: 2600, deviceScaleFactor: 1 });

async function openOrg(date, id) {
  await page.goto(
    "http://127.0.0.1:8792/?" + Math.random().toString(36).slice(2) +
      `#date=${date}&org=${id}&c=48,8&z=4`,
    { waitUntil: "networkidle0", timeout: 120000 },
  );
  await page.waitForFunction(() => (document.querySelector("#detailBody")?.innerText || "").length > 80, { timeout: 30000 });
  return page.evaluate(() => document.querySelector("#detailBody").innerText);
}

const league = await openOrg("1935-06-01", "league");
if (!league.includes("国际联盟")) problems.push("没有国际联盟标题");
if (league.includes("名单不完整")) problems.push("国联名册已写全，不应再标名单不完整");
if (!league.includes("中华民国")) problems.push("国联没有中国");
if (!league.includes("已宣布退出，通知期未满")) problems.push("德国资格不对");
if (!league.includes("大日本帝国")) problems.push("日本没有用当时国号");
if (!league.includes("德意志国")) problems.push("德国没有用当时国号");
if (!league.includes("已退出")) problems.push("日本退出没有写在面板上");
await page.evaluate(prepareShot);
await (await page.$("#detailBody")).screenshot({ path: OUT + "/league-1935-06-01.png" });

const un = await openOrg("1972-06-01", "un");
if (!un.includes("联合国")) problems.push("没有联合国标题");
if (!un.includes("中华人民共和国")) problems.push("1972 没有中华人民共和国");
if (!un.includes("中国席位")) problems.push("没有中国席位");
if (!un.includes("不再持有这一席位")) problems.push("中华民国的席位变化没有写");
if (!un.includes("2758")) problems.push("没有第2758号决议");
if (un.includes("名单不完整")) problems.push("联合国名册已写全，不应再标名单不完整");
if (!un.includes("中华民国")) problems.push("1972 没有写出中华民国");
await page.evaluate(prepareShot);
await (await page.$("#detailBody")).screenshot({ path: OUT + "/un-1972-06-01.png" });

console.log(problems.length ? "FAIL\n" + problems.join("\n") : "PASS");
await browser.close();
process.exit(problems.length ? 1 : 0);
