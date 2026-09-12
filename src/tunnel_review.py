"""Reproducible endpoint diagnostics and validated manual endpoint overrides."""
import argparse
import copy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OVERRIDES = ROOT / 'data/tunnels/endpoint-overrides.json'


def audit(case, direction):
    from tunnels import meters
    car, free = (direction['routes'][m] for m in ('car', 'step_free'))
    reasons = []
    if not direction['valid_tunnel_crossing']:
        reasons.append('El auto no atraviesa el túnel elegido.')
    if case.get('endpoint_method') != 'manual_map_review' and any(n < 60 for n in case.get('portal_extensions_m', [])):
        reasons.append('Hay un extremo a menos de 60 m del portal.')
    straight = meters(case['origin'], case['destination'])
    ratio = car.get('distance_m', 0) / max(straight, 1)
    if car['status'] == 'ok' and ratio > 1.6:
        reasons.append('Rodeo vehicular a revisar: supera 1,6 veces la distancia recta.')
    separation = None
    if car['status'] == free['status'] == 'ok':
        separation = [round(meters(car['geometry']['coordinates'][i], free['geometry']['coordinates'][i]), 1) for i in (0, -1)]
        if max(separation) > 20:
            reasons.append('Auto y caminata ajustan sus extremos a más de 20 m entre sí.')
        if max(car['snap_m'] + free['snap_m']) > 20:
            reasons.append('Algún extremo se ajusta más de 20 m a la red.')
    else:
        reasons.append('Falta una de las dos rutas principales.')
    if case['id'] == 'osm_440436964':
        reasons.append('Altolaguirre: falta verificar las conexiones de veredas, escaleras y rampas.')
    usable = not reasons and car.get('distance_m', 0) > 0
    extra = round(free['distance_m'] - car['distance_m'], 1) if usable else None
    return {'reasons': reasons, 'car_circuity': round(ratio, 2),
            'endpoint_separation_m': separation, 'comparison_usable': usable,
            'extra_m': extra,
            'extra_percent': round(100 * extra / car['distance_m'], 1) if usable else None}


def apply_overrides(cases, payload):
    """All-or-nothing validation; no OSM or access tags are invented."""
    from tunnels import meters
    result = copy.deepcopy(cases)
    known = {c['id']: c for c in result}
    if payload.get('schema_version') != 1 or not isinstance(payload.get('cases'), list):
        raise ValueError('Formato de revisión no compatible')
    seen = set()
    for item in payload['cases']:
        cid = item.get('id')
        if cid not in known or cid in seen:
            raise ValueError(f'Cruce desconocido o duplicado: {cid}')
        seen.add(cid)
        c = known[cid]
        for key in ('origin', 'destination'):
            p = item.get(key)
            if not isinstance(p, list) or len(p) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in p):
                raise ValueError(f'{cid}: coordenadas inválidas')
            south, west, north, east = c['bbox']
            if not west <= p[0] <= east or not south <= p[1] <= north:
                raise ValueError(f'{cid}: extremo fuera de la instantánea; ampliar los datos primero')
            baseline = item.get('baseline', {}).get(key)
            if baseline != c[key] and p != c[key]:
                raise ValueError(f'{cid}: revisión desactualizada; volver a exportar desde los resultados actuales')
        if meters(item['origin'], item['destination']) < 30:
            raise ValueError(f'{cid}: los extremos deben estar separados al menos 30 m')
        if c.get('single_direction_tunnel'):
            from tunnels import route
            elements=json.loads((ROOT/f'data/tunnels/{cid}.osm.json').read_text(encoding='utf-8'))['elements']
            car=route(elements,item['origin'],item['destination'],'car',c.get('corridor'))
            if car['status']!='ok' or not set(car['osm_way_ids'])&set(c['tunnel_way_ids']):
                raise ValueError(f'{cid}: A debe quedar antes de la entrada y B después de la salida, en la mano del túnel')
        c.update(origin=item['origin'], destination=item['destination'],
                 endpoint_method='manual_map_review', endpoint_review_notes=str(item.get('notes', ''))[:2000],
                 endpoints='A y B revisados en el mapa', audit_status='Extremos revisados en mapa · accesos pendientes')
        c.pop('portal_extensions_m', None)
    return result


def load_overrides(cases):
    return apply_overrides(cases, json.loads(OVERRIDES.read_text(encoding='utf-8'))) if OVERRIDES.exists() else cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-endpoints', type=Path)
    args = parser.parse_args()
    if args.import_endpoints:
        base = json.loads((ROOT/'data/tunnels/cases_all.json').read_text(encoding='utf-8'))['cases']
        old = json.loads(OVERRIDES.read_text(encoding='utf-8')) if OVERRIDES.exists() else {'schema_version': 1, 'cases': []}
        current = apply_overrides(base, old)
        incoming = json.loads(args.import_endpoints.read_text(encoding='utf-8'))
        apply_overrides(current, incoming)
        merged = {c['id']: c for c in old['cases']}
        for item in incoming['cases']:
            item = copy.deepcopy(item)
            original = next(c for c in base if c['id'] == item['id'])
            item['baseline'] = {k: original[k] for k in ('origin', 'destination')}
            merged[item['id']] = item
        payload = {'schema_version': 1, 'cases': list(merged.values())}
        apply_overrides(base, payload)
        OVERRIDES.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(f'{len(incoming["cases"])} revisiones importadas. Ejecutar python src/tunnels_batch.py para recalcular.')
    else:
        data = json.loads((ROOT/'data/processed/tunnels-all.json').read_text(encoding='utf-8'))
        report = [{'id': c['id'], 'name': c['name'], 'directions': {key: audit(c, d) for key, d in c['directions'].items()}} for c in data['cases']]
        target = ROOT/'data/processed/tunnel-endpoint-audit.json'
        target.write_text(json.dumps({'schema_version': 1, 'cases': report}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(f'Auditoría de {len(report)} cruces: {target}')


if __name__ == '__main__':
    main()
