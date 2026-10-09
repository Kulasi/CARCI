# CARCI

CARCI (Cost Anomaly Root Cause Intelligence) is a lightweight Streamlit application for:

- uploading AWS CUR-style CSV files,
- validating and auto-detecting core billing columns,
- detecting unusual daily cost spikes,
- analyzing service, region, resource, tag, and usage-type contributors,
- explaining feature impact with SHAP-based attribution when available,
- writing the root-cause explanation and recommended action with an LLM,
- visualizing anomaly trends and factor breakdowns,
- generating downloadable text and CSV reports.

Anomaly detection uses the Isolation Forest model in `carci/isolation_forest_model.py`.
Root-cause wording comes from Google Gemini via `carci/llm_reasoning.py`.

The dashboard is a three-step wizard: **Upload CSV**, **Anomaly Summary**, and
**Investigation Details**. Analysis moves to the summary page automatically when it
finishes, and navigating back to the upload page does not discard the results.

## Dataset

`dataset.csv` is the bundled training and testing data, and is what every number in
the Evaluation section below is measured on.

| Property | Value |
| --- | --- |
| Rows | 10,000 |
| Labels | 9,000 normal / 1,000 anomaly (10.0%) |
| Period | 2025-11-01 to 2026-05-25 (206 days) |
| Services | 8 |
| Regions | 5 |
| Cost range | $0.88 min, $24.28 median, $1,011.65 max |

Columns: `billing_date, service_name, region, resource_id, usage_type, cost,
usage_quantity, autoscaling_count, data_transfer_gb, department, environment,
project_name, is_anomaly`.

One caution about this file: **`usage_type` encodes the label exactly.** All four of
`NormalUsage`, `BurstUsage`, `BackupWindow` and `BatchJob` are 100% normal, and all
seven of `SuspiciousSpike`, `CryptoMiningTraffic`, `RunawayJob`, `MassiveDataTransfer`,
`UnauthorizedScaling`, `SubtleCostDrift` and `MisconfiguredTagging` are 100% anomaly,
with no overlap. Any model given that column scores a perfect 1.0 by reading the answer
rather than detecting anything. The Isolation Forest is unaffected because it uses only
the seven numeric features above, but see the Gradient Boosting caveat in Evaluation.

## ML features

| Feature | Meaning |
| --- | --- |
| `cost` | Line-item cost |
| `usage_quantity` | Billed usage amount |
| `autoscaling_count` | Scaling activity |
| `data_transfer_gb` | Network transfer |
| `cost_per_usage` | Unit-price proxy, `cost / (usage_quantity + 1)` |
| `transfer_per_cost` | Transfer efficiency, `data_transfer_gb / (cost + 1)` |
| `daily_z` | How unusual the row's calendar day is by total spend |

`daily_z` is shared by every row on a given day. Without it the model is entirely
row-local and cannot tell whether a line item sat on a quiet day or a spike day,
even though daily spike detection is the stated goal. It degrades to `0.0` when the
file has no usable date column or covers only one day.

Whether it pays off depends on the shape of the data, and on `dataset.csv` it does not —
see the ablation in Evaluation. It earns its place when anomalies cluster onto a few
days; it dilutes the other six features when they are spread thinly across many.

## How an anomaly is defined

Detection runs at the **service-day** level:

1. Every row is scored by Isolation Forest.
2. Rows are aggregated to `(service, date)`. The baseline for a service-day is the
   mean of that service's **other days**, so a service that is uniformly expensive
   is not flagged simply for having a costly row.
3. A service-day is reported when the model flagged its driving line item, **or**
   the cost rose at least 75% above baseline with at least $5 of impact.
4. One card is produced per service-day, keeping the highest-scoring row as the driver.

If nothing qualifies, the highest-impact service-day is shown marked
**"Reference only"** and is excluded from the detected-anomaly count.

## Root cause explanation

Each detected service-day gets a written explanation and a recommended action. Both are
produced by **Google Gemini (`gemini-3.5-flash-lite`)**, called over the REST API in
`carci/llm_reasoning.py`. The previous keyword-rule recommendation and the template
paragraph are no longer what the user reads; they survive only as an offline fallback.

The division of labour is the part that matters:

| Produced by the pipeline | Produced by the model |
| --- | --- |
| Every number: observed cost, baseline, increase %, impact, region share, driver row cost | The wording of the paragraph |
| Which service-day is an anomaly, and why it qualified | Which of those facts to foreground |
| The SHAP feature ranking | The recommended action for this specific anomaly |

One request carries up to 20 anomalies as a JSON array. The reply is constrained with
`responseMimeType: application/json` and an explicit `responseSchema`, so it is parsed
rather than scraped. The system prompt forbids calculating, rounding or inventing any
figure, and no rule-based suggestion is sent in the payload, so the returned action is
the model's own reading of the facts rather than a rewrite of a keyword match.

### Configuration

Put the key in a `.env` file at the project root (already git-ignored):

