#!/usr/bin/env python3
"""Local port of BonusHunt.gg's Engine 'Test your math' table reader (from site JS, Nov 2026)
plus the public warning thresholds from bonushunt.gg/engine/how-it-works.
Usage: python bh_rate_check.py <publish_files dir>   (needs index.json + lookUpTable_<mode>_0.csv)
Optional: put tier_lists_all.csv next to this script to see RTP percentile vs live games.
Not the official scorer: the balance score and 'top 15% volatility' / 'extreme 10%' rules
depend on the live cohort and are only approximated. For the official answer drop the same
folder on https://bonushunt.gg/engine/math-check (runs in your browser)."""
import sys, os, json, math, csv
BANDS=[.1,.25,.5,1,2,5,10,25,50,100,250,500,1e3,5e3,float('inf')]
def band(x): return 0 if x==0 else next(i for i,t in enumerate(BANDS) if x<t)+1
def eff(ps): return math.exp(-sum(p*math.log(p) for p in ps if p>0))
def read(fn):
    by={}; tot=0
    with open(fn) as f:
        for line in f:
            p=line.strip().split(',')
            if len(p)<3 or not p[1].strip().isdigit(): continue
            w=int(p[1]); pay=int(p[2])
            if w==0: continue
            by[pay]=by.get(pay,0)+w; tot+=w
    return by,tot
def stats(by,tot,cost):
    n=sorted((pay/(100*cost),w/tot,w) for pay,w in by.items())
    o=l=z=loss=prof=0; u=[0]*(len(BANDS)+1); xr=[0]*(len(BANDS)+1)
    for x,p,w in n:
        r=p*x; o+=r; l+=r*x
        if x==0: z+=p
        if x<1: loss+=p
        if x>1: prof+=p
        b=band(x); u[b]+=p; xr[b]+=r
    half=(tot+1)//2; acc=0; med=n[-1][0]
    for x,p,w in n:
        acc+=w
        if acc>=half: med=x; break
    def top(m):
        t=m; r=0
        for x,p,w in reversed(n):
            if t<=0: break
            a=min(t,p); r+=a*x; t-=a
        return r/o if o else 0
    mx,mp,_=n[-1]
    return dict(rtp=o,zeroRate=z,lossRate=loss,profitRate=prof,medianX=med,sd=math.sqrt(max(0,l-o*o)),
        maxX=mx,maxWinOfBet=mx*cost,maxProbability=mp,maxRtpShare=mp*mx/o if o else 0,
        top1=top(.01),top01=top(.001),top001=top(1e-4),effectiveResultBands=eff(u),uniquePayouts=len(n))
def warnings(s,cost,is_base,base_rtp):
    cat='base' if is_base else ('enhanced' if cost<=5 else 'paid')
    W=[]; avoid=False
    if s['maxRtpShare']>=.5: W.append('AVOID max win carries >=50% of RTP'); avoid=True
    if cat=='paid':
        if s['zeroRate']>=.9 and s['lossRate']>=.95: W.append('AVOID dead buy'); avoid=True
        if s['top01']>=.5 or s['top1']>=.8: W.append('AVOID tail-funded buy'); avoid=True
        if s['zeroRate']>=.5: W.append('CAUTION paid spin (pays 0 on >=50%): goes to Paid spins list; capped at B if it lands in Mystery')
    if not is_base and base_rtp is not None and s['rtp']<=base_rtp-0.005: W.append('AVOID worse than base (>=0.5pp below)'); avoid=True
    soft=[]
    if .2<=s['maxRtpShare']<.5: soft.append('max win 20-50% of RTP')
    if s['top01']>=.3 or s['top1']>=.6: soft.append('tail heavy (top0.1%>=30% or top1%>=60%)'+(' [spins: only if extreme 10%]' if cat!='paid' else ''))
    if s['zeroRate']>=.8: soft.append('>=80% pay zero'+(' [spins: only if extreme 10%]' if cat!='paid' else ''))
    if s['lossRate']>=.9: soft.append('>=90% pay under stake')
    if s['effectiveResultBands']<2.5: soft.append('<2.5 effective payout bands')
    soft.append('(+ volatility top-15% for type: check on site)')
    real=[x for x in soft if not x.startswith('(')]
    if len(real)>=2: W.append('CAUTION (capped at B): '+'; '.join(real))
    elif real: W.append('one soft signal (needs 2 for Caution): '+real[0])
    return cat,W,avoid
def main(d):
    idx=json.load(open(os.path.join(d,'index.json')))
    res={}
    for m in idx['modes']:
        fn=os.path.join(d,f"lookUpTable_{m['name']}_0.csv")
        if not os.path.exists(fn): fn=os.path.join(d,m['weights'].replace('.zst','')) if 'weights' in m else fn
        if not os.path.exists(fn): print('missing',fn); continue
        by,tot=read(fn); res[m['name']]=(float(m['cost']),stats(by,tot,float(m['cost'])))
    base=res.get('base',(1,None))[1]; brtp=base['rtp'] if base else None
    probs={}
    for name,(c,s) in res.items(): probs.setdefault(round(s['maxProbability'],15),[]).append((name,c))
    cohort=None
    here=os.path.join(os.path.dirname(os.path.abspath(__file__)),'tier_lists_all.csv')
    if os.path.exists(here): cohort=[float(r['rtp']) for r in csv.DictReader(open(here))]
    for name,(c,s) in res.items():
        cat,W,_=warnings(s,c,name.lower()=='base',brtp)
        print(f"\n== {name} cost {c}x [{cat}]")
        for k,v in s.items(): print(f"   {k:22s} {v:.6g}")
        if cohort:
            pr=(sum(r<s['rtp'] for r in cohort)+.5*sum(r==s['rtp'] for r in cohort))/len(cohort)*100
            print(f"   RTP percentile vs live tier lists ~{pr:.0f} (A needs ~>=75 in practice; 96.70% ~= 92nd)")
        for w in W: print('   !',w)
    for p,ms in probs.items():
        if len(ms)>=3 and len({c for _,c in ms})>=3: print(f"\n!!! LAZY-MATH FLAG (FLAT_MAX_ODDS): {ms} share max-win probability {p} -> whole game F")
if __name__=='__main__': main(sys.argv[1])
