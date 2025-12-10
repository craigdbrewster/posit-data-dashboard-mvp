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
    TOTAL_ACTIVE_BASE = 9100
    SESSION_HOURS_PER_SESSION = 1.5

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
        """Aggregate usage to one row per user with latest tenancy/component/env and summed logins."""
        if usage.empty:
            return pd.DataFrame(
                columns=[
                    "userId",
                    "tenancy",
                    "component",
                    "environment",
                    "lastLogin",
                    "loginCount",
                ]
            )
        # Sum logins per user in the window
        sums = usage.groupby("user_id", as_index=False)["logins"].sum().rename(columns={"user_id": "userId", "logins": "loginCount"})
        # Latest login per user with associated tenancy/component/env
        latest = (
            usage.sort_values("login_time")
            .groupby("user_id", as_index=False)
            .tail(1)
            .rename(columns={"user_id": "userId", "login_time": "lastLogin"})
        )
        merged = latest[["userId", "tenancy", "component", "environment", "lastLogin"]].merge(
            sums, on="userId", how="left"
        )
        return merged

    @reactive.Calc
    def filtered_users():
        usage = usage_filtered()
        return _aggregate_users(usage)

    @reactive.Calc
    def filtered_users_prev_period():
        start, end = comparison_period()
        usage = usage_base()
        usage = usage[(usage["login_time"] >= start) & (usage["login_time"] <= end)]
        return _aggregate_users(usage)

    @reactive.Calc
    def filtered_timeseries():
        start, end = current_period()
        df = data.timeseries[
            (data.timeseries["date"] >= start) & (data.timeseries["date"] <= end)
        ].copy()
        # apply tenancy/environment filters using the usage log info
        usage = usage_filtered()
        if usage.empty:
            return df.iloc[0:0]
        df = (
            usage.assign(date=usage["login_time"].dt.normalize())
            .groupby("date", as_index=False)
            .agg(
                activeUsers=("user_id", "nunique"),
                regularUsers=("user_id", "nunique"),
                powerUsers=("user_id", "nunique"),
                sessionHours=("session_length_hours", "sum"),
            )
        )
        return df

    def usage_base():
        """Apply tenancy/env/component filters, without date restriction."""
        usage = data.usage_log.copy()
        tenancy_val = input.tenancy()
        env_val = input.environment()
        comp_val = user_component()
        if tenancy_val != "All Tenancies":
            usage = usage[usage["tenancy"] == tenancy_val]
        if env_val != "All Environments":
            usage = usage[usage["environment"] == env_val]
        if comp_val and comp_val != "All Components":
            usage = usage[usage["component"] == comp_val]
        return usage

    def usage_filtered():
        start, end = current_period()
        usage = usage_base()
        usage = usage[
            (usage["login_time"] >= start) & (usage["login_time"] <= end)
        ].copy()
        return usage

    def usage_cumulative(end_date):
        """Return usage filtered by tenancy/env/component up to end_date (cumulative)."""
        usage = usage_base()
        usage = usage[usage["login_time"] <= end_date].copy()
        return usage

    @reactive.Calc
    def usage_window():
        return usage_filtered()

    @reactive.Calc
    def total_users_cumulative():
        """Cumulative unique users up to the end of the current period (respecting filters)."""
        _, end = current_period()
        usage = usage_cumulative(end)
        return usage["user_id"].nunique()

    @reactive.Calc
    def active_users_current():
        """Unique users with activity in the current period (respecting filters)."""
        usage = usage_window()
        active = usage["user_id"].nunique()
        return min(active, total_users_cumulative() if total_users_cumulative() else active)

    def first_seen_series():
        """First login per user for current tenancy/env/component filters."""
        usage = usage_base()
        if usage.empty:
            return pd.Series(dtype="datetime64[ns]")
        return usage.groupby("user_id")["login_time"].min()

    @reactive.Calc
    def tenancy_usage():
        start, end = current_period()
        usage = data.usage_log[
            (data.usage_log["login_time"] >= start) & (data.usage_log["login_time"] <= end)
        ].copy()
        env_val = input.tenancy_environment()
        if env_val != "All Environments":
            usage = usage[usage["environment"] == env_val]
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
    def total_session_hours_current():
        """Total session hours in current period."""
        df = filtered_timeseries()
        return df["sessionHours"].sum() if not df.empty else 0

    @reactive.Calc
    def total_session_hours_previous():
        """Total session hours in previous period."""
        start, end = comparison_period()
        df = data.timeseries[
            (data.timeseries["date"] >= start) & (data.timeseries["date"] <= end)
        ].copy()
        return df["sessionHours"].sum() if not df.empty else 0

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
        """Users not logged in during current period."""
        tenancy_val = input.tenancy()
        env_val = input.environment()
        comp_val = user_component()

        all_users = data.users.copy()
        if tenancy_val != "All Tenancies":
            all_users = all_users[all_users["tenancy"] == tenancy_val]
        if env_val != "All Environments":
            all_users = all_users[all_users["environment"] == env_val]
        if comp_val != "All Components":
            all_users = all_users[all_users["component"] == comp_val]

        logged_in_ids = set(filtered_users()["userId"])
        not_logged_in = len(all_users[~all_users["userId"].isin(logged_in_ids)])
        return not_logged_in

    @reactive.Calc
    def avg_session_length_current():
        """Average session length (hours) in current period."""
        df = filtered_timeseries()
        if df.empty or len(filtered_users()) == 0:
            return 0.0
        total_hours = df["sessionHours"].sum()
        num_users = len(filtered_users())
        return total_hours / num_users if num_users > 0 else 0.0

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
    def avg_session_length_previous():
        """Average session length (hours) in comparison period."""
        start, end = comparison_period()
        df = data.timeseries[
            (data.timeseries["date"] >= start) & (data.timeseries["date"] <= end)
        ]
        df_current_users = filtered_users_prev_period()
        if df.empty or len(df_current_users) == 0:
            return 0.0
        total_hours = (df["activeUsers"] * 8.5).sum()
        num_users = len(df_current_users)
        return total_hours / num_users if num_users > 0 else 0.0

    @reactive.Calc
    def sessions_per_user_previous():
        """Average sessions per user in comparison period."""
        start, end = comparison_period()
        df = data.timeseries[
            (data.timeseries["date"] >= start) & (data.timeseries["date"] <= end)
        ]
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
        _, end = current_period()
        _, comp_end = comparison_period()
        current = usage_cumulative(end)["user_id"].nunique()
        prev = usage_cumulative(comp_end)["user_id"].nunique()
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
    def overview_session_hours():
        hours = total_session_hours_current()
        return f"{hours:,.0f}"

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
        df_prev = data.timeseries[
            (data.timeseries["date"] >= prev_start) & (data.timeseries["date"] <= prev_end)
        ]
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
        df_prev = data.timeseries[
            (data.timeseries["date"] >= prev_start) & (data.timeseries["date"] <= prev_end)
        ]
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
    def users_hours_pie():
        usage = usage_filtered()
        start, end = current_period()
        days = max((end - start).days + 1, 1)
        weeks = max(days / 7, 1)
        if usage.empty:
            return ui.tags.div("No data for selected period", class_="gds-secondary")

        user_hours = (
            usage.groupby("user_id")["session_length_hours"].sum() / weeks
        )
        hours_per_week = user_hours.reindex(user_hours.index, fill_value=0)
        inactive = max(not_logged_in_current(), 0)
        if inactive:
            hours_per_week = pd.concat(
                [hours_per_week, pd.Series([0] * inactive)], ignore_index=True
            )
        labels, counts, colors = _pie_from_series(
            hours_per_week,
            [
                ("More than 20 hours per week", 20, None, "#0b7a0b"),
                ("10 to 19 hours per week", 10, 19.999, "#1d70b8"),
                ("5 to 9 hours per week", 5, 9.999, "#6f777b"),
                ("Less than 5 hours per week", 0, 4.999, "#b58800"),
                ("No activity", -0.0001, 0.0001, "#b56d00"),
            ],
        )
        fig = px.pie(
            names=labels,
            values=counts,
            color=labels,
            color_discrete_map={l: c for l, _, _, c in [
                ("More than 20 hours per week", 20, None, "#0b7a0b"),
                ("10 to 19 hours per week", 10, 19.999, "#1d70b8"),
                ("5 to 9 hours per week", 5, 9.999, "#6f777b"),
                ("Less than 5 hours per week", 0, 4.999, "#b58800"),
                ("No activity", -0.0001, 0.0001, "#b56d00"),
            ]},
        )
        fig.update_layout(showlegend=True)
        return render_plotly(fig)

    @output
    @render.ui
    def users_logins_pie():
        usage = usage_filtered()
        start, end = current_period()
        days = max((end - start).days + 1, 1)
        weeks = max(days / 7, 1)
        if usage.empty:
            return ui.tags.div("No data for selected period", class_="gds-secondary")

        user_logins = usage.groupby("user_id")["logins"].sum() / weeks
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

        usage = usage.assign(week=usage["login_time"].dt.to_period("W-MON").dt.start_time)
        weeks = sorted(usage["week"].unique())

        # Active users per week within the selected window
        active_weekly = (
            usage.groupby("week")["user_id"].nunique().reindex(weeks, fill_value=0)
        )

        # Cumulative total users up to each week using all history for the filters
        base_raw = usage_base()
        base = base_raw.assign(week=base_raw["login_time"].dt.to_period("W-MON").dt.start_time)
        cumulative_totals = []
        for wk in weeks:
            cutoff = wk + pd.Timedelta(days=6)
            cumulative_totals.append(
                base[base["login_time"] <= cutoff]["user_id"].nunique()
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

        usage = usage.assign(week=usage["login_time"].dt.to_period("W-MON").dt.start_time)
        df_weekly = (
            usage.groupby("week")
            .agg(
                total_hours=("session_length_hours", "sum"),
                total_logins=("logins", "sum"),
            )
            .reset_index()
        )

        plot_df = df_weekly.melt(
            id_vars=["week"],
            value_vars=["total_logins", "total_hours"],
            var_name="metric",
            value_name="value",
        )
        plot_df["metric"] = plot_df["metric"].map(
            {"total_logins": "Total logins", "total_hours": "Total hours"}
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
        include_component = user_component() in (None, "All Components")

        def fmt_hours(hours_float: float) -> str:
            minutes = int(round(hours_float * 60))
            hh, mm = divmod(minutes, 60)
            dd, hh = divmod(hh, 24)
            return f"{dd:02d}:{hh:02d}:{mm:02d}"

        def fmt_last_login(series: pd.Series) -> pd.Series:
            """Return series of date-only strings from datetime-like values."""
            formatted = pd.to_datetime(series, errors="coerce").dt.date.astype(str)
            return formatted.replace("NaT", "")

        if df.empty:
            cols = [
                "PID",
                "Tenancy",
                "Environment",
                "Last login",
                "Avg logins per week",
                "Avg hours per week",
                "Total logins",
                "Total hours",
            ]
            if include_component:
                cols.insert(2, "Component")
            empty_df = pd.DataFrame(
                columns=cols
            )
            return ui.HTML(empty_df.to_html(index=False, classes="full-table", border=0))

        df = df.sort_values("lastLogin", ascending=False)
        base_cols = ["userId", "tenancy", "environment", "lastLogin", "loginCount"]
        if include_component:
            base_cols.insert(2, "component")
        out = df[base_cols].copy()
        out = out.rename(
            columns={
                "userId": "PID",
                "tenancy": "Tenancy",
                "environment": "Environment",
                "lastLogin": "Last login",
                "loginCount": "Total logins",
            }
        )
        out["Last login"] = fmt_last_login(out["Last login"])
        out["Total hours"] = out["Total logins"] * SESSION_HOURS_PER_SESSION
        out["Avg logins per week"] = (out["Total logins"] / weeks).round(0).astype(int)
        out["Avg hours per week"] = out["Total hours"] / weeks
        out["Avg hours per week"] = out["Avg hours per week"].apply(fmt_hours)
        out["Total hours"] = out["Total hours"].apply(fmt_hours)
        final_cols = [
            "PID",
            "Tenancy",
            "Environment",
            "Last login",
            "Avg logins per week",
            "Total logins",
            "Avg hours per week",
            "Total hours",
        ]
        if include_component:
            final_cols.insert(2, "Component")
        out = out[final_cols]
        return ui.HTML(out.to_html(index=False, classes="full-table", border=0))

    @output
    @render.download(filename="users.csv")
    def download_users():
        df = filtered_users_by_pid().copy()
        include_component = user_component() in (None, "All Components")
        if df.empty:
            cols = [
                "PID",
                "Tenancy",
                "Environment",
                "Last login",
                "Avg logins per week",
                "Total logins",
                "Avg hours per week",
                "Total hours",
            ]
            if include_component:
                cols.insert(2, "Component")
            df = pd.DataFrame(columns=cols)
        else:
            start, end = current_period()
            days = max((end - start).days + 1, 1)
            weeks = max(days / 7, 1)

            def fmt_hours(hours_float: float) -> str:
                minutes = int(round(hours_float * 60))
                hh, mm = divmod(minutes, 60)
                dd, hh = divmod(hh, 24)
                return f"{dd:02d}:{hh:02d}:{mm:02d}"

            def fmt_last_login(series: pd.Series) -> pd.Series:
                formatted = pd.to_datetime(series, errors="coerce").dt.date.astype(str)
                return formatted.replace("NaT", "")

            df = df.sort_values("lastLogin", ascending=False)
            base_cols = ["userId", "tenancy", "environment", "lastLogin", "loginCount"]
            if include_component:
                base_cols.insert(2, "component")
            df = df[base_cols].copy()
            rename_map = {
                "userId": "PID",
                "tenancy": "Tenancy",
                "environment": "Environment",
                "lastLogin": "Last login",
                "loginCount": "Total logins",
            }
            if include_component:
                rename_map["component"] = "Component"
            df = df.rename(columns=rename_map)
            df["Last login"] = fmt_last_login(df["Last login"])
            df["Total hours"] = df["Total logins"] * SESSION_HOURS_PER_SESSION
            df["Avg logins per week"] = (df["Total logins"] / weeks).round(0).astype(int)
            df["Avg hours per week"] = df["Total hours"] / weeks
            df["Avg hours per week"] = df["Avg hours per week"].apply(fmt_hours)
            df["Total hours"] = df["Total hours"].apply(fmt_hours)
            final_cols = [
                "PID",
                "Tenancy",
                "Environment",
                "Last login",
                "Avg logins per week",
                "Total logins",
                "Avg hours per week",
                "Total hours",
            ]
            if include_component:
                final_cols.insert(2, "Component")
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
            usage.groupby(["tenancy", "component"])["user_id"]
            .nunique()
            .reset_index()
            .rename(columns={"user_id": "Users", "tenancy": "Tenancy", "component": "Component"})
        )
        long = agg
        fig = px.bar(
            long,
            x="Tenancy",
            y="Users",
            color="Component",
            barmode="group",
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
            usage.groupby(["tenancy", "component"])["user_id"]
            .nunique()
            .reset_index()
            .rename(columns={"user_id": "Users", "tenancy": "Tenancy", "component": "Component"})
        )
        long = active
        fig = px.bar(
            long,
            x="Tenancy",
            y="Users",
            color="Component",
            barmode="group",
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
            x="Tenancy",
            y="Logins",
            color="Component",
            barmode="group",
            labels={"Logins": "Logins"},
        )
        fig.update_layout(legend_title_text="Component")
        return render_plotly(fig)

    @output
    @render.ui
    def tenancy_hours_bars():
        usage = tenancy_usage()
        if usage.empty:
            fig = px.bar(title="No data")
            return render_plotly(fig)
        hours = (
            usage.groupby(["tenancy", "component"])["session_length_hours"]
            .sum()
            .reset_index()
            .rename(columns={"session_length_hours": "Hours", "tenancy": "Tenancy", "component": "Component"})
        )
        long = hours
        fig = px.bar(
            long,
            x="Tenancy",
            y="Hours",
            color="Component",
            barmode="group",
            labels={"Hours": "Hours"},
        )
        fig.update_layout(legend_title_text="Component")
        return render_plotly(fig)

    def _tenancy_common():
        df = data.tenancies.copy()
        if df.empty:
            return df, None, None, None
        ratios = df["connectUsers"] / (df["connectUsers"] + df["workbenchUsers"])
        connect_active = (df["activeUsers"] * ratios).fillna(0)
        workbench_active = df["activeUsers"] - connect_active
        connect_logins = (df["totalLogins"] * ratios).fillna(0)
        workbench_logins = df["totalLogins"] - connect_logins
        connect_hours = connect_logins * SESSION_HOURS_PER_SESSION
        workbench_hours = workbench_logins * SESSION_HOURS_PER_SESSION
        return df, connect_active, workbench_active, (connect_logins, workbench_logins, connect_hours, workbench_hours)

    def _fmt_hours(val):
        minutes = int(round(val * 60))
        dd, rem = divmod(minutes, 1440)
        hh, mm = divmod(rem, 60)
        return f"{dd:02d}:{hh:02d}:{mm:02d}"

    @output
    @render.ui
    def tenancies_table_totals():
        df, _, _, _ = _tenancy_common()
        if df.empty:
            empty = pd.DataFrame(columns=["Tenancy", "Connect total users", "Workbench total users"])
            return ui.HTML(empty.to_html(index=False, classes="full-table", border=0))
        table = pd.DataFrame(
            {
                "Tenancy": df["tenancy"],
                "Connect total users": df["connectUsers"].astype(int),
                "Workbench total users": df["workbenchUsers"].astype(int),
            }
        ).sort_values("Tenancy")
        return ui.HTML(table.to_html(index=False, classes="full-table", border=0))

    @output
    @render.ui
    def tenancies_table_active():
        df, connect_active, workbench_active, _ = _tenancy_common()
        if df.empty or connect_active is None:
            empty = pd.DataFrame(columns=["Tenancy", "Connect active users", "Workbench active users"])
            return ui.HTML(empty.to_html(index=False, classes="full-table", border=0))
        table = pd.DataFrame(
            {
                "Tenancy": df["tenancy"],
                "Connect active users": connect_active.round(0).astype(int),
                "Workbench active users": workbench_active.round(0).astype(int),
            }
        ).sort_values("Tenancy")
        return ui.HTML(table.to_html(index=False, classes="full-table", border=0))

    @output
    @render.ui
    def tenancies_table_logins():
        df, _, _, logs = _tenancy_common()
        if df.empty or logs is None:
            empty = pd.DataFrame(columns=["Tenancy", "Connect logins", "Workbench logins"])
            return ui.HTML(empty.to_html(index=False, classes="full-table", border=0))
        connect_logins, workbench_logins, _, _ = logs
        table = pd.DataFrame(
            {
                "Tenancy": df["tenancy"],
                "Connect logins": connect_logins.round(0).astype(int),
                "Workbench logins": workbench_logins.round(0).astype(int),
            }
        ).sort_values("Tenancy")
        return ui.HTML(table.to_html(index=False, classes="full-table", border=0))

    @output
    @render.ui
    def tenancies_table_hours():
        return ui.HTML(pd.DataFrame().to_html(index=False, classes="full-table", border=0))

    @output
    @render.ui
    def tenancies_table_all():
        usage = tenancy_usage()
        if usage.empty:
            empty = pd.DataFrame(
                columns=[
                    "Tenancy",
                    "Connect total users",
                    "Connect active users",
                    "Connect logins",
                    "Connect hours",
                    "Workbench total users",
                    "Workbench active users",
                    "Workbench logins",
                    "Workbench hours",
                ]
            )
            return ui.HTML(empty.to_html(index=False, classes="full-table", border=0))

        start, end = current_period()
        active_usage = usage[
            (usage["login_time"] >= start) & (usage["login_time"] <= end)
        ]
        user_counts = (
            usage.groupby(["tenancy", "component"])["user_id"]
            .nunique()
            .unstack(fill_value=0)
            .rename(columns={"Connect": "Connect total users", "Workbench": "Workbench total users"})
            .reset_index()
            .rename(columns={"tenancy": "Tenancy"})
        )
        active_counts = (
            active_usage.groupby(["tenancy", "component"])["user_id"]
            .nunique()
            .unstack(fill_value=0)
            .rename(columns={"Connect": "Connect active users", "Workbench": "Workbench active users"})
            .reset_index()
            .rename(columns={"tenancy": "Tenancy"})
        )
        logins = (
            usage.groupby(["tenancy", "component"])["logins"]
            .sum()
            .unstack(fill_value=0)
            .rename(columns={"Connect": "Connect logins", "Workbench": "Workbench logins"})
            .reset_index()
            .rename(columns={"tenancy": "Tenancy"})
        )
        hours = (
            usage.groupby(["tenancy", "component"])["session_length_hours"]
            .sum()
            .unstack(fill_value=0)
            .rename(columns={"Connect": "Connect hours", "Workbench": "Workbench hours"})
            .reset_index()
            .rename(columns={"tenancy": "Tenancy"})
        )

        merged = (
            user_counts
            .merge(active_counts, on="Tenancy", how="outer")
            .merge(logins, on="Tenancy", how="outer")
            .merge(hours, on="Tenancy", how="outer")
            .fillna(0)
        )

        table = pd.DataFrame(
            {
                "Tenancy": merged["Tenancy"],
                "Connect total users": merged.get("Connect total users", 0).astype(int),
                "Connect active users": merged.get("Connect active users", 0).astype(int),
                "Connect logins": merged.get("Connect logins", 0).astype(int),
                "Connect hours": merged.get("Connect hours", 0).apply(_fmt_hours),
                "Workbench total users": merged.get("Workbench total users", 0).astype(int),
                "Workbench active users": merged.get("Workbench active users", 0).astype(int),
                "Workbench logins": merged.get("Workbench logins", 0).astype(int),
                "Workbench hours": merged.get("Workbench hours", 0).apply(_fmt_hours),
            }
        ).sort_values("Tenancy")
        return ui.HTML(table.to_html(index=False, classes="full-table", border=0))

    @output
    @render.download(filename="tenancies.csv")
    def download_tenancies():
        df, connect_active, workbench_active, logs = _tenancy_common()
        if df.empty or logs is None:
            combined = pd.DataFrame()
        else:
            connect_logins, workbench_logins, connect_hours, workbench_hours = logs
            combined = pd.DataFrame(
                {
                    "Tenancy": df["tenancy"],
                    "Connect total users": df["connectUsers"].astype(int),
                    "Workbench total users": df["workbenchUsers"].astype(int),
                    "Connect active users": connect_active.round(0).astype(int),
                    "Workbench active users": workbench_active.round(0).astype(int),
                    "Connect logins": connect_logins.round(0).astype(int),
                    "Workbench logins": workbench_logins.round(0).astype(int),
                    "Connect hours": connect_hours.apply(_fmt_hours),
                    "Workbench hours": workbench_hours.apply(_fmt_hours),
                }
            ).sort_values("Tenancy")
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
