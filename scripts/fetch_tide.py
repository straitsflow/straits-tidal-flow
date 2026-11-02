"""Update data/sg_tide.json (Tanjong Pagar HW/LW, MPA predictions published by NEA).
Page: https://www.nea.gov.sg/corporate-functions/weather/tide-timings . Table 1 = current month, table 2 = next month
(table 2 sometimes carries a stray earlier block; only the last day-1..N block is used). Merges with existing events."""
import json, datetime, urllib.request, sys
from html.parser import HTMLParser
URL = "https://www.nea.gov.sg/corporate-functions/weather/tide-timings"
MON = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
class P(HTMLParser):
    def __init__(s): super().__init__(); s.t = []; s.row = None; s.cell = None
    def handle_starttag(s, tag, a):
        if tag == 'table': s.t.append([])
        elif tag == 'tr' and s.t: s.row = []; s.t[-1].append(s.row)
        elif tag in ('td', 'th') and s.row is not None: s.cell = ''
    def handle_endtag(s, tag):
        if tag in ('td', 'th') and s.cell is not None: s.row.append(s.cell.strip()); s.cell = None
    def handle_data(s, d):
        if s.cell is not None: s.cell += d
req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
try: html = urllib.request.urlopen(req, timeout=90).read().decode('utf8', 'ignore')
except Exception as e: print("NEA fetch failed:", e); sys.exit(0)
p = P(); p.feed(html)
today = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).date()
new = []
for t in p.t:
    if not t or not t[0] or t[0][0][:3] not in MON: continue
    mon = MON[t[0][0][:3]]
    year = today.year + (1 if mon < today.month - 6 else 0) - (1 if mon > today.month + 6 else 0)
    blocks, cur = [], None
    for r in t[2:]:
        if len(r) == 4:
            if r[0] == '1': cur = []; blocks.append(cur)
            if cur is None: continue
            day, r = int(r[0]), r[1:]; cur.append((day, r))
        elif len(r) == 3 and cur is not None and cur: cur.append((cur[-1][0], r))
    if not blocks: continue
    for day, (hhmm, h, hl) in blocks[-1]:
        try: dt = datetime.datetime(year, mon, day, int(hhmm[:2]), int(hhmm[2:])) - datetime.timedelta(hours=8)
        except ValueError: continue
        new.append([int(dt.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000), float(h), hl])
print("NEA events parsed:", len(new))
if len(new) < 50: print("too few events; keeping previous"); sys.exit(0)
tide = json.load(open('data/sg_tide.json'))
ev = {e[0]: e for e in tide['events']}
lo = min(e[0] for e in new)
ev = {k: v for k, v in ev.items() if k < lo}; ev.update({e[0]: e for e in new})
cut = (datetime.datetime.utcnow() - datetime.timedelta(days=75)).timestamp() * 1000
tide['events'] = sorted((e for e in ev.values() if e[0] >= cut), key=lambda e: e[0])
json.dump(tide, open('data/sg_tide.json', 'w'), separators=(',', ':'))
print("tide events now", len(tide['events']))
