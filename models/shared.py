
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import pandas as pd

FEATURE_COLUMNS = [
    "cost",
    "usage_quantity",
    "autoscaling_count",
    "data_transfer_gb",
    "cost_per_usage",
    "transfer_per_cost",
]

COLUMN_ALIASES = {
    "cost_usd": "cost",
    "label": "is_anomaly",
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


def normalize_dataset_columns(df):
    df = df.copy()

    for source_column, target_column in COLUMN_ALIASES.items():
        if target_column not in df.columns and source_column in df.columns:
            df[target_column] = df[source_column]

    for column in OPTIONAL_NUMERIC_COLUMNS:
        if column not in df.columns:
            df[column] = 0

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        available_columns = ", ".join(df.columns)
        missing_text = ", ".join(missing_columns)
        raise ValueError(
            f"Missing required column(s): {missing_text}. "
            f"Available columns: {available_columns}"
        )

    numeric_columns = REQUIRED_COLUMNS + OPTIONAL_NUMERIC_COLUMNS
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="raise")

    return df


def add_engineered_features(df):
    df = normalize_dataset_columns(df)

    df["cost_per_usage"] = df["cost"] / (df["usage_quantity"] + 1)
    df["transfer_per_cost"] = df["data_transfer_gb"] / (df["cost"] + 1)

    return df


def prepare_features(df):
    df = add_engineered_features(df)

    X = df[FEATURE_COLUMNS]
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    return X_scaled


def prepare_train_test_features(df, test_size=0.2, random_state=42):
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
    X_train = scaler.fit_transform(train_df[FEATURE_COLUMNS])
    X_test = scaler.transform(test_df[FEATURE_COLUMNS])
    y_test = test_df["is_anomaly"]

    return X_train, X_test, y_test, train_df, test_df


def prepare_external_test_features(train_source_df, test_source_df):
    train_source_df = add_engineered_features(train_source_df)
    test_df = add_engineered_features(test_source_df)

    train_df = train_source_df[train_source_df["is_anomaly"] == 0].reset_index(drop=True)
    test_df = test_df.reset_index(drop=True)

    scaler = StandardScaler()
    X_train = scaler.fit_transform(train_df[FEATURE_COLUMNS])
    X_test = scaler.transform(test_df[FEATURE_COLUMNS])
    y_test = test_df["is_anomaly"]

    return X_train, X_test, y_test, train_df, test_df


def print_split_summary(train_df, test_df):
    test_normal_count = int((test_df["is_anomaly"] == 0).sum())
    test_anomaly_count = int((test_df["is_anomaly"] == 1).sum())

    print("Training:", len(train_df), "normal records only")
    print("Testing: ", len(test_df), "records total")
    print("         ", test_normal_count, "held-out normal records")
    print("         ", test_anomaly_count, "anomaly records")
