# Python workflow

Python scripts for data exploration, engagement analysis and visualization using pandas, NumPy and Matplotlib.

| File | Responsibility |
| --- | --- |
| `analyze.py` | Read raw CSVs, validate keys/types/dates, profile quality issues, calculate observation windows, study targets, fixed-cohort retention, module usage, early behavior and sensitivity scenarios |
| `plot_results.py` | Read `reports/extended_analysis.json` and render four narrative figures as PNG and SVG |

```sh
python -m pip install -r requirements.txt
python src/analyze.py --input-dir data/raw
python src/plot_results.py
```

Run from the repository root. `--input-dir` may point to another authorized folder containing the two source filenames. By default the analysis uses this repository's `data/raw` folder.

## Data handling

- Decode the user CSV as Windows-1258 and the learning CSV as UTF-8.
- Parse dates explicitly and reject missing IDs, duplicate user-days, unknown users, missing/nonfinite numeric values and negative counters.
- Retain suspect chronology and duration rows in primary estimates, with separate sensitivity scenarios.
- Include users with no recorded activity in eligible denominators; exclude incomplete observation windows.
- Reconcile subgroup counts, summed module hours, frequency bands and the retention decomposition before exporting.

Run normally without Python's `-O` flag: validation assertions must remain enabled. Assertions stop the analysis rather than silently replacing invalid source values.

## Outputs

- `reports/extended_analysis.json`: aggregate findings, quality audit, distributions, sensitivities and validation results.
- `reports/figures/01_target_attainment.*`
- `reports/figures/02_retention_decomposition.*`
- `reports/figures/03_module_adoption.*`
- `reports/figures/04_early_frequency.*`
