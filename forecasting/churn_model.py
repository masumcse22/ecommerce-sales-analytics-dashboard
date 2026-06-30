"""
forecasting/churn_model.py
Churn prediction model adapted for Olist's customer_features table.

Olist note: most customers buy only once (Olist is a marketplace).
The model therefore predicts "will NOT return" risk, which is meaningful
for seller/category level retention analysis.

Features used: recency_days, frequency, monetary, aov, tenure_days,
               state_enc, rfm_score
Output: data/processed/churn_predictions.csv
"""
import pandas as pd
import numpy as np
from pathlib import Path
from loguru import logger
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_PROCESSED

FEATURE_COLS = [
    "recency_days", "frequency", "monetary", "aov",
    "tenure_days", "rfm_score", "state_enc",
]


def encode_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Encode Brazilian state
    states = sorted(df["state"].dropna().unique().tolist()) if "state" in df.columns else []
    state_map = {s: i for i, s in enumerate(states)}
    df["state_enc"] = df.get("state", pd.Series([""] * len(df))).map(state_map).fillna(0).astype(int)

    # Fill numeric NAs with median
    for col in ["recency_days", "frequency", "monetary", "aov", "tenure_days", "rfm_score"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].fillna(df[col].median())

    return df


def train_churn_model(customer_features: pd.DataFrame):
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import roc_auc_score, classification_report
    from sklearn.preprocessing import StandardScaler

    df = encode_features(customer_features)

    # Need is_churned label
    if "is_churned" not in df.columns:
        raise ValueError("customer_features must contain 'is_churned' column")

    df["is_churned"] = df["is_churned"].astype(str).str.lower().map(
        {"true": 1, "false": 0, "1": 1, "0": 0}
    ).fillna(0).astype(int)

    available = [c for c in FEATURE_COLS if c in df.columns]
    X = df[available]
    y = df["is_churned"]

    logger.info(f"Training churn model | {len(df):,} customers | "
                f"churn rate={y.mean()*100:.1f}% | features={available}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = GradientBoostingClassifier(
        n_estimators=200, learning_rate=0.05,
        max_depth=4, min_samples_leaf=10, random_state=42,
    )
    model.fit(X_train, y_train)

    y_pred  = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    auc     = roc_auc_score(y_test, y_proba)

    logger.success(f"Churn model AUC = {auc:.4f}")
    logger.info("\n" + classification_report(y_test, y_pred, zero_division=0))

    importance = pd.DataFrame({
        "feature":    available,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)
    logger.info(f"Feature importances:\n{importance.to_string(index=False)}")

    return model, available


def predict_churn(
    customer_features: pd.DataFrame,
    model,
    feature_cols: list[str],
) -> pd.DataFrame:
    df = encode_features(customer_features)
    available = [c for c in feature_cols if c in df.columns]
    proba = model.predict_proba(df[available])[:, 1]

    df["churn_probability"] = proba.round(4)
    df["churn_risk"] = pd.cut(
        proba, bins=[0, 0.35, 0.65, 1.0],
        labels=["Low", "Medium", "High"]
    ).astype(str)

    keep_cols = [
        "customer_unique_id", "churn_probability", "churn_risk", "is_churned",
        "recency_days", "frequency", "monetary", "aov", "rfm_score", "rfm_segment", "state",
    ]
    keep_cols = [c for c in keep_cols if c in df.columns]
    result = df[keep_cols].copy()

    # Decode is_churned back to bool string for readability
    result["is_churned"] = result["is_churned"].astype(str).map(
        {"1": "True", "0": "False", "True": "True", "False": "False"}
    )

    out = DATA_PROCESSED / "churn_predictions.csv"
    result.to_csv(out, index=False)
    logger.success(f"Churn predictions → {out}  ({len(result):,} customers)")
    return result


def run_churn_pipeline() -> pd.DataFrame:
    path = DATA_PROCESSED / "customer_features.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Run ETL first (python main.py --mode etl). Missing: {path}"
        )
    logger.info(f"Loading customer features from {path}")
    customer_features = pd.read_csv(path)
    model, feature_cols = train_churn_model(customer_features)
    return predict_churn(customer_features, model, feature_cols)


if __name__ == "__main__":
    run_churn_pipeline()
