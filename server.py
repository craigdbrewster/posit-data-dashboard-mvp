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

    @reactive.Calc
    def filtered_users():
        tenancy_val = input.tenancy()
        env_val = input.environment()
        comp_val = user_component()
        start, end = current_period()

        df = data.users.copy()

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
        comp_val = user_component()
        start, end = comparison_period()

        df = data.users.copy()

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
        df = data.timeseries[
            (data.timeseries["date"] >= start) & (data.timeseries["date"] <= end)
        ].copy()
        return df

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
        """Count of users first seen in current period."""
        tenancy_val = input.tenancy()
        env_val = input.environment()
        comp_val = user_component()
        start, end = current_period()

        df = data.users.copy()
        if tenancy_val != "All Tenancies":
            df = df[df["tenancy"] == tenancy_val]
        if env_val != "All Environments":
            df = df[df["environment"] == env_val]
        if comp_val != "All Components":
            df = df[df["component"] == comp_val]

        # New users: those who appear in current period but not in any earlier data
        comp_start, _ = comparison_period()
        before_period = df[df["lastLogin"] < comp_start]
        in_current = df[(df["lastLogin"] >= start) & (df["lastLogin"] <= end)]
        new_ids = set(in_current["userId"]) - set(before_period["userId"])
        return len(new_ids)

    @reactive.Calc
    def new_users_previous():
        """Count of new users in previous period for comparison."""
        tenancy_val = input.tenancy()
        env_val = input.environment()
        comp_val = user_component()
        comp_start, comp_end = comparison_period()

        df = data.users.copy()
        if tenancy_val != "All Tenancies":
            df = df[df["tenancy"] == tenancy_val]
        if env_val != "All Environments":
            df = df[df["environment"] == env_val]
        if comp_val != "All Components":
            df = df[df["component"] == comp_val]

        before_comp = comp_start - timedelta(days=1)
        before_period = df[df["lastLogin"] < before_comp]
        in_prev = df[(df["lastLogin"] >= comp_start) & (df["lastLogin"] <= comp_end)]
        new_ids = set(in_prev["userId"]) - set(before_period["userId"])
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
        return f"{len(filtered_users()):,}"

    @output
    @render.text
    def overview_total_users_change():
        current = 10000
        prev = max(current - 47, 0)
        change = (current - prev) / prev * 100 if prev else 0.0
        arrow = "▲" if change >= 0 else "▼"
        return f"{arrow} {change:.1f}% vs previous period"

    # ------------------------------------------------------------------
    # RAG cards (snapshot)
    # ------------------------------------------------------------------

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
        df = filtered_users()
        return f"{len(df):,}"

    @output
    @render.text
    def users_active():
        active_count = len(filtered_users())
        return f"{active_count:,}"

    @output
    @render.text
    def users_active_change():
        cur_active = len(filtered_users())
        prev_active = len(filtered_users_prev_period())
        if prev_active == 0:
            return ""
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
        df = filtered_users()
        start, end = current_period()
        days = max((end - start).days + 1, 1)
        weeks = max(days / 7, 1)
        if df.empty:
            return ui.tags.div("No data for selected period", class_="gds-secondary")

        hours_per_week = (df["loginCount"] * SESSION_HOURS_PER_SESSION) / weeks
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
        df = filtered_users()
        start, end = current_period()
        days = max((end - start).days + 1, 1)
        weeks = max(days / 7, 1)
        if df.empty:
            return ui.tags.div("No data for selected period", class_="gds-secondary")

        logins_per_week = df["loginCount"] / weeks
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

        plot_df = df_weekly.melt(
            id_vars=["week"],
            value_vars=["regularUsers", "activeUsers"],
            var_name="metric",
            value_name="value",
        )
        plot_df["metric"] = plot_df["metric"].map(
            {
                "regularUsers": "Total users",
                "activeUsers": "Total active users",
            }
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
    def users_frequency():
        df = filtered_timeseries()
        if df.empty:
            fig = px.line(title="No data for selected period")
            return render_plotly(fig)

        df_weekly = (
            df.set_index("date")
            .resample("W-MON")
            .agg({"sessionHours": "sum"})
            .reset_index()
        )
        df_weekly["week"] = df_weekly["date"].dt.date
        df_weekly["total_logins"] = df_weekly["sessionHours"] / SESSION_HOURS_PER_SESSION

        plot_df = df_weekly.melt(
            id_vars=["week"],
            value_vars=["total_logins", "sessionHours"],
            var_name="metric",
            value_name="value",
        )
        plot_df["metric"] = plot_df["metric"].map(
            {"total_logins": "Total logins", "sessionHours": "Total hours"}
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

        def fmt_hours(hours_float: float) -> str:
            minutes = int(round(hours_float * 60))
            hh, mm = divmod(minutes, 60)
            dd, hh = divmod(hh, 24)
            return f"{dd:02d}:{hh:02d}:{mm:02d}"

        if df.empty:
            empty_df = pd.DataFrame(
                columns=[
                    "PID",
                    "Tenancy",
                    "Component",
                    "Environment",
                    "Last login",
                    "Avg sessions per week",
                    "Avg hours per week",
                    "Total sessions",
                    "Total hours",
                ]
            )
            return ui.HTML(empty_df.to_html(index=False, classes="full-table", border=0))

        df = df.sort_values("lastLogin", ascending=False)
        out = df[
            ["userId", "tenancy", "component", "environment", "lastLogin", "loginCount"]
        ].copy()
        out = out.rename(
            columns={
                "userId": "PID",
                "tenancy": "Tenancy",
                "component": "Component",
                "environment": "Environment",
                "lastLogin": "Last login",
                "loginCount": "Total logins",
            }
        )
        out["Total hours"] = out["Total logins"] * SESSION_HOURS_PER_SESSION
        out["Avg logins per week"] = (out["Total logins"] / weeks).round(0).astype(int)
        out["Avg hours per week"] = out["Total hours"] / weeks
        out["Avg hours per week"] = out["Avg hours per week"].apply(fmt_hours)
        out["Total hours"] = out["Total hours"].apply(fmt_hours)
        out = out[
            [
                "PID",
                "Tenancy",
                "Component",
                "Environment",
                "Last login",
                "Avg logins per week",
                "Total logins",
                "Avg hours per week",
                "Total hours",
            ]
        ]
        return ui.HTML(out.to_html(index=False, classes="full-table", border=0))

    @output
    @render.download(filename="users.csv")
    def download_users():
        df = filtered_users_by_pid().copy()
        if df.empty:
            df = pd.DataFrame(
                columns=[
                    "PID",
                    "Tenancy",
                    "Component",
                    "Environment",
                    "Last login",
                    "Avg logins per week",
                    "Total logins",
                    "Avg hours per week",
                    "Total hours",
                ]
            )
        else:
            start, end = current_period()
            days = max((end - start).days + 1, 1)
            weeks = max(days / 7, 1)

            def fmt_hours(hours_float: float) -> str:
                minutes = int(round(hours_float * 60))
                hh, mm = divmod(minutes, 60)
                dd, hh = divmod(hh, 24)
                return f"{dd:02d}:{hh:02d}:{mm:02d}"

            df = df.sort_values("lastLogin", ascending=False)
            df = df[
                ["userId", "tenancy", "component", "environment", "lastLogin", "loginCount"]
            ].copy()
            df = df.rename(
                columns={
                    "userId": "PID",
                    "tenancy": "Tenancy",
                    "component": "Component",
                    "environment": "Environment",
                    "lastLogin": "Last login",
                    "loginCount": "Total logins",
                }
            )
            df["Total hours"] = df["Total logins"] * SESSION_HOURS_PER_SESSION
            df["Avg logins per week"] = (df["Total logins"] / weeks).round(0).astype(int)
            df["Avg hours per week"] = df["Total hours"] / weeks
            df["Avg hours per week"] = df["Avg hours per week"].apply(fmt_hours)
            df["Total hours"] = df["Total hours"].apply(fmt_hours)
            df = df[
                [
                    "PID",
                    "Tenancy",
                    "Component",
                    "Environment",
                    "Last login",
                    "Avg logins per week",
                    "Total logins",
                    "Avg hours per week",
                    "Total hours",
                ]
            ]

        def _writer():
            return df.to_csv(index=False)

        return _writer

    # ------------------------------------------------------------------
    # Tenancies tab (combined licences + activity)
    # ------------------------------------------------------------------

    @output
    @render.ui
    def tenancy_licence_bars():
        df = data.tenancies.copy()
        if df.empty:
            fig = px.bar(title="No data")
            return render_plotly(fig)
        long = pd.DataFrame(
            {
                "Tenancy": pd.concat([df["tenancy"], df["tenancy"]], ignore_index=True),
                "Component": ["Connect"] * len(df) + ["Workbench"] * len(df),
                "Users": pd.concat([df["connectUsers"], df["workbenchUsers"]], ignore_index=True),
            }
        )
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
        df = data.tenancies.copy()
        if df.empty:
            fig = px.bar(title="No data")
            return render_plotly(fig)
        ratios = df["connectUsers"] / (df["connectUsers"] + df["workbenchUsers"])
        connect_active = (df["activeUsers"] * ratios).fillna(0)
        workbench_active = df["activeUsers"] - connect_active
        long = pd.DataFrame(
            {
                "Tenancy": pd.concat([df["tenancy"], df["tenancy"]], ignore_index=True),
                "Component": ["Connect"] * len(df) + ["Workbench"] * len(df),
                "Users": pd.concat([connect_active, workbench_active], ignore_index=True),
            }
        )
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
        df = data.tenancies.copy()
        if df.empty:
            fig = px.bar(title="No data")
            return render_plotly(fig)
        ratios = df["connectUsers"] / (df["connectUsers"] + df["workbenchUsers"])
        connect_logins = (df["totalLogins"] * ratios).fillna(0)
        workbench_logins = df["totalLogins"] - connect_logins
        long = pd.DataFrame(
            {
                "Tenancy": pd.concat([df["tenancy"], df["tenancy"]], ignore_index=True),
                "Component": ["Connect"] * len(df) + ["Workbench"] * len(df),
                "Logins": pd.concat([connect_logins, workbench_logins], ignore_index=True),
            }
        )
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
        df = data.tenancies.copy()
        if df.empty:
            fig = px.bar(title="No data")
            return render_plotly(fig)
        ratios = df["connectUsers"] / (df["connectUsers"] + df["workbenchUsers"])
        connect_hours = (df["totalLogins"] * ratios * SESSION_HOURS_PER_SESSION).fillna(0)
        workbench_hours = df["totalLogins"] * SESSION_HOURS_PER_SESSION - connect_hours
        long = pd.DataFrame(
            {
                "Tenancy": pd.concat([df["tenancy"], df["tenancy"]], ignore_index=True),
                "Component": ["Connect"] * len(df) + ["Workbench"] * len(df),
                "Hours": pd.concat([connect_hours, workbench_hours], ignore_index=True),
            }
        )
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
        df, _, _, logs = _tenancy_common()
        if df.empty or logs is None:
            empty = pd.DataFrame(columns=["Tenancy", "Connect logins", "Connect hours", "Workbench logins", "Workbench hours"])
            return ui.HTML(empty.to_html(index=False, classes="full-table", border=0))
        connect_logins, workbench_logins, connect_hours, workbench_hours = logs
        table = pd.DataFrame(
            {
                "Tenancy": df["tenancy"],
                "Connect logins": connect_logins.round(0).astype(int),
                "Connect hours": connect_hours.apply(_fmt_hours),
                "Workbench logins": workbench_logins.round(0).astype(int),
                "Workbench hours": workbench_hours.apply(_fmt_hours),
            }
        ).sort_values("Tenancy")
        return ui.HTML(table.to_html(index=False, classes="full-table", border=0))

    @output
    @render.ui
    def tenancies_table_all():
        df, connect_active, workbench_active, logs = _tenancy_common()
        if df.empty or logs is None:
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
        connect_logins, workbench_logins, connect_hours, workbench_hours = logs
        table = pd.DataFrame(
            {
                "Tenancy": df["tenancy"],
                "Connect total users": df["connectUsers"].astype(int),
                "Connect active users": connect_active.round(0).astype(int),
                "Connect logins": connect_logins.round(0).astype(int),
                "Connect hours": connect_hours.apply(_fmt_hours),
                "Workbench total users": df["workbenchUsers"].astype(int),
                "Workbench active users": workbench_active.round(0).astype(int),
                "Workbench logins": workbench_logins.round(0).astype(int),
                "Workbench hours": workbench_hours.apply(_fmt_hours),
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
