"""Reproducible OSM candidate inventory; download once, rebuild offline thereafter."""
import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from tunnels import intersects, meters, CAR_ROADS

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/tunnels/city-inventory.osm.json'
QUERY = '''[out:json][timeout:180];
area["ISO3166-2"="AR-C"]["boundary"="administrative"]->.city;
(way(area.city)[highway][tunnel][tunnel!="no"];way(area.city)[railway=rail];);
out geom;'''

def build():
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    ways = [e for e in raw['elements'] if e['type'] == 'way' and e.get('geometry')]
    coords = lambda w: [[p['lon'], p['lat']] for p in w['geometry']]
    rails = [w for w in ways if w.get('tags', {}).get('railway') == 'rail']
    segments = [(a,b) for w in rails for a,b in zip(coords(w), coords(w)[1:])]
    candidates = []
    for w in ways:
        t = w.get('tags', {})
        if t.get('highway') not in CAR_ROADS or t.get('tunnel') in (None, 'no', 'building_passage'): continue
        points = coords(w)
        if not any(intersects(a,b,c,d) for a,b in zip(points,points[1:]) for c,d in segments): continue
        center = [sum(p[i] for p in points)/len(points) for i in (0,1)]
        candidates.append({'name':t.get('name','Paso sin nombre en OSM'), 'center':center, 'way_ids':[w['id']]})
    # Opposite carriageways may be distinct OSM ways. Merge only same-name neighbors.
    merged = []
    for c in sorted(candidates, key=lambda c:c['way_ids'][0]):
        match = next((m for m in merged if m['name']==c['name'] and meters(m['center'],c['center'])<100),None)
        if match: match['way_ids'] += c['way_ids']
        else: merged.append(c)
    pilot = json.loads((ROOT/'data/processed/tunnels.json').read_text(encoding='utf-8'))
    config = json.loads((ROOT/'data/tunnels/cases.json').read_text(encoding='utf-8'))
    for case in pilot['cases']:
        ids = next(c['tunnel_way_ids'] for c in config['cases'] if c['id']==case['id'])
        match = next((m for m in merged if set(ids)&set(m['way_ids'])),None)
        if match is None:
            match = {'name':case['name'],'center':case['center'],'way_ids':ids,'from_pilot':True}
            merged.append(match)
        match['case_id']=case['id']; match['name']=case['name']
    result={'source':'OpenStreetMap','snapshot_at':raw.get('osm3s',{}).get('timestamp_osm_base'),
            'method':'CABA administrative area; road tunnel geometrically crossing railway=rail; same-name carriageways within 100 m grouped. Candidates, not exhaustive census.',
            'sites':sorted(merged,key=lambda c:c['name']),
            'rails':{'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':{'type':'LineString','coordinates':coords(w)}} for w in rails]}}
    (ROOT/'data/processed/tunnel-inventory.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    print(f"{len(merged)} candidate sites; {len(rails)} railway ways")

if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--download',action='store_true'); args=parser.parse_args()
    if args.download:
        req=Request('https://overpass-api.de/api/interpreter',data=urlencode({'data':QUERY}).encode(),headers={'User-Agent':'PacificandoCiudad/1.0 research'})
        with urlopen(req,timeout=240) as response: body=response.read()
        parsed=json.loads(body)
        if parsed.get('remark') or not parsed.get('elements'): raise ValueError('Incomplete or empty Overpass response')
        RAW.write_bytes(body)
        RAW.with_suffix('.overpassql').write_text(QUERY,encoding='utf-8')
    build()
