"""第三批：经济悬停只认所选年份的原值；现代行政区参考线自报身份。
这是接口测试，不是鼠标点击。用法：WHA_PORT=8792 python3 tools/accept/p0_batch3.py
"""
import json, os, sys, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.econ import EconStore, value_at  # noqa: E402

B = f"http://127.0.0.1:{os.environ.get('WHA_PORT', '8792')}"
fails = []


def get(path, **kw):
    return json.load(urllib.request.urlopen(B + path + "?" + urllib.parse.urlencode(kw), timeout=180))


def check(label, cond, got):
    print(("PASS " if cond else "FAIL ") + label + " | " + got)
    if not cond:
        fails.append(label)


S = EconStore(ROOT / "data")
fra = S.series("mpd_gdppc", "FRA")
chn = S.series("mpd_gdppc", "CHN")
years = [y for y, _v in fra]
last = years[-1]
carry = last + 1
gap = 1050  # 中国序列在 1000 与 1090 之间，旧规则会插值
check("法国有 Maddison 人均序列", bool(years) and last >= 2020, str(years[:3]) + "…" + str(years[-3:]))
check("1050 不在中国原表", gap not in [y for y, _v in chn], "1050")
interp = value_at(chn, gap, 100, 5)
carried = value_at(fra, carry, 100, 5)
exact_gap = S.exact_at("mpd_gdppc", "CHN", gap)
exact_last = S.exact_at("mpd_gdppc", "FRA", last)
exact_carry = S.exact_at("mpd_gdppc", "FRA", carry)
check("空档年旧规则会插值", interp is not None and interp.get("interp") == [1000, 1090], str(interp))
check("空档年悬停规则没有值", exact_gap is None, str(exact_gap))
check("末年悬停规则有原值", exact_last and exact_last["year"] == last and "interp" not in exact_last, str(exact_last))
check("末年之后一年旧规则可能沿用", carried is not None and carried.get("carried") and carried.get("year") == last, str(carried))
check("沿用年悬停规则没有值", exact_carry is None, str(exact_carry))

loc = get("/api/locate", date="2011-06-01", lat=48.86, lon=2.35)
fid = (loc.get("polity") or {}).get("fid")
snap = loc.get("snapshot")
check("2011 巴黎能定位", fid is not None, str((loc.get("polity") or {}).get("NAME")))
bj = get("/api/locate", date="2011-06-01", lat=39.9, lon=116.4)
bj_fid = (bj.get("polity") or {}).get("fid")
check("2011 北京能定位", bj_fid is not None, str((bj.get("polity") or {}).get("NAME")))

def values_of(h):
    return [v for c in h.get("countries") or [] for v in c.get("values") or []]

h_gap = get("/api/econ_hover", date=f"{gap}-06-01", snap=bj["snapshot"], fid=bj_fid)
h_last = get("/api/econ_hover", date=f"{last}-06-01", snap=snap, fid=fid)
h_carry = get("/api/econ_hover", date=f"{carry}-06-01", snap=snap, fid=fid)
check("接口空档年没有任何数值", h_gap.get("empty") and not values_of(h_gap), json.dumps(h_gap, ensure_ascii=False)[:240])
check("接口末年有数值、年份、单位、来源", any(
    v.get("year") == last and v.get("unit") and v.get("source") and v.get("v") is not None and "interp" not in v and "carried" not in v
    for v in values_of(h_last)), json.dumps(values_of(h_last), ensure_ascii=False)[:300])
check("接口不把沿用年当成所选年", not values_of(h_carry) and h_carry.get("empty"), json.dumps(h_carry, ensure_ascii=False)[:240])
check("说明写明不是当时政权的账", "不是当时政权" in (h_last.get("note") or ""), h_last.get("note", "")[:80])

low = get("/api/admin1_ref", west=100, south=20, east=120, north=40, zoom=3)
check("缩小到 3 级不返回现代省界", low.get("features") == [] and "不是历史省界" in (low.get("note") or ""), f"n={len(low.get('features') or [])}")
hi = get("/api/admin1_ref", west=110, south=20, east=122, north=35, zoom=6)
feats = hi.get("features") or []
check("放大后有现代行政区线且标明现代", 0 < len(feats) <= 360 and all(
    (f.get("properties") or {}).get("era") == "modern" and "不是历史省界" in ((f.get("properties") or {}).get("note") or "")
    for f in feats) and hi.get("license") == "Public domain", f"n={len(feats)} license={hi.get('license')}")
check("参考线说明不是古代或战时省界", "不是古代" in (hi.get("note") or "") and "战时" in (hi.get("note") or ""), hi.get("note", "")[:90])

print(f"FAILS {len(fails)}")
sys.exit(1 if fails else 0)
