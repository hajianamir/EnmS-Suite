"""
Generates the canonical ISO 50006 ground-truth baseline dataset for Workstream 12.
Generation Formula:
  y = 5.0 + 0.30 * HDD18.3 + 0.20 * production_tons + N(0, sigma=2.0)

Ground Truth Parameters:
  beta_0 = 5.0  (intercept, kWh/day)
  beta_1 = 0.30 (kWh/HDD)
  beta_2 = 0.20 (kWh/ton)
  sigma  = 2.0  (residual noise standard deviation)
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

def generate_ground_truth_dataset(n_days=365, seed=42) -> pd.DataFrame:
    np.random.seed(seed)
    start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    dates = [start_date + timedelta(days=i) for i in range(n_days)]

    # 1. Synthetic Temperature -> HDD18.3
    # Synthetic ambient temperature variation around 12 deg C
    day_of_year = np.arange(n_days)
    temp = 12.0 + 8.0 * np.sin(2 * np.pi * day_of_year / 365.0 - 1.0) + np.random.normal(0, 1.5, n_days)
    hdd18_3 = np.maximum(0.0, 18.3 - temp)

    # 2. Production tons (stochastic industrial schedule)
    production_tons = np.random.uniform(50.0, 150.0, n_days)

    # 3. Non-driver candidates (for variable discovery testing)
    hour_of_day = np.zeros(n_days) # constant daily aggregation
    day_of_week = np.array([d.weekday() for d in dates], dtype=float)

    # 4. Target energy consumption y with Gaussian noise sigma=2.0
    noise = np.random.normal(0, 2.0, n_days)
    y_kwh = 5.0 + 0.30 * hdd18_3 + 0.20 * production_tons + noise

    df = pd.DataFrame({
        "timestamp": dates,
        "energy_kwh": y_kwh,
        "hdd18_3": hdd18_3,
        "production_tons": production_tons,
        "hour_of_day": hour_of_day,
        "day_of_week": day_of_week
    })
    return df

if __name__ == "__main__":
    df = generate_ground_truth_dataset()
    df.to_csv("docs/slice/evidence/baseline_ground_truth.csv", index=False)
    print(f"Generated ground truth dataset with {len(df)} samples.")
    print("Summary:")
    print(df.describe().to_string())
