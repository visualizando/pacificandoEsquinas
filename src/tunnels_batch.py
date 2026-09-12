"""Expand every inventoried site. Preserve the original pilot and its endpoints."""
import argparse
import json
import heapq
import math
import time
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from tunnels import ROOT, DATA, build, meters, permitted

RAW=DATA/'city-network.osm.json'

def download(sites):
    minimum_date=json.loads((ROOT/'data/processed/tunnel-inventory.json').read_text(encoding='utf-8'))['snapshot_at'][:10]
    xs=[s['center'][0] for s in sites]; ys=[s['center'][1] for s in sites]
    south,north=min(ys)-.015,max(ys)+.015
    merged={}; dates=[]
    for i in range(6):
        box=f'{south+(north-south)*i/6},{min(xs)-.018},{south+(north-south)*(i+1)/6},{max(xs)+.018}'
        query=f'[out:json][timeout:90];(way[highway]({box});way[railway=rail]({box});relation[type=restriction]({box}););(._;>;);out body;'
        cache=DATA/f'city-network-part-{i}.json'
        cached=cache.read_bytes() if cache.exists() else None
        cache_valid=cached and json.loads(cached).get('osm3s',{}).get('timestamp_osm_base','')[:10]>=minimum_date
        if cache_valid: body=cached
        else:
            if cached: cache.with_suffix('.rejected.json').write_bytes(cached)
            combined={}; tile_dates=[]
            for tile in range(4):
                s,w,n,e=map(float,box.split(','));mid=(w+e)/2;ymid=(s+n)/2
                tile_box=f'{s if tile<2 else ymid},{w if tile%2==0 else mid},{ymid if tile<2 else n},{mid if tile%2==0 else e}'
                tile_query=query.replace(box,tile_box).replace('[timeout:90]','[timeout:60]')
                tile_cache=DATA/f'city-network-part-{i}-tile-{tile}.json'
                if tile_cache.exists():parsed=json.loads(tile_cache.read_bytes())
                else:
                    for attempt in range(4):
                        try:
                            req=Request('https://overpass-api.de/api/interpreter',data=urlencode({'data':tile_query+f'\n/* attempt {attempt} */'}).encode(),headers={'User-Agent':'PacificandoCiudad/1.1 research'})
                            with urlopen(req,timeout=90) as response:parsed=json.load(response)
                            break
                        except Exception:
                            if attempt==3:raise
                            print('Retry tile',i,tile,attempt+1,flush=True);time.sleep(10)
                    if parsed.get('remark') or not parsed.get('elements'):raise ValueError('Incomplete response')
                    if parsed.get('osm3s',{}).get('timestamp_osm_base','')[:10]<minimum_date:raise ValueError('Stale snapshot')
                    tile_cache.write_text(json.dumps(parsed),encoding='utf-8');tile_cache.with_suffix('.overpassql').write_text(tile_query,encoding='utf-8')
                tile_dates.append(parsed['osm3s']['timestamp_osm_base'])
                for element in parsed['elements']:combined[(element['type'],element['id'])]=element
                print('Downloaded block/tile',i+1,tile+1,flush=True)
            body=json.dumps({'osm3s':{'timestamp_osm_base':max(tile_dates),'tile_timestamps':tile_dates},'elements':list(combined.values())}).encode()
        result=json.loads(body)
        if result.get('remark') or not result.get('elements'): raise ValueError('Incomplete Overpass response')
        cache.write_bytes(body);cache.with_suffix('.overpassql').write_text(query,encoding='utf-8')
        dates.append(result.get('osm3s',{}).get('timestamp_osm_base'))
        for e in result['elements']: merged[(e['type'],e['id'])]=e
        print('Downloaded block',i+1,len(result['elements']),'elements',flush=True)
    RAW.write_text(json.dumps({'osm3s':{'timestamp_osm_base':max(dates),'block_timestamps':dates},'elements':list(merged.values())}),encoding='utf-8')

