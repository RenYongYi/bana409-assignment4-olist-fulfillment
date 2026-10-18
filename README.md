# Fulfillment Desk

A small Streamlit dashboard for one **e-commerce fulfillment operations manager** who
must prioritize overdue orders and assign seller or carrier follow-up.

**App URL:** https://bana409-olist-fulfillment-renyongyi.streamlit.app/
**Repository URL:** https://github.com/RenYongYi/bana409-assignment4-olist-fulfillment

This README answers Steps 1–4 of the BANA409 Data App exercise. The separate
`phone-trade-in.ipynb` contains Part 2 and the two submission links in its first Markdown
cell. Review and personalize this working draft before submission: the assignment
requires each student's own explanations and accounts.

## Step 1 — Dataset and decision-maker

**Source:** [Brazilian E-Commerce Public Dataset by Olist on Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).
It is anonymized real commercial data about orders made through Olist in multiple
Brazilian marketplaces. The source includes 99,441 orders, 112,650 order-item records
and 99,441 customer records in the three files used here. Purchase timestamps run from
September 4, 2016 to October 17, 2018. The late tail is sparse, so the app's review-date
window is February 1, 2017 through August 31, 2018; it is not evidence of current
operations.

**Unit of observation:** one row per order. `scripts/prepare_olist.py` first sums item
prices and counts items/sellers within each order, then joins orders and customer
destination state with explicit one-to-one/many-to-one validation. This prevents a
multi-item order from multiplying headline order counts or merchandise value. No
sampling is performed. The resulting single CSV has 99,441 rows, 11 columns and
16,045,919 bytes (about 16.05 MB), below the exercise's approximately 25 MB limit.
The raw files and large, unused geolocation table are not committed.

**One decision-maker:** the fulfillment operations manager. This is not a sales,
marketing or general executive dashboard. The manager coordinates the seller-operations
and logistics leads and needs to decide which overdue orders need follow-up today.
The destination filter supports a regional investigation within that role.

## Step 2 — Why this dashboard should exist

**Decision sentence:** If the fulfillment manager sees the overdue queue rising, they
will inspect the oldest overdue orders and assign follow-up to seller operations when
handoff has not occurred, or to the logistics lead when the order is already with a
carrier. Merchandise value helps break ties between orders of similar overdue age.

In the proposed current workflow, the manager exports order and logistics files, joins
them manually and asks colleagues for updates. This is a business-workflow assumption,
not a claim verified by Olist. Repeating those steps consumes time, encourages duplicate
counting and can leave late orders unassigned. This project does not invent measured
labor savings or a monetary return on investment.

The decision recurs every working day and exceptions can change within the day as
orders are approved, handed over or delivered. An interactive dashboard lets the same
person check direction, isolate a destination and download a work queue. A weekly email
would be stale for same-day follow-up; a one-off report would answer a past question
without maintaining a queue. Alerts complement the dashboard when a threshold is
crossed, but the manager still needs a view to investigate and allocate work.

## Step 3 — EDA, selected content and page order

`olist-eda.ipynb` is executed and shows shape, dtypes, missingness, distributions,
monthly source coverage, event-sequence anomalies, destination differences and the
seller/carrier stage relationship. At the default replay of **August 1, 2018, 00:00**,
the eligible cohort contains 96,802 orders. There are **1,649 overdue open orders**,
**R$262,443.30** in overdue merchandise value and **585 awaiting seller handoff**;
the remaining 1,064 are with carriers. These are historical descriptive results, not
predictions or live operating claims.

### Top: three headline numbers, visible immediately

1. **Overdue open orders:** the size of the exception queue.
2. **Merchandise value overdue:** the item-price value associated with those orders,
   excluding freight. This is neither the platform's revenue nor an estimate of lost
   sales, compensation or profit.
3. **Awaiting seller handoff:** the overdue orders that still require seller-side
   investigation rather than only carrier follow-up.

Each uses `st.metric` within `st.columns` and compares with the previous day's same
scope. No additional headline KPIs compete for attention.

### Middle: two supporting charts

- A **14-day overdue-count trend** shows whether the queue is building or clearing.
- An **overdue-stage breakdown** separates awaiting handoff from with-carrier orders,
  identifying the appropriate follow-up team. It explains the composition of the queue;
  it does not establish a causal reason for delay.

### Bottom: optional operational detail

A collapsed order queue is sorted by days overdue, then merchandise value. It contains
order IDs, destination, follow-up stage, promised date, overdue age, value and seller
count, and supports CSV export. This makes the dashboard actionable without adding a
third chart or crowding the first screen. Multi-seller orders require item-level
verification because the source's handoff timestamp is recorded at order level.

The page was planned in this order before implementation:

```text
Title / audience and decision / period and refresh caption
Review scope: historical date and delivery destination
Overdue orders | Merchandise value overdue | Awaiting seller handoff
Exception rule and suggested follow-up
14-day trend | Overdue-stage breakdown
Collapsed follow-up queue and CSV export
Historical-view limitations and source attribution
```

**Only two filters:** review date and destination state. The date is needed to inspect
the historical demonstration; destination supports a focused operational review. A
production version would default to the latest verified event snapshot.

