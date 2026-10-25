"""Explore raw learner data with pandas and export aggregate analysis results."""
from pathlib import Path
import json, sys, math
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input-dir',type=Path,default=Path(__file__).resolve().parents[1]/'data/raw')
args=parser.parse_args()
base=args.input_dir
project=Path(__file__).resolve().parents[1]
(project/'reports').mkdir(exist_ok=True)

u=pd.read_csv(base/'paid_user_data.csv',encoding='cp1258')
d=pd.read_csv(base/'paid_user_learning_data.csv',encoding='utf-8')
mods=['gym','other','communicate_roadmap','vocabulary_roadmap','onion_gpt']
nums=mods+['total_using_time','total_complete_lesson']
original_missing={'users':u.isna().sum().to_dict(),'learning':d.isna().sum().to_dict()}
for c in ['install_date','active_at','expire_date']:
    u[c]=pd.to_datetime(u[c],format='%m/%d/%Y',errors='coerce')
d['date']=pd.to_datetime(d['check_in_date'],format='%m/%d/%Y',errors='coerce')
for c in nums: d[c]=pd.to_numeric(d[c],errors='coerce')
assert u.user_id.is_unique
assert u.user_id.notna().all() and d.user_id.notna().all(), 'Missing user IDs.'
assert d.user_id.isin(u.user_id).all(), 'Unknown user IDs in learning logs.'
assert not d.duplicated(['user_id','date']).any()
assert not d[nums].isna().any().any(), 'Missing numeric values: stop instead of silently filling.'
assert not u[['install_date','active_at','expire_date']].isna().any().any()
assert not d.date.isna().any()
assert not d[nums].lt(0).any().any()
assert np.isfinite(d[nums].to_numpy(dtype=float)).all(), 'Nonfinite numeric values.'
d['study']=d[mods].sum(axis=1,min_count=len(mods))
d['module_gt_app']=d.study>d.total_using_time+1e-6
d['extreme_day']=d.study.gt(8)|d.total_using_time.gt(8)
d['study_active']=d.study.gt(0)
u['invalid_dates']=u.install_date.gt(u.active_at)|u.expire_date.lt(u.active_at)
u['cohort']=u.active_at.dt.to_period('M').astype(str)
d=d.merge(u[['user_id','active_at','expire_date','install_date','plan','cohort','invalid_dates']],on='user_id',how='left',validate='many_to_one')
d['day']=(d.date-d.active_at).dt.days
d['week']=d.day//7
lo,hi=d.date.min(),d.date.max()

def f(x):
    if isinstance(x,(np.integer,)): return int(x)
    if isinstance(x,(np.floating,)): return None if not np.isfinite(x) else float(x)
    if isinstance(x,(np.bool_,)): return bool(x)
    if isinstance(x,(pd.Timestamp,)): return x.isoformat()
    raise TypeError(type(x).__name__)

def wilson(k,n,z=1.959963984540054):
    if not n: return [None,None]
    p=k/n; den=1+z*z/n; ctr=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [ctr-half,ctr+half]

def dist(s):
    return {'mean':float(s.mean()),'median':float(s.median()),'q10':float(s.quantile(.1)),
            'q25':float(s.quantile(.25)),'q75':float(s.quantile(.75)),
            'q90':float(s.quantile(.9)),'q95':float(s.quantile(.95)),
            'q99':float(s.quantile(.99)),'min':float(s.min()),'max':float(s.max())}

def eligible(period, valid=False):
    z=u.loc[u.active_at.ge(lo)&(u.active_at+pd.Timedelta(days=period-1)).le(hi)]
    return z.loc[~z.invalid_dates] if valid else z

