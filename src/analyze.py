"""Reproduce the private SQL analysis and publish aggregate-only Power BI inputs."""
from pathlib import Path
import argparse
import hashlib
import json
import duckdb
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODULES = ['gym', 'other', 'communicate_roadmap', 'vocabulary_roadmap', 'onion_gpt']

def run(input_dir, output_dir):
    users_path = input_dir / 'paid_user_data.csv'
    learning_path = input_dir / 'paid_user_learning_data.csv'
    users = pd.read_csv(users_path, encoding='cp1258')
    learning = pd.read_csv(learning_path).rename(columns={'check_in_date.1': 'check_in_day'})
    # SQL validates keys, nulls, dates, nonfinite values and negative durations.
    con = duckdb.connect()
    con.register('raw_users', users)
    con.register('raw_learning', learning)
    con.execute((ROOT / 'sql/01_pipeline.sql').read_text(encoding='utf-8'))
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir = ROOT / 'reports'
    report_dir.mkdir(exist_ok=True)
    exports = {}
    for name, table in [('goals', 'goals_agg'), ('retention', 'retention_agg'), ('modules', 'modules_agg')]:
        frame = con.table(table).df()
        public = frame.loc[frame.eligible_users >= 10].sort_values(list(frame.columns[:3]))
        public.to_csv(output_dir / f'{name}.csv', index=False)
        exports[name] = {'rows': len(public), 'omitted_cells': int((frame.eligible_users < 10).sum())}
    for name in ['cohort', 'plan']:
        con.execute(f'SELECT DISTINCT {name} FROM users ORDER BY {name}').df().to_csv(output_dir / f'{name}.csv', index=False)
    pd.DataFrame({'week_index': range(13), 'week_label': [f'W{i:02d}' for i in range(13)]}).to_csv(output_dir / 'week.csv', index=False)
    pd.DataFrame({'period_days': [30,120,150], 'period_label': ['First 30 days','First 120 days','First 150 days'], 'target_hours': [20,100,100]}).to_csv(output_dir / 'period.csv', index=False)
    pd.DataFrame({'module': MODULES, 'module_label': ['Gym','Other learning','Communication roadmap','Vocabulary roadmap','Onion GPT']}).to_csv(output_dir / 'module.csv', index=False)

    # Independent pandas reconciliation: sum raw counters and retain all eligible
    # users, including those without postactivation activity. No SQL-derived sums.
    u = users.copy()
    u['active_at'] = pd.to_datetime(u.active_at, format='%m/%d/%Y')
    l = learning.copy()
    l['log_date'] = pd.to_datetime(l.check_in_date, format='%m/%d/%Y')
    l['study_hours'] = l[MODULES].sum(axis=1, skipna=False)
    joined = l.merge(u[['user_id', 'active_at']], on='user_id', validate='many_to_one')
    joined['day'] = (joined.log_date - joined.active_at).dt.days
    cutoff, start = l.log_date.max(), l.log_date.min()
    summaries = []
    for days, target in [(30,20),(120,100),(150,100)]:
        eligible = u.loc[(u.active_at >= start) & (u.active_at + pd.Timedelta(days=days-1) <= cutoff), 'user_id']
        counts = joined.loc[joined.day.between(0,days-1)].groupby('user_id').study_hours.sum().reindex(eligible, fill_value=0)
        sql = con.execute('SELECT user_id,study_hours FROM user_windows WHERE period_days=? ORDER BY user_id', [days]).df().set_index('user_id')
        np.testing.assert_array_equal(sorted(eligible), sql.index)
        np.testing.assert_allclose(counts.reindex(sql.index), sql.study_hours, rtol=1e-10, atol=1e-8)
        summaries.append({'period_days':days,'target_hours':target,'eligible_users':len(counts),'goal_users':int((counts >= target).sum()),'attainment_pct':float(100*(counts >= target).mean()),'mean_study_hours':float(counts.mean()),'median_study_hours':float(counts.median())})
    pd.DataFrame(summaries).to_csv(output_dir / 'goal_summary.csv', index=False)
    fixed = con.execute('''SELECT week_index,count(*) eligible_users,sum(checkin_user::INT) checkin_users,
      sum(study_user::INT) study_users,sum(study_days) study_days,sum(study_hours) study_hours,
      sum(app_hours) app_hours FROM user_weeks
      WHERE active_at + INTERVAL 90 DAY <= (SELECT cutoff FROM parameters)
      GROUP BY week_index ORDER BY week_index''').df()
    fixed['learning_retention'] = fixed.study_users / fixed.eligible_users
    fixed['days_per_learner'] = fixed.study_days / fixed.study_users
    fixed['minutes_per_study_day'] = fixed.study_hours * 60 / fixed.study_days
    fixed['minutes_per_eligible_day'] = fixed.study_hours * 60 / fixed.eligible_users / 7
    np.testing.assert_allclose(fixed.learning_retention * fixed.days_per_learner * fixed.minutes_per_study_day / 7, fixed.minutes_per_eligible_day)
    fixed.to_csv(output_dir / 'fixed_retention.csv', index=False)
    quality = con.execute('''SELECT count(*) logs,sum(pre_active::INT) pre_activation,
       sum(module_over_total::INT) module_exceeds_app,sum(extreme_day::INT) extreme_days,
       sum(post_expiry::INT) after_expiry,sum(before_install::INT) before_install,
       sum(redundant_date_mismatch::INT) redundant_date_mismatch,
       sum((app_hours>0 AND study_hours=0)::INT) app_without_recorded_study FROM daily''').df().iloc[0].to_dict()
    evidence = {'sources': {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [users_path,learning_path]},
      'users':len(users),'logs':len(learning),'cutoff':str(cutoff.date()),'quality':quality,
      'goals':summaries,'public_exports':exports,'verification':{'pandas_sql_user_window_reconciliation':'passed','weekly_decomposition_identity':'passed'},
      'assumptions':['Recorded study = sum of five module counters; possible overlap remains.', 'Missing logs inside eligible windows treated as inactivity, conditional on complete tracking.', 'Original purchases and renewal history unavailable.']}
    (report_dir / 'analysis_evidence.json').write_text(json.dumps(evidence, indent=2, default=int), encoding='utf-8')
    print(json.dumps({'goals':summaries,'checks':evidence['verification']}, indent=2))
    con.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'data/processed')
    args = parser.parse_args()
    run(args.input_dir, args.output_dir)
