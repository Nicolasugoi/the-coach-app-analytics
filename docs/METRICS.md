# Metric dictionary

| Metric | Numerator / calculation | Denominator / scope |
| --- | --- | --- |
| Recorded study hours | Sum of gym, other, communicate_roadmap, vocabulary_roadmap, onion_gpt | Eligible observation window; hours |
| App hours | total_using_time | Includes non-learning screens |
| Goal attainment | Users with study hours ≥20 or ≥100 | All users with complete 30 / 120 / 150-day window |
| Check-in retention | Users with at least one source daily record in week | Users whose full week is observable |
| Learning retention | Users with positive summed module time in week | Same weekly eligible population |
| Study frequency | Positive-study user-days | Users with positive study time in that week |
| Study-day duration | Total study hours × 60 | Positive-study user-days |
| Mean daily study across cohort | Total study hours × 60 | Eligible users × 7 for a complete week |
| Module adoption | Users with positive module time on ≥1 day | All 30-day-eligible users |
| Repeat among adopters | Users with module time on ≥2 distinct days | Module adopters in the same 30-day window |
| Week 8 participation | Users with study time on days 56–62 | Users observable through day 62; grouped by days 0–6 behavior |

Activation day is day 0. Windows are inclusive: day 0–29, day 0–119, day 0–149. Week index w covers days 7w through 7w+6. These are elapsed calendar dates; the sources do not contain timestamps for rolling 24-hour windows.

`age` contains onboarding categories and is not a continuous age measure. `motivation` is self-reported; retain Other. `total_complete_lesson` counts communication lessons, not all app lessons. `active_at` is the earliest Pro activation across purchases. `expire_date` alone cannot reconstruct subscription history.

Source `communicate_roadmap` corresponds to the supplied dictionary's `communication_roadmap`. The second `check_in_date` column is a day component; pandas names it `check_in_date.1`, and the runner renames it `check_in_day`. Redundant date parts are checked separately.

Ratios use sums of counts rather than averages of percentages. People are not additive across weeks, modules or observation windows. Median hours must be recomputed from individual values; do not average subgroup medians. The public model intentionally omits subgroup medians.

Complete date coverage is an eligibility condition, not proof of complete tracking. A zero after a left join means no observed activity under the tracking assumption. Numeric source nulls never become zeros. Study hours are recorded module counters and may overlap; they are not a validated measure of active attention or language proficiency.
