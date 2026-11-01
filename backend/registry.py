"""
内容模块（插件）注册表。

每个内容层（事件、某类人物……）是一个独立模块，放在 backend/modules/ 下的一个 .py 文件里，
文件中定义 `MODULE = SomeModule(...)`（或 `MODULES = [...]`）。启动时自动发现并注册，
前端通过 /api/modules 获取清单，自动生成侧边栏标签页。新增类别 = 新增一个模块文件。

模块接口（见 ContentModule）：
  id / title / order / description   元信息（前端标签页名称与排序）
  load(ctx)                          启动时加载自己的数据文件（ctx 提供 data_dir 与 basemaps）
  query(ctx, polity, date, params)   返回该政权在该日期的条目列表（统一的 Item 字典格式）
  frontend                           可选：前端自定义渲染脚本 frontend/modules/<id>.js；默认通用列表
  kind                               "panel"（侧边栏标签页，实现 query）或 "layer"（地图图层，实现 layer_query）

统一的 Item 格式（前端通用渲染器使用）：
  {"id": "Q6539", "title": "攻占巴士底狱", "title_en": "...", "date": "1789年7月14日",
   "subtitle": "...", "desc": "...", "coord": [lon, lat], "match": "coord|country",
   "links": [{"label": "Wikidata", "url": "..."}, ...], "score": 123}
"""
from __future__ import annotations

import importlib
import pkgutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .geo import BasemapStore
from .timeutil import HDate


@dataclass
class Context:
    data_dir: Any
    basemaps: BasemapStore
    shared: dict = field(default_factory=dict)  # 模块之间共享的缓存（如国家 QID 标签表）


class ContentModule:
    """侧边栏内容模块（kind="panel"）：点击政权后在侧边栏显示一个标签页。"""
    kind: str = "panel"
    id: str = ""
    title: str = ""
    order: int = 100
    description: str = ""
    frontend: str | None = None  # 例如 "modules/timeline.js"
    source: str = ""             # 数据来源说明（显示在面板底部）

    def load(self, ctx: Context) -> None:  # pragma: no cover - 由子类实现
        pass

    def query(self, ctx: Context, polity: dict | None, date: HDate, params: dict) -> dict:
        raise NotImplementedError

    def stats(self) -> dict:
        return {}

    def manifest(self) -> dict:
        return {"id": self.id, "kind": self.kind, "title": self.title, "order": self.order,
                "description": self.description, "frontend": self.frontend, "source": self.source,
                "stats": self.stats()}


class LayerModule(ContentModule):
    """地图图层模块（kind="layer"）：随日期变化叠加在地图上（如主要城市、以后的阵营着色）。
    后端实现 layer_query(ctx, date, params) -> dict；前端在 frontend 指定的脚本里调用
    WHA.registerLayer(id, {update(data, state), clear()}) 负责绘制。"""
    kind = "layer"
    default_on: bool = True

    def layer_query(self, ctx: Context, date: HDate, params: dict) -> dict:
        raise NotImplementedError

    def manifest(self) -> dict:
        return {**super().manifest(), "default_on": self.default_on}


class Registry:
    def __init__(self) -> None:
        self.modules: dict[str, ContentModule] = {}

    def register(self, m: ContentModule) -> None:
        if m.id in self.modules:
            raise ValueError(f"重复的模块 id: {m.id}")
        self.modules[m.id] = m

    def discover(self, package: str = "backend.modules") -> None:
        """导入 backend/modules 下所有不以 _ 开头的模块文件并注册其中的 MODULE / MODULES。

        源码运行时 pkgutil 能看到这些文件。PyInstaller 把字节码放进 PYZ 后，
        pkgutil 常常是空的，所以再扫一遍 sys._MEIPASS/backend/modules（打包时作为数据放进去的 .py）。
        """
        pkg = importlib.import_module(package)
        names: set[str] = set()
        for info in pkgutil.iter_modules(pkg.__path__):
            if not info.name.startswith("_"):
                names.add(info.name)
        folders = [Path(p) for p in pkg.__path__]
        if getattr(sys, "frozen", False):
            folders.append(Path(getattr(sys, "_MEIPASS", "")) / "backend" / "modules")
        for folder in folders:
            if not folder.is_dir():
                continue
            for py in folder.glob("*.py"):
                if py.name.startswith("_"):  # _common.py、__init__.py 都不是内容模块
                    continue
                names.add(py.stem)
        if not names:
            raise RuntimeError(f"没有找到内容模块（{package}）")
        for name in sorted(names):
            mod = importlib.import_module(f"{package}.{name}")
            for m in ([getattr(mod, "MODULE")] if hasattr(mod, "MODULE") else []) + list(getattr(mod, "MODULES", [])):
                self.register(m)

    def load_all(self, ctx: Context) -> None:
        for m in self.modules.values():
            m.load(ctx)

    def manifests(self) -> list[dict]:
        return sorted((m.manifest() for m in self.modules.values()), key=lambda x: x["order"])
