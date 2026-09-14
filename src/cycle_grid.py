"""Baseline cycle grid on OSM streets. Offline, deterministic; not an optimum."""
import json
import math
import heapq
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone
from shapely.geometry import LineString, Point, shape, mapping
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
SPACING = 900
ROAD_TYPES = {'residential', 'living_street', 'unclassified', 'primary', 'secondary',
              'tertiary', 'primary_link', 'secondary_link', 'tertiary_link'}


def infrastructure(tags):
    if tags.get('highway') in {'construction', 'proposed', 'disused'}:
        return False
    if tags.get('highway') == 'cycleway':
        return True
    if tags.get('highway') in {'path', 'footway'} and tags.get('bicycle') == 'designated':
        return True
    return any(tags.get(k) in {'lane', 'track', 'opposite_lane', 'opposite_track'}
               for k in ('cycleway', 'cycleway:left', 'cycleway:right', 'cycleway:both'))


def shortest_path(graph, start, end, cost):
    distances, previous, queue = {start: 0}, {}, [(0, start)]
    while queue:
        distance, node = heapq.heappop(queue)
        if distance != distances[node]:
            continue
        if node == end:
            result = []
            while node != start:
                node, edge = previous[node]
                result.append(edge)
            return result[::-1]
        for neighbor, edge in graph[node]:
            candidate = distance + cost(edge)
            if candidate < distances.get(neighbor, math.inf):
                distances[neighbor] = candidate
                previous[neighbor] = (node, edge)
                heapq.heappush(queue, (candidate, neighbor))
    return []


def extensions(graph, edges, xy):
    """Continue degree-one ends of established street corridors; never seed a grid."""
    existing_graph = defaultdict(list)
    for i, e in enumerate(edges):
        if e['existing']:
            existing_graph[e['a']].append((e['b'], i))
            existing_graph[e['b']].append((e['a'], i))
    selected, corridors = defaultdict(list), []
    def unit(a, b):
        dx, dy = xy[b][0]-xy[a][0], xy[b][1]-xy[a][1]
        length = math.hypot(dx, dy)
        return (dx/length, dy/length)
    def dot(a, b):
        return a[0]*b[0]+a[1]*b[1]
    # Existing long edges are also used to detect parallel infrastructure nearby.
    existing_ids = [i for i, e in enumerate(edges) if e['existing'] and e['length'] > 15]
    tree = STRtree([edges[i]['geometry'] for i in existing_ids])
    for start in sorted(existing_graph):
        if len(existing_graph[start]) != 1:
            continue
        neighbor, first = existing_graph[start][0]
        # Ignore tiny cartographic stubs: require 200 m of connected infrastructure behind.
        previous, cursor, back_length = start, neighbor, edges[first]['length']
        visited = {start, neighbor}
        while back_length < 200:
            options = [(n, i) for n, i in existing_graph[cursor] if n not in visited]
            if not options:
                break
            heading = unit(previous, cursor)
            n, i = max(options, key=lambda pair: dot(heading, unit(cursor, pair[0])))
            if dot(heading, unit(cursor, n)) < .8:
                break
            back_length += edges[i]['length']
            previous, cursor = cursor, n
            visited.add(n)
        if back_length < 200:
            continue
        heading = unit(neighbor, start)
        initial = heading
        current, previous_street, route, length = start, edges[first]['street'], [], 0
        visited = {start}
        reason = 'Sin continuación suficientemente recta'
        while length < 3000:
            options = []
            for n, i in graph[current]:
                e = edges[i]
                if n in visited or e['existing'] or i in selected:
                    continue
                direction = unit(current, n)
                if dot(heading, direction) < .866 or dot(initial, direction) < .707:
                    continue
                if length+e['length'] > 3000:
                    continue
                midpoint = e['geometry'].interpolate(.5, normalized=True)
                parallel = False
                for k in tree.query(midpoint, predicate='dwithin', distance=400):
                    other = edges[existing_ids[k]]
                    if abs(dot(direction, unit(other['a'], other['b']))) < .94:
                        continue
                    nearest = other['geometry'].interpolate(other['geometry'].project(midpoint))
                    dx, dy = nearest.x-midpoint.x, nearest.y-midpoint.y
                    along = abs(dx*direction[0]+dy*direction[1])
                    lateral = abs(dx*direction[1]-dy*direction[0])
                    if 40 < lateral < 400 and along < 50:
                        parallel = True
                        break
                if not parallel:
                    options.append((dot(heading, direction)+(.05 if e['street']==previous_street else 0), -i, n, i))
            if not options:
                break
            _, _, n, i = max(options)
            route.append(i)
            length += edges[i]['length']
            heading, previous_street = unit(current, n), edges[i]['street']
            current = n
            visited.add(n)
            if existing_graph.get(current):
                reason = 'Conecta con la red existente'
                break
            if length >= 2900:
                reason = 'Límite de exploración de 3 km'
        if length < 150:
            continue
        cid = f'P{len(corridors)+1:03d}'
        corridors.append({'id': cid, 'length_m': round(length, 1), 'start_node': start,
                          'end_node': current, 'street': edges[first]['street'],
                          'stop_reason': reason, 'edge_count': len(route)})
        for i in route:
            selected[i].append(cid)
    return selected, corridors


