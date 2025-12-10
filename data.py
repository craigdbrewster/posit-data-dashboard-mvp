from datetime import timedelta
import os

import pandas as pd

DATA_DIR = "data"

TOTAL_USERS = 10500
TOTAL_CONNECT_LICENCES = 10000
TOTAL_WORKBENCH_LICENCES = 5000

USAGE_LOG_PATH = os.path.join(DATA_DIR, "usage_log.json")

# Load unified usage log from JSON (fields match the source API)
usage_log = pd.read_json(USAGE_LOG_PATH, convert_dates=["last_seen"])
# Each record is a login event; derive logins by counting occurrences
usage_log["logins"] = 1

# Dynamic total users derived from the data (unique user_name)
TOTAL_USERS = usage_log["user_name"].nunique()

# Validate single tenancy/product per user to fail fast on bad inputs
_counts = usage_log.groupby("user_name").agg(tenancies=("tenancy", "nunique"), products=("product", "nunique"))
if (_counts["tenancies"] > 1).any() or (_counts["products"] > 1).any():
    raise ValueError("Each user_name must map to exactly one tenancy and one product in usage_log.json")

# Defaults for date range based on usage log
max_date = usage_log["last_seen"].max().normalize()
min_date = usage_log["last_seen"].min().normalize()
default_end = max_date.date()
default_start = (max_date - timedelta(days=29)).date()


def tenancy_choices():
    all_vals = sorted(usage_log["tenancy"].unique())
    return ["All Tenancies"] + all_vals


def environment_choices():
    base = ["Production", "Development", "Staging"]
    data_vals = sorted(usage_log["product"].unique())
    merged = []
    for val in base + list(data_vals):
        if val not in merged:
            merged.append(val)
    return ["All Environments"] + merged


def component_choices():
    data_vals = sorted(usage_log["component"].unique())
    return ["All Components"] + list(data_vals)


# Derived users summary (per user)
users = (
    usage_log.groupby(["user_name", "tenancy", "component", "product"], as_index=False)
    .agg(
        lastLogin=("last_seen", "max"),
        loginCount=("logins", "sum"),
    )
    .rename(columns={"user_name": "userId", "product": "environment"})
)

# Derived tenancies summary
tenancies = (
    usage_log.groupby(["tenancy", "component"], as_index=False)
    .agg(
        activeUsers=("user_name", "nunique"),
        totalLogins=("logins", "sum"),
    )
)
tenancies["growth"] = 0.0  # placeholder
tenancies["workbenchUsers"] = tenancies.apply(
    lambda r: r["activeUsers"] if r["component"] == "Workbench" else 0, axis=1
)
tenancies["connectUsers"] = tenancies.apply(
    lambda r: r["activeUsers"] if r["component"] == "Connect" else 0, axis=1
)

# Derived licences (approximate: assigned equals unique users per tenancy/component)
licences = (
    usage_log.groupby(["tenancy", "component"])["user_name"]
    .nunique()
    .reset_index()
    .rename(columns={"user_name": "licencesUsed"})
)
