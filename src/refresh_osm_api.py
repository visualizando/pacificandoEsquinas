"""Refresh saved case areas from OSM read API, then rebuild with our local router.

Downloads are staged; failed runs do not replace active snapshots or results.
No OSM edits and no automatic endpoint changes.
"""
import json
import argparse
import shutil
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from tunnels import DATA, ROOT, build
from tunnel_review import load_overrides

def parse(raw):
    root = ET.fromstring(raw)
    elements = []
    for item in root:
        if item.tag not in ('node', 'way', 'relation'):
            continue
        e = {'type': item.tag, 'id': int(item.attrib['id']),
             'tags': {t.attrib['k']: t.attrib['v'] for t in item.findall('tag')}}
        if item.tag == 'node':
            e.update(lat=float(item.attrib['lat']), lon=float(item.attrib['lon']))
        elif item.tag == 'way':
            e['nodes'] = [int(n.attrib['ref']) for n in item.findall('nd')]
        else:
            e['members'] = [{**m.attrib, 'ref': int(m.attrib['ref'])} for m in item.findall('member')]
        elements.append(e)
    nodes = {e['id'] for e in elements if e['type'] == 'node'}
    ways = [e for e in elements if e['type'] == 'way' and ('highway' in e['tags'] or e['tags'].get('railway') == 'rail')]
    if not ways or any(n not in nodes for w in ways for n in w['nodes']):
        raise ValueError('Incomplete map response')
    return [e for e in elements if e['type'] != 'way'] + ways

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resume', help='Existing refresh-run directory name')
    args = parser.parse_args()
    cases = json.loads((DATA/'cases_all.json').read_text(encoding='utf-8'))['cases']
    stamp = args.resume or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    if '/' in stamp or '\\' in stamp or stamp in ('.', '..'):
        raise ValueError('Invalid run name')
    stage = DATA/'refresh-runs'/stamp
    if args.resume and not stage.is_dir():
        raise ValueError('Refresh run not found')
    stage.mkdir(parents=True, exist_ok=bool(args.resume))
    for c in cases:
        saved = stage/f'{c["id"]}.osm.json'
        if args.resume and saved.exists():
            snapshot = json.loads(saved.read_text(encoding='utf-8'))
            if not snapshot.get('elements'):
                raise ValueError('Incomplete saved snapshot')
            print(c['id'], 'reusing downloaded snapshot', flush=True)
            continue
        s,w,n,e = c['bbox']
        url = f'https://api.openstreetmap.org/api/0.6/map?bbox={w},{s},{e},{n}'
        req = Request(url, headers={'User-Agent': 'PacificandoEsquinas/1.0 local map review'})
        with urlopen(req, timeout=45) as response:
            raw = response.read()
        elements = parse(raw)
        snapshot = {'osm3s': {'timestamp_osm_base': datetime.now(timezone.utc).isoformat()},
                    'source_url': url, 'timestamp_note': 'Retrieval time from live OSM API, not an atomic database snapshot', 'elements': elements}
        (stage/f'{c["id"]}.osm.json').write_text(json.dumps(snapshot), encoding='utf-8')
        print(c['id'], len(elements), 'downloaded', flush=True)
        time.sleep(1)
    backup = stage/'previous'
    backup.mkdir()
    for c in cases:
        name = f'{c["id"]}.osm.json'
        shutil.copy2(DATA/name, backup/name)
        shutil.copy2(stage/name, DATA/name)
    try:
        build(load_overrides(cases), stage/'tunnels-all.json')
    except Exception:
        for c in cases:
            name = f'{c["id"]}.osm.json'
            shutil.copy2(backup/name, DATA/name)
        raise
    shutil.copy2(stage/'tunnels-all.json', ROOT/'data/processed/tunnels-all.json')
    print('Updated all cases:', stage, flush=True)

if __name__ == '__main__':
    main()
