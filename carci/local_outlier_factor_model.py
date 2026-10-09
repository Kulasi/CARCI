
from sklearn.neighbors import LocalOutlierFactor
from sklearn.metrics import precision_score, recall_score, f1_score
from models.shared import (
    prepare_external_test_features,
    prepare_train_test_features,
    print_split_summary,
)
import pandas as pd
import argparse

def run_model(csv_file, test_csv_file=None):
    df = pd.read_csv(csv_file)

    if test_csv_file:
        test_source_df = pd.read_csv(test_csv_file)
        X_train, X_test, y_true, train_df, test_df = prepare_external_test_features(
            df,
            test_source_df,
        )
    else:
        X_train, X_test, y_true, train_df, test_df = prepare_train_test_features(df)

    model = LocalOutlierFactor(
        n_neighbors=20,
        contamination=0.08,
        novelty=True
    )

    model.fit(X_train)

    preds = model.predict(X_test)

    y_pred = [1 if p == -1 else 0 for p in preds]

    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    print("\nLocal Outlier Factor Results")
    print_split_summary(train_df, test_df)
    print("Precision:", round(precision, 4))
    print("Recall:   ", round(recall, 4))
    print("F1 Score: ", round(f1, 4))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Local Outlier Factor anomaly model.")
    parser.add_argument(
        "csv_file",
        nargs="?",
        default="natural_aws_anomaly_dataset.csv",
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
