"""Local address lookup index from the same official street snapshot."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def build():
    data = json.loads((ROOT/'data/processed/school-streets.json').read_text(encoding='utf-8'))
    byid = {i:f['properties']['id'] for f in data['features'] for i in f['properties']['source_segments']}
    streets = json.loads((ROOT/'data/schools/streets.geojson').read_text(encoding='utf-8-sig'))
    rows = []
    for f in streets['features']:
        p, g = f['properties'], f.get('geometry')
        if not g or g['type'] != 'LineString':
            continue
        rows.append({'street':p.get('nomoficial') or '', 'alias':p.get('nom_mapa') or '',
            'ranges':[[p.get('alt_izqini') or 0,p.get('alt_izqfin') or 0],[p.get('alt_derini') or 0,p.get('alt_derfin') or 0]],
            'block':byid.get(p['id']), 'point':g['coordinates'][len(g['coordinates'])//2]})
    (ROOT/'data/processed/school-addresses.json').write_text(json.dumps(rows, ensure_ascii=False, separators=(',',':')), encoding='utf-8')
if __name__ == '__main__':
    build()