def frame(period,z=None,rows=None):
    if z is None: z=eligible(period)
    if rows is None: rows=d
    t=rows.loc[rows.user_id.isin(z.user_id)&rows.day.between(0,period-1)]
    x=z.set_index('user_id').join(t.groupby('user_id').agg(study_hours=('study','sum'),
        app_hours=('total_using_time','sum'),study_days=('study_active','sum'),
        checkin_days=('date','nunique'),module_gt_app_days=('module_gt_app','sum'),extreme_days=('extreme_day','sum')))
    for c in ['study_hours','app_hours','study_days','checkin_days','module_gt_app_days','extreme_days']:
        x[c]=x[c].fillna(0)
    return x,t

def summarize(x,target):
    n=len(x); k=int(x.study_hours.ge(target).sum()); ns=int(x.study_hours.gt(0).sum())
    return {'eligible_users':n,'checkin_users':int(x.checkin_days.gt(0).sum()),'study_users':ns,'no_study_users':n-ns,
            'goal_users':k,'goal_rate':k/n if n else None,'goal_wilson_95':wilson(k,n),
            'study_hours':float(x.study_hours.sum()),'app_hours':float(x.app_hours.sum()),'study_days':int(x.study_days.sum()),
            'study_hours_per_user':dist(x.study_hours),'app_hours_per_user':dist(x.app_hours),
            'study_days_per_user':dist(x.study_days),
            'active_user_study_hours':dist(x.loc[x.study_hours.gt(0),'study_hours']),
            'goal_rate_among_study_users':k/ns if ns else None,
            'users_with_module_gt_app_days':int(x.module_gt_app_days.gt(0).sum()),
            'users_with_extreme_days':int(x.extreme_days.gt(0).sum())}

