"""BANA409 Part 1: a small dashboard for one fulfillment operations manager."""
from pathlib import Path
import json
import altair as alt
import pandas as pd
import streamlit as st
from fulfillment import load_orders, replay_cohort, overdue_orders, headline, backlog_trend

ROOT = Path(__file__).parent
st.set_page_config(page_title="Olist | Fulfillment Desk", page_icon="📦", layout="wide")


@st.cache_data
def data():
    return load_orders(ROOT / "data/olist_orders.csv")


orders = data()
cohort = replay_cohort(orders)
st.title("Fulfillment Desk")
st.caption("For the e-commerce fulfillment operations manager: prioritize overdue orders and assign seller or carrier follow-up.")
st.caption("Data: Sep 2016–Oct 2018, Olist / Kaggle snapshot · Production refresh: hourly · Manager review: 09:00 and 15:00, plus exception alerts.")

with st.sidebar:
    st.header("Review scope")
    as_of = st.date_input("Review date · start of day", value=pd.Timestamp("2018-08-01").date(),
                          min_value=pd.Timestamp("2017-02-01").date(), max_value=pd.Timestamp("2018-08-31").date())
    state = st.selectbox("Delivery destination", ["All destinations"] + sorted(cohort.destination_state.dropna().unique()))
    st.caption("Historical replay at 00:00 in source time. The operational window ends Aug 2018; later purchase records are sparse.")

backlog = overdue_orders(cohort, as_of, state)
previous = overdue_orders(cohort, pd.Timestamp(as_of) - pd.Timedelta(days=1), state)
now, before = headline(backlog), headline(previous)
st.subheader(f"Priority queue · {as_of:%d %b %Y}, 00:00")
cols = st.columns(3)
cols[0].metric("Overdue open orders", f"{now['overdue_orders']:,}",
               f"{now['overdue_orders'] - before['overdue_orders']:+,} vs previous day", delta_color="inverse")
cols[1].metric("Merchandise value overdue", f"R$ {now['merchandise_brl']:,.0f}",
               f"R$ {now['merchandise_brl'] - before['merchandise_brl']:+,.0f}", delta_color="inverse")
cols[2].metric("Awaiting seller handoff", f"{now['awaiting_handoff']:,}",
               f"{now['awaiting_handoff'] - before['awaiting_handoff']:+,} vs previous day", delta_color="inverse")
st.caption("Overdue = approved before this snapshot, promised before today, and not delivered before this snapshot. R$ is BRL item value, excluding freight; it is not a loss estimate.")

if before['overdue_orders'] >= 20 and now['overdue_orders'] > 1.20 * before['overdue_orders']:
    st.warning("Action trigger: overdue orders rose by more than 20% from a base of at least 20. Review today's queue with the seller and logistics leads.")
else:
    st.info("Review rule: a >20% daily rise from at least 20 overdue orders triggers escalation. Follow up the longest-overdue orders first; verify current status before contacting a seller or carrier.")

left, right = st.columns([1.35, 1])
with left:
    st.subheader("Is the overdue queue growing?")
    trend = backlog_trend(cohort, as_of, state)
    chart = alt.Chart(trend).mark_line(point=True, color="#147D75").encode(
        x=alt.X("Date:T", title=None, axis=alt.Axis(format="%d %b", labelAngle=-30)),
        y=alt.Y("Overdue orders:Q", title="Orders", scale=alt.Scale(zero=True)),
        tooltip=[alt.Tooltip("Date:T", format="%d %b %Y"), "Overdue orders:Q"],
    ).properties(height=260)
    st.altair_chart(chart, width="stretch")
with right:
    st.subheader("Who needs to follow up?")
    stages = backlog.groupby("stage").size().reindex(["Awaiting seller handoff", "With carrier"], fill_value=0).rename("Orders").reset_index()
    chart = alt.Chart(stages).mark_bar(cornerRadiusEnd=5).encode(
        y=alt.Y("stage:N", title=None, sort=["Awaiting seller handoff", "With carrier"]),
        x=alt.X("Orders:Q", title="Overdue orders", axis=alt.Axis(tickMinStep=1)),
        color=alt.Color("stage:N", scale=alt.Scale(domain=["Awaiting seller handoff", "With carrier"], range=["#D99035", "#147D75"]), legend=None),
        tooltip=[alt.Tooltip("stage:N", title="Stage"), "Orders:Q"],
    ).properties(height=260)
    st.altair_chart(chart, width="stretch")

with st.expander("Open the follow-up queue"):
    queue = backlog[["order_id", "destination_state", "stage", "promised_date", "days_overdue", "merchandise_brl", "seller_count"]].rename(columns={
        "order_id": "Order ID", "destination_state": "Destination", "stage": "Follow-up owner",
        "promised_date": "Promised date", "days_overdue": "Days overdue", "merchandise_brl": "Item value (BRL)", "seller_count": "Seller count",
    })
    queue["Promised date"] = queue["Promised date"].dt.strftime("%Y-%m-%d")
    st.dataframe(queue, hide_index=True, width="stretch", column_config={"Item value (BRL)": st.column_config.NumberColumn(format="R$ %.2f")})
    st.download_button("Download follow-up queue", queue.to_csv(index=False).encode(), file_name=f"olist-follow-up-{as_of}.csv", mime="text/csv")

with st.expander("How to read this historical view"):
    st.write("This is a historical demonstration, not a live feed. Only approval, carrier handoff and delivery events before the selected date determine each displayed stage. A carrier handoff applies to an order; multi-seller orders may need item-level verification.")
    st.write(f"The source has {len(orders):,} orders; this replay covers {len(cohort):,}. Final cancelled/unavailable orders, records missing required approval, promise or value data, and inconsistent event sequences are excluded. Cancellation timestamps are absent, so the selected cohort cannot reconstruct the complete live backlog and can understate exposure.")
    st.write("A transaction record does not show when an event first reached the source system. Source time zones are unspecified. The last dates are incomplete, and the app does not estimate profit, compensation or causal losses. In production, use event-time records including cancellations and refresh hourly from the order and logistics systems.")
    st.markdown("[Source: Olist on Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)")
