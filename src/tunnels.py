"""Small, dependency-free OSM pilot. Download snapshots, then build offline.

python src/tunnels.py --download
python src/tunnels.py
"""
from __future__ import annotations
import argparse
import hashlib
import heapq
import json
import math
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'tunnels'
CAR_ROADS = {'motorway','motorway_link','trunk','trunk_link','primary','primary_link',
             'secondary','secondary_link','tertiary','tertiary_link','unclassified',
             'residential','living_street','service'}
WALK_ROADS = CAR_ROADS | {'footway','pedestrian','path','steps','track','cycleway'}
DENIED = {'no','private','customers','delivery','destination'}
MODES = ('car','walk','step_free')

def meters(a, b):
    """Great-circle horizontal distance; inputs are [lon, lat]."""
    lon1, lat1, lon2, lat2 = map(math.radians, (*a, *b))
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371008.8 * 2 * math.asin(min(1, math.sqrt(h)))

def permitted(tags, mode):
    h = tags.get('highway')
    if h not in (CAR_ROADS if mode == 'car' else WALK_ROADS):
        return False
    access = tags.get('motorcar', tags.get('motor_vehicle', tags.get('vehicle', tags.get('access')))) if mode == 'car' else tags.get('foot', tags.get('access'))
    if access in DENIED or tags.get('area') == 'yes' or tags.get('indoor') == 'yes':
        return False
    if mode != 'car':
        if h in {'motorway','motorway_link','trunk','trunk_link','cycleway'} and tags.get('foot') not in {'yes','designated','permissive'}:
            return False
        # Separately mapped sidewalks must be followed on their own geometry.
        if tags.get('sidewalk') == 'separate':
            return False
        if h in CAR_ROADS and tags.get('tunnel') == 'yes' and tags.get('foot') not in {'yes','designated'} and tags.get('sidewalk') not in {'yes','both','left','right'}:
            return False
        if mode == 'step_free' and (h == 'steps' or tags.get('wheelchair') == 'no'):
            return False
    return True

def node_allowed(tags, mode):
    access = tags.get('motorcar', tags.get('motor_vehicle', tags.get('vehicle', tags.get('access')))) if mode == 'car' else tags.get('foot', tags.get('access'))
    if access in DENIED:
        return False
    barrier = tags.get('barrier')
    if mode == 'car' and barrier in {'bollard','block','cycle_barrier','stile','turnstile'}:
        return False
    if mode == 'step_free' and (barrier in {'stile','turnstile'} or tags.get('wheelchair') == 'no' or tags.get('kerb') == 'raised'):
        return False
    return barrier not in {'wall','fence'}

def graph(elements, mode):
    nodes = {e['id']:e for e in elements if e['type']=='node'}
    coords = {k:[n['lon'],n['lat']] for k,n in nodes.items()}
    adj, ways = {}, {}
    for e in elements:
        if e['type'] != 'way' or not permitted(e.get('tags',{}), mode):
            continue
        ways[e['id']] = e
        t = e['tags']
        ow = t.get('oneway', 'yes' if t.get('junction') == 'roundabout' else 'no') if mode == 'car' else t.get('oneway:foot','no')
        for a,b in zip(e['nodes'],e['nodes'][1:]):
            if a not in nodes or b not in nodes or any(not node_allowed(nodes[k].get('tags',{}),mode) for k in (a,b)):
                continue
            length = meters(coords[a],coords[b])
            if ow != '-1': adj.setdefault(a,[]).append((b,length,e['id']))
            if ow not in {'yes','1','true'}: adj.setdefault(b,[]).append((a,length,e['id']))
    return adj, coords, nodes, ways

def restrictions(elements):
    rules, unsupported = {}, 0
    for e in elements:
        if e['type'] != 'relation' or e.get('tags',{}).get('type') != 'restriction': continue
        t = e['tags']
        if 'motorcar' in t.get('except','').split(';'): continue
        members = {m['role']:m for m in e.get('members',[])}
        rule = t.get('restriction:motorcar',t.get('restriction'))
        if set(members) >= {'from','to','via'} and members['via']['type']=='node' and rule:
            key = (members['via']['ref'],members['from']['ref'])
            rules.setdefault(key,[]).append((rule,members['to']['ref']))
        else: unsupported += 1
    return rules, unsupported