quality={
 'users':len(u),'unique_users':u.user_id.nunique(),'daily_rows':len(d),'unique_log_users':d.user_id.nunique(),
 'duplicate_user_dates':int(d.duplicated(['user_id','date']).sum()),
 'users_without_logs':int((~u.user_id.isin(d.user_id)).sum()),'unmatched_log_rows':int(d.active_at.isna().sum()),
 'source_missing':original_missing,'numeric_missing_after_parse':d[nums].isna().sum().to_dict(),
 'negative_values':d[nums].lt(0).sum().to_dict(),
 'ranges':{c:[str(u[c].min().date()),str(u[c].max().date())] for c in ['install_date','active_at','expire_date']},
 'observation_start':str(lo.date()),'observation_end':str(hi.date()),
 'calendar_gap_days':[str(x.date()) for x in pd.date_range(lo,hi).difference(d.date.unique())],
 'calendar_gap_days_2024':[str(x.date()) for x in pd.date_range('2024-01-01',hi).difference(d.date.unique())],
 'invalid_chronology_users':int(u.invalid_dates.sum()),'install_after_activation_users':int(u.install_date.gt(u.active_at).sum()),
 'expiry_before_activation_users':int(u.expire_date.lt(u.active_at).sum()),
 'invalid_chronology_plan':u.loc[u.invalid_dates,'plan'].value_counts().to_dict(),
 'pre_activation_rows':int(d.day.lt(0).sum()),'pre_activation_users':d.loc[d.day.lt(0),'user_id'].nunique(),
 'post_expiry_rows':int(d.date.gt(d.expire_date).sum()),'post_expiry_users':d.loc[d.date.gt(d.expire_date),'user_id'].nunique(),
 'before_install_rows':int(d.date.lt(d.install_date).sum()),
 'module_gt_app_days':int(d.module_gt_app.sum()),'module_gt_app_users':d.loc[d.module_gt_app,'user_id'].nunique(),
 'module_gt_app_excess_hours':float((d.study-d.total_using_time).clip(lower=0).sum()),
 'extreme_days':int(d.extreme_day.sum()),'extreme_users':d.loc[d.extreme_day,'user_id'].nunique(),
 'app_gt8_days':int(d.total_using_time.gt(8).sum()),'study_gt8_days':int(d.study.gt(8).sum()),
 'study_hours_extreme_days':float(d.loc[d.extreme_day,'study'].sum()),'total_study_hours':float(d.study.sum()),
 'app_hours_extreme_days':float(d.loc[d.extreme_day,'total_using_time'].sum()),'total_app_hours':float(d.total_using_time.sum()),
 'positive_app_zero_study_days':int((d.total_using_time.gt(0)&d.study.eq(0)).sum()),
 'zero_study_days':int(d.study.eq(0).sum()),'zero_app_days':int(d.total_using_time.eq(0).sum()),
 'lesson_positive_zero_modules_days':int((d.total_complete_lesson.gt(0)&d.study.eq(0)).sum()),
 'other_only_study_days':int((d.other.gt(0)&d[[c for c in mods if c!='other']].sum(axis=1).eq(0)).sum()),
 'day_distributions':{'app_hours':dist(d.total_using_time),'module_hours':dist(d.study)},
 'redundant_checkin_date_mismatches':{'day':int(d.date.dt.day.ne(d['check_in_date.1']).sum()),
        'month':int(d.date.dt.month.ne(d.check_in_month).sum()),'year':int(d.date.dt.year.ne(d.check_in_year).sum())},
 'motivation_counts':u.motivation.value_counts(dropna=False).to_dict(),'plan_counts':u.plan.value_counts().to_dict(),
 'activation_cohorts':u.cohort.value_counts().sort_index().to_dict()
}
out={'definitions':{
 'study_hours':'sum gym, other, communicate_roadmap, vocabulary_roadmap, onion_gpt; hours proxy, possible module overlap',
 'study_day':'sum of five modules > 0; excludes lesson count from criterion',
 'checkin_day':'observed daily source row even if recorded hours zero',
 'window':'N days inclusive day 0 through N-1 from earliest Pro activation; must be within observation bounds',
 'zeros':'Missing user-days treated as zero recorded activity only under complete tracking assumption; no numeric missing values observed.',
 'fixed_weekly_cohort':'activation through observation_end minus 90 days; all 13 weeks use same users',
 'W8':'zero-based week 8, days 56-62; requires 63-day observation; early week days 0-6',
 'invalid_chronology':'install_date > active_at OR expire_date < active_at; retained primary, excluded sensitivity',
 'module_gt_app':'study > total_using_time + 0.000001 hours; retained primary',
 'extreme_day':'app_hours > 8 OR study_hours > 8; retained primary',
 'row_exclusions':'Remove flagged logged rows only, denominator unchanged; these are reduced-recorded-hours bounds, not corrected truth',
 'user_exclusions':'Remove entire users with a flagged row in analyzed window; creates selected population',
 'long_windows':'120/150 days are operational approximations for 4/5 months',
 'renewal_limits':'Earliest activation may precede repeat purchase; plan and expiry cannot reconstruct purchase episodes',
 'statistical_limits':'Associations are descriptive, observational; CIs do not cover tracking bias or prove causality'
 },'quality':quality,'goals':{},'fixed_retention':[],'module_first30':[],'early7_w8':[]}

