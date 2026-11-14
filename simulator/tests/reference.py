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
        tou = T['tou']; sidx, per, price = tou_arrays(tou)
        for m in range(12):
            en = 0; kw = 0
            sm = tou['seasonMonths'][m] if tou.get('seasonMonths') else season(np.array([m+1]))[0]
            for k in range(3):
                sel = (MONTH == m+1) & (per == k)
                b = netm(imp[sel].sum(), exp[sel].sum(), st, f'p{k}') if net else imp[sel].sum()
                en += b * tou['rates'][sm][k]; kw += b
            add = tou['addQ'][m // 3] if tou.get('addQ') else tou.get('addPerKwh', 0)
            sub = tou.get('baseFee', 0) + tou.get('dailyFee', 0) * MD[m] + en + kw * add
            tot += math.floor((sub + round(sub*0.1) + math.floor(sub*0.027/10)*10)/10)*10 if tou.get('krTax') else sub * fx
    if P['exportMode'] == 'fit': inc = exp.sum() * P['fitPrice'] * fx
    elif P['exportMode'] == 'tou': inc = (exp * price).sum() * P['touExportRatio'] * fx
    return tot, inc

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
    load_=eA*(1-red[sea])
    pv1=np.array(meta['pv1kw_kwh']); kw=P['pvN']*P['pvModW']/1000; ek=P['essN']*P['essModKwh']
    price=None
    if T['type']=='tou':
        tou=T['tou']
        _,_,price=tou_arrays(tou); dmin=np.repeat(price.reshape(365,24).min(1),24); dmax=np.repeat(price.reshape(365,24).max(1),24)
    gross = kw*C['pvPerKw']+ek*C['essPerKwh']+(C['awhp'] if c['awhp'] else 0)+(C['hems'] if hm['on'] and C['hemsInclude'] else 0)+(C['misc'] if (kw>0 or ek>0 or c['awhp']) else 0)
    sub = (C['subPV'] if kw>0 else 0)+(C['subESS'] if ek>0 else 0)+(C['subAWHP'] if c['awhp'] else 0)+(C['subHEMS'] if hm['on'] and C['hemsInclude'] else 0)
    inv = max(C['invMin'], C['invPerKw']*max(kw, ek*P['essCrate'] if ek>0 else 0)) if (kw>0 or ek>0) else 0
    bB,_ = bill(eB, np.zeros(8760), P, T, K, {'c':0})
    st={'c':0}; ages=dict(pv=0,ess=0,inv=0,aw=0); soc=0; res=[]; cumB=cumC=0
    for y in range(1,P['years']+1):
        capT = gross-sub if y==1 else 0
        if y>1:
            if kw>0 and P['pvDeg']>0 and 1-P['pvDeg']/100*ages['pv']<=P['pvRepl']/100+1e-9: capT+=kw*C['pvReplPerKw']; ages['pv']=0; ages['inv']=0
            if ek>0 and P['essDeg']>0 and 1-P['essDeg']/100*ages['ess']<=P['essRepl']/100+1e-9: capT+=ek*C['essReplPerKwh']; ages['ess']=0
            if inv>0 and P['invLife']>0 and ages['inv']>=P['invLife']: capT+=inv; ages['inv']=0
            if c['awhp'] and P['awhpLife']>0 and ages['aw']>=P['awhpLife']: capT+=C['awhpRepl']; ages['aw']=0
        pv=pv1*kw*max(0,1-P['pvDeg']/100*ages['pv']); cap=ek*max(0,1-P['essDeg']/100*ages['ess']); pm=cap*P['essCrate']; e=math.sqrt(P['essRte'])
        imp=np.zeros(8760); exp=np.zeros(8760); soc=min(soc,cap)
        for h in range(8760):
            n=load_[h]-pv[h]
            if n<=0:
                s_=-n
                if cap>0: q=min(s_,pm,(cap-soc)/e); soc+=q*e; s_-=q
                exp[h]=s_
            else:
                need=n; tm = price is not None and P['essMode']=='tou'
                if cap>0 and (not tm or price[h]>dmin[h]+1e-9): q=min(need,pm,soc*e); soc-=q/e; need-=q
                imp[h]=need
                if tm and P['gridCharge'] and cap>0 and price[h]<=dmin[h]+1e-9 and dmax[h]*P['essRte']>price[h]:
                    q=min(pm,(cap-soc)/e)
                    if q>0: soc+=q*e; imp[h]+=q
        bA,inc = bill(imp,exp,P,T,K,st)
        fe=(1+P['escE']/100)**(y-1); fg=(1+P['escG']/100)**(y-1)
        before=bB*fe+gB.sum()*P['gasPrice']*fg
        after=bA*fe-inc*(1 if P['exportMode']=='fit' else fe)+gA.sum()*P['gasPrice']*fg+gross*P['omPct']/100
        ben=before-after; cumB+=ben; cumC+=capT
        res.append(dict(y=y,capT=capT,ben=ben,net=cumB-cumC,imp=imp.sum(),exp=exp.sum(),pv=pv.sum()))
        for k in ages: ages[k]+=1
    return res

if __name__=='__main__':
    D=json.load(open(ROOT/'tests/defaults.json')); cases=json.load(open(ROOT/'tests/cases.json'))
    js={c['key']:c for c in json.load(open(sys.argv[1]))}
    worst=0
    for c in cases:
        r=run(c.get('region','kr_central'),c,D); j=js[c['key']+c.get('region','')]['years']
        for a,b in zip(r,j):
            for k in ['capT','ben','net','imp','exp','pv']:
                d=abs(a[k]-b[k]); worst=max(worst,d)
                if d>1.0: print('DIFF',c['key'],a['y'],k,a[k],b[k])
        print(c['key'],'years',len(r),'최종 누적순이익 py',round(r[-1]['net']),'js',round(j[-1]['net']))
    print('최대 절대 차이',worst)
