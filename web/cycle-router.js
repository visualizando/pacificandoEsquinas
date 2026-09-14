(function(root){
'use strict';
class CycleRouter {
  constructor(data){this.osm_date=data.osm_date;this.nodes=data.nodes;this.adj=this.nodes.map(()=>[]);for(const [a,b,d] of data.edges){this.adj[a].push([b,d]);this.adj[b].push([a,d]);}}
  nearest(p){let best=-1,distance=Infinity;this.nodes.forEach((n,i)=>{const d=Math.hypot((n[0]-p[0])*91600,(n[1]-p[1])*111200);if(d<distance){distance=d;best=i;}});if(distance>120)throw Error('Marcá un punto a menos de 120 m de una calle disponible.');return best;}
  path(start,end){
    const dist=new Float64Array(this.nodes.length).fill(Infinity),prev=new Int32Array(this.nodes.length).fill(-1),heap=[];
    function push(item){let i=heap.length;heap.push(item);while(i){const p=(i-1)>>1;if(heap[p][0]<=item[0])break;heap[i]=heap[p];i=p;}heap[i]=item;}
    function pop(){const first=heap[0],last=heap.pop();if(heap.length){let i=0;while(i*2+1<heap.length){let c=i*2+1;if(c+1<heap.length&&heap[c+1][0]<heap[c][0])c++;if(heap[c][0]>=last[0])break;heap[i]=heap[c];i=c;}heap[i]=last;}return first;}
    dist[start]=0;push([0,start]);
    while(heap.length){const [d,n]=pop();if(d!==dist[n])continue;if(n===end)break;for(const [v,w] of this.adj[n])if(d+w<dist[v]){dist[v]=d+w;prev[v]=n;push([d+w,v]);}}
    if(!Number.isFinite(dist[end]))throw Error('No hay una conexión por calles entre esos puntos. Probá otro punto.');
    const ids=[];for(let n=end;n!==-1;n=prev[n]){ids.push(n);if(n===start)break;}return {ids:ids.reverse(),length:dist[end]};
  }
  route(points){const anchors=points.map(p=>this.nearest(p)),ids=[];let length=0;for(let i=1;i<anchors.length;i++){const leg=this.path(anchors[i-1],anchors[i]);ids.push(...(i===1?leg.ids:leg.ids.slice(1)));length+=leg.length;}return {points:anchors.map(i=>this.nodes[i]),coordinates:ids.map(i=>this.nodes[i]),length};}
}
root.CycleRouter=CycleRouter;
if(typeof module!=='undefined')module.exports=CycleRouter;
})(typeof window==='undefined'?globalThis:window);
