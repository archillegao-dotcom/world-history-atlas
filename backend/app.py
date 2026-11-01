"""
世界历史地图 (World History Atlas) — 本地 Web 服务 (FastAPI)。

API:
  GET /api/meta                         应用信息、快照列表、模块清单、数据来源
  GET /api/snapshot?date=1789-07-14     该日期使用哪个边界快照（及下一个快照年份）
  GET /api/basemap/{snap}               该快照的 GeoJSON（gzip）
  GET /api/polity?snap=1783&fid=12      政权属性
  GET /api/locate?date=..&lon=..&lat=.. 某点在该日期属于哪个政权
  GET /api/modules                      已注册内容模块清单（前端据此生成标签页）
  GET /api/modules/{id}?date=..&snap=..&fid=..[&span=&limit=]   某模块在该政权/日期的条目
      不传 fid 表示「全世界」
"""
from __future__ import annotations

import json
import os
import threading
import time

from fastapi import Request, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import config
from .geo import BasemapStore
from .live import scheduler
from .registry import Context, Registry
from .timeutil import parse_date

app = FastAPI(title="世界历史地图 World History Atlas", version=config.APP_VERSION)

basemaps: BasemapStore | None = None
ctx: Context | None = None
registry: Registry | None = None


def _on_news_update(years):
    m = registry.modules.get("news") if registry else None
    if m:
        m.invalidate(years)


def boot() -> None:
    """加载历史数据并启动每日新闻调度。导入本模块就会调用（服务进程如此）。"""
    global basemaps, ctx, registry
    basemaps = BasemapStore()
    ctx = Context(data_dir=config.DATA_DIR, basemaps=basemaps)
    registry = Registry()
    registry.discover("backend.modules")
    registry.load_all(ctx)
    scheduler.start(on_update=_on_news_update)


# PyInstaller 分析依赖时会导入本模块。那时不要把全部数据装进内存，也不要去写 data/live。
if os.environ.get("WHA_PYINSTALLER_ANALYZE") != "1":
    boot()

SOURCES = [
    {"name": "historical-basemaps (A. Ourednik)", "url": "https://github.com/aourednik/historical-basemaps",
     "license": "GPL-3.0", "use": "历史边界 / 政权多边形"},
    {"name": "Wikidata", "url": "https://www.wikidata.org/", "license": "CC0", "use": "事件、人物、生卒日期、坐标、政权、职位与任职者、阵营成员"},
    {"name": "Maddison Project Database 2023 (Bolt & van Zanden 2024)", "url": "https://doi.org/10.34894/INZBF2",
     "license": "CC BY 4.0", "use": "历史人均 GDP、人口（按现代国家）"},
    {"name": "World Bank World Development Indicators", "url": "https://data.worldbank.org/", "license": "CC BY 4.0",
     "use": "1960 年起的 GDP、人均 GDP、人口、预期寿命、产业结构等"},
    {"name": "维基百科 REST API（中文/英文）", "url": "https://zh.wikipedia.org/api/rest_v1/", "license": "CC BY-SA 4.0",
     "use": "人物/机构/阵营摘要、政权定义（条目首句），在线获取并缓存"},
    {"name": "English Wikipedia — Portal:Current events", "url": "https://en.wikipedia.org/wiki/Portal:Current_events",
     "license": "CC BY-SA 4.0", "use": "每日新闻（1995 年至今，自动更新）"},
    {"name": "Natural Earth", "url": "https://www.naturalearthdata.com/", "license": "Public domain",
     "use": "2011 年至今的现代国家边界"},
    {"name": "QLever (Univ. Freiburg) Wikidata SPARQL", "url": "https://qlever.dev/wikidata", "license": "—",
     "use": "构建数据时查询 Wikidata 的端点"},
    {"name": "Leaflet", "url": "https://leafletjs.com/", "license": "BSD-2-Clause", "use": "地图显示"},
]


def _date(s: str):
    try:
        return parse_date(s)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/meta")
def meta():
    return {"version": config.APP_VERSION, "snapshots": basemaps.index, "modules": registry.manifests(),
            "sources": SOURCES}


@app.get("/api/snapshot")
def snapshot(date: str):
    d = _date(date)
    s = basemaps.snapshot_for(d.y)
    return {"date": date, "date_zh": d.label_zh(), "snapshot": s, "next": basemaps.next_snapshot(s)}


@app.get("/api/basemap/{snap}")
def basemap(snap: int):
    if snap not in basemaps.years:
        raise HTTPException(404, "没有这个快照")
    return Response(basemaps.raw_bytes(snap), media_type="application/geo+json",
                    headers={"Content-Encoding": "gzip", "Cache-Control": "max-age=86400"})


