"""几何计算的线程锁（v0.6.1）。
FastAPI 同步接口在线程池里并发执行；两个请求同时合成同一张边界（如 /api/snapshot 与 /api/basemap 同时请求 1900 年），
会对同一个共享几何对象并发调用 shapely.prepare，GEOS 内部重复释放内存导致整个服务进程崩溃（"double free or corruption"）。
合成与缓存读取统一加一把可重入锁：命中缓存时只是很短的加锁，未命中时并发请求排队、第二个请求直接用第一个算好的结果。"""
from __future__ import annotations

import threading
from functools import lru_cache, wraps

GEO_LOCK = threading.RLock()


def locked_lru(maxsize):
    def deco(fn):
        cached = lru_cache(maxsize=maxsize)(fn)

        @wraps(fn)
        def w(*a, **k):
            with GEO_LOCK:
                return cached(*a, **k)
        w.cache_clear = cached.cache_clear
        w.cache_info = cached.cache_info
        return w
    return deco