def route(elements, origin, destination, mode, corridor=None):
    adj, coords, nodes, ways = graph(elements,mode)
    used = set(adj) | {b for edges in adj.values() for b,_,_ in edges}
    if not used: return {'status':'no_network'}
    anchor_nodes = used
    if mode == 'car' and corridor:
        main = {n for w in ways.values() if w['tags'].get('name')==corridor and w['tags']['highway'] in {'primary','secondary','tertiary'} for n in w['nodes']} & used
        if not main: return {'status':'no_corridor'}
        anchor_nodes = main
    start = min(anchor_nodes,key=lambda n:meters(origin,coords[n]))
    end = min(anchor_nodes,key=lambda n:meters(destination,coords[n]))
    snaps = [meters(origin,coords[start]),meters(destination,coords[end])]
    if max(snaps)>45: return {'status':'snap_too_far','snap_m':[round(v,1) for v in snaps]}
    if start==end: return {'status':'coincident_anchors','snap_m':[round(v,1) for v in snaps]}
    rules, unsupported = restrictions(elements) if mode=='car' else ({},0)
    initial = (start,0,0)
    distances, previous, heap = {initial:0}, {}, [(0,initial)]
    final = None
    while heap:
        cost,state = heapq.heappop(heap)
        if cost != distances[state]: continue
        node, incoming, prior_node = state
        if node == end:
            final = state
            break
        for nxt,length,way in adj.get(node,[]):
            blocked = False
            for rule,to_way in rules.get((node,incoming),[]):
                if rule == 'no_u_turn':
                    blocked |= way == to_way and nxt == prior_node
                elif (rule.startswith('only_') and way != to_way) or (rule.startswith('no_') and way == to_way):
                    blocked=True
            if blocked: continue
            target=(nxt,way,node)
            if cost+length < distances.get(target,math.inf):
                distances[target]=cost+length
                previous[target]=(state,length,way)
                heapq.heappush(heap,(cost+length,target))
    if final is None: return {'status':'no_path','snap_m':[round(v,1) for v in snaps]}
    edges, path = [], [final[0]]
    state = final
    while state != initial:
        before,length,way=previous[state]
        edges.append((length,way))
        path.append(before[0])
        state=before
    edges.reverse(); path.reverse()
    geometry = [coords[n] for n in path]
    step_ways = {w for _,w in edges if ways[w]['tags']['highway']=='steps'}
    wheelchair_no = {w for _,w in edges if ways[w]['tags'].get('wheelchair')=='no'}
    incline_ways = {w for _,w in edges if ways[w]['tags'].get('incline') not in {None,'0','0%','no'}}
    crossing_points = [coords[n] for n in path if nodes[n].get('tags',{}).get('highway')=='crossing']
    for i,(_,w) in enumerate(edges):
        if ways[w]['tags'].get('footway') == 'crossing': crossing_points.append(geometry[i])
    # Nearby annotations may represent the two ends of one crossing.
    clusters=[]
    for p in crossing_points:
        if all(meters(p,c)>20 for c in clusters): clusters.append(p)
    seconds=0
    for length,w in edges:
        t=ways[w]['tags']
        speed = (2.5 if t['highway']=='steps' else 4.5) if mode!='car' else 30
        if mode=='car':
            try: speed=min(30,float(t.get('maxspeed',30)))
            except ValueError: pass
        seconds += length / (max(speed,1)/3.6)
    simplified=[geometry[0]]
    for p in geometry[1:-1]:
        if meters(simplified[-1],p)>=8: simplified.append(p)
    simplified.append(geometry[-1])
    turns=0
    for a,b,c in zip(simplified,simplified[1:],simplified[2:]):
        k=math.cos(math.radians(b[1]))
        u=((b[0]-a[0])*k,b[1]-a[1]); v=((c[0]-b[0])*k,c[1]-b[1])
        delta=abs(math.degrees(math.atan2(u[0]*v[1]-u[1]*v[0],u[0]*v[0]+u[1]*v[1])))
        turns += delta>=40
    implicit=sum(length for length,w in edges if mode!='car' and ways[w]['tags']['highway'] in CAR_ROADS)
    return {'status':'ok','distance_m':round(distances[final],1),'model_minutes':round(seconds/60,1),
            'snap_m':[round(v,1) for v in snaps], 'geometry':{'type':'LineString','coordinates':geometry},
            'osm_way_ids':list(dict.fromkeys(w for _,w in edges)), 'step_way_count':len(step_ways),
            'wheelchair_no_way_count':len(wheelchair_no),
            'incline_way_count':len(incline_ways),
            'mapped_crossings':len(clusters),'turns_approx':turns,'implicit_sidewalk_m':round(implicit,1),
            'unsupported_restrictions':unsupported}

def intersects(a,b,c,d):
    def cross(p,q,r):
        return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    return cross(a,b,c)*cross(a,b,d)<0 and cross(c,d,a)*cross(c,d,b)<0

