/**
 * 宪法页：桌面和手机上真实点击，并切换日期。
 * 用法：node tools/accept/browser_constitutions.mjs
 */
import { createRequire } from "module";
const require = createRequire("/tmp/wha-shot/package.json");
const puppeteer = require("puppeteer-core");
const problems = [];
const browser = await puppeteer.launch({
  executablePath: "/usr/local/bin/google-chrome",
  headless: "new",
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const page = await browser.newPage();
page.setDefaultTimeout(30000);

async function open(w, h, hash) {
  await page.setViewport({ width: w, height: h, deviceScaleFactor: 1 });
  await page.goto("http://127.0.0.1:8792/?const=" + Math.random().toString(36).slice(2) + hash, { waitUntil: "networkidle0", timeout: 90000 });
  await page.waitForFunction(() => window.WHA && window.WHA.selectAt, { timeout: 30000 });
}

async function pick(lat, lon) {
  await page.evaluate(async (lat, lon) => { await window.WHA.selectAt(lat, lon); }, lat, lon);
  await page.waitForFunction(() => document.querySelector("#panel") && !document.querySelector("#panel").classList.contains("hidden"), { timeout: 20000 });
  await page.waitForFunction(() => {
    const body = document.querySelector("#tabBody");
    return body && !body.textContent.includes("加载中");
  }, { timeout: 20000 });
  await new Promise((r) => setTimeout(r, 400));
}

async function lawButton() {
  return page.evaluate(() => [...document.querySelectorAll("#tabs button")].some((b) => b.textContent.startsWith("宪法")));
}

async function openLaw() {
  await page.waitForFunction(() => [...document.querySelectorAll("#tabs button")].some((b) => b.textContent.startsWith("宪法")), { timeout: 15000 });
  const box = await page.evaluate(() => {
    const b = [...document.querySelectorAll("#tabs button")].find((x) => x.textContent.startsWith("宪法"));
    b.scrollIntoView({ block: "nearest", inline: "center" });
    const r = b.getBoundingClientRect();
    return { x: r.x + r.width / 2, y: r.y + Math.min(r.height / 2, 12) };
  });
  await page.mouse.click(box.x, box.y);
  await page.waitForSelector(".mod-constitution .item", { timeout: 10000 });
}

async function headings() {
  return page.evaluate(() => [...document.querySelectorAll(".mod-constitution .item > .t")].map((e) => (e.childNodes[0].textContent || "").trim()));
}

async function jump(y, m, d) {
  await page.click("#yearIn", { clickCount: 3 });
  await page.type("#yearIn", String(y));
  await page.select("#monthIn", String(m));
  await page.select("#dayIn", String(d));
  await page.click("#goBtn");
  await page.waitForFunction((yy, mm, dd) => {
    const h = new URLSearchParams(location.hash.slice(1)).get("date") || "";
    return h === `${yy}-${String(mm).padStart(2, "0")}-${String(dd).padStart(2, "0")}`;
  }, { timeout: 20000 }, y, m, d);
  await new Promise((r) => setTimeout(r, 500));
}

await open(1440, 900, "#date=1944-12-01&style=strategy&c=48.8,2.3&z=5");
await pick(48.8566, 2.3522);
if (!(await lawButton())) problems.push("1944 巴黎没有宪法页");
else {
  await openLaw();
  const t = await headings();
  if (!t.includes("1944年8月9日恢复共和合法性法令")) problems.push("1944 巴黎标题不对 " + t.join("|"));
  if (t.includes("1946年10月27日宪法")) problems.push("1944 巴黎显示了1946宪法");
}
await page.screenshot({ path: "/opt/cursor/artifacts/const-desktop-1944-paris.png" });

await jump(1946, 10, 26);
await pick(48.8566, 2.3522);
if (!(await lawButton())) problems.push("1946-10-26 巴黎没有宪法页");
else {
  await openLaw();
  const t = await headings();
  if (t.includes("1946年10月27日宪法")) problems.push("10月26日提前显示1946宪法");
  if (!t.includes("1945年11月2日宪法性法律")) problems.push("10月26日缺少1945年法律 " + t.join("|"));
}
await page.screenshot({ path: "/opt/cursor/artifacts/const-desktop-1946-10-26-paris.png" });

await jump(1946, 10, 27);
await pick(48.8566, 2.3522);
if (!(await lawButton())) problems.push("1946-10-27 巴黎没有宪法页");
else {
  await openLaw();
  const t = await headings();
  if (!t.includes("1946年10月27日宪法")) problems.push("10月27日没有1946宪法 " + t.join("|"));
  if (t.includes("1944年8月9日恢复共和合法性法令")) problems.push("10月27日仍显示8月9日法令");
}
await page.screenshot({ path: "/opt/cursor/artifacts/const-desktop-1946-paris.png" });

await jump(1944, 12, 1);
await pick(52.52, 13.405);
if (await lawButton()) problems.push("1944 柏林不该出现宪法页");
await page.screenshot({ path: "/opt/cursor/artifacts/const-desktop-1944-berlin.png" });

await open(390, 844, "#date=1947-05-02&style=strategy&c=35.7,139.7&z=5");
await pick(35.69, 139.69);
if (!(await lawButton())) problems.push("1947-05-02 东京没有宪法页");
else {
  await openLaw();
  const t = await headings();
  if (!t.includes("大日本帝国宪法")) problems.push("5月2日不是帝国宪法 " + t.join("|"));
  if (t.includes("日本国宪法")) problems.push("5月2日提前显示日本国宪法");
}
await page.screenshot({ path: "/opt/cursor/artifacts/const-phone-1947-05-02-tokyo.png" });

await jump(1947, 5, 3);
await pick(35.69, 139.69);
if (!(await lawButton())) problems.push("1947-05-03 东京没有宪法页");
else {
  await openLaw();
  const t = await headings();
  if (!t.includes("日本国宪法")) problems.push("5月3日不是日本国宪法 " + t.join("|"));
  if (t.includes("大日本帝国宪法")) problems.push("5月3日仍显示帝国宪法");
}
await page.screenshot({ path: "/opt/cursor/artifacts/const-phone-1947-05-03-tokyo.png" });

await open(390, 844, "#date=2000-06-01&style=strategy&c=51.5,-0.1&z=5");
await pick(51.5074, -0.1276);
if (!(await lawButton())) problems.push("2000 伦敦没有宪法页");
else {
  await openLaw();
  const text = await page.evaluate(() => document.querySelector(".mod-constitution").innerText);
  if (!text.includes("不成文宪法")) problems.push("伦敦不是不成文宪法");
  if (!text.includes("1949年议会法")) problems.push("伦敦没有1949年议会法");
  if (text.includes("单一成文宪法") && !text.includes("没有一部")) problems.push("伦敦被写成单一成文宪法");
}
await page.screenshot({ path: "/opt/cursor/artifacts/const-phone-london-2000.png" });

await browser.close();
if (problems.length) {
  console.log("FAIL");
  for (const p of problems) console.log(" -", p);
  process.exit(1);
}
console.log("PASS");
