"""Assemble site/index.html: src/app.src.html + vendor libs + data, fully self-contained (works offline too)."""
import json, os
s = open('src/app.src.html').read()
mpa = json.load(open('data/mpa_data.json')); tide = json.load(open('data/sg_tide.json'))
data = ('const MPA_DATA=' + json.dumps(mpa, separators=(',', ':')) + ';\nconst SG_TIDE=' + json.dumps(tide, separators=(',', ':')) +
        ';\nconst CMEMS=' + (open('data/cmems.json').read() if os.path.exists('data/cmems.json') else 'null') + ';\nconst LAND=' + open('data/land.json').read() + ';\nconst JOHOR=' + open('data/johor_channels.json').read() + ';')
for k, v in {'/*__LEAFLET_CSS__*/': open('src/vendor/leaflet.css').read(), '/*__LEAFLET_JS__*/': open('src/vendor/leaflet.js').read(),
             '/*__CHART_JS__*/': open('src/vendor/chart.js').read(), '/*__DATA__*/': data}.items():
    assert k in s, k; s = s.replace(k, v)
os.makedirs('site', exist_ok=True)
open('site/index.html', 'w').write(s); print('site/index.html', len(s))
