"""
make_demo.py - MVP: tạo demo.html (một file, mở bằng trình duyệt, không cần cài gì) mô phỏng luồng hoạt động của hệ thống. Người 4.
  python src/make_demo.py                                  # demo: hệ thống huấn luyện trên 300 người mô phỏng, trang hiển thị 20 người (tập test)
  python src/make_demo.py --per-pattern 10                 # hiển thị 40 người (10 người mỗi kiểu chi tiêu)
  python src/make_demo.py --csv chi_tieu.csv --balance 1500000    # demo trên file CSV của một người (date, spend, income[, balance])
Hệ thống (XGBoost, phân phối sai số, ngưỡng tau, biên của B1/B2) luôn được huấn luyện trên dữ liệu MÔ PHỎNG; với file CSV,
mô hình chỉ được ÁP DỤNG để minh họa, chưa từng được kiểm chứng trên dữ liệu thật.
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import simulate
from baselines import alert_by_margin, predict_spend_b1, predict_spend_b2, projected_end_balance, tune_margin
from evaluate import evaluate
from explain import LABEL, contributions
from features import FEATURES
from import_real import load_user_csv
from labels import make_dp, prepare_df
from model_xgb import XGBForecaster
from risk import bigdays, cum_pool, cum_prob, tune_pstar, volatility

NOTE_PATTERN = {"even": "chi đều mỗi ngày", "front": "hay dồn chi vào đầu chu kỳ",
                "weekend": "chi nhiều hơn vào cuối tuần", "spike": "thỉnh thoảng có khoản chi lớn bất thường"}
NOTE_INCOME = {"allowance_1st": "nhận trợ cấp đầu tháng", "salary_25": "nhận lương ngày 25"}


def train_system(seed, users):
    raw, _ = simulate.simulate(users, seed, 0.85, 1.05, 0.10)
    df = prepare_df(raw)
    dp = make_dp(df)
    sp = dp.split.to_numpy()
    tr, calib, val, test = (dp[sp == s].reset_index(drop=True) for s in ("train", "calib", "val", "test"))
    fc = XGBForecaster(seed=seed).fit(df, tr, val)
    yc, yv = fc.predict_spend(df, calib), fc.predict_spend(df, val)
    pool = cum_pool(calib, yc, df, volatility(df, calib)[1], bigdays(df, calib))      # phân phối sai số dựng trên calib
    p_val = cum_prob(pool, val, yv, volatility(df, val)[1], bigdays(df, val))
    tau, _ = tune_pstar(val, p_val, evaluate)                                         # tau chọn trên val
    m1, _ = tune_margin(val, predict_spend_b1(df, val), evaluate)
    m2, _ = tune_margin(val, predict_spend_b2(df, val), evaluate)
    return dict(df=df, dp=dp, fc=fc, pool=pool, tau=tau, m1=m1, m2=m2, test=test)


def assemble(S, dfT, dpT, user_meta):
    """Tính p và cảnh báo cho các điểm quyết định dpT của dfT, rồi gom theo người và chu kỳ."""
    y = S["fc"].predict_spend(dfT, dpT)
    p = cum_prob(S["pool"], dpT, y, volatility(dfT, dpT)[1], bigdays(dfT, dpT))
    y1, y2 = predict_spend_b1(dfT, dpT), predict_spend_b2(dfT, dpT)
    a1, a2 = alert_by_margin(dpT, y1, S["m1"]), alert_by_margin(dpT, y2, S["m2"])
    e0, e1, e2 = (projected_end_balance(dpT, v) for v in (y, y1, y2))
    k = lambda v: int(round(float(v) / 1000.0))                                       # lưu theo nghìn đồng cho gọn
    T, _, _ = contributions(S["fc"], dfT, dpT)                                        # SHAP (VND) vào tổng chi dự báo D ngày

    def why(j, n_up=3, n_down=2):
        """Lý do: các đặc trưng làm tăng / giảm dự báo tổng chi nhiều nhất (bỏ đóng góp dưới 1 nghìn đồng)."""
        order = np.argsort(-T[j])
        up = [[LABEL[FEATURES[f]], k(T[j, f])] for f in order[:n_up] if k(T[j, f]) > 0]
        down = [[LABEL[FEATURES[f]], k(T[j, f])] for f in order[::-1][:n_down] if k(T[j, f]) < 0]
        return {"up": up, "down": down}
    users = []
    for uid, meta in user_meta:
        cycles = []
        for c in sorted(dpT[dpT.user_id == uid].cycle_id.unique()):
            g = dfT[(dfT.user_id == uid) & (dfT.cycle_id == c)].sort_values("day_in_cycle")
            idx = dpT.index[(dpT.user_id == uid) & (dpT.cycle_id == c)]
            sub = dpT.loc[idx]
            theta = float(sub.theta_c.iloc[0])
            by_t = {int(t): i for i, t in zip(idx, sub.t)}
            days = []
            for _, r in g.iterrows():
                t = int(r.day_in_cycle)
                rec = {"t": t, "s": k(r.spend), "b": k(r.balance)}
                if t in by_t:
                    i = by_t[t]
                    D = int(dpT.loc[i, "D"])
                    rec.update(st="p", p=round(float(p[dpT.index.get_loc(i)]), 3), al=int(p[dpT.index.get_loc(i)] > S["tau"]),
                               a1=int(a1[dpT.index.get_loc(i)]), a2=int(a2[dpT.index.get_loc(i)]),
                               y=[k(v) for v in y[dpT.index.get_loc(i)][:D]],
                               e=k(e0[dpT.index.get_loc(i)]), e1=k(e1[dpT.index.get_loc(i)]), e2=k(e2[dpT.index.get_loc(i)]),
                               w=why(dpT.index.get_loc(i)))
                else:
                    rec["st"] = "b" if r.balance < theta else "l"
                days.append(rec)
            cycles.append({"id": int(c), "L": int(len(g)), "start": pd.Timestamp(g.date.iloc[0]).strftime("%Y-%m-%d"),
                           "theta": k(theta), "end": k(sub.end_balance.iloc[0]), "short": int(sub.y.iloc[0]), "days": days})
        if cycles:
            users.append({"id": int(uid), "label": meta["label"], "note": meta["note"], "cycles": cycles})
    return users


def pick_sim_users(S, per_pattern=2):
    t = S["test"]
    cyc = t.groupby(["user_id", "cycle_id"]).agg(y=("y", "max"), pattern=("pattern", "first"), income=("income_type", "first")).reset_index()
    picked = []
    for pat in ("even", "front", "weekend", "spike"):
        n = 0
        for uid, g in cyc[cyc.pattern == pat].groupby("user_id"):
            if g.y.nunique() == 2:                                                   # có cả chu kỳ thiếu tiền lẫn đủ tiền
                picked.append((int(uid), pat, g.income.iloc[0])); n += 1
            if n == per_pattern:
                break
    meta = [(uid, {"label": f"Người {i + 1}", "note": f"Dữ liệu mô phỏng: {NOTE_INCOME[inc]}, {NOTE_PATTERN[pat]}. Mô hình không được biết kiểu chi tiêu này."})
            for i, (uid, pat, inc) in enumerate(picked)]
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--users", type=int, default=300)
    ap.add_argument("--csv", default=None)
    ap.add_argument("--missing-policy", choices=("error", "zero"), default="error")
    ap.add_argument("--balance-policy", choices=("error", "ffill"), default="error")
    ap.add_argument("--balance", type=float, default=0.0, help="số dư trước ngày nhận thu nhập đầu tiên (khi file không có cột balance)")
    ap.add_argument("--per-pattern", type=int, default=5, help="số người hiển thị cho mỗi kiểu chi tiêu (4 kiểu); mặc định 5 = 20 người trong tổng số --users (300)")
    ap.add_argument("--out", default="demo.html")
    a = ap.parse_args()
    imported = load_user_csv(a.csv, initial_balance=a.balance, missing_policy=a.missing_policy,
                             balance_policy=a.balance_policy) if a.csv else None
    S = train_system(a.seed, a.users)
    print(f"đã huấn luyện hệ thống: tau = {S['tau']:.2f}, biên B1 = {S['m1']:+.2f}, B2 = {S['m2']:+.2f}")
    if a.csv:
        dfT = prepare_df(imported)
        dpT = make_dp(dfT)
        meta = [(0, {"label": "Dữ liệu của bạn", "note": "Dữ liệu thật do nhóm cung cấp. Mô hình được huấn luyện trên dữ liệu mô phỏng nên kết quả chỉ mang tính minh họa."})]
        source = "Dữ liệu: tệp CSV của nhóm. Mô hình huấn luyện trên dữ liệu mô phỏng, chưa kiểm chứng trên dữ liệu thật."
        if imported.attrs["quality"]["imputation_assumption"]:
            source += " Có dữ liệu thiếu được điền theo chính sách đã chọn; dự báo phụ thuộc giả định điền dữ liệu."
    else:
        dfT, dpT = S["df"], S["test"]
        meta = pick_sim_users(S, a.per_pattern)
        source = f"Dữ liệu: hệ thống được huấn luyện trên {a.users} người dùng mô phỏng; trang hiển thị {len(meta)} người, ở các chu kỳ mô hình chưa từng thấy khi huấn luyện."
    dpT = dpT.reset_index(drop=True)
    users = assemble(S, dfT, dpT, meta)
    data = {"meta": {"tau": round(float(S["tau"]), 3), "source": source,
                     "limit": "Giới hạn: bản minh họa trên dữ liệu mô phỏng, chưa phải lời khuyên tài chính; mô hình chưa được kiểm chứng trên dữ liệu thật."},
            "users": users, "data_quality": imported.attrs["quality"] if imported is not None else None}
    tpl = open(os.path.join(os.path.dirname(__file__), "demo_template.html"), encoding="utf-8").read()
    html = tpl.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(html)
    n_c = sum(len(u["cycles"]) for u in users)
    print(f"đã ghi {a.out}: {len(users)} người, {n_c} chu kỳ, {os.path.getsize(a.out) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
