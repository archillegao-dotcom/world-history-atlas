"""打包结果的接口检查。由 packaging/smoke.sh 调用。

    python packaging/smoke_check.py http://127.0.0.1:18790 /tmp/wha-home
"""
import gzip
import json
import sys
import urllib.request
from pathlib import Path


def fetch(url, timeout):
    req = urllib.request.Request(url, headers={"Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        if r.status != 200:
            raise SystemExit(f"{url} -> HTTP {r.status}")
        return r.read()


def load_json(url, timeout):
    data = fetch(url, timeout)
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return json.loads(data)


def ring_area(ring):
    area = 0.0
    for i, p in enumerate(ring):
        q = ring[(i + 1) % len(ring)]
        area += p[0] * q[1] - q[0] * p[1]
    return abs(area) / 2


def feature_area(feat):
    g = feat["geometry"]
    polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    return sum(ring_area(pl[0]) for pl in polys)


def main():
    base = sys.argv[1].rstrip("/")
    home = Path(sys.argv[2])

    html = fetch(base + "/", 60)
    if "世界历史地图".encode() not in html:
        raise SystemExit("GET / did not return the atlas page")

    meta = load_json(base + "/api/meta", 180)
    by_id = {m["id"]: m for m in meta.get("modules") or []}
    if "events" not in by_id or "cities" not in by_id:
        raise SystemExit(f"modules missing events/cities: {sorted(by_id)}")
    if by_id["events"]["stats"].get("records", 0) < 1000:
        raise SystemExit(f"events did not load: {by_id['events']['stats']}")
    if by_id["cities"]["stats"].get("records", 0) < 100:
        raise SystemExit(f"cities did not load: {by_id['cities']['stats']}")
    print(f"meta version={meta.get('version')} modules={len(by_id)} "
          f"events={by_id['events']['stats'].get('records')} cities={by_id['cities']['stats'].get('records')}")

    status = load_json(base + "/api/live/status", 30)
    if "interval_minutes" not in status:
        raise SystemExit(f"unexpected live status: {status}")

    snap = load_json(base + "/api/snapshot?date=1789-07-14", 60)
    year = snap["snapshot"]
    print(f"snapshot for 1789-07-14: {year}")
    fc = load_json(f"{base}/api/basemap/{year}", 120)
    frances = [f for f in fc["features"] if f["properties"].get("NAME") == "France"]
    if not frances:
        raise SystemExit("basemap has no feature named France")
    frances.sort(key=feature_area, reverse=True)
    fid = frances[0]["properties"]["fid"]
    print(f"France fid={fid}")

    ev = load_json(f"{base}/api/modules/events?date=1789-07-14&snap={year}&fid={fid}&limit=80", 180)
    blob = " ".join(
        f"{it.get('id', '')} {it.get('title', '')} {it.get('title_en', '')}" for it in ev.get("items") or []
    )
    if "Q6539" not in blob and "巴士底" not in blob and "Bastille" not in blob:
        sample = [it.get("title") for it in (ev.get("items") or [])[:8]]
        raise SystemExit(f"1789-07-14 France events did not include the Storming of the Bastille; sample={sample}")
    print(f"events total={ev.get('total')} bastille ok")

    cities = load_json(base + "/api/layers/cities?date=1789-07-14&limit=50", 180)
    items = cities.get("items") or []
    if not items or not cities.get("total"):
        raise SystemExit(f"cities layer empty: {cities}")
    if not (isinstance(items[0].get("coord"), list) and len(items[0]["coord"]) == 2):
        raise SystemExit(f"city item missing coord: {items[0]}")
    print(f"cities returned={len(items)} total={cities.get('total')}")

    note = home / "README.txt"
    if not note.is_file() or note.stat().st_size < 20:
        raise SystemExit(f"first-run seed missing: {note}")
    if (home / "events.json.xz").exists() or (home / "data" / "events.json.xz").exists():
        raise SystemExit("historical seed was copied into the writable user dir; it must stay read-only in the bundle")
    info = json.loads((home / "server.json").read_text(encoding="utf-8"))
    if "port" not in info:
        raise SystemExit(f"server.json missing port: {info}")
    print(f"user dir ok: {home}")
    print("smoke check ok")


if __name__ == "__main__":
    main()
