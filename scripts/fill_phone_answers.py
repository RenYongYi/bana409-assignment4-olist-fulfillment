"""Fill plain Markdown answers from the notebook's executed numerical evidence."""
from pathlib import Path
import json
import nbformat

ROOT = Path(__file__).resolve().parents[1]
d = json.loads((ROOT / 'evidence/phone_results.json').read_text())
s = d['scores']
profit = d['profit_table']
linear = s['Linear regression']
forest = s['Random forest']
contrast = d['contrasts']
missing = d['missing_pct_by_brand']
age = d['age_profit']
money = lambda x: f"${x:,.2f}"

answers = {}
answers['battery'] = f"""**Answer — Missing battery health.** In the training set, Apple is missing battery health for only {missing['Apple']:.2f}% of phones. The other brands are missing it for {min(v for k,v in missing.items() if k != 'Apple'):.2f}%–{max(v for k,v in missing.items() if k != 'Apple'):.2f}%; the highest share is OPPO ({missing['OPPO']:.2f}%). Observed brand medians are quite similar, ranging from {min(d['battery_median_by_brand'].values()):.0f}% to {max(d['battery_median_by_brand'].values()):.0f}%, while the age relationship is much stronger: age-0 phones have a median of {d['battery_median_by_age']['0']:.0f}%, age-3 phones {d['battery_median_by_age']['3']:.0f}%, and age-6 phones {d['battery_median_by_age']['6']:.0f}%.

The training-wide median is **{d['global_battery_median']:.0f}%**. Relative to these observed age-group medians, this guess is too low for newer phones (for example, 20 percentage points below the age-0 median) and too high for older phones (15 points above the age-6 median). These are plausible group-level biases; the truly missing battery values cannot be checked. The models still see `release_year` and `days_since_launch`, so they can recover much of the age-related price information even when battery health is imputed. That does not make imputation harmless, particularly if reporting patterns change."""
answers['price_shape'] = f"""**Answer — Price over time.** The scatter shows a steep decline in resale value followed by a flatter low-price region, with substantial spread at similar ages. Training median resale prices fall from {money(d['resale_median_by_age']['0'])} for age-0 phones to {money(d['resale_median_by_age']['3'])} at age 3 and {money(d['resale_median_by_age']['6'])} at age 6. A single straight line misses this curvature and the differing price levels of phone types."""
improvement_text = '; '.join(
    f"{name}: RMSE lower by {money(row['RMSE_reduction_USD'])}, MAE lower by {money(row['MAE_reduction_USD'])}, and R² higher by {row['R_squared_increase']:.4f}"
    for name, row in d['improvements'].items())
answers['best_model'] = f"""**Answer — Which model is best?** The random forest wins all three scores: RMSE **{money(forest['RMSE'])}**, MAE **{money(forest['MAE'])}**, and R² **{forest['R_squared']:.4f}**. The baseline has RMSE {money(s['Baseline']['RMSE'])}, MAE {money(s['Baseline']['MAE'])}, and R² {s['Baseline']['R_squared']:.6f}. Improvements over the baseline are: {improvement_text}. Higher R² is better; lower RMSE and MAE are better."""
answers['sgd_comparison'] = f"""**Answer — Same model, two algorithms.** Their results are close: linear regression has RMSE {money(linear['RMSE'])} and SGD {money(s['SGD']['RMSE'])}, a difference of only {money(abs(linear['RMSE'] - s['SGD']['RMSE']))}. Their R² values are {linear['R_squared']:.4f} and {s['SGD']['R_squared']:.4f}. Both fit additive linear predictions on exactly the same transformed features; one solves least squares directly and the other updates weights iteratively. Exact equality is not expected because SGD has finite stopping tolerance and its specified default also includes a small L2 penalty, unlike the unregularized least-squares model. The selected SGD settings are `eta0=0.01`, `max_iter=10000`, `tol=1e-5`."""
answers['forest_shape'] = f"""**Answer — Why the forest wins.** Linear regression predicts **{d['negative_linear_predictions']} negative resale prices out of 1,000 test phones**, which is economically impossible here. The training scatter shows a curved depreciation pattern; the additive straight-line model cannot follow both the steep early decline and the low-price floor. The forest can split on age, original price and condition and fit different price levels in different regions. Its predictions are averages of positive training prices and therefore cannot be negative in this dataset. Its RMSE is {money(linear['RMSE'] - forest['RMSE'])} lower than the linear model's; this is evidence for this dataset, not a guarantee that forests always win."""
answers['linear_weights'] = f"""**Answer — What the linear weights say.** Subtracting the requested category coefficients gives:

- A cracked screen changes the predicted price by **{money(contrast['Cracked minus perfect screen'])}** compared with a perfect screen: about a {money(abs(contrast['Cracked minus perfect screen']))} deduction.
- An Apple phone is predicted to be **{money(contrast['Apple minus Honor'])} more** than an otherwise identical Honor.
- Having been repaired before changes the prediction by **{money(contrast['Previously repaired minus not repaired'])}**, about a {money(abs(contrast['Previously repaired minus not repaired']))} deduction.

These are conditional comparisons from the fitted simulated-data model; they are not real-world causal estimates."""
answers['constant_screen_cost'] = f"""**Answer — One number for every phone.** The model deducts the same {money(abs(contrast['Cracked minus perfect screen']))} for a cracked screen from a $150 budget phone and a $900 flagship, equivalent to {abs(contrast['Cracked minus perfect screen']) / 150 * 100:.1f}% and {abs(contrast['Cracked minus perfect screen']) / 900 * 100:.1f}% of those prices. A universal dollar deduction is restrictive because screen damage can matter differently by original price, tier and age. A random forest can first split on these variables and then learn different screen-condition effects in the resulting groups. It can represent interactions; whether a particular interaction is present must still be checked against data."""
def importance_list(name):
    return ', '.join(f"`{feature}` (+{money(value['RMSE_increase_USD'])})" for feature, value in list(d['importance'][name].items())[:5])
