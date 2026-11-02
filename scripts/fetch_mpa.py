"""Download MPA Digital Tidal Atlas hourly current predictions (previous, current and next month if published)
and write data/mpa_data.json. Source: https://digitalport-service.mpa.gov.sg/ta/ (no login)."""
import re, json, io, datetime, urllib.request, http.cookiejar, openpyxl, sys
BASE = "https://digitalport-service.mpa.gov.sg/ta/"
POINTS = [("SSP","A","POINTA"),("SSP","B","POINTB"),("SSP","C","POINTC"),("SSP","D","POINTD"),("SSP","ADCP","POINTADCP"),("EBA","A","EBAPOINTA"),("EBA","B","EBAPOINTB")]
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
op.addheaders = [("User-Agent", "Mozilla/5.0 (straits-tidal-flow updater)")]
def get(url):
    try: return op.open(url, timeout=90).read()
    except Exception as e: print("  fail", url, e); return b""
def months():
    d = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).date().replace(day=1)
    prev = (d - datetime.timedelta(days=1)).replace(day=1); nxt = (d + datetime.timedelta(days=32)).replace(day=1)
    return [m.strftime("%Y%m") for m in (prev, d, nxt)]
def xlsx(fid, ym):
    raw = get(BASE + "ExcelServlet?id=" + fid + ym + ".xlsx")
    if raw[:2] != b"PK":   # not an xlsx: open a session through the disclaimer, retry once
        for loc in ("SSP", "EBA"): get(BASE + f"jsp/TA_tidalAtlas.jsp?hid_cmd=pass&hid_locn={loc}")
        raw = get(BASE + "ExcelServlet?id=" + fid + ym + ".xlsx")
    return raw if raw[:2] == b"PK" else None
out = {}
for area, pt, fid in POINTS:
    key = f"{area}_{pt}"
    for ym in (sys.argv[1:] or months()):
        raw = xlsx(fid, ym)
        if not raw: print("missing", key, ym); continue
        rows = list(openpyxl.load_workbook(io.BytesIO(raw), read_only=True).worksheets[0].iter_rows(values_only=True))
        m = re.search(r"Latitude\s*([\d.]+).*?Longitude\s*([\d.]+)", rows[0][0])
        loc = rows[1][0].split(":", 1)[1].strip().strip("'").strip()
        st = out.setdefault(key, {"id": key.lower(), "area": area, "point": pt, "name": loc, "lat": float(m.group(1)), "lng": float(m.group(2)), "obs": {}})
        n = 0
        for r in rows[3:]:
            if r[0] is None: continue
            y, mo, d, h, spd, dr = r[:6]
            t = datetime.datetime(int(y), int(mo), int(d), int(h)) - datetime.timedelta(hours=8)   # SGT -> UTC
            st["obs"][int(t.replace(tzinfo=datetime.timezone.utc).timestamp() // 3600)] = (round(float(spd), 2), round(float(dr))); n += 1
        print("ok", key, ym, n, "hours")
if len(out) < len(POINTS): sys.exit("MPA download incomplete; keeping previous data")
res = []
for st in out.values():
    hs = sorted(st["obs"]); h0 = hs[0]; n = hs[-1] - h0 + 1
    spd = [None] * n; dr = [None] * n
    for h in hs: spd[h - h0], dr[h - h0] = st["obs"][h]
    st.pop("obs"); st.update(t0=h0 * 3600000, spd=spd, dir=dr); res.append(st)
json.dump(res, open("data/mpa_data.json", "w"), separators=(",", ":"))
print("wrote data/mpa_data.json")
