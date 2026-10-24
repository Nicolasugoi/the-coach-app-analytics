-- DuckDB SQL. The runner registers validated pandas frames as raw_users and
-- raw_learning; the latter renames duplicate CSV header check_in_date.1 to
-- check_in_day. Source dates are month/day/year and source durations are HOURS.
-- All individual-level relations below are PRIVATE build artifacts.
-- No statements read or write private paths, and no source values are changed.

CREATE OR REPLACE TABLE users AS
SELECT
    CAST(user_id AS BIGINT) AS user_id,
    CAST(strptime(CAST(install_date AS VARCHAR), '%m/%d/%Y') AS DATE) AS install_date,
    CAST(strptime(CAST(active_at AS VARCHAR), '%m/%d/%Y') AS DATE) AS active_at,
    CAST(strptime(CAST(expire_date AS VARCHAR), '%m/%d/%Y') AS DATE) AS expire_date,
    CAST(os AS VARCHAR) AS os,
    CAST(age AS VARCHAR) AS age,
    CAST(motivation AS VARCHAR) AS motivation,
    CAST(plan AS VARCHAR) AS plan,
    strftime(strptime(CAST(active_at AS VARCHAR), '%m/%d/%Y'), '%Y-%m') AS cohort
FROM raw_users;

SELECT CASE WHEN
    count(*) = 0 OR count(*) <> count(DISTINCT user_id)
    OR count(*) <> count(install_date) OR count(*) <> count(active_at)
    OR count(*) <> count(expire_date)
    THEN error('users must be nonempty with unique nonnull IDs and valid dates')
    ELSE TRUE END AS users_valid
FROM users;

-- Strict casts deliberately reject malformed numbers. Missing source values
-- remain missing here; only absent rows inside an eligible window become zero.
CREATE OR REPLACE TABLE learning_typed AS
SELECT
    CAST(user_id AS BIGINT) AS user_id,
    CAST(strptime(CAST(check_in_date AS VARCHAR), '%m/%d/%Y') AS DATE) AS log_date,
    CAST(total_using_time AS DOUBLE) AS app_hours,
    CAST(gym AS DOUBLE) AS gym,
    CAST(other AS DOUBLE) AS other,
    CAST(communicate_roadmap AS DOUBLE) AS communicate_roadmap,
    CAST(vocabulary_roadmap AS DOUBLE) AS vocabulary_roadmap,
    CAST(onion_gpt AS DOUBLE) AS onion_gpt,
    CAST(total_complete_lesson AS DOUBLE) AS total_complete_lesson,
    CAST(check_in_day AS INTEGER) AS check_in_day,
    CAST(check_in_month AS INTEGER) AS check_in_month,
    CAST(check_in_year AS INTEGER) AS check_in_year
FROM raw_learning;

SELECT CASE WHEN EXISTS (
    SELECT 1 FROM learning_typed
    WHERE user_id IS NULL OR log_date IS NULL
       OR app_hours IS NULL OR gym IS NULL OR other IS NULL
       OR communicate_roadmap IS NULL OR vocabulary_roadmap IS NULL
       OR onion_gpt IS NULL OR total_complete_lesson IS NULL
       OR NOT isfinite(app_hours) OR NOT isfinite(gym) OR NOT isfinite(other)
       OR NOT isfinite(communicate_roadmap) OR NOT isfinite(vocabulary_roadmap)
       OR NOT isfinite(onion_gpt) OR NOT isfinite(total_complete_lesson)
       OR least(app_hours, gym, other, communicate_roadmap, vocabulary_roadmap,
                onion_gpt, total_complete_lesson) < 0
    ) THEN error('learning contains null, nonfinite, or negative numeric values')
    ELSE TRUE END AS learning_values_valid;

SELECT CASE WHEN
    (SELECT count(*) FROM learning_typed) = 0
    OR EXISTS (SELECT user_id, log_date FROM learning_typed
               GROUP BY user_id, log_date HAVING count(*) > 1)
    OR EXISTS (SELECT 1 FROM learning_typed l
               LEFT JOIN users u USING (user_id) WHERE u.user_id IS NULL)
    THEN error('learning must be nonempty, unique by user/date, with known users')
    ELSE TRUE END AS learning_keys_valid;

