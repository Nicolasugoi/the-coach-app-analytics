-- Run after 01_pipeline.sql in the same session, from the repository root.
-- data/processed must exist. Only aggregate tables are exported.
COPY (SELECT * FROM goals_agg WHERE eligible_users >= 10 ORDER BY cohort,plan,period_days)
TO 'data/processed/goals.csv' (HEADER, DELIMITER ',');
COPY (SELECT * FROM retention_agg WHERE eligible_users >= 10 ORDER BY cohort,plan,week_index)
TO 'data/processed/retention.csv' (HEADER, DELIMITER ',');
COPY (SELECT * FROM modules_agg WHERE eligible_users >= 10 ORDER BY cohort,plan,module)
TO 'data/processed/modules.csv' (HEADER, DELIMITER ',');
COPY (SELECT DISTINCT cohort FROM users ORDER BY cohort)
TO 'data/processed/cohort.csv' (HEADER, DELIMITER ',');
COPY (SELECT DISTINCT plan FROM users ORDER BY plan)
TO 'data/processed/plan.csv' (HEADER, DELIMITER ',');
COPY (SELECT range AS week_index, 'W' || lpad(range::VARCHAR,2,'0') AS week_label FROM range(13))
TO 'data/processed/week.csv' (HEADER, DELIMITER ',');
COPY (SELECT period_days, 'First ' || period_days || ' days' AS period_label, target_hours FROM period_catalog)
TO 'data/processed/period.csv' (HEADER, DELIMITER ',');
COPY (SELECT * FROM (VALUES
    ('gym','Gym'), ('other','Other learning'),
    ('communicate_roadmap','Communication roadmap'),
    ('vocabulary_roadmap','Vocabulary roadmap'), ('onion_gpt','Onion GPT')
) AS t(module,module_label))
TO 'data/processed/module.csv' (HEADER, DELIMITER ',');

COPY (
    SELECT period_days,target_hours,count(*) AS eligible_users,
           count(*) FILTER (WHERE goal_user) AS goal_users,
           100.0 * count(*) FILTER (WHERE goal_user) / count(*) AS attainment_pct,
           avg(study_hours) AS mean_study_hours,median(study_hours) AS median_study_hours
    FROM user_windows GROUP BY period_days,target_hours ORDER BY period_days
) TO 'data/processed/goal_summary.csv' (HEADER, DELIMITER ',');

COPY (
    WITH totals AS (
        SELECT week_index,count(*) AS eligible_users,
               count(*) FILTER (WHERE checkin_user) AS checkin_users,
               count(*) FILTER (WHERE study_user) AS study_users,
               sum(study_days) AS study_days,sum(study_hours) AS study_hours,sum(app_hours) AS app_hours
        FROM user_weeks WHERE active_at + INTERVAL 90 DAY <= (SELECT cutoff FROM parameters)
        GROUP BY week_index
    )
    SELECT *,study_users::DOUBLE / eligible_users AS learning_retention,
           study_days::DOUBLE / nullif(study_users,0) AS days_per_learner,
           study_hours * 60 / nullif(study_days,0) AS minutes_per_study_day,
           study_hours * 60 / eligible_users / 7 AS minutes_per_eligible_day
    FROM totals ORDER BY week_index
) TO 'data/processed/fixed_retention.csv' (HEADER, DELIMITER ',');

-- Report how many small aggregate cells were omitted.
SELECT 'goals' AS dataset,count(*) FILTER (WHERE eligible_users < 10) AS omitted_cells FROM goals_agg
UNION ALL SELECT 'retention',count(*) FILTER (WHERE eligible_users < 10) FROM retention_agg
UNION ALL SELECT 'modules',count(*) FILTER (WHERE eligible_users < 10) FROM modules_agg;
