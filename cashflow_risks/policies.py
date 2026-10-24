"""Validation-only alert policies; test data never enters threshold selection.

Costs are per decision point. FAR/burden use eligible cycles in make_dp, not
all calendar cycles. A threshold uses the strict score > threshold convention.
"""
import numpy as np
import pandas as pd

from evaluate import evaluate

COST_RATIOS = (1, 2, 3, 5, 10, 20)


def checked_scores(dp, score):
    s = np.asarray(score, dtype=float)
    if s.ndim != 1 or len(s) != len(dp) or not len(s) or not np.isfinite(s).all():
        raise ValueError("Scores must be finite, nonempty and aligned with decision points")
    return s


def cost_per_100(y, score, threshold, ratio):
    y = np.asarray(y, dtype=bool)
    alert = np.asarray(score) > threshold
    return float(100 * (np.sum(alert & ~y) + ratio * np.sum(~alert & y)) / len(y))


def select_cost_threshold(dp_val, score_val, ratio):
    """Exact sweep, including alert-all/none; ties prefer fewer alerts."""
    if not np.isfinite(ratio) or ratio <= 0:
        raise ValueError("FN/FP cost ratio must be positive and finite")
    s = checked_scores(dp_val, score_val)
    order = np.argsort(s, kind="stable")
    ss, yy = s[order], dp_val.y.to_numpy(dtype=bool)[order]
    last = np.r_[ss[1:] != ss[:-1], True]
    tp_removed = np.cumsum(yy)[last]
    negatives_removed = np.cumsum(~yy)[last]
    thresholds = np.r_[np.nextafter(ss[0], -np.inf), ss[last]]
    costs = np.r_[np.sum(~yy), np.sum(~yy) - negatives_removed + ratio * tp_removed]
    return float(thresholds[np.flatnonzero(costs == costs.min())[-1]])


def select_far_threshold(dp_val, score_val, target=0.2):
    """Higher quantile ensures empirical validation FAR <= target, including ties."""
    if not 0 <= target <= 1:
        raise ValueError("FAR target must be in [0, 1]")
    s = checked_scores(dp_val, score_val)
    c = dp_val.assign(score=s).groupby(["user_id", "cycle_id"]).agg(
        y=("y", "max"), score=("score", "max"))
    neg = c.loc[c.y == 0, "score"].to_numpy()
    if not len(neg):
        raise ValueError("Validation needs at least one negative cycle to select FAR")
    return float(np.nextafter(neg.min(), -np.inf) if target == 1 else
                 np.quantile(neg, 1 - target, method="higher"))


def alert_metrics(dp, alert):
    """Metrics and repeated-alert burden, counting missed positive cycles as zero lead."""
    c = dp[["user_id", "cycle_id", "t", "y", "dip_day"]].assign(a=np.asarray(alert, bool))
    keys = ["user_id", "cycle_id"]
    cycles = c.groupby(keys).agg(y=("y", "max"), days=("a", "sum"), dip=("dip_day", "first"))
    cycles = cycles.join(c[c.a].groupby(keys).t.min().rename("first"))
    neg, pos = cycles[cycles.y == 0], cycles[cycles.y == 1]
    lead = (pos.dip - pos["first"]).dropna()
    return {**evaluate(dp, alert),
            "lead_mean_all": float(lead.sum() / len(pos)) if len(pos) else np.nan,
            "lead_median_caught": float(lead.median()) if len(lead) else np.nan,
            "negative_alert_days_mean": float(neg.days.mean()),
            "negative_cycles_ge5_alert_days": float((neg.days >= 5).mean()),
            "negative_notifications_once_per_cycle": float((neg.days > 0).mean())}


def policy_table(val, scores_val, test, scores_test, f1_thresholds, probability_models=()):
    """Prespecified policies, reported individually; no best-on-test selection."""
    rows = []
    for model in scores_val:
        sv = checked_scores(val, scores_val[model])
        st = checked_scores(test, scores_test[model])
        choices = [("f1_val", f1_thresholds[model], np.nan, "validation"),
                   ("far20_val", select_far_threshold(val, sv), np.nan, "validation")]
        choices += [(f"cost_r{r}_val", select_cost_threshold(val, sv, r), r, "validation")
                    for r in COST_RATIOS]
        if model in probability_models:
            choices += [(f"bayes_r{r}", 1 / (1 + r), r, "fixed_cost_assumption") for r in COST_RATIOS]
        for policy, threshold, ratio, source in choices:
            row = {"model": model, "policy": policy, "threshold": threshold,
                   "threshold_source": source, "fn_fp_ratio": ratio, "far_target": 0.2 if policy == "far20_val" else np.nan}
            for split, dp, score in (("val", val, sv), ("test", test, st)):
                row.update({f"{split}_{k}": v for k, v in alert_metrics(dp, score > threshold).items()})
                if np.isfinite(ratio):
                    row[f"{split}_cost_per_100"] = cost_per_100(dp.y, score, threshold, ratio)
            rows.append(row)
    return pd.DataFrame(rows)
