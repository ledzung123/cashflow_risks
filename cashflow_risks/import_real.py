"""
import_real.py - Chuyển file CSV chi tiêu của một người (date, spend, income) sang định dạng của pipeline. Người 1.
  from import_real import load_user_csv
  df = load_user_csv("chi_tieu_cua_toi.csv", initial_balance=1_500_000)

Quy tắc:
  - Mỗi dòng: date (YYYY-MM-DD), spend (tổng chi trong ngày, VND), income (số tiền vào; 0 nếu không có).
  - Mặc định từ chối ô lỗi/ngày thiếu/số dư thiếu. Chỉ điền khi người dùng chọn chính sách rõ ràng.
  - Một "lần nhận thu nhập" là ngày có income >= income_min_ratio x income lớn nhất; các khoản nhỏ hơn chỉ cộng vào số dư.
  - Chu kỳ = từ ngày nhận thu nhập đến ngày trước lần nhận kế tiếp. Chu kỳ cuối (chưa biết ngày nhận kế tiếp) bị bỏ.
  - Số dư: nếu file có cột balance (số dư cuối ngày) thì dùng đúng số đó; nếu không, balance = initial_balance + tích lũy (income - spend)
    tính từ ngày nhận thu nhập đầu tiên.
Cần ít nhất 3 lần nhận thu nhập (2 chu kỳ đầy đủ) để dự báo được từ chu kỳ thứ hai.
"""
import os
import warnings

import numpy as np
import pandas as pd

COLS = ["user_id", "date", "spend", "income", "balance", "cycle_id", "day_in_cycle", "D", "pattern", "income_type", "split"]
OUTLIER_X = 10.0      # một ngày chi > 10 lần trung vị các ngày có chi tiêu -> báo là ngoại lai


def _warn_quality(q):
    """Thông báo những biến đổi đã được chọn và các ngoại lai được giữ nguyên.
    Kết quả nằm trong df.attrs['quality']; nguồn đầu vào không bị ghi đè."""
    msgs = []
    if q["o_trong_hoac_loi"]:
        msgs.append(f"{q['o_trong_hoac_loi']} ô spend/income trống hoặc không phải số -> đã coi là 0.")
    if q["dong_chi_am"]:
        msgs.append(f"{q['dong_chi_am']} dòng spend âm (tổng {q['tong_chi_am']:,.0f} VND), có thể là hoàn tiền -> giữ nguyên, nên kiểm tra lại.")
    if q["ngay_thieu"]:
        msgs.append(f"{q['ngay_thieu']} ngày không có dòng nào trong khoảng dữ liệu -> coi như chi 0; nếu là do quên ghi thì dự báo sẽ thấp hơn thực tế.")
    if q["ngay_ngoai_lai"]:
        msgs.append(f"{q['ngay_ngoai_lai']} ngày chi > {OUTLIER_X:.0f} lần trung vị ({q['nguong_ngoai_lai']:,.0f} VND) -> giữ nguyên, kiểm tra có nhập nhầm không.")
    if q["so_du_thieu"]:
        msgs.append(f"{q['so_du_thieu']} ngày thiếu số dư -> lấy theo số dư ngày trước đó.")
    for m in msgs:
        warnings.warn("Chất lượng dữ liệu: " + m, stacklevel=3)