CREATE OR REPLACE TABLE parameters AS
SELECT min(log_date) AS observation_start, max(log_date) AS cutoff,
       0.000001::DOUBLE AS module_tolerance_hours,
       8.0::DOUBLE AS extreme_threshold_hours
FROM learning_typed;

-- Study is the sum of all FIVE counters, including other. This is a recorded
-- time proxy; counters may overlap. A check-in is simply an observed daily row,
-- not an inferred login event or a reconstructed session.
CREATE OR REPLACE TABLE daily AS
WITH measured AS (
    SELECT l.*, u.install_date, u.active_at, u.expire_date,
           u.os, u.age, u.motivation, u.plan, u.cohort,
           date_diff('day', u.active_at, l.log_date)::INTEGER AS day_index,
           l.gym + l.other + l.communicate_roadmap
                 + l.vocabulary_roadmap + l.onion_gpt AS study_hours
    FROM learning_typed l JOIN users u USING (user_id)
)
SELECT m.*,
       floor(day_index / 7.0)::INTEGER AS week_index,
       study_hours > 0 AS study_active,
       TRUE AS checkin_active,
       study_hours - app_hours > p.module_tolerance_hours AS module_over_total,
       study_hours > p.extreme_threshold_hours
           OR app_hours > p.extreme_threshold_hours AS extreme_day,
       log_date < active_at AS pre_active,
       log_date > expire_date AS post_expiry,
       log_date < install_date AS before_install,
       total_complete_lesson > 0 AND study_hours = 0 AS lesson_positive_zero_study,
       check_in_day IS DISTINCT FROM day(log_date)
           OR check_in_month IS DISTINCT FROM month(log_date)
           OR check_in_year IS DISTINCT FROM year(log_date) AS redundant_date_mismatch
FROM measured m CROSS JOIN parameters p;

CREATE OR REPLACE TABLE period_catalog AS
SELECT * FROM (VALUES (30, 20.0), (120, 100.0), (150, 100.0))
    AS t(period_days, target_hours);

CREATE OR REPLACE TABLE module_catalog AS
SELECT * FROM (VALUES ('gym'), ('other'), ('communicate_roadmap'),
                     ('vocabulary_roadmap'), ('onion_gpt')) AS t(module);

-- Eligibility requires the WHOLE inclusive window to be inside the source's
-- observed calendar range. 30 days is day 0..29; 120/150 operationalize 4/5
-- months, not calendar-month arithmetic. Expiry does not censor because repeat
-- purchase history is unavailable. Raw flagged rows remain in primary results.
CREATE OR REPLACE TABLE user_windows AS
WITH eligible AS (
    SELECT u.*, c.period_days, c.target_hours::DOUBLE AS target_hours,
           u.active_at AS window_start,
           u.active_at + c.period_days - 1 AS window_end
    FROM users u CROSS JOIN period_catalog c CROSS JOIN parameters p
    WHERE u.active_at >= p.observation_start
      AND u.active_at + c.period_days - 1 <= p.cutoff
), measured AS (
    SELECT e.user_id, e.cohort, e.plan, e.os, e.age, e.motivation, e.active_at,
           e.period_days, e.target_hours, e.window_start, e.window_end,
           coalesce(sum(d.study_hours), 0.0)::DOUBLE AS study_hours,
           coalesce(sum(d.app_hours), 0.0)::DOUBLE AS app_hours,
           count(d.user_id) FILTER (WHERE d.study_active)::BIGINT AS study_days,
           count(d.user_id)::BIGINT AS checkin_days,
           coalesce(sum(d.total_complete_lesson), 0.0)::DOUBLE AS communication_lessons
    FROM eligible e LEFT JOIN daily d
      ON e.user_id = d.user_id AND d.log_date BETWEEN e.window_start AND e.window_end
    GROUP BY ALL
), study_islands AS (
    SELECT e.user_id, e.period_days,
           date_diff('day', DATE '2000-01-01', d.log_date)
           - row_number() OVER (
               PARTITION BY e.user_id, e.period_days ORDER BY d.log_date
             ) AS island
    FROM eligible e JOIN daily d
      ON e.user_id = d.user_id AND d.log_date BETWEEN e.window_start AND e.window_end
    WHERE d.study_active
), streaks AS (
    SELECT user_id, period_days, island, count(*) AS streak_days
    FROM study_islands GROUP BY user_id, period_days, island
), longest AS (
    SELECT user_id, period_days, max(streak_days)::BIGINT AS longest_study_streak
    FROM streaks GROUP BY user_id, period_days
)
SELECT m.*, study_days > 0 AS study_user, study_hours >= target_hours AS goal_user,
       coalesce(l.longest_study_streak, 0)::BIGINT AS longest_study_streak
