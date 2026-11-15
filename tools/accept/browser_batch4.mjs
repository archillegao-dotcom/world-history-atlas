// 第四批：同一视角的 1944 年欧洲和东亚。系统 Chrome，无头。
import { createRequire } from "node:module";
import fs from "node:fs";
const puppeteer = createRequire("/tmp/wha-shot/package.json")("puppeteer-core");
const OUT = "/opt/cursor/artifacts";
fs.mkdirSync(OUT, { recursive: true });
const browser = await puppeteer.launch({
  executablePath: "/usr/local/bin/google-chrome",
  headless: "new",
  args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
  defaultViewport: { width: 1440, height: 900 },
});
const page = await browser.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });

async function shot(q, hash, name) {
  await page.goto("http://127.0.0.1:8792/?" + q + hash, { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.waitForSelector(".leaflet-overlay-pane path", { timeout: 90000 });
  await new Promise((r) => setTimeout(r, 1800));
  await page.screenshot({ path: `${OUT}/${name}.png` });
  return page.evaluate(() => ({
    labels: [...document.querySelectorAll(".strategy-label span")].map((s) => s.textContent),
    stars: document.querySelectorAll(".city-dot.cap").length,
    cityNames: [...document.querySelectorAll(".city-name")].map((s) => s.textContent),
    center: window.WHA && WHA.map ? [+WHA.map.getCenter().lat.toFixed(2), +WHA.map.getCenter().lng.toFixed(2), WHA.map.getZoom()] : null,
    strategy: document.body.classList.contains("strategy"),
    ocean: getComputedStyle(document.querySelector(".leaflet-container")).backgroundColor,
  }));
}

const europe = await shot("e4=1", "#date=1944-12-01&c=48,8&z=4&style=strategy", "b4-1944-europe-after");
const asia = await shot("a4=1", "#date=1944-12-01&c=32,114&z=4&style=strategy", "b4-1944-asia-after");
const normal = await shot("n4=1", "#date=1944-12-01&c=48,8&z=4", "b4-1944-europe-normal");

await page.goto("http://127.0.0.1:8792/?h4=1#date=2000-06-01&c=48.86,2.35&z=5&style=strategy", { waitUntil: "domcontentloaded", timeout: 90000 });
await page.waitForSelector(".leaflet-overlay-pane path", { timeout: 90000 });
await new Promise((r) => setTimeout(r, 1200));
await page.mouse.move(30, 30);
const pt = await page.evaluate(() => {
  const map = WHA.map;
  const ll = map.latLngToContainerPoint([48.86, 2.35]);
  const rect = map.getContainer().getBoundingClientRect();
  return { x: rect.left + ll.x, y: rect.top + ll.y };
});
await page.mouse.move(pt.x, pt.y);
await new Promise((r) => setTimeout(r, 3200));
const early = await page.$eval("#econHover", (el) => el.classList.contains("on"));
await new Promise((r) => setTimeout(r, 2300));
const text = await page.$eval("#econHover", (el) => el.innerText);
await page.screenshot({ path: `${OUT}/b4-hover-2000.png` });
const maddisonLines = text.split("\n").filter((l) => l.includes("Maddison Project")).length;

const report = {
  europe, asia, normal, earlyHover: early, hover: text.slice(0, 500), maddisonLines, errors,
};
fs.writeFileSync(`${OUT}/b4-browser-result.json`, JSON.stringify(report, null, 2));
fs.writeFileSync(`${OUT}/b4-console.txt`, errors.join("\n") || "(no console errors)\n");
console.log(JSON.stringify({
  europeLabels: europe.labels, asiaLabels: asia.labels, europeStars: europe.stars, europeCityNames: europe.cityNames,
  asiaStars: asia.stars, normalStrategy: normal.strategy, ocean: europe.ocean,
  earlyHover: early, hoverHead: text.split("\n").slice(0, 6), maddisonLines, nErrors: errors.length,
}, null, 2));
if (errors.length || early || maddisonLines !== 1 || !text.includes("现代国家") || !europe.strategy || normal.strategy) process.exit(1);
await browser.close();
