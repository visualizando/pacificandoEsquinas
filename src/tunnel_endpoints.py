"""Choose upstream/downstream anchors for single-direction tunnel components."""
import copy
import heapq
import json
import math
from tunnels import DATA, graph, meters, route


def one_way_portals(elements, tunnel_ids):
    selected=[e for e in elements if e['type']=='way' and e['id'] in tunnel_ids]
    if not selected or any(w.get('tags',{}).get('oneway') not in {'yes','1','true','-1'} for w in selected):return None
    outgoing={}; incoming={}; undirected={}
    for w in selected:
        ns=w['nodes'][::-1] if w['tags']['oneway']=='-1' else w['nodes']
        for a,b in zip(ns,ns[1:]):
            outgoing.setdefault(a,set()).add(b);incoming.setdefault(b,set()).add(a)
            undirected.setdefault(a,set()).add(b);undirected.setdefault(b,set()).add(a)
    starts=set(undirected)-set(incoming);ends=set(undirected)-set(outgoing)
    # Paired opposite carriageways are not a single one-way crossing.
    if len(starts)!=1 or len(ends)!=1:return None
    a=next(iter(starts));seen=set();stack=[a]
    while stack:
        n=stack.pop()
        if n not in seen:seen.add(n);stack.extend(outgoing.get(n,set())-seen)
    return (a,next(iter(ends))) if seen==set(undirected) else None


def align_oneway(cases):
    result=copy.deepcopy(cases)
    for c in result:
        es=json.loads((DATA/f'{c["id"]}.osm.json').read_text(encoding='utf-8'))['elements']
        portals=one_way_portals(es,c['tunnel_way_ids'])
        if not portals:continue
        c['single_direction_tunnel']=True
        if c.get('endpoint_method')=='manual_map_review':continue
        car_adj,xy,_,ways=graph(es,'car')
        names={ways[w]['tags'].get('name') for w in c['tunnel_way_ids'] if w in ways}
        forward={};backward={}
        for a,edges in car_adj.items():
            for b,length,w in edges:
                if w in c['tunnel_way_ids'] or ways[w]['tags'].get('name') not in names:continue
                forward.setdefault(a,[]).append((b,length));backward.setdefault(b,[]).append((a,length))
        def extend(start,other,adj):
            base=xy[start];v=((base[0]-xy[other][0])*.82,base[1]-xy[other][1]);norm=math.hypot(*v)
            heap=[(0,start)];dist={start:0};choices=[]
            while heap:
                cost,n=heapq.heappop(heap)
                if cost!=dist[n] or cost>350:continue
                choices.append((abs(cost-120),n,cost))
                for nxt,length in adj.get(n,[]):
                    outward=(((xy[nxt][0]-base[0])*.82*v[0]+(xy[nxt][1]-base[1])*v[1])/max(norm,1e-12))*111195
                    if outward < -5:continue
                    new=cost+length
                    if new<dist.get(nxt,math.inf):dist[nxt]=new;heapq.heappush(heap,(new,nxt))
            return sorted(choices)
        upstream=extend(portals[0],portals[1],backward)
        downstream=extend(portals[1],portals[0],forward)
        # Prefer the target distance, but validate turn restrictions and tunnel use.
        found=None
        for _,a,da in upstream[:4]:
            for _,b,db in downstream[:4]:
                if da<60 or db<60:continue
                r=route(es,xy[a],xy[b],'car',c.get('corridor'))
                if r['status']=='ok' and set(r['osm_way_ids'])&set(c['tunnel_way_ids']) and r['distance_m']<=1.6*meters(xy[a],xy[b]):
                    found=(xy[a],xy[b],da,db);break
            if found:break
        if not found:
            existing=route(es,c['origin'],c['destination'],'car',c.get('corridor'))
            valid=existing['status']=='ok' and bool(set(existing['osm_way_ids'])&set(c['tunnel_way_ids']))
            c['endpoint_alignment_status']='Extremos existentes en el sentido del túnel' if valid else 'No se encontraron extremos directos; revisión manual pendiente'
            continue
        a,b,da,db=found
        c.setdefault('previous_endpoints',{k:copy.deepcopy(c[k]) for k in ('origin','destination','endpoint_method','endpoints')})
        c.update(origin=a,destination=b,endpoint_method='directed_street_120m',portal_extensions_m=[round(da,1),round(db,1)],
                 endpoints=f'A antes de la entrada (+{round(da)} m) → B después de la salida (+{round(db)} m)',
                 audit_status='Extremos orientados con la mano del túnel · accesos peatonales pendientes',
                 endpoint_alignment_status='Ruta vehicular directa comprobada en la instantánea')
        print('Aligned one-way',c['id'],flush=True)
    return result