```
GEMINI_API_KEY=your-key-here
CARCI_LLM_REASONING=1
```

`GOOGLE_API_KEY` and a real environment variable both work too. The layer is **on by
default whenever a key is present**; set `CARCI_LLM_REASONING=0` to force the
deterministic template.

### What happens when it is unavailable

No key, no network, an API error, a safety block, or an unparseable reply all produce
the same outcome: the record keeps its template paragraph and rule-based recommendation,
and `metadata["explanation_method"]` reports `deterministic template` instead of
`LLM (gemini-3.5-flash-lite)`. The analysis itself never fails, because no number in the
report depends on the model. Every record also retains `template_explanation` and
`template_recommendation`, so the two can be compared side by side.

The Streamlit page states which engine wrote the text above the anomaly list.

## Decision threshold

The cut-off is recalibrated for every uploaded file from that dataset's own score
distribution. `decision_function` values are meaningful only relative to the forest
that produced them, so the previously hardcoded `-0.0034` carried no meaning on a
different upload. `DECISION_THRESHOLD` survives only as a fallback if calibration fails.

To be precise about what this buys: it is a **portability** fix, not an accuracy one. On
`dataset.csv` the calibrated cut-off lands at 0.000000 and scores within ±0.001 F1 of the
old constant (see the ablation in Evaluation). The point is that the cut-off now tracks
whatever file is uploaded instead of being a constant tuned on a file that is no longer
here.

## Run locally

1. Install dependencies:

```powershell
pip install -r requirements.txt
```

2. Add your Gemini key so the root-cause explanations are LLM-written. Create `.env` in
   the project root:

```
GEMINI_API_KEY=your-key-here
CARCI_LLM_REASONING=1
```

   Skip this step and the app still runs; explanations fall back to the template.

3. Start the app:

```powershell
streamlit run app.py
```

4. Optional: run the model evaluation directly:

```powershell
python -m carci.isolation_forest_model dataset.csv
```

   This path never calls SHAP or the LLM, so it is fast.

5. Run the tests:

```powershell
python -m pytest tests/
```

Note: `tests/` is currently empty, so this collects nothing until test files are added.

## Evaluation

Measured on the bundled `dataset.csv` (10,000 rows, 1,000 labelled anomalies, 206 days).
Training uses normal rows only (7,200 rows); the test set is the 1,800 held-out normals
plus all 1,000 anomalies. Reproduce with:

```powershell
python -m carci.isolation_forest_model dataset.csv
```

| Model | Accuracy | Precision | Recall | F1 |
| --- | --- | --- | --- | --- |
| **Isolation Forest** | **0.845** | **0.877** | **0.657** | **0.751** |
| Cost percentile baseline | 0.708 | 0.665 | 0.367 | 0.473 |
| Labeled Gradient Boosting (5-fold CV) | 1.000 | 1.000 | 1.000 | 1.000 |

Averaged over 10 random splits rather than the single default split, the Isolation Forest
scores F1 **0.748 ± 0.004**, so the headline number is not a lucky split.

### Ablation: does `daily_z` help?

Not on this dataset. Averaging F1 over the same 10 splits for each combination:

| Features | Fixed `-0.0034` | Calibrated |
| --- | --- | --- |
| 6 features (no `daily_z`) | 0.759 | **0.760** |
| 7 features (with `daily_z`) | 0.748 | 0.748 |

Two things follow, and the second one is inconvenient:

- **Threshold calibration is score-neutral here** (±0.001, inside the ±0.004 spread). That
  is expected: scikit-learn's `offset_` is already the contamination quantile, so the
  calibrated rule is equivalent to `model.predict() == -1`. Its value is portability, not
  accuracy — the old constant was tuned on a different file and carried no meaning here.
- **`daily_z` costs about 0.012 F1 on this dataset.** It helped on the earlier 303-row,
  28-day file, where anomalies clustered onto a few days so daily totals were informative.
  `dataset.csv` spreads 1,000 anomalies across 206 days, so daily totals barely move and
  the feature mostly dilutes the six row-local ones. It is retained because the SRS asks
  for detection of unusual changes in *daily* spend and the other features are all
  row-local, but on data shaped like this it is a small net cost, not a gain.

Four caveats worth stating plainly:

- The **Gradient Boosting 1.000 is not a real result.** It is label leakage: `usage_type`
  is in `CATEGORICAL_CONTEXT_COLUMNS`, and in this dataset that column maps one-to-one
  onto `is_anomaly` (see Dataset above), so the classifier reads the answer instead of
  detecting anything. It is left in the table only as a worked example of why a perfect
  score should be treated as a bug report. The Isolation Forest is unaffected — it never
  sees `usage_type`, only the seven numeric features.
- The **cost percentile baseline** scores far below the model because these anomalies are
  unusual *combinations* of cost, usage, transfer and autoscaling rather than simply large
  amounts. That is the argument for using a model over a single-column rule. An earlier
  `mean + 2*std` rule scored 0.0, so the percentile version is used to avoid comparing
  against a straw man.
