from __future__ import annotations

import pandas as pd

from carci.schema import detect_columns


def preprocess_cur_data(df: pd.DataFrame) -> pd.DataFrame:
    cols = detect_columns(df)

    prepared = pd.DataFrame(
        {
            "date": pd.to_datetime(df[cols.date], errors="coerce").dt.date,
            "service": df[cols.service].fillna("Unknown Service").astype(str),
            "region": (
                df[cols.region].fillna("Unknown Region").astype(str)
                if cols.region
                else "Unknown Region"
            ),
            "resource": (
                df[cols.resource].fillna("Unknown Resource").astype(str)
                if cols.resource
                else "Unknown Resource"
            ),
            "usage_type": (
                df[cols.usage_type].fillna("Unknown Usage Type").astype(str)
                if cols.usage_type
                else "Unknown Usage Type"
            ),
            "tag": (
                df[cols.tag].fillna("Untagged").astype(str)
                if cols.tag
                else "Untagged"
            ),
            "cost": pd.to_numeric(df[cols.cost], errors="coerce").fillna(0.0),
            "usage_quantity": (
                pd.to_numeric(df[cols.usage_quantity], errors="coerce").fillna(0.0)
                if cols.usage_quantity
                else 0.0
            ),
            "autoscaling_count": (
                pd.to_numeric(df[cols.autoscaling_count], errors="coerce").fillna(0.0)
                if cols.autoscaling_count
                else 0.0
            ),
            "data_transfer_gb": (
                pd.to_numeric(df[cols.data_transfer_gb], errors="coerce").fillna(0.0)
                if cols.data_transfer_gb
                else 0.0
            ),
            "is_anomaly": (
                pd.to_numeric(df[cols.is_anomaly], errors="coerce").fillna(0).astype(int)
                if cols.is_anomaly
                else 0
            ),
        }
    )

    prepared = prepared.dropna(subset=["date"]).copy()
    prepared["date"] = pd.to_datetime(prepared["date"])
    prepared = prepared[prepared["cost"] >= 0].copy()

    if prepared.empty:
        raise ValueError("The uploaded CSV does not contain valid date/cost rows after preprocessing.")

    return prepared
