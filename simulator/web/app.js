/* SC ROI Simulator — UI */
(function () {
  'use strict';
  const E = window.SCEngine, D = window.SCDEF, AVAIL = window.SCREGIONS || {};
  const $ = s => document.querySelector(s), $$ = s => Array.from(document.querySelectorAll(s));
  const COL = { s1: '#2a78d6', s2: '#eb6834', s3: '#1baf7a', s4: '#eda100', s5: '#e87ba4', s6: '#008300', s7: '#6250d6', s8: '#e34948', grid: '#eef0f2', axis: '#9aa1ab', txt: '#5c6370', ink: '#1f2328' };
  const SEQ = ['#f4f8fd', '#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b'];
  const MON = ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월'];

  // ---------------- 상태 ----------------
  const S = Object.assign({}, D.init);
  const COST = {}; D.costFields.forEach(f => { if (f[0] !== 'g') COST[f[0]] = f[2]; });
  const TARIFF = JSON.parse(JSON.stringify(D.tariffs));
  const conf = { l1: null, l2: null, l3: null };   // 확정 시점 입력 스냅샷(JSON)
  let combo = null, L1 = null, META = {}, R2 = null, R3 = null, selDay = 17;
  const DATA = { meta: {}, raw: {} };
  window.SCDATA = { meta: m => { DATA.meta[m.region] = m; }, add: (r, b) => { DATA.raw[r.key] = [r, b]; } };

  // ---------------- 유틸 ----------------
  const num = v => { const x = parseFloat(String(v).replace(/[^0-9.\-]/g, '')); return isFinite(x) ? x : 0; };
  const f0 = v => { const r = Math.round(v); return (r === 0 ? 0 : r).toLocaleString('ko-KR'); };
  const f1 = v => (Math.round(v * 10) / 10).toLocaleString('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const pct = v => (v * 100).toFixed(0) + '%';
  function cur() { const c = $('#curSel').value; const fx = c === 'USD' ? num($('#fxUSD').value) : c === 'AUD' ? num($('#fxAUD').value) : 1; return { c, fx: fx > 0 ? fx : 1 }; }
  function money(krw, short) { // short: KPI용
    const { c, fx } = cur();
    if (c === 'KRW') return short ? [f0(krw / 1e4), '만 원'] : f0(krw / 1e4);
    const v = krw / fx; return short ? [f0(v), c] : f0(v);
  }
  const unitLabel = () => { const { c } = cur(); return c === 'KRW' ? '만 원' : c; };
  function loadScript(src) { return new Promise((ok, no) => { const s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = () => no(new Error('불러오기 실패: ' + src)); document.head.appendChild(s); }); }
  const snap1 = () => JSON.stringify([S.house, S.occ, S.rate, S.region, S.awhp]);
  const snap2 = () => JSON.stringify([S.pvN, S.essN, S.pvDeg, S.essDeg, S.pvRepl, S.essRepl, S.awhpLife, S.invLife, S.hemsOn, S.hemsWinter, S.hemsSummer, S.hemsMid, S.hemsInclude, COST]);
  const snap3 = () => JSON.stringify([S.tariff, S.exportMode, S.fitPrice, S.touExportPct, S.essMode, S.gridCharge, S.escE, S.escG, S.gasPrice, S.omPct, S.years, TARIFF]);
  const region = () => D.regions.find(r => r.id === S.region);
  const houseKey = h => D.houses.find(x => x[0] === h)[1];

  // ---------------- 입력 UI 생성 ----------------
  function seg(el, opts, get, set) {
    el.innerHTML = opts.map(o => `<button data-v="${o[0]}" ${o[2] ? 'disabled title="' + o[2] + '"' : ''}>${o[1]}</button>`).join('');
    const paint = () => el.querySelectorAll('button').forEach(b => b.classList.toggle('on', b.dataset.v === String(get())));
    el.addEventListener('click', e => { const b = e.target.closest('button'); if (!b || b.disabled) return; set(b.dataset.v); paint(); changed(); });
    paint(); el._paint = paint;
  }
  function buildInputs() {
    seg($('[data-k=house]'), D.houses.map(h => [h[0], h[2]]), () => S.house, v => S.house = v);
    seg($('[data-k=occ]'), [[1, '1인'], [2, '2인'], [3, '3인']], () => S.occ, v => S.occ = +v);
    seg($('[data-k=rate]'), D.rates.map(r => [r, Math.round(r * 100) + '%']), () => S.rate, v => S.rate = +v);
    seg($('[data-k=awhp]'), [['false', '가스보일러 유지'], ['true', 'AWHP 도입']], () => S.awhp, v => S.awhp = v === 'true');
    $('#region').innerHTML = D.regions.map(r => { const ok = AVAIL[r.id]; return `<option value="${r.id}" ${ok ? '' : 'disabled'}>${r.label}${ok ? '' : ' — ' + (r.pending || '준비 중')}</option>`; }).join('');
    $('#region').value = S.region; $('#region').onchange = e => { S.region = e.target.value; changed(); };
    $$('.stepper').forEach(el => {
      const k = el.dataset.k, mn = +el.dataset.min, mx = +el.dataset.max;
      el.innerHTML = `<button data-d="-1">−</button><input type="text" value="${S[k]}"><button data-d="1">+</button><span class="u"></span>`;
      const inp = el.querySelector('input'), u = el.querySelector('.u');
      const paint = () => { inp.value = S[k]; u.textContent = k === 'pvN' ? `= ${(S[k] * D.fixed.pvModW / 1000).toFixed(1)} kW` : `= ${S[k] * D.fixed.essModKwh} kWh`; };
      el.addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; S[k] = Math.max(mn, Math.min(mx, S[k] + +b.dataset.d)); paint(); changed(); });
      inp.addEventListener('change', () => { S[k] = Math.max(mn, Math.min(mx, Math.round(num(inp.value)))); paint(); changed(); });
      paint();
    });
    $$('.slider').forEach(el => {
      const k = el.dataset.k;
      el.innerHTML = `<input type="range" min="${el.dataset.min}" max="${el.dataset.max}" step="${el.dataset.step}" value="${S[k]}"><input type="text" value="${S[k]}"><span class="u">${el.dataset.unit}</span>`;
      const r = el.querySelector('[type=range]'), t = el.querySelector('[type=text]');
      r.addEventListener('input', () => { S[k] = +r.value; t.value = r.value; changed(); });
      t.addEventListener('change', () => { let v = num(t.value); v = Math.max(+el.dataset.min, Math.min(+el.dataset.max, v)); S[k] = v; t.value = v; r.value = v; changed(); });
    });
    $$('select.life').forEach(el => {
      const k = el.dataset.k;
      el.innerHTML = D.lifeOptions.map(y => `<option value="${y}">${y ? y + '년 후 교체' : '고장 없음 (교체 안 함)'}</option>`).join('');
      el.value = S[k]; el.onchange = () => { S[k] = +el.value; changed(); };
    });
    $$('input[type=checkbox][data-k]').forEach(el => { const k = el.dataset.k; el.checked = !!S[k]; el.onchange = () => { S[k] = el.checked; paintHems(); changed(); }; });
    $$('input[type=text][data-k]').forEach(el => { const k = el.dataset.k; if (el.closest('.slider') || el.closest('.stepper')) return; el.value = S[k]; el.onchange = () => { S[k] = num(el.value); el.value = S[k]; changed(); }; });
    // 단가·보조금
    $('#costGrid').innerHTML = D.costFields.map(f => f[0] === 'g' ? `<div class="gh">${f[1]}</div>` :
      `<label title="${f[4]}">${f[1]} <span class="st ${f[3]}">${{ V: '확인', U: '미검증', P: '임시', A: '가정', I: '입력' }[f[3]]}</span></label><input type="text" data-c="${f[0]}" value="${(+f[2]).toLocaleString('ko-KR')}" title="${f[4]}">`).join('');
    $$('#costGrid input').forEach(el => el.onchange = () => { COST[el.dataset.c] = num(el.value); el.value = COST[el.dataset.c].toLocaleString('ko-KR'); changed(); });
    // 요금제
    $('#tariffSel').onchange = e => { S.tariff = e.target.value; if (TARIFF[S.tariff].type === 'kr_prog' && S.exportMode === 'tou') S.exportMode = 'net'; paintL3(); changed(); };
    seg($('[data-k=exportMode]'), [['net', '월 상계'], ['fit', 'FIT'], ['tou', 'TOU']], () => S.exportMode, v => { S.exportMode = v; paintL3(); });
    seg($('[data-k=essMode]'), [['self', '자가소비 우선'], ['tou', 'TOU 피크 방전']], () => S.essMode, v => { S.essMode = v; paintL3(); });
    paintHems(); paintL3();
    ['#curSel', '#fxUSD', '#fxAUD'].forEach(s => $(s).addEventListener('change', () => { $('#fxUSD').value = num($('#fxUSD').value).toLocaleString('ko-KR'); $('#fxAUD').value = num($('#fxAUD').value).toLocaleString('ko-KR'); renderAll(); }));
  }
  function paintHems() { $('#hemsBox').classList.toggle('off', !S.hemsOn); }
  function paintL3() {
    const reg = region();
    $('#tariffSel').innerHTML = Object.entries(TARIFF).filter(([, t]) => t.country === reg.country).map(([k, t]) => `<option value="${k}">${t.label}</option>`).join('');
    $('#tariffSel').value = S.tariff;
    const T = TARIFF[S.tariff], isTou = T.type === 'tou';
    const eb = $('[data-k=exportMode]'); eb.querySelector('[data-v=tou]').disabled = !isTou;
    eb.querySelector('[data-v=tou]').title = isTou ? '' : '누진제에는 시간대 단가가 없어 TOU 매전을 쓸 수 없습니다';
    eb._paint();
    $('#fitRow').style.display = S.exportMode === 'fit' ? '' : 'none';
    $('#touExpRow').style.display = S.exportMode === 'tou' ? '' : 'none';
    $('#essModeRow').style.display = isTou ? '' : 'none';
    $('#gridChgRow').style.display = isTou && S.essMode === 'tou' ? '' : 'none';
    $('[data-k=essMode]')._paint && $('[data-k=essMode]')._paint();
    const box = $('#touBox'); box.classList.toggle('show', isTou);
    if (isTou) {
      const t = T.tou, sn = ['간절기', '하절기', '동절기'], pn = ['경부하', '중간', '최대'], pc = ['#cde2fb', '#6da7ec', '#184f95'];
      box.innerHTML = `<table><tr><th></th>${pn.map(p => `<th>${p}</th>`).join('')}</tr>` +
        sn.map((s, i) => `<tr><th>${s}</th>${[0, 1, 2].map(k => `<td><input type="text" data-ts="${i}" data-tp="${k}" value="${t.rates[i][k]}"></td>`).join('')}</tr>`).join('') +
        `</table><div class="inl" style="margin-top:4px">기본요금 <input type="text" data-tb value="${t.baseFee}"> 원/월 · 기후·연료 <input type="text" data-ta value="${t.addPerKwh}"> 원/kWh</div>` +
        sn.map((s, i) => `<div class="hrs"><b style="font-weight:500">${s}</b>${t.hours[i].map((k, h) => `<span style="background:${pc[k]}" title="${h}시 ${pn[k]}"></span>`).join('')}</div>`).join('') +
        `<div class="warn">원/kWh 세전 단가. 시간대·배율은 2019년 한전 실증사업 일반형(하계 13~17시 2.3배, 동계 9~12시 1.7배)을 바탕으로 한 가정값. 한국 일반 가정에는 아직 전국 시행 요금표가 없음.</div>`;
      box.querySelectorAll('input[data-ts]').forEach(el => el.onchange = () => { t.rates[+el.dataset.ts][+el.dataset.tp] = num(el.value); changed(); });
      box.querySelector('[data-tb]').onchange = e => { t.baseFee = num(e.target.value); changed(); };
      box.querySelector('[data-ta]').onchange = e => { t.addPerKwh = num(e.target.value); changed(); };
    }
  }

  // ---------------- 상태 표시 ----------------
  let _deb = null;
  function changed() { clearTimeout(_deb); _deb = setTimeout(() => run(3), 120); }

  // ---------------- 계산 ----------------
  async function confirm1() {
    const reg = S.region, key = `${houseKey(S.house)}_${S.occ}_${Math.round(S.rate * 100)}`;
    if (!DATA.meta[reg]) await loadScript(`data/${reg}/meta.js`);
    if (!DATA.raw[key] || DATA.raw[key][0].region !== reg) { await loadScript(`data/${reg}/c_${key}.js`); DATA.raw[key][0].region = reg; }
    META = DATA.meta[reg];
    combo = E.decodeCombo(META, ...DATA.raw[key]);
    L1 = E.level1(combo, S.awhp);
    conf.l1 = snap1();
  }
  function params() {
    const T = TARIFF[S.tariff], reg = region();
    const P = {
      pvN: S.pvN, essN: S.essN, pvModW: D.fixed.pvModW, essModKwh: D.fixed.essModKwh, pvDeg: S.pvDeg, essDeg: S.essDeg, pvRepl: S.pvRepl, essRepl: S.essRepl,
      awhpLife: S.awhpLife, invLife: S.invLife, essRte: COST.essRte, essCrate: COST.essCrate,
      hems: { on: S.hemsOn, winter: S.hemsWinter, summer: S.hemsSummer, mid: S.hemsMid }, hemi: reg.hemi,
      tariff: T, exportMode: S.exportMode, fitPrice: S.fitPrice, touExportRatio: S.touExportPct / 100, essMode: S.essMode, gridCharge: S.gridCharge,
      escE: S.escE, escG: S.escG, gasPrice: S.gasPrice, omPct: S.omPct, years: S.years,
      cost: Object.assign({}, COST, { hemsInclude: S.hemsInclude }),
    };
    if (T.type === 'tou') P.touArr = E.touPriceArray(T.tou, reg.hemi);
    return P;
  }
  async function run(level) {
    try {
      if (conf.l1 !== snap1()) await confirm1();
      if (!R3) level = 3; // 첫 화면은 전체 계산
      // 앞 단계를 확인하면, 뒤 단계 입력이 바뀌지 않은 경우에 한해 뒤 단계도 그대로 다시 계산(결과 일관성 유지)
      const do2 = level >= 2 || conf.l2 === snap2();
      const do3 = do2 && (level >= 3 || conf.l3 === snap3());
      if (do2) { R2 = E.level2(L1, META.pv1kw_kwh, params()); conf.l2 = snap2(); }
      if (do3) { R3 = E.simulate(L1, META.pv1kw_kwh, params()); conf.l3 = snap3(); }
      renderAll();
    } catch (err) { flash('오류: ' + err.message); console.error(err); }
  }

  // ---------------- SVG 차트 ----------------
  function axisTicks(mn, mx, n) {
    const span = mx - mn || 1, raw = span / n, p = Math.pow(10, Math.floor(Math.log10(raw))), st = [1, 2, 2.5, 5, 10].map(m => m * p).find(s => s >= raw) || raw;
    const a = Math.floor(mn / st + 1e-9) * st, out = []; let v = a; out.push(+v.toFixed(10)); while (v < mx - st * 1e-6) { v += st; out.push(+v.toFixed(10)); } return out;
  }
  function svg(w, h, body) { return `<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg">${body}</svg>`; }
  const tipAttr = html => `data-tip="${html.replace(/"/g, '&quot;')}"`;
  function legend(el, items) { $(el).innerHTML = items.map(([n, c, ln]) => `<span><i class="${ln ? 'ln' : ''}" style="background:${c}"></i>${n}</span>`).join(''); }
  function yAxis(ticks, y, L, W, fmt) {
    return ticks.map(t => `<line x1="${L}" x2="${W}" y1="${y(t)}" y2="${y(t)}" stroke="${t === 0 ? COL.axis : COL.grid}"/><text x="${L - 6}" y="${y(t) + 3.5}" text-anchor="end" font-size="10" fill="${COL.txt}">${fmt(t)}</text>`).join('');
  }
  function bar(x, y0, y1, w, color, tip) { // 데이터 쪽 끝 4px 라운드, 기준선 쪽 직각
    const top = Math.min(y0, y1), h = Math.abs(y1 - y0); if (h < 0.5) return '';
    const r = Math.min(4, h, w / 2), up = y1 < y0;
    const d = up ? `M${x},${y0}V${top + r}Q${x},${top} ${x + r},${top}H${x + w - r}Q${x + w},${top} ${x + w},${top + r}V${y0}Z`
      : `M${x},${y0}V${y1 - r}Q${x},${y1} ${x + r},${y1}H${x + w - r}Q${x + w},${y1} ${x + w},${y1 - r}V${y0}Z`;
    return `<path d="${d}" fill="${color}"${tip ? ' ' + tipAttr(tip) : ''}/>`;
  }
  function groupedBars(el, cats, series, opt) {
    const box = $(el), W = Math.max(320, box.clientWidth), H = opt.h || 230, L = opt.L || 46, R = 8, T = 10, B = 24;
    let mx = 0; series.forEach(s => s.values.forEach(v => mx = Math.max(mx, v)));
    const ticks = axisTicks(0, mx * 1.05, 4), top = ticks[ticks.length - 1], y = v => T + (top - v) / top * (H - T - B);
    const cw = (W - L - R) / cats.length, gw = cw * 0.78, bw = (gw - (series.length - 1) * 2) / series.length;
    let body = yAxis(ticks, y, L, W - R, opt.fmt || f0);
    cats.forEach((c, i) => {
      const x0 = L + i * cw + (cw - gw) / 2;
      const tip = `<b>${c}</b><br>` + series.map(s => `${s.name}: ${(opt.vfmt || f0)(s.values[i])} ${opt.unit || ''}`).join('<br>');
      series.forEach((s, j) => { if (s.type !== 'line') body += bar(x0 + j * (bw + 2), y(0), y(s.values[i]), bw, s.color); });
      body += `<rect x="${L + i * cw}" y="${T}" width="${cw}" height="${H - T - B}" fill="transparent" ${tipAttr(tip)}/>`;
      body += `<text x="${L + i * cw + cw / 2}" y="${H - 7}" text-anchor="middle" font-size="10" fill="${COL.txt}">${c}</text>`;
    });
    series.filter(s => s.type === 'line').forEach(s => {
      body += `<path d="${s.values.map((v, i) => (i ? 'L' : 'M') + (L + i * cw + cw / 2) + ',' + y(v)).join('')}" fill="none" stroke="${s.color}" stroke-width="2" pointer-events="none"/>`;
    });
    box.innerHTML = svg(W, H, body);
  }
  function stackedBars(el, cats, series, opt) {
    const box = $(el), W = Math.max(320, box.clientWidth), H = opt.h || 210, L = 46, R = 8, T = 10, B = 24;
    const tot = cats.map((_, i) => series.reduce((a, s) => a + s.values[i], 0));
    const ticks = axisTicks(0, Math.max(...tot, 1e-6) * 1.05, 4), top = ticks[ticks.length - 1], y = v => T + (top - v) / top * (H - T - B);
    const cw = (W - L - R) / cats.length, bw = Math.min(46, cw * 0.62);
    let body = yAxis(ticks, y, L, W - R, opt.fmt || f0);
    cats.forEach((c, i) => {
      const x = L + i * cw + (cw - bw) / 2; let acc = 0; const segs = series.filter(s => s.values[i] > 0);
      segs.forEach((s, j) => {
        const y0 = y(acc), y1 = y(acc + s.values[i]); acc += s.values[i];
        const last = j === segs.length - 1;
        if (last) body += bar(x, y0 - (j ? 1 : 0), y1, bw, s.color);
        else body += `<rect x="${x}" y="${y1 + 1}" width="${bw}" height="${Math.max(0, y0 - y1 - 2 + (j ? 0 : 1))}" fill="${s.color}"/>`;
      });
      const tip = `<b>${c}</b> 합계 ${(opt.vfmt || f0)(tot[i])} ${opt.unit || ''}<br>` + series.slice().reverse().map(s => `${s.name}: ${(opt.vfmt || f0)(s.values[i])}`).join('<br>');
      body += `<rect x="${L + i * cw}" y="${T}" width="${cw}" height="${H - T - B}" fill="transparent" ${tipAttr(tip)}/>`;
      body += `<text x="${L + i * cw + cw / 2}" y="${H - 7}" text-anchor="middle" font-size="10" fill="${COL.txt}">${c}</text>`;
    });
    if (opt.line) body += `<path d="${opt.line.values.map((v, i) => (i ? 'L' : 'M') + (L + i * cw + cw / 2) + ',' + y(v)).join('')}" fill="none" stroke="${opt.line.color}" stroke-width="2" pointer-events="none"/>`;
    box.innerHTML = svg(W, H, body);
  }

  // ---------------- 시뮬레이터 탭 렌더 ----------------
  function kpiHTML(t, v, u, s, hl) { return `<div class="kpi${hl ? ' hl' : ''}"><div class="t">${t}</div><div class="v">${v}<small>${u}</small></div><div class="s">${s}</div></div>`; }
  function renderSim() {
    if (!R3) return;
    const k = R3.kpi, N = R3.years.length, r2 = R2 || {};
    const [cv, cu] = money(k.capexNet, true), [bv, bu] = money(k.benefit1, true), [nv, nu] = money(k.cumNet, true);
    const ss = r2.selfSuffProd != null ? r2 : { selfSuffProd: k.selfSuffProd, selfSuffSupply: k.selfSuffSupply, pv: R3.years[0].energy.pv, use: k.useAfter };
    $('#kpis').innerHTML =
      kpiHTML('에너지 자립률 (대표)', (ss.selfSuffProd * 100).toFixed(0), '%', `PV 발전 ${f0(ss.pv)} ÷ 전력 사용 ${f0(ss.use)} kWh<br>자가충족률 ${(ss.selfSuffSupply * 100).toFixed(0)}% (1 − 계통 수전 ÷ 사용)`) +
      kpiHTML('초기 CAPEX (보조금 차감)', cv, cu, `설치 ${money(k.capexGross, true).join(' ')} · 보조금 ${money(k.subsidy, true).join(' ')}`) +
      kpiHTML('1년 차 연간 이득', bv, bu, `설치 전 ${money(R3.years[0].before.total, true).join(' ')} → 설치 후 ${money(R3.years[0].after.total, true).join(' ')}`) +
      kpiHTML(`${N}년 누적 순이익`, nv, nu, `교체 CAPEX ${money(R3.years.slice(1).reduce((a, y) => a + y.capT, 0), true).join(' ')} 포함`) +
      kpiHTML('회수 연도', k.payback ? k.payback + '년 차' : `${N}년 내 미회수`, '', paybackNote(), true);
    // 누적 차트
    legend('#legCum', [['연간 이득', COL.s1], ['CAPEX (설치·교체, 보조금 차감)', COL.s2], ['누적 순이익', COL.s7, true]]);
    cumChart();
    // 월별 에너지
    const y1 = R3.y1;
    legend('#legMon', [['전력 사용', COL.s1], ['PV 발전', COL.s4], ['계통 수전', COL.s7], ['역송', COL.s3]]);
    groupedBars('#chMon', MON, [{ name: '전력 사용', color: COL.s1, values: Array.from(y1.monthUse) }, { name: 'PV 발전', color: COL.s4, values: Array.from(y1.monthPv) },
      { name: '계통 수전', color: COL.s7, values: Array.from(y1.monthImp) }, { name: '역송', color: COL.s3, values: Array.from(y1.monthExp) }], { unit: 'kWh', h: 240 });
    // 월별 비용
    const gp = S.gasPrice, { fx, c } = cur(), dv = c === 'KRW' ? 1e4 : fx;
    const bB = y1.monthBillBefore.map((v, m) => (v + y1.monthGasBefore[m] * gp) / dv);
    const expInc = R3.years[0].after.exportIncome, expM = Array.from(y1.monthExp), expT = expM.reduce((a, b) => a + b, 0) || 1;
    const bA = y1.monthBillAfter.map((v, m) => (v + y1.monthGasAfter[m] * gp - expInc * expM[m] / expT) / dv);
    legend('#legBill', [['설치 전 (전기+가스)', COL.s8], ['설치 후 (전기+가스−매전)', COL.s3]]);
    groupedBars('#chBill', MON, [{ name: '설치 전', color: COL.s8, values: bB }, { name: '설치 후', color: COL.s3, values: bA.map(v => Math.max(0, v)) }], { unit: unitLabel(), vfmt: v => c === 'KRW' ? f1(v) : f0(v), fmt: v => c === 'KRW' ? f0(v) : f0(v), h: 220 });
    renderCapex();
    renderTable();
  }
  function paybackNote() {
    const ev = R3.years.filter(y => y.ev.length).map(y => `${y.y}년 차 ${y.ev.join('·')}`);
    return ev.length ? '교체: ' + ev.slice(0, 3).join(', ') + (ev.length > 3 ? ' 외' : '') : '분석 기간 내 교체 없음';
  }
  function cumChart() {
    const box = $('#chCum'), W = Math.max(400, box.clientWidth), H = 260, L = 56, R = 10, T = 18, B = 24, Y = R3.years, { c, fx } = cur(), dv = c === 'KRW' ? 1e4 : fx;
    const vals = []; Y.forEach(y => { vals.push(y.benefit / dv, -y.capT / dv, y.net / dv); });
    const ticks = axisTicks(Math.min(0, ...vals), Math.max(0, ...vals), 5), mn = ticks[0], mx = ticks[ticks.length - 1];
    const y = v => T + (mx - v) / (mx - mn) * (H - T - B), cw = (W - L - R) / Y.length, bw = Math.min(16, cw * 0.32);
    let body = yAxis(ticks, y, L, W - R, f0);
    Y.forEach((r, i) => {
      const x = L + i * cw + cw / 2;
      body += bar(x - bw - 1, y(0), y(r.benefit / dv), bw, COL.s1);
      if (r.capT) body += bar(x + 1, y(0), y(-r.capT / dv), bw, COL.s2);
      if (r.ev.length) body += `<text x="${x + 1 + bw / 2}" y="${Math.min(H - B - 2, y(-r.capT / dv) + 12)}" text-anchor="middle" font-size="9.5" fill="${COL.txt}">${r.ev.map(e => e.replace(' 교체', '')).join('·')}</text>`;
      body += `<text x="${x}" y="${H - 7}" text-anchor="middle" font-size="10" fill="${COL.txt}">${r.y}</text>`;
    });
    body += `<path d="${Y.map((r, i) => (i ? 'L' : 'M') + (L + i * cw + cw / 2) + ',' + y(r.net / dv)).join('')}" fill="none" stroke="${COL.s7}" stroke-width="2"/>`;
    Y.forEach((r, i) => body += `<circle cx="${L + i * cw + cw / 2}" cy="${y(r.net / dv)}" r="3.2" fill="${COL.s7}" stroke="#fff" stroke-width="1.5"/>`);
    const pb = R3.kpi.payback;
    if (pb) { const x = L + (pb - 1) * cw + cw / 2; body += `<line x1="${x}" x2="${x}" y1="${T - 6}" y2="${H - B}" stroke="${COL.ink}" stroke-dasharray="3 3"/><text x="${x + 5}" y="${T + 2}" font-size="11" font-weight="700" fill="${COL.ink}">회수 ${pb}년 차</text>`; }
    Y.forEach((r, i) => {
      const tip = `<b>${r.y}년 차</b><br>연간 이득 ${money(r.benefit)} · CAPEX ${money(r.capT)}<br>누적 순이익 <b>${money(r.net)}</b> ${unitLabel()}${r.ev.length ? '<br>' + r.ev.join(', ') : ''}`;
      body += `<rect x="${L + i * cw}" y="${T}" width="${cw}" height="${H - T - B}" fill="transparent" ${tipAttr(tip)}/>`;
    });
    box.innerHTML = svg(W, H, body);
  }
  function renderCapex() {
    const k = R3.kpi, C = COST, y = R3.years[0].cap;
    const rows = [['PV ' + (k.pvKw ? `${k.pvKw.toFixed(1)} kW` : '없음'), y.pv], ['ESS ' + (k.essKwh ? `${k.essKwh} kWh` : '없음'), y.ess], ['AWHP', y.awhp], ['HEMS', y.hems], ['부대공사비', y.misc], ['보조금', y.sub]];
    $('#capexList').innerHTML = `<div class="capl">${rows.map(([a, b]) => `<div class="k">${a}</div><div class="v">${money(b)} ${unitLabel()}</div>`).join('')}
      <div class="k tot">합계 (1년 차)</div><div class="v tot">${money(R3.years[0].capT)} ${unitLabel()}</div></div>
      <div class="note">교체 예정: ${R3.years.filter(r => r.ev.length).map(r => `${r.y}년 차 ${r.ev.join('·')} ${money(r.capT)}`).join(' / ') || '없음'} (${unitLabel()})<br>
      인버터 교체비 = max(${f0(C.invMin)}원, ${f0(C.invPerKw)}원/kW × PV kW). PV 교체 시 인버터도 함께 교체된 것으로 봄.</div>`;
  }
  let TABLE = [];
  function renderTable() {
    const Y = R3.years, aw = L1.awhp;
    const rows = [
      ['CAPEX', 'PV', r => r.cap.pv, 'gstart'], ['', 'ESS', r => r.cap.ess], ['', 'AWHP', r => r.cap.awhp], ['', '인버터', r => r.cap.inv], ['', 'HEMS', r => r.cap.hems], ['', '부대공사비', r => r.cap.misc], ['', '보조금 (−)', r => r.cap.sub],
      ['', '합계', r => r.capT, 'sum'], ['', '누적', r => r.cumC, 'sum'],
      ['OPEX (설치 전)', '전기', r => r.before.elec, 'gstart'], ['', '가스 (프로판)', r => r.before.gas], ['', '합계', r => r.before.total, 'sum'],
      ['OPEX (설치 후)', '전기', r => r.after.elec, 'gstart'], ['', '매전 수익 (−)', r => -r.after.exportIncome], ['', '가스 (프로판)', r => r.after.gas], ['', '유지보수비', r => r.after.om], ['', '합계', r => r.after.total, 'sum'],
      ['연간 이득', '설치 전 − 설치 후', r => r.benefit, 'gstart'], ['', '누적', r => r.cumB, 'sum'],
      ['누적 순이익', '누적 이득 − 누적 CAPEX', r => r.net, 'net gstart'],
    ];
    TABLE = rows;
    const pb = R3.kpi.payback;
    let h = `<thead><tr><th class="g"></th><th class="k"></th>${Y.map(r => `<th>${r.y}년 차</th>`).join('')}</tr></thead><tbody>`;
    let gi = 0;
    rows.forEach((row, ri) => {
      const [g, k, f, cls] = row; const span = g ? rows.slice(ri + 1).findIndex(x => x[0]) : 0;
      h += `<tr class="${cls || ''}">` + (g ? `<td class="g" rowspan="${span < 0 ? rows.length - ri : span + 1}">${g}</td>` : '') + `<td class="k">${k}</td>` +
        Y.map(r => { const v = f(r); let c = ''; if (row[0] === '누적 순이익') c = (v < 0 ? 'neg' : 'pos') + (pb === r.y ? ' pay' : ''); if (ri < 9 && r.ev.length && r.y > 1 && v) c += ' ev'; return `<td class="${c}">${money(v)}</td>`; }).join('') + '</tr>';
    });
    $('#tbl').innerHTML = h + '</tbody>';
    $('#unitNote').textContent = `단위: ${unitLabel()} · 좌우 스크롤`;
    const T = TARIFF[S.tariff];
    $('#tblNote').innerHTML = `설치 전 = 가스보일러(프로판) + 계통 전력, PV·ESS·AWHP·HEMS 없음. 설치 후 = ${aw ? 'AWHP(난방·급탕)' : '가스보일러 유지'}${R3.kpi.pvKw ? ` + PV ${R3.kpi.pvKw.toFixed(1)}kW` : ''}${R3.kpi.essKwh ? ` + ESS ${R3.kpi.essKwh}kWh` : ''}${S.hemsOn ? ' + HEMS' : ''}.
      요금제 ${T.label}, 매전 ${{ net: '월 상계(잉여 kWh 무기한 이월)', fit: `FIT ${f0(S.fitPrice)}원/kWh 고정`, tou: `TOU 수전 단가의 ${S.touExportPct}%` }[S.exportMode]}.
      전기요금 ${S.escE}%/년·가스 ${S.escG}%/년 인상, 할인율 없음. 회수 연도는 테두리, 교체가 있는 해는 노란 칸. 매년 같은 기상(TMY)·같은 생활 패턴이 반복된다고 가정.`;
  }

  // ---------------- 1년 데이터 탭 ----------------
  const EU = [['cook', '조리', COL.s4], ['laundry', '세탁·식세기', COL.s5], ['plugl', '가전·플러그·조명', COL.s7], ['fridge', '냉장고·환기·대기', COL.s6], ['cool', '냉방', COL.s1], ['heat', '난방 (AWHP)', COL.s8], ['dhw', '급탕 (AWHP)', COL.s3]];
  let heatMode = 'after', euMode = 'after';
  function euHourly(mode) { // 반환 {key: Float64Array}
    const c = combo.ch, o = {}, aw = mode === 'after' && S.awhp && L1.awhp;
    o.cook = c.cook; o.laundry = c.laundry; o.plugl = c.plug.map((v, h) => v + c.light[h]);
    o.fridge = aw ? c.fridge.map((v, h) => v + c.aw_standby[h]) : c.fridge;
    o.cool = aw ? c.aw_cool : c.cool_base;
    o.heat = aw ? c.aw_heat.map((v, h) => v + c.aw_backup[h]) : new Float64Array(E.H);
    o.dhw = aw ? c.aw_dhw : new Float64Array(E.H);
    return o;
  }
  const ORANGE = ['#fdeee6', '#fbd3bf', '#f6ae8c', '#f08a5d', '#eb6834', '#c94f20', '#9e3b14', '#6e290d'];
  const HEAT_DESC = {
    before: '기준안 = 지금 상태(가스보일러 난방·급탕, PV·ESS 없음)의 시간별 전력 소비. 가전·조명·냉방만 전기를 씁니다.',
    after: '도입안 = 1단계에서 고른 난방 방식의 시간별 전력 소비. AWHP 도입이면 AWHP 난방·급탕 전력이 더해집니다. PV 발전·HEMS 절감을 빼기 전 값.',
    heat: '난방이 켜진 시간만 색칠(회색 = 꺼짐). 색이 진할수록 그 시간 난방에 쓴 에너지가 큼.',
    gas: '기준안(가스보일러)의 시간별 프로판 소비. 난방 + 급탕.',
    pv: '현재 PV 용량 기준 1년 차 시간별 발전량.', tin: '도입안 기준 실내 온도(난방·냉방 운전 결과).', tout: 'TMY 외기 온도.', occ: '집에 있는 인원(수면 포함).',
  };
  function heatSeries(mode) {
    const c = combo.ch;
    switch (mode) {
      case 'after': return { a: L1.after.elec, unit: 'kWh', name: `도입안 전력 소비 (${L1.awhp ? 'AWHP 난방' : '가스보일러 유지'})` };
      case 'before': return { a: L1.before.elec, unit: 'kWh', name: '기준안 전력 소비 (가스보일러)' };
      case 'heat': {
        if (L1.awhp) return { a: c.aw_heat.map((v, h) => v + c.aw_backup[h]), unit: 'kWh', name: '난방 가동 · AWHP 난방 전력 (보조히터 포함)', ramp: ORANGE, offZero: true };
        return { a: c.heat_th_base, unit: 'kWh열', name: '난방 가동 · 가스보일러 난방 열량', ramp: ORANGE, offZero: true };
      }
      case 'gas': return { a: L1.before.gas, unit: 'kg', name: '프로판 (설치 전)' };
      case 'pv': { const kw = (R3 ? R3.kpi.pvKw : S.pvN * 0.4) || 1; return { a: META.pv1kw_kwh.map(v => v * kw), unit: 'kWh', name: `PV 발전 (${kw.toFixed(1)} kW, 1년 차)` }; }
      case 'tin': return { a: S.awhp ? c.t_in_aw : c.t_in_base, unit: '°C', name: '실내 온도', temp: true };
      case 'tout': return { a: META.temp_out, unit: '°C', name: '외기 온도', temp: true };
      case 'occ': { const a = new Float64Array(E.H); combo.persons.forEach(p => { for (let h = 0; h < E.H; h++) if (p[h] !== 0) a[h]++; }); return { a, unit: '명', name: '재택 인원 (수면 포함)' }; }
    }
  }
  function renderData() {
    if (!combo) return;
    const rec = combo.rec, sm = rec.summary;
    $('#dctx').innerHTML = `현재 1단계 조건: <span class="chip">${S.house}</span><span class="chip">${S.occ}인</span><span class="chip">이용률 ${Math.round(S.rate * 100)}%</span><span class="chip">${META.label}</span><span class="chip">${L1.awhp ? 'AWHP 도입' : '가스보일러 유지'}</span><span class="hint" style="margin-left:auto">기상: ${META.weather_src} · 1단계를 바꾸려면 시뮬레이터 탭에서 확인</span>`;
    const ue = E.sum(L1.after.elec), ub = E.sum(L1.before.elec), g = E.sum(L1.before.gas);
    let pk = 0, pkH = 0; L1.after.elec.forEach((v, h) => { if (v > pk) { pk = v; pkH = h; } });
    $('#dkpis').innerHTML = kpiHTML('전력 사용 (설치 후)', f0(ue), 'kWh', 'HEMS 절감 전') + kpiHTML('전력 사용 (설치 전)', f0(ub), 'kWh', '기준안: 가스보일러') +
      kpiHTML('프로판 (설치 전)', f0(g), 'kg', `난방 ${f0(sm.gas_heat_kg)} · 급탕 ${f0(sm.gas_dhw_kg)} kg`) + kpiHTML('최대 시간 부하', pk.toFixed(1), 'kWh/h', dateLabel(Math.floor(pkH / 24)) + ` ${pkH % 24}시`) +
      kpiHTML('재실일', rec.occupied_days, '일', `이용률 ${Math.round(S.rate * 100)}%`) + kpiHTML('PV 1kW 연간 발전', f0(E.sum(META.pv1kw_kwh)), 'kWh/kW', '경사 25°, 정남향');
    // 히트맵 보기 전환
    const hv = $('#heatView');
    if (!hv._built) { seg(hv, [['before', '기준안 전력'], ['after', '도입안 전력'], ['heat', '난방 가동'], ['gas', '프로판'], ['pv', 'PV 발전'], ['tin', '실내 온도'], ['tout', '외기 온도'], ['occ', '재택 인원']], () => heatMode, v => { heatMode = v; }); hv.addEventListener('click', () => drawHeat()); hv._built = 1; }
    const ev = $('#euView');
    if (!ev._built) { seg(ev, [['after', '도입안'], ['before', '기준안']], () => euMode, v => { euMode = v; }); ev.addEventListener('click', () => drawEU()); ev._built = 1; }
    drawHeat(); drawEU();
    // 가스
    const gm = E.sumMonthly(combo.ch.gas_heat_kg), dm = E.sumMonthly(combo.ch.gas_dhw_kg);
    legend('#legGas', [['급탕', COL.s3], ['난방', COL.s8]]);
    stackedBars('#chGas', MON, [{ name: '급탕', color: COL.s3, values: Array.from(dm) }, { name: '난방', color: COL.s8, values: Array.from(gm) }], { unit: 'kg', h: 170 });
    drawOcc(); drawDay();
  }
  function dateLabel(d) { const dt = new Date(2026, 0, 1 + d); return `${dt.getMonth() + 1}월 ${dt.getDate()}일(${'일월화수목금토'[dt.getDay()]})`; }
  function drawHeat() {
    const { a, unit, name, temp, ramp, offZero } = heatSeries(heatMode), box = $('#heat'), RAMP = ramp || SEQ;
    $('#heatTitle').textContent = '연간 시간별 히트맵 · ' + name;
    $('#heatDesc').textContent = HEAT_DESC[heatMode];
    let mn = Infinity, mx = -Infinity; for (const v of a) { mn = Math.min(mn, v); mx = Math.max(mx, v); }
    if (!temp) { mn = 0; const s = Array.from(a).filter(v => !offZero || v > 1e-4).sort((p, q) => p - q); mx = Math.max(s[Math.floor(s.length * 0.995)] || 0, 1e-6); }
    const cw = 3, ch = 9, L = 34, W = L + 365 * cw + 70, Hh = 24 * ch + 22;
    box.innerHTML = `<canvas width="${W * 2}" height="${Hh * 2}" style="aspect-ratio:${W}/${Hh}"></canvas>`;
    const cv = box.querySelector('canvas'), g = cv.getContext('2d'); g.scale(2, 2);
    const col = v => { if (offZero && v <= 1e-4) return '#eceef1'; const t = Math.max(0, Math.min(1, (v - mn) / (mx - mn || 1))); const i = (offZero ? 0.15 + 0.85 * t : t) * (RAMP.length - 1), k = Math.floor(i), f = i - k; if (k >= RAMP.length - 1) return RAMP[RAMP.length - 1]; const p = hx(RAMP[k]), q = hx(RAMP[k + 1]); return `rgb(${p.map((x, j) => Math.round(x + (q[j] - x) * f)).join(',')})`; };
    for (let d = 0; d < 365; d++) for (let h = 0; h < 24; h++) { g.fillStyle = col(a[d * 24 + h]); g.fillRect(L + d * cw, h * ch, cw, ch); }
    g.fillStyle = COL.txt; g.font = '10px sans-serif'; g.textAlign = 'right';
    [0, 6, 12, 18, 23].forEach(h => g.fillText(h + '시', L - 4, h * ch + 8));
    g.textAlign = 'left'; let d0 = 0; MON.forEach((m, i) => { g.fillText(m, L + d0 * cw + 2, 24 * ch + 14); d0 += E.MDAYS[i]; });
    g.strokeStyle = COL.ink; g.lineWidth = 1.2; g.strokeRect(L + selDay * cw - 0.5, -0.5 + 0.5, cw + 1, 24 * ch);
    for (let i = 0; i < 40; i++) { g.fillStyle = col(Math.max(offZero ? 1e-3 : -1e9, mn + (mx - mn) * (39 - i) / 39)); g.fillRect(L + 365 * cw + 14, i * (24 * ch / 40), 10, 24 * ch / 40 + 0.5); }
    g.fillStyle = COL.txt; g.fillText((temp ? mx.toFixed(0) : mx.toFixed(1)) + ' ' + unit, L + 365 * cw + 28, 8); g.fillText((temp ? mn.toFixed(0) : '0') + ' ' + unit, L + 365 * cw + 28, 24 * ch);
    const pos = e => { const r = cv.getBoundingClientRect(), sx = (e.clientX - r.left) / r.width * W, sy = (e.clientY - r.top) / r.height * Hh; const d = Math.floor((sx - L) / cw), h = Math.floor(sy / ch); return (d >= 0 && d < 365 && h >= 0 && h < 24) ? [d, h] : null; };
    cv.onmousemove = e => { const p = pos(e); if (!p) return hideTip(); const i = p[0] * 24 + p[1], v = +a[i]; const extra = heatMode === 'heat' ? (v > 1e-4 ? `<br>설정 ${combo.ch.t_set[i].toFixed(1)}°C · 실내 ${(L1.awhp ? combo.ch.t_in_aw : combo.ch.t_in_base)[i].toFixed(1)}°C · 외기 ${META.temp_out[i].toFixed(1)}°C` : '<br>난방 꺼짐') : ''; showTip(e, `<b>${dateLabel(p[0])} ${p[1]}시</b><br>${name}: ${v.toFixed(2)} ${unit}${extra}<br>${combo.occDays[p[0]] ? '재실일' : '비재실일'}`); };
    cv.onmouseleave = hideTip; cv.onclick = e => { const p = pos(e); if (p) { selDay = p[0]; drawHeat(); drawDay(); drawOcc(); } };
  }
  function hx(c) { return [1, 3, 5].map(i => parseInt(c.substr(i, 2), 16)); }
  function drawEU() {
    const o = euHourly(euMode), ser = EU.map(([k, n, c]) => ({ name: n, color: c, values: Array.from(E.sumMonthly(o[k])) })).filter(s => s.values.some(v => v > 0.05));
    legend('#legEu', ser.map(s => [s.name, s.color]));
    stackedBars('#chEu', MON, ser, { unit: 'kWh', h: 220 });
  }
  function drawDay() {
    const o = euHourly('after'), d = selDay, box = $('#chDay');
    $('#dayTitle').textContent = `선택일 상세 · ${dateLabel(d)} · ${combo.occDays[d] ? '재실' : '비재실'}`;
    const ser = EU.map(([k, n, c]) => ({ name: n, color: c, values: Array.from(o[k].slice(d * 24, d * 24 + 24)) })).filter(s => s.values.some(v => v > 0.001));
    const pvkw = R3 ? R3.kpi.pvKw : 0;
    legend('#legDay', ser.map(s => [s.name, s.color]).concat(pvkw ? [['PV 발전', COL.ink, true]] : []));
    stackedBars('#chDay', Array.from({ length: 24 }, (_, i) => String(i)), ser, { unit: 'kWh', h: 210, vfmt: v => v.toFixed(2), fmt: v => v.toFixed(1), line: pvkw ? { color: COL.ink, values: META.pv1kw_kwh.slice(d * 24, d * 24 + 24).map(v => v * pvkw) } : null });
    // 사람
    const pb = $('#chPpl'), W = Math.max(300, pb.clientWidth), L = 46, rowH = 22, n = combo.persons.length, Hh = n * rowH + 26;
    const SC = [['외출', COL.s4], ['재택', COL.s1], ['수면', '#3b4a63']], x = h => L + h * (W - L - 6) / 24;
    let body = '';
    combo.persons.forEach((p, i) => {
      body += `<text x="0" y="${i * rowH + 15}" font-size="11" fill="${COL.txt}">거주자${i + 1}</text>`;
      let h0 = 0; for (let h = 1; h <= 24; h++) { if (h === 24 || p[d * 24 + h] !== p[d * 24 + h0]) { const s = p[d * 24 + h0]; body += `<rect x="${x(h0) + 1}" y="${i * rowH + 3}" width="${Math.max(1, x(h) - x(h0) - 2)}" height="15" rx="3" fill="${SC[s][1]}" ${tipAttr(`거주자${i + 1} ${h0}~${h}시 ${SC[s][0]}`)}/>`; h0 = h; } }
    });
    [0, 6, 12, 18, 24].forEach(h => body += `<text x="${x(h)}" y="${n * rowH + 10}" font-size="10" text-anchor="middle" fill="${COL.txt}">${h}</text>`);
    let lx = L; SC.forEach(([nm, c]) => { body += `<rect x="${lx}" y="${n * rowH + 15}" width="10" height="10" rx="2" fill="${c}"/><text x="${lx + 14}" y="${n * rowH + 24}" font-size="10" fill="${COL.txt}">${nm}</text>`; lx += 58; });
    pb.innerHTML = svg(W, Hh, body);
    // 온도
    const tb = $('#chTmp'), H2 = 130, T = 8, B = 18, tin = (L1.awhp ? combo.ch.t_in_aw : combo.ch.t_in_base).slice(d * 24, d * 24 + 24), tset = combo.ch.t_set.slice(d * 24, d * 24 + 24), tout = META.temp_out.slice(d * 24, d * 24 + 24);
    const all = [...tin, ...tset, ...tout], ticks = axisTicks(Math.min(...all) - 1, Math.max(...all) + 1, 4), mn = ticks[0], mx = ticks[ticks.length - 1];
    const yy = v => T + (mx - v) / (mx - mn) * (H2 - T - B), xx = h => L + (h + 0.5) * (W - L - 6) / 24;
    let tbody = yAxis(ticks, yy, L, W - 6, f0);
    [[tout, COL.s1, '외기'], [tin, COL.s8, '실내'], [tset, COL.axis, '설정']].forEach(([arr, c, nm], j) => { tbody += `<path d="${Array.from(arr).map((v, h) => (h ? 'L' : 'M') + xx(h) + ',' + yy(v)).join('')}" fill="none" stroke="${c}" stroke-width="2" ${j === 2 ? 'stroke-dasharray="4 3"' : ''}/>`; });
    for (let h = 0; h < 24; h++) tbody += `<rect x="${xx(h) - (W - L) / 48}" y="${T}" width="${(W - L) / 24}" height="${H2 - T - B}" fill="transparent" ${tipAttr(`${h}시 · 외기 ${tout[h].toFixed(1)} · 실내 ${tin[h].toFixed(1)} · 설정 ${tset[h].toFixed(1)} °C`)}/>`;
    [0, 6, 12, 18, 23].forEach(h => tbody += `<text x="${xx(h)}" y="${H2 - 4}" font-size="10" text-anchor="middle" fill="${COL.txt}">${h}</text>`);
    legend('#legTmp', [['외기', COL.s1, true], ['실내', COL.s8, true], ['설정 (재택 21 · 수면 18 · 외출 16 · 비재실 10)', COL.axis, true]]);
    tb.innerHTML = svg(W, H2, tbody);
  }
  function drawOcc() {
    const el = $('#occCal'); let h = ''; for (let i = 0; i < 4; i++) h += '<i style="visibility:hidden"></i>';
    for (let d = 0; d < 365; d++) h += `<i data-d="${d}" class="${d === selDay ? 'sel' : ''}" style="background:${combo.occDays[d] ? COL.s1 : '#e3e6ea'}" ${tipAttr(dateLabel(d) + (combo.occDays[d] ? ' 재실' : ' 비재실'))}></i>`;
    el.innerHTML = h; el.onclick = e => { const t = e.target.closest('[data-d]'); if (t) { selDay = +t.dataset.d; drawDay(); drawOcc(); drawHeat(); } };
    $('#occTitle').textContent = `재실 달력 · ${combo.rec.occupied_days}일 / 365일 (이용률 ${Math.round(S.rate * 100)}%)`;
  }

  // ---------------- CSV ----------------
  const framed = (() => { try { return window.self !== window.top; } catch (e) { return true; } })();
  function flash(msg) { const n = $('#staleNote'); n.textContent = msg; n.classList.add('show'); setTimeout(() => n.classList.remove('show'), 3500); }
  function download(name, text) {
    if (framed) { // claude.ai 아티팩트 안에서는 다운로드가 막혀 있어 클립보드로 복사
      navigator.clipboard.writeText(text).then(() => flash(`CSV(${name})를 클립보드에 복사했습니다. 엑셀에 붙여넣기 하세요.`), () => flash('이 화면에서는 CSV 저장·복사가 막혀 있습니다. 오프라인 버전(zip)에서 내보내기를 사용하세요.'));
      return;
    }
    const b = new Blob(['\ufeff' + text], { type: 'text/csv;charset=utf-8' }); const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }
  function csvYears() {
    if (!R3) return; const { c, fx } = cur(), dv = c === 'KRW' ? 1 : fx, Y = R3.years; let g = '';
    let t = `구분,항목,${Y.map(r => r.y + '년 차').join(',')}\n`;
    TABLE.forEach(([gg, k, f]) => { if (gg) g = gg; t += `${g},${k},${Y.map(r => Math.round(f(r) / dv)).join(',')}\n`; });
    t += `\n단위,${c === 'KRW' ? '원' : c}\n조건,${S.house} ${S.occ}인 이용률${Math.round(S.rate * 100)}% ${region().label} ${S.awhp ? 'AWHP' : '가스보일러'} PV${S.pvN}모듈 ESS${S.essN}모듈\n`;
    download(`SC_ROI_${houseKey(S.house)}_${S.occ}_${Math.round(S.rate * 100)}.csv`, t);
  }
  function csvHours() {
    if (!combo) return; const c = combo.ch; let t = '시각,월,재실일,외기온도,PV1kW_kWh,' + META.channels.map(x => x[1]).join(',') + ',전력_설치전_kWh,전력_설치후_kWh,프로판_설치전_kg\n';
    for (let h = 0; h < E.H; h++) {
      const d = Math.floor(h / 24), dt = new Date(2026, 0, 1 + d);
      t += `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')} ${String(h % 24).padStart(2, '0')}:00,${E.MONTH[h]},${combo.occDays[d]},${META.temp_out[h]},${META.pv1kw_kwh[h]},` +
        META.channels.map(x => c[x[0]][h].toFixed(4)).join(',') + `,${L1.before.elec[h].toFixed(4)},${L1.after.elec[h].toFixed(4)},${L1.before.gas[h].toFixed(4)}\n`;
    }
    download(`SC_8760h_${combo.rec.key}_${S.region}.csv`, t);
  }

  // ---------------- 가정·출처 ----------------
  function renderInfo() {
    const st = s => `<span class="st ${s}">${{ V: '공식 확인', U: '미검증', P: '임시값', A: '가정', I: '상사 입력' }[s]}</span>`;
    $('#infoBody').innerHTML = `
<h2>이 시뮬레이터가 계산하는 방법</h2>
<ul>
<li><b>1단계 (사용량)</b>: 한국 v10 보고서의 엔진을 그대로 사용해 SC 모델 × 거주자 × 이용률 45조합의 1년 시간별 에너지를 미리 계산해 두었습니다. 거주자 일과는 KOSIS 2024 생활시간조사(취업자 30분 행동비율) 기반 확률 표본(고정 시드 42), 가전은 활동 확률 × 보정계수, 난방·냉방은 5R1C 열모델, 급탕은 75L/인·재실일, AWHP는 Therma V 공식 데이터시트 COP입니다. <b>실측이 아닌 통계 기반 시뮬레이션</b>입니다.</li>
<li>v10 회귀 확인: v10과 겹치는 28조합 모두 기준안 전력·프로판·AWHP 전력이 0.1% 이내로 일치(예: Core 72 3인 100% = 4,205kWh · 552.9kg · 6,599kWh). 3인 Core 54/DUO Max 45와 이용률 10%는 이번에 새로 계산한 조합입니다.</li>
<li><b>2단계 (설비)</b>: PV는 지역별 1kW당 시간 발전량 × 모듈 수 × (1 − 연간 열화 × 경과 연수). ESS는 가용 용량 = 모듈 × 5kWh × SOH, 충방전 효율 √0.9씩, C-rate 0.5의 단순 규칙 운전(자가소비 우선: PV 잉여만 충전, 부족할 때 방전). 최적화 운전(LP)은 하지 않습니다.</li>
<li><b>에너지 자립률</b>: 대표값 = PV 발전량 ÷ 연간 전력 사용량(생산 기준, 100%를 넘을 수 있음). 보조값 = 자가충족률 = 1 − 계통 수전량 ÷ 연간 전력 사용량. 가스(프로판) 사용분은 포함하지 않습니다. 둘 다 1년 차, 자가소비 우선 운전 기준.</li>
<li><b>HEMS</b>: 실제 제어는 구현하지 않고, 설치 후 전체 전력 사용량에 계절별 절감률을 곱해 줄입니다(가스는 미적용). 동절기 12~2월, 하절기 6~8월, 나머지 간절기(남반구는 반대).</li>
<li><b>교체</b>: PV·ESS는 "1 − 열화율 × 경과 연수"가 교체 기준 이하가 되는 해 초에 교체(교체 후 새 제품). AWHP·인버터는 선택한 수명이 지난 해 초에 교체("고장 없음"이면 교체 안 함). PV 교체 시 인버터도 새로 봅니다.</li>
<li><b>3단계 (요금)</b>: 한전 주택용 저압 누진제는 v10 요금 계산기를 그대로 옮겼습니다(51,900개 경우 원 단위 일치, 300kWh = 57,760원). 월 상계는 잉여 kWh가 다음 달로 무기한 이월되며, 20년을 순서대로 계산합니다(1년 차는 이월 0에서 시작). 요금 인상률은 매년 청구액 전체에 곱합니다. FIT 단가는 고정, TOU 매전 단가는 전기요금 인상률을 따릅니다.</li>
<li><b>연간 이득</b> = 설치 전 총비용(전기 + 프로판) − 설치 후 총비용(전기 − 매전 수익 + 프로판 + 유지보수비). <b>누적 순이익</b> = 누적 이득 − 누적 CAPEX(보조금 차감, 교체 포함). 할인율은 적용하지 않습니다.</li>
<li>매년 같은 기상(TMY)과 같은 생활 패턴이 반복된다고 봅니다. 15분 계산 결과를 1시간 단위로 합쳐 씁니다.</li>
<li>계산 검증: 2·3단계 계산(JS)은 별도로 작성한 Python 기준 구현과 4개 시나리오 × 20년에서 0.000001원 이내로 일치합니다.</li>
</ul>
<h2>입력값과 근거 수준</h2>
<table><tr><th>항목</th><th>값</th><th>근거</th><th>수준</th></tr>
<tr><td>기상</td><td>${META.weather_src || ''}</td><td>15분 보간, 연간 PV 1kW 발전 ${f0(E.sum(META.pv1kw_kwh || [0]))}kWh (경사 25°, 정남, 시스템 손실 14%, 인버터 97%)</td><td>${st('V')}</td></tr>
<tr><td>설정온도</td><td>난방 재택 21 / 수면 18 / 외출 16 / 비재실 10°C, 냉방 6~9월 재택 26 / 수면 27°C</td><td>v10 가정</td><td>${st('A')}</td></tr>
<tr><td>외피 U값·창 면적</td><td>모델별 houses.yaml</td><td>v10 가정</td><td>${st('A')}</td></tr>
<tr><td>AWHP COP</td><td>A7/W35 4.7, A2/W35 3.7, A-7/W35 2.7 등</td><td>Therma V HM091HF UB40 데이터시트(A-7 미만 외삽은 미검증)</td><td>${st('V')}</td></tr>
<tr><td>가스보일러 효율</td><td>90%</td><td>v10</td><td>${st('V')}</td></tr>
<tr><td>프로판 단가</td><td>${f0(D.init.gasPrice)}원/kg (기본값)</td><td>오피넷 일반프로판 2026-10 4주 전국 평균</td><td>${st('V')}</td></tr>
<tr><td>한전 누진제</td><td>기본 910/1,600/7,300원, 120/214.6/307.3원/kWh, 하계 7~8월 300/450kWh, 기후 9·연료 5원, VAT 10%, 기금 2.7%</td><td>한전 요금표</td><td>${st('V')}</td></tr>
<tr><td>주택용 계시별(TOU)</td><td>편집 가능</td><td>2019 한전 실증사업 시간대·배율 기반 가정. 한국 일반 가정 전국 요금표 없음</td><td>${st('A')}</td></tr>
${D.costFields.filter(f => f[0] !== 'g').map(f => `<tr><td>${f[1].replace(/<[^>]+>/g, '')}</td><td>${(+f[2]).toLocaleString('ko-KR')}</td><td>${f[4]}</td><td>${st(f[3])}</td></tr>`).join('')}
<tr><td>전기·가스 인상률, 유지보수비, FIT 단가</td><td>기본 ${D.init.escE}% · ${D.init.escG}% · ${D.init.omPct}% · ${D.init.fitPrice}원/kWh</td><td>근거 없는 출발값. 상사 입력용</td><td>${st('I')}</td></tr>
<tr><td>환율</td><td>USD 1,400원 · AUD 900원 (기본)</td><td>표시용. 상단에서 직접 입력</td><td>${st('I')}</td></tr>
</table>
<h2>한계</h2>
<ul>
<li>ESS 단가는 국내 근거가 없어 미국 벤치마크를 환산한 값이며 가장 불확실한 입력입니다.</li>
<li>월 상계에서는 ESS가 요금을 거의 줄이지 못합니다(잉여를 다음 달로 넘길 수 있으므로). ESS 효과를 보려면 TOU 요금제·TOU 운전을 선택하세요.</li>
<li>계약전력 증설 시설부담금 등 부대비용은 "부대공사비"에 직접 넣어야 반영됩니다(기본 0원).</li>
<li>한국 남부(광주)는 기상 파일 확보 후 추가, LA·멜버른은 생활시간·요금·기상 데이터 확보 후 추가 예정입니다.</li>
</ul>`;
  }

  // ---------------- 툴팁 ----------------
  const tip = $('#tip');
  function showTip(e, html) { tip.innerHTML = html; tip.hidden = false; const x = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 8), y = Math.min(e.clientY + 14, innerHeight - tip.offsetHeight - 8); tip.style.left = x + 'px'; tip.style.top = y + 'px'; }
  function hideTip() { tip.hidden = true; }
  document.addEventListener('mousemove', e => { const t = e.target.closest && e.target.closest('[data-tip]'); if (t) showTip(e, t.getAttribute('data-tip')); else if (!e.target.closest('canvas')) hideTip(); });

  // ---------------- 시작 ----------------
  function renderAll() { renderSim(); if (!$('#tab-data').hidden) renderData(); renderInfo(); }
  function boot() {
    buildInputs();
    $$('#tabs a').forEach(a => a.onclick = () => { $$('#tabs a').forEach(x => x.classList.toggle('on', x === a)); $$('.tab').forEach(t => t.hidden = t.id !== 'tab-' + a.dataset.tab); if (a.dataset.tab === 'data') renderData(); scrollTo(0, 0); });
    $('#csvBtn').onclick = csvYears; $('#csvHour').onclick = csvHours;
    if (framed) { $('#csvBtn').textContent = 'CSV 복사'; $('#csvHour').textContent = '이 조합의 8,760시간 데이터 CSV 복사'; }
    $('#dataVer').textContent = window.SCREGIONS_VER ? '데이터 ' + window.SCREGIONS_VER : '';
    let rt; addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(renderAll, 150); });
    run(3);
  }
  boot();
})();
