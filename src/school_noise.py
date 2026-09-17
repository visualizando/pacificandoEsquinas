"""Sample official daytime noise bands along school street axes; no extrapolation."""
import csv
import hashlib
import json
import math
from pathlib import Path
from shapely import from_wkt, STRtree
from shapely.geometry import shape
from shapely.ops import transform
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://data.buenosaires.gob.ar/dataset/mapa-ruido/resource/ce377913-43ac-4686-b244-0ac4c55012da/download'

def sample(line, tree, lower):
    n = max(1, math.ceil(line.length / 5))
    bands = []
    for i in range(n):
        hits = tree.query(line.interpolate((i + .5) * line.length / n), predicate='intersects')
        # Shared boundaries: use the higher band, without counting a point twice.
        if len(hits):
            bands.append(max(lower[int(j)] for j in hits))
    ordered = sorted(bands)
    return {'noise_band': ordered[(len(ordered)-1)//2] if ordered else None,
            'coverage_pct': round(len(bands) / n * 100, 1),
            'high_pct': round(sum(b >= 65 for b in bands) / len(bands) * 100, 1) if bands else None}

def build():
    raw = ROOT / 'data/raw/noise-download'
    csv.field_size_limit(100_000_000)
    project = Transformer.from_crs(4326, 32721, always_xy=True).transform
    polygons, lower = [], []
    with raw.open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            assert row['periodo'] == 'Diurno'
            geom = from_wkt(row['wkt'])
            for part in geom.geoms:
                polygons.append(transform(project, part))
                lower.append(float(row['limite_inferior_rango_db']))
    tree = STRtree(polygons)
    schools = json.loads((ROOT / 'data/processed/school-streets.json').read_text(encoding='utf-8'))
    rows = []
    for feature in schools['features']:
        p = feature['properties']
        rows.append({'id': p['id'], 'street': p['street'], 'schools': len({s['id'] for s in p['schools']}),
                     **sample(transform(project, shape(feature['geometry'])), tree, lower)})
    output = {'source': SOURCE, 'sha256': hashlib.sha256(raw.read_bytes()).hexdigest(),
              'threshold_db': 65, 'step_m': 5, 'rows': rows}
    (ROOT / 'data/processed/school-noise.json').write_text(json.dumps(output, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print('Total:', len(rows), 'coverage >=80%:', sum(r['coverage_pct'] >= 80 for r in rows),
          'majority >=65:', sum(r['coverage_pct'] >= 80 and r['high_pct'] >= 50 for r in rows))

if __name__ == '__main__':
    build()
