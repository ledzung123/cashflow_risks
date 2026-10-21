"""Huấn luyện baseline và mô hình phân loại thiếu tiền theo chu kỳ."""

import itertools
import json
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.inspection import permutation_importance

from config import DATA_DIR, RESULTS_DIR, RANDOM_SEED


NUMERIC_FEATURES = [
    "current_income",
    "cycle_start_balance",
    "start_balance_to_income",
    "days_in_cycle",
    "avg_daily_spend_30d",
    "std_daily_spend_30d",
    "max_daily_spend_30d",
    "total_spend_30d",
    "weekend_spend_share_30d",
    "spending_volatility_30d",
    "previous_cycle_spend_ratio",
    "previous_cycle_shortfall",
    "projected_spend_to_start_balance",
    "cycle_start_day_of_month",
]
CATEGORICAL_FEATURES = ["pattern", "income_type"]
TARGET = "shortfall"


def best_f1_threshold(y_true, probabilities):
    """Chọn ngưỡng trên tập validation, không dùng tập test để chọn ngưỡng."""
    best = (float("-inf"), 0.5)
    for threshold in np.linspace(0.05, 0.95, 91):
        predicted = (probabilities >= threshold).astype(int)
        score = f1_score(y_true, predicted, zero_division=0)
        if score > best[0] or (np.isclose(score, best[0]) and abs(threshold - 0.5) < abs(best[1] - 0.5)):
            best = (float(score), float(threshold))
    return best[1], best[0]


def compute_metrics(y_true, score, threshold, probability_for_brier=None):
    y_true = np.asarray(y_true, dtype=int)
    score = np.asarray(score, dtype=float)
    predicted = (score >= threshold).astype(int)
    metrics = {
        "accuracy": float(accuracy_score(y_true, predicted)),
        "precision": float(precision_score(y_true, predicted, zero_division=0)),
        "recall": float(recall_score(y_true, predicted, zero_division=0)),
        "f1": float(f1_score(y_true, predicted, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, score)) if len(np.unique(y_true)) > 1 else float("nan"),
        "pr_auc": float(average_precision_score(y_true, score)) if len(np.unique(y_true)) > 1 else float("nan"),
        "threshold": float(threshold),
    }
    if probability_for_brier is not None:
        metrics["brier_score"] = float(brier_score_loss(y_true, np.clip(probability_for_brier, 0, 1)))
    else:
        metrics["brier_score"] = float("nan")
    return metrics


