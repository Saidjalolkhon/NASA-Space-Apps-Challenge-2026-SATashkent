"""Download real MOLA elevation around famous Mars locations, and Mars Odyssey's water map, for locations3d.html.

Writes 3d map/sites.js (the location list), 3d map/sites/<id>.js (heightmaps) and 3d map/water.js (soil water map).
Each location gets two grids from the NASA PDS MOLA MEGDR (median topography, metres above the areoid):
  f: 3 deg window at 128 px/deg (~463 m)   c: 20 deg window at 16 px/deg (~3.7 km) for the far horizon.
Only the needed bytes are fetched, with HTTP multi-range requests. Existing heightmaps and water.js are kept; delete one to refetch.
Run: py "3d map/fetch_sites.py"
"""
import base64, json, math, re, struct, sys, urllib.request
from pathlib import Path

PDS = 'https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/'
GRS = 'https://pds-geosciences.wustl.edu/ody/ody-m-grs-5-elements-v1/odgm_xxxx/data/smoothed/h2o_sr_5x5.tab'
OUT = Path(__file__).parent

# Ice seen directly at sites the GRS water map leaves out (it is masked poleward of 57.5 deg)
ICE_SEEN = {'phoenix': 'water ice dug up a few cm down by Phoenix', 'korolev': 'ice mound ~1.8 km thick seen by Mars Express'}

# id, name, lat, lon (east, -180..180), description, points of interest [name, lat, lon]; the first lat/lon is the spawn
SITES = [
    ('jezero', 'Jezero Crater · Perseverance', 18.4447, 77.4508,
     '45 km crater that held a lake ~3.5 billion years ago, with a river delta on its western side. Perseverance landed here on 18 Feb 2021 and is caching rock samples for return to Earth.',
     [['Jezero crater centre', 18.38, 77.58]]),
    ('gale', 'Gale Crater · Curiosity', -4.5895, 137.4417,
     '154 km impact crater with Mount Sharp (Aeolis Mons), a 5.5 km mound of layered sediment, in the middle. Curiosity landed at Bradbury Landing on 6 Aug 2012 and is still climbing the mountain.',
     [['Mount Sharp summit', -5.08, 137.85]]),
    ('olympus', 'Olympus Mons', 18.65, -133.8,
     'Tallest volcano in the Solar System: about 21.9 km above datum and 600 km across, ringed by cliffs up to 8 km high. The summit caldera is roughly 80 × 60 km and 3 km deep.',
     []),
    ('valles', 'Valles Marineris', -13.9, -59.2,
     'Canyon system more than 4,000 km long and up to 7 km deep, torn open by the Tharsis bulge. Walls expose kilometres of layered rock.',
     []),
    ('gusev', 'Gusev Crater · Spirit', -14.5684, 175.4726,
     '166 km crater, likely an old lake fed by the Ma\'adim Vallis channel. Spirit landed on 4 Jan 2004 and found silica-rich soil, a sign of hot springs.',
     []),
    ('meridiani', 'Meridiani Planum · Opportunity', -1.9462, -5.5266,
     'Flat plain rich in grey hematite. Opportunity landed in tiny Eagle crater on 25 Jan 2004 and drove 45 km, reaching 22 km Endeavour crater.',
     [['Victoria crater', -2.05, -5.50], ['Endeavour crater', -2.28, -5.23]]),
    ('insight', 'Elysium Planitia · InSight', 4.502, 135.623,
     'Smooth, flat volcanic plain picked for a safe landing. InSight (26 Nov 2018) recorded over 1,300 marsquakes and measured the size of the core.',
     []),
    ('viking1', 'Chryse Planitia · Viking 1', 22.27, -47.95,
     'First successful Mars landing, 20 July 1976. A smooth plain where ancient outflow floods drained from the highlands.',
     []),
    ('pathfinder', 'Ares Vallis · Pathfinder', 19.13, -33.22,
     'Mouth of a giant flood channel. Pathfinder and Sojourner, the first Mars rover, landed here on 4 July 1997.',
     []),
    ('viking2', 'Utopia Planitia · Viking 2', 47.64, 134.29,
     'Viking 2 landed on 3 Sept 1976 and photographed a thin layer of water frost on the ground in winter.',
     []),
    ('phoenix', 'Vastitas Borealis · Phoenix', 68.22, -125.7,
     'Arctic plain with polygon-patterned ground. Phoenix (25 May 2008) scraped up water ice a few centimetres under the soil.',
     []),
    ('hellas', 'Hellas Planitia', -42.4, 70.5,
     'Floor of the largest visible impact basin on Mars, about 2,300 km wide and 7 km deep. Air pressure down here is nearly double the Martian average.',
     []),
    ('korolev', 'Korolev Crater', 72.77, 164.58,
     '82 km crater in the northern lowlands filled all year round with a mound of water ice about 1.8 km thick.',
     []),
]


