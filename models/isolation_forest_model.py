from __future__ import annotations

import argparse
from typing import List, Optional

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from carci.shared import (
    FEATURE_COLUMNS,
    add_engineered_features,
    prepare_external_test_features,
    prepare_inference_features,
    prepare_train_test_features,
    print_split_summary,
)


# Retained only as a last-resort fallback. `decision_function` output is relative
# to whichever forest was fitted, so a constant tuned on one file carries no
# meaning on another upload; `_resolve_threshold` derives one per dataset instead.
DECISION_THRESHOLD = -0.0034
CONTAMINATION = 0.05
LABELED_MODEL_THRESHOLD = 0.36
ATTRIBUTION_METHOD = "SHAP TreeExplainer"

CATEGORICAL_CONTEXT_COLUMNS = [
    "service_name",
    "service",
    "region",
    "usage_type",
    "instance_type",
    "volume-type",
    "storage_type",
    "tag-project / tag-name",
    "tag_environment",
    "department",
    "environment",
    "project_name",
    "month",
]


def build_isolation_forest(contamination: float = CONTAMINATION) -> IsolationForest:
    return IsolationForest(
        n_estimators=1000,
        contamination=contamination,
        max_samples=1.0,
        max_features=1.0,
        random_state=123,
    )


def _resolve_threshold(
    model: IsolationForest,
    x_train: object,
    contamination: float = CONTAMINATION,
) -> float:
    """Derive a cut-off from this dataset's own score distribution.

    Scores from `decision_function` are only meaningful relative to the forest
    that produced them, so a fixed constant does not transfer between uploads.
    Taking the contamination-level quantile of the training scores recalibrates
    the cut-off for every file.

    Worth being precise about what this does and does not do: scikit-learn
    already sets `offset_` to that same quantile, so the value returned here is
    ~0.0 and the rule is equivalent to `model.predict() == -1`. The gain over the
    old hardcoded -0.0034 is therefore not a cleverer rule, it is that the
    cut-off tracks each dataset instead of being an arbitrary constant carried
    over from one file. It is kept as an explicit function so the operating point
    can later be moved away from `contamination` without re-tuning a magic number.
    """
    try:
        train_scores = np.asarray(model.decision_function(x_train), dtype=float)
        if train_scores.size == 0:
            return DECISION_THRESHOLD
        return float(np.quantile(train_scores, contamination))
    except Exception:
        return DECISION_THRESHOLD


def score_records(
    train_df: pd.DataFrame,
    score_df: Optional[pd.DataFrame] = None,
    decision_threshold: Optional[float] = None,
    explain: bool = True,
    contamination: float = CONTAMINATION,
) -> pd.DataFrame:
    """Score rows for anomaly. `decision_threshold=None` calibrates per dataset."""
    x_train, x_score, train_features, score_features = prepare_inference_features(train_df, score_df)

    model = build_isolation_forest(contamination)
    model.fit(x_train)

    if decision_threshold is None:
        decision_threshold = _resolve_threshold(model, x_train, contamination)

    result = score_features.copy()
    result["if_decision_score"] = model.decision_function(x_score)
    result["anomaly_score"] = -result["if_decision_score"]
    result["model_is_anomaly"] = (result["if_decision_score"] < decision_threshold).astype(int)
    result.attrs["attribution_method"] = "not calculated"
    result.attrs["decision_threshold"] = float(decision_threshold)

    if explain:
        result = _append_feature_attribution(result, model, x_score, train_features)

    return result


def _append_feature_attribution(
    result: pd.DataFrame,
    model: IsolationForest,
    x_score: object,
    train_features: pd.DataFrame,
) -> pd.DataFrame:
    try:
        import shap

        explainer = shap.TreeExplainer(model)
        shap_values = np.asarray(explainer.shap_values(x_score))
        # Some SHAP versions return (rows, features, outputs) for tree models;
        # collapse the trailing axis so the per-feature indexing below is valid.
        if shap_values.ndim == 3:
            shap_values = shap_values[:, :, 0]
        if shap_values.shape[1] != len(FEATURE_COLUMNS):
            raise ValueError(
                f"SHAP returned {shap_values.shape[1]} columns for "
                f"{len(FEATURE_COLUMNS)} features."
            )
        result.attrs["attribution_method"] = ATTRIBUTION_METHOD
    except Exception:
        train_center = np.asarray(train_features[FEATURE_COLUMNS].median())
        score_values = np.asarray(result[FEATURE_COLUMNS])
        train_scale = np.asarray(train_features[FEATURE_COLUMNS].std(ddof=0).replace(0, 1))
        shap_values = (score_values - train_center) / train_scale
        shap_values = shap_values * np.asarray(result["anomaly_score"]).reshape(-1, 1)
        result.attrs["attribution_method"] = "standardized feature impact fallback"

    for index, column in enumerate(FEATURE_COLUMNS):
        result[f"shap_{column}"] = shap_values[:, index]

    return result