for n,target in [(30,20),(120,100),(150,100)]:
    x,t=frame(n)
    obj={'activation_cutoff':str((hi-pd.Timedelta(days=n-1)).date()),'primary':summarize(x,target)}
    obj['app_time_goal_comparison']={'app_goal_users':int(x.app_hours.ge(target).sum()),'app_goal_rate':float(x.app_hours.ge(target).mean()),
       'app_only_goal_users':int((x.app_hours.ge(target)&x.study_hours.lt(target)).sum())}
    obj['by_plan']=[{'plan':p,**summarize(v,target)} for p,v in x.groupby('plan')]
    obj['by_cohort']=[{'cohort':p,**summarize(v,target)} for p,v in x.groupby('cohort')]
    obj['by_motivation']=[{'motivation':p,**summarize(v,target)} for p,v in x.groupby('motivation')]
    obj['distribution_counts']={'zero':int(x.study_hours.eq(0).sum()),'gt0_lt5':int(x.study_hours.gt(0).mul(x.study_hours.lt(5)).sum()),
        'ge5_lt10':int(x.study_hours.ge(5).mul(x.study_hours.lt(10)).sum()),'ge10_lt20':int(x.study_hours.ge(10).mul(x.study_hours.lt(20)).sum()),
        'ge20_lt50':int(x.study_hours.ge(20).mul(x.study_hours.lt(50)).sum()),'ge50_lt100':int(x.study_hours.ge(50).mul(x.study_hours.lt(100)).sum()),'ge100':int(x.study_hours.ge(100).sum())}
    obj['sensitivity']={}
    for name,flag in [('omit_module_gt_app_rows',d.module_gt_app),('omit_extreme_rows',d.extreme_day),('omit_either_flagged_rows',d.module_gt_app|d.extreme_day)]:
        xs,ts=frame(n,rows=d.loc[~flag]); obj['sensitivity'][name]=summarize(xs,target)
    xv,tv=frame(n,z=eligible(n,valid=True)); obj['sensitivity']['exclude_invalid_date_users']=summarize(xv,target)
    for flag,label in [('module_gt_app_days','exclude_users_with_module_gt_app'),('extreme_days','exclude_users_with_extreme_days')]:
        obj['sensitivity'][label]=summarize(x.loc[x[flag].eq(0)],target)
    out['goals'][str(n)]=obj

fixed=eligible(91)
out['fixed_retention_cohort']={'users':len(fixed),'activation_cutoff':str((hi-pd.Timedelta(days=90)).date()),'start':str(fixed.active_at.min().date())}
for w in range(13):
    t=d.loc[d.user_id.isin(fixed.user_id)&d.week.eq(w)]
    st=t.loc[t.study_active]; n=len(fixed); sc=st.user_id.nunique(); cc=t.user_id.nunique()
    row={'week_index':w,'eligible_users':n,'checkin_users':cc,'study_users':sc,
      'checkin_retention':cc/n,'study_retention':sc/n,'study_wilson_95':wilson(sc,n),
      'checkin_days':len(t),'study_days':len(st),'study_hours':float(st.study.sum()),'app_hours':float(t.total_using_time.sum()),
      'study_days_per_study_user':len(st)/sc if sc else None,'study_minutes_per_study_day':st.study.mean()*60,
      'study_minutes_per_eligible_calendar_day':st.study.sum()*60/(7*n),
      'app_minutes_per_checkin_day':t.total_using_time.mean()*60,
      'checkin_days_per_checkin_user':len(t)/cc,
      'app_minutes_per_eligible_calendar_day':t.total_using_time.sum()*60/(7*n),
      'study_hours_user_distribution':dist(st.groupby('user_id').study.sum().reindex(fixed.user_id,fill_value=0))}
    assert math.isclose(row['study_minutes_per_eligible_calendar_day'],row['study_retention']*row['study_days_per_study_user']*row['study_minutes_per_study_day']/7,rel_tol=1e-12)
    out['fixed_retention'].append(row)

out['fixed_retention_sensitivity']=[]
for label,rows,base_users in [
    ('omit_extreme_rows',d.loc[~d.extreme_day],fixed),
    ('omit_module_gt_app_rows',d.loc[~d.module_gt_app],fixed),
    ('exclude_invalid_date_users',d,fixed.loc[~fixed.invalid_dates])]:
    for w in [0,1,4,8,12]:
        t=rows.loc[rows.user_id.isin(base_users.user_id)&rows.week.eq(w)]
        st=t.loc[t.study_active]; n=len(base_users)
        out['fixed_retention_sensitivity'].append({'scenario':label,'week_index':w,'eligible_users':n,
            'study_users':st.user_id.nunique(),'study_retention':st.user_id.nunique()/n,
            'study_hours':float(st.study.sum()),'study_minutes_per_eligible_calendar_day':float(st.study.sum()*60/(7*n))})