def choose_ml_model(X_train, y_train, X_val, y_val):
    """Thử vài cấu hình nhỏ, chọn cấu hình tốt nhất theo ROC-AUC trên validation."""
    try:
        from xgboost import XGBClassifier

        candidates = []
        for n_estimators, max_depth in [(150, 2), (250, 3), (250, 4)]:
            candidates.append(
                (
                    f"XGBoost (n_estimators={n_estimators}, max_depth={max_depth})",
                    XGBClassifier(
                        objective="binary:logistic",
                        eval_metric="logloss",
                        tree_method="hist",
                        n_estimators=n_estimators,
                        max_depth=max_depth,
                        learning_rate=0.05,
                        min_child_weight=3,
                        subsample=0.85,
                        colsample_bytree=0.85,
                        reg_lambda=2.0,
                        n_jobs=1,
                        random_state=RANDOM_SEED,
                    ),
                )
            )
        family = "XGBoost"
    except Exception as exc:
        warnings.warn(f"Không nạp được XGBoost ({exc}); dùng HistGradientBoosting thay thế.")
        candidates = []
        for max_iter, max_leaf_nodes in itertools.product([100, 180], [7, 15, 31]):
            candidates.append(
                (
                    f"HistGradientBoosting (max_iter={max_iter}, max_leaf_nodes={max_leaf_nodes})",
                    HistGradientBoostingClassifier(
                        max_iter=max_iter,
                        learning_rate=0.06,
                        max_leaf_nodes=max_leaf_nodes,
                        l2_regularization=1.0,
                        random_state=RANDOM_SEED,
                    ),
                )
            )
        family = "HistGradientBoosting"

    best_model = None
    best_name = None
    best_params = None
    best_auc = -1.0
    tuning_rows = []
    for name, candidate in candidates:
        candidate.fit(X_train, y_train)
        probabilities = candidate.predict_proba(X_val)[:, 1]
        auc = float(roc_auc_score(y_val, probabilities)) if len(np.unique(y_val)) > 1 else 0.5
        tuning_rows.append({"configuration": name, "validation_roc_auc": auc})
        if auc > best_auc:
            best_auc = auc
            best_model = candidate
            best_name = name
            best_params = candidate.get_params(deep=False)

    return best_model, best_name, best_params, best_auc, pd.DataFrame(tuning_rows), family


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(DATA_DIR / "cycle_dataset.csv", parse_dates=["cycle_start_date", "cycle_end_date"])
    users = pd.read_csv(DATA_DIR / "users.csv")
    if data.empty:
        raise RuntimeError("cycle_dataset.csv rỗng. Hãy chạy generate_data.py và build_dataset.py trước.")

    data["previous_cycle_shortfall"] = data["previous_cycle_shortfall"].astype(int)
    data["pattern"] = pd.Categorical(data["pattern"], categories=sorted(data["pattern"].unique()))
    data["income_type"] = pd.Categorical(data["income_type"], categories=sorted(data["income_type"].unique()))
    X_raw = data[NUMERIC_FEATURES + CATEGORICAL_FEATURES].copy()
    X = pd.get_dummies(X_raw, columns=CATEGORICAL_FEATURES, dtype=float)
    X = X.replace([np.inf, -np.inf], np.nan)

    # Chia theo người dùng (không chia ngẫu nhiên từng dòng) để tránh cùng một người
    # xuất hiện ở cả train và test.
    user_groups = users.copy()
    user_groups["stratum"] = user_groups["pattern"].astype(str) + " | " + user_groups["income_type"].astype(str)
    user_ids = user_groups["user_id"].to_numpy()
    strata = user_groups["stratum"].to_numpy()
    train_users, temporary_users = train_test_split(
        user_ids, test_size=0.30, random_state=RANDOM_SEED, stratify=strata
    )
    temporary_map = user_groups.set_index("user_id").loc[temporary_users]
    val_users, test_users = train_test_split(
        temporary_users,
        test_size=0.50,
        random_state=RANDOM_SEED,
        stratify=temporary_map["stratum"].to_numpy(),
    )

    train_mask = data["user_id"].isin(train_users)
    val_mask = data["user_id"].isin(val_users)
    test_mask = data["user_id"].isin(test_users)
    y = data[TARGET].astype(int)

    X_train = X.loc[train_mask].fillna(X.loc[train_mask].median())
    X_val = X.loc[val_mask].fillna(X.loc[train_mask].median())
    X_test = X.loc[test_mask].fillna(X.loc[train_mask].median())
    y_train, y_val, y_test = y.loc[train_mask], y.loc[val_mask], y.loc[test_mask]

    print(
        f"Chia dữ liệu theo người dùng: train {len(train_users)} người, "
        f"validation {len(val_users)} người, test {len(test_users)} người."
    )
    print("Đang huấn luyện B2 - Logistic Regression...")
    logistic = make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, random_state=RANDOM_SEED))
    logistic.fit(X_train, y_train)
    logistic_val_prob = logistic.predict_proba(X_val)[:, 1]
    logistic_threshold, logistic_val_f1 = best_f1_threshold(y_val, logistic_val_prob)

    print("Đang thử cấu hình mô hình chính trên validation...")
    ml_model, ml_name, ml_params, ml_val_auc, tuning_results, ml_family = choose_ml_model(
        X_train, y_train, X_val, y_val
    )
    ml_val_prob = ml_model.predict_proba(X_val)[:, 1]
    ml_threshold, ml_val_f1 = best_f1_threshold(y_val, ml_val_prob)
    tuning_results.to_csv(RESULTS_DIR / "hyperparameter_tuning.csv", index=False, encoding="utf-8-sig")

    # B1: luật đơn giản. Nếu mức chi ước tính cho cả chu kỳ lớn hơn số dư đầu chu kỳ,
    # cảnh báo nguy cơ thiếu tiền. Điểm ratio cũng được dùng để vẽ ROC/PR.
    test_data = data.loc[test_mask].copy().reset_index(drop=True)
    b1_score = test_data["projected_spend_to_start_balance"].astype(float).to_numpy()
    b1_threshold = 1.0

    logistic_test_prob = logistic.predict_proba(X_test)[:, 1]
    ml_test_prob = ml_model.predict_proba(X_test)[:, 1]

    comparison_rows = []
    comparison_rows.append(
        {
            "model": "B1 - Quy tắc chi tiêu",
            **compute_metrics(y_test, b1_score, b1_threshold, None),
        }
    )
    comparison_rows.append(
        {
            "model": "B2 - Logistic Regression",
            **compute_metrics(y_test, logistic_test_prob, logistic_threshold, logistic_test_prob),
        }
    )
    comparison_rows.append(
        {
            "model": f"Mô hình chính - {ml_family}",
            **compute_metrics(y_test, ml_test_prob, ml_threshold, ml_test_prob),
        }
    )
    metrics = pd.DataFrame(comparison_rows)
    metrics.to_csv(RESULTS_DIR / "metrics.csv", index=False, encoding="utf-8-sig", float_format="%.6f")

    prediction_output = test_data[
        ["user_id", "cycle_start_date", "cycle_end_date", "income_type", "pattern", "shortfall"]
    ].copy()
    prediction_output = prediction_output.rename(columns={"shortfall": "y_true"})
    prediction_output["score_B1_rule"] = b1_score
    prediction_output["prob_B2_logistic"] = logistic_test_prob
    prediction_output["prob_main_model"] = ml_test_prob
    prediction_output["pred_B1_rule"] = (b1_score >= b1_threshold).astype(int)
    prediction_output["pred_B2_logistic"] = (logistic_test_prob >= logistic_threshold).astype(int)
    prediction_output["pred_main_model"] = (ml_test_prob >= ml_threshold).astype(int)
    prediction_output.to_csv(RESULTS_DIR / "test_predictions.csv", index=False, encoding="utf-8-sig", float_format="%.6f")

    # Độ quan trọng đặc trưng: dùng importance của cây nếu có, nếu không dùng permutation importance.
    feature_names = X.columns.tolist()
    if hasattr(ml_model, "feature_importances_"):
        importances = np.asarray(ml_model.feature_importances_, dtype=float)
    else:
        permutation = permutation_importance(
            ml_model, X_val, y_val, scoring="roc_auc", n_repeats=3, random_state=RANDOM_SEED, n_jobs=2
        )
        importances = np.asarray(permutation.importances_mean, dtype=float)
    feature_table = pd.DataFrame({"feature": feature_names, "importance": importances})
    feature_table = feature_table.sort_values("importance", ascending=False).reset_index(drop=True)
    feature_table.to_csv(RESULTS_DIR / "feature_importance.csv", index=False, encoding="utf-8-sig", float_format="%.8f")

    summary = {
        "model_family": ml_family,
        "model_name": ml_name,
        "validation_roc_auc": float(ml_val_auc),
        "validation_f1_at_selected_threshold": float(ml_val_f1),
        "selected_threshold": float(ml_threshold),
        "logistic_validation_f1": float(logistic_val_f1),
        "logistic_threshold": float(logistic_threshold),
        "n_train_users": int(len(train_users)),
        "n_validation_users": int(len(val_users)),
        "n_test_users": int(len(test_users)),
        "n_train_samples": int(train_mask.sum()),
        "n_validation_samples": int(val_mask.sum()),
        "n_test_samples": int(test_mask.sum()),
        "train_shortfall_rate": float(y_train.mean()),
        "validation_shortfall_rate": float(y_val.mean()),
        "test_shortfall_rate": float(y_test.mean()),
        "ml_parameters": {key: value for key, value in ml_params.items() if key in {
            "n_estimators", "max_depth", "learning_rate", "min_child_weight", "subsample",
            "colsample_bytree", "reg_lambda", "max_iter", "max_leaf_nodes", "l2_regularization"
        }},
        "feature_columns": feature_names,
        "note": "Siêu tham số và ngưỡng được chọn bằng validation; tập test chỉ dùng để báo cáo cuối cùng.",
    }
    (RESULTS_DIR / "model_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    joblib.dump(
        {
            "feature_columns": feature_names,
            "logistic_model": logistic,
            "main_model": ml_model,
            "main_model_name": ml_name,
            "main_model_family": ml_family,
            "logistic_threshold": logistic_threshold,
            "main_threshold": ml_threshold,
            "baseline_rule_threshold": b1_threshold,
        },
        RESULTS_DIR / "trained_models.joblib",
    )

    print("\nKết quả trên tập test:")
    print(metrics[["model", "accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]].to_string(index=False))
    print(f"Mô hình chính được chọn: {ml_name}")
    print(f"Ngưỡng cảnh báo của mô hình chính (chọn từ validation): {ml_threshold:.2f}")
    print(f"Đã lưu kết quả vào {RESULTS_DIR}")


if __name__ == "__main__":
    main()
