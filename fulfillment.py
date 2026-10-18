"""Historical order replay using milestone timestamps, with an explicit cohort limit."""
from pathlib import Path
import pandas as pd

TIMESTAMPS = ["purchase_at", "approved_at", "handoff_at", "delivered_at", "promised_date"]


def load_orders(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=TIMESTAMPS)
    if not df.order_id.is_unique:
        raise ValueError("Expected exactly one row per order")
    return df


def replay_cohort(df: pd.DataFrame) -> pd.DataFrame:
    # Cancellation event times are absent: this is a retrospectively selected cohort.
    # Never call these totals the complete live operational backlog.
    valid = (
        ~df.final_status.isin(["canceled", "unavailable"])
        & df.approved_at.notna() & df.promised_date.notna() & df.merchandise_brl.notna()
        & df.purchase_at.notna() & (df.approved_at >= df.purchase_at)
        & ~(df.handoff_at < df.approved_at)
        & ~(df.delivered_at < df.handoff_at)
        & ~(df.delivered_at < df.approved_at)
        & ~(df.delivered_at.notna() & df.handoff_at.isna())
    )
    return df.loc[valid].copy()


def overdue_orders(cohort: pd.DataFrame, as_of, state="All destinations") -> pd.DataFrame:
    cutoff = pd.Timestamp(as_of).normalize()
    df = cohort if state == "All destinations" else cohort.loc[cohort.destination_state.eq(state)]
    # The view is the START of the selected date. Events exactly at cutoff are not yet observed.
    approved = df.approved_at.lt(cutoff)
    delivered = df.delivered_at.notna() & df.delivered_at.lt(cutoff)
    late = df.promised_date.lt(cutoff)
    result = df.loc[approved & ~delivered & late].copy()
    handed_off = result.handoff_at.notna() & result.handoff_at.lt(cutoff)
    result["stage"] = handed_off.map({False: "Awaiting seller handoff", True: "With carrier"})
    result["days_overdue"] = (cutoff - result.promised_date).dt.days
    return result.sort_values(["days_overdue", "merchandise_brl"], ascending=[False, False])


def headline(backlog: pd.DataFrame) -> dict:
    return {
        "overdue_orders": int(len(backlog)),
        "merchandise_brl": float(backlog.merchandise_brl.sum()),
        "awaiting_handoff": int(backlog.stage.eq("Awaiting seller handoff").sum()),
    }


def backlog_trend(cohort: pd.DataFrame, as_of, state="All destinations", days=14) -> pd.DataFrame:
    dates = pd.date_range(end=pd.Timestamp(as_of).normalize(), periods=days, freq="D")
    return pd.DataFrame([
        {"Date": day, "Overdue orders": len(overdue_orders(cohort, day, state))}
        for day in dates
    ])
