"""Harmonic least-squares fits used by the app outside the published data range.
Phase convention matches app harm(): v = Z + sum amp*cos(speed*t - phase), t = hours since 2000-01-01 UTC."""
import json, math, numpy as np
SPEED = {'M2': 28.9841042, 'S2': 30.0, 'N2': 28.4397295, 'K1': 15.0410686, 'O1': 13.9430356, 'Q1': 13.3986609, 'M4': 57.9682084, 'MS4': 58.9841042}
J2000_MS = 946684800000
def fit(t, y, cons, zkey='Z'):
    t = np.asarray(t, float); y = np.asarray(y, float)
    cols = [np.ones_like(t)]
    for c in cons:
        w = math.radians(SPEED[c]) * t; cols += [np.cos(w), np.sin(w)]
    x, *_ = np.linalg.lstsq(np.column_stack(cols), y, rcond=None)
    o = {zkey: round(float(x[0]), 3)}
    for i, c in enumerate(cons):
        a, b = x[1 + 2 * i], x[2 + 2 * i]
        o[c] = [round(float(math.hypot(a, b)), 3), round(math.degrees(math.atan2(b, a)) % 360, 1)]
    return o
def fit_mpa(st):
    cons = ['M2', 'S2', 'N2', 'K1', 'O1', 'M4', 'MS4']
    t, e, n = [], [], []
    for i, (s, d) in enumerate(zip(st['spd'], st['dir'])):
        if s is None or d is None: continue
        t.append((st['t0'] + i * 3.6e6 - J2000_MS) / 3.6e6)
        r = math.radians(d); e.append(s * math.sin(r)); n.append(s * math.cos(r))
    return {'E': fit(t, e, cons), 'N': fit(t, n, cons)}
def fit_tide(events):
    # events [msUTC, h, 'H'|'L'] -> fit on cosine-interpolated 30-min series between extremes
    t, y = [], []
    for (a, ha, _), (b, hb, _) in zip(events, events[1:]):
        for k in range(int((b - a) / 1.8e6)):
            f = k * 1.8e6 / (b - a); t.append((a + k * 1.8e6 - J2000_MS) / 3.6e6)
            y.append(ha + (hb - ha) * (1 - math.cos(math.pi * f)) / 2)
    return fit(t, y, ['M2', 'S2', 'N2', 'K1', 'O1', 'Q1', 'M4', 'MS4'], 'Z0')
if __name__ == '__main__':
    mpa = json.load(open('data/mpa_data.json'))
    for st in mpa: st['fit'] = fit_mpa(st)
    json.dump(mpa, open('data/mpa_data.json', 'w'), separators=(',', ':'))
    tide = json.load(open('data/sg_tide.json'))
    tide['fit'] = fit_tide(tide['events'])
    json.dump(tide, open('data/sg_tide.json', 'w'), separators=(',', ':'))
    print('fits updated:', len(mpa), 'MPA points; tide events', len(tide['events']))
