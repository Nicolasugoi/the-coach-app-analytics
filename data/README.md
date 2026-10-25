# Data

- `raw/`: source files, `paid_user_data.csv` and `paid_user_learning_data.csv`, containing user profiles and daily learning records.
- `processed/`: aggregate CSVs reproducible using `sql/00_import.sql`, `01_pipeline.sql` and `02_export.sql`. The Power BI report reads these files.

The Python analysis reads `raw/` and saves aggregate findings and charts under `reports/`.

Raw competition data is excluded from the public package and Git tracking. To reproduce the analysis, place authorized copies of the two source CSVs in `raw/`.
