"""Run nine independent ORS checks. Set ORS_API_KEY in the process environment.

Preserves current published results. Archives payloads (never auth headers),
responses and engine metadata for inspection and repeatability.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://api.heigit.org/openrouteservice/v2/directions'

def main():
    key = os.environ.get('ORS_API_KEY')
    if not key:
        raise SystemExit('Set ORS_API_KEY in the process environment.')
    data = json.loads((ROOT/'data/processed/tunnels-all.json').read_text(encoding='utf-8'))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder = ROOT/'data/processed/ors-trials'/stamp
    folder.mkdir(parents=True, exist_ok=False)
    rows = []
    for cid in ['osm_10054711', 'beiro', 'osm_440436964']:
        case = next(c for c in data['cases'] if c['id'] == cid)
        for mode in ['car', 'walk', 'step_free']:
            profile = 'driving-car' if mode == 'car' else 'foot-walking'
            payload = {'coordinates': [case['origin'], case['destination']],
                       'preference': 'shortest', 'instructions': True,
                       'radiuses': [45, 45]}
            if mode == 'step_free':
                payload['options'] = {'avoid_features': ['steps']}
            url = f'{BASE}/{profile}/geojson'
            request = Request(url, data=json.dumps(payload).encode(), headers={
                'Authorization': key, 'Content-Type': 'application/json'})
            record = {'case_id': cid, 'name': case['name'], 'mode': mode,
                      'url': url, 'request': payload,
                      'local_distance_m': case['directions']['outbound']['routes'][mode].get('distance_m')}
            try:
                with urlopen(request, timeout=45) as response:
                    result = json.load(response)
                record['response'] = result
                summary = result['features'][0]['properties']['summary']
                record['distance_m'] = summary['distance']
                record['duration_s'] = summary['duration']
                record['status'] = 'ok'
            except HTTPError as error:
                record.update(status='error', http_status=error.code)
                print(f'{case["name"]} {mode}: HTTP {error.code}', flush=True)
                if error.code in (401, 403, 429):
                    (folder/'failure.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
                    raise SystemExit('Authentication or quota error; no further requests made.')
            (folder/f'{cid}-{mode}.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
            rows.append({k: v for k, v in record.items() if k not in ('response', 'request')})
            print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    (folder/'summary.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Results: {folder}', flush=True)

if __name__ == '__main__':
    main()
