"""Validate public CSV relationships, counts, and independent aggregate totals."""
from pathlib import Path
import csv,json,math
ROOT=Path(__file__).resolve().parents[1]
def read(name):
    with (ROOT/'data/processed'/f'{name}.csv').open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
dimensions={name:{row[name] for row in read(name)} for name in ['cohort','plan','module','week_index'] if name!='week_index'}
dimensions['week_index']={row['week_index'] for row in read('week')}
dimensions['period_days']={row['period_days'] for row in read('period')}
for name,cols in [('goals',['cohort','plan','period_days']),('retention',['cohort','plan','week_index']),('modules',['cohort','plan','module'])]:
    rows=read(name)
    keys=[tuple(row[c] for c in cols) for row in rows]
    assert len(keys)==len(set(keys)),name
    for row in rows:
        assert all(row[c] in dimensions[c] for c in cols)
        assert int(row['eligible_users'])>=10
        for col,value in row.items():
            if col not in cols:
                assert math.isfinite(float(value)) and float(value)>=0,(name,col)
        if name=='goals':assert int(row['goal_users'])<=int(row['study_users'])<=int(row['eligible_users'])
        if name=='retention':assert int(row['study_users'])<=int(row['checkin_users'])<=int(row['eligible_users'])
        if name=='modules':assert int(row['repeat_users'])<=int(row['module_users'])<=int(row['eligible_users'])
audit=json.loads((ROOT/'reports/extended_analysis.json').read_text(encoding='utf-8'))
for summary in read('goal_summary'):
    days=summary['period_days']; rows=[x for x in read('goals') if x['period_days']==days]
    independent=audit['goals'][days]['primary']
    for col in ['eligible_users','goal_users']:
        assert sum(int(x[col]) for x in rows)==int(summary[col])==independent[col]
for item in audit['module_first30']:
    rows=[x for x in read('modules') if x['module']==item['module']]
    for col in ['eligible_users','module_users','repeat_users','module_days']:
        assert sum(int(x[col]) for x in rows)==item[col],(item['module'],col)
    assert math.isclose(sum(float(x['module_hours']) for x in rows),item['module_hours'],rel_tol=1e-10)
result={'public_csv_keys_relationships_counts':'passed','sql_exports_vs_independent_pandas_goals_modules':'passed'}
(ROOT/'reports/public_export_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