def build():
    project = Transformer.from_crs(4326, 32721, always_xy=True).transform
    geographic = Transformer.from_crs(32721, 4326, always_xy=True).transform
    streets = json.loads((ROOT / 'data/schools/streets.geojson').read_text(encoding='utf-8-sig'))
    # Street coverage, not an administrative boundary. Keeps the existing CABA scope.
    street_lines = [transform(project, shape(f['geometry'])) for f in streets['features']
                    if f.get('geometry')]
    street_tree = STRtree(street_lines)
    def local_footprint(line):
        nearby = street_tree.query(line, predicate='dwithin', distance=60)
        return unary_union([street_lines[i].buffer(60, quad_segs=4) for i in nearby])
    print('CABA street footprint ready', flush=True)
    osm = json.loads((ROOT / 'data/cycling/city-network.osm.json').read_text(encoding='utf-8'))
    nodes = {n['id']: (n['lon'], n['lat']) for n in osm['elements'] if n['type'] == 'node'}
    xy = {n: project(*p) for n, p in nodes.items()}
    existing, edges, graph = [], [], defaultdict(list)
    for way in osm['elements']:
        if way['type'] != 'way':
            continue
        tags = way.get('tags', {})
        refs = way.get('nodes', [])
        if len(refs) < 2 or any(n not in xy for n in refs):
            continue
        line = LineString([xy[n] for n in refs])
        is_existing = infrastructure(tags)
        if is_existing:
            clipped = line.intersection(local_footprint(line))
            parts = [clipped] if clipped.geom_type == 'LineString' else getattr(clipped, 'geoms', [])
            for part in parts:
                if part.geom_type == 'LineString' and part.length > 1:
                    existing.append({'type': 'Feature', 'geometry': mapping(transform(geographic, part)),
                                     'properties': {'osm_id': way['id'], 'street': tags.get('name', 'Ciclovía sin nombre'),
                                                    'length_m': round(part.length, 1), 'kind': 'existing'}})
        if tags.get('highway') not in ROAD_TYPES or tags.get('access') in {'private', 'no'}:
            continue
        for a, b in zip(refs, refs[1:]):
            segment = LineString([xy[a], xy[b]])
            if segment.length < .1 or not local_footprint(segment).covers(segment):
                continue
            idx = len(edges)
            edges.append({'a': a, 'b': b, 'geometry': segment, 'length': segment.length,
                          'street': tags.get('name', 'Calle sin nombre'), 'osm_id': way['id'],
                          'existing': is_existing})
            graph[a].append((b, idx))
            graph[b].append((a, idx))
    print(f'Graph ready: {len(edges)} edges; {len(existing)} existing lines', flush=True)
    routing_nodes = sorted(graph)
    routing_index = {n: i for i, n in enumerate(routing_nodes)}
    routing = {'version': 1, 'osm_date': osm['osm3s']['timestamp_osm_base'],
               'nodes': [[round(v, 7) for v in nodes[n]] for n in routing_nodes],
               'edges': [[routing_index[e['a']], routing_index[e['b']], round(e['length'], 2)] for e in edges]}
    (ROOT / 'data/processed/cycle-routing.json').write_text(json.dumps(routing, separators=(',', ':')), encoding='utf-8')
    existing_lines = [transform(project, shape(f['geometry'])) for f in existing]
    existing_tree = STRtree(existing_lines)
    for edge in edges:
        if not edge['existing']:
            nearby = existing_tree.query(edge['geometry'], predicate='dwithin', distance=18)
            if len(nearby):
                local_buffer = unary_union([existing_lines[i].buffer(18) for i in nearby])
                edge['existing'] = edge['geometry'].intersection(local_buffer).length / edge['length'] >= .8
    print('Existing infrastructure matched', flush=True)
    selected, corridors = extensions(graph, edges, xy)
    proposed = []
    for i, ids in sorted(selected.items()):
        e = edges[i]
        proposed.append({'type': 'Feature', 'geometry': mapping(transform(geographic, e['geometry'])),
                         'properties': {'kind': 'proposed', 'osm_id': e['osm_id'], 'street': e['street'],
                                        'length_m': round(e['length'], 1), 'corridors': ', '.join(ids)}})
    metadata = {'generated_at': datetime.now(timezone.utc).isoformat(),
                'osm_date': osm['osm3s']['timestamp_osm_base'], 'max_extension_m': 3000,
                'existing_km': round(sum(f['properties']['length_m'] for f in existing)/1000, 1),
                'proposed_km': round(sum(f['properties']['length_m'] for f in proposed)/1000, 1),
                'corridors': corridors, 'method': 'existing-corridor-extensions-v2',
                'scope': 'Calles de CABA (BA Data), buffer de 60 m; no límite administrativo exacto.'}
    output = {'metadata': metadata, 'existing': {'type': 'FeatureCollection', 'features': existing},
              'proposed': {'type': 'FeatureCollection', 'features': proposed}}
    (ROOT / 'data/processed/cycle-grid.json').write_text(json.dumps(output, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(json.dumps({k: v for k, v in metadata.items() if k != 'corridors'}, ensure_ascii=False))
    print(f'{len(existing)} existing features; {len(proposed)} proposed edges; {len(corridors)} corridors')


if __name__ == '__main__':
    build()