FROM measured m LEFT JOIN longest l USING (user_id, period_days);

-- Each week has its own eligible denominator. Later weeks can have fewer
-- eligible users. A missing daily row is zero only under complete tracking.
CREATE OR REPLACE TABLE user_weeks AS
WITH eligible AS (
    SELECT u.*, w.week_index::INTEGER AS week_index,
           u.active_at + (7 * w.week_index)::INTEGER AS window_start,
           u.active_at + (7 * w.week_index + 6)::INTEGER AS window_end
    FROM users u CROSS JOIN range(0, 13) w(week_index) CROSS JOIN parameters p
    WHERE u.active_at + (7 * w.week_index)::INTEGER >= p.observation_start
      AND u.active_at + (7 * w.week_index + 6)::INTEGER <= p.cutoff
), measured AS (
    SELECT e.user_id, e.cohort, e.plan, e.os, e.age, e.motivation, e.active_at,
           e.week_index, e.window_start, e.window_end,
           coalesce(sum(d.study_hours), 0.0)::DOUBLE AS study_hours,
           coalesce(sum(d.app_hours), 0.0)::DOUBLE AS app_hours,
           count(d.user_id) FILTER (WHERE d.study_active)::BIGINT AS study_days,
           count(d.user_id)::BIGINT AS checkin_days
    FROM eligible e LEFT JOIN daily d
      ON e.user_id = d.user_id AND d.log_date BETWEEN e.window_start AND e.window_end
    GROUP BY ALL
)
SELECT *, study_days > 0 AS study_user, checkin_days > 0 AS checkin_user
FROM measured;

-- Every 30-day-eligible user has five rows, including non-users of a module.
-- Repeat means positive recorded module time on at least two distinct days.
CREATE OR REPLACE TABLE module_user30 AS
WITH module_days AS (
    SELECT d.user_id, v.module, d.log_date, v.module_hours
    FROM daily d CROSS JOIN LATERAL (VALUES
        ('gym', d.gym), ('other', d.other),
        ('communicate_roadmap', d.communicate_roadmap),
        ('vocabulary_roadmap', d.vocabulary_roadmap), ('onion_gpt', d.onion_gpt)
    ) AS v(module, module_hours)
    WHERE d.day_index BETWEEN 0 AND 29 AND v.module_hours > 0
), measured AS (
    SELECT u.user_id, u.cohort, u.plan, u.os, u.age, u.motivation, c.module,
           coalesce(sum(m.module_hours), 0.0)::DOUBLE AS module_hours,
           count(m.log_date)::BIGINT AS module_days
    FROM user_windows u CROSS JOIN module_catalog c
    LEFT JOIN module_days m ON u.user_id = m.user_id AND c.module = m.module
    WHERE u.period_days = 30
    GROUP BY ALL
)
SELECT *, module_days > 0 AS module_user, module_days >= 2 AS repeat_user
FROM measured;

