"""Render aggregate analysis charts; these are Python figures, not Power BI screenshots."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/figures'
OUT.mkdir(parents=True,exist_ok=True)
data=json.loads((ROOT/'reports/extended_analysis.json').read_text(encoding='utf-8'))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','figure.facecolor':'white'})
teal,navy,gold='#007F7A','#163344','#D79B35'

def save(fig,name):
    fig.savefig(OUT/f'{name}.png',dpi=170,bbox_inches='tight')
    fig.savefig(OUT/f'{name}.svg',bbox_inches='tight')
    plt.close(fig)

goals=pd.read_csv(ROOT/'data/processed/goal_summary.csv')
fig,ax=plt.subplots(figsize=(10,4.5))
bars=ax.bar(['20h / 30 days','100h / 120 days','100h / 150 days'],goals.attainment_pct,color=[teal,navy,gold],width=.55)
for bar,row in zip(bars,goals.to_dict('records')):
    ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+.15,f"{row['attainment_pct']:.2f}%\n{row['goal_users']:,} / {row['eligible_users']:,}",ha='center',fontsize=11)
ax.set(ylim=(0,7),ylabel='Eligible learners reaching target (%)',title='Few paid learners reach the recorded study-time targets')
fig.text(.12,-.02,'Complete windows only. Different eligible populations; the bars are not a within-user progression.',fontsize=9,color=navy)
save(fig,'01_target_attainment')

fixed=pd.read_csv(ROOT/'data/processed/fixed_retention.csv')
fig,axes=plt.subplots(1,3,figsize=(15,4.4))
axes[0].plot(fixed.week_index,100*fixed.checkin_users/fixed.eligible_users,label='Check-in',color=gold,lw=2)
axes[0].plot(fixed.week_index,100*fixed.learning_retention,label='Recorded study',color=teal,lw=2)
axes[0].set(title='Returning learners',ylabel='Share of fixed cohort (%)',ylim=(0,105)); axes[0].legend(frameon=False)
axes[1].plot(fixed.week_index,fixed.days_per_learner,color=teal,lw=2)
axes[1].set(title='Frequency among weekly learners',ylabel='Study days per weekly learner',ylim=(0,7))
axes[2].plot(fixed.week_index,fixed.minutes_per_study_day,color=navy,lw=2)
axes[2].set(title='Duration on study days',ylabel='Recorded minutes per study day',ylim=(0,45))
for ax in axes: ax.set_xlabel('Week index after first Pro activation'); ax.set_xticks([0,4,8,12]); ax.grid(axis='y',alpha=.15)
fig.suptitle('Engagement declines in all three components',fontsize=16,fontweight='bold',y=1.03)
fig.text(.08,-.04,f"Fixed cohort: {int(fixed.eligible_users.iloc[0]):,} learners with 91 days of follow-up. Week 0 = days 0–6.",fontsize=10)
fig.tight_layout(); save(fig,'02_retention_decomposition')

mods=pd.DataFrame(data['module_first30'])
names={'gym':'Gym','other':'Other learning','communicate_roadmap':'Communication','vocabulary_roadmap':'Vocabulary','onion_gpt':'Onion GPT'}
mods=mods.sort_values('adoption_rate')
fig,axes=plt.subplots(1,2,figsize=(12,4.5))
for ax,col,title in [(axes[0],'adoption_rate','Tried at least once / eligible learners'),(axes[1],'repeat_rate_among_adopters','Used on 2+ days / module adopters')]:
    bars=ax.barh([names[m] for m in mods.module],100*mods[col],color=teal)
    for bar,v in zip(bars,mods[col]): ax.text(100*v+1,bar.get_y()+bar.get_height()/2,f'{100*v:.1f}%',va='center',fontsize=10)
    ax.set(title=title,xlim=(0,112),xlabel='Percentage'); ax.set_xticks([0,25,50,75,100])
fig.suptitle('Onion has broad reach; communication dominates recorded study time',fontweight='bold',y=1.03)
fig.text(.1,-.03,'First 30 days; 12,851 eligible learners. Repeat means distinct days, not sessions. Module users overlap.',fontsize=9)
fig.tight_layout(); save(fig,'03_module_adoption')

early=pd.DataFrame(data['early7_w8'])
fig,ax=plt.subplots(figsize=(10,4.5))
bars=ax.bar(early.early_study_days,100*early.w8_study_rate,color=teal,width=.6)
for bar,row in zip(bars,early.to_dict('records')): ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+1,f"{100*row['w8_study_rate']:.1f}%\nn={row['eligible_users']:,}",ha='center',fontsize=10)
ax.set(title='Early study frequency is associated with later participation',ylabel='Recorded study in week 8 (%)',xlabel='Number of study days in days 0–6',ylim=(0,68))
fig.text(.12,-.02,'Week 8 = days 56–62. Complete follow-up only. Observational association; not a causal effect.',fontsize=9)
save(fig,'04_early_frequency')
print('Rendered four PNG and four SVG figures from aggregate analysis outputs.')