- The test set contains **all** anomalies plus only 20% of normals, a 36% anomaly rate
  against the file's true 10%, which inflates precision for every row in the table.
- The model is fitted and scored on the same file. Use the two-argument form
  (`python -m carci.isolation_forest_model train.csv test.csv`) for a clean split where
  the forest never sees the test data.

## Known limitations

- The explanation layer calls an external API. That adds roughly 5-10 seconds per
  analysis, sends anomaly facts (service, region, resource id, tags, costs) to Google,
  and depends on the key remaining valid. Resource ids and tag names are the sensitive
  part of that payload; raw billing rows are never sent. Set `CARCI_LLM_REASONING=0` if
  the data may not leave the environment.
- The model is instructed not to compute or invent figures, and the payload contains only
  pre-computed values, but nothing in the code verifies the returned prose against those
  values. A stricter version would re-check every number that appears in the text.
- The model is fitted on the same upload it scores. This is standard for unsupervised
  detection with no separate training corpus, but it means the scaler and the forest both
  see the anomalies they are looking for.
- `contamination` is 0.05, so roughly 5% of rows are flagged regardless of how clean the
  file is. A genuinely clean upload will still produce flags. The 75% / $5 business rule
  in the analysis layer is what keeps the reported list short. Note that 5% is a rate over
  the *training* rows, not over the scored file: on `dataset.csv` the app flags 1,107 of
  10,000 rows (11%), which decomposes as 450 false positives (5% of the 9,000 normal rows
  used for training) plus the 657 anomalies genuinely caught at 0.657 recall.
- Isolation Forest uses 1000 trees over all samples, and SHAP explains every scored row.
  This is the binding cost. Measured on the bundled 10,000-row `dataset.csv`:
  preprocessing is instant and scoring takes about 5 seconds, but SHAP attribution takes
  roughly **28 minutes** (~170 ms per row), so it is about 99% of total runtime. Per-row
  SHAP cost also grows with the training set, because `max_samples=1.0` makes the trees
  deeper on larger files: it rises from ~26 ms/row when fitted on 500 rows to ~170 ms/row
  when fitted on 10,000. The CLI evaluation is unaffected, as it does not run SHAP. Only
  the Streamlit app pays this, and it will appear to hang for the duration. Explaining
  just the rows actually displayed, rather than all scored rows, is the obvious fix.

## Expected logical columns

The app matches common AWS CUR column names to these logical fields, requiring
`date`, `service`, and `cost`:

- `date`, `service`, `region`, `resource`, `usage_type`, `cost`

Also used when present:

- `usage_quantity`, `autoscaling_count` (or `autoscaling-count`), `data_transfer_gb`,
  `is_anomaly`, and tag columns such as `tag_environment`, `tag-project / tag-name`,
  `project_name`, or `environment`

CUR-style aliases such as `line_item_usage_start_date`, `line_item_resource_id`, and
`line_item_unblended_cost` are recognised. Missing optional columns produce a partial
explanation rather than an error.

## Output style

With the LLM layer active, an explanation reads like this (real output, produced from the
first 150 rows of `data set/test_2_obvious_anomalies.csv`):

> On 05 January 2026, AmazonRDS in the us-west-2 region experienced a cost anomaly flagged
> by the model. The observed cost reached 1488.53 USD compared to a baseline cost of
> 687.92 USD, resulting in an impact of 800.61 USD or a 116.38 percent increase. The
> specific driver line item cost was 241.33 USD under the NormalUsage usage type for
> resource db-175a715d-744c-4ec9-9ff0-288d340e0a3c, which is tagged as InternalTools and
> accounts for 22.65 percent of the region share. The top features driving the anomaly
> score are autoscaling count, cost, and cost per usage.
>
> **Recommended action:** Review the autoscaling count and cost per usage metrics for
> database resource db-175a715d-744c-4ec9-9ff0-288d340e0a3c in us-west-2 to determine if
> scaling limits can be tightened for InternalTools.

Every figure in that paragraph was computed by the pipeline and handed to the model as
JSON. Compare it with the fallback template for the same anomaly, which is what appears
when no key is configured:

> A cost anomaly was detected for AmazonRDS on 05 January 2026.
>
> The observed cost was $1,488.53, compared with a normal daily baseline of $687.92 for
> this service. This is an increase of approximately 116%.
>
> Recommended action: Review the listed service, resource, tag, and usage type before
> increasing the budget.

The difference is the point of the LLM layer: the template's action is one of five
keyword branches and fits any anomaly, while the model's names the actual resource,
region and metric to check.

The dashboard also includes summary metrics, a daily cost trend chart with anomaly days
highlighted, an anomaly impact chart, overall breakdown tables, per-anomaly root-cause
expanders, SHAP feature attribution tables, and three downloadable exports.
