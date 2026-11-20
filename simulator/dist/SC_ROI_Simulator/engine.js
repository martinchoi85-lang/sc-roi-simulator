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
  const ZERO_KWH = 0.001, ZERO_WON = 0.5; // Zero Energy / Zero Bill 판정 허용 오차
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
    const shift = { laundry: c.laundry, dhw: awhp ? c.aw_dhw : null, comp: awhp ? c.aw_heat : null }; // HEMS 부하 이동 대상
    return { before, after, enduse, awhp, shift };
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
  // TOU: tou.seasonMonths(12개월 → 계절 번호)가 있으면 그것을, 없으면 한국식 3계절(간/하/동). 주말은 hoursWe 또는 weekendOffpeak
  function touSeason(tou, month, hemi) { return tou.seasonMonths ? tou.seasonMonths[month - 1] : seasonOf(month, hemi); }
  function touNP(tou) { let n = 0; for (const r of tou.rates) n = Math.max(n, r.length); return n; }
  function touPriceArray(tou, hemi) {
    const p = new Float64Array(H), per = new Uint8Array(H);
    for (let h = 0; h < H; h++) {
      const s = touSeason(tou, MONTH[h], hemi);
      const wkend = (DOW[h] === 0 || DOW[h] === 6);
      const k = wkend && tou.hoursWe ? tou.hoursWe[s][HOD[h]] : (tou.weekendOffpeak && wkend) ? 0 : tou.hours[s][HOD[h]];
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
  // 연간 전기요금(원). 요금표는 자기 통화(T.currency)로 계산한 뒤 P.fx(원/현지통화)를 곱한다.
  function netMonth(imp, exp, state, key) { // kWh 상계, 잉여는 무기한 이월
    const cred = exp + (state[key] || 0);
    if (imp >= cred) { state[key] = 0; return imp - cred; }
    state[key] = cred - imp; return 0;
  }
  function annualElecBill(imp, exp, P, state) {
    const res = { bill: 0, exportIncome: 0, monthBill: new Float64Array(12), monthExpInc: new Float64Array(12), billedKwh: 0 };
    const T = P.tariff, fx = P.fx || 1, net = P.exportMode === 'net';
    const mi = sumMonthly(imp), me = sumMonthly(exp);
    if (T.type === 'kr_prog') {
      for (let m = 0; m < 12; m++) {
        const billed = net ? netMonth(mi[m], me[m], state, 'carry') : mi[m];
        const b = krMonthBill(billed, m + 1, T.kr); res.monthBill[m] = b; res.bill += b; res.billedKwh += billed;
      }
    } else if (T.type === 'tiered') { // 미국식 월 누진(LADWP R-1A 등)
      const t = T.tiered;
      for (let m = 0; m < 12; m++) {
        const k = net ? netMonth(mi[m], me[m], state, 'carry') : mi[m];
        const s = t.seasonMonths[m], r = t.rates[s];
        let e = 0, rest = k, prev = 0, tier = 0;
        for (let i = 0; i < r.length; i++) {
          const lim = i < t.limits.length ? t.limits[i] : Infinity, q = Math.max(0, Math.min(rest, lim - prev));
          e += q * r[i]; rest -= q; if (q > 0) tier = i; prev = lim;
        }
        const usage = e + (t.pac ? t.pac[tier] : 0);
        const add = t.addQ ? t.addQ[Math.floor(m / 3)] : (t.addPerKwh || 0); // 분기별 조정요금
        const b = (Math.max(usage, t.minCharge || 0) + k * add) * fx;
        res.monthBill[m] = b; res.bill += b; res.billedKwh += k;
      }
    } else if (T.type === 'flat') { // 호주식: 하루 기본료 + 단일 단가
      const f = T.flat;
      for (let m = 0; m < 12; m++) {
        const k = net ? netMonth(mi[m], me[m], state, 'carry') : mi[m];
        const b = (f.dailyFee * MDAYS[m] + k * f.rate) * fx; res.monthBill[m] = b; res.bill += b; res.billedKwh += k;
      }
    } else { // TOU
      const per = P.touArr.period, t = T.tou, nP = touNP(t);
      const pi = Array.from({ length: 12 }, () => new Float64Array(nP)), pe = Array.from({ length: 12 }, () => new Float64Array(nP));
      for (let h = 0; h < H; h++) { pi[MONTH[h] - 1][per[h]] += imp[h]; pe[MONTH[h] - 1][per[h]] += exp[h]; }
      if (t.cap) { // 하루 한도(예: Midday Power Saver 무료 구간 24kWh/일): 초과분은 overPeriod 단가로 청구
        res.capOverKwh = 0;
        for (let d = 0; d < 365; d++) {
          let s = 0; for (let k = 0; k < 24; k++) { const h = d * 24 + k; if (per[h] === t.cap.period) s += imp[h]; }
          const over = s - t.cap.kwh; if (over > 0) { const m = MONTH[d * 24] - 1; pi[m][t.cap.period] -= over; pi[m][t.cap.overPeriod] += over; res.capOverKwh += over; }
        }
      }
      for (let m = 0; m < 12; m++) {
        let energy = 0, kwh = 0; const s = touSeason(t, m + 1, P.hemi);
        for (let k = 0; k < nP; k++) {
          const billed = net ? netMonth(pi[m][k], pe[m][k], state, 'carryP' + k) : pi[m][k];
          energy += billed * t.rates[s][k]; kwh += billed;
        }
        const sub = (t.baseFee || 0) + (t.dailyFee || 0) * MDAYS[m] + energy + kwh * (t.addQ ? t.addQ[Math.floor(m / 3)] : (t.addPerKwh || 0));
        const b = t.krTax ? Math.floor((sub + pyRound(sub * 0.1) + Math.floor(sub * 0.027 / 10) * 10) / 10) * 10 : sub * fx;
        res.monthBill[m] = b; res.bill += b; res.billedKwh += kwh;
      }
    }
    if (P.exportMode === 'fit') { res.exportIncome = sum(exp) * P.fitPrice * fx; const me2 = sumMonthly(exp); for (let m = 0; m < 12; m++) res.monthExpInc[m] = me2[m] * P.fitPrice * fx; }
    else if (P.exportMode === 'tou' && P.touArr) { const pr = P.touArr.price; for (let h = 0; h < H; h++) { const v = exp[h] * pr[h] * P.touExportRatio * fx; res.exportIncome += v; res.monthExpInc[MONTH[h] - 1] += v; } }
    return res;
  }

  // ---------- 2·3단계: 전체 시뮬레이션 ----------
  function hemsFactor(P) {
    const f = new Float64Array(H);
    for (let h = 0; h < H; h++) { const s = seasonOf(MONTH[h], P.hemi); f[h] = 1 - (P.hems.on ? [P.hems.mid, P.hems.summer, P.hems.winter][s] / 100 : 0); }
    return f;
  }

  // ---------- HEMS 부하 이동 (TOU 요금제일 때) ----------
  // 같은 날 안에서 옮길 수 있는 부하(세탁·식세기, AWHP 급탕 재가열)를 더 싼 시간으로 옮긴다(1년 차 PV 기준으로 한 번 정하고 매년 같은 일정 사용).
  // 옮길 수 있는 양 = 그 시간 부하 중 PV로 못 채우고 계통에서 받는 몫. 받는 시간의 비용 = PV 잉여가 있으면 매전 가치(월 상계는 그 시간 단가), 없으면 수전 단가.
  // 가장 비싼 시간부터, 가장 싼 시간으로(같으면 이른 시간). 세탁·식세기는 7~22시 시작(23시 전 종료)·시간당 2.0kWh 이하, 급탕은 하루 이동 상한·AWHP 압축기 3.91kW 이하.
  const SHIFT_LCAP = 2.0, SHIFT_COMP = 3.91, SHIFT_LWIN = [7, 22];
  function hemsShift(L1, pv1, P) {
    const base = Float64Array.from(L1.after.elec), res = { load: base, on: false, laundry: 0, dhw: 0, lauM: new Float64Array(12), dhwM: new Float64Array(12), months: [] };
    if (!P.hems || !P.hems.on || !P.hems.shift || !P.touArr || P.offGrid || !L1.shift) return res;
    res.on = true;
    const pr = P.touArr.price, pvKw = P.pvN * P.pvModW / 1000;
    const expVal = h => P.exportMode === 'net' ? pr[h] : P.exportMode === 'fit' ? P.fitPrice : P.exportMode === 'tou' ? pr[h] * P.touExportRatio : 0;
    const lau = Float64Array.from(L1.shift.laundry), dhw = L1.shift.dhw ? Float64Array.from(L1.shift.dhw) : null, comp = L1.shift.comp;
    const dhwCap = Math.max(0, P.hems.dhwCap || 0);
    for (let d = 0; d < 365; d++) {
      const o = d * 24;
      for (let kind = 0; kind < 2; kind++) {
        const s = kind === 0 ? lau : dhw; if (!s) continue;
        let budget = kind === 0 ? Infinity : dhwCap; if (budget <= 1e-9) continue;
        const done = new Uint8Array(24);
        for (let it = 0; it < 500; it++) {
          let src = -1, ms = 0;
          for (let k = 0; k < 24; k++) {
            if (done[k]) continue; const h = o + k, m = Math.min(s[h], Math.max(0, base[h] - pv1[h] * pvKw));
            if (m > 1e-9 && (src < 0 || pr[h] > pr[o + src] + 1e-12)) { src = k; ms = m; }
          }
          if (src < 0) break;
          const ps = pr[o + src];
          let dst = -1, cd = 0, room = 0;
          for (let k = 0; k < 24; k++) {
            if (k === src || (kind === 0 && (k < SHIFT_LWIN[0] || k > SHIFT_LWIN[1]))) continue;
            const h = o + k, cap = kind === 0 ? SHIFT_LCAP - s[h] : SHIFT_COMP - comp[h] - s[h];
            if (cap <= 1e-9) continue;
            const sur = pv1[h] * pvKw - base[h], c = sur > 1e-9 ? expVal(h) : pr[h], r = sur > 1e-9 ? Math.min(sur, cap) : cap;
            if (c < ps - 1e-9 && (dst < 0 || c < cd - 1e-12)) { dst = k; cd = c; room = r; }
          }
          if (dst < 0) { done[src] = 1; continue; }
          const q = Math.min(ms, room, budget), hs = o + src, hd = o + dst;
          s[hs] -= q; s[hd] += q; base[hs] -= q; base[hd] += q; budget -= q;
          if (kind === 0) res.lauM[MONTH[o] - 1] += q; else res.dhwM[MONTH[o] - 1] += q;
          if (budget <= 1e-9) break;
        }
      }
    }
    res.lauS = lau; res.dhwS = dhw; // 이동 후 채널(12개월 모두 이동한 경우)
    return res;
  }
  function touOpt(P) { // ESS TOU 운전용 하루 최저·최고 단가
    if (!P.touArr) return null;
    const dayMin = new Float64Array(H), dayMax = new Float64Array(H);
    for (let d = 0; d < 365; d++) { let mn = 1e9, mx = -1e9; for (let k = 0; k < 24; k++) { const v = P.touArr.price[d * 24 + k]; mn = Math.min(mn, v); mx = Math.max(mx, v); } for (let k = 0; k < 24; k++) { dayMin[d * 24 + k] = mn; dayMax[d * 24 + k] = mx; } }
    return { mode: P.essMode, price: P.touArr.price, dayMin, dayMax, gridCharge: P.gridCharge };
  }
  // 1년 차 조건의 정상 상태 연간 전기 비용(전기요금 − 매전 수익): ESS 시작 SOC·상계 이월 모두 한 해를 미리 돌린 값
  function yearCost(load, pv, ess, opt, P) {
    const soc0 = ess.cap > 0 ? dispatchYear(load, pv, ess, 0, opt).soc : 0, d = dispatchYear(load, pv, ess, soc0, opt);
    const exp = P.exportMode === 'none' ? new Float64Array(H) : d.exp, st = { carry: 0 };
    annualElecBill(d.imp, exp, P, st); const b = annualElecBill(d.imp, exp, P, st);
    return b.bill - b.exportIncome;
  }
  // 부하 이동 → 계절별 절감률. 이동은 달마다 1년 차 정상 상태 비용이 줄어드는 달에만 적용(1월부터 차례로 판단).
  // 월 상계에서 크레딧이 남는 달처럼 시간대 단가가 실제 한계비용이 아닌 달에는 옮겨도 이득이 없거나 손해이므로 HEMS가 옮기지 않는다고 본다.
  function hemsLoad(L1, pv1, P) {
    const sh = hemsShift(L1, pv1, P), fH = hemsFactor(P);
    let load = new Float64Array(H); for (let h = 0; h < H; h++) load[h] = L1.after.elec[h] * fH[h];
    if (!sh.on) return { load, sh, fH };
    const pvKw = P.pvN * P.pvModW / 1000, essKwh = P.essN * P.essModKwh, opt = touOpt(P);
    const pv = new Float64Array(H); for (let h = 0; h < H; h++) pv[h] = pv1[h] * pvKw;
    const ess = { cap: essKwh, pmax: essKwh * P.essCrate, rte: P.essRte };
    let best = yearCost(load, pv, ess, opt, P); sh.cost0 = best;
    for (let m = 1; m <= 12; m++) {
      if (sh.lauM[m - 1] + sh.dhwM[m - 1] <= 1e-9) continue;
      const trial = Float64Array.from(load); for (let h = 0; h < H; h++) if (MONTH[h] === m) trial[h] = sh.load[h] * fH[h];
      const c = yearCost(trial, pv, ess, opt, P);
      if (c < best - 1e-6) { load = trial; best = c; sh.months.push(m); sh.laundry += sh.lauM[m - 1]; sh.dhw += sh.dhwM[m - 1]; }
    }
    sh.cost1 = best;
    if (sh.months.length) { // 적용된 달만 이동 후 채널로(1년 데이터 탭 표시용)
      const lau = Float64Array.from(L1.shift.laundry), dhw = L1.shift.dhw ? Float64Array.from(L1.shift.dhw) : null, on = new Uint8Array(13);
      sh.months.forEach(m => { on[m] = 1; });
      for (let h = 0; h < H; h++) if (on[MONTH[h]]) { lau[h] = sh.lauS[h]; if (dhw) dhw[h] = sh.dhwS[h]; }
      sh.lauF = lau; sh.dhwF = dhw;
    }
    return { load, sh, fH };
  }

  function simulate(L1, pv1, P) {
    // 계통 미연결(오프그리드): 남는 PV는 버림, ESS는 자가소비 우선(계통 충전 없음), 전기요금 0. 계통 수전 = 공급 부족(정전)
    const OFF = !!P.offGrid;
    if (OFF) P = Object.assign({}, P, { exportMode: 'none', essMode: 'self', gridCharge: false });
    const NOBILL = { bill: 0, exportIncome: 0, monthBill: new Float64Array(12), monthExpInc: new Float64Array(12), billedKwh: 0 };
    const N = P.years, out = { years: [] };
    const HL = hemsLoad(L1, pv1, P), loadA = HL.load;
    out.hemsView = { fH: HL.fH, laundry: HL.sh.lauF || L1.shift.laundry, dhw: HL.sh.dhwF || L1.shift.dhw }; // HEMS 반영 채널(절감률 곱하기 전)
    const monGasB = sumMonthly(L1.before.gas), monGasA = sumMonthly(L1.after.gas);
    const pvKw = P.pvN * P.pvModW / 1000, essKwh = P.essN * P.essModKwh;
    const gasBeforeKg = sum(L1.before.gas), gasAfterKg = sum(L1.after.gas);
    const useBefore = sum(L1.before.elec), useAfter = sum(loadA);
    const opt = touOpt(P); // TOU 보조
    // 설치 전(기준안): 계통만
    const zero = new Float64Array(H);
    const stB = { carry: 0 }; const billB1 = annualElecBill(L1.before.elec, zero, P, stB);
    const fixedBill = OFF ? 0 : annualElecBill(zero, zero, P, { carry: 0 }).bill; // 사용량 0일 때의 연간 요금(기본요금·최소요금)
    const noExport = P.exportMode === 'none';
    // 상태
    let pvAge = 0, essAge = 0, invAge = 0, awAge = 0, soc = 0;
    if (essKwh > 0) { // 시작 SOC = 1년 차 조건으로 한 해를 미리 돌린 연말 SOC(정상 상태). 1월 1일 0시 빈 배터리로 시작하는 왜곡 방지
      const pv0 = new Float64Array(H); for (let h = 0; h < H; h++) pv0[h] = pv1[h] * pvKw;
      soc = dispatchYear(loadA, pv0, { cap: essKwh, pmax: essKwh * P.essCrate, rte: P.essRte }, 0, opt).soc;
    }
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
      const curtA = noExport ? d.exp : zero, expA = noExport ? zero : d.exp; // 매전 없음: 남는 PV는 버림
      const billA = OFF ? NOBILL : annualElecBill(d.imp, expA, P, stA);
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
      const pvGen = sum(pvArr), imp = sum(d.imp), exp = sum(expA), curt = sum(curtA);
      out.years.push({ y, cap, capT, cumC, before, after, benefit, cumB, net, ev,
        energy: { use: useAfter, pv: pvGen, imp, exp, curt, selfUse: d.selfUse, chg: d.chg, dis: d.dis, pvHealth: pvH, soh },
        monthBillAfter: billA.monthBill.map(v => v * escE), carry: stA.carry,
        mon: { pv: sumMonthly(pvArr), imp: sumMonthly(d.imp), exp: sumMonthly(expA), curt: sumMonthly(curtA), // N년 차 월별 차트용 (금액은 원, 인상률 반영)
          billB: billB1.monthBill.map(v => v * escE), billA: billA.monthBill.map(v => v * escE), expInc: billA.monthExpInc.map(v => v * expEsc),
          gasB: monGasB.map(v => v * P.gasPrice * escG), gasA: monGasA.map(v => v * P.gasPrice * escG) } });
      if (y === 1) {
        let impDays = 0; for (let dd = 0; dd < 365; dd++) { let s = 0; for (let k = 0; k < 24; k++) s += d.imp[dd * 24 + k]; if (s > ZERO_KWH) impDays++; }
        out.y1 = { monthUse: sumMonthly(loadA), monthPv: sumMonthly(pvArr), monthImp: sumMonthly(d.imp), monthExp: sumMonthly(expA), monthCurt: sumMonthly(curtA),
          hourImp: d.imp, hourExp: expA, hourCurt: curtA, hourLoad: loadA, impDays,
          billVar: billA.bill - fixedBill - billA.exportIncome, fixedBill, capOverKwh: billA.capOverKwh || 0,
          monthBillBefore: billB1.monthBill, monthBillAfter: billA.monthBill,
          monthGasBefore: sumMonthly(L1.before.gas), monthGasAfter: sumMonthly(L1.after.gas) };
      }
      pvAge++; essAge++; invAge++; awAge++;
    }
    const y1 = out.years[0].energy, Y1 = out.y1;
    { // Zero Bill 정상 상태 판정: 1년 차 수전·역송으로 한 해를 미리 돌려 생긴 상계 이월을 안고 다시 계산(설치 첫해는 이월 0에서 시작)
      const stW = { carry: 0 }; if (!OFF) annualElecBill(Y1.hourImp, Y1.hourExp, P, stW);
      const bS = OFF ? NOBILL : annualElecBill(Y1.hourImp, Y1.hourExp, P, stW);
      Y1.billVarSteady = bS.bill - Y1.fixedBill - bS.exportIncome; Y1.monthBillSteady = bS.monthBill;
    }
    let unservedHours = 0; for (let h = 0; h < H; h++) if (Y1.hourImp[h] > ZERO_KWH) unservedHours++;
    out.kpi = {
      offGrid: OFF, offGridSupply: { ok: y1.imp <= ZERO_KWH, unservedKwh: y1.imp, hours: unservedHours, days: Y1.impDays },
      selfSuff: useAfter > 0 ? 1 - y1.imp / useAfter : 0,        // 대표: 에너지 자립률(실시간) = 1 − 계통 수전 / 전력 사용량
      pvOffset: useAfter > 0 ? y1.pv / useAfter : 0,             // 보조: 연간 발전 상쇄율 = PV 발전량 / 전력 사용량 (100% 초과 가능)
      pvOffsetUsed: useAfter > 0 ? (y1.pv - y1.curt) / useAfter : 0, // 버려진 PV 제외
      selfCons: y1.pv > 0 ? (y1.pv - y1.exp - y1.curt) / y1.pv : 0, // 자가소비율 = 집에서 쓴(ESS 경유 포함) PV ÷ PV 발전량
      hemsShift: { on: HL.sh.on, laundry: HL.sh.laundry, dhw: HL.sh.dhw, months: HL.sh.months, cand: HL.sh.on ? sum(HL.sh.lauM) + sum(HL.sh.dhwM) : 0, cost0: HL.sh.cost0, cost1: HL.sh.cost1 },
      curt: y1.curt, curtRatio: y1.pv > 0 ? y1.curt / y1.pv : 0,
      zeroEnergy: { ok: y1.imp <= ZERO_KWH, impKwh: y1.imp, impDays: Y1.impDays },
      zeroBill: { ok: Y1.billVar <= ZERO_WON, varBill: Y1.billVar, fixedBill: Y1.fixedBill, okSteady: Y1.billVarSteady <= ZERO_WON, varBillSteady: Y1.billVarSteady },
      capexGross: grossInit, subsidy, capexNet: grossInit - subsidy,
      benefit1: out.years[0].benefit, cumNet: out.years[N - 1].net, payback,
      useBefore, useAfter, gasBeforeKg, gasAfterKg, pvKw, essKwh,
    };
    return out;
  }

  // 2단계만 (요금 무관, 자가소비 우선 1년 차)
  function level2(L1, pv1, P) {
    const load = hemsLoad(L1, pv1, P).load;
    const pvKw = P.pvN * P.pvModW / 1000, essKwh = P.essN * P.essModKwh;
    const pv = new Float64Array(H); for (let h = 0; h < H; h++) pv[h] = pv1[h] * pvKw;
    const d = dispatchYear(load, pv, { cap: essKwh, pmax: essKwh * P.essCrate, rte: P.essRte }, 0, null);
    const use = sum(load), g = sum(pv), imp = sum(d.imp);
    return { use, pv: g, imp, exp: sum(d.exp), selfUse: d.selfUse, pvOffset: use > 0 ? g / use : 0, selfSuff: use > 0 ? 1 - imp / use : 0, pvKw, essKwh };
  }

  // Zero Energy(1년 차 계통 수전 0)에 필요한 최소 ESS 모듈 수. 현재 PV·HEMS 기준, 자가소비 우선 운전(계통 충전 없음),
  // 시작 SOC는 simulate와 같은 정상 상태. 반환 { n: 모듈 수 또는 null, imp: n(또는 maxN)에서의 남은 수전 kWh, days }
  function minEssForZero(L1, pv1, P, maxN) {
    const load = hemsLoad(L1, pv1, P).load; // simulate와 같은 부하(오프그리드면 이동 없음)
    const pvKw = P.pvN * P.pvModW / 1000, pv = new Float64Array(H); for (let h = 0; h < H; h++) pv[h] = pv1[h] * pvKw;
    let last = null;
    for (let n = 0; n <= maxN; n++) {
      const cap = n * P.essModKwh, ess = { cap, pmax: cap * P.essCrate, rte: P.essRte };
      const soc0 = cap > 0 ? dispatchYear(load, pv, ess, 0, null).soc : 0;
      const d = dispatchYear(load, pv, ess, soc0, null), imp = sum(d.imp);
      let days = 0; for (let dd = 0; dd < 365; dd++) { let s = 0; for (let k = 0; k < 24; k++) s += d.imp[dd * 24 + k]; if (s > ZERO_KWH) days++; }
      last = { n: null, imp, days, tried: n };
      if (imp <= ZERO_KWH) return { n, imp, days };
    }
    return last;
  }

  const api = { H, MONTH, DOW, HOD, MDAYS, decodeCombo, level1, level2, simulate, hemsShift, minEssForZero, touNP, krMonthBill, touPriceArray, dispatchYear, seasonOf, sum, sumMonthly };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.SCEngine = api;
})(typeof window !== 'undefined' ? window : globalThis);
