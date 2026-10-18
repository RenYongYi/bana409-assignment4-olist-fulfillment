from pathlib import Path
import textwrap
import nbformat as nbf

root = Path(__file__).resolve().parents[1]
cells = []
def md(s): cells.append(nbf.v4.new_markdown_cell(textwrap.dedent(s).strip()))
def code(s): cells.append(nbf.v4.new_code_cell(textwrap.dedent(s).strip()))

md("""
# Olist — EDA and dashboard decisions

**Audience:** one e-commerce fulfillment operations manager.
**Decision:** prioritize overdue open orders and assign seller or carrier follow-up.

Source: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce),
anonymized real commercial orders, 2016–2018. This notebook analyzes the one-order-per-row
CSV prepared by `scripts/prepare_olist.py`. That script first aggregates item prices at
order level, then joins customers with cardinality checks. No sampling is performed.
Re-download the three original files with `scripts/download_olist.py` if reconstruction
from the official source is needed; the small derived CSV is already in the repository.
""")
code("""
from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display
from fulfillment import load_orders, replay_cohort, overdue_orders, headline, backlog_trend
%matplotlib inline
plt.rcParams.update({'figure.figsize': (9, 4), 'axes.spines.top': False, 'axes.spines.right': False})
orders = load_orders('data/olist_orders.csv')
cohort = replay_cohort(orders)
print('Rows and columns:', orders.shape)
print('Derived CSV bytes:', Path('data/olist_orders.csv').stat().st_size)
print('Purchase coverage:', orders.purchase_at.min(), 'to', orders.purchase_at.max())
print('Unique order IDs:', orders.order_id.nunique())
display(orders.head())
display(orders.dtypes.rename('dtype').to_frame())
display(orders.isna().sum().rename('missing').to_frame())
display(orders.describe().T)
""")
md("""
Missing delivery timestamps can describe open orders, so they are not blindly filled or
dropped. Missing approval, promise or merchandise value prevents safe inclusion in this
particular replay. Final cancellation status is known only retrospectively: excluding
cancelled/unavailable orders defines a limited cohort, not a complete reconstruction of
the live historical order book. The dashboard states this limitation explicitly.
""")
code("""
quality = pd.Series({
    'final_canceled_or_unavailable': orders.final_status.isin(['canceled','unavailable']).sum(),
    'missing_approval': orders.approved_at.isna().sum(),
    'missing_item_value': orders.merchandise_brl.isna().sum(),
    'handoff_before_approval': (orders.handoff_at < orders.approved_at).sum(),
    'delivery_before_handoff': (orders.delivered_at < orders.handoff_at).sum(),
    'delivery_before_approval': (orders.delivered_at < orders.approved_at).sum(),
    'delivered_but_missing_handoff': (orders.delivered_at.notna() & orders.handoff_at.isna()).sum(),
    'excluded_union': len(orders) - len(cohort),
    'replay_cohort': len(cohort),
}, name='orders')
display(quality.to_frame())
display(orders.final_status.value_counts().rename('orders').to_frame())
monthly = orders.groupby(orders.purchase_at.dt.to_period('M')).size()
display(monthly.rename('orders').to_frame())
fig, ax = plt.subplots(figsize=(11, 4))
monthly.plot.bar(ax=ax, color='#147D75')
ax.set(title='Source order coverage: the late tail is sparse', xlabel='Purchase month', ylabel='Orders')
fig.tight_layout(); fig.savefig('evidence/olist-monthly-coverage.png', dpi=140); plt.show()
""")
md("""
The source's late tail is not evidence of a business collapse: September and October
2018 are sparsely represented. The app therefore restricts the replay date to February
2017–August 2018 and shows the full source period separately. Impossible milestone
sequences are excluded rather than silently re-ordered. Quality counts overlap, so only
the union is used for the total excluded count.
""")
code("""
as_of = pd.Timestamp('2018-08-01')
queue = overdue_orders(cohort, as_of)
metrics = headline(queue)
print('Default historical view:', as_of, metrics)
stage = queue.groupby('stage').agg(orders=('order_id','size'), merchandise_brl=('merchandise_brl','sum'))
display(stage)
display(queue.groupby('destination_state').agg(orders=('order_id','size'), merchandise_brl=('merchandise_brl','sum')).sort_values('orders',ascending=False).head(10))
display(queue[['days_overdue','merchandise_brl']].describe())
print('Orders with multiple sellers in source:', int((orders.seller_count > 1).sum()))
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
queue.days_overdue.clip(upper=60).hist(ax=axes[0], bins=20, color='#147D75')
axes[0].set(title='Overdue age (values above 60 pooled)', xlabel='Days overdue', ylabel='Orders')
queue.merchandise_brl.clip(upper=queue.merchandise_brl.quantile(.99)).hist(ax=axes[1],bins=25,color='#D99035')
axes[1].set(title='Overdue item value (99th-percentile display cap)',xlabel='BRL',ylabel='Orders')
fig.tight_layout(); fig.savefig('evidence/olist-queue-distributions.png',dpi=140); plt.show()
""")
md("""
The queue contains both orders not yet handed to a carrier and orders already with a
carrier. This split identifies different follow-up owners; it earns a place on the app.
The value distribution is skewed, so the app displays total item value alongside count
and keeps individual values in the optional action queue. No values are capped in the
KPIs: the caps above are for EDA visualization only. Long-overdue records may also be
stale source records, so the manager must verify current status before escalating.
""")
code("""
trend = backlog_trend(cohort, as_of)
fig, ax = plt.subplots()
ax.plot(trend.Date, trend['Overdue orders'],marker='o',color='#147D75')
ax.set(title='Overdue backlog: recent direction',xlabel='Historical snapshot date',ylabel='Overdue orders')
fig.autofmt_xdate(); fig.tight_layout(); fig.savefig('evidence/olist-backlog-trend.png',dpi=140); plt.show()
display(trend)
evidence = {'as_of': str(as_of.date()), 'headlines': metrics,
    'cohort_rows': len(cohort), 'excluded_rows': len(orders)-len(cohort),
    'quality': {k:int(v) for k,v in quality.items()},
    'stage_counts': {k:int(v) for k,v in queue.stage.value_counts().items()},
    'previous_day': headline(overdue_orders(cohort,as_of-pd.Timedelta(days=1)))}
Path('evidence/olist_default_snapshot.json').write_text(json.dumps(evidence,indent=2)+'\\n')
""")
md("""
## Decisions carried into the app

- **Top:** overdue open orders, their merchandise value, and the count awaiting seller handoff.
  These answer how large the exception is and whether seller action is still possible.
- **Middle:** one 14-day trend and one stage breakdown. These show direction and follow-up owner.
- **Bottom:** a collapsed queue sorted by overdue days, then item value, with order IDs and export.
  This supports actual case assignment while keeping the first screen small.
- **Filters:** historical review date and delivery destination. A manager can focus a regional review.
- **Cut:** payment-method mix and product-popularity rankings. Neither changes who should follow up
  these already approved overdue orders. A geographic map is also omitted: a destination filter and
  actionable order queue are more useful here and avoid a large geolocation file.
- **Refresh:** hourly in production, reviewed at 09:00 and 15:00; a >20% daily rise from a base of
  at least 20 overdue orders triggers an exception alert. Thresholds are proposed operating rules,
  not statistically calibrated or empirically optimal thresholds.

No predictive model is necessary for this Part 1 decision. The full design justification,
business cost of stale data, metric definitions and production limitations are in `README.md`.
""")
nb = nbf.v4.new_notebook(cells=cells, metadata={'kernelspec':{'display_name':'Python 3.14 (BANA409)','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.14'}})
nbf.write(nb, root/'olist-eda.ipynb')
print('Created olist-eda.ipynb')