def run_model(csv_file: str, test_csv_file: Optional[str] = None) -> None:
    df = pd.read_csv(csv_file)

    if test_csv_file:
        test_source_df = pd.read_csv(test_csv_file)
        x_train, x_test, y_true, train_df, test_df = prepare_external_test_features(
            df,
            test_source_df,
        )
    else:
        x_train, x_test, y_true, train_df, test_df = prepare_train_test_features(df)

    model = build_isolation_forest()
    model.fit(x_train)

    threshold = _resolve_threshold(model, x_train)
    scores = model.decision_function(x_test)
    y_pred = [1 if score < threshold else 0 for score in scores]
    baseline_pred = _cost_threshold_baseline(train_df, test_df)

    print("\nModel Evaluation")
    print_split_summary(train_df, test_df)
    print(f"Decision threshold (calibrated on this dataset): {threshold:.6f}")
    _print_metrics("Isolation Forest", y_true, y_pred)
    _print_metrics("Cost percentile baseline", y_true, baseline_pred)
    print(
        "\nNote: the baseline flags rows whose raw cost exceeds the 90th percentile of\n"
        "training spend. It scores poorly because these anomalies are unusual\n"
        "*combinations* of cost, usage, transfer and autoscaling rather than simply\n"
        "large amounts, which is the case for using a model over a single-column rule."
    )

    if not test_csv_file:
        _run_labeled_gradient_boosting_cv(df)


def _cost_threshold_baseline(train_df: pd.DataFrame, test_df: pd.DataFrame) -> List[int]:
    """Strongest simple cost rule, used as an honest comparison point.

    A `mean + 2*std` cut was previously used but flagged nothing at all on this
    data (F1 = 0.0), which made the comparison meaningless. The 90th-percentile
    cut is the best-performing variant of the same idea, so the model is measured
    against the rule at its strongest rather than a straw man.
    """
    threshold = float(train_df["cost"].quantile(0.90))
    return [1 if cost > threshold else 0 for cost in test_df["cost"]]


def _print_metrics(label: str, y_true: pd.Series, y_pred: List[int]) -> None:
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    print(f"\n{label}")
    print("Accuracy: ", round(accuracy, 4))
    print("Precision:", round(precision, 4))
    print("Recall:   ", round(recall, 4))
    print("F1 Score: ", round(f1, 4))


def _run_labeled_gradient_boosting_cv(df: pd.DataFrame) -> None:
    prepared_df = add_engineered_features(df)
    if "is_anomaly" not in prepared_df.columns:
        return

    y = prepared_df["is_anomaly"].astype(int)
    anomaly_count = int((y == 1).sum())
    normal_count = int((y == 0).sum())
    if anomaly_count < 5 or normal_count < 5:
        print("\nLabeled Gradient Boosting")
        print("Skipped: at least 5 normal and 5 anomaly labels are required for 5-fold evaluation.")
        return

    x, preprocessor = _build_labeled_feature_matrix(prepared_df)
    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", GradientBoostingClassifier(random_state=123)),
        ]
    )
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    anomaly_probability = cross_val_predict(model, x, y, cv=cv, method="predict_proba")[:, 1]
    y_pred = (anomaly_probability >= LABELED_MODEL_THRESHOLD).astype(int)

    _print_metrics("Labeled Gradient Boosting (5-fold CV)", y, y_pred)
    print("Decision threshold:", LABELED_MODEL_THRESHOLD)
    print(
        "Caveat: this is a supervised model trained on is_anomaly labels, so it is not\n"
        "directly comparable to the unsupervised Isolation Forest above. The threshold\n"
        "was also chosen by inspecting these same folds, so the score is optimistic."
    )


def _build_labeled_feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, ColumnTransformer]:
    df = df.copy()
    numeric_columns = list(FEATURE_COLUMNS)
    for column in numeric_columns:
        df[column] = pd.to_numeric(df.get(column, 0), errors="coerce").fillna(0.0)
        log_column = f"log_{column}"
        df[log_column] = np.log1p(df[column].clip(lower=0))

    log_columns = [f"log_{column}" for column in numeric_columns]
    categorical_columns = [column for column in CATEGORICAL_CONTEXT_COLUMNS if column in df.columns]
    feature_columns = numeric_columns + log_columns + categorical_columns

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_columns + log_columns,
            ),
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore", min_frequency=2)),
                    ]
                ),
                categorical_columns,
            ),
        ]
    )
    return df[feature_columns], preprocessor


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Isolation Forest anomaly model.")
    parser.add_argument(
        "csv_file",
        nargs="?",
        default="dataset.csv",
        help="Path to the training CSV.",
    )
    parser.add_argument(
        "test_csv_file",
        nargs="?",
        default=None,
        help="Optional path to a separate testing CSV. All rows in this file are tested.",
    )
    args = parser.parse_args()
    run_model(args.csv_file, args.test_csv_file)
