import os

import matplotlib.pyplot as plt
import pandas as pd
from fredapi import Fred

# ---- 1. Data
fred = Fred(api_key=os.environ["FRED_API_KEY"])
ids = {
    "rent": "CUSR0000SEHA",
    "food": "CUSR0000SAF11",
    "gas": "CUSR0000SETB01",
    "books": "CUSR0000SEEA",
    "cpi": "CPIAUCSL",
}
df = pd.DataFrame({name: fred.get_series(sid) for name, sid in ids.items()})
df = df.loc["2019-01":]

print("Months missing before filling:")
print(df.isna().sum())
df = df.interpolate(method="linear", limit_area="inside")
rebased = df / df.loc["2019-01-01"] * 100

# ---- 2. Weights (UW-Madison 2026-27 undergrad COA, WI resident)
H, GAS, BOOKS = 0.9195, 0.0375, 0.0429


def build(w):
    w = pd.Series(w)
    w = w / w.sum()
    return (rebased[w.index] * w).sum(axis=1)


scenarios = {}
for split in (0.60, 0.72, 0.80):
    scenarios[f"rent {int(split * 100)}% of housing+meals"] = {
        "rent": H * split, "food": H * (1 - split), "gas": GAS, "books": BOOKS}
scenarios["no books (rent 72%)"] = {
    "rent": H * 0.72, "food": H * 0.28, "gas": GAS}
scenarios["no books, no gas (rent 72%)"] = {
    "rent": H * 0.72, "food": H * 0.28}
scenarios["2019-20 COA weights"] = {
    "rent": 0.610, "food": 0.238, "gas": 0.061, "books": 0.092}

# ---- 3. Results
cpi = rebased["cpi"]
rows = {}
for name, w in scenarios.items():
    gap = build(w) - cpi
    rows[name] = {
        "latest month gap": gap.iloc[-1],
        "avg gap, last 12 months": gap.iloc[-12:].mean(),
        "avg gap, 2023-2025": gap.loc["2023":"2025"].mean(),
    }
results = pd.DataFrame(rows).T.round(2)
print("\nGap = student index minus official CPI (index points)")
print(results.to_string())
results.to_csv("sensitivity_results.csv")

# ---- 4. Chart
fig, ax = plt.subplots(figsize=(9, 5))
for name, w in scenarios.items():
    ax.plot(build(w), label=name, linewidth=1.2)
ax.plot(cpi, label="official CPI", color="black", linewidth=2.2)
ax.set_ylabel("Index (Jan 2019 = 100)")
ax.set_title("Student non-tuition basket vs official CPI")
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig("student_cpi.png", dpi=150)
plt.show()