a=out['fixed_retention'][0]; b=out['fixed_retention'][12]
factors={c:b[c]/a[c] for c in ['study_retention','study_days_per_study_user','study_minutes_per_study_day','study_minutes_per_eligible_calendar_day']}
out['retention_decomposition_w0_w12']={'ratios_w12_div_w0':factors,
 'log_change_share':{c:math.log(factors[c])/math.log(factors['study_minutes_per_eligible_calendar_day']) for c in ['study_retention','study_days_per_study_user','study_minutes_per_study_day']},
 'identity':'study minutes per eligible calendar day = study retention * study days per studying user * minutes per study day / 7',
 'note':'Arithmetic decomposition, not causal attribution. Log shares sum to one.'}

x120_150,_=frame(120,z=eligible(150)); x150,_=frame(150)
out['common_cohort_120_vs_150']={'eligible_users':len(x150),'day120_100h_users':int(x120_150.study_hours.ge(100).sum()),
 'day150_100h_users':int(x150.study_hours.ge(100).sum()),'additional_achievers_days120to149':int((x150.study_hours.ge(100)&x120_150.study_hours.lt(100)).sum()),
 'day120_median_hours':float(x120_150.study_hours.median()),'day150_median_hours':float(x150.study_hours.median())}

x30,t30=frame(30)
for mod in mods:
    pos=t30.loc[t30[mod].gt(0)]; days=pos.groupby('user_id').date.nunique(); users=len(days); repeat=int(days.ge(2).sum())
    out['module_first30'].append({'module':mod,'eligible_users':len(x30),'module_users':users,'adoption_rate':users/len(x30),
      'repeat_users':repeat,'repeat_rate_among_adopters':repeat/users,'repeat_rate_among_eligible':repeat/len(x30),
      'module_hours':float(pos[mod].sum()),'module_days':len(pos),'module_hours_per_adopter':float(pos[mod].sum()/users),
      'share_recorded_study_hours':float(pos[mod].sum()/t30.study.sum()),'days_per_adopter':dist(days)})

e63=eligible(63)
early=d.loc[d.user_id.isin(e63.user_id)&d.day.between(0,6)]
w8=d.loc[d.user_id.isin(e63.user_id)&d.day.between(56,62)]
e=e63.set_index('user_id').join(early.groupby('user_id').agg(early_study_days=('study_active','sum'),early_study_hours=('study','sum'),early_checkin_days=('date','nunique')))
e[['early_study_days','early_study_hours','early_checkin_days']]=e[['early_study_days','early_study_hours','early_checkin_days']].fillna(0)
e['w8_study']=e.index.isin(w8.loc[w8.study_active,'user_id'])
e['w8_checkin']=e.index.isin(w8.user_id)
e['early_band']=pd.cut(e.early_study_days,[-1,0,1,2,4,7],labels=['0','1','2','3-4','5-7'])
for band,g in e.groupby('early_band',observed=True):
    k=int(g.w8_study.sum());n=len(g)
    out['early7_w8'].append({'early_study_days':str(band),'eligible_users':n,'w8_study_users':k,'w8_study_rate':k/n,'w8_study_wilson_95':wilson(k,n),
      'w8_checkin_users':int(g.w8_checkin.sum()),'w8_checkin_rate':float(g.w8_checkin.mean()),'early_study_hours':float(g.early_study_hours.sum())})
