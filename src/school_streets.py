"""Rebuild school street candidates from BA Data snapshots. Python + shapely + pyproj."""
import json
import re
import unicodedata
import hashlib
import argparse
from urllib.request import urlopen
from collections import defaultdict, Counter
from pathlib import Path
from datetime import datetime, timezone
from shapely.geometry import shape, mapping, Point
from shapely.ops import transform, linemerge, polygonize, unary_union
from shapely.strtree import STRtree
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'schools': 'https://cdn.buenosaires.gob.ar/datosabiertos/datasets/ministerio-de-educacion/establecimientos-educativos/establecimientos_educativos.geojson',
    'streets': 'https://data.buenosaires.gob.ar/dataset/calles/resource/2941f731-0a2e-4391-b8c9-a2912a80c081/download',
}

def tokens(value):
    text = unicodedata.normalize('NFKD', str(value)).encode('ascii', 'ignore').decode().upper()
    return set(re.findall(r'[A-Z]+', text)) - {'AV', 'AVENIDA', 'CALLE', 'PRES', 'GRAL', 'DR', 'INT', 'DE', 'DEL', 'LA', 'EL'}

def similarity(a, b):
    a, b = tokens(a), tokens(b)
    return len(a & b) / max(1, len(a | b))

def levels(text):
    text = text.lower()
    result = [k for k, term in [('inicial', 'inicial'), ('primaria', 'primario'), ('secundaria', 'secundario'), ('superior', 'superior')] if term in text]
    return result or ['otros']

