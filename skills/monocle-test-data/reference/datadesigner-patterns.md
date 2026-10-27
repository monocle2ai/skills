# DataDesigner patterns

DataDesigner (NVIDIA NeMo) builds **one table per config**: declare columns, it generates
`num_records` rows, filling columns in dependency order. Samplers and expressions call no LLM;
LLM columns call one model per row.

## When to use it

- Many combinations of facts (cities × dates × preferences × styles) with controlled weights.
- Generating world tables (parent table first, then child tables seeded from it).
- Natural wording at scale (one LLM text column) with an LLM judge column to filter bad rows.

For a few dozen cases, plain Python is simpler.

## Skeleton

```python
import data_designer.config as dd
from data_designer.interface import DataDesigner

b = dd.DataDesignerConfigBuilder()
b.add_column(dd.SamplerColumnConfig(name="scenario", sampler_type=dd.SamplerType.CATEGORY,
    params=dd.CategorySamplerParams(values=["a", "b"], weights=[2, 1])))
b.add_column(dd.SamplerColumnConfig(name="origin", sampler_type=dd.SamplerType.CATEGORY,
    params=dd.CategorySamplerParams(values=CITIES)))
b.add_column(dd.SamplerColumnConfig(name="destination", sampler_type=dd.SamplerType.SUBCATEGORY,
    params=dd.SubcategorySamplerParams(category="origin", values={c: [d for d in CITIES if d != c] for c in CITIES})))
b.add_column(dd.SamplerColumnConfig(name="flight_date", sampler_type=dd.SamplerType.DATETIME,
    params=dd.DatetimeSamplerParams(start="2026-11-01", end="2026-12-31", unit="D"), convert_to="%Y-%m-%d"))
b.add_column(dd.SamplerColumnConfig(name="checkin", sampler_type=dd.SamplerType.TIMEDELTA,
    params=dd.TimeDeltaSamplerParams(dt_min=0, dt_max=3, reference_column_name="flight_date", unit="D"),
    convert_to="%Y-%m-%d"))
b.add_column(dd.ExpressionColumnConfig(name="checkin_day", expr="{{ checkin[8:10] | int }}", dtype="int"))

df = DataDesigner(artifact_path="artifacts").create(b, num_records=50, dataset_name="cases").load_dataset()
```

Seeding from existing rows (real world data → one case per sampled row):

```python
b.with_seed_dataset(dd.LocalFileSeedSource(path="world/flights_sample.parquet"))
```

Hugging Face seeds use `dd.HuggingFaceSeedSource`.

## Gotchas (each one cost a failed run)

- **An expression that renders an empty string drops the whole row.** Use `-` for "not
  applicable" and map it back in Python.
- The Jinja is restricted: no `{% set %}`, and many filters (for example `reject`) are not allowed.
  Use `if`/`else` and helper columns.
- Dropped rows are only warnings: always compare the row count with `num_records`.
- Each row is independent. Rules across rows ("the cheapest on this route is full") and across
  tables (foreign keys) belong in Python (planters, integrity checks), not in DataDesigner.
- Samplers draw new values each run unless a seed is fixed; regenerating changes `test_name`s that
  include sampled values — derive `test_name` from stable parts when stability matters.
- The run logs a warning about missing model API keys even when no LLM column is used; ignore it.
- Install the `data-designer` package, e.g. `uv run --with data-designer python generate.py`.
