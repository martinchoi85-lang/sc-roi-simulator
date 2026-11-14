/* SC ROI Simulator — 계산 엔진 (브라우저 + Node 공용)
 * 모든 금액 단위: 원(KRW). 표시 통화 변환은 UI에서.
 * 1단계 데이터(조합별 시간별 에너지)는 precompute.py가 만든 데이터팩을 decodeCombo()로 읽는다.
 */
(function (root) {
  'use strict';
  const H = 8760;
  const MDAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  const MONTH = new Uint8Array(H), DOW = new Uint8Array(H), HOD = new Uint8Array(H);
  (function () { let h = 0; for (let m = 0; m < 12; m++) for (let d = 0; d < MDAYS[m]; d++) for (let k = 0; k < 24; k++) { MONTH[h] = m + 1; HOD[h] = k; h++; } for (let i = 0; i < H; i++) DOW[i] = (Math.floor(i / 24) + 4) % 7; })(); // 2026-01-01 = 목(4), 0=일

  // ---------- 데이터팩 ----------
  function b64ToBytes(b64) {
    if (typeof atob === 'function') { const s = atob(b64); const u = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i); return u; }
    return new Uint8Array(Buffer.from(b64, 'base64'));
  }
  function decodeCombo(meta, rec, b64) {
    const bytes = b64ToBytes(b64);
    const nch = meta.channels.length;
    const u16 = new Uint16Array(bytes.buffer, bytes.byteOffset, nch * H);
    const ch = {};
    meta.channels.forEach(([k], i) => {
      const [sc, off] = rec.scales[i]; const a = new Float64Array(H);
      for (let h = 0; h < H; h++) a[h] = u16[i * H + h] / sc + off;
      ch[k] = a;
    });
    let p = nch * H * 2; const persons = [];
    for (let o = 0; o < rec.occ; o++) { persons.push(bytes.slice(p, p + H)); p += H; }
    const occDays = bytes.slice(p, p + 365);
    return { rec, ch, persons, occDays };
  }

  // ---------- 1단계: 사용량 ----------
  const APP = ['cook', 'laundry', 'plug', 'light', 'fridge'];
  function seasonOf(month, hemi) { // 0=간절기 1=하절기 2=동절기
    const s = (hemi === 'S') ? ((month >= 12 || month <= 2) ? 1 : (month >= 6 && month <= 8) ? 2 : 0)
      : ((month >= 6 && month <= 8) ? 1 : (month >= 12 || month <= 2) ? 2 : 0);
    return s;
  }
  function level1(combo, awhp) {
    const c = combo.ch, before = { elec: new Float64Array(H), gas: new Float64Array(H) }, after = { elec: new Float64Array(H), gas: new Float64Array(H) };
    const enduse = {}; // 설치 후 용도별 (시각화용)
    for (const k of APP) enduse[k] = c[k];
    for (let h = 0; h < H; h++) {
      let app = 0; for (const k of APP) app += c[k][h];
      before.elec[h] = app + c.cool_base[h];
      before.gas[h] = c.gas_heat_kg[h] + c.gas_dhw_kg[h];
      if (awhp) { after.elec[h] = app + c.aw_heat[h] + c.aw_backup[h] + c.aw_dhw[h] + c.aw_cool[h] + c.aw_standby[h]; after.gas[h] = 0; }
      else { after.elec[h] = before.elec[h]; after.gas[h] = before.gas[h]; }
    }
    if (awhp) { enduse.heat = c.aw_heat.map((v, h) => v + c.aw_backup[h]); enduse.dhw = c.aw_dhw; enduse.cool = c.aw_cool; enduse.standby_aw = c.aw_standby; }
    else { enduse.cool = c.cool_base; }
    return { before, after, enduse, awhp };
  }

  // ---------- 요금 ----------
  function pyRound(x) { const f = Math.floor(x), d = x - f; if (Math.abs(d - 0.5) < 1e-9) return (f % 2 === 0) ? f : f + 1; return Math.round(x); }
  // 한전 주택용 저압 누진 (engine/tariffs/korea.py _calculate_single_month 이식)
  function krMonthBill(kwh, month, T) {
    const summer = (month === 7 || month === 8), winter = (month === 12 || month === 1 || month === 2);
    const t1 = summer ? 300 : 200, t2 = summer ? 450 : 400;
    const b = summer ? T.baseSummer : T.baseStd, e = summer ? T.energySummer : T.energyStd;
    let base, energy;
    if (kwh <= t1) { base = b[0]; energy = kwh * e[0]; }
    else if (kwh <= t2) { base = b[1]; energy = t1 * e[0] + (kwh - t1) * e[1]; }
    else {
      base = b[2];
      if ((summer || winter) && kwh > T.superKwh) energy = t1 * e[0] + (t2 - t1) * e[1] + (T.superKwh - t2) * e[2] + (kwh - T.superKwh) * T.superRate;
      else energy = t1 * e[0] + (t2 - t1) * e[1] + (kwh - t2) * e[2];
    }
    const variable = energy + kwh * (T.climate + T.fuel);
    const sub = base + variable;
    const vat = pyRound(sub * T.vat);
    const fund = Math.floor(sub * T.fund / 10) * 10;
    return Math.floor((sub + vat + fund) / 10) * 10;
  }
  // TOU 가격 배열 (원/kWh, 세전 에너지 단가)
  function touPriceArray(tou, hemi) {
    const p = new Float64Array(H), per = new Uint8Array(H);
    for (let h = 0; h < H; h++) {
      const s = seasonOf(MONTH[h], hemi);
      const wkend = (DOW[h] === 0 || DOW[h] === 6);
      const k = (tou.weekendOffpeak && wkend) ? 0 : tou.hours[s][HOD[h]];
      per[h] = k; p[h] = tou.rates[s][k];
    }
    return { price: p, period: per };
  }

  // ---------- ESS 디스패치 (1년) ----------
  function dispatchYear(load, pv, ess, soc0, opt) {
    // load, pv: kWh/h. ess: {cap(kWh 가용), pmax(kW), rte}
    const n = load.length, imp = new Float64Array(n), exp = new Float64Array(n);
    const ec = Math.sqrt(ess.rte), ed = Math.sqrt(ess.rte);
    let soc = Math.min(soc0, ess.cap), selfUse = 0, chg = 0, dis = 0;
    const touMode = opt && opt.mode === 'tou' && opt.price;
    for (let h = 0; h < n; h++) {
      const net = load[h] - pv[h];
      if (net <= 0) {
        let sur = -net; selfUse += load[h];
        if (ess.cap > 0) { const c = Math.min(sur, ess.pmax, (ess.cap - soc) / ec); soc += c * ec; sur -= c; chg += c; }
        exp[h] = sur;
      } else {
        let need = net; selfUse += pv[h];
        const allowDis = !touMode || opt.price[h] > opt.dayMin[h] + 1e-9;
        if (ess.cap > 0 && allowDis) { const d = Math.min(need, ess.pmax, soc * ed); soc -= d / ed; need -= d; dis += d; }
        imp[h] = need;
        if (touMode && opt.gridCharge && ess.cap > 0 && opt.price[h] <= opt.dayMin[h] + 1e-9 && opt.dayMax[h] * ess.rte > opt.price[h]) {
          const c = Math.min(ess.pmax - 0, (ess.cap - soc) / ec); if (c > 0) { soc += c * ec; imp[h] += c; chg += c; }
        }
      }
    }
    return { imp, exp, soc, selfUse, chg, dis };
  }

  function sumMonthly(a) { const m = new Float64Array(12); for (let h = 0; h < H; h++) m[MONTH[h] - 1] += a[h]; return m; }
  function sum(a) { let s = 0; for (let i = 0; i < a.length; i++) s += a[i]; return s; }

  // 연간 전기요금 (에스컬레이션 전, 매전 수익 별도). state.carry: 상계 이월 (kWh 또는 기간별)
  function annualElecBill(imp, exp, P, state) {
    const res = { bill: 0, exportIncome: 0, monthBill: new Float64Array(12), billedKwh: 0 };
    const T = P.tariff;
    if (T.type === 'kr_prog') {
      const mi = sumMonthly(imp), me = sumMonthly(exp);
      for (let m = 0; m < 12; m++) {
        let billed = mi[m];
        if (P.exportMode === 'net') { const cred = me[m] + state.carry; if (mi[m] >= cred) { billed = mi[m] - cred; state.carry = 0; } else { billed = 0; state.carry = cred - mi[m]; } }
        const b = krMonthBill(billed, m + 1, T.kr); res.monthBill[m] = b; res.bill += b; res.billedKwh += billed;
      }
    } else { // TOU
      const pr = P.touArr.price, per = P.touArr.period;
      const mi = Array.from({ length: 12 }, () => [0, 0, 0]), me = Array.from({ length: 12 }, () => [0, 0, 0]);
      for (let h = 0; h < H; h++) { mi[MONTH[h] - 1][per[h]] += imp[h]; me[MONTH[h] - 1][per[h]] += exp[h]; }
      if (!state.carryP) state.carryP = [0, 0, 0];
      for (let m = 0; m < 12; m++) {
        let energy = 0, kwh = 0;
        for (let k = 0; k < 3; k++) {
          let billed = mi[m][k];
          if (P.exportMode === 'net') { const cred = me[m][k] + state.carryP[k]; if (billed >= cred) { billed -= cred; state.carryP[k] = 0; } else { state.carryP[k] = cred - billed; billed = 0; } }
          // 기간 단가: 해당 월 대표 계절 단가
          const s = seasonOf(m + 1, P.hemi); energy += billed * T.tou.rates[s][k]; kwh += billed;
        }
        const sub = T.tou.baseFee + energy + kwh * (T.tou.addPerKwh || 0);
        const b = T.tou.krTax ? Math.floor((sub + pyRound(sub * 0.1) + Math.floor(sub * 0.027 / 10) * 10) / 10) * 10 : sub;
        res.monthBill[m] = b; res.bill += b; res.billedKwh += kwh;
      }
    }
    if (P.exportMode === 'fit') res.exportIncome = sum(exp) * P.fitPrice;
    else if (P.exportMode === 'tou') {
      const pr = P.touArr ? P.touArr.price : null;
      if (pr) { for (let h = 0; h < H; h++) res.exportIncome += exp[h] * pr[h] * P.touExportRatio; }
      else res.exportIncome = sum(exp) * P.fitPrice; // 누진제 + TOU매전: 정의 불가 → FIT 단가 사용 (UI에서 막음)
    }
    return res;
  }

  // ---------- 2·3단계: 전체 시뮬레이션 ----------
  function hemsFactor(P) {
    const f = new Float64Array(H);
    for (let h = 0; h < H; h++) { const s = seasonOf(MONTH[h], P.hemi); f[h] = 1 - (P.hems.on ? [P.hems.mid, P.hems.summer, P.hems.winter][s] / 100 : 0); }
    return f;
  }

  function simulate(L1, pv1, P) {
    const N = P.years, out = { years: [] };
    const fH = hemsFactor(P);
    const loadA = new Float64Array(H); for (let h = 0; h < H; h++) loadA[h] = L1.after.elec[h] * fH[h];
    const pvKw = P.pvN * P.pvModW / 1000, essKwh = P.essN * P.essModKwh;
    const gasBeforeKg = sum(L1.before.gas), gasAfterKg = sum(L1.after.gas);
    const useBefore = sum(L1.before.elec), useAfter = sum(loadA);
    // TOU 보조
    let opt = null;
    if (P.touArr) {
      const dayMin = new Float64Array(H), dayMax = new Float64Array(H);
      for (let d = 0; d < 365; d++) { let mn = 1e9, mx = -1e9; for (let k = 0; k < 24; k++) { const v = P.touArr.price[d * 24 + k]; mn = Math.min(mn, v); mx = Math.max(mx, v); } for (let k = 0; k < 24; k++) { dayMin[d * 24 + k] = mn; dayMax[d * 24 + k] = mx; } }
      opt = { mode: P.essMode, price: P.touArr.price, dayMin, dayMax, gridCharge: P.gridCharge };
    }
    // 설치 전(기준안): 계통만
    const zero = new Float64Array(H);
    const stB = { carry: 0 }; const billB1 = annualElecBill(L1.before.elec, zero, P, stB);
    // 상태
    let pvAge = 0, essAge = 0, invAge = 0, awAge = 0, soc = 0;
    const stA = { carry: 0 };
    const C = P.cost;
    const pvInit = pvKw * C.pvPerKw, essInit = essKwh * C.essPerKwh, awInit = L1.awhp ? C.awhp : 0, hemsInit = (P.hems.on && C.hemsInclude) ? C.hems : 0;
    const miscInit = (pvKw > 0 || essKwh > 0 || L1.awhp) ? C.misc : 0;
    const subsidy = (pvKw > 0 ? C.subPV : 0) + (essKwh > 0 ? C.subESS : 0) + (L1.awhp ? C.subAWHP : 0) + (hemsInit > 0 ? C.subHEMS : 0);
    const grossInit = pvInit + essInit + awInit + hemsInit + miscInit;
    const invCost = (pvKw > 0 || essKwh > 0) ? Math.max(C.invMin, C.invPerKw * Math.max(pvKw, essKwh > 0 ? essKwh * P.essCrate : 0)) : 0;
    let cumB = 0, cumC = 0, payback = null;
    for (let y = 1; y <= N; y++) {
      const cap = { pv: 0, ess: 0, awhp: 0, inv: 0, hems: 0, misc: 0, sub: 0 };
      const ev = [];
      if (y === 1) { cap.pv = pvInit; cap.ess = essInit; cap.awhp = awInit; cap.hems = hemsInit; cap.misc = miscInit; cap.sub = -subsidy; }
      else {
        if (pvKw > 0 && P.pvDeg > 0 && (1 - P.pvDeg / 100 * pvAge) <= P.pvRepl / 100 + 1e-9) { cap.pv = pvKw * C.pvReplPerKw; pvAge = 0; invAge = 0; ev.push('PV 교체'); }
        if (essKwh > 0 && P.essDeg > 0 && (1 - P.essDeg / 100 * essAge) <= P.essRepl / 100 + 1e-9) { cap.ess = essKwh * C.essReplPerKwh; essAge = 0; ev.push('ESS 교체'); }
        if (invCost > 0 && P.invLife > 0 && invAge >= P.invLife) { cap.inv = invCost; invAge = 0; ev.push('인버터 교체'); }
        if (L1.awhp && P.awhpLife > 0 && awAge >= P.awhpLife) { cap.awhp = C.awhpRepl; awAge = 0; ev.push('AWHP 교체'); }
      }
      const pvH = Math.max(0, 1 - P.pvDeg / 100 * pvAge), soh = Math.max(0, 1 - P.essDeg / 100 * essAge);
      const pvArr = new Float64Array(H); for (let h = 0; h < H; h++) pvArr[h] = pv1[h] * pvKw * pvH;
      const ess = { cap: essKwh * soh, pmax: essKwh * soh * P.essCrate, rte: P.essRte };
      const d = dispatchYear(loadA, pvArr, ess, soc, opt); soc = d.soc;
      const billA = annualElecBill(d.imp, d.exp, P, stA);
      const escE = Math.pow(1 + P.escE / 100, y - 1), escG = Math.pow(1 + P.escG / 100, y - 1);
      const expEsc = P.exportMode === 'fit' ? 1 : escE;
      const before = { elec: billB1.bill * escE, gas: gasBeforeKg * P.gasPrice * escG };
      const after = { elec: billA.bill * escE, exportIncome: billA.exportIncome * expEsc, gas: gasAfterKg * P.gasPrice * escG, om: grossInit * P.omPct / 100 };
      before.total = before.elec + before.gas;
      after.total = after.elec - after.exportIncome + after.gas + after.om;
      const capT = cap.pv + cap.ess + cap.awhp + cap.inv + cap.hems + cap.misc + cap.sub;
      const benefit = before.total - after.total;
      cumB += benefit; cumC += capT;
      const net = cumB - cumC; if (payback === null && net >= 0 && y >= 1) payback = y;
      const pvGen = sum(pvArr), imp = sum(d.imp), exp = sum(d.exp);
      out.years.push({ y, cap, capT, cumC, before, after, benefit, cumB, net, ev,
        energy: { use: useAfter, pv: pvGen, imp, exp, selfUse: d.selfUse, chg: d.chg, dis: d.dis, pvHealth: pvH, soh },
        monthBillAfter: billA.monthBill.map(v => v * escE), carry: stA.carry });
      if (y === 1) {
        out.y1 = { monthUse: sumMonthly(loadA), monthPv: sumMonthly(pvArr), monthImp: sumMonthly(d.imp), monthExp: sumMonthly(d.exp),
          monthBillBefore: billB1.monthBill, monthBillAfter: billA.monthBill,
          monthGasBefore: sumMonthly(L1.before.gas), monthGasAfter: sumMonthly(L1.after.gas) };
      }
      pvAge++; essAge++; invAge++; awAge++;
    }
    const y1 = out.years[0].energy;
    out.kpi = {
      selfSuffProd: useAfter > 0 ? y1.pv / useAfter : 0,          // 대표: 생산 기준 = PV 발전량 / 전력 사용량
      selfSuffSupply: useAfter > 0 ? 1 - y1.imp / useAfter : 0,  // 자가충족 = 1 − 계통 수전 / 전력 사용량
      capexGross: grossInit, subsidy, capexNet: grossInit - subsidy,
      benefit1: out.years[0].benefit, cumNet: out.years[N - 1].net, payback,
      useBefore, useAfter, gasBeforeKg, gasAfterKg, pvKw, essKwh,
    };
    return out;
  }

  // 2단계만 (요금 무관, 자가소비 우선 1년 차)
  function level2(L1, pv1, P) {
    const fH = hemsFactor(P), load = new Float64Array(H); for (let h = 0; h < H; h++) load[h] = L1.after.elec[h] * fH[h];
    const pvKw = P.pvN * P.pvModW / 1000, essKwh = P.essN * P.essModKwh;
    const pv = new Float64Array(H); for (let h = 0; h < H; h++) pv[h] = pv1[h] * pvKw;
    const d = dispatchYear(load, pv, { cap: essKwh, pmax: essKwh * P.essCrate, rte: P.essRte }, 0, null);
    const use = sum(load), g = sum(pv), imp = sum(d.imp);
    return { use, pv: g, imp, exp: sum(d.exp), selfUse: d.selfUse, selfSuffProd: use > 0 ? g / use : 0, selfSuffSupply: use > 0 ? 1 - imp / use : 0, pvKw, essKwh };
  }

  const api = { H, MONTH, DOW, HOD, MDAYS, decodeCombo, level1, level2, simulate, krMonthBill, touPriceArray, dispatchYear, seasonOf, sum, sumMonthly };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.SCEngine = api;
})(typeof window !== 'undefined' ? window : globalThis);
