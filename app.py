"""BANA409 Part 1: a small dashboard for one fulfillment operations manager."""
from html import escape
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from fulfillment import load_orders, replay_cohort, overdue_orders, headline, backlog_trend

ROOT = Path(__file__).parent
TEAL = "#287C70"
AMBER = "#C67B38"
FONT = "-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
st.set_page_config(page_title="Olist | Fulfillment Desk", page_icon="📦", layout="wide")
st.html("<style>" + (ROOT / "styles.css").read_text() + "</style>")


@st.cache_data
def data():
    return load_orders(ROOT / "data/olist_orders.csv")


def finish_chart(chart):
    """Use one restrained visual language for both supporting charts."""
    return (chart.configure(background="transparent", font=FONT)
            .configure_view(strokeWidth=0)
            .configure_axis(labelColor="#6E7F7A", titleColor="#6E7F7A", labelFontSize=11,
                            titleFontSize=11, titleFontWeight=400, domain=False,
                            tickSize=0, labelPadding=10, gridColor="#EDF0EB", gridOpacity=1)
            .configure_axisX(grid=False)
            .configure_title(font=FONT, color="#203630"))


orders = data()
cohort = replay_cohort(orders)

with st.sidebar:
    st.html('''<div class="brand"><span class="brand-mark">FD<span></span></span>
        <div class="brand-copy">Fulfillment Desk<small>OPERATIONS WORKSPACE</small></div></div>
        <div class="sidebar-divider"></div>
        <div class="sidebar-eyebrow">YOUR DAILY REVIEW</div>''')
    st.header("Review scope")
    as_of = st.date_input("Review date · start of day", value=pd.Timestamp("2018-08-01").date(),
                          min_value=pd.Timestamp("2017-02-01").date(), max_value=pd.Timestamp("2018-08-31").date())
    state = st.selectbox("Delivery destination", ["All destinations"] + sorted(cohort.destination_state.dropna().unique()))
    st.caption("Snapshot at 00:00, in source time.")
    st.html('''<div class="rhythm-card"><div class="sidebar-eyebrow">PROPOSED PRODUCTION RHYTHM</div>
        <div class="rhythm-row"><span>Data refresh</span><strong>Hourly</strong></div>
        <div class="rhythm-row"><span>Manager review</span><strong>09:00 · 15:00</strong></div>
        <p>Exception alerts between reviews.</p></div>
        <div class="source-note"><span class="source-dot"></span> HISTORICAL DEMONSTRATION
        <p>Olist · Sep 2016–Oct 2018<br>A frozen dataset, with a proposed live workflow. Review dates end Aug 2018; later records are sparse.</p></div>''')

backlog = overdue_orders(cohort, as_of, state)
previous = overdue_orders(cohort, pd.Timestamp(as_of) - pd.Timedelta(days=1), state)
now, before = headline(backlog), headline(previous)

with st.container(key="pageheader"):
    st.html('''<div class="masthead"><span class="eyebrow">E-COMMERCE / OPERATIONS</span>
        <span class="replay-badge"><i></i> Historical replay</span></div>''')
    st.title("Fulfillment Desk")
    st.markdown("For the **e-commerce fulfillment operations manager**. Prioritize overdue orders and assign the next follow-up.")
    st.caption("Olist / Kaggle · Data: Sep 2016–Oct 2018 · Proposed refresh: hourly · Manager review: 09:00 & 15:00 + exception alerts")

st.html(f'''<div class="section-heading"><span class="eyebrow">01 / PRIORITY SNAPSHOT</span>
    <span class="snapshot-date">{as_of:%d %b %Y} <span>· 00:00 · {escape(state)}</span></span></div>''')
cols = st.columns(3, gap="medium")
cols[0].metric("Overdue open orders", f"{now['overdue_orders']:,}",
               f"{now['overdue_orders'] - before['overdue_orders']:+,} vs previous day", delta_color="inverse", border=True)
cols[1].metric("Merchandise value overdue", f"R$ {now['merchandise_brl']:,.0f}",
               f"R$ {now['merchandise_brl'] - before['merchandise_brl']:+,.0f} vs previous day", delta_color="inverse", border=True)
cols[2].metric("Awaiting seller handoff", f"{now['awaiting_handoff']:,}",
               f"{now['awaiting_handoff'] - before['awaiting_handoff']:+,} vs previous day", delta_color="inverse", border=True)
st.caption("Overdue = approved, past the promised date and still undelivered at this snapshot. R$ is BRL item value, excluding freight; it is not a loss estimate.")

escalate = before['overdue_orders'] >= 20 and now['overdue_orders'] > 1.20 * before['overdue_orders']
if escalate:
    brief_class = "action-brief escalation"
    brief_title = "Escalation recommended"
    brief_text = "Overdue orders rose by more than 20% from a base of at least 20. Review the oldest cases with the seller and logistics leads."
else:
    brief_class = "action-brief"
    brief_title = "Start with the oldest overdue orders"
    brief_text = "Verify current status, then assign seller operations or the logistics lead. Escalate a >20% daily rise from a base of at least 20 orders."
st.html(f'''<div class="{brief_class}" role="status"><span class="brief-symbol" aria-hidden="true">↗</span>
    <div><strong>{brief_title}</strong><p>{brief_text}</p></div><span class="brief-tag">REVIEW BRIEF</span></div>''')

