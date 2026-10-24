"""Secondary evaluation with disjoint users for train/calib/val/test roles.

The temporal evaluation remains the primary result. This diagnostic asks whether the
model can transfer to users whose labels were not used in any other role.
"""
import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from labels import make_dp
from run_risk import load, run, user_roles


def main(seeds, csv=None, K=500):
    out_dir = "results/user_holdout"
    os.makedirs(out_dir, exist_ok=True)
    all_users = None
    for seed in seeds:
        df = load(seed, csv)
        dp = make_dp(df)
        roles = user_roles(dp.user_id.unique())
        assignment = pd.DataFrame([
            {"user_id": int(uid), "role": role}
            for role, ids in roles.items() for uid in sorted(ids)
        ])
        if all_users is None:
            all_users = assignment
        elif not all_users.equals(assignment):
            raise AssertionError("User holdout partition changed between model seeds")

        base, methods, risk, by, (test, p_test, best), pts, (_, _, _, _, _, precision), q1 = run(
            seed, csv=csv, K=K, split_mode="user_holdout")
        q2 = pd.concat([base, risk], ignore_index=True)
        q2["seed"] = seed
        q1["seed"] = seed
        precision["seed"] = seed
        q1.to_csv(f"{out_dir}/q1_seed{seed}.csv", index=False)
        q2.to_csv(f"{out_dir}/q2_seed{seed}.csv", index=False)
        precision.to_csv(f"{out_dir}/precision_seed{seed}.csv", index=False)
        pd.DataFrame([{
            "seed": seed,
            "n_users_train": len(roles["train"]), "n_users_calib": len(roles["calib"]),
            "n_users_val": len(roles["val"]), "n_users_test": len(roles["test"]),
            "n_points_train": len(dp[(dp.user_id.isin(roles["train"])) & (dp.split == "train")]),
            "n_points_calib": len(dp[(dp.user_id.isin(roles["calib"])) & (dp.split == "calib")]),
            "n_points_val": len(dp[(dp.user_id.isin(roles["val"])) & (dp.split == "val")]),
            "n_points_test": len(test), "selected_risk_method": best,
        }]).to_csv(f"{out_dir}/split_sizes_seed{seed}.csv", index=False)
        print(f"seed {seed}: user-holdout test={len(test):,} điểm, {len(roles['test'])} người; p method={best}")

    all_users.to_csv(f"{out_dir}/user_assignments.csv", index=False)
    print(f"Đã lưu kết quả đánh giá người dùng giữ riêng trong {out_dir}/")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--csv", default=None)
    ap.add_argument("--K", type=int, default=500)
    a = ap.parse_args()
    main(a.seeds, a.csv, a.K)