def ranges(url, spans):
    """Bytes for each (start, length) span of url, fetched 150 spans per HTTP multi-range request."""
    out = []
    for i in range(0, len(spans), 150):
        part = spans[i:i + 150]
        req = urllib.request.Request(url, headers={'Range': 'bytes=' + ','.join(f'{a}-{a + n - 1}' for a, n in part)})
        body = urllib.request.urlopen(req, timeout=300).read()
        # the server may merge adjacent spans, so cut each span out of whichever returned chunk holds it
        chunks = [(part[0][0], body)] if len(part) == 1 else [
            (int(m[1]), body[m.end():m.end() + int(m[2]) - int(m[1]) + 1])
            for m in re.finditer(rb'Content-Range: bytes (\d+)-(\d+)/\d+\r\n\r\n', body)]
        for a, n in part:
            ca, cb = next((ca, cb) for ca, cb in chunks if ca <= a and a + n <= ca + len(cb))
            out.append(cb[a - ca:a - ca + n])
    return out


def grid(lat, lon, span, ppd):
    """Heights around lat/lon: span deg of latitude, span/cos(lat) of longitude, columns thinned to ~square cells."""
    k = max(1, round(1 / math.cos(math.radians(lat))))
    if ppd == 128:  # 16 tiles of 44 x 90 deg; the window must sit inside one
        top = next(t for t in (88, 44, 0, -44) if t - 44 <= lat - span / 2 and lat + span / 2 <= t)
        lonE = lon % 360
        west = int(lonE // 90) * 90
        url = PDS + f'meg128/megt{abs(top):02d}{"s" if top < 0 else "n"}{west:03d}hb.img'
        cols = 11520
    else:  # one global grid, 90N..90S, 0..360E
        top, west, url, cols = 90, 0, PDS + 'meg016/megt90n000eb.img', 5760
    r0 = int((top - (lat + span / 2)) * ppd)
    ny = int(span * ppd)
    lspan = span / math.cos(math.radians(lat))
    c0 = int(((lon - lspan / 2) % 360 - west) * ppd) if ppd == 128 else int(((lon - lspan / 2) % 360) * ppd)
    nx = int(lspan * ppd) // k
    want = [(c0 + j * k) % cols for j in range(nx)]
    if ppd == 128:
        assert want[-1] > want[0] and c0 >= 0, 'window crosses a MOLA tile edge'
    # per row: one span from the first to the last wanted column, or two if the window wraps 360E
    segs = [(want[0], cols - 1), (0, want[-1])] if want[-1] < want[0] else [(want[0], want[-1])]
    spans = [((r0 + i) * cols + a) * 2 for i in range(ny) for a, _ in segs]
    spans = [(s, (b - a + 1) * 2) for s, (a, b) in zip(spans, segs * ny)]
    data = ranges(url, spans)
    h = []
    for i in range(ny):
        row = b''.join(data[i * len(segs):(i + 1) * len(segs)])
        vals = struct.unpack(f'>{len(row) // 2}h', row)
        h += [vals[(c - want[0]) % cols] for c in want]
    lon0 = west + (c0 + .5) / ppd
    return {'lat0': top - (r0 + .5) / ppd, 'dlat': 1 / ppd, 'lon0': (lon0 + 180) % 360 - 180, 'dlon': k / ppd,
            'ny': ny, 'nx': nx, 'h': h}


def at(g, lat, lon):
    """Nearest grid height at lat/lon."""
    i = round((g['lat0'] - lat) / g['dlat'])
    j = round(((lon - g['lon0'] + 180) % 360 - 180) / g['dlon'])
    return g['h'][i * g['nx'] + j]


def water():
    """Write 3d map/water.js: Mars Odyssey GRS soil water (H2O weight %, top few tens of cm, 2002-2005), 5 deg bins smoothed over 10 deg,
    null where masked, plus h2oAt(lat, lon) to look a point up."""
    rows = [l.split() for l in urllib.request.urlopen(GRS, timeout=120).read().decode().splitlines() if l.strip()]
    rows.sort(key=lambda r: (float(r[0]), float(r[1])))
    v = [None if float(r[2]) > 9000 else float(r[2]) for r in rows]
    assert len(v) == 36 * 72 and all(0 < x < 20 for x in v if x is not None), 'GRS H2O: 36 x 72 bins of a few weight %'
    assert v[int((68.22 + 90) // 5) * 72 + int(234.3 // 5)] is None, 'GRS H2O is masked at the poles (Phoenix, 68N)'
    (OUT / 'water.js').write_text(
        '// Mars Odyssey Gamma Ray Spectrometer soil water: H2O weight % in the top few tens of cm (2002-2005), NASA PDS ODY-M-GRS-5-ELEMENTS-V1\n'
        '// h2o_sr_5x5: 5 deg bins smoothed over 10 deg, rows 87.5S..87.5N, columns 2.5E..357.5E; null where masked (poleward of 57.5 deg)\n'
        f'window.GRS_H2O={json.dumps(v, separators=(",", ":"))};\n'
        '// H2O weight % at lat/lon (deg, east longitude), or null outside the map\n'
        'window.h2oAt=(lat,lon)=>GRS_H2O[Math.min(35,Math.max(0,Math.floor((lat+90)/5)))*72+Math.floor(((lon%360)+360)%360/5)%72];\n',
        encoding='utf-8')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    (OUT / 'sites').mkdir(exist_ok=True)
    if not (OUT / 'water.js').exists():
        print('fetching Odyssey GRS water map', flush=True)
        water()
    meta = []
    for sid, name, lat, lon, desc, pois in SITES:
        meta.append({'id': sid, 'name': name, 'lat': lat, 'lon': lon, 'desc': desc, 'pois': pois, **({'ice': ICE_SEEN[sid]} if sid in ICE_SEEN else {})})
        f = OUT / 'sites' / f'{sid}.js'
        if f.exists():
            g = json.loads(f.read_text(encoding='utf-8').split('"]=', 1)[1].rstrip(';\n'))
            for k in 'fc':
                g[k]['h'] = list(struct.unpack(f'<{g[k]["nx"] * g[k]["ny"]}h', base64.b64decode(g[k]['h'])))
        else:
            print('fetching', sid, flush=True)
            g = {'f': grid(lat, lon, 3, 128), 'c': grid(lat, lon, 20, 16)}
            enc = {k: {**v, 'h': base64.b64encode(struct.pack(f'<{len(v["h"])}h', *v['h'])).decode()} for k, v in g.items()}
            f.write_text(f'(window.SITE_DATA=window.SITE_DATA||{{}})["{sid}"]={json.dumps(enc, separators=(",", ":"))};\n', encoding='utf-8')
        fh = g['f']['h']
        meta[-1]['h'] = at(g['f'], lat, lon)
        print(f'{sid:11} spawn {meta[-1]["h"]:6} m  fine {min(fh):6}..{max(fh):6} m  grid {g["f"]["nx"]}x{g["f"]["ny"]} + {g["c"]["nx"]}x{g["c"]["ny"]}')
        H = {m['id']: m['h'] for m in meta}
        # sanity checks against published numbers: if these fail the grid is misplaced, not just imprecise
        if sid == 'olympus': assert max(fh) > 21000, 'Olympus Mons summit ~21.9 km'
        if sid == 'gale': assert at(g['f'], -5.08, 137.85) - H['gale'] > 4000, 'Mount Sharp rises ~5 km over Bradbury Landing'
        if sid == 'valles': assert max(fh) - min(fh) > 5000, 'Valles Marineris is several km deep'
        if sid == 'hellas': assert H['hellas'] < -6000, 'Hellas floor is ~7 km below datum'
        if sid == 'jezero': assert -3000 < H['jezero'] < -2000, 'Jezero floor ~2.5 km below datum'
    (OUT / 'sites.js').write_text('// Famous Mars locations for locations3d.html; generated by fetch_sites.py (h = MOLA height at the spawn, m)\n'
                                  f'const SITES3D={json.dumps(meta, ensure_ascii=False, indent=0)};\n', encoding='utf-8')


if __name__ == '__main__':
    main()
