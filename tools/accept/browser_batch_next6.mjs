/**
 * 1950-06-01 联合国机构树，1927-09-07 国际联盟机构树。
 * 用法：node tools/accept/browser_batch_next6.mjs
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
await page.setViewport({ width: 1100, height: 2200, deviceScaleFactor: 1 });

async function openOrg(date, id) {
  await page.goto(
    "http://127.0.0.1:8792/?" + Math.random().toString(36).slice(2) +
      `#date=${date}&org=${id}&c=48,8&z=4`,
    { waitUntil: "networkidle0", timeout: 120000 },
  );
  await page.waitForFunction(() => (document.querySelector("#diplomacyTree")?.innerText || "").length > 40, { timeout: 30000 });
  return page.evaluate(() => document.querySelector("#diplomacyTree").innerText);
}

const un = await openOrg("1950-06-01", "un");
for (const s of ["大会", "安全理事会", "托管理事会", "国际法院", "秘书处", "联合国教育、科学及文化组织", "专门机构", "无记录"]) {
  if (!un.includes(s)) problems.push("联合国树缺少 " + s);
}
if (un.includes("名单不完整")) problems.push("联合国树不该出现名单不完整");
await page.evaluate(prepareShot);
await (await page.$("#diplomacyTree")).screenshot({ path: OUT + "/un-tree-1950-06-01.png" });

const league = await openOrg("1927-09-07", "league");
for (const s of ["大会", "行政院", "秘书处", "常设国际法院", "国际劳工组织", "Lotus"]) {
  if (!league.includes(s)) problems.push("国联树缺少 " + s);
}
if (league.includes("下属机关") && league.includes("国际劳工组织是国联的下属")) problems.push("劳工组织被写成下属");
await page.evaluate(prepareShot);
await (await page.$("#diplomacyTree")).screenshot({ path: OUT + "/league-tree-1927-09-07.png" });

console.log(problems.length ? "FAIL\n" + problems.join("\n") : "PASS");
await browser.close();
process.exit(problems.length ? 1 : 0);