def load_user_csv(src, initial_balance=0.0, income_min_ratio=0.5, user_id=0,
                  missing_policy="error", balance_policy="error"):
    """missing_policy=zero and balance_policy=ffill are explicit opt-ins.

    Zero imputation is an assumption, not recovery of unknown transactions.
    Per-date flags are retained even for dates excluded from complete cycles.
    """
    if missing_policy not in ("error", "zero") or balance_policy not in ("error", "ffill"):
        raise ValueError("missing_policy: error/zero; balance_policy: error/ffill")
    if not np.isfinite(initial_balance) or not 0 < income_min_ratio <= 1:
        raise ValueError("initial_balance phải hữu hạn; income_min_ratio thuộc (0, 1]")
    d = pd.read_csv(src) if isinstance(src, (str, os.PathLike)) else src.copy()
    d.columns = [str(c).strip().lower() for c in d.columns]
    missing = {"date", "spend", "income"} - set(d.columns)
    if missing:
        raise ValueError(f"Thiếu cột: {sorted(missing)}. File cần có các cột date, spend, income.")
    d["date"] = pd.to_datetime(d["date"])
    if d.empty or d.date.isna().any() or (d.date != d.date.dt.normalize()).any():
        raise ValueError("CSV cần ngày hợp lệ, không kèm giờ, và ít nhất một dòng")
    for c in ("spend", "income"):
        d[c] = pd.to_numeric(d[c], errors="coerce").replace([np.inf, -np.inf], np.nan)
    invalid = d[["spend", "income"]].isna()
    flags = [{"date": date.strftime("%Y-%m-%d"), "field": col, "action": "zero_invalid_cell"}
             for col in ("spend", "income") for date in d.loc[invalid[col], "date"]]
    q = {"so_dong": len(d), "o_trong_hoac_loi": int(d[["spend", "income"]].isna().sum().sum()),
         "dong_chi_am": int((d["spend"] < 0).sum()), "tong_chi_am": float(d.loc[d["spend"] < 0, "spend"].sum())}
    if q["o_trong_hoac_loi"] and missing_policy == "error":
        raise ValueError(f"{q['o_trong_hoac_loi']} ô spend/income thiếu hoặc lỗi; sửa nguồn hoặc chọn missing_policy='zero' nếu chấp nhận giả định điền 0")
    d[["spend", "income"]] = d[["spend", "income"]].fillna(0.0)
    has_bal = "balance" in d.columns
    agg = {"spend": "sum", "income": "sum"}
    if has_bal:
        d["balance"] = pd.to_numeric(d["balance"], errors="coerce").replace([np.inf, -np.inf], np.nan)
        flags += [{"date": date.strftime("%Y-%m-%d"), "field": "balance", "action": "missing_input_balance"}
                  for date in d.loc[d.balance.isna(), "date"]]
        if d.balance.isna().any() and balance_policy == "error":
            raise ValueError("Số dư thiếu/lỗi; sửa nguồn hoặc chọn balance_policy='ffill'")
        agg["balance"] = "last"
    d = d.groupby("date", as_index=False).agg(agg)                            # gộp nhiều dòng cùng ngày
    full = pd.date_range(d["date"].min(), d["date"].max())
    q["ngay_thieu"] = len(full) - len(d)
    missing_dates = full.difference(pd.DatetimeIndex(d.date))
    if q["ngay_thieu"] and missing_policy == "error":
        raise ValueError(f"{q['ngay_thieu']} ngày chưa có dữ liệu; không đồng nghĩa chi tiêu bằng 0. Chọn missing_policy='zero' chỉ khi chấp nhận giả định này")
    flags += [{"date": date.strftime("%Y-%m-%d"), "field": "spend,income", "action": "zero_missing_day"}
              for date in missing_dates]
    d = d.set_index("date").reindex(full).rename_axis("date").reset_index()
    d[["spend", "income"]] = d[["spend", "income"]].fillna(0.0)
    med = float(d.loc[d["spend"] > 0, "spend"].median()) if (d["spend"] > 0).any() else 0.0
    q["nguong_ngoai_lai"] = OUTLIER_X * med
    q["ngay_ngoai_lai"] = int((d["spend"] > q["nguong_ngoai_lai"]).sum()) if med > 0 else 0
    q["so_du_thieu"] = int(d["balance"].isna().sum()) if has_bal else 0
    if has_bal:
        if q["so_du_thieu"] and balance_policy == "error":
            raise ValueError("Số dư thiếu sau bổ sung ngày; cần sửa nguồn hoặc chọn balance_policy='ffill'")
        flags += [{"date": date.strftime("%Y-%m-%d"), "field": "balance", "action": "forward_fill"}
                  for date in d.loc[d.balance.isna(), "date"]]
        d["balance"] = d["balance"].ffill()
        if d.balance.isna().any():
            raise ValueError("Không thể điền số dư đầu chuỗi: chưa có số dư trước đó")
    q.update(missing_policy=missing_policy, balance_policy=balance_policy, transformations=flags,
             imputation_assumption=bool(flags))
    _warn_quality(q)
    if d["income"].max() <= 0:
        raise ValueError("Không có ngày nào có income > 0.")
    start = d["income"] >= income_min_ratio * d["income"].max()
    if int(start.sum()) < 3:
        raise ValueError("Cần ít nhất 3 lần nhận thu nhập (2 chu kỳ đầy đủ). Hãy thêm dữ liệu hoặc giảm income_min_ratio.")
    d["is_start"] = start
    d = d.loc[d.index[d["is_start"]][0]:].reset_index(drop=True)              # bỏ các ngày trước lần nhận tiền đầu tiên
    # Mô hình giả định giữa chu kỳ không có tiền vào nên số dư chỉ giảm (SPEC mục 1). Khoản thu phụ và chi âm (hoàn tiền)
    # làm số dư tăng giữa kỳ: nhãn có thể sai và p bỏ qua khoản thu tương lai. Chỉ cảnh báo, không sửa.
    q["thu_nhap_giua_ky"] = int(((d["income"] > 0) & ~d["is_start"]).sum())
    q["chi_am_sau_ngay_nhan_dau"] = int((d["spend"] < 0).sum())
    q["vi_pham_so_du_chi_giam"] = bool(q["thu_nhap_giua_ky"] or q["chi_am_sau_ngay_nhan_dau"])
    if q["vi_pham_so_du_chi_giam"]:
        warnings.warn(f"Chất lượng dữ liệu: {q['thu_nhap_giua_ky']} ngày có tiền vào giữa chu kỳ và {q['chi_am_sau_ngay_nhan_dau']} "
                      "ngày chi âm. Mô hình giả định số dư chỉ giảm giữa chu kỳ, nên nhãn và xác suất có thể sai.", stacklevel=2)
    d["cycle_id"] = d["is_start"].cumsum() - 1
    d = d[d["cycle_id"] < d["cycle_id"].max()].copy()                         # bỏ chu kỳ cuối (chưa biết ngày nhận kế tiếp)
    d["day_in_cycle"] = d.groupby("cycle_id").cumcount() + 1
    d["D"] = d.groupby("cycle_id")["day_in_cycle"].transform("max") - d["day_in_cycle"]
    if not has_bal:
        d["balance"] = float(initial_balance) + (d["income"] - d["spend"]).cumsum()
    d["user_id"], d["pattern"], d["income_type"], d["split"] = user_id, "unknown", "real", "demo"
    d["date"] = d["date"].dt.strftime("%Y-%m-%d")
    for c in ("spend", "income", "balance"):
        d[c] = d[c].round().astype(int)
    out = d[COLS].reset_index(drop=True)
    out.attrs["quality"] = q
    return out
