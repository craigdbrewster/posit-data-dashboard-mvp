from datetime import timedelta

import pandas as pd

DATA_DIR = "data"

TOTAL_USERS = 10500
TOTAL_CONNECT_LICENCES = 10000
TOTAL_WORKBENCH_LICENCES = 5000
NEW_USERS = 50  # static for MVP


# Load datasets once for app lifetime
users = pd.read_csv(f"{DATA_DIR}/users.csv")
tenancies = pd.read_csv(f"{DATA_DIR}/tenancies.csv")
licences = pd.read_csv(f"{DATA_DIR}/licences.csv")
timeseries = pd.read_csv(f"{DATA_DIR}/timeseries.csv")

# Parse dates
users["lastLogin"] = pd.to_datetime(users["lastLogin"])
timeseries["date"] = pd.to_datetime(timeseries["date"])

# Convenience: session hours per day based on guide
timeseries["sessionHours"] = timeseries["activeUsers"] * 8.5

# Defaults for date range
max_date = timeseries["date"].max()
min_date = timeseries["date"].min()
default_end = max_date.date()
default_start = (max_date - timedelta(days=29)).date()


def tenancy_choices():
    all_vals = sorted(users["tenancy"].unique())
    return ["All Tenancies"] + all_vals


def environment_choices():
    # Base list from guide, merged with whatever is in the data
    base = ["Production", "Development", "Staging"]
    data_vals = sorted(users["environment"].unique())
    merged = []
    for val in base + list(data_vals):
        if val not in merged:
            merged.append(val)
    return ["All Environments"] + merged


def component_choices():
    data_vals = sorted(
        pd.concat([users["component"], licences["component"]]).unique()
    )
    return ["All Components"] + list(data_vals)
