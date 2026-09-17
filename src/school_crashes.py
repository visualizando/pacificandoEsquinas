"""Unique injury crashes within 50 m of school street axes, including endpoints."""
import csv
import hashlib
import json
from datetime import time
from pathlib import Path
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform
from shapely import STRtree

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://data.buenosaires.gob.ar/dataset/victimas-siniestros-viales/resource/40ec993a-00ad-40e5-936f-0a25f8d2c90b/download'

def school_hours(value):
    try:
        hour = time.fromisoformat(value.strip())
    except (ValueError, AttributeError):
        return None
    return time(7) <= hour < time(18)

def build():
    raw = ROOT / 'data/raw/siniestros_viales_hechos.csv'
    project = Transformer.from_crs(4326,32721,always_xy=True).transform
    events, seen, missing = [], set(), 0
    unknown_time, outside_time, in_window = 0, 0, 0
    with raw.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f,delimiter=';'):
            if not 2019 <= int(r['anio_siniestro']) <= 2025:
                continue
            key=r['id_siniestro']
            if key in seen:
                continue
            seen.add(key)
            eligible = school_hours(r['hora_siniestro'])
            if eligible is None:
                unknown_time += 1
                continue
            if not eligible:
                outside_time += 1
                continue
            in_window += 1
            try:
                lon,lat=float(r['longitud_siniestro']),float(r['latitud_siniestro'])
                if not (-59 < lon < -58 and -35 < lat < -34):
                    raise ValueError()
            except ValueError:
                missing+=1
                continue
            events.append({'id':key,'severity':r['gravedad_siniestro'],'deaths':int(r['numero_victimas_mortal_siniestro']),
                           'point':Point(*project(lon,lat))})
    tree=STRtree([e['point'] for e in events])
    schools=json.loads((ROOT/'data/processed/school-streets.json').read_text(encoding='utf-8'))
    rows, all_hits=[],set()
    school_hits = {}
    for f in schools['features']:
        line=transform(project,shape(f['geometry']))
        hits={int(i) for i in tree.query(line,predicate='dwithin',distance=50)}
        all_hits.update(hits)
        p=f['properties']
        for link in p['schools']:
            school_hits.setdefault(link['id'], set()).update(hits)
        rows.append({'id':p['id'],'street':p['street'],'events':len(hits),
                     'deaths':sum(events[i]['deaths'] for i in hits)})
    school_rows = [{'id':key,'events':len(hits)} for key,hits in sorted(school_hits.items())]
    result={'school_rows':school_rows,'unlinked_schools':len(set(schools['schools'])-set(school_hits)),
            'source':SOURCE,'sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'period':[2019,2025],
            'radius_m':50,'events_total':in_window,'all_hours_events_total':len(seen),
            'time_window':'07:00 inclusive–18:00 exclusive','unknown_time_events':unknown_time,
            'outside_time_events':outside_time,'unlocated_events':missing,
            'located_events':len(events),'nearby_unique_events':len(all_hits),
            'nearby_severity':{severity:sum(events[i]['severity']==severity for i in all_hits) for severity in ['LEVE','GRAVE','MORTAL']},
            'nearby_deaths':sum(events[i]['deaths'] for i in all_hits),'rows':rows}
    (ROOT/'data/processed/school-crashes.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print({k:v for k,v in result.items() if k not in ('rows','school_rows')})
    print('Escuelas:',len(school_rows),'con hechos:',sum(r['events']>0 for r in school_rows))
    print('Cuadras con hechos:',sum(r['events']>0 for r in rows))

if __name__=='__main__':
    build()
