/**
 * 选中政权的红线必须贴着当前缩放下已经画出来的填色边。
 * 比较的是屏幕上的线，不是另一套省界。几个日期、几种缩放都要过。
 * 用法：node tools/accept/regime_outline.mjs
 */
import { createRequire } from "module";
const require = createRequire("/tmp/wha-shot/package.json");
const puppeteer = require("puppeteer-core");

const TOL = 1;
const fails = [];
const browser = await puppeteer.launch({
  executablePath: "/usr/local/bin/google-chrome",
  headless: "new",
  args: ["--no-sandbox", "--disable-dev-shm-usage", "--window-size=390,844"],
  defaultViewport: { width: 390, height: 844, deviceScaleFactor: 1 },
});
const page = await browser.newPage();
page.setDefaultTimeout(90000);

function distPointSeg(px, py, ax, ay, bx, by) {
  const dx = bx - ax, dy = by - ay;
  const len2 = dx * dx + dy * dy;
  let t = len2 ? ((px - ax) * dx + (py - ay) * dy) / len2 : 0;
  t = Math.max(0, Math.min(1, t));
  const x = ax + t * dx, y = ay + t * dy;
  return Math.hypot(px - x, py - y);
}

async function openAt(date, lat, lon, zoom) {
  await page.goto(
    "http://127.0.0.1:8792/?" + Math.random().toString(36).slice(2) +
      `#date=${date}&c=${lat},${lon}&z=${zoom}&layers=roc_provinces`,
    { waitUntil: "domcontentloaded", timeout: 120000 },
  );
  await page.waitForFunction(() => window.WHA && WHA.map && WHA.map._loaded, { timeout: 90000 });
  await page.waitForFunction((z) => WHA.map.getZoom() === z && !WHA.map._animatingZoom, { timeout: 30000 }, zoom);
  await page.waitForFunction(() => document.querySelectorAll(".leaflet-overlay-pane path").length > 5, { timeout: 90000 });
}

async function selectAt(lat, lon) {
  await page.evaluate(async ([lat, lon]) => {
    await WHA.selectAt(lat, lon);
    const panel = document.getElementById("panel");
    if (panel) panel.style.visibility = "hidden";
  }, [lat, lon]);
  await page.waitForFunction(() => document.querySelectorAll("path.regime-outline").length > 0, { timeout: 20000 });
}

async function measure() {
  return page.evaluate(() => {
    const fids = new Set(WHA.linkedFids());
    const fill = [];
    WHA.map.eachLayer((l) => {
      if (!l.feature || !fids.has(l.feature.properties.fid) || !l._parts) return;
      for (const part of l._parts) {
        if (!part || part.length < 2) continue;
        fill.push(part.map((p) => [p.x, p.y]));
      }
    });
    const outline = [];
    document.querySelectorAll("path.regime-outline").forEach((path) => {
      const nums = [...path.getAttribute("d").matchAll(/-?\d+(?:\.\d+)?/g)].map((m) => Number(m[0]));
      const pts = [];
      for (let i = 0; i < nums.length; i += 2) pts.push([nums[i], nums[i + 1]]);
      if (pts.length >= 2) outline.push(pts);
    });
    // 按路径顶点变换到屏幕。不沿总长度抽样，避免小圈被跳过。
    function screenRings(path) {
      const ctm = path.getScreenCTM();
      if (!ctm) return [];
      const nums = [...path.getAttribute("d").matchAll(/-?\d+(?:\.\d+)?/g)].map((m) => Number(m[0]));
      const cmds = path.getAttribute("d").match(/[MLZmlz]/g) || [];
      const rings = [];
      let ring = [], ni = 0;
      for (const cmd of cmds) {
        if (cmd === "M" || cmd === "m") {
          if (ring.length >= 2) rings.push(ring);
          const s = new DOMPoint(nums[ni], nums[ni + 1]).matrixTransform(ctm);
          ni += 2;
          ring = [[s.x, s.y]];
        } else if (cmd === "L" || cmd === "l") {
          const s = new DOMPoint(nums[ni], nums[ni + 1]).matrixTransform(ctm);
          ni += 2;
          ring.push([s.x, s.y]);
        }
      }
      if (ring.length >= 2) rings.push(ring);
      return rings;
    }
    const screenFill = [];
    WHA.map.eachLayer((l) => {
      if (!l.feature || !fids.has(l.feature.properties.fid) || !l._path) return;
      screenFill.push(...screenRings(l._path));
    });
    const screenOutline = [];
    document.querySelectorAll("path.regime-outline").forEach((path) => {
      screenOutline.push(...screenRings(path));
    });
    return {
      fill, outline, screenFill, screenOutline,
      nFill: fill.length, nOut: outline.length, zoom: WHA.map.getZoom(),
    };
  });
}

