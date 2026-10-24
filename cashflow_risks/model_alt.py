"""
model_alt.py - Các mô hình thay thế để trả lời "vì sao chọn XGBoost": cùng đặc trưng, cùng mục tiêu, cùng giao diện predict_spend.
  ridge : hồi quy tuyến tính có điều chuẩn (mô hình đơn giản, dễ giải thích)
  rf    : random forest (cây bagging; 40 cây, mỗi cây dùng 8% mẫu để kịp thời gian)
  hgb   : HistGradientBoosting của scikit-learn (boosting khác XGBoost)
"""
import time

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from features import build_matrix
from labels import HORIZON_MAX


def make_estimator(name, seed):
    if name == "ridge":
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=1.0))
    if name == "rf":
        return make_pipeline(SimpleImputer(strategy="constant", fill_value=-1.0),
                             RandomForestRegressor(n_estimators=40, max_depth=12, min_samples_leaf=100, max_features=0.6,
                                                   max_samples=0.08, n_jobs=-1, random_state=seed))
    if name == "hgb":
        return HistGradientBoostingRegressor(max_depth=6, learning_rate=0.06, max_iter=150, min_samples_leaf=100,
                                             l2_regularization=5.0, random_state=seed)
    raise ValueError(name)


class SkForecaster:
    def __init__(self, name, seed=0):
        self.name, self.seed = name, seed
        self.model = make_estimator(name, seed)
        self.fit_seconds = float("nan")

    def fit(self, df, dp_train, dp_val=None):
        X, _, y = build_matrix(df, dp_train, with_target=True)
        t0 = time.time()
        self.model.fit(X, y)
        self.fit_seconds = time.time() - t0
        return self

    def predict_spend(self, df, dp):
        X, meta = build_matrix(df, dp)
        rel = np.clip(self.model.predict(X), 0.0, None)
        out = np.full((len(dp), HORIZON_MAX), np.nan)
        out[meta["idx"], meta["h"] - 1] = rel * meta["scale"]
        return out
