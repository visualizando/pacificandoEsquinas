"""Comparable straight-line distance from block centres to current/completed network."""
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from shapely.geometry import shape
from shapely.ops import transform
from shapely.strtree import STRtree
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]


def distances(block, current, total):
    point = block.centroid
    if not block.covers(point):
        point = block.representative_point()
    return (point.distance(current.geometries[current.nearest(point)]),
            point.distance(total.geometries[total.nearest(point)]))


def build():
    source = ROOT / 'data/processed/cycle-completion.json'
    base = json.loads(source.read_text(encoding='utf-8'))
    blocks = json.loads((ROOT / 'data/processed/school-blocks-base.json').read_text(encoding='utf-8'))
    project = Transformer.from_crs(4326, 32721, always_xy=True).transform
    existing = [transform(project, shape(f['geometry'])) for f in base['existing']['features']]
    proposed = [transform(project, shape(f['geometry'])) for f in base['proposed']['features']]
    assert existing, 'Missing existing network'
    current, total = STRtree(existing), STRtree(existing+proposed)
    for i, feature in enumerate(blocks['features']):
        a, b = distances(transform(project, shape(feature['geometry'])), current, total)
        assert b <= a+1e-7
        feature['id'] = i
        feature['properties'] = {'block_id': i+1, 'current_m': round(a, 1), 'total_m': round(b, 1)}
    blocks['metadata'] = {'generated_at': datetime.now(timezone.utc).isoformat(),
                          'method': 'centroid-straight-line-utm21s',
                          'network_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                          'network_generated_at': base['metadata']['generated_at'],
                          'blocks': len(blocks['features']),
                          'description': 'Centroide interior o punto interior alternativo. Distancia euclídea, no por calles. Manzanas esquemáticas de BA Data.'}
    (ROOT / 'data/processed/cycle-coverage.json').write_text(json.dumps(blocks, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(json.dumps({'blocks': len(blocks['features']),
                      'max_current_m': max(f['properties']['current_m'] for f in blocks['features']),
                      'max_total_m': max(f['properties']['total_m'] for f in blocks['features'])}))


if __name__ == '__main__':
    build()
