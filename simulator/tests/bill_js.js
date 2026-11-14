const E=require('../web/engine.js');
const T={baseStd:[910,1600,7300],baseSummer:[910,1600,7300],energyStd:[120,214.6,307.3],energySummer:[120,214.6,307.3],superKwh:1000,superRate:736.2,climate:9,fuel:5,vat:0.1,fund:0.027};
const out=[];for(let m=1;m<=12;m++)for(let k=0;k<=1600;k+=0.37)out.push([m,+k.toFixed(2),E.krMonthBill(+k.toFixed(2),m,T)]);
console.log(JSON.stringify(out));
