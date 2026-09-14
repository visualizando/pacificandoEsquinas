(function(root){
'use strict';
const limits=[0,100,250,500,1000];
const colors=['#fff0ea','#fdd0c0','#fc9983','#e44432','#b30000'];
function aggregate(features,step=100,weightField='population'){
  const bins=limits.map((lo,i)=>({lo,hi:limits[i+1]??null,current:0,total:0}));let count=0,under500=0,under500Total=0;
  for(const f of features){const p=f.properties,w=p[weightField];if(!Number.isFinite(w)||w<0||!Number.isFinite(p.current_m)||!Number.isFinite(p.total_m)||p.current_m<0||p.total_m<0)continue;
    count+=w;if(p.current_m<500)under500+=w;if(p.total_m<500)under500Total+=w;
    for(const [key,field] of [['current','current_m'],['total','total_m']]){let i=0;while(i+1<limits.length&&p[field]>=limits[i+1])i++;bins[i][key]+=w;}
  }return {bins,count,under500,under500Total};
}
function render(features,options={}){
  const field=options.weightField||'population',a=aggregate(features,100,field),$=id=>document.getElementById(id),fmt=n=>Math.round(n).toLocaleString('es-AR');
  const pct=n=>(a.count?100*n/a.count:0).toLocaleString('es-AR',{maximumFractionDigits:1});
  const range=b=>b.hi===null?'1.000 m o más':`${fmt(b.lo)}–<${fmt(b.hi)} m`;
  $('histogram-summary').textContent=`≈ ${fmt(a.count)} personas${field==='age_0_14_est'?' de 0–14 años':''}. A menos de 500 m: ${pct(a.under500)}% → ${pct(a.under500Total)}% con la propuesta.`;
  const chart=$('distance-histogram');chart.replaceChildren();
  for(const [key,label] of [['current','Situación actual'],['total','Con la propuesta']]){
    const row=document.createElement('div');row.className='population-stack-row';const head=document.createElement('div');head.className='population-stack-head';
    const name=document.createElement('strong');name.textContent=label;const total=document.createElement('span');total.textContent='100% de la población seleccionada';head.append(name,total);row.append(head);
    const bar=document.createElement('div');bar.className='population-stack';bar.setAttribute('role','group');bar.setAttribute('aria-label',label);
    a.bins.forEach((b,i)=>{const percentage=a.count?100*b[key]/a.count:0;if(!percentage)return;const segment=document.createElement('button');segment.type='button';segment.className='population-segment';segment.style.width=`${percentage}%`;segment.style.background=colors[i];segment.style.color=i>=3?'white':'#4b211b';
      const description=`${label} · ${range(b)}: ≈ ${fmt(b[key])} personas (${pct(b[key])}%).`;segment.setAttribute('aria-label',description);segment.title=description;if(percentage>=7)segment.textContent=`${pct(b[key])}%`;
      const show=()=>{$('histogram-detail').textContent=description;};segment.addEventListener('mouseenter',show);segment.addEventListener('focus',show);segment.addEventListener('click',show);bar.append(segment);
    });row.append(bar);chart.append(row);
  }
  const legend=$('population-stack-legend');legend.replaceChildren();a.bins.forEach((b,i)=>{const item=document.createElement('span'),swatch=document.createElement('i');swatch.style.background=colors[i];swatch.setAttribute('aria-hidden','true');item.append(swatch,document.createTextNode(range(b)));legend.append(item);});
  $('histogram-detail').textContent='De izquierda a derecha: más cerca → más lejos. Seleccioná un tramo para ver población y porcentaje.';
  const body=$('histogram-table-body');body.replaceChildren();for(const b of a.bins){const tr=document.createElement('tr');for(const text of [range(b),`${fmt(b.current)} (${pct(b.current)}%)`,`${fmt(b.total)} (${pct(b.total)}%)`]){const td=document.createElement('td');td.textContent=text;tr.append(td);}body.append(tr);}
}
root.CycleHistogram={aggregate,render};
})(typeof window==='undefined'?globalThis:window);