st.html('<div class="chart-section eyebrow">02 / UNDERSTAND THE QUEUE</div>')
left, right = st.columns([1.2, 1], gap="medium")
with left, st.container(border=True, key="trend-panel"):
    st.subheader("Is the queue growing?")
    st.caption("Overdue open orders · last 14 days")
    trend = backlog_trend(cohort, as_of, state)
    base = alt.Chart(trend).encode(
        x=alt.X("Date:T", title=None, axis=alt.Axis(format="%d %b", labelAngle=0, tickCount=5)),
        y=alt.Y("Overdue orders:Q", title=None, scale=alt.Scale(zero=True), axis=alt.Axis(tickCount=4, format=",d")),
        tooltip=[alt.Tooltip("Date:T", title="Snapshot", format="%d %b %Y"), alt.Tooltip("Overdue orders:Q", title="Overdue orders", format=",")],
    )
    area = base.mark_area(color=TEAL, opacity=0.07)
    line = base.mark_line(color=TEAL, strokeWidth=2.8, point=alt.OverlayMarkDef(color=TEAL, filled=True, size=22))
    last = base.transform_filter(alt.FieldEqualPredicate(field="Date", equal=alt.DateTime(year=as_of.year, month=as_of.month, date=as_of.day))).mark_point(color=TEAL, filled=True, size=75, stroke="white", strokeWidth=2)
    chart = finish_chart((area + line + last).properties(height=190))
    st.altair_chart(chart, width="stretch", theme=None)
    st.html('<div class="panel-footnote"><span class="legend-dot teal"></span>Daily snapshots at 00:00 · same destination scope</div>')

with right, st.container(border=True, key="stage-panel"):
    st.subheader("Who needs to follow up?")
    st.caption("Overdue orders by operational stage")
    stages = backlog.groupby("stage").size().reindex(["Awaiting seller handoff", "With carrier"], fill_value=0).rename("Orders").reset_index()
    base = alt.Chart(stages).encode(
        y=alt.Y("stage:N", title=None, sort=["Awaiting seller handoff", "With carrier"],
                axis=alt.Axis(labelLimit=130, labelExpr="datum.label === 'Awaiting seller handoff' ? 'Seller handoff' : datum.label")),
        x=alt.X("Orders:Q", title=None, scale=alt.Scale(domain=[0, max(1, int(stages.Orders.max()) * 1.22)]),
                axis=alt.Axis(tickCount=4, format=",d", tickMinStep=1)),
        tooltip=[alt.Tooltip("stage:N", title="Stage"), alt.Tooltip("Orders:Q", title="Orders", format=",")],
    )
    bars = base.mark_bar(cornerRadiusEnd=5, size=30).encode(
        color=alt.Color("stage:N", scale=alt.Scale(domain=["Awaiting seller handoff", "With carrier"], range=[AMBER, TEAL]), legend=None))
    labels = base.mark_text(align="left", dx=9, fontSize=12, fontWeight=600, color="#304A41").encode(text=alt.Text("Orders:Q", format=","))
    chart = finish_chart((bars + labels).properties(height=190))
    st.altair_chart(chart, width="stretch", theme=None)
    st.html('<div class="panel-footnote"><span class="legend-dot amber"></span>Seller operations<span class="legend-dot teal separated"></span>Logistics lead</div>')

st.html('<div class="detail-section eyebrow">03 / TAKE THE NEXT STEP</div>')
with st.expander("Open the follow-up queue"):
    st.caption("Sorted by overdue age, then merchandise value. Verify each case before contacting a seller or carrier.")
    queue = backlog[["order_id", "destination_state", "stage", "promised_date", "days_overdue", "merchandise_brl", "seller_count"]].rename(columns={
        "order_id": "Order ID", "destination_state": "Destination", "stage": "Follow-up owner",
        "promised_date": "Promised date", "days_overdue": "Days overdue", "merchandise_brl": "Item value (BRL)", "seller_count": "Seller count",
    })
    queue["Promised date"] = queue["Promised date"].dt.strftime("%Y-%m-%d")
    st.dataframe(queue, hide_index=True, width="stretch", column_config={"Item value (BRL)": st.column_config.NumberColumn(format="R$ %.2f")})
    st.download_button("Download follow-up queue", queue.to_csv(index=False).encode(), file_name=f"olist-follow-up-{as_of}.csv", mime="text/csv", icon=":material/download:")

with st.expander("How to read this historical view"):
    st.write("This is a historical demonstration, not a live feed. Only approval, carrier handoff and delivery events before the selected date determine each displayed stage. A carrier handoff applies to an order; multi-seller orders may need item-level verification.")
    st.write(f"The source has {len(orders):,} orders; this replay covers {len(cohort):,}. Final cancelled/unavailable orders, records missing required approval, promise or value data, and inconsistent event sequences are excluded. Cancellation timestamps are absent, so the selected cohort cannot reconstruct the complete live backlog and can understate exposure.")
    st.write("A transaction record does not show when an event first reached the source system. Source time zones are unspecified. The last dates are incomplete, and the app does not estimate profit, compensation or causal losses. In production, use event-time records including cancellations and refresh hourly from the order and logistics systems.")
    st.markdown("[Source: Olist on Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)")

st.html('<div class="page-footer"><span>FULFILLMENT DESK</span><span>Historical context. Clear priorities. Informed follow-up.</span></div>')
