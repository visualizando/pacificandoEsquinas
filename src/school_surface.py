"""Integrate widths between sidewalk polygons. Missing intervals are never extrapolated."""
import json
import math
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from shapely.geometry import shape, LineString
from shapely.ops import transform, unary_union
from shapely import make_valid
from shapely.strtree import STRtree
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://data.buenosaires.gob.ar/dataset/veredas/resource/b1ff503e-1b8e-469a-822d-7bcdc53e51cd/download'

def width_at(line, distance, sidewalks):
    p = line.interpolate(distance)
    a, b = line.interpolate(max(0, distance-1)), line.interpolate(min(line.length, distance+1))
    dx, dy = b.x-a.x, b.y-a.y
    norm = math.hypot(dx, dy)
    if norm == 0 or sidewalks.covers(p):
        return None
    nx, ny = -dy/norm, dx/norm
    transect = LineString([(p.x-40*nx, p.y-40*ny), (p.x+40*nx, p.y+40*ny)])
    free = transect.difference(sidewalks)
    parts = [free] if free.geom_type == 'LineString' else getattr(free, 'geoms', [])
    for part in parts:
        if part.geom_type != 'LineString' or part.distance(p) > 1e-6:
            continue
        if any(math.dist(end, edge) < 1e-5 for end in (part.coords[0], part.coords[-1]) for edge in (transect.coords[0], transect.coords[-1])):
            return None
        return part.length if 2 <= part.length <= 40 else None
    return None

def integrate(line, sidewalks):
    # Leave the first/last 10 m out: intersections are not added to released area.
    usable = max(0, line.length-20)
    n = math.ceil(usable/5)
    if not n:
        return 0, 0
    step = usable/n
    area = covered = 0
    for i in range(n):
        width = width_at(line, 10+(i+.5)*step, sidewalks)
        if width is not None:
            area += width*step
            covered += step
    return area, covered

def build():
    path = ROOT/'data/processed/school-streets.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    raw = ROOT/'data/raw/veredas-2019.geojson'
    source = json.loads(raw.read_text(encoding='utf-8-sig'))
    assert source['crs']['properties']['name'].endswith('CRS84')
    project = Transformer.from_crs(4326, 32721, always_xy=True).transform
    print('Preparando veredas…', flush=True)
    sidewalks = [make_valid(transform(project, shape(f['geometry']))) for f in source['features'] if f.get('geometry')]
    del source
    tree = STRtree(sidewalks)
    for f in data['features']:
        geom = transform(project, shape(f['geometry']))
        ids = tree.query(geom.buffer(45))
        nearby = unary_union([sidewalks[int(i)] for i in ids])
        lines = [geom] if geom.geom_type == 'LineString' else geom.geoms
        result = [integrate(line, nearby) for line in lines]
        area, covered = map(sum, zip(*result))
        f['properties'].update(area_m2=round(area, 1) if covered else None, measured_length_m=round(covered, 2), area_method='sidewalk_transects_2019')
    data['metadata']['surface'] = {
        'source': SOURCE, 'source_year': 2019, 'license': 'CC-BY-2.5-AR',
        'generated_at': datetime.now(timezone.utc).isoformat(), 'sha256': hashlib.sha256(raw.read_bytes()).hexdigest(),
        'sample_step_max_m': 5, 'excluded_end_m': 10, 'width_range_m': [2,40],
        'method': 'Sum of valid interval widths × interval lengths. Missing intervals and first/last 10 m excluded. No assumed width.',
    }
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(json.dumps({'area_m2':sum(f['properties']['area_m2'] or 0 for f in data['features']), 'covered_m':sum(f['properties']['measured_length_m'] for f in data['features']), 'blocks_with_area':sum(f['properties']['area_m2'] is not None for f in data['features'])}))

if __name__ == '__main__':
    build()
