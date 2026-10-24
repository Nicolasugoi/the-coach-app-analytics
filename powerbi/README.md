# Open and verify The Coach report

The editable project contains three PBIR report pages, eight imported tables, nine relationships and 35 DAX measures. `build_report.py` regenerates these definitions; it does not execute DAX or embed source records.

1. Generate aggregate CSVs using the project Python runner.
2. In Power BI Desktop with PBIP/PBIR support, open `TheCoach.pbip`.
3. Open Transform data → Manage parameters. Set `DataFolder` to the full local path of the project's `data/processed` directory. Close and apply, then refresh.
4. On the Goals page, select First 30 days. With no cohort/plan filter, verify 12,851 eligible learners, 702 achievers, 5.46% attainment and 6.63 mean study hours.
5. Select a cohort and plan. Check that all visuals on the page respond and that counts agree with the corresponding rows of goals.csv.
6. On Retention, verify weeks are ordered W00–W12. Each week has its own eligible population; do not compare its cards to the separate fixed-cohort Python chart without matching the denominator.
7. On Modules, verify Onion adoption 93.74% and repeat among adopters 89.12% with no filters. Module-selection changes module charts; top cards intentionally summarize all learning.
8. Confirm no clipped text, unexpected blanks, errors or broken interactions on all three pages. Capture screenshots only after this native check.

Goals measures return blank across multiple selected periods to prevent duplicate-person totals. Module totals and cross-week totals are guarded for the same reason. Select a single period to populate goals cards.

## Verification status

- 51 report/project JSON documents validated against official Microsoft schemas.
- Visual field bindings and model relationship bindings checked.
- model.bim successfully deserialized using Microsoft.AnalysisServices.Tabular 19.94.1.1; eight tables were read.
- The author confirmed successful Desktop opening and data loading after configuring DataFolder on 24 October 2026.
- The author confirmed that all three rendered pages display normally after Close & Apply. Individual DAX measures have not been independently queried.

Python figures elsewhere in the repository are not Power BI screenshots. The original competition PBIX was inspected locally and contains 21 pages and an embedded data model; it is not redistributed.

References: [Power BI projects](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview), [report folder and PBIR](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report), [Microsoft schemas](https://github.com/microsoft/json-schemas).
