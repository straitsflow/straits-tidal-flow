"""Copernicus Marine SMOC surface currents (tide + circulation + waves), Malacca to mid South China Sea.

Writes data/cmems.json with two grids (fine near Singapore/Malacca, coarse for the wide area). For each:
  fc   : forecast total current (utotal/vtotal), every 2 h, ~6.5 days from now  -> int8, 0.04 kn steps
  harm : tidal harmonics fitted per cell to the past 30 days of SMOC tide component (utide/vtide, FES model),
         used for dates outside the forecast window -> int16, 0.001 kn
Phase convention: v = Z + sum a*cos(w t) + b*sin(w t), t = hours since 2000-01-01 UTC, w = speed deg/h.
Needs COPERNICUSMARINE_SERVICE_USERNAME / _PASSWORD in the environment.
"""
import base64, datetime as dt, json, math, os, sys
import numpy as np
import copernicusmarine as cm

DS = 'cmems_mod_glo_phy_anfc_merged-uv_PT1H-i'
KN = 1.943844
SPEED = {'M2': 28.9841042, 'S2': 30.0, 'N2': 28.4397295, 'K1': 15.0410686, 'O1': 13.9430356, 'M4': 57.9682084}
CONS = list(SPEED)
J2000 = dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)
GRIDS = {   # name: (lon_min, lon_max, lat_min, lat_max, stride on the 1/12 deg native grid)
    'fine':   (99.0, 106.0, -0.5, 4.5, 1),
    'coarse': (98.5, 116.0, -1.5, 12.5, 3),
}
FC_STEP_H, FC_DAYS, HIST_DAYS = 2, 6.5, 30


def b64(a): return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()


def load(var, box, t0, t1, stride):
    ds = cm.open_dataset(dataset_id=DS, variables=var, minimum_longitude=box[0], maximum_longitude=box[1],
                         minimum_latitude=box[2], maximum_latitude=box[3], start_datetime=t0.strftime('%Y-%m-%dT%H:%M:%S'),
                         end_datetime=t1.strftime('%Y-%m-%dT%H:%M:%S'))
    if stride > 1: ds = ds.isel(longitude=slice(0, None, stride), latitude=slice(0, None, stride))
    return ds.load()


def hours_since_j2000(times):
    return np.array([(np.datetime64(t, 's').astype('datetime64[s]').astype(np.int64) - int(J2000.timestamp())) / 3600 for t in times])


def grid(name, box, stride, now):
    # --- forecast window (total current) ---
    f0, f1 = now - dt.timedelta(hours=6), now + dt.timedelta(days=FC_DAYS)
    fc = load(['utotal', 'vtotal'], box, f0, f1, stride)
    lon, lat = fc.longitude.values, fc.latitude.values
    t = fc.time.values[::FC_STEP_H]
    u = fc.utotal.values[::FC_STEP_H] * KN; v = fc.vtotal.values[::FC_STEP_H] * KN    # (t, lat, lon)
    wet = np.isfinite(u).all(0) & np.isfinite(v).all(0)
    idx = np.flatnonzero(wet.ravel())
    q = lambda a: np.clip(np.round(a.reshape(len(t), -1)[:, idx] / 0.04), -127, 127).astype(np.int8)
    # --- tidal harmonics from the past 30 days of the tide component ---
    h0, h1 = now - dt.timedelta(days=HIST_DAYS), now
    hi = load(['utide', 'vtide'], box, h0, h1, stride)
    th = hours_since_j2000(hi.time.values)
    cols = [np.ones_like(th)]
    for c in CONS:
        w = math.radians(SPEED[c]) * th; cols += [np.cos(w), np.sin(w)]
    A = np.column_stack(cols)
    def fit(a):
        y = (a * KN).reshape(len(th), -1)[:, idx]
        y = np.where(np.isfinite(y), y, 0.0)
        x, *_ = np.linalg.lstsq(A, y, rcond=None)              # (1+2n, cells)
        return np.clip(np.round(x / 0.001), -32767, 32767).astype('<i2')
    hu, hv = fit(hi.utide.values), fit(hi.vtide.values)
    t0ms = int((np.datetime64(t[0], 's').astype(np.int64)) * 1000)
    print(f'{name}: {len(lon)}x{len(lat)} grid, {len(idx)} wet cells, {len(t)} forecast steps from {np.datetime_as_string(t[0], "m")}Z')
    return {
        'lon0': round(float(lon[0]), 5), 'lat0': round(float(lat[0]), 5),
        'dlon': round(float(lon[1] - lon[0]), 6), 'dlat': round(float(lat[1] - lat[0]), 6),
        'nx': int(len(lon)), 'ny': int(len(lat)),
        'wet': b64(np.packbits(wet.ravel().astype(np.uint8))), 'nwet': int(len(idx)),
        'fc': {'t0': t0ms, 'dt': FC_STEP_H * 3600000, 'n': int(len(t)), 'scale': 0.04, 'u': b64(q(u)), 'v': b64(q(v))},
        'harm': {'cons': CONS, 'scale': 0.001, 'u': b64(hu), 'v': b64(hv)},
    }


def main():
    if not os.environ.get('COPERNICUSMARINE_SERVICE_USERNAME'):
        print('No Copernicus credentials; keeping previous data'); return 0
    now = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0, tzinfo=None)
    out = {'source': 'Copernicus Marine SMOC (' + DS + ')', 'fetched': now.strftime('%Y-%m-%dT%H:%MZ'), 'grids': {}}
    for name, (*box, stride) in GRIDS.items():
        out['grids'][name] = grid(name, box, stride, now)
    json.dump(out, open('data/cmems.json', 'w'), separators=(',', ':'))
    print('data/cmems.json', os.path.getsize('data/cmems.json'), 'bytes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