function hausdorff(aRings, bRings) {
  let max = 0, n = 0;
  for (const ring of aRings) {
    for (const [x, y] of ring) {
      let best = Infinity;
      for (const other of bRings) {
        for (let i = 0; i < other.length; i++) {
          const a = other[i], b = other[(i + 1) % other.length];
          best = Math.min(best, distPointSeg(x, y, a[0], a[1], b[0], b[1]));
        }
      }
      if (best < Infinity) { max = Math.max(max, best); n++; }
    }
  }
  return { max, n };
}

async function settle(zoom) {
  await page.waitForFunction(() => WHA.map && !WHA.map._animatingZoom && !WHA.map._zooming);
  const now = await page.evaluate(() => WHA.map.getZoom());
  if (now !== zoom) {
    await page.evaluate((z) => new Promise((resolve) => {
      WHA.map.once("zoomend", () => resolve(WHA.map.getZoom()));
      WHA.map.setZoom(z);
    }), zoom);
  }
  await page.waitForFunction((z) => WHA.map.getZoom() === z && !WHA.map._animatingZoom, {}, zoom);
  await page.evaluate(() => WHA.restyle());
}

async function checkCase(label, date, lat, lon, zoom) {
  await openAt(date, lat, lon, zoom);
  await selectAt(lat, lon);
  await page.evaluate(() => WHA.restyle());
  const m = await measure();
  const ab = hausdorff(m.outline, m.fill);
  const ba = hausdorff(m.fill, m.outline);
  const sab = hausdorff(m.screenOutline, m.screenFill);
  const sba = hausdorff(m.screenFill, m.screenOutline);
  const worst = Math.max(ab.max, ba.max, sab.max, sba.max);
  const ok = m.zoom === zoom && m.nOut > 0 && m.nFill > 0 && m.nOut === m.nFill && worst <= TOL && ab.n > 0 && ba.n > 0 && sab.n > 0;
  const line = `${ok ? "PASS" : "FAIL"} ${label} zoom=${m.zoom} rings=${m.nOut}/${m.nFill} outline→fill ${ab.max.toFixed(2)}px fill→outline ${ba.max.toFixed(2)}px screen ${Math.max(sab.max, sba.max).toFixed(2)}px`;
  console.log(line);
  if (!ok) fails.push(line);
}

await checkCase("1949-09-26 兰州 z6", "1949-09-26", 36.06, 103.83, 6);
await settle(4);
{
  const m = await measure();
  const ab = hausdorff(m.outline, m.fill);
  const ba = hausdorff(m.fill, m.outline);
  const sab = hausdorff(m.screenOutline, m.screenFill);
  const sba = hausdorff(m.screenFill, m.screenOutline);
  const worst = Math.max(ab.max, ba.max, sab.max, sba.max);
  const ok = m.zoom === 4 && m.nOut > 0 && m.nOut === m.nFill && worst <= TOL && sab.n > 0;
  const line = `${ok ? "PASS" : "FAIL"} 1949-09-26 兰州 z4 zoom=${m.zoom} rings=${m.nOut}/${m.nFill} outline→fill ${ab.max.toFixed(2)}px fill→outline ${ba.max.toFixed(2)}px screen ${Math.max(sab.max, sba.max).toFixed(2)}px`;
  console.log(line);
  if (!ok) fails.push(line);
}
await settle(7);
{
  const m = await measure();
  const ab = hausdorff(m.outline, m.fill);
  const ba = hausdorff(m.fill, m.outline);
  const sab = hausdorff(m.screenOutline, m.screenFill);
  const sba = hausdorff(m.screenFill, m.screenOutline);
  const worst = Math.max(ab.max, ba.max, sab.max, sba.max);
  const ok = m.zoom === 7 && m.nOut > 0 && m.nOut === m.nFill && worst <= TOL && sab.n > 0;
  const line = `${ok ? "PASS" : "FAIL"} 1949-09-26 兰州 z7 zoom=${m.zoom} rings=${m.nOut}/${m.nFill} outline→fill ${ab.max.toFixed(2)}px fill→outline ${ba.max.toFixed(2)}px screen ${Math.max(sab.max, sba.max).toFixed(2)}px`;
  console.log(line);
  if (!ok) fails.push(line);
}

