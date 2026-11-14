/**
 * 真实浏览器验收（系统 Chrome + puppeteer-core）。不是接口冒充点击，也不生成假图。
 * 用法：NODE_PATH=/tmp/wha-shot/node_modules node tools/accept/browser_batch3.mjs
 * 截图写到 /opt/cursor/artifacts/
 */
import fs from "node:fs";
import { createRequire } from "node:module";
const require = createRequire(process.env.PUPPETEER_REQUIRE || "/tmp/wha-shot/package.json");
const puppeteer = require("puppeteer-core");

const OUT = "/opt/cursor/artifacts";
const BASE = process.env.WHA_URL || "http://127.0.0.1:8792";
fs.mkdirSync(OUT, { recursive: true });
const consoleLog = [];
const shots = [];

function log(s) { console.log(s); consoleLog.push(s); }

async function shot(page, name) {
  const p = `${OUT}/${name}.png`;
  await page.screenshot({ path: p, fullPage: false });
  shots.push(p);
  log("SHOT " + p);
}

async function mapPoint(page, lat, lon) {
  return page.evaluate(([lat, lon]) => {
    const r = document.getElementById("map").getBoundingClientRect();
    const p = WHA.map.latLngToContainerPoint([lat, lon]);
    return { x: r.left + p.x, y: r.top + p.y };
  }, [lat, lon]);
}

async function waitMap(page) {
  await page.waitForSelector(".leaflet-overlay-pane path", { timeout: 90000 });
  await new Promise((r) => setTimeout(r, 600));
}

const browser = await puppeteer.launch({
  executablePath: process.env.CHROME || "/usr/local/bin/google-chrome",
  headless: "new",
  args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--window-size=1440,900"],
  defaultViewport: { width: 1440, height: 900 },
});
const page = await browser.newPage();
page.on("console", (m) => consoleLog.push(`CONSOLE ${m.type()}: ${m.text()}`));
page.on("pageerror", (e) => consoleLog.push(`PAGEERROR ${e.message}`));
page.on("response", (r) => { if (r.status() >= 400) consoleLog.push(`HTTP ${r.status()} ${r.url()}`); });
const fails = [];
const check = (name, ok, extra = "") => {
  log((ok ? "PASS " : "FAIL ") + name + (extra ? " | " + extra : ""));
  if (!ok) fails.push(name);
};

