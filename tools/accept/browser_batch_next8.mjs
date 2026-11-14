/**
 * 1950-06-27 安理会第83号决议，1986-06-27 尼加拉瓜案判决。
 * 用法：node tools/accept/browser_batch_next8.mjs
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
await page.setViewport({ width: 1100, height: 1400, deviceScaleFactor: 1 });

async function openNode(date, nodeId) {
  await page.goto(
    "http://127.0.0.1:8792/?" + Math.random().toString(36).slice(2) +
      `#date=${date}&org=un&c=40,20&z=3`,
    { waitUntil: "networkidle0", timeout: 120000 },
  );
  await page.waitForSelector("#diplomacyTree", { timeout: 30000 });
  const node = await page.$(`[data-node="${nodeId}"]`);
  if (!node) {
    problems.push(date + " 没有节点 " + nodeId);
    return;
  }
  await node.click();
  await page.waitForFunction(
    (id) => {
      const el = document.querySelector(`[data-node="${id}"] .node-acts`);
      return el && el.style.display === "block" && (el.innerText || "").length > 8;
    },
    { timeout: 10000 },
    nodeId,
  );
  await page.evaluate((id) => {
    const el = document.querySelector(`[data-node="${id}"]`);
    el.scrollIntoView({ block: "center" });
  }, nodeId);
  await page.screenshot({ path: `${OUT}/node-${date}-${nodeId}.png` });
  return page.evaluate((id) => document.querySelector(`[data-node="${id}"]`).innerText, nodeId);
}

const sc = await openNode("1950-06-27", "sc") || "";
if (!sc.includes("第83（1950）号决议")) problems.push("截图文本没有第83号决议");
if (!sc.includes("Korea")) problems.push("截图文本没有韩国议题");
const icj = await openNode("1986-06-27", "icj") || "";
if (!icj.includes("Nicaragua")) problems.push("截图文本没有尼加拉瓜案");
if (!icj.includes("27 June 1986")) problems.push("截图文本没有1986年6月27日");

console.log(problems.length ? "FAIL\n" + problems.join("\n") : "PASS");
await browser.close();
process.exit(problems.length ? 1 : 0);
