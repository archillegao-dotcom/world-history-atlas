"""经济类模块共用：EconStore 单例。"""
from ..econ import EconStore


def store(ctx) -> EconStore:
    if "econ" not in ctx.shared:
        ctx.shared["econ"] = EconStore(ctx.data_dir)
        ctx.shared["econ"].set_names(ctx.basemaps)
    return ctx.shared["econ"]
