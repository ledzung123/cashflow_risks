"""model_xgb.py - XGBoost dự báo trực tiếp chi tiêu ngày t+h (SPEC mục 5: predict_spend). Người 3."""
import numpy as np
import xgboost as xgb

from labels import HORIZON_MAX
from features import build_matrix, FEATURES

DEFAULT_PARAMS = dict(n_estimators=600, learning_rate=0.06, max_depth=6, min_child_weight=100,
                      subsample=0.7, colsample_bytree=0.8, reg_lambda=5.0, tree_method="hist",
                      n_jobs=-1, random_state=0, early_stopping_rounds=40)


class XGBForecaster:
    def __init__(self, seed=0, feature_names=None, **params):
        self.feature_names = list(FEATURES if feature_names is None else feature_names)
        if not self.feature_names or len(set(self.feature_names)) != len(self.feature_names) or set(self.feature_names) - set(FEATURES):
            raise ValueError("feature_names must be a nonempty unique subset of FEATURES")
        self.feature_indices = [FEATURES.index(f) for f in self.feature_names]
        p = {**DEFAULT_PARAMS, **params, "random_state": seed}
        self.model = xgb.XGBRegressor(**p)

    def fit(self, df, dp_train, dp_val):
        Xtr, _, ytr = build_matrix(df, dp_train, with_target=True)
        Xva, _, yva = build_matrix(df, dp_val, with_target=True)
        self.model.fit(Xtr[:, self.feature_indices], ytr, eval_set=[(Xva[:, self.feature_indices], yva)], verbose=False)
        self.best_iteration = int(self.model.best_iteration) + 1
        return self

    def predict_spend(self, df, dp):
        """(n_dp, 31): chi tiêu dự báo (VND) ngày t+1..t+D, NaN phía sau D."""
        X, meta = build_matrix(df, dp)
        rel = np.clip(self.model.predict(X[:, self.feature_indices]), 0.0, None)
        out = np.full((len(dp), HORIZON_MAX), np.nan)
        out[meta["idx"], meta["h"] - 1] = rel * meta["scale"]
        return out

    def importance(self):
        imp = self.model.get_booster().get_score(importance_type="gain")
        gains = {self.feature_names[int(k[1:])]: v for k, v in imp.items()}
        tot = sum(gains.values())
        return dict(sorted(((k, v / tot) for k, v in gains.items()), key=lambda kv: -kv[1]))
