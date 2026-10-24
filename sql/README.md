# DuckDB analysis pipeline

Run `01_pipeline.sql` through the project Python runner after registering two validated data frames as `raw_users` and `raw_learning`. The SQL performs no file access. Original data must remain private.

## Input contract

- `raw_users`: `user_id`, `install_date`, `active_at`, `expire_date`, `os`, `age`, `motivation`, `plan`.
- `raw_learning`: `user_id`, `check_in_date`, `total_using_time`, `gym`, `other`, `communicate_roadmap`, `vocabulary_roadmap`, `onion_gpt`, `total_complete_lesson`, `check_in_day`, `check_in_month`, `check_in_year`. The runner renames pandas' duplicate-header field `check_in_date.1` to `check_in_day`.
- Dates are strings formatted month/day/year. User IDs are integers. Durations are numeric **hours**. `age` is a supplied category, not a derived age. User IDs must be unique in users; learning rows must be unique by user/date and belong to known users.
- Source numeric nulls, malformed numbers, infinity, NaN and negative values are errors. SQL casts strictly and verifies values before aggregation. No source numeric null becomes zero.

## Definitions and boundaries

`active_at` is the earliest Pro activation, not necessarily the current subscription start. Cohort is its year and month. `parameters` contains `observation_start = MIN(log_date)` and `cutoff = MAX(log_date)`, plus a module/app tolerance of `0.000001` hours and an extreme-day threshold of `8` hours.

Recorded study hours are the sum of all five module counters, including `other`. This is a time proxy that may overstate distinct time if counters overlap. Recorded study activity requires that sum to be positive. A check-in means a source daily row exists, including a zero-duration row; it does not establish an actual login or session. Communication lesson counts are diagnostics and do not prove measured duration. A positive lesson count with zero study hours is flagged separately.

The 30-day window includes activation day through day 29; the 120- and 150-day windows include through day 119 and 149, respectively. Targets are 20, 100 and 100 hours. These long windows operationalize four/five months and are not calendar-month arithmetic. Weeks are 0 through 12, each seven days, with a separately computed denominator. A window is eligible only when both endpoints lie inside the observed source range. Therefore no incomplete window is classified as an inactive user or a failed goal.

An eligible user without matching rows is retained with zero observed activity. This interpretation assumes complete tracking across the window; the calendar bounds alone cannot prove tracking completeness. Subscription expiry does not end observation because purchase history is incomplete. Pre-activation activity is excluded from all activation-based metrics. Flagged rows remain in the primary analysis; sensitivity exclusions belong to the Python analysis.

## Relations and interfaces

| Relation | Grain and key fields |
|---|---|
| `users` | One user; source facts, parsed dates and `cohort`. |
| `learning_typed` | One source user/date; strictly typed numeric/date fields. Private staging table. |
| `parameters` | One row: `observation_start`, `cutoff`, `module_tolerance_hours`, `extreme_threshold_hours`. |
| `daily` | One user/date; original module names and lesson count; `log_date`, `day_index`, `week_index`, `study_hours`, `app_hours`, `study_active`, `checkin_active`, user facts and diagnostic flags. |
| `user_windows` | One eligible user/period; `user_id`, `cohort`, `plan`, `os`, `age`, `motivation`, `active_at`, `period_days`, `target_hours`, `window_start`, `window_end`, `study_hours`, `app_hours`, `study_days`, `checkin_days`, `communication_lessons`, `study_user`, `goal_user`, `longest_study_streak`. |
| `user_weeks` | One eligible user/week; same user facts and dates, `week_index`, window bounds, `study_hours`, `app_hours`, `study_days`, `checkin_days`, `study_user`, `checkin_user`. |
| `module_user30` | One 30-day-eligible user/module, including zeros; user segment fields, `module`, `module_hours`, `module_days`, `module_user`, `repeat_user`. Repeat means at least two positive-time days. |
| `daily_progress` | One postactivation source user/date for users with observable activation; `previous_log_date`, `days_since_previous_log`, `cumulative_study_hours`, `cumulative_study_days`, plus user/cohort/plan/date/day/time/activity fields. |
| `user_milestones` | One user; `activation_observable`, `first_study_date`, `days_to_first_study`, `day_reached_20_hours`, `day_reached_100_hours`, `observed_study_hours`, `longest_study_streak`, plus user/cohort/plan. Day indices are zero-based. Milestone dates are null if not reached; time/streak values are null when activation is outside observation bounds. |
| `goals_agg` | `cohort`, `plan`, `period_days`, `target_hours`, `eligible_users`, `study_users`, `goal_users`, `study_hours`, `app_hours`, `study_days`. |
| `retention_agg` | `cohort`, `plan`, `week_index`, `eligible_users`, `checkin_users`, `study_users`, `study_days`, `study_hours`, `app_hours`, `checkin_days`. |
| `modules_agg` | `cohort`, `plan`, `module`, `eligible_users`, `module_users`, `repeat_users`, `module_hours`, `module_days`. |

`daily` flags are `module_over_total` (study sum exceeds app time beyond tolerance), `extreme_day` (study sum or app time exceeds eight hours), `pre_active`, `post_expiry`, `before_install`, `lesson_positive_zero_study` and `redundant_date_mismatch`. Boundaries for expiry/install flags are strict, so the boundary date itself is not flagged.

The SQL demonstrates joins, conditional aggregation, full-window denominator construction, `LAG`, cumulative window sums and row-number islands for consecutive study-day streaks. It never invents sessions or fills a physical calendar with fabricated logs. Longest streak in each user window is restricted to that window; milestone streak spans the observable postactivation period. Variable follow-up means milestones are descriptive, not comparable completion probabilities without further censoring analysis.

Only aggregate exports are public. The Python runner omits public cells with fewer than ten eligible users; SQL keeps them for private reconciliation. Dashboard rates must use summed numerators divided by summed eligible counts. Eligible counts must not be summed across different periods, weeks or modules to imply distinct people.