out['early7_w8_denominator']={'eligible_users':len(e),'activation_cutoff':str((hi-pd.Timedelta(days=62)).date()),'w8_study_users':int(e.w8_study.sum()),'w8_study_rate':float(e.w8_study.mean())}
out['early7_w8_by_exact_days']=[{'early_study_days':int(v),'eligible_users':len(g),'w8_study_users':int(g.w8_study.sum()),'w8_study_rate':float(g.w8_study.mean())} for v,g in e.groupby('early_study_days')]
out['early7_w8_by_plan_and_band']=[{'plan':p,'early_study_days':str(b),'eligible_users':len(g),'w8_study_users':int(g.w8_study.sum()),'w8_study_rate':float(g.w8_study.mean())} for (p,b),g in e.groupby(['plan','early_band'],observed=True)]
low=e.loc[e.early_study_days.le(2)]; high=e.loc[e.early_study_days.ge(5)]
kr,nr=int(high.w8_study.sum()),len(high); kc,nc=int(low.w8_study.sum()),len(low)
rr=(kr/nr)/(kc/nc); se=math.sqrt(1/kr-1/nr+1/kc-1/nc)
out['early7_high_vs_low']={'high_early_study_days':'5-7','low_early_study_days':'0-2',
 'high_eligible':nr,'high_w8_study':kr,'high_rate':kr/nr,'low_eligible':nc,'low_w8_study':kc,'low_rate':kc/nc,
 'risk_ratio':rr,'risk_ratio_95':[math.exp(math.log(rr)-1.95996398454*se),math.exp(math.log(rr)+1.95996398454*se)],'risk_difference':kr/nr-kc/nc}
out['early7_high_vs_low_strata']=[]
for (p,c),g in e.groupby(['plan','cohort']):
    high=g.loc[g.early_study_days.ge(5)]; low=g.loc[g.early_study_days.le(2)]
    if len(high)<10 or len(low)<10: continue
    out['early7_high_vs_low_strata'].append({'plan':p,'cohort':c,'high_users':len(high),'low_users':len(low),
       'high_w8_study':int(high.w8_study.sum()),'low_w8_study':int(low.w8_study.sum()),
       'high_rate':float(high.w8_study.mean()),'low_rate':float(low.w8_study.mean())})

post=d.loc[d.day.ge(0)]
out['post_activation_overview']={'rows':len(post),'users':post.user_id.nunique(),'study_users':post.loc[post.study_active,'user_id'].nunique(),
 'app_hours':float(post.total_using_time.sum()),'study_hours':float(post.study.sum()),'positive_app_zero_study_days':int((post.total_using_time.gt(0)&~post.study_active).sum()),
 'module_gt_app_days':int(post.module_gt_app.sum()),'extreme_days':int(post.extreme_day.sum())}

for period,goal in out['goals'].items():
    primary=goal['primary']
    for group in ['by_plan','by_cohort','by_motivation']:
        assert sum(g['eligible_users'] for g in goal[group])==primary['eligible_users']
        assert sum(g['goal_users'] for g in goal[group])==primary['goal_users']
        assert math.isclose(sum(g['study_hours'] for g in goal[group]),primary['study_hours'],rel_tol=1e-12)
    assert sum(goal['distribution_counts'].values())==primary['eligible_users']
    assert primary['goal_users']<=primary['study_users']<=primary['checkin_users']<=primary['eligible_users']
assert sum(g['eligible_users'] for g in out['early7_w8'])==len(e)
assert sum(g['w8_study_users'] for g in out['early7_w8'])==int(e.w8_study.sum())
assert math.isclose(sum(g['module_hours'] for g in out['module_first30']),out['goals']['30']['primary']['study_hours'],rel_tol=1e-12)
assert all(g['eligible_users']==len(fixed) for g in out['fixed_retention'])
assert math.isclose(sum(out['retention_decomposition_w0_w12']['log_change_share'].values()),1,rel_tol=1e-12)
out['validation']={'unique_keys':True,'numeric_fields_complete_nonnegative':True,'date_parse_complete':True,
 'goal_group_reconciliation':True,'hour_distribution_partition':True,'early_bands_reconciliation':True,
 'module_hours_reconciliation':True,'fixed_retention_constant_denominator':True,'retention_decomposition_identity':True,
 'no_user_level_output':True}

(project/'reports/extended_analysis.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=f,allow_nan=False),encoding='utf-8')
print('Extended analysis passed internal reconciliations; wrote reports/extended_analysis.json')
