from datetime import timedelta
import os

import pandas as pd

DATA_DIR = "data"

TOTAL_USERS = 10500
TOTAL_CONNECT_LICENCES = 10000
TOTAL_WORKBENCH_LICENCES = 5000
NEW_USERS = 50  # static for MVP

USAGE_LOG_PATH = os.path.join(DATA_DIR, "usage_log.json")

# Load unified usage log from JSON and normalize column names
raw_log = pd.read_json(USAGE_LOG_PATH, convert_dates=["last_seen"])
usage_log = raw_log.rename(
    columns={
        "user_name": "user_id",
        "product": "environment",
        "last_seen": "login_time",
    }
)
# Each record is a login event; derive logins by counting occurrences
usage_log["logins"] = 1

# Defaults for date range based on usage log
max_date = usage_log["login_time"].max().normalize()
min_date = usage_log["login_time"].min().normalize()
default_end = max_date.date()
default_start = (max_date - timedelta(days=29)).date()


def tenancy_choices():
    all_vals = sorted(usage_log["tenancy"].unique())
    return ["All Tenancies"] + all_vals


def environment_choices():
    base = ["Production", "Development", "Staging"]
    data_vals = sorted(usage_log["environment"].unique())
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
    usage_log.groupby(
        ["user_id", "tenancy", "component", "environment"], as_index=False
    )
    .agg(
        lastLogin=("login_time", "max"),
        loginCount=("logins", "sum"),
    )
    .rename(columns={"user_id": "userId"})
)

# Derived tenancies summary
tenancies = (
    usage_log.groupby(["tenancy", "component"], as_index=False)
    .agg(
        activeUsers=("user_id", "nunique"),
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
    usage_log.groupby(["tenancy", "component"])["user_id"]
    .nunique()
    .reset_index()
    .rename(columns={"user_id": "licencesUsed"})
)

# Derived timeseries (daily)
timeseries = (
    usage_log.assign(date=usage_log["login_time"].dt.normalize())
    .groupby("date", as_index=False)
    .agg(
        activeUsers=("user_id", "nunique"),
        regularUsers=("user_id", "nunique"),
        powerUsers=("user_id", "nunique"),
        totalLogins=("logins", "sum"),
    )
)