def build(cases, target=None):
    results=[]
    for case in cases:
        raw=(DATA/f"{case['id']}.osm.json").read_bytes()
        snapshot=json.loads(raw)
        elements=snapshot['elements']
        ways={e['id']:e for e in elements if e['type']=='way'}
        nodes={e['id']:[e['lon'],e['lat']] for e in elements if e['type']=='node'}
        tunnel_ids=case['tunnel_way_ids']
        if any(w not in ways for w in tunnel_ids): raise ValueError('Target tunnel missing from snapshot')
        tunnel_points=[nodes[n] for w in tunnel_ids for n in ways[w]['nodes']]
        railway_segments=[(nodes[a],nodes[b]) for w in ways.values() if w.get('tags',{}).get('railway')=='rail' for a,b in zip(w['nodes'],w['nodes'][1:])]
        has_rail_crossing=any(intersects(nodes[a],nodes[b],c,d) for wid in tunnel_ids for a,b in zip(ways[wid]['nodes'],ways[wid]['nodes'][1:]) for c,d in railway_segments)
        if not has_rail_crossing:
            raise ValueError(f"{case['id']}: target tunnel does not geometrically cross a railway")
        center=[sum(p[i] for p in tunnel_points)/len(tunnel_points) for i in (0,1)]
        directions={}
        for direction,a,b in [('outbound',case['origin'],case['destination']),('return',case['destination'],case['origin'])]:
            routes={mode:route(elements,a,b,mode,case['corridor']) for mode in MODES}
            car=routes['car']
            valid=car['status']=='ok' and bool(set(car['osm_way_ids']) & set(tunnel_ids))
            for mode,r in routes.items():
                if r['status']=='ok' and valid:
                    r['ratio_to_car']=round(r['distance_m']/car['distance_m'],3)
                    r['extra_m']=round(r['distance_m']-car['distance_m'],1)
            walk,free=routes['walk'],routes['step_free']
            penalty=None
            comparable=walk['status']=='ok' and free['status']=='ok' and all(meters(walk['geometry']['coordinates'][i],free['geometry']['coordinates'][i])<=3 for i in (0,-1))
            if comparable and walk['distance_m']>0 and free['distance_m']>=walk['distance_m']:
                penalty={'extra_m':round(free['distance_m']-walk['distance_m'],1),
                         'extra_percent':round(100*(free['distance_m']/walk['distance_m']-1),1),
                         'extra_minutes_distance_only':round((free['distance_m']-walk['distance_m'])/75,1)}
            directions[direction]={'valid_tunnel_crossing':valid,'pedestrian_endpoints_comparable':comparable,'routes':routes,'step_free_penalty':penalty}
        context=[]
        for e in elements:
            if e['type']!='way': continue
            t=e.get('tags',{})
            if t.get('railway')=='rail' or t.get('highway'):
                context.append({'type':'Feature','properties':{'kind':'rail' if t.get('railway')=='rail' else 'street','name':t.get('name','')},'geometry':{'type':'LineString','coordinates':[nodes[n] for n in e['nodes'] if n in nodes]}})
        results.append({**case,'center':center,'snapshot_at':snapshot.get('osm3s',{}).get('timestamp_osm_base'),
                        'sha256':hashlib.sha256(raw).hexdigest(),'directions':directions,
                        'context':{'type':'FeatureCollection','features':context}})
        print(case['id'],json.dumps({d:{m:(r['status'],r.get('distance_m'),r.get('snap_m')) for m,r in v['routes'].items()} for d,v in directions.items()}),flush=True)
    output={'schema_version':1,'method_version':'1.1','source':'OpenStreetMap contributors','license':'ODbL 1.0',
            'license_url':'https://www.openstreetmap.org/copyright','cases':results}
    target=target or ROOT/'data'/'processed'/'tunnels.json'
    target.write_text(json.dumps(output,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print('Built',target)

def download(cases, endpoint):
    for case in cases:
        box = ','.join(map(str, case['bbox']))
        query = f'[out:json][timeout:90];(way[highway]({box});way[railway=rail]({box});relation[type=restriction]({box}););(._;>;);out body;'
        request = Request(endpoint, data=urlencode({'data': query}).encode(),
                          headers={'User-Agent':'PacificandoEsquinas/1.0 (research pilot)'})
        with urlopen(request, timeout=120) as response:
            raw = response.read()
        parsed = json.loads(raw)
        if parsed.get('remark') or not parsed.get('elements'):
            raise ValueError(f"Incomplete Overpass response: {parsed.get('remark')}")
        (DATA / f"{case['id']}.osm.json").write_bytes(raw)
        (DATA / f"{case['id']}.overpassql").write_text(query+'\n',encoding='utf-8')
        print(case['id'], len(parsed['elements']), 'OSM elements', flush=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--inventory', action='store_true', help='List candidate road tunnels in saved snapshots')
    parser.add_argument('--case', help='Process one case ID')
    parser.add_argument('--endpoint', default='https://overpass-api.de/api/interpreter')
    args = parser.parse_args()
    cases = json.loads((DATA / 'cases.json').read_text(encoding='utf-8'))['cases']
    if args.case:
        cases = [c for c in cases if c['id'] == args.case]
        if not cases:
            parser.error('Unknown case ID')
    if args.inventory:
        for c in cases:
            snapshot=json.loads((DATA/f"{c['id']}.osm.json").read_text(encoding='utf-8'))
            for e in snapshot['elements']:
                t=e.get('tags',{})
                if e['type']=='way' and t.get('tunnel')=='yes' and t.get('highway') in CAR_ROADS:
                    print(c['id'],e['id'],t.get('name','unnamed'),flush=True)
    elif args.download:
        download(cases, args.endpoint)
    else:
        if args.case:
            parser.error('--case requires --download or --inventory; build always includes every case')
        build(cases)

if __name__ == '__main__':
    main()