-- SQL window examples: lagged observed dates and cumulative recorded learning.
-- Pre-activation rows and users whose activation predates observation_start
-- cannot support an activation-to-date trajectory and are excluded here.
CREATE OR REPLACE TABLE daily_progress AS
SELECT d.user_id, d.cohort, d.plan, d.log_date, d.day_index,
       d.study_hours, d.study_active,
       lag(d.log_date) OVER user_history AS previous_log_date,
       date_diff('day', lag(d.log_date) OVER user_history, d.log_date)
           AS days_since_previous_log,
       sum(d.study_hours) OVER (
           PARTITION BY d.user_id ORDER BY d.log_date
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS cumulative_study_hours,
       sum(CASE WHEN d.study_active THEN 1 ELSE 0 END) OVER (
           PARTITION BY d.user_id ORDER BY d.log_date
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       )::BIGINT AS cumulative_study_days
FROM daily d CROSS JOIN parameters p
WHERE d.day_index >= 0 AND d.log_date <= p.cutoff
  AND d.active_at >= p.observation_start
WINDOW user_history AS (PARTITION BY d.user_id ORDER BY d.log_date);

CREATE OR REPLACE TABLE user_milestones AS
WITH progress AS (
    SELECT user_id,
           min(log_date) FILTER (WHERE study_active) AS first_study_date,
           min(day_index) FILTER (WHERE study_active) AS days_to_first_study,
           min(day_index) FILTER (WHERE cumulative_study_hours >= 20) AS day_reached_20_hours,
           min(day_index) FILTER (WHERE cumulative_study_hours >= 100) AS day_reached_100_hours,
           max(cumulative_study_hours)::DOUBLE AS observed_study_hours
    FROM daily_progress GROUP BY user_id
), islands AS (
    SELECT user_id,
           date_diff('day', DATE '2000-01-01', log_date)
             - row_number() OVER (PARTITION BY user_id ORDER BY log_date) AS island
    FROM daily_progress WHERE study_active
), streaks AS (
    SELECT user_id, island, count(*) AS streak_days FROM islands GROUP BY user_id, island
), longest AS (
    SELECT user_id, max(streak_days)::BIGINT AS longest_study_streak
    FROM streaks GROUP BY user_id
)
SELECT u.user_id, u.cohort, u.plan,
       u.active_at BETWEEN p.observation_start AND p.cutoff AS activation_observable,
       r.first_study_date, r.days_to_first_study, r.day_reached_20_hours, r.day_reached_100_hours,
       CASE WHEN u.active_at BETWEEN p.observation_start AND p.cutoff
            THEN coalesce(r.observed_study_hours, 0.0) END AS observed_study_hours,
       CASE WHEN u.active_at BETWEEN p.observation_start AND p.cutoff
            THEN coalesce(l.longest_study_streak, 0)::BIGINT END AS longest_study_streak
FROM users u CROSS JOIN parameters p
LEFT JOIN progress r ON u.user_id = r.user_id
LEFT JOIN longest l ON u.user_id = l.user_id;

-- Public export contracts. These relations deliberately retain all aggregate
-- cells internally; Python suppresses cells with eligible_users < 10 at export.
-- Rates are derived from SUM(numerator)/SUM(denominator), not averaged rates.
CREATE OR REPLACE TABLE goals_agg AS
SELECT cohort, plan, period_days, target_hours,
       count(*)::BIGINT AS eligible_users,
       count(*) FILTER (WHERE study_user)::BIGINT AS study_users,
       count(*) FILTER (WHERE goal_user)::BIGINT AS goal_users,
       sum(study_hours)::DOUBLE AS study_hours,
       sum(app_hours)::DOUBLE AS app_hours,
       sum(study_days)::BIGINT AS study_days
FROM user_windows GROUP BY cohort, plan, period_days, target_hours;

CREATE OR REPLACE TABLE retention_agg AS
SELECT cohort, plan, week_index,
       count(*)::BIGINT AS eligible_users,
       count(*) FILTER (WHERE checkin_user)::BIGINT AS checkin_users,
       count(*) FILTER (WHERE study_user)::BIGINT AS study_users,
       sum(study_days)::BIGINT AS study_days,
       sum(study_hours)::DOUBLE AS study_hours,
       sum(app_hours)::DOUBLE AS app_hours,
       sum(checkin_days)::BIGINT AS checkin_days
FROM user_weeks GROUP BY cohort, plan, week_index;

CREATE OR REPLACE TABLE modules_agg AS
SELECT cohort, plan, module,
       count(*)::BIGINT AS eligible_users,
       count(*) FILTER (WHERE module_user)::BIGINT AS module_users,
       count(*) FILTER (WHERE repeat_user)::BIGINT AS repeat_users,
       sum(module_hours)::DOUBLE AS module_hours,
       sum(module_days)::BIGINT AS module_days
FROM module_user30 GROUP BY cohort, plan, module;
