from datetime import date, datetime, timedelta

import pandas as pd
from shiny import App, ui, render, reactive
import plotly.express as px

# -------------------------------------------------------------------
# Data loading
# -------------------------------------------------------------------

DATA_DIR = "data"

TOTAL_USERS = 10500
TOTAL_CONNECT_LICENCES = 10000
TOTAL_WORKBENCH_LICENCES = 5000
NEW_USERS = 50  # static for MVP

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


# -------------------------------------------------------------------
# UI
# -------------------------------------------------------------------

app_ui = ui.page_fluid(
    ui.h1("Posit Platform Analytics", class_="mt-3"),
    ui.p(
        "Track platform adoption and engagement. Use the filters below to slice by tenancy, "
        "environment, component, and period."
    ),
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_select(
                "tenancy",
                "Tenancy",
                choices=tenancy_choices(),
                selected="All Tenancies",
            ),
            ui.input_select(
                "environment",
                "Environment",
                choices=environment_choices(),
                selected="All Environments",
            ),
            ui.input_select(
                "component",
                "Component",
                choices=component_choices(),
                selected="All Components",
            ),
            ui.input_date_range(
                "dates",
                "Date range",
                start=default_start,
                end=default_end,
                min=min_date.date(),
                max=max_date.date(),
            ),
            open="always",
        ),
        ui.navset_tab(
            # -------------------- Overview --------------------
            ui.nav_panel(
                "Overview",
                ui.layout_column_wrap(
                    ui.card(
                        ui.card_header("Total users"),
                        ui.h3(TOTAL_USERS),
                    ),
                    ui.card(
                        ui.card_header("Active users"),
                        ui.output_text("overview_active_users"),
                        ui.div(
                            {"class": "text-muted"},
                            ui.output_text("overview_active_users_change"),
                        ),
                    ),
                    ui.card(
                        ui.card_header("New users"),
                        ui.h3(NEW_USERS),
                        ui.div({"class": "text-muted"}, "Static for MVP"),
                    ),
                    width=3,
                ),
                ui.layout_column_wrap(
                    ui.card(
                        ui.card_header("Active users & session hours by week"),
                        ui.output_plot("overview_timeseries"),
                    ),
                    ui.card(
                        ui.card_header("Active users & session hours by tenancy"),
                        ui.output_plot("overview_tenancy_bars"),
                    ),
                    width=2,
                ),
            ),
            # -------------------- Licences --------------------
            ui.nav_panel(
                "Licences",
                ui.layout_column_wrap(
                    ui.card(
                        ui.card_header("Connect licences used"),
                        ui.output_text("lic_connect_summary"),
                    ),
                    ui.card(
                        ui.card_header("Workbench licences used"),
                        ui.output_text("lic_workbench_summary"),
                    ),
                    width=2,
                ),
                ui.card(
                    ui.card_header("Licence usage by tenancy & component"),
                    ui.output_table("lic_table"),
                ),
            ),
            # -------------------- Users --------------------
            ui.nav_panel(
                "Users",
                ui.layout_column_wrap(
                    ui.card(
                        ui.card_header("Daily users"),
                        ui.output_text("users_daily"),
                    ),
                    ui.card(
                        ui.card_header("Weekly users"),
                        ui.output_text("users_weekly"),
                    ),
                    ui.card(
                        ui.card_header("Active users in period"),
                        ui.output_text("users_active"),
                    ),
                    ui.card(
                        ui.card_header("Dormant users"),
                        ui.output_text("users_dormant"),
                    ),
                    width=4,
                ),
                ui.layout_column_wrap(
                    ui.card(
                        ui.card_header("Usage distribution"),
                        ui.output_plot("users_distribution"),
                    ),
                    ui.card(
                        ui.card_header("Session metrics"),
                        ui.tags.ul(
                            ui.tags.li(
                                "Average session length: 45 minutes (+7.1% vs previous)"
                            ),
                            ui.tags.li(
                                "Average sessions per user: 8.5 (+9.0% vs previous)"
                            ),
                        ),
                    ),
                    width=2,
                ),
                ui.card(
                    ui.card_header("User details"),
                    ui.output_table("users_table"),
                ),
            ),
            # -------------------- Tenancies --------------------
            ui.nav_panel(
                "Tenancies",
                ui.card(
                    ui.card_header("Tenancy summary"),
                    ui.output_table("tenancies_table"),
                ),
            ),
        ),
    ),
)


