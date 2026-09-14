"""Union the reviewed user drawing and automatic extensions on shared street edges."""
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
from shapely.geometry import LineString, shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]


def edge_key(a, b):
    return tuple(sorted((tuple(round(v, 7) for v in a), tuple(round(v, 7) for v in b))))


def build():
    read = lambda p: json.loads((ROOT / p).read_text(encoding='utf-8-sig'))
    base = read('data/processed/cycle-grid.json')
    user = read('data/cycling/user-proposal.json')
    routing = read('data/processed/cycle-routing.json')
    osm = read('data/cycling/city-network.osm.json')
    project = Transformer.from_crs(4326, 32721, always_xy=True).transform
    nodes = {n['id']: (n['lon'], n['lat']) for n in osm['elements'] if n['type'] == 'node'}
    road_info = {}
    for way in osm['elements']:
        if way['type'] != 'way':
            continue
        for a, b in zip(way.get('nodes', []), way.get('nodes', [])[1:]):
            road_info[edge_key(nodes[a], nodes[b])] = (way['id'], way.get('tags', {}).get('name', 'Calle sin nombre'))
    allowed = {edge_key(routing['nodes'][a], routing['nodes'][b]) for a, b, _ in routing['edges']}
    merged, occurrences = {}, defaultdict(int)
    input_length = 0
    for origin, features in [('manual', user['geometry']['features']), ('automatic', base['proposed']['features'])]:
        for f in features:
            assert f['geometry']['type'] == 'LineString'
            coordinates = f['geometry']['coordinates']
            for a, b in zip(coordinates, coordinates[1:]):
                key = edge_key(a, b)
                if key[0] == key[1]:
                    continue
                assert key in allowed, f'Tramo fuera del grafo: {key}'
                line = LineString([project(*p) for p in key])
                input_length += line.length
                occurrences[origin] += 1
                if key not in merged:
                    merged[key] = {'line': line, 'origins': set(), 'corridors': set()}
                merged[key]['origins'].add(origin)
                merged[key]['corridors'].add(f['properties'].get('name') or f['properties'].get('corridors', 'Automático'))
    existing = [transform(project, shape(f['geometry'])) for f in base['existing']['features']]
    tree = STRtree(existing)
    features, excluded, excluded_length = [], 0, 0
    for key, item in sorted(merged.items()):
        line = item['line']
        near = tree.query(line, predicate='dwithin', distance=18)
        if len(near) and line.intersection(unary_union([existing[i].buffer(18) for i in near])).length / line.length >= .8:
            excluded += 1
            excluded_length += line.length
            continue
        osm_id, street = road_info[key]
        features.append({'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': list(key)},
                         'properties': {'kind': 'proposed', 'street': street, 'osm_id': osm_id,
                                        'length_m': round(line.length, 2), 'origins': ', '.join(sorted(item['origins'])),
                                        'corridors': ', '.join(sorted(item['corridors']))}})
    unique_length = sum(i['line'].length for i in merged.values())
    audit = {'manual_corridors': len(user['geometry']['features']),
             'empty_corridors': sum(not r['points'] for r in user['corridors']),
             'input_occurrences': dict(occurrences), 'unique_edges_before_existing': len(merged),
             'duplicate_occurrences_removed': sum(occurrences.values())-len(merged),
             'duplicate_km_removed': round((input_length-unique_length)/1000, 2),
             'existing_edges_removed': excluded, 'existing_km_removed': round(excluded_length/1000, 2),
             'shared_manual_automatic_edges': sum(len(i['origins']) == 2 for i in merged.values())}
    metadata = {**base['metadata'], 'method': 'completion-union-v1', 'generated_at': datetime.now(timezone.utc).isoformat(),
                'proposed_km': round(sum(f['properties']['length_m'] for f in features)/1000, 2),
                'label': 'Ciclovías para completar la red', 'merge_audit': audit}
    metadata.pop('corridors', None)
    output = {'metadata': metadata, 'existing': base['existing'], 'proposed': {'type': 'FeatureCollection', 'features': features}}
    (ROOT / 'data/processed/cycle-completion.json').write_text(json.dumps(output, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(json.dumps({'km': metadata['proposed_km'], 'segments': len(features), **audit}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    build()
