from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from carci.isolation_forest_model import score_records
from carci.llm_reasoning import MODEL as LLM_MODEL
from carci.llm_reasoning import generate_explanations
from carci.preprocessing import preprocess_cur_data
from carci.shared import FEATURE_COLUMNS


BREAKDOWN_COLUMNS = ["service", "region", "resource", "tag", "usage_type"]

# Upper bound on anomaly cards rendered. The UI reports when this truncates.
MAX_ANOMALIES = 20


def _safe_pct_change(current_value: float, previous_value: float) -> float:
    if previous_value <= 0 and current_value > 0:
        return 100.0
    if previous_value <= 0:
        return 0.0
    return ((current_value - previous_value) / previous_value) * 100.0


def _format_money(value: float) -> str:
    return f"${value:,.2f}"


def _to_breakdown(df: pd.DataFrame, column: str, limit: int = 8) -> List[Dict]:
    if df.empty or column not in df.columns:
        return []

    total_cost = float(df["cost"].sum())
    grouped = (
        df.groupby(column, dropna=False)["cost"]
        .sum()
        .sort_values(ascending=False)
        .head(limit)
        .reset_index()
        .rename(columns={column: "name"})
    )
    grouped["share_pct"] = np.where(total_cost > 0, (grouped["cost"] / total_cost) * 100.0, 0.0)
    grouped["cost"] = grouped["cost"].round(2)
    grouped["share_pct"] = grouped["share_pct"].round(2)
    return grouped.to_dict(orient="records")


def _top_name(breakdowns: Dict[str, List[Dict]], key: str, fallback: str) -> str:
    rows = breakdowns.get(key, [])
    if not rows:
        return fallback
    return str(rows[0]["name"])


def _top_share(breakdowns: Dict[str, List[Dict]], key: str) -> float:
    rows = breakdowns.get(key, [])
    if not rows:
        return 0.0
    return float(rows[0]["share_pct"])


def _build_daily_features(df: pd.DataFrame) -> pd.DataFrame:
    daily = df.groupby("date", as_index=False)["cost"].sum().sort_values("date").reset_index(drop=True)
    daily["previous_cost"] = daily["cost"].shift(1).fillna(0.0)
    daily["pct_change"] = [
        _safe_pct_change(curr, prev) for curr, prev in zip(daily["cost"], daily["previous_cost"])
    ]
    daily["rolling_mean_3"] = daily["cost"].rolling(window=3, min_periods=1).mean()
    daily["rolling_std_3"] = daily["cost"].rolling(window=3, min_periods=1).std(ddof=0).fillna(0.0)
    daily["cost_delta"] = daily["cost"] - daily["previous_cost"]

    mean_cost = float(daily["cost"].mean())
    std_cost = float(daily["cost"].std(ddof=0))
    daily["z_score"] = 0.0 if std_cost == 0 else (daily["cost"] - mean_cost) / std_cost
    return daily