def build():
    raw = ROOT / 'data/schools'
    streets = json.loads((raw / 'streets.geojson').read_text(encoding='utf-8-sig'))['features']
    schools = json.loads((raw / 'establishments.geojson').read_text(encoding='utf-8-sig'))['features']
    project = Transformer.from_crs(4326, 32721, always_xy=True).transform
    geographic = Transformer.from_crs(32721, 4326, always_xy=True).transform
    school_project = Transformer.from_crs(9498, 32721, always_xy=True).transform
    # Collapse cartographic subdivisions only at degree-two nodes of the entire network.
    valid = [f for f in streets if f['geometry'] and f['geometry']['type'] == 'LineString']
    # Quiet schematic background: enclosed cells of the street network, not cadastral parcels.
    cells = polygonize(unary_union([transform(project, shape(f['geometry'])) for f in valid]))
    base = []
    for cell in cells:
        if cell.area < 150:
            continue
        geometry = mapping(transform(geographic, cell.simplify(1, preserve_topology=True)))
        base.append({'type': 'Feature', 'properties': {}, 'geometry': geometry})
    (ROOT / 'data/processed/school-blocks-base.json').write_text(json.dumps({
        'type': 'FeatureCollection', 'features': base,
        'description': 'Manzanas esquemáticas derivadas del callejero BA Data; no catastro.',
    }, separators=(',', ':')), encoding='utf-8')
    ends = defaultdict(list)
    for i, f in enumerate(valid):
        for c in (f['geometry']['coordinates'][0], f['geometry']['coordinates'][-1]):
            ends[tuple(round(x, 7) for x in c)].append(i)
    parent = list(range(len(valid)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for ids in ends.values():
        if len(ids) == 2:
            a, b = ids
            pa, pb = valid[a]['properties'], valid[b]['properties']
            if all(pa.get(k) == pb.get(k) for k in ('codigo', 'tipo_c', 'sentido')):
                parent[find(a)] = find(b)
    groups = defaultdict(list)
    for i in range(len(valid)):
        groups[find(i)].append(valid[i])
    blocks = []
    geometries = []
    ranges = []
    for members in groups.values():
        p = members[0]['properties']
        if p.get('tipo_c') not in {'CALLE', 'AVENIDA', 'PASAJE', 'BOULEVARD'} or p.get('sentido') not in {'CRECIENTE', 'DECRECIENTE', 'DOBLE'}:
            continue
        g = linemerge([shape(f['geometry']) for f in members])
        mg = transform(project, g)
        if mg.length < 5:
            continue
        ids = sorted(f['properties']['id'] for f in members)
        heights = [int(f['properties'].get(k) or 0) for f in members for k in ('alt_izqini', 'alt_izqfin', 'alt_derini', 'alt_derfin')]
        heights = [h for h in heights if h > 0]
        ranges.append((min(heights), max(heights)) if heights else (0, 0))
        geometries.append(mg)
        blocks.append({'type': 'Feature', 'geometry': mapping(g), 'properties': {
            'id': 'c-' + '-'.join(map(str, ids)), 'street': p.get('nomoficial') or 'Sin nombre',
            'avenue': p.get('tipo_c') in {'AVENIDA', 'BOULEVARD'}, 'direction': p.get('sentido'),
            'length_m': round(mg.length, 2), 'schools': [], 'source_segments': ids,
            'address_range': ranges[-1],
        }})
    tree = STRtree(geometries)
    registry = {}
    unresolved = []
    for f in schools:
        p = f['properties']
        key = f"{p.get('cue')}-{p.get('anx')}-{p.get('cui')}"
        if key not in registry:
            registry[key] = {'id': key, 'name': p.get('nam'), 'address': p.get('dir'), 'site': str(p.get('cui') or key),
                             'levels': [], 'sector': p.get('ges'), 'commune': p.get('com'), 'neighborhood': p.get('bar')}
        school = registry[key]
        school['levels'] = sorted(set(school['levels'] + levels(p.get('nen_mde') or '')))
        if not f.get('geometry'):
            unresolved.append({'school': key, 'reason': 'Sin geometría'})
            continue
        pt = transform(school_project, shape(f['geometry']))
        if not (-59 < transform(geographic, pt).x < -58 and -35 < transform(geographic, pt).y < -34):
            unresolved.append({'school': key, 'reason': 'Coordenadas fuera de CABA'})
            continue
        candidates = [int(i) for i in tree.query(pt.buffer(150)) if geometries[int(i)].distance(pt) <= 150]
        assigned = set()
        for address in re.split(r'\s+-\s+', p.get('dir') or ''):
            number = re.search(r'\b(\d+)\b', address)
            height = int(number[1]) if number else None
            ranked = []
            for i in candidates:
                score = similarity(address, blocks[i]['properties']['street'])
                in_range = height is not None and ranges[i][0] <= height <= ranges[i][1] and ranges[i][1] > 0
                distance = geometries[i].distance(pt)
                if score >= .5:
                    ranked.append((not in_range, -score, distance, i))
            ranked.sort()
            if ranked:
                no_range, score, distance, i = ranked[0]
                confident = not no_range and score <= -.65 and distance <= 100
                quality = 'domicilio' if confident else 'revisar'
            elif candidates:
                i = min(candidates, key=lambda j: geometries[j].distance(pt))
                distance, quality = geometries[i].distance(pt), 'revisar'
            else:
                continue
            if i not in assigned:
                entry = {'id': key, 'quality': quality, 'distance_m': round(distance, 1)}
                existing = blocks[i]['properties']['schools']
                if not any(s['id'] == key for s in existing):
                    existing.append(entry)
                assigned.add(i)
        if not assigned:
            unresolved.append({'school': key, 'reason': 'Sin calle candidata a 150 m'})
    result = [b for b in blocks if b['properties']['schools']]
    meta = {'generated_at': datetime.now(timezone.utc).isoformat(), 'sources': SOURCES,
            'license': 'CC-BY-2.5-AR', 'source_records': len(schools), 'unique_establishments': len(registry),
            'eligible_city_blocks': len(blocks), 'school_blocks': len(result), 'unresolved': unresolved,
            'quality_counts': dict(Counter(s['quality'] for b in result for s in b['properties']['schools'])),
            'sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in raw.glob('*.geojson')}}
    output = {'type': 'FeatureCollection', 'features': result, 'schools': registry, 'metadata': meta}
    (ROOT / 'data/processed/school-streets.json').write_text(json.dumps(output, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(json.dumps(meta, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true', help='Refresh the two official source snapshots before rebuilding')
    args = parser.parse_args()
    if args.download:
        raw = ROOT / 'data/schools'
        raw.mkdir(parents=True, exist_ok=True)
        for key, filename in [('schools', 'establishments.geojson'), ('streets', 'streets.geojson')]:
            with urlopen(SOURCES[key], timeout=120) as response:
                payload = response.read()
            parsed = json.loads(payload.decode('utf-8-sig'))
            assert parsed['type'] == 'FeatureCollection' and parsed['features'], filename
            (raw / filename).write_bytes(payload)
    build()
    from school_addresses import build as build_addresses
    build_addresses()
    if (ROOT / 'data/raw/veredas-2019.geojson').exists():
        from school_surface import build as build_surface
        build_surface()