# -------------------------------------------------------------------
# Server logic
# -------------------------------------------------------------------

def server(input, output, session):
    # --- reactive helpers -------------------------------------------------

    @reactive.Calc
    def current_period():
        start, end = input.dates()
        if isinstance(start, date):
            start = datetime.combine(start, datetime.min.time())
        if isinstance(end, date):
            end = datetime.combine(end, datetime.max.time())
        return start, end

    @reactive.Calc
    def comparison_period():
        # As per guide: same length, immediately before current
        start, end = current_period()
        day_diff = (end - start).days
        comp_end = start - timedelta(days=1)
        comp_start = start - timedelta(days=day_diff + 1)
        return comp_start, comp_end

    @reactive.Calc
    def filtered_users():
        tenancy_val = input.tenancy()
        env_val = input.environment()
        comp_val = input.component()
        start, end = current_period()

        df = users.copy()

        if tenancy_val != "All Tenancies":
            df = df[df["tenancy"] == tenancy_val]

        if env_val != "All Environments":
            df = df[df["environment"] == env_val]

        if comp_val != "All Components":
            df = df[df["component"] == comp_val]

        df = df[(df["lastLogin"] >= start) & (df["lastLogin"] <= end)]
        return df

    @reactive.Calc
    def filtered_users_prev_period():
        tenancy_val = input.tenancy()
        env_val = input.environment()
        comp_val = input.component()
        start, end = comparison_period()

        df = users.copy()

        if tenancy_val != "All Tenancies":
            df = df[df["tenancy"] == tenancy_val]

        if env_val != "All Environments":
            df = df[df["environment"] == env_val]

        if comp_val != "All Components":
            df = df[df["component"] == comp_val]

        df = df[(df["lastLogin"] >= start) & (df["lastLogin"] <= end)]
        return df

    @reactive.Calc
    def filtered_timeseries():
        start, end = current_period()
        df = timeseries[(timeseries["date"] >= start) & (timeseries["date"] <= end)].copy()
        return df

    # ------------------------------------------------------------------
    # Overview tab
    # ------------------------------------------------------------------

    @output
    @render.text
    def overview_active_users():
        # Active users = distinct users with lastLogin in current period (with filters)
        return f"{len(filtered_users()):,}"

    @output
    @render.text
    def overview_active_users_change():
        current = len(filtered_users())
        prev = len(filtered_users_prev_period())
        if prev > 0:
            change = (current - prev) / prev * 100
        else:
            change = 0.0
        arrow = "▲" if change >= 0 else "▼"
        return f"{arrow} {change:.1f}% vs previous period"

    @output
    @render.plot
    def overview_timeseries():
        df = filtered_timeseries()
        if df.empty:
            return px.line(title="No data for selected period")

        # Weekly aggregation (guide)
        df_weekly = (
            df.set_index("date")
            .resample("W-MON")
            .agg({"activeUsers": "mean", "sessionHours": "sum"})
            .reset_index()
        )
        df_weekly["week"] = df_weekly["date"].dt.date

        fig = px.line(
            df_weekly,
            x="week",
            y=["activeUsers", "sessionHours"],
            markers=True,
            labels={"value": "Value", "week": "Week", "variable": "Metric"},
        )
        fig.update_layout(legend_title_text="Metric")
        return fig

    @output
    @render.plot
    def overview_tenancy_bars():
        # Use tenancy snapshot for "by tenancy" bar chart
        df = tenancies.copy()
        df["sessionHours"] = df["activeUsers"] * 8.5
        df = df.sort_values("activeUsers", ascending=False).head(5)

        fig = px.bar(
            df,
            x="tenancy",
            y=["activeUsers", "sessionHours"],
            barmode="group",
            labels={"value": "Value", "tenancy": "Tenancy", "variable": "Metric"},
        )
        fig.update_layout(legend_title_text="Metric")
        return fig

    # ------------------------------------------------------------------
    # Licences tab
    # ------------------------------------------------------------------

    def _licence_active_users_for_period(start: datetime, end: datetime):
        tenancy_val = input.tenancy()
        comp_val = input.component()

        df = users.copy()
        if tenancy_val != "All Tenancies":
            df = df[df["tenancy"] == tenancy_val]
        if comp_val != "All Components":
            df = df[df["component"] == comp_val]

        df = df[(df["lastLogin"] >= start) & (df["lastLogin"] <= end)]
        # active licences = active users in period per component
        connect_active = len(df[df["component"] == "Connect"])
        workbench_active = len(df[df["component"] == "Workbench"])
        return connect_active, workbench_active

    @output
    @render.text
    def lic_connect_summary():
        tenancy_val = input.tenancy()
        comp_val = input.component()
        # filter licences snapshot
        lic_df = licences.copy()
        if tenancy_val != "All Tenancies":
            lic_df = lic_df[lic_df["tenancy"] == tenancy_val]
        if comp_val != "All Components":
            lic_df = lic_df[lic_df["component"] == comp_val]

        connect_assigned = lic_df.loc[
            lic_df["component"] == "Connect", "licencesUsed"
        ].sum()
        current_start, current_end = current_period()
        prev_start, prev_end = comparison_period()
        connect_active_current, _ = _licence_active_users_for_period(
            current_start, current_end
        )
        connect_active_prev, _ = _licence_active_users_for_period(
            prev_start, prev_end
        )

        if connect_active_prev > 0:
            change = (connect_active_current - connect_active_prev) / connect_active_prev * 100
        else:
            change = 0.0
        arrow = "▲" if change >= 0 else "▼"

        return (
            f"{connect_active_current:,} active of {connect_assigned:,} assigned "
            f"(total capacity {TOTAL_CONNECT_LICENCES:,}) — {arrow} {change:.1f}% vs previous"
        )

    @output
    @render.text
    def lic_workbench_summary():
        tenancy_val = input.tenancy()
        comp_val = input.component()
        lic_df = licences.copy()
        if tenancy_val != "All Tenancies":
            lic_df = lic_df[lic_df["tenancy"] == tenancy_val]
        if comp_val != "All Components":
            lic_df = lic_df[lic_df["component"] == comp_val]

        workbench_assigned = lic_df.loc[
            lic_df["component"] == "Workbench", "licencesUsed"
        ].sum()
        current_start, current_end = current_period()
        prev_start, prev_end = comparison_period()
        _, workbench_active_current = _licence_active_users_for_period(
            current_start, current_end
        )
        _, workbench_active_prev = _licence_active_users_for_period(
            prev_start, prev_end
        )

        if workbench_active_prev > 0:
            change = (workbench_active_current - workbench_active_prev) / workbench_active_prev * 100
        else:
            change = 0.0
        arrow = "▲" if change >= 0 else "▼"

        return (
            f"{workbench_active_current:,} active of {workbench_assigned:,} assigned "
            f"(total capacity {TOTAL_WORKBENCH_LICENCES:,}) — {arrow} {change:.1f}% vs previous"
        )

    @output
    @render.table
    def lic_table():
        tenancy_val = input.tenancy()
        comp_val = input.component()

        # Start from snapshot for assigned licences
        lic_df = licences.copy()
        if tenancy_val != "All Tenancies":
            lic_df = lic_df[lic_df["tenancy"] == tenancy_val]
        if comp_val != "All Components":
            lic_df = lic_df[lic_df["component"] == comp_val]

        current_start, current_end = current_period()
        df_users = users[
            (users["lastLogin"] >= current_start)
            & (users["lastLogin"] <= current_end)
        ]
        if tenancy_val != "All Tenancies":
            df_users = df_users[df_users["tenancy"] == tenancy_val]
        if comp_val != "All Components":
            df_users = df_users[df_users["component"] == comp_val]

        active_counts = (
            df_users.groupby(["tenancy", "component"])["userId"]
            .nunique()
            .reset_index(name="activeLicences")
        )

        merged = lic_df.merge(
            active_counts,
            on=["tenancy", "component"],
            how="left",
        ).fillna({"activeLicences": 0})

        out = merged[["tenancy", "component", "licencesUsed", "activeLicences"]].copy()
        out = out.rename(
            columns={
                "tenancy": "Tenancy",
                "component": "Component",
                "licencesUsed": "Assigned licences",
                "activeLicences": "Active licences",
            }
        )

        # Totals per component
        totals = (
            out.groupby("Component")[["Assigned licences", "Active licences"]]
            .sum()
            .reset_index()
        )
        totals["Tenancy"] = "Total"

        final = pd.concat([out, totals], ignore_index=True)
        final = final[["Tenancy", "Component", "Assigned licences", "Active licences"]]
        return final.sort_values(["Tenancy", "Component"])

    # ------------------------------------------------------------------
    # Users tab
    # ------------------------------------------------------------------

    @output
    @render.text
    def users_active():
        return f"{len(filtered_users()):,}"

    @output
    @render.text
    def users_dormant():
        dormant = TOTAL_USERS - len(filtered_users())
        return f"{dormant:,}"

    @output
    @render.text
    def users_daily():
        # Use powerUsers from latest date in period as proxy for "daily users"
        df = filtered_timeseries()
        if df.empty:
            return "0"
        latest = df.sort_values("date").iloc[-1]
        return f"{int(latest['powerUsers']):,}"

    @output
    @render.text
    def users_weekly():
        df = filtered_timeseries()
        if df.empty:
            return "0"
        latest = df.sort_values("date").iloc[-1]
        return f"{int(latest['regularUsers']):,}"

    @output
    @render.plot
    def users_distribution():
        df = filtered_timeseries()
        if df.empty:
            return px.pie(title="No data for selected period")

        latest = df.sort_values("date").iloc[-1]
        dist = pd.DataFrame(
            {
                "segment": ["Daily", "Weekly", "Light", "Dormant"],
                "users": [
                    latest["powerUsers"],
                    latest["regularUsers"],
                    latest["lightUsers"],
                    latest["dormantUsers"],
                ],
            }
        )
        fig = px.bar(
            dist,
            x="segment",
            y="users",
            text="users",
            labels={"users": "Users"},
        )
        fig.update_traces(textposition="outside")
        return fig

    @output
    @render.table
    def users_table():
        df = filtered_users().copy()
        if df.empty:
            # Return an empty frame with the correct columns so the table still renders
            return pd.DataFrame(
                columns=["userId", "tenancy", "component", "environment", "lastLogin", "loginCount"]
            )

        df = df.sort_values("lastLogin", ascending=False)
        return df[["userId", "tenancy", "component", "environment", "lastLogin", "loginCount"]]

    # ------------------------------------------------------------------
    # Tenancies tab
    # ------------------------------------------------------------------

    @output
    @render.table
    def tenancies_table():
        tenancy_val = input.tenancy()
        comp_val = input.component()
        start, end = current_period()

        df_users = users[(users["lastLogin"] >= start) & (users["lastLogin"] <= end)]

        if tenancy_val != "All Tenancies":
            df_users = df_users[df_users["tenancy"] == tenancy_val]
        if comp_val != "All Components":
            df_users = df_users[df_users["component"] == comp_val]

        # total and active users per tenancy & component
        total_per_tenancy_comp = (
            users.groupby(["tenancy", "component"])["userId"]
            .nunique()
            .reset_index(name="totalUsers")
        )
        active_per_tenancy_comp = (
            df_users.groupby(["tenancy", "component"])["userId"]
            .nunique()
            .reset_index(name="activeUsersComponent")
        )
        merged = total_per_tenancy_comp.merge(
            active_per_tenancy_comp, on=["tenancy", "component"], how="left"
        ).fillna({"activeUsersComponent": 0})

        # pivot into columns for Connect / Workbench
        pivot = merged.pivot_table(
            index="tenancy",
            columns="component",
            values=["totalUsers", "activeUsersComponent"],
            fill_value=0,
        )
        pivot.columns = [
            f"{metric}_{component}" for metric, component in pivot.columns.to_flat_index()
        ]
        pivot = pivot.reset_index()

        # add licence snapshot for assigned counts
        lic_pivot = licences.pivot_table(
            index="tenancy",
            columns="component",
            values="licencesUsed",
            fill_value=0,
        )
        lic_pivot.columns = [f"licences_{c}" for c in lic_pivot.columns.to_list()]
        lic_pivot = lic_pivot.reset_index()

        out = pivot.merge(lic_pivot, on="tenancy", how="left").fillna(0)

        # Build final display frame to match guide
        def get(col, default=0):
            return out[col] if col in out.columns else default

        display = pd.DataFrame(
            {
                "Tenancy": out["tenancy"],
                "Total users": get("totalUsers_Connect")
                + get("totalUsers_Workbench"),
                "Active users": get("activeUsersComponent_Connect")
                + get("activeUsersComponent_Workbench"),
                "Assigned Connect": get("licences_Connect"),
                "Active Connect": get("activeUsersComponent_Connect"),
                "Assigned Workbench": get("licences_Workbench"),
                "Active Workbench": get("activeUsersComponent_Workbench"),
            }
        )

        return display.sort_values("Tenancy")


app = App(app_ui, server)