**Two things deliberately not shown:**

- **Payment-method mix.** The queue already concerns approved orders. A card-versus-
  installment chart would not change who follows up these overdue cases.
- **Best-selling products.** Product popularity can interest sales or inventory teams,
  but it does not assign responsibility for an overdue order. It would dilute this
  manager's first-screen priorities.

A geographic map is also omitted: a destination filter and order queue answer the
operational question without a large geolocation file.

### Definitions and potentially misleading data

The snapshot is **00:00 at the start of the selected date**, in the source timestamps'
unspecified local time. An eligible order is open if approved strictly before that
time and not delivered strictly before it. It is overdue if its promised date is
earlier than the selected date. A promise for today is not yet late at 00:00. A handoff
strictly before the snapshot places the order with the carrier. Future handoff and
delivery timestamps do not determine an earlier displayed stage.

The source lacks cancellation-event timestamps. Final cancelled/unavailable orders
are excluded retrospectively rather than pretending to know when cancellation occurred.
Records lacking required approval, promise or value information, and impossible event
sequences, are also excluded. The excluded union is **2,639 orders**; individual quality
categories overlap. Therefore the replay is a **retrospectively selected, limited
cohort**, not the complete historical live backlog. Conditioning on eventual status
and complete timestamps creates selection bias and can understate exposure.

Other limits are shown in the app's historical-view note: a missing delivery event can
be an open order or an unrecorded update; very old cases need verification; event times
do not prove when information reached the source system; time zones are unspecified;
the sparse September/October 2018 tail is not used for the operational review window.
Outliers are retained in monetary totals. EDA plot display caps do not alter app data.

## Step 4 — Refresh, review and action

**Production refresh: hourly** from the order-management and logistics systems.
Approvals, handoffs and deliveries arrive throughout the day. An hourly refresh can
remove a resolved case or route an unresolved one to the correct team before the
next review. Minute-by-minute polling would add integration cost without helping a
manager who allocates work in batches. This cadence is a design choice for the proposed
workflow, not something the frozen CSV already does.

**Manager review: 09:00 and 15:00 on working days**, plus an exception notification.
The refresh schedule and review schedule differ: the data should be ready when the
manager needs it, but the manager should not have to watch the page continuously.

**Track over time:** the overdue order count for a consistent destination scope.
**Proposed action threshold:** a daily increase greater than 20%, provided the previous
day had at least 20 overdue orders, triggers a call to the seller and logistics leads
and an allocation of the oldest cases. The minimum base avoids percentage alerts from
one or two cases. This is an explainable starting rule, not a calibrated optimum;
production history and staffing capacity should be used to validate it.

**Cost of stale data:** a day-old view can keep already delivered orders on the worklist,
miss newly overdue orders and send follow-up to the wrong team. A week-old view is too
late for many customer recovery opportunities. That can waste staff time, prolong
resolution and increase customer-service demand, but the dataset cannot quantify those
costs or establish lost revenue. We therefore show merchandise exposure rather than
inventing a profit or savings metric.

**Production requirement:** use an event log including cancellation and observation
times, item-level shipment milestones where needed, and a documented time zone. The
source-period and intended-refresh caption remains visible in this demonstration; it
does not display an artificial current timestamp or claim a live connection.

## Step 5 — Run and deploy

The project was initialized with `uv init` and uses Python **3.14** as required.

```bash
uv sync --frozen
uv run streamlit run app.py
```

For an app-only environment, `pip install -r requirements.txt` installs the Streamlit
runtime. For the full notebooks use the locked `uv` environment. To reproduce the
derived data from the official source:

```bash
uv run python scripts/download_olist.py
uv run python scripts/prepare_olist.py
```

Publish the project files (excluding `.venv/` and `data/raw/`) to a **public repository
under the submitting student's own GitHub account**. In the student's own Streamlit
Community Cloud account, deploy that repository's `main` branch with main file
`app.py`; select **Python 3.14** under Advanced settings. Verify the deployed page,
then place both actual URLs above and in the first Markdown cell of
`phone-trade-in.ipynb`. Do not substitute a teammate's app or repository.

## Verification and Part 2

- `python -m unittest test_fulfillment.py -v` checks historical milestones, due-date
  boundaries, destination scope, exclusions and exposure calculations.
- `olist-eda.ipynb` is executed with no error outputs.
- `phone-trade-in.ipynb` is executed with the required split, parameter grids and
  holdout rules; plain Markdown answers follow the relevant code outputs.
- Part 2 selects a 75% offer rate for the forest and reports $5,700.76 profit on 568
  purchases from the assignment's 1,000-phone test batch, before operating costs.
  This is a simulation result, not a guaranteed future return.

## Attribution

Olist data and the derived CSV: **CC BY-NC-SA 4.0**; see `DATA_LICENSE.md` for attribution,
changes and the source link. Phone data: instructor-provided simulated BANA409 data.
Assignment: https://bana409.harrywang.me/docs/assignments/assignment-4-linear-regression-sgd-and-random-forest
Exercise: https://bana409.harrywang.me/docs/lectures/data-app/in-class-group-exercise
