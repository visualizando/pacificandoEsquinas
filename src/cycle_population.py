"""Census-area population assigned to representative centre distances, not homes."""
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from shapely.geometry import shape
from shapely.ops import transform
from shapely import make_valid
from shapely.strtree import STRtree
from pyproj import Transformer
try:
    from .cycle_coverage import distances
except ImportError:
    from cycle_coverage import distances

ROOT = Path(__file__).resolve().parents[1]


def build():
    source = ROOT / 'data/processed/cycle-completion.json'
    network = json.loads(source.read_text(encoding='utf-8'))
    census = json.loads((ROOT / 'data/cycling/census-input.geojson').read_text(encoding='utf-8-sig'))
    assert census['type'] == 'FeatureCollection'  # The supplied file is GeoJSON despite its name.
    project = Transformer.from_crs(4326, 32721, always_xy=True).transform
    lines = [transform(project, shape(f['geometry'])) for f in network['existing']['features']]
    additions = [transform(project, shape(f['geometry'])) for f in network['proposed']['features']]
    current, total = STRtree(lines), STRtree(lines+additions)
    features, seen = [], set()
    for f in census['features']:
        p = f['properties']; identifier = str(p['link'])
        assert identifier not in seen
        seen.add(identifier)
        age_key = next(k for k in p if '0 a 14' in k)
        population = float(p['poblacion'])
        percentage = float(str(p[age_key]).replace(',', '.'))
        assert population >= 0 and 0 <= percentage <= 100
        geom = make_valid(transform(project, shape(f['geometry'])))
        a, b = distances(geom, current, total)
        assert b <= a+1e-7
        features.append({'type': 'Feature', 'id': len(features), 'geometry': f['geometry'],
                         'properties': {'radio': identifier, 'comuna': p.get('depto', ''),
                                        'population': population, 'age_0_14_pct': percentage,
                                        'age_0_14_est': population*percentage/100,
                                        'current_m': round(a, 1), 'total_m': round(b, 1)}})
    metadata = {'generated_at': datetime.now(timezone.utc).isoformat(),
                'network_generated_at': network['metadata']['generated_at'],
                'network_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'source': 'Archivo cabaTopojson.json aportado por el usuario; campo sag=INDEC; procedencia no verificada.',
                'census_year': None, 'age_definition': '0 a 14 años inclusive',
                'method': 'Población íntegra de cada radio asignada a la distancia euclídea de su centroide interior o punto interior alternativo. No es distancia domiciliaria.',
                'population': sum(f['properties']['population'] for f in features),
                'age_0_14_est': sum(f['properties']['age_0_14_est'] for f in features),
                'radios': len(features)}
    result = {'type': 'FeatureCollection', 'features': features, 'metadata': metadata}
    (ROOT / 'data/processed/cycle-population.json').write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(json.dumps(metadata, ensure_ascii=False))


if __name__ == '__main__':
    build()
