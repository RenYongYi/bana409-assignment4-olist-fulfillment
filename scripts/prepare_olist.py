"""Build one order-level CSV; do not let order-item joins multiply orders."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
(ROOT / "evidence").mkdir(exist_ok=True)


def prepare():
    raw = ROOT / "data/raw/olist"
    orders = pd.read_csv(raw / "olist_orders_dataset.csv")
    items = pd.read_csv(raw / "olist_order_items_dataset.csv")
    customers = pd.read_csv(raw / "olist_customers_dataset.csv")
    assert orders.order_id.is_unique
    assert customers.customer_id.is_unique
    values = items.groupby("order_id", as_index=False).agg(
        merchandise_brl=("price", "sum"), item_count=("order_item_id", "count"),
        seller_count=("seller_id", "nunique"),
    )
    result = orders.merge(values, on="order_id", how="left", validate="one_to_one").merge(
        customers[["customer_id", "customer_state"]], on="customer_id", how="left", validate="many_to_one"
    )
    result = result.rename(columns={
        "order_purchase_timestamp": "purchase_at", "order_approved_at": "approved_at",
        "order_delivered_carrier_date": "handoff_at", "order_delivered_customer_date": "delivered_at",
        "order_estimated_delivery_date": "promised_date", "order_status": "final_status",
        "customer_state": "destination_state",
    })
    columns = ["order_id", "purchase_at", "approved_at", "handoff_at", "delivered_at", "promised_date",
               "final_status", "destination_state", "merchandise_brl", "item_count", "seller_count"]
    result = result[columns].sort_values(["purchase_at", "order_id"]).reset_index(drop=True)
    result["merchandise_brl"] = result.merchandise_brl.round(2)
    target = ROOT / "data/olist_orders.csv"
    result.to_csv(target, index=False, float_format="%.2f")
    assert len(result) == len(orders)
    assert target.stat().st_size < 25_000_000
    timestamps = pd.to_datetime(result.purchase_at)
    diagnostics = {
        "orders": len(orders), "items": len(items), "customers": len(customers),
        "file_bytes": target.stat().st_size,
        "period_start": str(timestamps.min()), "period_end": str(timestamps.max()),
        "missing_by_column": result.isna().sum().astype(int).to_dict(),
        "final_status_counts": result.final_status.value_counts().astype(int).to_dict(),
        "multiple_item_orders": int((result.item_count > 1).sum()),
        "multiple_seller_orders": int((result.seller_count > 1).sum()),
        "definition": "One row per order; merchandise_brl sums item prices, excludes freight and is not platform revenue or profit.",
    }
    (ROOT / "evidence/olist_preparation.json").write_text(json.dumps(diagnostics, indent=2) + "\n")
    print(json.dumps(diagnostics, indent=2))


if __name__ == "__main__":
    prepare()

