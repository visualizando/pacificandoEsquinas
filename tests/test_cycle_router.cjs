// Run from repository root: Get-Content tests/test_cycle_router.cjs -Raw | node
const fs=require('fs'),vm=require('vm'),assert=require('assert');
vm.runInThisContext(fs.readFileSync('web/cycle-router.js','utf8'));
const r=new CycleRouter({nodes:[[0,0],[.001,0],[.002,0],[.003,0]],edges:[[0,1,100],[1,2,100],[0,2,500]]});
assert.deepStrictEqual(r.path(0,2).ids,[0,1,2]);
assert.equal(r.path(0,2).length,200);
assert.throws(()=>r.path(0,3),/conexión/);
assert.throws(()=>r.nearest([10,10]),/120 m/);
assert.deepStrictEqual(r.route([[0,0],[.002,0],[.001,0]]).coordinates,[[0,0],[.001,0],[.002,0],[.001,0]]);
assert.equal(r.route([]).length,0);
const actual=new CycleRouter(JSON.parse(fs.readFileSync('data/processed/cycle-routing.json','utf8')));
for(let i=0;i<actual.nodes.length;i+=2500){
  if(!actual.adj[i].length)continue;
  const target=actual.adj[i][0][0],path=actual.path(i,target);
  assert.equal(path.ids[0],i);assert.equal(path.ids.at(-1),target);
  for(let k=1;k<path.ids.length;k++)assert(actual.adj[path.ids[k-1]].some(([v])=>v===path.ids[k]));
}
console.log('Router checks passed, including real street connectivity.');