def prepare(sites):
    snapshot=json.loads(RAW.read_text(encoding='utf-8'))
    nodes={e['id']:e for e in snapshot['elements'] if e['type']=='node'}
    ways={e['id']:e for e in snapshot['elements'] if e['type']=='way'}
    relations=[e for e in snapshot['elements'] if e['type']=='relation']
    xy=lambda n:[nodes[n]['lon'],nodes[n]['lat']]
    cases=json.loads((DATA/'cases.json').read_text(encoding='utf-8'))['cases']
    for c in cases: c['endpoint_method']='pilot_manual';c['audit_status']='Auditoría de campo pendiente'
    for site in sites:
        if site.get('case_id'): continue
        ids=site['way_ids']; tunnel=ways[ids[0]]; name=tunnel.get('tags',{}).get('name')
        center=site['center']; radius=.014
        near={n for n in nodes if abs(xy(n)[0]-center[0])<radius/.82 and abs(xy(n)[1]-center[1])<radius}
        local=[w for w in ways.values() if any(n in near for n in w['nodes'])]
        used={n for w in local for n in w['nodes']}
        local_ids={w['id'] for w in local}
        local_rel=[r for r in relations if any(m['type']=='way' and m['ref'] in local_ids for m in r.get('members',[]))]
        elements=[nodes[n] for n in sorted(used)]+local+local_rel
        # Extend each portal along the same named street, without following tunnel edges.
        adj={}
        for w in local:
            t=w.get('tags',{})
            if w['id'] in ids or not permitted(t,'car') or (name and t.get('name')!=name): continue
            for a,b in zip(w['nodes'],w['nodes'][1:]):
                length=meters(xy(a),xy(b));adj.setdefault(a,[]).append((b,length));adj.setdefault(b,[]).append((a,length))
        def extend(start,other):
            base=xy(start);opposite=xy(other)
            vx=(base[0]-opposite[0])*.82;vy=base[1]-opposite[1];norm=math.hypot(vx,vy)
            def outward(n):
                p=xy(n)
                return (((p[0]-base[0])*.82*vx+(p[1]-base[1])*vy)/norm*111195) if norm else 0
            heap=[(0,start)]; distances={start:0}; choices=[]
            while heap:
                distance,n=heapq.heappop(heap)
                if distance!=distances[n] or distance>350: continue
                choices.append((abs(distance-120),n,distance))
                for nxt,length in adj.get(n,[]):
                    if outward(nxt)<-5:continue
                    new=distance+length
                    if new<distances.get(nxt,math.inf):distances[nxt]=new;heapq.heappush(heap,(new,nxt))
            _,n,distance=min(choices)
            return xy(n),round(distance,1)
        tunnel_adj={}
        for wid in ids:
            for u,v in zip(ways[wid]['nodes'],ways[wid]['nodes'][1:]):
                tunnel_adj.setdefault(u,set()).add(v);tunnel_adj.setdefault(v,set()).add(u)
        component=set();queue=[tunnel['nodes'][0]]
        while queue:
            u=queue.pop()
            if u in component:continue
            component.add(u);queue.extend(tunnel_adj.get(u,set())-component)
        tips=sorted(n for n in component if len(tunnel_adj[n])==1)
        if len(tips)>=2:
            portal_a,portal_b=max(((u,v) for u in tips for v in tips if u<v),key=lambda pair:meters(xy(pair[0]),xy(pair[1])))
            if meters(xy(portal_b),xy(tunnel['nodes'][0]))<meters(xy(portal_a),xy(tunnel['nodes'][0])):portal_a,portal_b=portal_b,portal_a
        else:portal_a,portal_b=tunnel['nodes'][0],tunnel['nodes'][-1]
        a,da=extend(portal_a,portal_b);b,db=extend(portal_b,portal_a)
        case_id='osm_'+str(ids[0])
        c={'id':case_id,'name':site['name'],'corridor':None,'origin':a,'destination':b,'center':center,
           'bbox':[center[1]-radius,center[0]-radius/.82,center[1]+radius,center[0]+radius/.82],
           'endpoints':f'Extremos automáticos fuera de portales: A +{da} m / B +{db} m',
           'tunnel_way_ids':ids,'endpoint_method':'same_street_120m_from_portals','portal_extensions_m':[da,db],
           'audit_status':'Extremos automáticos · revisión visual pendiente'}
        (DATA/f'{case_id}.osm.json').write_text(json.dumps({'osm3s':snapshot.get('osm3s',{}),'elements':elements}),encoding='utf-8')
        cases.append(c);print('Prepared',case_id,site['name'],da,db,flush=True)
    (DATA/'cases_all.json').write_text(json.dumps({'cases':cases},ensure_ascii=False,indent=2),encoding='utf-8')
    return cases

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--download',action='store_true');p.add_argument('--prepare',action='store_true',help='Explicitly regenerate automatic endpoints; existing configuration is otherwise preserved');p.add_argument('--align-oneway',action='store_true',help='Orient automatic anchors upstream/downstream of one-way tunnels');args=p.parse_args()
    sites=json.loads((ROOT/'data/processed/tunnel-inventory.json').read_text(encoding='utf-8'))['sites']
    if args.download:
        # Refresh every case snapshot, including pilots, without regenerating anchors.
        from tunnels import download as download_cases
        configured=json.loads((DATA/'cases_all.json').read_text(encoding='utf-8'))['cases']
        for case in configured:
            for attempt in range(3):
                try:
                    download_cases([case], ['https://overpass.kumi.systems/api/interpreter','https://overpass-api.de/api/interpreter'][attempt%2])
                    break
                except Exception:
                    if attempt==2:raise
                    time.sleep(5)
    config=DATA/'cases_all.json'
    regenerate=args.prepare or not config.exists()
    cases=prepare(sites) if regenerate else json.loads(config.read_text(encoding='utf-8'))['cases']
    from tunnel_review import load_overrides
    if args.align_oneway or regenerate:
        from tunnel_endpoints import align_oneway
        # Keep exported manual edits separate and never overwrite them here.
        cases=align_oneway(cases)
        config.write_text(json.dumps({'cases':cases},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    build(load_overrides(cases),ROOT/'data/processed/tunnels-all.json')