try {
  const tOpen = Date.now();
  await page.goto(`${BASE}/#date=1944-12-01&c=48,8&z=4`, { waitUntil: "domcontentloaded", timeout: 90000 });
  await waitMap(page);
  log(`PERF first map paint ${Date.now() - tOpen} ms`);
  const w0 = await page.evaluate(() => {
    const p = document.querySelector(".leaflet-overlay-pane svg path");
    return p ? p.getAttribute("stroke-width") : null;
  });
  await shot(page, "b3-1944-normal");
  const tStyle = Date.now();
  await page.click("#styleBtn");
  await new Promise((r) => setTimeout(r, 400));
  log(`PERF strategy toggle handler returned, waited 400 ms, click+wait ${Date.now() - tStyle} ms`);
  const w1 = await page.evaluate(() => {
    const p = document.querySelector(".leaflet-overlay-pane svg path");
    const note = document.getElementById("eraNote")?.innerText || "";
    const btn = document.getElementById("styleBtn")?.innerText || "";
    return { w: p ? p.getAttribute("stroke-width") : null, note, btn };
  });
  check("策略地图加粗边界而不是只换底色", w0 != null && w1.w != null && Number(w1.w) > Number(w0), `before ${w0} after ${w1.w}`);
  if (!w1.note.includes("不是 TNO")) await page.click("#eraToggle");
  const noteOpen = await page.evaluate(() => document.getElementById("eraNote")?.innerText || "");
  check("说明写明不是历史省界、省界待考，也不是 TNO", noteOpen.includes("不是历史省界") && noteOpen.includes("省界待考") && noteOpen.includes("不画今天的省界") && noteOpen.includes("不是 TNO"), noteOpen.slice(0, 120));
  check("按钮可切回普通地图", w1.btn === "普通地图", w1.btn);
  await shot(page, "b3-1944-strategy");

  await page.evaluate(() => {
    const boxes = [...document.querySelectorAll("#layerCtl input")];
    for (const el of boxes) {
      const label = el.parentElement?.innerText || "";
      if (label.includes("实际控制区") && !el.checked) el.click();
    }
  });
  const tAdmin = Date.now();
  await page.evaluate(() => WHA.map.setView([24.5, 110.5], 6));
  await page.waitForFunction(() => document.querySelectorAll(".leaflet-rocprov-pane path").length > 0, { timeout: 20000 });
  await new Promise((r) => setTimeout(r, 400));
  const adminInfo = await page.evaluate(() => {
    const modern = document.querySelectorAll(".leaflet-admin1-pane path").length;
    const hist = document.querySelectorAll(".leaflet-rocprov-pane path").length;
    const ctl = document.getElementById("layerCtl")?.getBoundingClientRect();
    const btn = document.getElementById("styleBtn")?.getBoundingClientRect();
    return { modern, hist, ctl: ctl && ctl.width > 0 && ctl.top >= 0, btn: btn && btn.top >= 0 };
  });
  log(`PERF province lines after ${Date.now() - tAdmin} ms, modern ${adminInfo.modern} hist ${adminInfo.hist}`);
  check("放大后不画今天的省界，1944年桂林有民国省界", adminInfo.modern === 0 && adminInfo.hist > 0, `modern ${adminInfo.modern} hist ${adminInfo.hist}`);
  check("图层开关和策略按钮仍在画面内", adminInfo.ctl && adminInfo.btn, "");
  await shot(page, "b3-1944-guilin-admin1");

  await page.goto(`${BASE}/?shot=hk#date=2020-01-01&c=20,114&z=3&style=strategy`, { waitUntil: "domcontentloaded", timeout: 90000 });
  await waitMap(page);
  await new Promise((r) => setTimeout(r, 500));
  const tiny = await page.evaluate(() => {
    const r = document.getElementById("map").getBoundingClientRect();
    const found = [];
    const walk = (layer) => {
      if (layer.eachLayer) layer.eachLayer(walk);
      const name = layer.feature && layer.feature.properties && layer.feature.properties.NAME;
      if (!name || !layer.getLatLng) return;
      if (/Hong Kong|Macao|Macau|Macau/.test(name)) {
        const p = WHA.map.latLngToContainerPoint(layer.getLatLng());
        found.push({ x: r.left + p.x, y: r.top + p.y, name, radius: layer.getRadius ? layer.getRadius() : null });
      }
    };
    WHA.map.eachLayer(walk);
    return found;
  });
  log("TINY " + JSON.stringify(tiny));
  check("缩小时能找到港澳圆点", tiny.length >= 1, JSON.stringify(tiny));
  const macao = tiny.find((t) => /Macau|Macao/.test(t.name));
  const hk = tiny.find((t) => t.name === "Hong Kong") || tiny.find((t) => /Hong Kong/.test(t.name));
  const target = macao || hk;
  if (target) {
    await page.mouse.click(target.x, target.y);
    await page.waitForFunction(() => !document.getElementById("panel").classList.contains("hidden"), { timeout: 20000 });
    await new Promise((r) => setTimeout(r, 800));
    const name = await page.evaluate(() => document.getElementById("polityName").innerText);
    check("点击圆点打开面板且不是空白", name && name !== "—", `${target.name} -> ${name}`);
    await shot(page, "b3-hk-click");
  }

  await page.goto(`${BASE}/?shot=hover#date=2000-06-01&c=47,2.5&z=5.5`, { waitUntil: "domcontentloaded", timeout: 90000 });
  await waitMap(page);
  await page.evaluate(() => WHA.map.setView([47.0, 2.5], 5.5));
  await new Promise((r) => setTimeout(r, 700));
  let paris = null;
  for (const [lat, lon] of [[47.0, 2.5], [46.6, 1.8], [47.4, 3.4], [48.4, 1.2]]) {
    const pt = await mapPoint(page, lat, lon);
    if (pt.x < 8 || pt.y < 8 || pt.x > 1400 || pt.y > 860) continue;
    const hit = await page.evaluate(([x, y]) => {
      const el = document.elementFromPoint(x, y);
      if (!el) return "";
      const cls = el.className && el.className.baseVal ? el.className.baseVal : el.className;
      return `${el.tagName} ${cls || ""}`;
    }, [pt.x, pt.y]);
    log(`HIT ${lat},${lon} ${hit}`);
    if (String(hit).includes("path")) { paris = pt; break; }
  }
  check("找到落在政权多边形上的点", !!paris, JSON.stringify(paris));
  if (!paris) throw new Error("no polygon under the pointer");
  log("PARIS " + JSON.stringify(paris));
  await page.mouse.move(30, 30);
  await new Promise((r) => setTimeout(r, 200));
  const tHover = Date.now();
  await page.mouse.move(paris.x, paris.y);
  await new Promise((r) => setTimeout(r, 3200));
  const early = await page.evaluate(() => document.getElementById("econHover").classList.contains("on"));
  const yearShown = await page.evaluate(() => document.getElementById("dateLabel").innerText);
  check("悬停页是 2000 年", yearShown.includes("2000"), yearShown);
  check("未满 5 秒不出现经济浮窗", early === false, "on=" + early);
  await shot(page, "b3-hover-3s");
  await page.waitForFunction(() => {
    const box = document.getElementById("econHover");
    const t = box.innerText || "";
    return box.classList.contains("on") && (/Maddison|暂无数据/.test(t));
  }, { timeout: 8000 });
  const elapsed = Date.now() - tHover;
  const text = await page.evaluate(() => document.getElementById("econHover").innerText);
  check("满约 5 秒后出现浮窗", elapsed >= 4800 && elapsed < 9000, elapsed + " ms");
  check("浮窗有年份和来源或明确暂无数据", /暂无数据|Maddison/.test(text) && /2000/.test(text), text.slice(0, 220).replace(/\n/g, " / "));
  check("浮窗不把插值或最近数据当成该年", !/插值|最近数据/.test(text), "");
  await shot(page, "b3-hover-5s");
  await page.mouse.move(80, 12);
  await new Promise((r) => setTimeout(r, 250));
  const gone = await page.evaluate(() => document.getElementById("econHover").classList.contains("on"));
  check("指针离开后浮窗立即消失", gone === false, "on=" + gone);
  await shot(page, "b3-hover-left");

  await page.mouse.move(paris.x, paris.y);
  await new Promise((r) => setTimeout(r, 1500));
  await page.click("#nextBtn");
  await new Promise((r) => setTimeout(r, 4500));
  const afterDate = await page.evaluate(() => document.getElementById("econHover").classList.contains("on"));
  check("改日期会取消未完成的悬停", afterDate === false, "on=" + afterDate);
  await shot(page, "b3-hover-date-cancel");
} catch (e) {
  log("PAGEERROR script " + (e && e.stack || e));
  fails.push("script");
  try { await shot(page, "b3-error"); } catch (_) { /* 没有页面可拍 */ }
} finally {
  const errs = consoleLog.filter((l) => l.startsWith("PAGEERROR") || l.startsWith("CONSOLE error"));
  log("CONSOLE_ERRORS " + errs.length);
  errs.forEach((l) => log(l));
  fs.writeFileSync(`${OUT}/b3-console.txt`, consoleLog.join("\n") + "\n");
  fs.writeFileSync(`${OUT}/b3-browser-result.json`, JSON.stringify({ fails, shots, consoleErrors: errs }, null, 2));
  await browser.close();
}
log("FAILS " + fails.length);
process.exit(fails.length ? 1 : 0);