await checkCase("2000-06-01 巴黎 z5", "2000-06-01", 48.86, 2.35, 5);
await checkCase("1944-12-01 南京 z5", "1944-12-01", 32.06, 118.8, 5);

const PROV_TOL = 9;
async function checkProvince(label, date, lat, lon, zoom, namePart) {
  await openAt(date, lat, lon, zoom);
  await page.waitForFunction(() => document.querySelectorAll(".leaflet-rocprov-pane path").length > 3, { timeout: 90000 });
  await selectAt(lat, lon);
  await page.evaluate(() => WHA.restyle());
  const m = await page.evaluate(() => {
    function screenRings(path) {
      const ctm = path.getScreenCTM();
      if (!ctm) return [];
      const nums = [...path.getAttribute("d").matchAll(/-?\d+(?:\.\d+)?/g)].map((x) => Number(x[0]));
      const cmds = path.getAttribute("d").match(/[MLZmlz]/g) || [];
      const rings = [];
      let ring = [], ni = 0;
      for (const cmd of cmds) {
        if (cmd === "M" || cmd === "m") {
          if (ring.length >= 2) rings.push(ring);
          const s = new DOMPoint(nums[ni], nums[ni + 1]).matrixTransform(ctm);
          ni += 2;
          ring = [[s.x, s.y]];
        } else if (cmd === "L" || cmd === "l") {
          const s = new DOMPoint(nums[ni], nums[ni + 1]).matrixTransform(ctm);
          ni += 2;
          ring.push([s.x, s.y]);
        }
      }
      if (ring.length >= 2) rings.push(ring);
      return rings;
    }
    const outline = [];
    document.querySelectorAll("path.regime-outline").forEach((path) => outline.push(...screenRings(path)));
    const prov = [];
    document.querySelectorAll(".leaflet-rocprov-pane path").forEach((path) => {
      const dash = path.getAttribute("stroke-dasharray") || "";
      if (!dash.startsWith("6")) return;
      prov.push(...screenRings(path));
    });
    const box = WHA.map.getContainer().getBoundingClientRect();
    const inset = [];
    for (const ring of outline) {
      for (const [x, y] of ring) {
        if (x < box.left + 8 || x > box.right - 8 || y < box.top + 8 || y > box.bottom - 8) continue;
        inset.push([x, y]);
      }
    }
    return { inset, prov, name: document.getElementById("polityName")?.textContent || "" };
  });
  const one = hausdorff([m.inset], m.prov);
  const sorted = [];
  for (const [x, y] of m.inset) {
    let best = Infinity;
    for (const other of m.prov) {
      for (let i = 0; i < other.length; i++) {
        const a = other[i], b = other[(i + 1) % other.length];
        best = Math.min(best, distPointSeg(x, y, a[0], a[1], b[0], b[1]));
      }
    }
    if (best < Infinity) sorted.push(best);
  }
  sorted.sort((a, b) => a - b);
  const median = sorted.length ? sorted[Math.floor(sorted.length / 2)] : Infinity;
  const ok = m.inset.length >= 8 && m.prov.length > 0 && one.max <= PROV_TOL && median <= 1 && one.n >= 8 && m.name.includes(namePart);
  const line = `${ok ? "PASS" : "FAIL"} ${label} 红线贴历史省界 最大 ${one.max.toFixed(2)}px 中位 ${median.toFixed(2)}px 顶点 ${one.n} 名称 ${m.name}`;
  console.log(line);
  if (!ok) fails.push(line);
}

await checkProvince("1930-06-01 太原", "1930-06-01", 37.8706, 112.5489, 6, "晋系");
await checkProvince("1944-12-01 昆明", "1944-12-01", 25.0389, 102.7183, 6, "滇系");
await checkProvince("1949-09-26 兰州历史省界", "1949-09-26", 36.06, 103.83, 6, "中国共产党");

await page.evaluate(() => document.getElementById("closePanel").click());
await page.waitForFunction(() => document.querySelectorAll("path.regime-outline").length === 0, { timeout: 10000 }).catch(() => {});
const left = await page.evaluate(() => document.querySelectorAll("path.regime-outline").length);
const cleared = left === 0;
console.log((cleared ? "PASS" : "FAIL") + ` 取消选择后没有红线 | ${left}`);
if (!cleared) fails.push("outline remains");

await browser.close();
if (fails.length) {
  console.log("FAIL", fails.length);
  process.exit(1);
}
console.log("regime_outline OK");
