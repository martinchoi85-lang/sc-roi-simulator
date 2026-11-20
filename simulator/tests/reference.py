"""시뮬레이터 계산의 독립 Python 기준 구현 (JS engine.js 교차검증용).
같은 사양 문서(가정·출처 탭)를 근거로 별도로 작성. 데이터팩 디코딩도 별도 구현."""
import json, base64, math, sys, datetime as dt
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import builtins, typing; builtins.Tuple = typing.Tuple
from engine.tariffs.korea import KoreaTariffCalculator
from engine.schema import load_country_config

ROOT = Path(__file__).resolve().parents[1]
dates = [dt.datetime(2026,1,1)+dt.timedelta(hours=h) for h in range(8760)]
MONTH = np.array([d.month for d in dates]); HOD = np.array([d.hour for d in dates]); DOW = np.array([(d.weekday()+1)%7 for d in dates])

def load(region, key):
    t = (ROOT/'data'/region/'meta.js').read_text(encoding='utf-8'); meta = json.loads(t[len('SCDATA.meta('):-3])
    t = (ROOT/'data'/region/f'c_{key}.js').read_text(encoding='utf-8'); i = t.index(',"')
    rec = json.loads(t[len('SCDATA.add('):i]); raw = base64.b64decode(t[i+2:t.rindex('"')])
    n = len(meta['channels']); u = np.frombuffer(raw[:n*8760*2], dtype='<u2').reshape(n, 8760).astype(float)
    ch = {k: u[j]/rec['scales'][j][0] + rec['scales'][j][1] for j,(k,_) in enumerate(meta['channels'])}
    return meta, rec, ch

def season(m): return np.where((m>=6)&(m<=8),1,np.where((m==12)|(m<=2),2,0))

def kr_bill(K, kwh, m): return K._calculate_single_month(kwh, m)['total_bill']

def netm(i, e, st, key):
    c = e + st.get(key, 0)
    if i >= c: st[key] = 0; return i - c
    st[key] = c - i; return 0

def tou_arrays(tou):
    if tou.get('seasonMonths'): sidx = np.array([tou['seasonMonths'][m-1] for m in MONTH])
    else: sidx = season(MONTH)
    wk = (DOW == 0) | (DOW == 6)
    per = np.array([(tou['hoursWe'][sidx[h]][HOD[h]] if (wk[h] and tou.get('hoursWe')) else (0 if (tou.get('weekendOffpeak') and wk[h]) else tou['hours'][sidx[h]][HOD[h]])) for h in range(8760)])
    price = np.array([tou['rates'][sidx[h]][per[h]] for h in range(8760)])
    return sidx, per, price

