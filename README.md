# Fulfillment Desk

A Streamlit dashboard for an **e-commerce fulfillment operations manager** who needs
to identify recorded overdue orders, verify their status and assign seller or carrier
follow-up.

- **Deployed app:** [Fulfillment Desk](https://bana409-olist-fulfillment-renyongyi.streamlit.app/)
- **Public repository:** [RenYongYi/bana409-assignment4-olist-fulfillment](https://github.com/RenYongYi/bana409-assignment4-olist-fulfillment)

## Step 1 — Dataset and decision-maker

**Dataset:** [Brazilian E-Commerce Public Dataset by Olist on Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).
The source contains anonymized, real commercial orders made through Olist across
Brazilian marketplaces. It is historical transaction data, not a synthetic teaching
example. The three source tables used contain 99,441 orders, 112,650 order-item records
and 99,441 customer records.

**Period:** purchase dates run from September 4, 2016 to October 17, 2018. The app's
review window is February 1, 2017 to August 31, 2018 because the final two months are
sparsely represented. The full source period remains visible on the page.

**One row:** one order in `data/olist_orders.csv`. Before joining, item prices are
summed and item/seller counts are calculated within each order. Orders and customer
destination state are then joined with explicit cardinality checks. This avoids
multiplying order counts and merchandise value when an order contains several items.
The app reads this one CSV: **99,441 rows, 11 columns, 16,045,919 bytes (16.05 MB)**,
below the exercise's approximately 25 MB limit. No sampling is used. The raw source
tables are excluded; the download and preparation code is in `scripts/`.

**One decision-maker:** the e-commerce fulfillment operations manager, who coordinates
seller operations and logistics. The destination filter supports regional investigation
by this same manager; it does not turn the page into a general sales or executive
report. Data attribution, processing changes and the CC BY-NC-SA 4.0 license are in
[DATA_LICENSE.md](DATA_LICENSE.md).

## Step 2 — Why this dashboard should exist

**Who checks it and when?** In the proposed production workflow, the fulfillment
manager reviews it at **09:00 and 15:00 on working days**, with additional checks after
an exception notification. The current application demonstrates that workflow through
historical snapshots.

**Decision sentence:** If the fulfillment manager sees the overdue queue rising, they
will inspect the oldest recorded exceptions, verify whether those orders are still
unresolved, and assign seller-operations follow-up when handoff is pending or
logistics follow-up when the order is already with a carrier. Among orders with the
same overdue age, merchandise value helps set the investigation order.

**Without the dashboard:** the assumed workflow is to export order and logistics
files, join them manually and ask colleagues for status updates. Repeating that work
consumes staff time and can cause duplicate counting, missed cases and follow-up sent
to the wrong team. This is a proposed business workflow, not an observation verified
at Olist. The dataset does not measure staff hours, compensation or the return on this
app, so no dollar savings are claimed.

**Why a dashboard?** This is a recurring queue-management decision, rather than a
one-time question. A weekly email or static report becomes stale as approvals,
handoffs and deliveries occur. An alert can flag an increase, but it cannot replace
checking the trend, narrowing the destination and exporting the affected orders for
assignment. The commercial value is faster, better-directed exception handling;
measured service or financial improvements would need production evaluation.

## Step 3 — EDA, content choices and page order

[olist-eda.ipynb](olist-eda.ipynb) uses Pandas and Matplotlib to inspect shape, data
types, missing values, distributions, source coverage and relationships between
order stage, overdue age, merchandise value and destination.

### Findings that shaped the design

| EDA finding | Dashboard consequence |
|---|---|
| 9,803 source orders contain multiple items. | Aggregate to one row per order before calculating headline counts or value. |
| August 2018 contains 6,512 purchases; September has only 16 and October only 4. | End the selectable review window in August; do not present the sparse tail as a business collapse. |
| At the default snapshot, 585 overdue orders await handoff and 1,064 are with carriers. | Show a stage breakdown so the manager can route follow-up to the relevant operational lead. |
| São Paulo accounts for 600 of the 1,649 default overdue records. | Provide a destination-state filter for regional investigation, rather than a large map. |
| 1,592 of the 1,649 default overdue records have no delivery timestamp anywhere in the source; median overdue age is 226 days and the maximum is 650. | Treat the queue as recorded exceptions that require status verification, not verified current service failures. Retain the records and explain the limitation. |

### Three headline metrics

The default is **August 1, 2018, 00:00, all destinations**. The eligible replay cohort
contains 96,802 orders; the following metrics describe the overdue subset at that date.

| Metric | Default result | Why it belongs at the top |
|---|---:|---|
| Overdue open orders | 1,649 | Shows the size of the recorded exception queue. |
| Merchandise value overdue | R$262,443.30 | Adds monetary context when prioritizing cases of similar overdue age. This is BRL item value, excluding freight, not platform revenue, profit or estimated loss. |
| Awaiting seller handoff | 585 | Identifies cases that need seller-side investigation rather than only carrier follow-up. |

These are the only three headline metrics. They use `st.metric` side by side in
`st.columns`, with changes against the previous day's snapshot using the same region.
The app rounds the monetary headline to **R$262,443** for readability.

### Two supporting charts and two filters

- **14-day overdue-count trend:** shows whether the exception queue is growing or
  clearing. For the default scope it rises from 1,584 on July 19 to 1,649 on August 1.
  The count axis starts at zero, avoiding an exaggerated impression of that change.
- **Overdue-stage breakdown:** separates awaiting seller handoff from with-carrier
  orders, making the likely follow-up responsibility visible. It describes the
  composition of the queue; it does not prove a causal reason for delay.

The only filters are **review date** and **delivery destination**. Date is necessary
for the historical demonstration; destination lets the manager investigate a region.
A production version should default to the latest verified snapshot.

### Two things deliberately omitted

1. **Monthly purchase-volume chart.** It is useful in EDA for checking source coverage,
   but it does not identify which overdue order needs follow-up. Showing it alongside
   the queue could also encourage misreading the sparse final months as a sales drop.
2. **Overdue-age and item-value histograms.** These reveal skew and old records in EDA,
   but neither identifies an actionable case or its follow-up owner. The sorted order
   table supplies the exact ages and values when the manager needs that detail.

Payment-method mix, product rankings and a geographic map are also outside this
manager's immediate decision. The first screen is reserved for the exception queue.

### Page sketch and ordering rationale

```text
SIDEBAR                         MAIN PAGE
Review date                     Title, decision-maker and decision
Delivery destination            Historical-replay badge, source period and cadence
Proposed production rhythm      01 / Three headline metrics + snapshot date/scope
Historical-source note          Suggested follow-up / escalation brief
                                02 / 14-day trend | Stage breakdown
                                03 / Collapsed order queue with CSV download
                                Collapsed historical-view definitions and limits
```

The metrics come first because the manager needs to assess scale immediately. The
brief then connects that assessment to an action. Charts provide direction and
follow-up context. Detail remains at the bottom for case assignment: order ID,
destination, stage, promised date, overdue age, item value and seller count. The queue
is sorted by overdue days, then merchandise value, both descending.

A deep green sidebar, warm neutral background and white cards separate controls from
results. Teal and amber distinguish carrier and seller stages, with text labels as
well as color. Local `styles.css` supplies consistent spacing and responsive layouts
without external fonts or images.

### Definitions and safeguards against misleading results

- **Snapshot boundary:** 00:00 at the start of the selected date, using the source's
  unspecified local time. Approval must occur strictly before that boundary. A delivery
  or handoff affects the displayed stage only if it occurred strictly before it.
- **Overdue:** the promised date is earlier than the selected date and no delivery is
  recorded before the snapshot. A promise for the selected date is not late at 00:00.
  Future handoff or delivery events cannot determine an earlier displayed stage.
- **Missing and inconsistent data:** final cancelled/unavailable orders, missing
  required approval/promise/value records and impossible milestone sequences are
  excluded. The union excluded is **2,639 orders**; quality categories overlap.
- **Selection bias:** cancellation-event times are absent, so the exclusions use final
  status retrospectively. This is a limited cohort, not a reconstruction of the
  complete historical live backlog, and it can understate exposure.
- **Unrecorded closure and old cases:** a missing delivery event can mean an unresolved
  order or an absent update. The old records found in EDA make status reconciliation
  essential before operational escalation. Event timestamps also do not establish when
  the source system first learned of an event.
- **Outliers and shipment detail:** app totals retain all eligible values; display caps
  used in EDA histograms do not alter those totals. An order-level handoff event may
  hide different shipment states in a multi-seller order, requiring item-level checks.

## Step 4 — Refresh, review and action

**Refresh the production data hourly.** Approvals, handoffs and deliveries change
throughout the day. Hourly ingestion from order-management and logistics systems can
remove resolved cases and update the responsible team before the next review.
Minute-by-minute integration would add cost without matching a manager who allocates
work in batches; daily ingestion could leave a morning resolution on the afternoon
worklist. Hourly is a proposed operating choice to validate against event latency and
staffing capacity.

**Review at 09:00 and 15:00 on working days.** Data freshness and human review are
separate: the data should be ready when needed without requiring the manager to watch
the page continuously. A production exception notification would prompt an extra check.

**Track overdue order count for a consistent destination scope.** A rise of **more than
20% from the previous day, when the previous day had at least 20 overdue orders**, is
the proposed action trigger. After verifying status, the manager calls the seller and
logistics leads and assigns the oldest unresolved cases. The minimum base avoids
percentage alerts caused by one or two orders. This is an explainable starting rule,
not a statistically calibrated optimum.

**Staleness has an operational cost.** A day-old view can miss newly overdue orders,
keep resolved cases in the queue and send follow-up to the wrong team. A week-old view
can prolong unresolved cases and miss opportunities for timely customer recovery.
Those errors waste staff effort and may increase customer-service demand; their
financial cost cannot be estimated from this dataset.

**Current app versus production plan:** this app reads a frozen Kaggle CSV, replays the
selected date and displays an on-page review brief. It does not automatically ingest
hourly data or send external alerts. The source period and intended refresh frequency
are visible on the page. A production implementation would require cancellation and
observation timestamps, reliable closure events, item-level shipment milestones where
needed, a documented time zone and monitored refresh jobs.

## Step 5 — Run and deploy

The project was initialized with `uv init` and uses **Python 3.14**.

```bash
uv sync --frozen
uv run streamlit run app.py
```

For an app-only environment, install `requirements.txt`. To rebuild the derived Olist
CSV from the official source:

```bash
uv run python scripts/download_olist.py
uv run python scripts/prepare_olist.py
```

The public repository and Streamlit Community Cloud app are linked above. Deployment
uses the repository's `main` branch, `app.py` as the entry point and Python **3.14**.
The submitting account is `RenYongYi` on GitHub; the app is deployed through the
corresponding personal Streamlit Cloud account.

## Sources

- [Olist dataset on Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
- [Data attribution and license](DATA_LICENSE.md)
- [Assignment 4](https://bana409.harrywang.me/docs/assignments/assignment-4-linear-regression-sgd-and-random-forest)
- [Data App In-Class Group Exercise](https://bana409.harrywang.me/docs/lectures/data-app/in-class-group-exercise)
