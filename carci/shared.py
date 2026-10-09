from __future__ import annotations

from typing import Iterable, List, Optional, Tuple

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


FEATURE_COLUMNS = [
    "cost",
    "usage_quantity",
    "autoscaling_count",
    "data_transfer_gb",
    "cost_per_usage",
    "transfer_per_cost",
    # Day-level spend context. The SRS asks for detection of unusual changes in
    # *daily* spending, but every other feature is row-local, leaving the model
    # blind to whether a row sits on a quiet day or a spike day.
    "daily_z",
]

# Column names searched when deriving daily context, in priority order.
DATE_COLUMN_CANDIDATES = ["date", "billing_date", "usage_date", "usage_start_date"]

COLUMN_ALIASES = {
    "cost_usd": "cost",
    "label": "is_anomaly",
    "autoscaling-count": "autoscaling_count",
    "data-transfer-gb": "data_transfer_gb",
}

OPTIONAL_NUMERIC_COLUMNS = [
    "autoscaling_count",
    "data_transfer_gb",
]

REQUIRED_COLUMNS = [
    "cost",
    "usage_quantity",
    "is_anomaly",
]


def normalize_dataset_columns(df: pd.DataFrame, require_labels: bool = True) -> pd.DataFrame:
    df = df.copy()

    for source_column, target_column in COLUMN_ALIASES.items():
        if target_column not in df.columns and source_column in df.columns:
            df[target_column] = df[source_column]

    if "usage_quantity" not in df.columns:
        df["usage_quantity"] = 0
    if "is_anomaly" not in df.columns:
        df["is_anomaly"] = 0

    for column in OPTIONAL_NUMERIC_COLUMNS:
        if column not in df.columns:
            df[column] = 0

    required_columns = list(REQUIRED_COLUMNS)
    if not require_labels:
        required_columns.remove("is_anomaly")

    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        available_columns = ", ".join(df.columns)
        missing_text = ", ".join(missing_columns)
        raise ValueError(
            f"Missing required column(s): {missing_text}. "
            f"Available columns: {available_columns}"
        )

    numeric_columns = ["cost", "usage_quantity", "is_anomaly"] + OPTIONAL_NUMERIC_COLUMNS
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    return df


def _find_date_column(df: pd.DataFrame) -> Optional[str]:
    for candidate in DATE_COLUMN_CANDIDATES:
        if candidate in df.columns:
            return candidate
    for column in df.columns:
        if "date" in str(column).lower():
            return column
    return None


def add_daily_context(df: pd.DataFrame) -> pd.DataFrame:
    """Add `daily_z`: how unusual this row's calendar day is by total spend.

    Every row on a given day shares the value, so it tells the model whether a
    line item sits on a quiet day or a spike day. Degrades to 0.0 when the file
    has no usable date column or only a single day, per SRS section 4.
    """
    df = df.copy()
    date_column = _find_date_column(df)
    if date_column is None:
        df["daily_z"] = 0.0
        return df

    parsed = pd.to_datetime(df[date_column], errors="coerce")
    if parsed.notna().sum() == 0:
        df["daily_z"] = 0.0
        return df

    daily_totals = df.assign(_day=parsed).groupby("_day", dropna=True)["cost"].sum()
    spread = float(daily_totals.std(ddof=0))
    if len(daily_totals) < 2 or spread == 0:
        df["daily_z"] = 0.0
        return df

    centre = float(daily_totals.mean())
    z_by_day = (daily_totals - centre) / spread
    df["daily_z"] = parsed.map(z_by_day).astype(float).fillna(0.0).to_numpy()
    return df


def add_engineered_features(df: pd.DataFrame, require_labels: bool = True) -> pd.DataFrame:
    df = normalize_dataset_columns(df, require_labels=require_labels)

    df["cost_per_usage"] = df["cost"] / (df["usage_quantity"] + 1)
    df["transfer_per_cost"] = df["data_transfer_gb"] / (df["cost"] + 1)
    df = add_daily_context(df)

    return df


def prepare_features(df: pd.DataFrame):
    df = add_engineered_features(df)

    x = df[FEATURE_COLUMNS]
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x)

    return x_scaled


def prepare_train_test_features(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42,
):
    df = add_engineered_features(df)

    normal_df = df[df["is_anomaly"] == 0]
    anomaly_df = df[df["is_anomaly"] == 1]

    normal_train_df, normal_test_df = train_test_split(
        normal_df,
        test_size=test_size,
        random_state=random_state,
        shuffle=True,
    )

    train_df = normal_train_df.reset_index(drop=True)
    test_df = pd.concat([normal_test_df, anomaly_df], ignore_index=True)
    test_df = test_df.sample(frac=1, random_state=random_state).reset_index(drop=True)

    scaler = StandardScaler()
    x_train = scaler.fit_transform(train_df[FEATURE_COLUMNS])
    x_test = scaler.transform(test_df[FEATURE_COLUMNS])
    y_test = test_df["is_anomaly"]

    return x_train, x_test, y_test, train_df, test_df


def prepare_external_test_features(train_source_df: pd.DataFrame, test_source_df: pd.DataFrame):
    train_source_df = add_engineered_features(train_source_df)
    test_df = add_engineered_features(test_source_df)

    train_df = train_source_df[train_source_df["is_anomaly"] == 0].reset_index(drop=True)
    test_df = test_df.reset_index(drop=True)

    scaler = StandardScaler()
    x_train = scaler.fit_transform(train_df[FEATURE_COLUMNS])
    x_test = scaler.transform(test_df[FEATURE_COLUMNS])
    y_test = test_df["is_anomaly"]

    return x_train, x_test, y_test, train_df, test_df


def prepare_inference_features(
    train_df: pd.DataFrame,
    score_df: Optional[pd.DataFrame] = None,
    normal_labels: Iterable[int] = (0,),
) -> Tuple[object, object, pd.DataFrame, pd.DataFrame]:
    train_features = add_engineered_features(train_df, require_labels=False)
    score_features = add_engineered_features(score_df if score_df is not None else train_df, require_labels=False)

    if "is_anomaly" in train_features.columns:
        normal_train_df = train_features[train_features["is_anomaly"].isin(list(normal_labels))]
        if len(normal_train_df) >= 2:
            train_features = normal_train_df

    scaler = StandardScaler()
    x_train = scaler.fit_transform(train_features[FEATURE_COLUMNS])
    x_score = scaler.transform(score_features[FEATURE_COLUMNS])

    return x_train, x_score, train_features, score_features


def print_split_summary(train_df: pd.DataFrame, test_df: pd.DataFrame) -> None:
    test_normal_count = int((test_df["is_anomaly"] == 0).sum())
    test_anomaly_count = int((test_df["is_anomaly"] == 1).sum())

    print("Training:", len(train_df), "normal records only")
    print("Testing: ", len(test_df), "records total")
    print("         ", test_normal_count, "held-out normal records")
    print("         ", test_anomaly_count, "anomaly records")
