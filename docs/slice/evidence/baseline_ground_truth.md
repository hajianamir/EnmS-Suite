# ISO 50006 Auto-Baseline Advisor Ground-Truth Specification (§10.4 / Workstream 12)

## 1. Ground Truth Mathematical Formulation
The canonical synthetic evaluation dataset is constructed with known parameters:

$$y = \beta_0 + \beta_1 \cdot \text{HDD}_{18.3} + \beta_2 \cdot \text{production\_tons} + \epsilon$$

Where:
- $\beta_0 = 5.0$ kWh/day (baseload intercept)
- $\beta_1 = 0.30$ kWh/HDD
- $\beta_2 = 0.20$ kWh/ton
- $\epsilon \sim \mathcal{N}(0, \sigma^2)$ with $\sigma = 2.0$ kWh/day
- Sample Size: 365 daily intervals (1 full calendar year)
- Uniform Sampling: 1 day intervals, 0 missing data gaps, coverage ratio = 1.0

## 2. Recovery Thresholds
Any compliant ISO 50006 candidate regression model must recover the true generating parameters within $\pm 10\%$:
- $\beta_0 \in [4.5, 5.5]$
- $\beta_1 \in [0.27, 0.33]$
- $\beta_2 \in [0.18, 0.22]$
- Residual standard error $s \approx 2.0 \pm 0.3$
- $R^2 > 0.90$