@app.get("/api/polity")
def polity(snap: int, fid: int):
    p = basemaps.polity(snap, fid)
    if not p:
        raise HTTPException(404, "没有这个政权")
    return {"snapshot": snap, **p["props"]}


@app.get("/api/locate")
def locate(date: str, lon: float, lat: float):
    d = _date(date)
    s = basemaps.snapshot_for(d.y)
    p = basemaps.locate(s, lon, lat)
    return {"snapshot": s, "polity": p["props"] if p else None}


@app.get("/api/polity_names")
def polity_names():
    """英文政权名 -> {qid, zh}（由 tools/build_polity_names.py 生成；没有可靠中文名时 zh 为 null）。"""
    f = config.DATA_DIR / "polity_names.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


@app.get("/api/live/status")
def live_status():
    """每日新闻自动更新状态。"""
    return scheduler.STATUS


@app.get("/api/modules")
def modules():
    return registry.manifests()


@app.get("/api/layers/{mid}")
def layer_query(mid: str, date: str, request: Request, limit: int | None = Query(None, le=20000)):
    m = registry.modules.get(mid)
    if not m or m.kind != "layer":
        raise HTTPException(404, f"未知图层 {mid}")
    d = _date(date)
    # 其余查询参数（如经济图层的 ind=指标）原样交给图层模块
    params = {k: v for k, v in request.query_params.items() if k not in ("date", "limit")}
    params["limit"] = limit
    return JSONResponse({"layer": mid, "date": date, **m.layer_query(ctx, d, params)})


@app.get("/api/modules/{mid}")
def module_query(mid: str, date: str, snap: int | None = None, fid: int | None = None,
                 span: float | None = None, limit: int | None = Query(None, le=500), state: str | None = None):
    m = registry.modules.get(mid)
    if not m or m.kind != "panel":
        raise HTTPException(404, f"未知模块 {mid}")
    d = _date(date)
    s = snap if snap is not None else basemaps.snapshot_for(d.y)
    pol = None
    if fid is not None:
        pol = basemaps.polity(s, fid)
        if not pol:
            raise HTTPException(404, "没有这个政权")
    res = m.query(ctx, pol, d, {"span": span, "limit": limit, "snap": s, "state": state})
    return JSONResponse({"module": mid, "date": date, "date_zh": d.label_zh(), "snapshot": s,
                         "polity": pol["props"] if pol else None, **res})


from .details import router as details_router  # noqa: E402

app.include_router(details_router)

_shutdown_cb = None


def set_shutdown(fn) -> None:
    """launcher 把 uvicorn 的 should_exit 接进来。没接时（run.py）就直接结束进程。"""
    global _shutdown_cb
    _shutdown_cb = fn


_QUIT_HTML = """<!doctype html>
<html lang="zh-CN">
<meta charset="utf-8">
<title>退出世界历史地图</title>
<body style="font:16px/1.5 sans-serif;padding:32px;max-width:40em">
<h1>退出世界历史地图</h1>
<p>从「下载」文件夹直接打开时，macOS 经常不弹出终端窗口。软件仍在运行。点下面的按钮即可退出。</p>
<p>如果屏幕上有一个终端窗口，关掉那个窗口也会退出。</p>
<button id="q" style="font-size:16px;padding:8px 16px">退出软件</button>
<p id="m"></p>
<script>
document.getElementById("q").onclick = async () => {
  document.getElementById("m").textContent = "正在退出…";
  try {
    await fetch("/api/shutdown", {method: "POST", headers: {"X-WHA-Shutdown": "1"}});
  } catch (e) {}
  document.getElementById("m").textContent = "已退出。可以关闭这个标签页。";
};
</script>
</body>
</html>
"""


@app.get("/quit")
def quit_page():
    """没有终端窗口时的退出页。本身不结束进程，避免被别的网页用链接悄悄关掉。"""
    return HTMLResponse(_QUIT_HTML)


@app.post("/api/shutdown")
def shutdown(request: Request):
    """只接受本机、且带自定义头的请求。普通跨站表单发不出这个头，所以别的网站关不掉它。"""
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "::1"):
        raise HTTPException(403, "only localhost")
    if request.headers.get("x-wha-shutdown") != "1":
        raise HTTPException(403, "missing shutdown header")

    def _stop():
        time.sleep(0.3)
        if _shutdown_cb:
            _shutdown_cb()
        else:
            os._exit(0)

    threading.Thread(target=_stop, daemon=True).start()
    return {"ok": True, "message": "正在退出"}


@app.get("/")
def index():
    return FileResponse(config.FRONTEND_DIR / "index.html")


app.mount("/", StaticFiles(directory=config.FRONTEND_DIR), name="static")
