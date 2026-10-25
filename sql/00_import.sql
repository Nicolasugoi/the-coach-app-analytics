-- Run from the repository root, in the same DuckDB session as 01 and 02.
-- The user source is Windows-1258, NOT UTF-8. This extension handles decoding
-- inside SQL. INSTALL is needed once; LOAD is needed for each new session.
INSTALL encodings;
LOAD encodings;

CREATE OR REPLACE TABLE raw_users AS
SELECT * FROM read_csv('data/raw/paid_user_data.csv',
    header = true, all_varchar = true, encoding = 'windows-1258');

-- Explicit column names resolve the repeated check_in_date header by position.
-- The first is the full date; the second is a redundant day-of-month field.
CREATE OR REPLACE TABLE raw_learning AS
SELECT * FROM read_csv('data/raw/paid_user_learning_data.csv',
    header = true, all_varchar = true,
    names = ['user_id', 'check_in_date', 'total_using_time', 'gym', 'other',
             'communicate_roadmap', 'vocabulary_roadmap', 'onion_gpt',
             'total_complete_lesson', 'check_in_day', 'check_in_month', 'check_in_year']);

-- Quick source profiling before the typed validation in 01_pipeline.sql.
SELECT 'users' AS source, count(*) AS rows, count(DISTINCT user_id) AS distinct_users FROM raw_users
UNION ALL
SELECT 'learning', count(*), count(DISTINCT user_id) FROM raw_learning;
