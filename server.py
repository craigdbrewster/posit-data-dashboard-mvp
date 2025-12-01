from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
from shiny import reactive, render, ui

import data


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


def format_duration(hours: float) -> str:
    """Break a duration in hours into d/h/m/s."""
    total_seconds = max(int(hours * 3600), 0)
    days, rem = divmod(total_seconds, 86_400)
    hrs, rem = divmod(rem, 3_600)
    mins, secs = divmod(rem, 60)
    return f"{days}d {hrs}h {mins}m {secs}s"


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
        comp_val = input.component()
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
        comp_val = input.component()
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
        comp_val = input.component()
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
        comp_val = input.component()

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
        current = len(data.users)
        prev = len(data.users)
        change = 0.0 if prev else 0.0
        arrow = "▲" if change >= 0 else "▼"
        return f"{arrow} {change:.1f}% vs previous period"

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
    def overview_session_hours_change():
        current = total_session_hours_current()
        prev = total_session_hours_previous()
        if prev > 0:
            change = (current - prev) / prev * 100
        else:
            change = 0.0 if current == 0 else 100.0
        arrow = "▲" if change >= 0 else "▼"
        return f"{arrow} {change:.1f}% vs previous period"

    @output
    @render.ui
    def overview_timeseries():
        df = filtered_timeseries()
        if df.empty:
            fig = px.line(title="No data for selected period")
            return render_plotly(fig)

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
        return render_plotly(fig)

    @output
    @render.ui
    def overview_tenancy_bars():
        df = data.tenancies.copy()
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
        return render_plotly(fig)

    # ------------------------------------------------------------------
    # Licences tab
    # ------------------------------------------------------------------

    def _licence_active_users_for_period(start: datetime, end: datetime):
        tenancy_val = input.tenancy()
        comp_val = input.component()

        df = data.users.copy()
        if tenancy_val != "All Tenancies":
            df = df[df["tenancy"] == tenancy_val]
        if comp_val != "All Components":
            df = df[df["component"] == comp_val]

        df = df[(df["lastLogin"] >= start) & (df["lastLogin"] <= end)]
        connect_active = len(df[df["component"] == "Connect"])
        workbench_active = len(df[df["component"] == "Workbench"])
        return connect_active, workbench_active

    @output
    @render.text
    def lic_connect_assigned():
        tenancy_val = input.tenancy()
        comp_val = input.component()
        lic_df = data.licences.copy()
        if tenancy_val != "All Tenancies":
            lic_df = lic_df[lic_df["tenancy"] == tenancy_val]
        if comp_val != "All Components":
            lic_df = lic_df[lic_df["component"] == comp_val]

        connect_assigned = lic_df.loc[
            lic_df["component"] == "Connect", "licencesUsed"
        ].sum()
        return f"{int(connect_assigned):,} of {data.TOTAL_CONNECT_LICENCES:,}"

    @output
    @render.text
    def lic_connect_active():
        current_start, current_end = current_period()
        connect_active_current, _ = _licence_active_users_for_period(
            current_start, current_end
        )
        return f"{connect_active_current:,}"

    @output
    @render.text
    def lic_connect_active_change():
        current_start, current_end = current_period()
        prev_start, prev_end = comparison_period()
        connect_active_current, _ = _licence_active_users_for_period(
            current_start, current_end
        )
        connect_active_prev, _ = _licence_active_users_for_period(prev_start, prev_end)
        if connect_active_prev > 0:
            change = (connect_active_current - connect_active_prev) / connect_active_prev * 100
        else:
            change = 0.0
        arrow = "▲" if change >= 0 else "▼"
        return f"{arrow} {change:.1f}% vs previous period"

    @output
    @render.text
    def lic_workbench_assigned():
        tenancy_val = input.tenancy()
        comp_val = input.component()
        lic_df = data.licences.copy()
        if tenancy_val != "All Tenancies":
            lic_df = lic_df[lic_df["tenancy"] == tenancy_val]
        if comp_val != "All Components":
            lic_df = lic_df[lic_df["component"] == comp_val]

        workbench_assigned = lic_df.loc[
            lic_df["component"] == "Workbench", "licencesUsed"
        ].sum()
        return f"{int(workbench_assigned):,} of {data.TOTAL_WORKBENCH_LICENCES:,}"

    @output
    @render.text
    def lic_workbench_active():
        current_start, current_end = current_period()
        _, workbench_active_current = _licence_active_users_for_period(
            current_start, current_end
        )
        return f"{workbench_active_current:,}"

    @output
    @render.text
    def lic_workbench_active_change():
        current_start, current_end = current_period()
        prev_start, prev_end = comparison_period()
        _, workbench_active_current = _licence_active_users_for_period(
            current_start, current_end
        )
        _, workbench_active_prev = _licence_active_users_for_period(prev_start, prev_end)
        if workbench_active_prev > 0:
            change = (workbench_active_current - workbench_active_prev) / workbench_active_prev * 100
        else:
            change = 0.0
        arrow = "▲" if change >= 0 else "▼"
        return f"{arrow} {change:.1f}% vs previous period"

    @output
    @render.data_frame
    def lic_table():
        tenancy_val = input.tenancy()
        comp_val = input.component()

        lic_df = data.licences.copy()
        if tenancy_val != "All Tenancies":
            lic_df = lic_df[lic_df["tenancy"] == tenancy_val]
        if comp_val != "All Components":
            lic_df = lic_df[lic_df["component"] == comp_val]

        current_start, current_end = current_period()
        df_users = data.users[
            (data.users["lastLogin"] >= current_start)
            & (data.users["lastLogin"] <= current_end)
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

        totals = (
            out.groupby("Component")[["Assigned licences", "Active licences"]]
            .sum()
            .reset_index()
        )
        totals["Tenancy"] = "Total"

        final = pd.concat([out, totals], ignore_index=True)
        final = final[["Tenancy", "Component", "Assigned licences", "Active licences"]]
        final.columns = ["Tenancy", "Component", "Assigned Licences", "Active Licences"]
        sorted_df = final.sort_values(["Tenancy", "Component"])
        return sorted_df

    # ------------------------------------------------------------------
    # Users tab
    # ------------------------------------------------------------------

    @output
    @render.text
    def users_active():
        return f"{len(filtered_users()):,}"

    @output
    @render.text
    def users_active_change():
        active_current = len(filtered_users())
        active_prev = len(filtered_users_prev_period())

        if active_prev > 0:
            change = (active_current - active_prev) / active_prev * 100
        else:
            change = 0.0
        arrow = "▲" if change >= 0 else "▼"
        return f"{arrow} {change:.1f}% vs previous period"

    @output
    @render.text
    def users_dormant():
        dormant = data.TOTAL_USERS - len(filtered_users())
        return f"{dormant:,}"

    @output
    @render.text
    def users_dormant_change():
        dormant_current = data.TOTAL_USERS - len(filtered_users())
        dormant_prev = data.TOTAL_USERS - len(filtered_users_prev_period())

        if dormant_prev > 0:
            change = (dormant_current - dormant_prev) / dormant_prev * 100
        else:
            change = 0.0
        arrow = "▲" if change >= 0 else "▼"
        return f"{arrow} {change:.1f}% vs previous period"

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
        df = filtered_timeseries()
        if df.empty:
            return ui.tags.div("No data for selected period", class_="gds-secondary")

        latest = df.sort_values("date").iloc[-1]
        segments = [
            ("Daily users", latest["powerUsers"], "#00703c"),
            ("Weekly users", latest["regularUsers"], "#1d70b8"),
            ("Other active users", latest["lightUsers"], "#b1b4b6"),
            ("Dormant users", latest["dormantUsers"], "#b58800"),
        ]
        total = sum(val for _, val, _ in segments)
        rows = []
        for label, value, color in segments:
            percent = (value / total * 100) if total > 0 else 0
            rows.append(
                ui.tags.div(
                    {"class": "gds-dist-row"},
                    ui.tags.div(
                        {"class": "gds-dist-label"},
                        label,
                        ui.tags.div(
                            {"class": "gds-progress"},
                            ui.tags.div(
                                {
                                    "class": "gds-progress__bar",
                                    "style": f"background:{color};width:{percent:.1f}%;",
                                }
                            ),
                        ),
                    ),
                    ui.tags.div(
                        {"class": "gds-dist-val"},
                        f"{int(value):,} ({percent:.1f}%)",
                    ),
                )
            )

        return ui.tags.div(*rows)

    @output
    @render.ui
    def users_session_metrics():
        hours = avg_session_length_current()
        hours_prev = avg_session_length_previous()
        minutes = hours * 60
        sessions = sessions_per_user_current()
        sessions_prev = sessions_per_user_previous()

        length_change = format_change(hours, hours_prev)
        sessions_change = format_change(sessions, sessions_prev)
        duration_label = format_duration(hours)

        return ui.tags.div(
            ui.tags.div(
                {"class": "gds-pill"},
                ui.tags.div(
                    {"class": "gds-pill__label"},
                    ui.tags.span({"class": "gds-pill__icon"}, "🕒"),
                    "Average session length",
                ),
                ui.tags.div(
                    {"class": "gds-pill__metrics"},
                    ui.tags.span({"class": "gds-pill__value-lg"}, duration_label),
                    ui.tags.span({"class": "gds-pill__sub"}, f"{minutes:.0f} mins total"),
                    ui.tags.div({"class": "gds-pill__change"}, length_change),
                ),
            ),
            ui.tags.div(
                {"class": "gds-pill"},
                ui.tags.div(
                    {"class": "gds-pill__label"},
                    ui.tags.span({"class": "gds-pill__icon"}, "〰"),
                    "Average sessions per user",
                ),
                ui.tags.div(
                    {"class": "gds-pill__metrics"},
                    ui.tags.span({"class": "gds-pill__value-lg"}, f"{sessions:.1f}"),
                    ui.tags.div({"class": "gds-pill__change"}, sessions_change),
                ),
            ),
        )

    @output
    @render.data_frame
    def users_table():
        df = filtered_users_by_pid().copy()
        if df.empty:
            return pd.DataFrame(
                columns=[
                    "User ID",
                    "Tenancy",
                    "Component",
                    "Environment",
                    "Last login",
                    "Login count",
                ]
            )

        df = df.sort_values("lastLogin", ascending=False)
        out = df[
            ["userId", "tenancy", "component", "environment", "lastLogin", "loginCount"]
        ].copy()
        out.columns = [
            "User ID",
            "Tenancy",
            "Component",
            "Environment",
            "Last login",
            "Login count",
        ]
        return out

    # ------------------------------------------------------------------
    # Tenancies tab
    # ------------------------------------------------------------------

    @output
    @render.data_frame
    def tenancies_table():
        tenancy_val = input.tenancy()
        comp_val = input.component()
        start, end = current_period()

        df_users = data.users[
            (data.users["lastLogin"] >= start) & (data.users["lastLogin"] <= end)
        ]

        if tenancy_val != "All Tenancies":
            df_users = df_users[df_users["tenancy"] == tenancy_val]
        if comp_val != "All Components":
            df_users = df_users[df_users["component"] == comp_val]

        total_per_tenancy_comp = (
            data.users.groupby(["tenancy", "component"])["userId"]
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

        lic_pivot = data.licences.pivot_table(
            index="tenancy",
            columns="component",
            values="licencesUsed",
            fill_value=0,
        )
        lic_pivot.columns = [f"licences_{c}" for c in lic_pivot.columns.to_list()]
        lic_pivot = lic_pivot.reset_index()

        out = pivot.merge(lic_pivot, on="tenancy", how="left").fillna(0)

        def get(col, default=0):
            return out[col] if col in out.columns else default

        display = pd.DataFrame(
            {
                "Tenancy": out["tenancy"],
                "Total users": get("totalUsers_Connect") + get("totalUsers_Workbench"),
                "Active users": get("activeUsersComponent_Connect")
                + get("activeUsersComponent_Workbench"),
                "Assigned Connect": get("licences_Connect"),
                "Active Connect": get("activeUsersComponent_Connect"),
                "Assigned Workbench": get("licences_Workbench"),
                "Active Workbench": get("activeUsersComponent_Workbench"),
            }
        )

        sorted_df = display.sort_values("Tenancy")
        return sorted_df
