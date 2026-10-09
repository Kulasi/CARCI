from __future__ import annotations

import pandas as pd


def build_report_text(result: dict) -> str:
    if "report_text" in result:
        return result["report_text"]

    lines = ["CARCI Cost Anomaly Root Cause Report", ""]
    for record in result.get("service_comparison", []):
        lines.extend(
            [
                f"{record['service_name']} - {record['date']}",
                f"Cost: {record['anomaly_value']}",
                f"Normal baseline: {record['normal_value']}",
                f"Impact: {record['impact_value']}",
                f"Region: {record['region']}",
                f"Resource: {record['resource']}",
                f"Tag: {record.get('tag', 'Untagged')}",
                f"Usage type: {record['usage_type']}",
                f"Recommendation: {record.get('recommendation', 'Review the contributing factors.')}",
                "",
            ]
        )
    return "\n".join(lines)


def build_report_dataframe(result: dict) -> pd.DataFrame:
    rows = []
    metadata = result.get("metadata", {})
    for key, value in metadata.items():
        rows.append({"section": "metadata", "metric": key, "value": value})

    for record in result.get("service_comparison", []):
        rows.extend(
            [
                {"section": record["service_name"], "metric": "date", "value": record["date"]},
                {"section": record["service_name"], "metric": "anomaly_cost", "value": record["anomaly_value"]},
                {"section": record["service_name"], "metric": "normal_cost", "value": record["normal_value"]},
                {"section": record["service_name"], "metric": "impact", "value": record["impact_value"]},
                {"section": record["service_name"], "metric": "increase_pct", "value": record["percentage"]},
                {"section": record["service_name"], "metric": "region", "value": record["region"]},
                {"section": record["service_name"], "metric": "resource", "value": record["resource"]},
                {"section": record["service_name"], "metric": "tag", "value": record.get("tag", "Untagged")},
                {"section": record["service_name"], "metric": "usage_type", "value": record["usage_type"]},
                {
                    "section": record["service_name"],
                    "metric": "top_ml_features",
                    "value": ", ".join(record.get("top_ml_features", [])),
                },
            ]
        )

        rows.extend(
            [
                {"section": record["service_name"], "metric": "severity",
                 "value": record.get("severity", "")},
                {"section": record["service_name"], "metric": "headline",
                 "value": record.get("headline", "")},
            ]
        )

        # Ranked, so the row name carries the rank and the export stays sortable.
        for rank, cause in enumerate(record.get("likely_causes", []), start=1):
            rows.append(
                {
                    "section": record["service_name"],
                    "metric": f"likely_cause_{rank}",
                    "value": (
                        f"[{cause.get('confidence', '')}] {cause.get('cause', '')} "
                        f"| evidence: {cause.get('evidence', '')}"
                    ),
                }
            )

        for step_number, step in enumerate(record.get("investigation_steps", []), start=1):
            rows.append(
                {
                    "section": record["service_name"],
                    "metric": f"investigation_step_{step_number}",
                    "value": step,
                }
            )

        for contribution in record.get("feature_contributions", [])[:5]:
            rows.append(
                {
                    "section": record["service_name"],
                    "metric": f"feature_contribution_{contribution['feature']}",
                    "value": (
                        f"value={contribution['feature_value']}, "
                        f"shap={contribution['shap_value']}"
                    ),
                }
            )

    return pd.DataFrame(rows)