def _score_input_rows(df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    model_input = df.copy().sort_values(["date", "cost"], ascending=[True, False]).reset_index(drop=True)
    if len(model_input) < 2 or model_input["cost"].nunique() <= 1:
        model_input["if_decision_score"] = 0.0
        model_input["anomaly_score"] = 0.0
        model_input["model_is_anomaly"] = 0
        for column in FEATURE_COLUMNS:
            model_input[f"shap_{column}"] = 0.0
        return model_input, "not calculated"

    scored = score_records(model_input)
    attribution_method = scored.attrs.get("attribution_method", "not calculated")

    passthrough_columns = ["date", "service", "region", "resource", "tag", "usage_type"]
    for column in passthrough_columns:
        scored[column] = model_input[column].values

    return scored, attribution_method


def _attach_service_context(scored_df: pd.DataFrame) -> pd.DataFrame:
    """Attach a date-aware baseline to every scored row.

    The baseline answers "what does this service normally cost on a day?" by
    aggregating to the (service, date) level and averaging the service's *other*
    days. The previous row-level leave-one-out mean ignored dates entirely, so a
    service that was uniformly expensive looked anomalous on its priciest row
    even with no change over time.
    """
    scored_df = scored_df.copy()
    scored_df["service_date_cost"] = scored_df.groupby(["service", "date"])["cost"].transform("sum")

    per_day = scored_df.drop_duplicates(subset=["service", "date"])
    day_totals = per_day.groupby("service")["service_date_cost"].agg(["sum", "count"])
    scored_df["service_total_cost"] = scored_df["service"].map(day_totals["sum"])
    scored_df["service_day_count"] = scored_df["service"].map(day_totals["count"])

    scored_df["normal_value"] = np.where(
        scored_df["service_day_count"] > 1,
        (scored_df["service_total_cost"] - scored_df["service_date_cost"])
        / (scored_df["service_day_count"] - 1),
        0.0,
    )
    scored_df["impact_value"] = scored_df["service_date_cost"] - scored_df["normal_value"]
    # A zero baseline means first-ever spend, not a "100% increase".
    scored_df["is_new_spend"] = (scored_df["normal_value"] <= 0) & (scored_df["service_date_cost"] > 0)
    scored_df["percentage"] = [
        _safe_pct_change(curr, prev)
        for curr, prev in zip(scored_df["service_date_cost"], scored_df["normal_value"])
    ]
    scored_df["priority_score"] = (
        scored_df["model_is_anomaly"].astype(float) * 2.0
        + scored_df["anomaly_score"].clip(lower=0)
        + scored_df["impact_value"].clip(lower=0) / max(float(scored_df["service_date_cost"].max()), 1.0)
    )
    return scored_df

def _candidate_anomaly_rows(scored_df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Select anomalous service-days and the row that drove each one.

    Returns the capped candidates plus the pre-cap count so the caller can tell
    the user when the list was truncated.
    """
    has_baseline = scored_df["service_day_count"] >= 2
    model_flagged = scored_df["model_is_anomaly"] == 1
    large_change = (scored_df["percentage"] >= 75.0) & (scored_df["impact_value"] >= 5.0)
    candidates = scored_df[has_baseline & (model_flagged | large_change) & (scored_df["impact_value"] > 0)].copy()
    candidates["is_fallback"] = 0

    if candidates.empty and not scored_df.empty:
        top_row = scored_df[has_baseline].sort_values(
            ["impact_value", "anomaly_score", "cost"],
            ascending=[False, False, False],
        ).head(1).copy()
        top_row["is_fallback"] = 1
        candidates = top_row

    # One card per service-day, keeping the highest-scoring row as the driver.
    # Without this, several rows of the same service and date produced duplicate
    # cards carrying identical breakdowns.
    candidates = candidates.sort_values(
        ["anomaly_score", "cost"], ascending=[False, False]
    ).drop_duplicates(subset=["service", "date"], keep="first")

    total_found = int(len(candidates))
    candidates = candidates.sort_values(
        ["priority_score", "impact_value", "cost"],
        ascending=[False, False, False],
    ).head(MAX_ANOMALIES)
    return candidates, total_found


def _get_feature_contributions(row: pd.Series) -> Tuple[List[Dict], List[str]]:
    feature_rows = []
    for column in FEATURE_COLUMNS:
        shap_value = float(row.get(f"shap_{column}", 0.0))
        feature_rows.append(
            {
                "feature": column,
                "feature_value": round(float(row.get(column, 0.0)), 4),
                "shap_value": round(shap_value, 4),
                "impact_strength": round(abs(shap_value), 4),
            }
        )

    feature_rows.sort(key=lambda item: item["impact_strength"], reverse=True)
    top_features = [item["feature"] for item in feature_rows[:3] if item["impact_strength"] > 0]
    return feature_rows, top_features


def _recommendation_for(record: Dict) -> str:
    usage_type = record["usage_type"].lower()
    if "datatransfer" in usage_type or "bandwidth" in usage_type:
        return "Review outbound data transfer, cross-region traffic, and CDN or caching options."
    if "boxusage" in usage_type or "instance" in usage_type or "compute" in usage_type:
        return "Review instance size, running hours, scaling activity, and idle compute resources."
    if "storage" in usage_type or "volume" in usage_type or "glacier" in usage_type:
        return "Review storage tier, lifecycle policies, and unexpected retained data volume."
    if "request" in usage_type:
        return "Review request volume, retry behavior, and application traffic sources."
    return "Review the listed service, resource, tag, and usage type before increasing the budget."


def _headline_for(record: Dict) -> str:
    """A one-line summary for the card header.

    The template can only describe the symptom, because naming a cause is exactly
    the judgement it cannot make. The LLM replaces this with a suspected cause.
    """
    if record["is_new_spend"]:
        return f"New {record['usage_type']} spend on {record['service_name']}"
    return (
        f"{record['service_name']} {record['usage_type']} up "
        f"{record['percentage']:.0f}% in {record['region']}"
    )


def _severity_for(record: Dict) -> str:
    """Rank an anomaly by money at stake, then by how sharp the rise was.

    Computed from the pipeline's own figures so that a severity exists even with
    the LLM switched off. When the model runs it may override this with its own
    reading, which also weighs the usage type and the feature pattern.
    """
    if record["is_fallback"]:
        # Nothing crossed the threshold; this row is context, not an incident.
        return "low"
    impact = record["impact_value"]
    percentage = record["percentage"]
    if impact >= 1000 or (impact >= 250 and percentage >= 500):
        return "critical"
    if impact >= 250 or (impact >= 50 and percentage >= 200):
        return "high"
    if impact >= 50:
        return "medium"
    return "low"


def _build_root_cause_text(record: Dict) -> str:
    if record["is_fallback"]:
        flag_text = (
            "No row crossed the anomaly threshold, so this service-day is shown only because it "
            "carries the largest positive cost impact. Treat it as informational, not as a detection."
        )
    elif record["model_flag"]:
        flag_text = "The Isolation Forest model flagged the driving line item as anomalous."
    else:
        flag_text = (
            "The model did not flag this service-day, but the cost increase exceeded the "
            "review thresholds (75% above baseline and at least $5 of impact)."
        )

    if record["is_new_spend"]:
        comparison_text = (
            f"The observed cost was {_format_money(record['anomaly_value'])}. This service has no prior "
            f"spending day in the uploaded file, so no baseline comparison is possible and this is "
            f"treated as new spend."
        )
    else:
        comparison_text = (
            f"The observed cost was {_format_money(record['anomaly_value'])}, compared with a normal daily "
            f"baseline of {_format_money(record['normal_value'])} for this service. This is an increase of "
            f"approximately {record['percentage']:.0f}%."
        )

    top_features = ", ".join(record["top_ml_features"]) if record["top_ml_features"] else "cost behavior"
    return (
        f"A cost anomaly was detected for {record['service_name']} on {record['display_date']}.\n\n"
        f"{comparison_text}\n\n"
        f"The main region was {record['region']} ({record['region_share_pct']:.0f}% of this service/date cost). "
        f"The main resource was {record['resource']}, with usage type {record['usage_type']} and tag {record['tag']}.\n\n"
        f"{flag_text} {record['attribution_method']} identified the strongest feature impacts from {top_features}.\n\n"
        f"Recommended action: {record['recommendation']}"
    )


def _build_anomaly_record(row: pd.Series, df: pd.DataFrame, attribution_method: str) -> Dict:
    date_value = pd.Timestamp(row["date"])
    same_service_date = df[(df["date"] == row["date"]) & (df["service"] == row["service"])]
    same_date = df[df["date"] == row["date"]]
    breakdowns = {
        "service": _to_breakdown(same_date, "service"),
        "region": _to_breakdown(same_service_date, "region"),
        "resource": _to_breakdown(same_service_date, "resource"),
        "tag": _to_breakdown(same_service_date, "tag"),
        "usage_type": _to_breakdown(same_service_date, "usage_type"),
    }
    feature_contributions, top_features = _get_feature_contributions(row)

    record = {
        "service_name": str(row["service"]),
        "date": date_value.strftime("%Y-%m-%d"),
        "display_date": date_value.strftime("%d %B %Y"),
        "region": _top_name(breakdowns, "region", str(row["region"])),
        "resource": _top_name(breakdowns, "resource", str(row["resource"])),
        "tag": _top_name(breakdowns, "tag", str(row["tag"])),
        "usage_type": _top_name(breakdowns, "usage_type", str(row["usage_type"])),
        # Day-level totals for the service, with the driving line item's cost kept
        # alongside so the card shows both the "what" and the "which row".
        "anomaly_value": round(float(row["service_date_cost"]), 2),
        "driver_row_cost": round(float(row["cost"]), 2),
        "normal_value": round(float(row["normal_value"]), 2),
        "percentage": round(float(row["percentage"]), 2),
        "impact_value": round(float(row["impact_value"]), 2),
        "model_anomaly_score": round(float(row.get("anomaly_score", 0.0)), 6),
        "model_decision_score": round(float(row.get("if_decision_score", 0.0)), 6),
        "model_flag": int(row.get("model_is_anomaly", 0)),
        "is_fallback": int(row.get("is_fallback", 0)),
        "is_new_spend": bool(row.get("is_new_spend", False)),
        "region_share_pct": _top_share(breakdowns, "region"),
        "resource_share_pct": _top_share(breakdowns, "resource"),
        "tag_share_pct": _top_share(breakdowns, "tag"),
        "usage_type_share_pct": _top_share(breakdowns, "usage_type"),
        "breakdowns": breakdowns,
        "feature_contributions": feature_contributions,
        "top_ml_features": top_features,
        "attribution_method": attribution_method,
    }
    record["recommendation"] = _recommendation_for(record)
    record["severity"] = _severity_for(record)
    record["headline"] = _headline_for(record)
    record["root_cause_analysis"] = _build_root_cause_text(record)
    return record


def _build_service_comparison(
    scored_df: pd.DataFrame, prepared_df: pd.DataFrame, attribution_method: str
) -> Tuple[List[Dict], int]:
    candidates, total_found = _candidate_anomaly_rows(scored_df)
    records = [_build_anomaly_record(row, prepared_df, attribution_method) for _, row in candidates.iterrows()]
    ordered = sorted(
        records,
        key=lambda item: (item["model_flag"], item["impact_value"], item["anomaly_value"]),
        reverse=True,
    )
    _apply_llm_explanations(ordered)
    return ordered, total_found


def _apply_llm_explanations(records: List[Dict]) -> None:
    """Replace the template narrative with the LLM's full investigation.

    The LLM is the primary explanation source. It supplies the narrative, the
    headline, the severity, the ranked cause hypotheses and the investigation
    steps; the last two have no template equivalent and stay empty without it.

    Every record still keeps `template_explanation`, `template_recommendation`
    and `template_headline`, so the deterministic text is never lost and the two
    can be compared. `explanation_method` records which one the card is actually
    showing. When the layer is off or the API call fails, nothing changes beyond
    those bookkeeping fields, so the analysis never depends on the network.
    """
    for record in records:
        record["template_explanation"] = record["root_cause_analysis"]
        record["template_recommendation"] = record["recommendation"]
        record["template_headline"] = record["headline"]
        record["explanation_method"] = "deterministic template"
        # Hypotheses and investigation steps have no template equivalent: naming a
        # probable cause is a judgement no keyword rule can make. In template mode
        # these stay empty and the UI simply omits those sections.
        record["likely_causes"] = []
        record["investigation_steps"] = []

    generated = generate_explanations(records)
    if not generated:
        return

    for index, item in generated.items():
        if not 0 <= index < len(records):
            continue
        records[index]["root_cause_analysis"] = item["explanation"]
        records[index]["explanation_method"] = f"LLM ({LLM_MODEL})"
        records[index]["likely_causes"] = item["likely_causes"]
        records[index]["investigation_steps"] = item["investigation_steps"]
        # Each remaining field falls back to the pipeline's own value, so a reply
        # that omits one is degraded rather than blank.
        if item.get("recommended_action"):
            records[index]["recommendation"] = item["recommended_action"]
        if item.get("headline"):
            records[index]["headline"] = item["headline"]
        if item.get("severity"):
            records[index]["severity"] = item["severity"]


def _build_daily_summary(df: pd.DataFrame, anomaly_records: List[Dict]) -> List[Dict]:
    daily = _build_daily_features(df)
    anomaly_dates = {record["date"] for record in anomaly_records}
    daily["has_anomaly"] = daily["date"].dt.strftime("%Y-%m-%d").isin(anomaly_dates)
    daily["date"] = daily["date"].dt.strftime("%Y-%m-%d")
    numeric_columns = ["cost", "previous_cost", "pct_change", "rolling_mean_3", "cost_delta", "z_score"]
    daily[numeric_columns] = daily[numeric_columns].round(4)
    return daily.to_dict(orient="records")


def _build_report_text(result: Dict) -> str:
    lines = [
        "CARCI Cost Anomaly Root Cause Report",
        "",
        f"Rows analyzed: {result['metadata']['row_count']}",
        f"Date range: {result['metadata']['date_range']}",
        f"Total cost: {_format_money(result['metadata']['total_cost'])}",
        f"Detected anomalies: {result['metadata']['anomaly_count']}",
        f"Attribution method: {result['metadata']['attribution_method']}",
        "",
    ]

    if result["metadata"]["truncated"]:
        lines.append(
            f"Note: {result['metadata']['total_found']} service-days qualified; "
            f"the {result['metadata']['shown_count']} highest-priority are listed below."
        )
        lines.append("")

    if not result["service_comparison"]:
        lines.append("No strong anomalies were detected in the uploaded file.")
        return "\n".join(lines)

    if result["metadata"]["anomaly_count"] == 0:
        lines.append(
            "No service-day crossed the anomaly threshold. The entry below is the "
            "highest-impact service-day, shown for reference only."
        )
        lines.append("")

    for index, record in enumerate(result["service_comparison"], start=1):
        increase = (
            "new spend (no prior baseline)"
            if record["is_new_spend"]
            else f"{record['percentage']:.0f}%"
        )
        lines.extend(
            [
                f"{index}. [{record['severity'].upper()}] {record['service_name']} - {record['date']}"
                + ("  [reference only]" if record["is_fallback"] else ""),
                f"   {record['headline']}",
                "",
                f"   Cost: {_format_money(record['anomaly_value'])}",
                f"   Normal baseline: {_format_money(record['normal_value'])}",
                f"   Increase: {increase}",
                f"   Region: {record['region']}",
                f"   Resource: {record['resource']}",
                f"   Tag: {record['tag']}",
                f"   Usage type: {record['usage_type']}",
                f"   Top ML features: {', '.join(record['top_ml_features']) or 'cost behavior'}",
            ]
        )

        if record["likely_causes"]:
            lines.append("   Likely causes:")
            for rank, cause in enumerate(record["likely_causes"], start=1):
                lines.append(f"     {rank}. [{cause['confidence']}] {cause['cause']}")
                lines.append(f"        Evidence: {cause['evidence']}")

        if record["investigation_steps"]:
            lines.append("   Investigation steps:")
            for step_number, step in enumerate(record["investigation_steps"], start=1):
                lines.append(f"     {step_number}. {step}")

        lines.extend([f"   Recommendation: {record['recommendation']}", ""])
    return "\n".join(lines)


def build_analysis_result(raw_df: pd.DataFrame) -> Dict:
    prepared_df = preprocess_cur_data(raw_df)
    scored_df, attribution_method = _score_input_rows(prepared_df)
    scored_df = _attach_service_context(scored_df)

    service_comparison, total_found = _build_service_comparison(
        scored_df, prepared_df, attribution_method
    )
    # A fallback row is a "nothing crossed the threshold" placeholder, not a detection.
    confirmed_count = sum(1 for record in service_comparison if not record["is_fallback"])
    date_min = prepared_df["date"].min().strftime("%Y-%m-%d")
    date_max = prepared_df["date"].max().strftime("%Y-%m-%d")
    result = {
        "metadata": {
            "row_count": int(len(prepared_df)),
            "service_count": int(prepared_df["service"].nunique()),
            "anomaly_count": confirmed_count,
            "shown_count": int(len(service_comparison)),
            "total_found": total_found,
            "truncated": bool(total_found > len(service_comparison)),
            "total_cost": round(float(prepared_df["cost"].sum()), 2),
            "date_range": f"{date_min} to {date_max}",
            "attribution_method": attribution_method,
            "explanation_method": (
                service_comparison[0]["explanation_method"]
                if service_comparison
                else "deterministic template"
            ),
        },
        "daily_summary": _build_daily_summary(prepared_df, service_comparison),
        "overall_breakdowns": {column: _to_breakdown(prepared_df, column) for column in BREAKDOWN_COLUMNS},
        "service_comparison": service_comparison,
        "service_root_causes": [
            {
                "service_name": row["service_name"],
                "root_cause_analysis": row["root_cause_analysis"],
            }
            for row in service_comparison
        ],
    }
    result["report_text"] = _build_report_text(result)
    return result
