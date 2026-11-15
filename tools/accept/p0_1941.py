"""本批 P0 复现（1941 维希职务、日治台湾/朝鲜、台南开城、同盟加入日、桂柳会战）。

对已启动的服务发请求。不改历史来迁就失败。
用法：WHA_PORT=8792 python tools/accept/p0_1941.py
"""
import json, os, sys, urllib.parse, urllib.request

B = "http://127.0.0.1:" + os.environ.get("WHA_PORT", "8792")
BARE = __import__("re").compile(r"^Q\d+(@Q\d+)?$")


def get(path, **kw):
    url = B + path
    if kw:
        url += "?" + urllib.parse.urlencode(kw)
    return json.load(urllib.request.urlopen(url, timeout=300))


def locate(date, lat, lon):
    loc = get("/api/locate", date=date, lat=lat, lon=lon)
    p = loc.get("polity") or {}
    reg = get("/api/modules/regime", date=date, snap=loc["snapshot"], fid=p["fid"]) if p else {}
    leaders = get("/api/modules/leaders", date=date, snap=loc["snapshot"], fid=p["fid"]) if p else {}
    st = reg.get("state") or {}
    return loc, st, leaders


fails = []
n = [0]


def check(name, ok, detail):
    n[0] += 1
    print(("PASS " if ok else "FAIL ") + name + " | " + detail)
    if not ok:
        fails.append(name)


# ① 维希 1941-04-25：不出现挂在法国 Q142 上的裸职务，面板职务名不是裸 QID
_, st, leaders = locate("1941-04-25", 46.13, 3.43)
offices = leaders.get("offices") or []
blob = json.dumps(offices, ensure_ascii=False)
names = [o.get("office", {}).get("name") or "" for o in offices]
check("维希不是裸Q1934893", "Q1934893" not in blob and st.get("id") == "Q69808",
      f"state={st.get('id')} {st.get('name')} offices={names[:8]}")
check("维希职务名无裸QID", all(not BARE.match(n) for n in names), " ".join(names[:12]))

# ② 1941-04-25 台北不是中华民国；汉城不是战后朝鲜/韩国
_, tw, _ = locate("1941-04-25", 25.037, 121.564)
check("1941台北=日治台湾", tw.get("id") == "Q137816", f"{tw.get('id')} {tw.get('name')}")
_, kr, _ = locate("1941-04-25", 37.566, 127.0)
check("1941汉城=朝鲜日治", kr.get("id") == "Q503585" and kr.get("id") not in ("Q884", "Q423", "Q865"),
      f"{kr.get('id')} {kr.get('name')}")
# 签约日尚未实控；民主国；台南开城之后才是日治
_, pre, _ = locate("1895-04-20", 25.037, 121.564)
check("1895-04-20台北不是日治也不是中华民国", pre.get("id") not in ("Q137816", "Q865", "Q13426199"),
      f"{pre.get('id')} {pre.get('name')}")
_, formosa, _ = locate("1895-06-15", 25.037, 121.564)
check("1895-06-15台北=台湾民主国", formosa.get("id") == "Q319881", f"{formosa.get('id')} {formosa.get('name')}")
_, after, _ = locate("1895-10-22", 22.99, 120.21)
check("1895-10-22台南=日治", after.get("id") == "Q137816", f"{after.get('id')} {after.get('name')}")
_, kr_before, _ = locate("1910-08-25", 37.566, 127.0)
check("1910-08-25汉城仍是大韩帝国", kr_before.get("id") == "Q28233", f"{kr_before.get('id')} {kr_before.get('name')}")
_, kr_eff, _ = locate("1910-08-29", 37.566, 127.0)
check("1910-08-29汉城=朝鲜日治", kr_eff.get("id") == "Q503585", f"{kr_eff.get('id')} {kr_eff.get('name')}")
_, kara, _ = locate("1910-06-01", 46.96, 142.74)
check("1910南桦太=大日本帝国", kara.get("id") == "Q188712", f"{kara.get('id')} {kara.get('name')}")

# ③ 台南开城
tr = get("/api/treaty/Q5035992")
check("台南开城不叫台南话", "台南话" not in (tr.get("name") or "") and "暂无通用译名" in (tr.get("name") or "")
      and "Capitulation of Tainan" in (tr.get("name") or ""), tr.get("name"))
parties = {p.get("id") for p in tr.get("parties") or []}
check("台南开城当事方不是中华民国", "Q865" not in parties and "Q188712" in parties and "Q319881" in parties,
      str(sorted(parties)))
check("台南开城不用机译摘要", not (tr.get("summary") or {}).get("mt"), str((tr.get("summary") or {}).get("mt")))

# ④ 同盟加入日
def members(date, qid):
    layer = get("/api/layers/alliances", date=date)
    for a in layer.get("alliances") or []:
        if a.get("id") == qid:
            return set(a.get("members") or [])
    return set()

allies_1940 = members("1940-11-15", "Q329888")
check("1940-11苏联不是同盟", "Q15180" not in allies_1940, "USSR" if "Q15180" in allies_1940 else "absent")
check("1940-11南斯拉夫不是同盟", "Q191077" not in allies_1940, "YU" if "Q191077" in allies_1940 else "absent")
check("1941-06-21苏联还不是同盟", "Q15180" not in members("1941-06-21", "Q329888"), "")
check("1941-06-22苏联是同盟", "Q15180" in members("1941-06-22", "Q329888"), "")
check("1941-04-05南斯拉夫还不是同盟", "Q191077" not in members("1941-04-05", "Q329888"), "")
check("1941-04-06南斯拉夫是同盟", "Q191077" in members("1941-04-06", "Q329888"), "")
axis_1940 = members("1940-11-15", "Q43056")
check("1940满洲国汪政权不是轴心成员国", "Q30623" not in axis_1940 and "Q696242" not in axis_1940, "")
# 波罗的海 1940-11：里加若已是苏联领土，不应因苏联从 1939 就算同盟而着成同盟
loc, riga, _ = locate("1940-11-15", 56.95, 24.11)
layer = get("/api/layers/alliances", date="1940-11-15")
fid = str((loc.get("polity") or {}).get("fid"))
pols = set((layer.get("polity_states") or {}).get(fid) or [])
ally_hit = pols & allies_1940
check("1940-11里加不着同盟色", not ally_hit, f"state={riga.get('id')} {riga.get('name')} ally_hit={sorted(ally_hit)}")

# 桂林
_, gl, _ = locate("1944-12-01", 25.27, 110.29)
check("1944-12桂林=日军不是汪政权", gl.get("id") == "Q188712" and "汪" not in (gl.get("name") or ""),
      f"{gl.get('id')} {gl.get('name')}")

print(f"TOTAL {n[0] - len(fails)}/{n[0]}")
if fails:
    print("FAILED:", ", ".join(fails))
    sys.exit(1)
