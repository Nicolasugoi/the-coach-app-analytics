-- Optional exploration after 00_import.sql and 01_pipeline.sql.
-- These queries run locally. User-level tables are not public exports.

-- 1. Quantify suspect records; flag rather than arbitrarily overwrite them.
SELECT count(*) AS log_rows,
       count(*) FILTER (WHERE pre_active) AS pre_activation_rows,
       count(*) FILTER (WHERE module_over_total) AS module_exceeds_app_rows,
       count(*) FILTER (WHERE extreme_day) AS over_8_hour_rows,
       count(*) FILTER (WHERE post_expiry) AS post_expiry_rows,
       count(*) FILTER (WHERE before_install) AS before_install_rows,
       count(*) FILTER (WHERE redundant_date_mismatch) AS redundant_date_mismatch_rows,
       count(*) FILTER (WHERE app_hours > 0 AND study_hours = 0) AS app_without_study_rows
FROM daily;
SELECT plan,count(*) AS users_with_date_conflict
FROM users WHERE install_date > active_at OR expire_date < active_at GROUP BY plan;

-- 2. Reach, frequency and duration: do not mistake shorter follow-up for churn.
SELECT week_index,sum(eligible_users) AS eligible_users,
       sum(checkin_users)::DOUBLE / sum(eligible_users) AS checkin_retention,
       sum(study_users)::DOUBLE / sum(eligible_users) AS learning_retention,
       sum(study_days)::DOUBLE / nullif(sum(study_users),0) AS days_per_learner,
       60 * sum(study_hours) / nullif(sum(study_days),0) AS minutes_per_study_day
FROM retention_agg GROUP BY week_index ORDER BY week_index;

-- 3. Module reach and repeat use have different denominators.
SELECT module,sum(eligible_users) AS eligible_users,
       sum(module_users)::DOUBLE / sum(eligible_users) AS adoption_rate,
       sum(repeat_users)::DOUBLE / nullif(sum(module_users),0) AS repeat_among_adopters,
       sum(module_hours) / nullif(sum(module_users),0) AS hours_per_adopter
FROM modules_agg GROUP BY module ORDER BY adoption_rate DESC;

-- 4. Sensitivity: removing flagged days is a lower recorded-hours scenario,
-- not a claim that the remaining values are the true hours. Denominator stays fixed.
WITH sensitivity AS (
    SELECT w.user_id,w.study_hours AS primary_hours,
           coalesce(sum(d.study_hours) FILTER (WHERE NOT d.extreme_day),0) AS without_extreme_hours,
           coalesce(sum(d.study_hours) FILTER (WHERE NOT d.module_over_total),0) AS without_overlap_hours
    FROM user_windows w LEFT JOIN daily d
      ON w.user_id=d.user_id AND d.day_index BETWEEN 0 AND 29
    WHERE w.period_days=30 GROUP BY w.user_id,w.study_hours
)
SELECT count(*) AS eligible_users,
       count(*) FILTER (WHERE primary_hours >= 20) AS primary_achievers,
       count(*) FILTER (WHERE without_extreme_hours >= 20) AS without_extreme_achievers,
       count(*) FILTER (WHERE without_overlap_hours >= 20) AS without_overlap_achievers
FROM sensitivity;

-- 5. Early behavior versus later learning: association, not causation.
WITH eligible AS (
    SELECT u.user_id FROM users u CROSS JOIN parameters p
    WHERE u.active_at >= p.observation_start AND u.active_at + 62 <= p.cutoff
), behavior AS (
    SELECT e.user_id,
           count(*) FILTER (WHERE d.day_index BETWEEN 0 AND 6 AND d.study_active) AS early_days,
           count(*) FILTER (WHERE d.day_index BETWEEN 56 AND 62 AND d.study_active) > 0 AS w8_learning
    FROM eligible e LEFT JOIN daily d USING(user_id) GROUP BY e.user_id
)
SELECT CASE WHEN early_days <= 2 THEN early_days::VARCHAR
            WHEN early_days <= 4 THEN '3-4' ELSE '5-7' END AS early_study_days,
       count(*) AS eligible_users,count(*) FILTER (WHERE w8_learning) AS w8_study_users,
       count(*) FILTER (WHERE w8_learning)::DOUBLE / count(*) AS w8_study_rate
FROM behavior GROUP BY early_study_days ORDER BY early_study_days;
