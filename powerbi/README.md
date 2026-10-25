# Power BI - Paid Learner Engagement

An interactive report exploring paid learners' study targets, retention and module usage. Power Query prepares the aggregate data, a relational model connects the tables, and DAX measures support comparisons by cohort, plan and observation period.

## Files

- [TheCoach.pbix](TheCoach.pbix): the report, including its data model, measures and three dashboard pages.
- [TheCoach_template.pbit](TheCoach_template.pbit): a reusable template containing queries, model definitions, measures and report pages. It requires a local data source when opened.

## Report development

### 1. Import and prepare data with Power Query

Import the aggregate CSVs from `data/processed`. A text parameter named `DataFolder` supplies the folder path. The queries read UTF-8 CSVs, promote headers and assign text, integer and decimal types.

The model uses three fact tables (`Goals`, `Retention`, `Modules`) and five dimensions (`Cohort`, `Plan`, `Period`, `Week`, `Module`). SQL performs the row-level cleaning and observation-window calculations; Power Query handles report ingestion and data types.

### 2. Model relationships

- `Cohort` and `Plan` filter all three fact tables.
- `Period` filters `Goals`.
- `Week` filters `Retention`.
- `Module` filters `Modules`.

The separate dimensions provide consistent slicers while respecting the different grains of the fact tables. People must not be summed across overlapping windows, weeks or modules.

### 3. Calculate metrics with DAX

Measures recompute ratios within the selected filter context rather than average percentages from separate cohorts. Key measures include:

```dax
Eligible learners =
IF (
    HASONEVALUE ( 'Period'[period_days] ),
    SUM ( Goals[eligible_users] )
)

Goal attainment =
DIVIDE ( [Goal achievers], [Eligible learners] )

Mean study hours =
DIVIDE ( [Recorded study hours], [Eligible learners] )

Target hours =
SELECTEDVALUE ( 'Period'[target_hours] )
```

The period guard prevents adding the same users across different target windows. Some measures intentionally return blank when the selection would produce an ambiguous denominator.

### 4. Design the dashboard pages

| Page | Analytical purpose | Report elements |
| --- | --- | --- |
| Goal Attainment | Compare recorded study with the target for each complete observation window | Cohort attainment bars, study/target comparison, KPI cards, denominator table, period/cohort/plan slicers |
| Retention: Showing up vs Learning | Distinguish returning to the app from recorded learning | Weekly lines, eligible-population table, cohort matrix and week/cohort/plan slicers |
| Module adoption and repeat learning | Separate module reach from repeat usage | Adoption/repeat bars, usage-depth table, KPI cards and module/cohort/plan slicers |

Slicers allow comparisons across cohorts and plans. KPI cards highlight the main results, while supporting tables show the counts behind each rate.

## Open and refresh

1. Open the PBIX, or open the PBIT to create a new report.
2. Set `DataFolder` to the absolute path of this repository's `data/processed` folder. For an existing report, use **Transform data → Manage parameters**.
3. Apply changes and refresh using the CSVs in `data/processed`.
4. Select one period on the goals page, then use cohort and plan filters. Inspect the accompanying count table before comparing rates.