MD = [31,28,31,30,31,30,31,31,30,31,30,31]
def bill(imp, exp, P, T, K, st):
    tot = 0.0; inc = 0.0; fx = P.get('fx', 1.0); net = P['exportMode'] == 'net'; price = None
    mi = np.bincount(MONTH-1, imp, 12); me = np.bincount(MONTH-1, exp, 12)
    if T['type'] == 'kr_prog':
        for m in range(12):
            b = netm(mi[m], me[m], st, 'c') if net else mi[m]
            tot += kr_bill(K, b, m+1)
    elif T['type'] == 'tiered':
        t = T['tiered']
        for m in range(12):
            k = netm(mi[m], me[m], st, 'c') if net else mi[m]
            r = t['rates'][t['seasonMonths'][m]]; lims = t['limits'] + [1e18]
            e = 0; prev = 0; tier = 0
            for i in range(len(r)):
                q = max(0, min(k - prev, lims[i] - prev)) if k > prev else 0
                e += q * r[i]
                if q > 0: tier = i
                prev = lims[i]
            add = t['addQ'][m // 3] if t.get('addQ') else t['addPerKwh']
            tot += (max(e + t['pac'][tier], t['minCharge']) + k * add) * fx
    elif T['type'] == 'flat':
        f = T['flat']
        for m in range(12):
            k = netm(mi[m], me[m], st, 'c') if net else mi[m]
            tot += (f['dailyFee'] * MD[m] + k * f['rate']) * fx
    else:
        tou = T['tou']; sidx, per, price = tou_arrays(tou); nP = max(len(r) for r in tou['rates'])
        # 월·기간별 수전량, 하루 한도 초과분은 다른 기간으로 이동
        PI = np.zeros((12, nP)); PE = np.zeros((12, nP))
        for m in range(12):
            for k in range(nP):
                sel = (MONTH == m+1) & (per == k); PI[m, k] = imp[sel].sum(); PE[m, k] = exp[sel].sum()
        if tou.get('cap'):
            cp = tou['cap']; daily = np.where(per == cp['period'], imp, 0).reshape(365, 24).sum(1)
            dmon = MONTH.reshape(365, 24)[:, 0]
            for d in range(365):
                o = daily[d] - cp['kwh']
                if o > 0: PI[dmon[d]-1, cp['period']] -= o; PI[dmon[d]-1, cp['overPeriod']] += o
        for m in range(12):
            en = 0; kw = 0
            sm = tou['seasonMonths'][m] if tou.get('seasonMonths') else season(np.array([m+1]))[0]
            for k in range(nP):
                b = netm(PI[m, k], PE[m, k], st, f'p{k}') if net else PI[m, k]
                en += b * tou['rates'][sm][k]; kw += b
            add = tou['addQ'][m // 3] if tou.get('addQ') else tou.get('addPerKwh', 0)
            sub = tou.get('baseFee', 0) + tou.get('dailyFee', 0) * MD[m] + en + kw * add
            tot += math.floor((sub + round(sub*0.1) + math.floor(sub*0.027/10)*10)/10)*10 if tou.get('krTax') else sub * fx
    if P['exportMode'] == 'fit': inc = exp.sum() * P['fitPrice'] * fx
    elif P['exportMode'] == 'tou': inc = (exp * price).sum() * P['touExportRatio'] * fx
    return tot, inc

# HEMS 부하 이동(TOU): 같은 날 안에서 세탁·식세기(7~22시, 시간당 2.0kWh 이하)와 AWHP 급탕(하루 상한, 압축기 3.91kW 이하)을
# 계통 수전분이 있는 가장 비싼 시간에서 가장 싼 시간(PV 잉여가 있으면 매전 가치)으로 옮긴다.
LCAP, COMP, LWIN = 2.0, 3.91, (7, 22)
def hems_shift(eA, ch, awhp, pv, price, P):
    base = eA.copy(); lau = ch['laundry'].copy(); dhw = ch['aw_dhw'].copy() if awhp else None; comp = ch['aw_heat'] if awhp else None
    em = P['exportMode']
    def ev(h): return price[h] if em == 'net' else P['fitPrice'] if em == 'fit' else price[h]*P['touExportRatio'] if em == 'tou' else 0.0
    tot = [np.zeros(12), np.zeros(12)]
    for d in range(365):
        o = d*24
        for kind, s in ((0, lau), (1, dhw)):
            if s is None: continue
            budget = math.inf if kind == 0 else max(0.0, P['hems'].get('dhwCap', 0))
            if budget <= 1e-9: continue
            done = [False]*24
            for _ in range(500):
                src = -1; ms = 0.0
                for k in range(24):
                    if done[k]: continue
                    h = o+k; m = min(s[h], max(0.0, base[h]-pv[h]))
                    if m > 1e-9 and (src < 0 or price[h] > price[o+src]+1e-12): src, ms = k, m
                if src < 0: break
                ps = price[o+src]; dst = -1; cd = 0.0; room = 0.0
                for k in range(24):
                    if k == src or (kind == 0 and not (LWIN[0] <= k <= LWIN[1])): continue
                    h = o+k; cap = LCAP-s[h] if kind == 0 else COMP-comp[h]-s[h]
                    if cap <= 1e-9: continue
                    sur = pv[h]-base[h]; cc = ev(h) if sur > 1e-9 else price[h]; r = min(sur, cap) if sur > 1e-9 else cap
                    if cc < ps-1e-9 and (dst < 0 or cc < cd-1e-12): dst, cd, room = k, cc, r
                if dst < 0: done[src] = True; continue
                q = min(ms, room, budget); s[o+src] -= q; s[o+dst] += q; base[o+src] -= q; base[o+dst] += q; budget -= q; tot[kind][MONTH[o]-1] += q
                if budget <= 1e-9: break
    return base, tot

def run(region, c, D):
    meta, rec, ch = load(region, c['key'])
    P = {**D, **c}; T = D['tariffs'][c['tariff']]; C = D['cost']
    if T['type'] == 'tou': tou = T['tou']
    K = KoreaTariffCalculator(load_country_config(ROOT.parent/'korea').values['tariff'])
    app = sum(ch[k] for k in ['cook','laundry','plug','light','fridge'])
    eB = app+ch['cool_base']; gB = ch['gas_heat_kg']+ch['gas_dhw_kg']
    eA = app+ch['aw_heat']+ch['aw_backup']+ch['aw_dhw']+ch['aw_cool']+ch['aw_standby'] if c['awhp'] else eB.copy()
    gA = np.zeros(8760) if c['awhp'] else gB
    hm=P['hems']; red=np.array([hm['mid'],hm['summer'],hm['winter']])/100 if hm['on'] else np.zeros(3)
    sea=season(MONTH) if P.get('hemi','N')=='N' else np.where(season(MONTH)==1,2,np.where(season(MONTH)==2,1,0))
    pv1=np.array(meta['pv1kw_kwh']); kw=P['pvN']*P['pvModW']/1000; ek=P['essN']*P['essModKwh']
    price=None
    OFF=bool(P.get('offGrid'))
    shiftTot=[0.0,0.0]; shiftOn = hm['on'] and hm.get('shift') and T['type']=='tou' and not OFF
    if shiftOn: eS,shiftM = hems_shift(eA, ch, c['awhp'], pv1*kw, tou_arrays(T['tou'])[2], P)
    load_=eA*(1-red[sea])
    if OFF: P['exportMode']='none'; P['essMode']='self'; P['gridCharge']=False
    if T['type']=='tou':
        tou=T['tou']
        _,_,price=tou_arrays(tou); dmin=np.repeat(price.reshape(365,24).min(1),24); dmax=np.repeat(price.reshape(365,24).max(1),24)
    gross = kw*C['pvPerKw']+ek*C['essPerKwh']+(C['awhp'] if c['awhp'] else 0)+(C['hems'] if hm['on'] and C['hemsInclude'] else 0)+(C['misc'] if (kw>0 or ek>0 or c['awhp']) else 0)
    sub = (C['subPV'] if kw>0 else 0)+(C['subESS'] if ek>0 else 0)+(C['subAWHP'] if c['awhp'] else 0)+(C['subHEMS'] if hm['on'] and C['hemsInclude'] else 0)
    inv = max(C['invMin'], C['invPerKw']*max(kw, ek*P['essCrate'] if ek>0 else 0)) if (kw>0 or ek>0) else 0
    bB,_ = bill(eB, np.zeros(8760), P, T, K, {'c':0})
    def disp(pv, cap, soc, L=None):
        LL = load_ if L is None else L
        pm=cap*P['essCrate']; e=math.sqrt(P['essRte']); imp=np.zeros(8760); exp=np.zeros(8760); soc=min(soc,cap)
        tm = price is not None and P['essMode']=='tou'
        for h in range(8760):
            n=LL[h]-pv[h]
            if n<=0:
                s_=-n
                if cap>0: q=min(s_,pm,(cap-soc)/e); soc+=q*e; s_-=q
                exp[h]=s_
            else:
                need=n
                if cap>0 and (not tm or price[h]>dmin[h]+1e-9): q=min(need,pm,soc*e); soc-=q/e; need-=q
                imp[h]=need
                if tm and P['gridCharge'] and cap>0 and price[h]<=dmin[h]+1e-9 and dmax[h]*P['essRte']>price[h]:
                    q=min(pm,(cap-soc)/e)
                    if q>0: soc+=q*e; imp[h]+=q
        return imp, exp, soc
    none = P['exportMode']=='none'
    if shiftOn:   # 달마다 1년 차 정상 상태 비용(전기요금 − 매전)이 줄어드는 달에만 이동 적용
        def ycost(L):
            s0 = disp(pv1*kw, ek, 0, L)[2] if ek>0 else 0
            i_,e_,_ = disp(pv1*kw, ek, s0, L)
            if none: e_ = np.zeros(8760)
            st_={'c':0}; bill(i_,e_,P,T,K,st_); b_,x_ = bill(i_,e_,P,T,K,st_); return b_-x_
        alt = eS*(1-red[sea]); best = ycost(load_)
        for m in range(1,13):
            if shiftM[0][m-1]+shiftM[1][m-1] <= 1e-9: continue
            tr = load_.copy(); tr[MONTH==m] = alt[MONTH==m]; cc = ycost(tr)
            if cc < best-1e-6: load_=tr; best=cc; shiftTot[0]+=shiftM[0][m-1]; shiftTot[1]+=shiftM[1][m-1]
    st={'c':0}; ages=dict(pv=0,ess=0,inv=0,aw=0); res=[]; cumB=cumC=0
    soc = disp(pv1*kw, ek, 0)[2] if ek>0 else 0   # 정상 상태 시작 SOC
    fixed,_ = (0,0) if OFF else bill(np.zeros(8760), np.zeros(8760), P, T, K, {'c':0})
    for y in range(1,P['years']+1):
        capT = gross-sub if y==1 else 0
        if y>1:
            if kw>0 and P['pvDeg']>0 and 1-P['pvDeg']/100*ages['pv']<=P['pvRepl']/100+1e-9: capT+=kw*C['pvReplPerKw']; ages['pv']=0; ages['inv']=0
            if ek>0 and P['essDeg']>0 and 1-P['essDeg']/100*ages['ess']<=P['essRepl']/100+1e-9: capT+=ek*C['essReplPerKwh']; ages['ess']=0
            if inv>0 and P['invLife']>0 and ages['inv']>=P['invLife']: capT+=inv; ages['inv']=0
            if c['awhp'] and P['awhpLife']>0 and ages['aw']>=P['awhpLife']: capT+=C['awhpRepl']; ages['aw']=0
        pv=pv1*kw*max(0,1-P['pvDeg']/100*ages['pv']); cap=ek*max(0,1-P['essDeg']/100*ages['ess'])
        imp,exp,soc = disp(pv, cap, soc)
        curt = exp if none else np.zeros(8760)
        if none: exp = np.zeros(8760)
        bA,inc = (0,0) if OFF else bill(imp,exp,P,T,K,st)
        fe=(1+P['escE']/100)**(y-1); fg=(1+P['escG']/100)**(y-1)
        before=bB*fe+gB.sum()*P['gasPrice']*fg
        after=bA*fe-inc*(1 if P['exportMode']=='fit' else fe)+gA.sum()*P['gasPrice']*fg+gross*P['omPct']/100
        ben=before-after; cumB+=ben; cumC+=capT
        res.append(dict(y=y,capT=capT,ben=ben,net=cumB-cumC,imp=imp.sum(),exp=exp.sum(),pv=pv.sum(),curt=curt.sum()))
        if y==1:
            use=load_.sum(); days=int((imp.reshape(365,24).sum(1)>0.001).sum())
            s0={'c':0}
            if OFF: bS,iS=0,0
            else: bill(imp,exp,P,T,K,s0); bS,iS=bill(imp,exp,P,T,K,s0)   # 정상 상태(이월 반영) Zero Bill
            res[0]['kpi']=dict(selfSuff=1-imp.sum()/use, pvOffset=pv.sum()/use, selfCons=(pv.sum()-exp.sum()-curt.sum())/pv.sum() if pv.sum()>0 else 0, shiftL=shiftTot[0], shiftD=shiftTot[1], impDays=days, billVar=bA-fixed-inc, billVarSteady=bS-fixed-iS, unservedHours=int((imp>0.001).sum()))
        for k in ages: ages[k]+=1
    return res

if __name__=='__main__':
    D=json.load(open(ROOT/'tests/defaults.json')); cases=json.load(open(ROOT/'tests/cases.json'))
    jl=json.load(open(sys.argv[1])); assert len(jl)==len(cases)
    worst=0
    for c,jc in zip(cases,jl):
        r=run(c.get('region','kr_central'),c,D); j=jc['years']
        for a,b in zip(r,j):
            for k in ['capT','ben','net','imp','exp','pv','curt']:
                d=abs(a[k]-b[k]); worst=max(worst,d)
                if d>1.0: print('DIFF',c['key'],a['y'],k,a[k],b[k])
        jk=dict(jc['kpi']); pk=r[0]['kpi']; jk['shiftL']=jk['hemsShift']['laundry']; jk['shiftD']=jk['hemsShift']['dhw']
        for k in ['selfSuff','pvOffset','selfCons','shiftL','shiftD','impDays','billVar','billVarSteady','unservedHours']:
            d=abs(pk[k]-jk[k]); worst=max(worst,d)
            if d>1e-6*max(1,abs(pk[k])): print('KPI DIFF',c['key'],k,pk[k],jk[k])
        print(c['key'],c.get('region','kr_central'),c['tariff'],c['exportMode'],'years',len(r),'누적순이익 py',round(r[-1]['net']),'js',round(j[-1]['net']),'자립률 %.3f'%pk['selfSuff'],'버림 %.0f'%r[0]['curt'],'변동요금 %.0f'%pk['billVar'],'정상상태 %.0f'%pk['billVarSteady'],('부하이동 세탁 %.0f 급탕 %.0f'%(pk['shiftL'],pk['shiftD'])) if (pk['shiftL'] or pk['shiftD']) else '')
    print('최대 절대 차이',worst)
