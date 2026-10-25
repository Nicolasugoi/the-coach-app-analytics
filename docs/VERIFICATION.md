# Verification - independent workflow release

Verified on 25 October 2026.

## SQL

- Executed all four SQL files against the original CSVs using DuckDB 2.0.0. SQL performed CSV import and Windows-1258 decoding directly; no DataFrame registration supplied the source tables.
- Compared every exported CSV with the previous validated outputs: all **10 files** matched in columns, rows and values, within floating-point tolerance of `rtol=1e-10`, `atol=1e-8`.
- Checked Windows-1258 text decoding against the established source decoding.
- Passed four fixture tests covering complete-window boundaries and inactive users, duplicate user-days, missing/negative values, and unknown user IDs.
- The development check invoked the DuckDB engine through its API. The shipped SQL has no Python dependency; a separate DuckDB CLI execution was not performed in this environment.

## Python

- Ran `analyze.py` and `plot_results.py` in an isolated folder containing only those scripts and the two raw CSVs. No SQL files, processed CSVs or Power BI assets were present.
- Compared the full analysis JSON with the previous analysis: all structures and findings matched within the same numeric tolerance.
- Generated four PNG and four SVG figures from Python's own analysis JSON.
- Input assertions and analytical reconciliation checks passed.

## Power BI

- Preserved PBIX and PBIT byte-for-byte from the author's supplied files.
- Confirmed both containers contain the three expected report pages.
- Inspected the template: eight model tables, nine relationships and 35 measures; the queries read aggregate CSVs using `DataFolder`.
- No interactive Desktop check was repeated for this release. The author previously confirmed successful data loading and page display. Local refresh still requires the user's own folder path.

## Repository boundaries

Only analytical Python files are included under `src`. No report generator, Python SQL runner, packaging helpers or obsolete generated-project audits are included. The former `tests` folder used Python to run SQL fixtures; it is not shipped because the requested deliverable keeps the branches separate. Necessary source validations remain in SQL and Python, and the fixture checks above were run during development.

The local working folder retains the supplied raw sources. The public ZIP excludes their contents and includes `.gitignore`. The PBIX/PBIT contain the supplied aggregate report; they were not rebuilt or changed during restructuring.
