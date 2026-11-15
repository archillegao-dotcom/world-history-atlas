/**
 * 第六批：国名按画出来的字框避让，不裁出屏幕，不互相叠住。
 * 用法：node tools/accept/browser_batch6.mjs
 * 需要本机 Chrome 与已启动的 8792。这是无头浏览器，不是手点。
 */
import { createRequire } from "module";
import { writeFileSync } from "fs";
const require = createRequire("/tmp/wha-shot/package.json");
const puppeteer = require("puppeteer-core");
const problems = [];
const browser = await puppeteer.launch({
  executablePath: "/usr/local/bin/google-chrome",
  headless: "new",
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const page = await browser.newPage();
async function open(w, h, hash) {
  await page.setViewport({ width: w, height: h, deviceScaleFactor: 1 });
  await page.goto("http://127.0.0.1:8792/?b6=" + Math.random().toString(36).slice(2) + hash, { waitUntil: "networkidle0", timeout: 90000 });
  await page.waitForFunction(() => document.body.classList.contains("strategy") && document.querySelectorAll("#map .strategy-label span").length > 0, { timeout: 30000 });
  await new Promise((r) => setTimeout(r, 700));
}
function layout() {
  return page.evaluate(() => {
    const map = document.querySelector("#map").getBoundingClientRect();
    const inset = { l: 8, t: map.width <= 720 ? 18 : 14, r: 8, b: 10 };
    const labs = [...document.querySelectorAll("#map .strategy-label span")].map((s) => {
      const r = s.getBoundingClientRect();
      return {
        t: s.textContent, title: s.getAttribute("title") || "",
        left: r.left - map.left, top: r.top - map.top, right: r.right - map.left, bot: r.bottom - map.top,
        lat: +s.dataset.lat, lng: +s.dataset.lng,
      };
    });
    const clipped = labs.filter((a) => a.left < inset.l - 0.5 || a.top < inset.t - 0.5 || a.right > map.width - inset.r + 0.5 || a.bot > map.height - inset.b + 0.5);
    const hits = [];
    for (let i = 0; i < labs.length; i++) for (let j = i + 1; j < labs.length; j++) {
      const a = labs[i], b = labs[j];
      if (!(a.right < b.left + 2 || a.left > b.right - 2 || a.bot < b.top + 2 || a.top > b.bot - 2)) hits.push(a.t + "|" + b.t);
    }
    const ell = labs.filter((a) => (a.t || "").includes("…")).map((a) => a.t);
    return { w: map.width, h: map.height, n: labs.length, clipped: clipped.map((a) => a.t), hits, ell, labs: labs.map((a) => a.t) };
  });
}
await open(1440, 900, "#date=1944-12-01&style=strategy&c=48,8&z=4");
const eu = await layout();
if (eu.clipped.length) problems.push("欧洲标签出屏 " + eu.clipped.join(","));
if (eu.hits.length) problems.push("欧洲标签相撞 " + eu.hits.join(","));
if (eu.ell.length) problems.push("欧洲省略号 " + eu.ell.join(","));
if (eu.labs.includes("波希米亚和摩拉维亚保护国")) problems.push("波希米亚全称仍画在地上");
if (eu.labs.includes("未命名区域")) problems.push("未命名区域被标在地图上");
for (const need of ["苏联", "纳粹德国", "罗马尼亚", "英国", "法国临时政府", "保加利亚王国", "希腊王国", "意大利王国"]) {
  if (!eu.labs.includes(need)) problems.push("欧洲缺少 " + need);
}
const tips = await page.evaluate(() => {
  const want = ["波希米亚和摩拉维亚保护国", "匈牙利王国", "意大利社会共和国"];
  const found = {};
  window.WHA.map.eachLayer((l) => {
    if (!l.feature || !l.getTooltip) return;
    const tip = l.getTooltip();
    if (!tip) return;
    const c = tip.getContent ? tip.getContent() : tip._content;
    const text = String(typeof c === "function" ? c(l) : (c || "")).replace(/<[^>]+>/g, "");
    for (const w of want) if (text.includes(w)) found[w] = true;
  });
  return found;
});
for (const w of ["波希米亚和摩拉维亚保护国", "匈牙利王国", "意大利社会共和国"]) {
  if (!tips[w]) problems.push("悬停缺少 " + w);
}
const soviet = await page.evaluate(() => {
  const s = [...document.querySelectorAll("#map .strategy-label span")].find((x) => x.textContent === "苏联");
  return s ? { lat: +s.dataset.lat, lng: +s.dataset.lng } : null;
});
if (!soviet || soviet.lng < 20) problems.push("欧洲苏联不在陆上 " + JSON.stringify(soviet));
await page.screenshot({ path: "/opt/cursor/artifacts/b6-after-desktop-europe.png" });

await open(390, 844, "#date=1944-12-01&style=strategy&c=32,114&z=4");
const asia = await layout();
if (asia.clipped.length) problems.push("手机东亚标签出屏 " + asia.clipped.join(","));
if (asia.hits.length) problems.push("手机东亚标签相撞 " + asia.hits.join(","));
if (asia.ell.length) problems.push("手机东亚省略号");
const jp = await page.evaluate(() => {
  const s = [...document.querySelectorAll("#map .strategy-label span")].find((x) => x.textContent === "大日本帝国");
  return s ? { lng: +s.dataset.lng, top: s.getBoundingClientRect().top } : null;
});
if (jp && jp.lng < 122) problems.push("大日本帝国经度 " + jp.lng);
await page.screenshot({ path: "/opt/cursor/artifacts/b6-after-narrow-asia.png" });

await open(390, 844, "#date=1944-12-01&style=strategy");
const phone = await layout();
if (phone.clipped.length) problems.push("手机首屏标签出屏 " + phone.clipped.join(","));
if (phone.hits.length) problems.push("手机首屏标签相撞 " + phone.hits.join(","));
const def = await page.evaluate(() => {
  const c = window.WHA.map.getCenter();
  return { z: window.WHA.map.getZoom(), lat: +c.lat.toFixed(2), lng: +c.lng.toFixed(2) };
});
if (Math.abs(def.z - 3) > 0.01) problems.push("手机默认缩放变了 " + def.z);
await page.screenshot({ path: "/opt/cursor/artifacts/b6-after-narrow-default.png" });

const out = { problems, eu, asia, phone, soviet, jp, def };
writeFileSync("logs/browser_batch6.json", JSON.stringify(out, null, 2));
console.log(JSON.stringify({ problems, eu: { n: eu.n, clipped: eu.clipped, hits: eu.hits, labs: eu.labs }, asia: { n: asia.n, clipped: asia.clipped, hits: asia.hits, labs: asia.labs }, phone: { n: phone.n, clipped: phone.clipped, hits: phone.hits }, soviet, def }, null, 2));
await browser.close();
process.exit(problems.length ? 1 : 0);
