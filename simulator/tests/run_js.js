const fs=require('fs'),path=require('path');const E=require('../web/engine.js');
let META=null;const RECS={};global.SCDATA={meta:m=>META=m,add:(r,b)=>RECS[r.key]=[r,b]};
const D=JSON.parse(fs.readFileSync(path.join(__dirname,'defaults.json')));const cases=JSON.parse(fs.readFileSync(path.join(__dirname,'cases.json')));
const out=[];
for(const c of cases){
  const dir=path.join(__dirname,'..','data',c.region||'kr_central'); eval(fs.readFileSync(path.join(dir,'meta.js'),'utf8'));
  eval(fs.readFileSync(path.join(dir,`c_${c.key}.js`),'utf8'));
  const combo=E.decodeCombo(META,...RECS[c.key]);const L1=E.level1(combo,c.awhp);
  const P=Object.assign({},D,c);P.tariff=D.tariffs[c.tariff];P.cost=D.cost;
  if(P.tariff.type==='tou')P.touArr=E.touPriceArray(P.tariff.tou,P.hemi);
  const t0=Date.now();const r=E.simulate(L1,META.pv1kw_kwh,P);const ms=Date.now()-t0;
  out.push({key:c.key+(c.region||''),ms,kpi:Object.assign({},r.kpi,{impDays:r.y1.impDays,billVar:r.y1.billVar}),years:r.years.map(y=>({y:y.y,curt:y.energy.curt,capT:y.capT,bE:y.before.elec,bG:y.before.gas,aE:y.after.elec,aX:y.after.exportIncome,aG:y.after.gas,om:y.after.om,ben:y.benefit,net:y.net,imp:y.energy.imp,exp:y.energy.exp,pv:y.energy.pv,ev:y.ev}))});
}
console.log(JSON.stringify(out));
