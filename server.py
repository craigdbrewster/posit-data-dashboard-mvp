from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
from shiny import reactive, render, ui

import data

# Static frequency buckets for display and comparison
FREQUENCY_CURRENT = {
    "10_plus": 2100,
    "5_9": 4100,
    "1_4": 1900,
    "lt1": 1000,
    "no_activity": 900,
}
FREQUENCY_PREV = FREQUENCY_CURRENT.copy()


def render_plotly(fig):
    """Render a Plotly figure as HTML for Shiny @render.ui."""
    html_str = fig.to_html(include_plotlyjs="require", div_id=f"plot-{id(fig)}")
    return ui.HTML(html_str)


def format_change(current: float, previous: float) -> str:
    """Return formatted percentage change with arrow."""
    if previous > 0:
        change = (current - previous) / previous * 100
    else:
        change = 0.0 if current == 0 else 100.0
    arrow = "▲" if change >= 0 else "▼"
    return f"{arrow} {change:.1f}%"


def server(input, output, session):
    TARGET_PENETRATION = 0.6  # 60% target
    TARGET_STICKINESS = 0.6
    TARGET_DEPTH_HOURS = 5.0

    # --- reactive helpers -------------------------------------------------

    @reactive.Calc
    def user_component():
        tab = input.main_tabs() if hasattr(input, "main_tabs") else None
        if tab == "connect":
            return "Connect"
        if tab == "workbench":
            return "Workbench"
        return None

    def _licences_available():
        if user_component() == "Connect":
            return data.TOTAL_CONNECT_LICENCES
        if user_component() == "Workbench":
            return data.TOTAL_WORKBENCH_LICENCES
        return data.TOTAL_CONNECT_LICENCES + data.TOTAL_WORKBENCH_LICENCES

    @reactive.Calc
    def current_period():
        tab = input.main_tabs() if hasattr(input, "main_tabs") else None
        if tab == "tenancies":
            start, end = input.tenancy_dates()
        else:
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

    def _aggregate_users(usage: pd.DataFrame) -> pd.DataFrame:
        """Aggregate usage to one row per user with first/last login and summed logins."""
        if usage.empty:
            return pd.DataFrame(
                columns=[
                    "userId",
                    "tenancy",
                    "component",
                    "environment",
                    "firstLogin",
                    "lastLogin",
                    "loginCount",
                ]
            )
        # First login map from all time (respecting current tenancy/env/component filters)
        usage_all = usage_base()
        first_map = (
            usage_all.groupby("user_name")["last_seen"].min()
            if not usage_all.empty
            else pd.Series(dtype="datetime64[ns]")
        )
        # Sum logins per user in the window
        sums = (
            usage.groupby("user_name", as_index=False)["logins"]
            .sum()
            .rename(columns={"user_name": "userId", "logins": "loginCount"})
        )
        # Latest login per user with associated tenancy/component/env
        latest = (
            usage.sort_values("last_seen")
            .groupby("user_name", as_index=False)
            .tail(1)
            .rename(columns={"user_name": "userId", "last_seen": "lastLogin"})
        )
        merged = (
            latest[["userId", "tenancy", "component", "environment", "lastLogin"]]
            .merge(sums, on="userId", how="left")
        )
        merged["firstLogin"] = merged["userId"].map(first_map)
        return merged

    @reactive.Calc
    def filtered_users():
        usage = usage_filtered()
        return _aggregate_users(usage)

    @reactive.Calc
    def filtered_users_prev_period():
        start, end = comparison_period()
        usage = usage_base()
        usage = usage[(usage["last_seen"] >= start) & (usage["last_seen"] <= end)]
        return _aggregate_users(usage)

    def _timeseries_for_range(start, end):
        """Aggregate usage into a daily timeseries for a given date window and current filters."""
        usage = usage_base()
        usage = usage[
            (usage["last_seen"] >= start) & (usage["last_seen"] <= end)
        ].copy()
        if usage.empty:
            return pd.DataFrame(
                columns=["date", "activeUsers", "regularUsers", "powerUsers", "totalLogins"]
            )
        df = (
            usage.assign(date=usage["last_seen"].dt.normalize())
            .groupby("date", as_index=False)
            .agg(
                activeUsers=("user_name", "nunique"),
                regularUsers=("user_name", "nunique"),
                powerUsers=("user_name", "nunique"),
                totalLogins=("logins", "sum"),
            )
        )
        return df

    @reactive.Calc
    def filtered_timeseries():
        start, end = current_period()
        return _timeseries_for_range(start, end)

    def usage_base(
        tenancy_val=None,
        env_val=None,
        comp_val=None,
    ):
        """
        Apply tenancy/environment/component filters to the unified log.
        Defaults pull from current inputs when not provided.
        """
        usage = data.usage_log.copy()
        tenancy_val = tenancy_val if tenancy_val is not None else input.tenancy()
        env_val = env_val if env_val is not None else input.environment()
        comp_val = comp_val if comp_val is not None else user_component()
        if tenancy_val != "All Tenancies":
            usage = usage[usage["tenancy"] == tenancy_val]
        if env_val != "All Environments":
            usage = usage[usage["product"] == env_val]
        if comp_val and comp_val != "All Components":
            usage = usage[usage["component"] == comp_val]
        return usage

    def usage_filtered():
        start, end = current_period()
        usage = usage_base()
        usage = usage[
            (usage["last_seen"] >= start) & (usage["last_seen"] <= end)
        ].copy()
        return usage

    @reactive.Calc
    def user_scope_cumulative_current():
        """Unique users up to end of current period (respecting filters)."""
        _, end = current_period()
        usage = usage_base()
        usage = usage[usage["last_seen"] <= end]
        return set(usage["user_name"].unique())

    @reactive.Calc
    def user_scope_cumulative_previous():
        """Unique users up to end of comparison period (respecting filters)."""
        _, comp_end = comparison_period()
        usage = usage_base()
        usage = usage[usage["last_seen"] <= comp_end]
        return set(usage["user_name"].unique())

    @reactive.Calc
    def user_scope_current():
        """Unique users with activity in the current period."""
        return set(usage_filtered()["user_name"].unique())

    @reactive.Calc
    def user_scope_previous():
        """Unique users with activity in the comparison period (same length as current)."""
        start, end = comparison_period()
        usage = usage_base()
        usage = usage[(usage["last_seen"] >= start) & (usage["last_seen"] <= end)]
        return set(usage["user_name"].unique())

    @reactive.Calc
    def total_users_cumulative():
        """
        Total unique users up to the end of the current period (respecting filters).
        """
        return len(user_scope_cumulative_current())

    @reactive.Calc
    def active_users_current():
        """Unique users with activity in the current period (respecting filters)."""
        return len(user_scope_current())

    def first_seen_series():
        """First login per user for current tenancy/env/component filters."""
        usage = usage_base()
        if usage.empty:
            return pd.Series(dtype="datetime64[ns]")
        return usage.groupby("user_name")["last_seen"].min()

    @reactive.Calc
    def tenancy_usage_base():
        """Base usage for Tenancies tab using its environment selector."""
        env_val = input.tenancy_environment()
        return usage_base(env_val=env_val, tenancy_val="All Tenancies", comp_val=None)

    @reactive.Calc
    def tenancy_usage():
        start, end = current_period()
        usage = tenancy_usage_base()
        usage = usage[
            (usage["last_seen"] >= start) & (usage["last_seen"] <= end)
        ].copy()
        return usage


    @reactive.Calc
    def filtered_users_by_pid():
        """Filter users table by PID search."""
        df = filtered_users().copy()
        pid_search = input.pid_search()
        if pid_search and pid_search.strip():
            df = df[df["userId"].str.contains(pid_search.strip(), case=False, na=False)]
        return df

    @reactive.Calc
    def new_users_current():
        start, end = current_period()
        first_seen = first_seen_series()
        new_ids = first_seen[(first_seen >= start) & (first_seen <= end)].index
        return len(new_ids)

    @reactive.Calc
    def new_users_previous():
        comp_start, comp_end = comparison_period()
        first_seen = first_seen_series()
        new_ids = first_seen[(first_seen >= comp_start) & (first_seen <= comp_end)].index
        return len(new_ids)

    @reactive.Calc
    def daily_active_users_current():
        """Users logging in at least once per day in current period (approx)."""
        return len(filtered_users())

    @reactive.Calc
    def weekly_active_users_current():
        """Users logging in at least once per week in current period (approx)."""
        return len(filtered_users())

    @reactive.Calc
    def any_login_users_current():
        """Users logging in at least once in current period."""
        return len(filtered_users())

    @reactive.Calc
    def not_logged_in_current():
        """Users from the filtered population with no logins in the current period."""
        total_scope = user_scope_cumulative_current()
        return max(len(total_scope - user_scope_current()), 0)

    @reactive.Calc
    def sessions_per_user_current():
        """Average sessions per user in current period (estimate from data)."""
        df = filtered_timeseries()
        num_users = len(filtered_users())
        if df.empty or num_users == 0:
            return 0.0
        avg_active_users_per_day = (
            df["activeUsers"].mean() if "activeUsers" in df.columns else 0
        )
        return avg_active_users_per_day if avg_active_users_per_day > 0 else 0.0

    @reactive.Calc
    def sessions_per_user_previous():
        """Average sessions per user in comparison period."""
        start, end = comparison_period()
        df = _timeseries_for_range(start, end)
        df_users = filtered_users_prev_period()
        if df.empty or len(df_users) == 0:
            return 0.0
        avg_active_users_per_day = (
            df["activeUsers"].mean() if "activeUsers" in df.columns else 0
        )
        return avg_active_users_per_day if avg_active_users_per_day > 0 else 0.0

    # ------------------------------------------------------------------
    # Overview tab
    # ------------------------------------------------------------------

    @output
    @render.text
    def overview_active_users():
        return f"{active_users_current():,}"

    @output
    @render.text
    def overview_total_users_change():
        current = len(user_scope_cumulative_current())
        prev = len(user_scope_cumulative_previous())
        if prev > 0:
            change = (current - prev) / prev * 100
        else:
            change = 0.0
        arrow = "▲" if change >= 0 else "▼"
        return f"{arrow} {change:.1f}% vs previous period"

    # ------------------------------------------------------------------
    # RAG cards (snapshot)
    # ------------------------------------------------------------------

    @output
    @render.text
    def overview_active_users_change():
        current = active_users_current()
        prev = len(filtered_users_prev_period())
        if prev > 0:
            change = (current - prev) / prev * 100
        else:
            change = 0.0
        arrow = "▲" if change >= 0 else "▼"
        return f"{arrow} {change:.1f}% vs previous period"

    @output
    @render.text
    def overview_new_users():
        return f"{new_users_current():,}"

    @output
    @render.text
    def overview_new_users_change():
        current = new_users_current()
        prev = new_users_previous()
        if prev > 0:
            change = (current - prev) / prev * 100
        else:
            change = 0.0 if current == 0 else 100.0
        arrow = "▲" if change >= 0 else "▼"
        return f"{arrow} {change:.1f}% vs previous period"

    @output
    @render.text
    def overview_penetration():
        df = filtered_timeseries()
        if df.empty:
            return "0.0%"
        latest = df.sort_values("date").iloc[-1]
        weekly_active = latest.get("regularUsers", 0)
        penetration = weekly_active / data.TOTAL_USERS * 100 if data.TOTAL_USERS else 0
        return f"{penetration:.1f}%"

    @output
    @render.text
    def overview_stickiness():
        df = filtered_timeseries()
        if df.empty:
            return "0.0%"
        latest = df.sort_values("date").iloc[-1]
        weekly_active = latest.get("regularUsers", 0)
        period_active = latest.get("activeUsers", 0)
        stickiness = weekly_active / period_active * 100 if period_active else 0
        return f"{stickiness:.1f}%"

    @output
    @render.text
    def overview_active_users_weekly():
        df = filtered_timeseries()
        if df.empty:
            return "0"
        df_weekly = (
            df.set_index("date")
            .resample("W-MON")
            .agg({"activeUsers": "mean"})
            .reset_index()
        )
        latest = df_weekly.sort_values("date").iloc[-1]
        return f"{int(latest['activeUsers']):,}"

    @output
    @render.text
    def overview_active_users_weekly_change():
        df = filtered_timeseries()
        if df.empty:
            return ""
        df_weekly = (
            df.set_index("date")
            .resample("W-MON")
            .agg({"activeUsers": "mean"})
            .reset_index()
        )
        if len(df_weekly) < 2:
            return ""
        latest = df_weekly.sort_values("date").iloc[-1]["activeUsers"]
        prev = df_weekly.sort_values("date").iloc[-2]["activeUsers"]
        change = (latest - prev) / prev * 100 if prev else 0
        arrow = "▲" if change >= 0 else "▼"
        return f"{arrow} {change:.1f}% vs prev week"

    @output
    @render.ui
    def overview_engagement_trend():
        df = filtered_timeseries()
        if df.empty:
            fig = px.line(title="No data for selected period")
            return render_plotly(fig)

        df_weekly = (
            df.set_index("date")
            .resample("W-MON")
            .agg({"activeUsers": "mean", "regularUsers": "mean"})
            .reset_index()
        )
        df_weekly["week"] = df_weekly["date"].dt.date
        df_weekly["penetration"] = df_weekly["regularUsers"] / data.TOTAL_USERS * 100

        fig = px.line(
            df_weekly,
            x="week",
            y=["activeUsers", "penetration"],
            markers=True,
            labels={
                "value": "Value",
                "variable": "Metric",
                "week": "Week",
                "activeUsers": "Active users (mean)",
                "penetration": "Penetration (%)",
            },
        )
        fig.update_traces(mode="lines+markers")
        fig.update_layout(legend_title_text="")
        return render_plotly(fig)

    # ------------------------------------------------------------------
    # Users tab
    # ------------------------------------------------------------------

    @output
    @render.text
    def users_total():
        _, end = current_period()
        return f"{total_users_cumulative():,}"

    @output
    @render.text
    def users_active():
        return f"{active_users_current():,}"

    @output
    @render.text
    def users_active_change():
        cur_active = active_users_current()
        prev_active = len(filtered_users_prev_period())
        if prev_active == 0:
            return "▲ 0.0% vs previous period"
        change = (cur_active - prev_active) / prev_active * 100
        arrow = "▲" if change >= 0 else "▼"
        return f"{arrow} {change:.1f}% vs previous period"

    @output
    @render.text
    def licences_available():
        return f"{_licences_available():,}"

    @output
    @render.text
    def users_inactive():
        return f"{not_logged_in_current():,}"

    @output
    @render.text
    def users_inactive_change():
        # Compare inactive users between current and previous date windows
        total_scope_current = len(user_scope_cumulative_current())
        total_scope_prev = len(user_scope_cumulative_previous())
        prev_active = len(user_scope_previous())
        prev_inactive = max(total_scope_prev - prev_active, 0)
        current = max(total_scope_current - len(user_scope_current()), 0)
        if prev_inactive == 0:
            change = 0.0 if current == 0 else 100.0
        else:
            change = (current - prev_inactive) / prev_inactive * 100
        arrow = "▲" if change >= 0 else "▼"
        return f"{arrow} {change:.1f}% vs previous period"

    @output
    @render.text
    def users_dormant():
        return "900"

    @output
    @render.text
    def users_dormant_change():
        return ""

    @output
    @render.text
    def users_daily():
        df = filtered_timeseries()
        if df.empty:
            return "0"
        latest = df.sort_values("date").iloc[-1]
        return f"{int(latest['powerUsers']):,}"

    @output
    @render.text
    def users_daily_change():
        df_current = filtered_timeseries()
        if df_current.empty:
            return ""
        latest_current = df_current.sort_values("date").iloc[-1]
        daily_current = latest_current["powerUsers"]

        prev_start, prev_end = comparison_period()
        df_prev = _timeseries_for_range(prev_start, prev_end)
        if df_prev.empty:
            return ""
        latest_prev = df_prev.sort_values("date").iloc[-1]
        daily_prev = latest_prev["powerUsers"]

        if daily_prev > 0:
            change = (daily_current - daily_prev) / daily_prev * 100
        else:
            change = 0.0
        arrow = "▲" if change >= 0 else "▼"
        return f"{arrow} {change:.1f}% vs previous period"

    @output
    @render.text
    def users_weekly():
        df = filtered_timeseries()
        if df.empty:
            return "0"
        latest = df.sort_values("date").iloc[-1]
        return f"{int(latest['regularUsers']):,}"

    @output
    @render.text
    def users_weekly_change():
        df_current = filtered_timeseries()
        if df_current.empty:
            return ""
        latest_current = df_current.sort_values("date").iloc[-1]
        weekly_current = latest_current["regularUsers"]

        prev_start, prev_end = comparison_period()
        df_prev = _timeseries_for_range(prev_start, prev_end)
        if df_prev.empty:
            return ""
        latest_prev = df_prev.sort_values("date").iloc[-1]
        weekly_prev = latest_prev["regularUsers"]

        if weekly_prev > 0:
            change = (weekly_current - weekly_prev) / weekly_prev * 100
        else:
            change = 0.0
        arrow = "▲" if change >= 0 else "▼"
        return f"{arrow} {change:.1f}% vs previous period"

    @output
    @render.ui
    def users_distribution():
        return ui.tags.div()

    def _pie_from_series(series, labels_colors):
        counts = []
        labels = []
        colors = []
        for label, lower, upper, color in labels_colors:
            if upper is None:
                mask = series > lower
            else:
                mask = (series >= lower) & (series <= upper)
            counts.append(int(mask.sum()))
            labels.append(label)
            colors.append(color)
        return labels, counts, colors

    @output
    @render.ui
    def users_logins_pie():
        usage = usage_filtered()
        start, end = current_period()
        days = max((end - start).days + 1, 1)
        weeks = max(days / 7, 1)
        if usage.empty:
            return ui.tags.div("No data for selected period", class_="app-muted")

        user_logins = usage.groupby("user_name")["logins"].sum() / weeks
        logins_per_week = user_logins.reindex(user_logins.index, fill_value=0)
        inactive = max(not_logged_in_current(), 0)
        if inactive:
            logins_per_week = pd.concat(
                [logins_per_week, pd.Series([0] * inactive)], ignore_index=True
            )
        labels, counts, colors = _pie_from_series(
            logins_per_week,
            [
                ("More than 10 logins per week", 10, None, "#0b7a0b"),
                ("5 to 9 logins per week", 5, 9.999, "#1d70b8"),
                ("1 to 4 logins per week", 1, 4.999, "#6f777b"),
                ("Less than 1 login per week", 0.01, 0.999, "#b58800"),
                ("No activity", -0.0001, 0.01, "#b56d00"),
            ],
        )
        fig = px.pie(
            names=labels,
            values=counts,
            color=labels,
            color_discrete_map={l: c for l, _, _, c in [
                ("More than 10 logins per week", 10, None, "#0b7a0b"),
                ("5 to 9 logins per week", 5, 9.999, "#1d70b8"),
                ("1 to 4 logins per week", 1, 4.999, "#6f777b"),
                ("Less than 1 login per week", 0.01, 0.999, "#b58800"),
                ("No activity", -0.0001, 0.01, "#b56d00"),
            ]},
        )
        fig.update_layout(showlegend=True)
        return render_plotly(fig)

    @output
    @render.ui
    def users_trend():
        usage = usage_filtered()
        if usage.empty:
            fig = px.line(title="No data for selected period")
            return render_plotly(fig)

        usage = usage.assign(week=usage["last_seen"].dt.to_period("W-MON").dt.start_time)
        weeks = sorted(usage["week"].unique())

        # Active users per week within the selected window
        active_weekly = (
            usage.groupby("week")["user_name"].nunique().reindex(weeks, fill_value=0)
        )

        # Cumulative total users up to each week using all history for the filters
        base_raw = usage_base()
        base = base_raw.assign(week=base_raw["last_seen"].dt.to_period("W-MON").dt.start_time)
        cumulative_totals = []
        for wk in weeks:
            cutoff = wk + pd.Timedelta(days=6)
            cumulative_totals.append(
                base[base["last_seen"] <= cutoff]["user_name"].nunique()
            )

        df_plot = pd.DataFrame(
            {
                "week": weeks,
                "Total users": cumulative_totals,
                "Total active users": active_weekly.values,
            }
        )

        df_plot = df_plot.melt(id_vars="week", var_name="metric", value_name="value")

        fig = px.line(
            df_plot,
            x="week",
            y="value",
            color="metric",
            markers=True,
            labels={"week": "Week", "value": "Users", "metric": "Metric"},
        )
        fig.update_layout(legend_title_text="")
        return render_plotly(fig)

    @output
    @render.ui
    def users_frequency():
        usage = usage_filtered()
        if usage.empty:
            fig = px.line(title="No data for selected period")
            return render_plotly(fig)

        usage = usage.assign(week=usage["last_seen"].dt.to_period("W-MON").dt.start_time)
        df_weekly = (
            usage.groupby("week")
            .agg(
                total_logins=("logins", "sum"),
            )
            .reset_index()
        )

        plot_df = df_weekly.melt(
            id_vars=["week"],
            value_vars=["total_logins"],
            var_name="metric",
            value_name="value",
        )
        plot_df["metric"] = plot_df["metric"].map(
            {"total_logins": "Logins per week"}
        )

        fig = px.line(
            plot_df,
            x="week",
            y="value",
            color="metric",
            markers=True,
            labels={"week": "Week", "value": "Weekly total", "metric": "Metric"},
        )
        fig.update_layout(legend_title_text="")
        return render_plotly(fig)

    @output
    @render.ui
    def users_table():
        df = filtered_users_by_pid().copy()
        start, end = current_period()
        days = max((end - start).days + 1, 1)
        weeks = max(days / 7, 1)
        usage_all = usage_base()
        total_logins_map = (
            usage_all.groupby("user_name")["logins"].sum() if not usage_all.empty else pd.Series(dtype="float")
        )

        def fmt_date(series: pd.Series) -> pd.Series:
            """Return series of date-only strings from datetime-like values."""
            formatted = pd.to_datetime(series, errors="coerce").dt.date.astype(str)
            return formatted.replace("NaT", "")

        if df.empty:
            cols = [
                "PID",
                "Tenancy",
                "Environment",
                "First login",
                "Last login",
                "Total logins\n(date range)",
                "Total logins\n(to date)",
                "Avg logins\n(per week)",
            ]
            empty_df = pd.DataFrame(
                columns=cols
            )
            return ui.HTML(empty_df.to_html(index=False, classes="full-table sortable", border=0))

        df = df.sort_values("lastLogin", ascending=False)
        base_cols = ["userId", "tenancy", "environment", "firstLogin", "lastLogin", "loginCount"]
        out = df[base_cols].copy()
        out = out.rename(
            columns={
                "userId": "PID",
                "tenancy": "Tenancy",
                "environment": "Environment",
                "firstLogin": "First login",
                "lastLogin": "Last login",
                "loginCount": "Total logins\n(date range)",
            }
        )
        out["Total logins\n(to date)"] = out["PID"].map(total_logins_map).fillna(0).astype(int)
        # First login should reflect first-ever login for the filtered population
        out["First login"] = fmt_date(out["First login"])
        out["Last login"] = fmt_date(out["Last login"])
        out["Avg logins\n(per week)"] = (out["Total logins\n(date range)"] / weeks).round(1)
        final_cols = [
            "PID",
            "Tenancy",
            "Environment",
            "First login",
            "Last login",
            "Total logins\n(date range)",
            "Total logins\n(to date)",
            "Avg logins\n(per week)",
        ]
        out = out[final_cols]
        return ui.HTML(out.to_html(index=False, classes="full-table sortable", border=0))

    @output
    @render.download(filename="users.csv")
    def download_users():
        df = filtered_users_by_pid().copy()
        usage_all = usage_base()
        total_logins_map = (
            usage_all.groupby("user_name")["logins"].sum() if not usage_all.empty else pd.Series(dtype="float")
        )
        if df.empty:
            cols = [
                "PID",
                "Tenancy",
                "Environment",
                "First login",
                "Last login",
                "Total logins\n(date range)",
                "Total logins\n(to date)",
                "Avg logins\n(per week)",
            ]
            df = pd.DataFrame(columns=cols)
        else:
            start, end = current_period()
            days = max((end - start).days + 1, 1)
            weeks = max(days / 7, 1)

            def fmt_date(series: pd.Series) -> pd.Series:
                formatted = pd.to_datetime(series, errors="coerce").dt.date.astype(str)
                return formatted.replace("NaT", "")

            df = df.sort_values("lastLogin", ascending=False)
            base_cols = ["userId", "tenancy", "environment", "firstLogin", "lastLogin", "loginCount"]
            df = df[base_cols].copy()
            rename_map = {
                "userId": "PID",
                "tenancy": "Tenancy",
                "environment": "Environment",
                "firstLogin": "First login",
                "lastLogin": "Last login",
                "loginCount": "Total logins\n(date range)",
            }
            df = df.rename(columns=rename_map)
            df["Total logins\n(to date)"] = df["PID"].map(total_logins_map).fillna(0).astype(int)
            df["First login"] = fmt_date(df["First login"])
            df["Last login"] = fmt_date(df["Last login"])
            df["Avg logins\n(per week)"] = (df["Total logins\n(date range)"] / weeks).round(1)
            final_cols = [
                "PID",
                "Tenancy",
                "Environment",
                "First login",
                "Last login",
                "Total logins\n(date range)",
                "Total logins\n(to date)",
                "Avg logins\n(per week)",
            ]
            df = df[final_cols]

        def _writer():
            return df.to_csv(index=False)

        return _writer

    # ------------------------------------------------------------------
    # Tenancies tab (combined licences + activity)
    # ------------------------------------------------------------------

    @output
    @render.ui
    def tenancy_licence_bars():
        usage = tenancy_usage()
        if usage.empty:
            fig = px.bar(title="No data")
            return render_plotly(fig)
        agg = (
            usage.groupby(["tenancy", "component"])["user_name"]
            .nunique()
            .reset_index()
            .rename(columns={"user_name": "Users", "tenancy": "Tenancy", "component": "Component"})
        )
        long = agg
        fig = px.bar(
            long,
            x="Users",
            y="Tenancy",
            color="Component",
            barmode="group",
            orientation="h",
            labels={"Users": "Users"},
        )
        fig.update_layout(legend_title_text="Component")
        return render_plotly(fig)

    @output
    @render.ui
    def tenancy_active_bars():
        usage = tenancy_usage()
        if usage.empty:
            fig = px.bar(title="No data")
            return render_plotly(fig)
        active = (
            usage.groupby(["tenancy", "component"])["user_name"]
            .nunique()
            .reset_index()
            .rename(columns={"user_name": "Users", "tenancy": "Tenancy", "component": "Component"})
        )
        long = active
        fig = px.bar(
            long,
            x="Users",
            y="Tenancy",
            color="Component",
            barmode="group",
            orientation="h",
            labels={"Users": "Users"},
        )
        fig.update_layout(legend_title_text="Component")
        return render_plotly(fig)

    @output
    @render.ui
    def tenancy_logins_bars():
        usage = tenancy_usage()
        if usage.empty:
            fig = px.bar(title="No data")
            return render_plotly(fig)
        logins = (
            usage.groupby(["tenancy", "component"])["logins"]
            .sum()
            .reset_index()
            .rename(columns={"logins": "Logins", "tenancy": "Tenancy", "component": "Component"})
        )
        long = logins
        fig = px.bar(
            long,
            x="Logins",
            y="Tenancy",
            color="Component",
            barmode="group",
            orientation="h",
            labels={"Logins": "Logins"},
        )
        fig.update_layout(legend_title_text="Component")
        return render_plotly(fig)

    def _tenancy_component_table(component: str):
        usage_range = tenancy_usage()
        usage_all = tenancy_usage_base()
        usage_range_comp = usage_range[usage_range["component"] == component]
        usage_all_comp = usage_all[usage_all["component"] == component]

        active_users = (
            usage_range_comp.groupby("tenancy")["user_name"]
            .nunique()
            .reset_index()
            .rename(columns={"tenancy": "Tenancy", "user_name": "Active users (Date range)"})
        )
        total_users = (
            usage_all_comp.groupby("tenancy")["user_name"]
            .nunique()
            .reset_index()
            .rename(columns={"tenancy": "Tenancy", "user_name": "Total users (To date)"})
        )
        logins_range = (
            usage_range_comp.groupby("tenancy")["logins"]
            .sum()
            .reset_index()
            .rename(columns={"tenancy": "Tenancy", "logins": "Total logins (Date range)"})
        )
        logins_total = (
            usage_all_comp.groupby("tenancy")["logins"]
            .sum()
            .reset_index()
            .rename(columns={"tenancy": "Tenancy", "logins": "Total logins (To date)"})
        )

        merged = (
            total_users.merge(active_users, on="Tenancy", how="outer")
            .merge(logins_range, on="Tenancy", how="outer")
            .merge(logins_total, on="Tenancy", how="outer")
        ).fillna(0)

        cols = [
            "Tenancy",
            "Active users (Date range)",
            "Total users (To date)",
            "Total logins (Date range)",
            "Total logins (To date)",
        ]
        for col in cols:
            if col not in merged.columns:
                merged[col] = 0
        merged = merged[cols]
        int_cols = [c for c in cols if c != "Tenancy"]
        merged[int_cols] = merged[int_cols].astype(int)
        return merged.sort_values("Tenancy")

    @output
    @render.ui
    def tenancies_table_connect():
        df = _tenancy_component_table("Connect")
        return ui.HTML(df.to_html(index=False, classes="full-table sortable", border=0))

    @output
    @render.ui
    def tenancies_table_workbench():
        df = _tenancy_component_table("Workbench")
        return ui.HTML(df.to_html(index=False, classes="full-table sortable", border=0))

    @output
    @render.download(filename="tenancies.csv")
    def download_tenancies():
        connect = _tenancy_component_table("Connect").assign(Component="Connect")
        workbench = _tenancy_component_table("Workbench").assign(Component="Workbench")
        combined = pd.concat([connect, workbench], ignore_index=True, sort=False)
        cols = ["Component"] + [c for c in connect.columns]
        combined = combined[cols]

        def _writer():
            return combined.to_csv(index=False)
        return _writer


def _frequency_buckets(previous: bool = False) -> dict:
    """Return static usage frequency buckets."""
    return FREQUENCY_PREV.copy() if previous else FREQUENCY_CURRENT.copy()


def _format_hours_dd_hh_mm(hours_float: float) -> str:
    minutes = int(round(hours_float * 60))
    dd, rem = divmod(minutes, 1440)
    hh, mm = divmod(rem, 60)
    return f"{dd:02d}:{hh:02d}:{mm:02d}"