answers['importance'] = f"""**Answer — What drives the price?** The linear model's top five features are {importance_list('Linear regression')}. The forest's top five are {importance_list('Random forest')}.

Both rank days since launch first and original launch price second, and both include battery health and brand in their top five. The linear model also relies on release year, while the forest places screen condition in its top five and obtains almost no additional importance from release year. Release year and days since launch overlap in the age information they carry, so individual permutation rankings are affected by redundancy; they should not be read as causal importance. The printed standard deviations describe variation across shuffles, not confidence intervals for production performance."""
answers['r2_profit'] = f"""**Answer — R-squared is not profit.** Linear regression has R² **{linear['R_squared']:.4f}**, yet at a 75% offer rate it loses **{money(-profit['0.75']['Linear regression profit_USD'])}**. Age 3 contributes {money(age['3']['total_profit_USD'])}, age 4 {money(age['4']['total_profit_USD'])}, and age 5 {money(age['5']['total_profit_USD'])}; together these are {money(sum(age[str(i)]['total_profit_USD'] for i in [3,4,5]))}. At age 3, mean actual resale is {money(age['3']['mean_actual_USD'])} while the mean prediction is {money(age['3']['mean_prediction_USD'])}; at age 4 the corresponding amounts are {money(age['4']['mean_actual_USD'])} and {money(age['4']['mean_prediction_USD'])}.

Overpriced offers are especially likely to be accepted, so overall predictive fit does not protect the platform against losses on the selected purchases. The age-1 group earns {money(age['1']['total_profit_USD'])}, which is insufficient to offset the other groups' losses. All 1,000 phones are included in the age table and rejected offers contribute zero, exactly as requested."""
answers['offer'] = f"""**Answer — The best offer.** Among the seven required rates, the forest's best rate is **{d['best_rf_rate']:.0%}**, buying **{d['best_rf_bought']} phones** and earning **{money(d['best_rf_profit'])}**. At 60%, it buys only {profit['0.6']['Random forest bought']} phones and earns {money(profit['0.6']['Random forest profit_USD'])}: many valuable sellers reject low offers. At 90%, it buys {profit['0.9']['Random forest bought']} phones but earns only {money(profit['0.9']['Random forest profit_USD'])}: paying more compresses margins and increases overpayment exposure. The 75% rate balances these forces on this particular test sample. It is the best tested rate, not a proven continuous or future optimum; production policy selection needs a separate validation period."""
b = d['baseline_selection']['0.75']
answers['baseline_profit'] = f"""**Answer — The baseline and adverse selection.** The baseline predicts the training mean, {money(d['training_mean_price'])}, for every phone. At a 75% rate, it therefore offers the same **{money(b['same_offer_USD'])}** to everyone. Sellers accept if actual value is at most `offer / 0.75`, so cheaper phones are disproportionately selected and many high-value phones leave. The {b['bought']} accepted phones have an average actual resale value of only **{money(b['accepted_mean_resale_USD'])}**; {b['share_accepted_at_loss_pct']:.2f}% are bought above their actual resale value. This produces {money(profit['0.75']['Baseline profit_USD'])} total profit.

The same pattern holds at all seven rates in the displayed diagnostic table: accepted phones' mean resale value is below the common offer, so the baseline loses money at every tested rate. This explains the loss in the supplied data. A constant offer does not mathematically guarantee a loss for every possible price distribution or on every accepted individual phone."""
answers['manager'] = f"""I recommend the pricing approach that adjusts each phone's valuation to its age, original price and condition, with an offer set at **{d['best_rf_rate']:.0%} of its estimated resale value**. In this simulated batch of 1,000 seller submissions, it bought **{d['best_rf_bought']} phones** and earned **{money(d['best_rf_profit'])} before operating costs**, which is the planning figure I would use only for a comparable batch. The simpler straight-line pricing approach lost {money(-profit['0.75']['Linear regression profit_USD'])} at the same offer percentage. Actual results may be worse because shipping, inspection, repairs, holding costs and changes in seller behavior are not included. Before committing a large budget, verify the offer percentage on a separate set of transactions and run a small pilot with spending and overpayment limits."""

path = ROOT / 'phone-trade-in.ipynb'
nb = nbformat.read(path, as_version=4)
# Move the age-profit answer next to the age-profit code without rerunning any scores.
idx = next(i for i,c in enumerate(nb.cells) if c.metadata.get('answer_key') == 'r2_profit')
cell = nb.cells.pop(idx)
age_idx = next(i for i,c in enumerate(nb.cells) if c.cell_type == 'code' and "age_profit.to_csv" in c.source)
nb.cells.insert(age_idx + 1, cell)
for cell in nb.cells:
    key = cell.metadata.get('answer_key')
    if key:
        cell.source = answers[key]
nbformat.validate(nb)
nbformat.write(nb, path)
print('Filled', len(answers), 'Markdown answers using the executed evidence.')
