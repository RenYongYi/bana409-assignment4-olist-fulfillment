"""Create the standalone assignment notebook. Answers are filled from its own run."""
from pathlib import Path
import textwrap
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
cells = []


def md(text, key=None):
    cell = nbf.v4.new_markdown_cell(textwrap.dedent(text).strip())
    if key:
        cell.metadata["answer_key"] = key
    cells.append(cell)


def code(text):
    cells.append(nbf.v4.new_code_cell(textwrap.dedent(text).strip()))


md("""
# Assignment 4 — Data App and Phone Trade-in Pricing

**Part 1 — Olist Fulfillment Desk**

- **Deployed app URL:** PENDING — add the verified URL from your own Streamlit Cloud account.
- **GitHub repository URL:** PENDING — add the verified public repository URL from your own GitHub account.

The repository contains `README.md`, the Streamlit app, an order-level Olist CSV, and
`olist-eda.ipynb`. The dashboard serves one e-commerce fulfillment operations manager
who prioritizes overdue orders and assigns seller or carrier follow-up.

**Part 2 — Phone Trade-in Pricing**

All answers below use the supplied simulated dataset, quoted on October 1, 2025.
These are findings about the assignment simulation, not evidence about the real phone market.
""")
md("""
## Evaluation plan

The required split is fixed before any exploration of the holdout: 4,000 training phones
and 1,000 test phones, `test_size=0.2, random_state=409`. EDA, preprocessing fitting,
and five-fold model selection use training data only. All four final predictive scorecards
are calculated once, together, after model fitting and tuning are complete.
The required holdout permutation analysis and offer-rate exercise then reuse those fixed
models; neither changes any model. Selecting an offer rate on this same holdout is a
retrospective assignment exercise, not an unbiased estimate of a production policy.
""")
code("""
from pathlib import Path
import hashlib
import json
import platform
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sklearn
from IPython.display import display
from sklearn.base import clone
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LinearRegression, SGDRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.inspection import permutation_importance

%matplotlib inline
pd.options.display.float_format = '{:,.3f}'.format
plt.rcParams.update({'figure.figsize': (9, 4.5), 'axes.spines.top': False,
                     'axes.spines.right': False, 'axes.grid': True, 'grid.alpha': 0.15})
ROOT = Path.cwd()
(ROOT / 'evidence').mkdir(exist_ok=True)
print('Python:', platform.python_version(), '| scikit-learn:', sklearn.__version__)
""")
md("""
## Part 2A — Prepare the data

The target is `resale_price`; the features are every column except `phone_id` and
`resale_price`. No phone is removed, no identifier is used as a predictor, and the
test set is not used to choose preprocessing.
""")
code("""
df = pd.read_csv('phone_trade_in.csv')
X = df.drop(columns=['phone_id', 'resale_price'])
y = df['resale_price']
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=409
)
assert len(df) == 5000 and len(X_train) == 4000 and len(X_test) == 1000
assert set(X_train.index).isdisjoint(X_test.index)
print('Data shape:', df.shape, '| train:', X_train.shape, '| test:', X_test.shape)
display(X_train.head())
display(X_train.dtypes.rename('dtype').to_frame())
display(X_train.isna().sum().rename('training_missing_count').to_frame())
train = X_train.assign(resale_price=y_train, phone_age=2025 - X_train.release_year)
""")
md("""
### Question 1 — Missing battery health

Which brands have missing battery information? What does observed battery health depend
on? Who receives a high or low guess under global median imputation, and why might the
effect on prediction be smaller than expected?
""")
code("""
missing_by_brand = train.groupby('brand').battery_health.apply(
    lambda s: s.isna().mean() * 100
).rename('missing_pct').sort_values(ascending=False)
battery_by_brand = train.groupby('brand').battery_health.median().rename('median_battery')
battery_by_age = train.groupby('phone_age').battery_health.agg(['median', 'count'])
global_battery_median = float(train.battery_health.median())
print('Training-set global battery median:', global_battery_median)
display(pd.concat([missing_by_brand, battery_by_brand], axis=1))
display(battery_by_age.rename(columns={'median': 'median_battery', 'count': 'observed_phones'}))
battery_groups = train.groupby(['brand', 'phone_age']).battery_health.agg(
    observed_median='median', missing_count=lambda s: s.isna().sum()
)
battery_groups['global_guess_minus_group_median'] = global_battery_median - battery_groups.observed_median
display(battery_groups.loc[battery_groups.missing_count > 0])
""")
md("Answer is populated from the executed output.", "battery")
md("""
### Question 2 — Price over time

Plot training resale price against days since launch. Describe the shape and whether
a straight line can represent it.
""")
code("""
fig, ax = plt.subplots()
ax.scatter(train.days_since_launch, train.resale_price, s=9, alpha=0.22, color='#147D75')
ax.set(xlabel='Days since launch', ylabel='Resale price (USD)',
       title='Training phones: resale value falls nonlinearly with age')
fig.tight_layout()
fig.savefig('evidence/phone-price-over-time.png', dpi=150)
plt.show()
age_resale = train.groupby('phone_age').resale_price.median()
display(age_resale.rename('training_median_resale_usd').to_frame())
""")
md("Answer is populated from the executed output.", "price_shape")
md("""
### One shared preprocessor

Numerical features receive training-fitted median imputation and z-score scaling.
Categorical features receive most-frequent imputation and full one-hot encoding, with
unknown categories ignored. Keeping every category lets us compare category weights by
subtraction as requested. Individual dummy coefficients depend on the redundant coding;
within-column contrasts are the meaningful comparisons. Each model gets an unfitted clone
of this same preprocessor. Cross-validation refits preprocessing inside each training fold.
""")
code("""
num_features = X_train.select_dtypes(include='number').columns.tolist()
cat_features = [c for c in X_train.columns if c not in num_features]
num_pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler()),
])
cat_pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='most_frequent')),
    ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False)),
])
preprocessor = ColumnTransformer([
    ('num', num_pipeline, num_features),
    ('cat', cat_pipeline, cat_features),
])
print('Numerical:', num_features)
print('Categorical:', cat_features)
""")
md("""
## Part 2B — Train and compare

### Step 1 — Model-free baseline

Use the **training mean**, without consulting test prices. Final scoring is deferred to
Step 5 so all models are evaluated after tuning is finished.
""")
code("""
baseline_value = float(y_train.mean())
print(f'Baseline prediction for every phone: ${baseline_value:,.3f}')
""")
md("### Step 2 — Linear regression")
code("""
lr_pipeline = Pipeline([
    ('preprocessor', clone(preprocessor)),
    ('lin_reg', LinearRegression()),
])
lr_pipeline.fit(X_train, y_train)
print('Linear regression fitted on', len(X_train), 'training phones; no grid search.')
""")
md("### Step 3 — SGD: the eight required parameter combinations, five folds")
code("""
sgd_pipeline = Pipeline([
    ('preprocessor', clone(preprocessor)),
    ('sgd', SGDRegressor(random_state=409)),
])
sgd_grid = {
    'sgd__max_iter': [10000, 100000],
    'sgd__tol': [1e-5, 1e-3],
    'sgd__eta0': [0.01, 0.1],
}
sgd_search = GridSearchCV(sgd_pipeline, sgd_grid, cv=5,
    scoring='neg_root_mean_squared_error', n_jobs=2, error_score='raise')
sgd_search.fit(X_train, y_train)
sgd_best = sgd_search.best_estimator_
print('Best SGD parameters:', sgd_search.best_params_)
print('Best training CV RMSE:', -sgd_search.best_score_)
display(pd.DataFrame(sgd_search.cv_results_)[['params', 'mean_test_score', 'rank_test_score']])
""")
md("### Step 4 — Random forest: the four required parameter combinations, five folds")
code("""
rf_pipeline = Pipeline([
    ('preprocessor', clone(preprocessor)),
    ('forest', RandomForestRegressor(random_state=409)),
])
rf_grid = {
    'forest__n_estimators': [100, 150],
    'forest__max_depth': [5, 10],
}
rf_search = GridSearchCV(rf_pipeline, rf_grid, cv=5,
    scoring='neg_root_mean_squared_error', n_jobs=2, error_score='raise')
rf_search.fit(X_train, y_train)
rf_best = rf_search.best_estimator_
print('Best random forest parameters:', rf_search.best_params_)
print('Best training CV RMSE:', -rf_search.best_score_)
display(pd.DataFrame(rf_search.cv_results_)[['params', 'mean_test_score', 'rank_test_score']])
""")
md("""
### Step 5 — One final predictive scorecard on the locked test set

Both searches are now finished. No model, feature or parameter is changed after this point.
""")
code("""
predictions = {
    'Baseline': np.full(len(X_test), baseline_value),
    'Linear regression': lr_pipeline.predict(X_test),
    'SGD': sgd_best.predict(X_test),
    'Random forest': rf_best.predict(X_test),
}
scores = pd.DataFrame({name: {
    'RMSE': np.sqrt(mean_squared_error(y_test, pred)),
    'MAE': mean_absolute_error(y_test, pred),
    'R_squared': r2_score(y_test, pred),
} for name, pred in predictions.items()}).T
y_pred_lr = predictions['Linear regression']
y_pred_rf = predictions['Random forest']
display(scores)
improvements = pd.DataFrame({
    'RMSE_reduction_USD': scores.loc['Baseline', 'RMSE'] - scores.RMSE,
    'MAE_reduction_USD': scores.loc['Baseline', 'MAE'] - scores.MAE,
    'R_squared_increase': scores.R_squared - scores.loc['Baseline', 'R_squared'],
}).drop(index='Baseline')
display(improvements)
scores.to_csv('evidence/phone_model_scores.csv')
""")
md("Answer is populated from the executed output.", "best_model")
md("Answer is populated from the executed output.", "sgd_comparison")
md("### Question 5 — Why the forest wins: count impossible linear predictions")
code("""
negative_linear_count = int((y_pred_lr < 0).sum())
linear_price_by_age = pd.DataFrame({
    'phone_age': 2025 - X_test.release_year,
    'actual': y_test, 'linear_prediction': y_pred_lr,
    'negative_prediction': y_pred_lr < 0,
}).groupby('phone_age').agg(
    phones=('actual', 'size'), mean_actual=('actual', 'mean'),
    mean_prediction=('linear_prediction', 'mean'), negative_predictions=('negative_prediction', 'sum')
)
print('Negative linear regression predictions:', negative_linear_count, 'out of', len(X_test))
display(linear_price_by_age)
""")
md("Answer is populated from the executed output.", "forest_shape")
md("""
## Part 2C — Interpret the models

### Step 1 — Linear weights and requested category contrasts

Numerical coefficients below are dollars per one **training standard deviation**.
Category contrasts are dollars relative to another category of the same input, holding
the other model inputs fixed. They describe the fitted prediction, not causal effects.
""")
code("""
weights = pd.Series(lr_pipeline['lin_reg'].coef_,
    index=lr_pipeline['preprocessor'].get_feature_names_out())
print(weights.round(0).to_string())
screen_difference = float(weights['cat__screen_condition_cracked'] - weights['cat__screen_condition_perfect'])
apple_honor_difference = float(weights['cat__brand_Apple'] - weights['cat__brand_Honor'])
repair_difference = float(weights['cat__repaired_before_yes'] - weights['cat__repaired_before_no'])
contrasts = pd.Series({
    'Cracked minus perfect screen': screen_difference,
    'Apple minus Honor': apple_honor_difference,
    'Previously repaired minus not repaired': repair_difference,
}, name='Predicted price difference (USD)')
display(contrasts.to_frame())
""")
md("Answer is populated from the executed output.", "linear_weights")
md("Answer is populated from the executed output.", "constant_screen_cost")
md("""
### Step 2 — Test-set permutation importance

Run the requested `scoring='neg_root_mean_squared_error'`, `n_repeats=10`,
`random_state=409` analysis on each **complete pipeline**, so the original input
features are permuted. Positive values are increases in RMSE (USD) after shuffling.
This is post-selection interpretation, not another model-selection exercise.
""")
code("""
importances = {}
for name, model in [('Linear regression', lr_pipeline), ('Random forest', rf_best)]:
    result = permutation_importance(model, X_test, y_test,
        scoring='neg_root_mean_squared_error', n_repeats=10, random_state=409, n_jobs=2)
    table = pd.DataFrame({'RMSE_increase_USD': result.importances_mean,
        'repeat_std_USD': result.importances_std}, index=X_test.columns)
    table = table.sort_values('RMSE_increase_USD', ascending=False)
    importances[name] = table
    print(name, '— five most important original features')
    display(table.head(5))
    table.to_csv('evidence/importance-' + name.lower().replace(' ', '-') + '.csv')
""")
md("Answer is populated from the executed output.", "importance")
md("""
## Part 2D — Turn predictions into the trade-in decision

The offer equals `offer_rate * predicted price`. A seller accepts when the offer is
at least 75% of actual resale value. Accepted-phone profit is `actual - offer`;
rejected phones contribute zero. No transaction, repair, shipping or holding costs
are included in this assignment's simplified profit definition.
""")
code("""
def trade_in_profit(predicted, actual, offer_rate):
    \"\"\"Offer offer_rate x predicted price; sellers accept at >=75% of actual.\"\"\"
    offer = offer_rate * predicted
    accepted = offer >= 0.75 * actual
    profit = (actual - offer)[accepted]
    return accepted.sum(), profit.sum()

actual = y_test.to_numpy()
offer_rates = np.round(np.arange(0.60, 0.901, 0.05), 2)
rows = []
for rate in offer_rates:
    row = {'offer_rate': rate}
    for name in ['Baseline', 'Linear regression', 'Random forest']:
        count, profit = trade_in_profit(predictions[name], actual, rate)
        row[name + ' bought'] = int(count)
        row[name + ' profit_USD'] = float(profit)
    rows.append(row)
profit_table = pd.DataFrame(rows).set_index('offer_rate')
display(profit_table)
profit_table.to_csv('evidence/phone_offer_rate_profit.csv')
""")
md("### Step 2 — Linear regression at 75%: include zeros for rejected phones")
code("""
linear_offers = 0.75 * y_pred_lr
linear_accepted = linear_offers >= 0.75 * actual
per_phone_profit = np.where(linear_accepted, actual - linear_offers, 0.0)
age_profit = pd.DataFrame({
    'phone_age': (2025 - X_test.release_year).to_numpy(), 'profit': per_phone_profit,
    'accepted': linear_accepted, 'actual': actual, 'prediction': y_pred_lr,
}).groupby('phone_age').agg(
    phones=('profit', 'size'), bought=('accepted', 'sum'),
    total_profit_USD=('profit', 'sum'), mean_actual_USD=('actual', 'mean'),
    mean_prediction_USD=('prediction', 'mean'),
)
assert np.isclose(age_profit.total_profit_USD.sum(), profit_table.loc[0.75, 'Linear regression profit_USD'])
display(age_profit)
age_profit.to_csv('evidence/phone_linear_profit_by_age.csv')
""")
md("Answer is populated from the executed output.", "r2_profit")
md("### Evidence for the offer-rate and adverse-selection questions")
code("""
best_rf_rate = float(profit_table['Random forest profit_USD'].idxmax())
best_rf_profit = float(profit_table.loc[best_rf_rate, 'Random forest profit_USD'])
best_rf_bought = int(profit_table.loc[best_rf_rate, 'Random forest bought'])
print(f'Best random forest offer rate: {best_rf_rate:.2f}; bought: {best_rf_bought}; profit: ${best_rf_profit:,.2f}')
baseline_selection = []
for rate in offer_rates:
    offered = rate * baseline_value
    accepted = offered >= 0.75 * actual
    baseline_selection.append({
        'offer_rate': rate, 'same_offer_USD': offered, 'bought': int(accepted.sum()),
        'accepted_mean_resale_USD': float(actual[accepted].mean()),
        'share_accepted_at_loss_pct': float((actual[accepted] < offered).mean() * 100),
    })
baseline_selection = pd.DataFrame(baseline_selection).set_index('offer_rate')
display(baseline_selection)
""")
md("Answer is populated from the executed output.", "offer")
md("Answer is populated from the executed output.", "baseline_profit")
md("""
## Part 2E — Advice to the platform manager

Four to six sentences, using dollar evidence and business language.
""")
md("Answer is populated from the executed output.", "manager")
md("""
## Reproducibility and evidence export

This cell exports the numbers used in the answers. It does not fit, tune or rescore a
model. Re-run from the top with the supplied CSV and pinned project environment.
""")
code("""
summary = {
    'data_sha256': hashlib.sha256(Path('phone_trade_in.csv').read_bytes()).hexdigest(),
    'python': platform.python_version(), 'sklearn': sklearn.__version__,
    'training_rows': len(X_train), 'test_rows': len(X_test),
    'missing_pct_by_brand': missing_by_brand.to_dict(),
    'battery_median_by_brand': battery_by_brand.to_dict(),
    'battery_median_by_age': battery_by_age['median'].to_dict(),
    'global_battery_median': global_battery_median,
    'resale_median_by_age': age_resale.to_dict(),
    'training_mean_price': baseline_value,
    'sgd_best_parameters': sgd_search.best_params_, 'rf_best_parameters': rf_search.best_params_,
    'scores': scores.to_dict(orient='index'),
    'improvements': improvements.to_dict(orient='index'),
    'negative_linear_predictions': negative_linear_count,
    'linear_price_by_age': linear_price_by_age.to_dict(orient='index'),
    'contrasts': contrasts.to_dict(),
    'importance': {name: table.to_dict(orient='index') for name, table in importances.items()},
    'profit_table': profit_table.to_dict(orient='index'),
    'baseline_selection': baseline_selection.to_dict(orient='index'),
    'age_profit': age_profit.to_dict(orient='index'),
    'best_rf_rate': best_rf_rate, 'best_rf_profit': best_rf_profit,
    'best_rf_bought': best_rf_bought,
}
Path('evidence/phone_results.json').write_text(json.dumps(summary, indent=2) + '\\n')
prediction_evidence = pd.DataFrame({'phone_id': df.loc[X_test.index, 'phone_id'],
    'actual_USD': actual, **{name: pred for name, pred in predictions.items()}})
prediction_evidence.to_csv('evidence/phone_test_predictions.csv', index=False)
print('Evidence exported. All question answers refer to the outputs immediately above them.')
""")

nb = nbf.v4.new_notebook(cells=cells, metadata={
    "kernelspec": {"display_name": "Python 3.14 (BANA409)", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.14"},
})
nbf.write(nb, ROOT / "phone-trade-in.ipynb")
print("Created", ROOT / "phone-trade-in.ipynb")
