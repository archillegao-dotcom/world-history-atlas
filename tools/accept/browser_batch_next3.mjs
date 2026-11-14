/**
 * 1951-03-16 打开 1948 年海上人命安全公约。策略地图下弹窗要能看清，且不出现 1974 或 1980。
 * 用法：node tools/accept/browser_batch_next3.mjs
 */
import { createRequire } from "module";
const require = createRequire("/tmp/wha-shot/package.json");
const puppeteer = require("puppeteer-core");
const problems = [];
const OUT = "/opt/cursor/artifacts";

function lum(rgb) {
  const m = String(rgb).match(/[\d.]+/g);
  if (!m || m.length < 3) return null;
  const f = m.slice(0, 3).map(Number).map((v) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2];
}
function ratio(a, b) {
  const x = lum(a), y = lum(b);
  if (x == null || y == null) return 0;
  const hi = Math.max(x, y), lo = Math.min(x, y);
  return (hi + 0.05) / (lo + 0.05);
}

const browser = await puppeteer.launch({
  executablePath: "/usr/local/bin/google-chrome",
  headless: "new",
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const page = await browser.newPage();
page.setDefaultTimeout(40000);
await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
await page.goto("http://127.0.0.1:8792/?" + Math.random().toString(36).slice(2) +
  "#date=1951-03-16&style=strategy&treaty=curated%3Asolas-1948&c=51.5,-0.12&z=5",
  { waitUntil: "networkidle0", timeout: 120000 });
await page.waitForFunction(() => {
  const t = document.querySelector("#detailBody")?.innerText || "";
  return t.includes("已签署未生效") && t.includes("1952年11月19日") && t.includes("1948年国际海上人命安全公约");
}, { timeout: 30000 });
const text = await page.evaluate(() => document.querySelector("#detailBody").innerText);
if (text.includes("1974")) problems.push("弹窗出现 1974");
if (text.includes("1980")) problems.push("弹窗出现 1980");
if (!text.includes("不是实际生效日")) problems.push("没有写明条件日期不是生效日");
const contrast = await page.evaluate(() => {
  const body = document.querySelector(".modal-body");
  const td = document.querySelector(".modal-body .kv td");
  const p = document.querySelector(".modal-body .wsum p") || document.querySelector(".modal-body .s");
  const cs = (el) => el ? getComputedStyle(el) : null;
  const bgOf = (el) => {
    let n = el;
    while (n) {
      const c = getComputedStyle(n).backgroundColor;
      if (c && c !== "rgba(0, 0, 0, 0)" && c !== "transparent") return c;
      n = n.parentElement;
    }
    return "rgb(0,0,0)";
  };
  return {
    strategy: document.body.classList.contains("strategy"),
    body: cs(body) && [cs(body).color, bgOf(body)],
    td: cs(td) && [cs(td).color, bgOf(td)],
    p: cs(p) && [cs(p).color, bgOf(p)],
  };
});
if (!contrast.strategy) problems.push("没有处在策略地图");
for (const [name, pair] of [["正文", contrast.body], ["表格", contrast.td], ["摘要", contrast.p]]) {
  if (!pair) { problems.push(name + " 没有量到颜色"); continue; }
  const r = ratio(pair[0], pair[1]);
  if (r < 4.5) problems.push(`${name} 对比度 ${r.toFixed(2)}（${pair[0]} / ${pair[1]}）`);
}
await page.screenshot({ path: OUT + "/solas-1951-03-16.png" });
console.log(problems.length ? "FAIL\n" + problems.join("\n") : "PASS");
await browser.close();
process.exit(problems.length ? 1 : 0);
