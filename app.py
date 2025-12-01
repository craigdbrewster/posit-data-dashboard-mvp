from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
from shiny import App, reactive, render, ui


def render_plotly(fig):
    """Render a Plotly figure as HTML for Shiny @render.ui"""
    html_str = fig.to_html(include_plotlyjs="require", div_id=f"plot-{id(fig)}")
    return ui.HTML(html_str)


def metric_card(title, value, change=None, aria_label=None):
    """Lightweight GDS-inspired stat card used across tabs."""
    parts = [
        ui.tags.div({"class": "gds-card__label"}, title),
        ui.tags.div({"class": "gds-card__value"}, value),
    ]
    if change is not None:
        parts.append(ui.tags.div({"class": "gds-card__change"}, change))
    return ui.tags.div(
        {"class": "gds-card", "role": "group", "aria-label": aria_label or title},
        *parts,
    )


def panel_card(title, body):
    """Panel wrapper matching the React mock styling."""
    return ui.tags.div(
        {"class": "gds-panel"},
        ui.tags.div({"class": "gds-panel__title"}, title),
        body,
    )

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
    ui.tags.head(
        ui.tags.link(
            rel="stylesheet",
            href="https://unpkg.com/govuk-frontend@4.7.0/dist/govuk/all.css",
        ),
        ui.tags.script(src="https://unpkg.com/govuk-frontend@4.7.0/dist/govuk/all.js"),
        ui.tags.script("window.GOVUKFrontend && window.GOVUKFrontend.initAll();"),
        ui.tags.style(
            """
            :root {
                --gds-ink: #0b0c0c;
                --gds-muted: #505a5f;
                --gds-border: #b1b4b6;
                --gds-surface: #ffffff;
                --gds-panel: #f3f2f1;
                --gds-focus: #ffdd00;
                --gds-accent: #1d70b8;
            }
            body {
                background: var(--gds-panel);
                color: var(--gds-ink);
                font-family: "GDS Transport", "Helvetica Neue", Arial, sans-serif;
            }
            .zenith-app {
                padding: 8px 0 40px;
            }
            .zenith-hero {
                padding: 12px 0 24px;
            }
            .zenith-hero h1 {
                margin: 0 0 8px;
                font-weight: 700;
            }
            .zenith-hero p {
                max-width: 900px;
                margin: 0;
                font-size: 17px;
                color: var(--gds-muted);
            }
            .gds-filter-bar {
                background: var(--gds-surface);
                border: 1px solid var(--gds-border);
                border-radius: 8px;
                padding: 16px 18px;
                margin: 20px 0;
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
                gap: 12px 18px;
            }
            .gds-filter-bar label.form-label {
                font-weight: 700;
                font-size: 16px;
                margin-bottom: 6px;
            }
            .gds-filter-bar .form-select,
            .gds-filter-bar input[type="text"],
            .gds-filter-bar input[type="date"] {
                border: 1px solid var(--gds-border);
                border-radius: 4px;
                min-height: 44px;
                font-size: 16px;
            }
            .gds-tabs .nav-tabs {
                border: none;
                gap: 8px;
                margin-bottom: 0;
            }
            .gds-tabs .nav-tabs .nav-link {
                border: 1px solid var(--gds-border);
                border-bottom: 0;
                background: #e7e8e8;
                color: var(--gds-ink);
                border-radius: 6px 6px 0 0;
                font-weight: 600;
                padding: 10px 14px;
            }
            .gds-tabs .nav-tabs .nav-link.active {
                background: var(--gds-surface);
                border-color: var(--gds-border);
                border-bottom: 0;
            }
            .gds-tabs .tab-content {
                border: 1px solid var(--gds-border);
                background: var(--gds-surface);
                padding: 18px;
                border-radius: 0 8px 8px 8px;
            }
            .gds-card-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 14px;
                margin-bottom: 16px;
            }
            .gds-card {
                background: var(--gds-surface);
                border: 1px solid var(--gds-border);
                border-radius: 8px;
                padding: 14px 16px;
                box-shadow: 0 1px 0 rgba(0,0,0,0.03);
            }
            .gds-card__label {
                font-size: 15px;
                color: var(--gds-muted);
                margin-bottom: 4px;
            }
            .gds-card__value {
                font-size: 32px;
                font-weight: 700;
                line-height: 1.1;
            }
            .gds-card__change {
                color: var(--gds-muted);
                font-size: 14px;
                margin-top: 2px;
            }
            .gds-panel-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
                gap: 14px;
            }
            .gds-panel {
                background: var(--gds-surface);
                border: 1px solid var(--gds-border);
                border-radius: 8px;
                padding: 12px 14px 10px;
                box-shadow: 0 2px 0 rgba(0,0,0,0.03);
            }
            .gds-panel__title {
                font-weight: 700;
                margin: 0 0 6px;
                font-size: 18px;
            }
            .gds-table-wrapper {
                margin-top: 14px;
                border: 1px solid var(--gds-border);
                border-radius: 8px;
                overflow: hidden;
                background: var(--gds-surface);
                padding: 8px;
            }
            table {
                width: 100%;
            }
            .shiny-data-grid table {
                font-size: 14px;
            }
            .gds-secondary {
                color: var(--gds-muted);
                font-size: 15px;
            }
            """
        ),
    ),
    ui.tags.div(
        {"class": "govuk-width-container zenith-app"},
        ui.tags.header(
            {"class": "zenith-hero"},
            ui.tags.span({"class": "govuk-caption-l"}, "Platform analytics"),
            ui.tags.h1("Posit Platform Analytics", class_="govuk-heading-l"),
            ui.tags.p(
                "Track adoption, licences, and tenancy engagement with a GDS-aligned interface.",
                class_="gds-secondary",
            ),
        ),
        ui.tags.div(
            {"class": "gds-filter-bar"},
            ui.input_select(
                "tenancy",
                "Tenancy",
                choices=tenancy_choices(),
                selected="All Tenancies",
                width="100%",
            ),
            ui.input_select(
                "environment",
                "Environment",
                choices=environment_choices(),
                selected="All Environments",
                width="100%",
            ),
            ui.input_select(
                "component",
                "Component",
                choices=component_choices(),
                selected="All Components",
                width="100%",
            ),
            ui.input_date_range(
                "dates",
                "Date range",
                start=default_start,
                end=default_end,
                min=min_date.date(),
                max=max_date.date(),
                width="100%",
            ),
        ),
        ui.tags.div(
            {"class": "gds-tabs"},
            ui.navset_tab(
                # -------------------- Overview --------------------
                ui.nav_panel(
                    "Overview",
                    ui.tags.div(
                        {"class": "gds-card-grid"},
                        metric_card(
                            "Total users",
                            ui.h3(f"{TOTAL_USERS:,}", class_="m-0"),
                            ui.output_text("overview_total_users_change"),
                        ),
                        metric_card(
                            "Active users",
                            ui.output_text("overview_active_users"),
                            ui.output_text("overview_active_users_change"),
                        ),
                        metric_card(
                            "New users",
                            ui.output_text("overview_new_users"),
                            ui.output_text("overview_new_users_change"),
                        ),
                        metric_card(
                            "Total session hours",
                            ui.output_text("overview_session_hours"),
                            ui.output_text("overview_session_hours_change"),
                        ),
                    ),
                    ui.tags.div(
                        {"class": "gds-panel-grid"},
                        panel_card(
                            "Active users & session hours by week",
                            ui.output_ui("overview_timeseries"),
                        ),
                        panel_card(
                            "Active users & session hours by tenancy",
                            ui.output_ui("overview_tenancy_bars"),
                        ),
                    ),
                ),
                # -------------------- Licences --------------------
                ui.nav_panel(
                    "Licences",
                    ui.tags.div(
                        {"class": "gds-card-grid"},
                        metric_card(
                            "Assigned Connect licences",
                            ui.output_text("lic_connect_assigned"),
                        ),
                        metric_card(
                            "Active Connect licences",
                            ui.output_text("lic_connect_active"),
                            ui.output_text("lic_connect_active_change"),
                        ),
                        metric_card(
                            "Assigned Workbench licences",
                            ui.output_text("lic_workbench_assigned"),
                        ),
                        metric_card(
                            "Active Workbench licences",
                            ui.output_text("lic_workbench_active"),
                            ui.output_text("lic_workbench_active_change"),
                        ),
                    ),
                    ui.tags.div({"class": "gds-table-wrapper"}, ui.output_data_frame("lic_table")),
                ),
                # -------------------- Users --------------------
                ui.nav_panel(
                    "Users",
                    ui.tags.div(
                        {"class": "gds-card-grid"},
                        metric_card(
                            "Daily users",
                            ui.output_text("users_daily"),
                            ui.output_text("users_daily_change"),
                        ),
                        metric_card(
                            "Weekly users",
                            ui.output_text("users_weekly"),
                            ui.output_text("users_weekly_change"),
                        ),
                        metric_card(
                            "Active users in period",
                            ui.output_text("users_active"),
                            ui.output_text("users_active_change"),
                        ),
                        metric_card(
                            "Dormant users",
                            ui.output_text("users_dormant"),
                            ui.output_text("users_dormant_change"),
                        ),
                    ),
                    ui.tags.div(
                        {"class": "gds-panel-grid"},
                        panel_card("Usage distribution", ui.output_ui("users_distribution")),
                        panel_card(
                            "Session metrics",
                            ui.tags.ul(
                                ui.tags.li(
                                    "Average session length: ",
                                    ui.output_text("users_avg_session_length"),
                                ),
                                ui.tags.li(
                                    "Average sessions per user: ",
                                    ui.output_text("users_sessions_per_user"),
                                ),
                            ),
                        ),
                    ),
                    ui.tags.div(
                        {"class": "gds-filter-bar", "style": "margin-top:14px"},
                        ui.input_text("pid_search", "Search by PID", placeholder="Enter user ID"),
                    ),
                    ui.tags.div(
                        {"class": "gds-table-wrapper"},
                        ui.output_data_frame("users_table"),
                    ),
                ),
                # -------------------- Tenancies --------------------
                ui.nav_panel(
                    "Tenancies",
                    ui.tags.div(
                        {"class": "gds-table-wrapper"},
                        ui.output_data_frame("tenancies_table"),
                    ),
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

    @reactive.Calc
    def filtered_users_by_pid():
        """Filter users table by PID search"""
        df = filtered_users().copy()
        pid_search = input.pid_search()
        if pid_search and pid_search.strip():
            df = df[df["userId"].str.contains(pid_search.strip(), case=False, na=False)]
        return df

    @reactive.Calc
    def new_users_current():
        """Count of users first seen in current period"""
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
        
        # New users: those who appear in current period but not in any earlier data
        comp_start, _ = comparison_period()
        before_period = df[df["lastLogin"] < comp_start]
        in_current = df[(df["lastLogin"] >= start) & (df["lastLogin"] <= end)]
        new_ids = set(in_current["userId"]) - set(before_period["userId"])
        return len(new_ids)

    @reactive.Calc
    def new_users_previous():
        """Count of new users in previous period for comparison"""
        tenancy_val = input.tenancy()
        env_val = input.environment()
        comp_val = input.component()
        comp_start, comp_end = comparison_period()
        
        df = users.copy()
        if tenancy_val != "All Tenancies":
            df = df[df["tenancy"] == tenancy_val]
        if env_val != "All Environments":
            df = df[df["environment"] == env_val]
        if comp_val != "All Components":
            df = df[df["component"] == comp_val]
        
        # Get date before comparison period
        before_comp = comp_start - timedelta(days=1)
        before_period = df[df["lastLogin"] < before_comp]
        in_prev = df[(df["lastLogin"] >= comp_start) & (df["lastLogin"] <= comp_end)]
        new_ids = set(in_prev["userId"]) - set(before_period["userId"])
        return len(new_ids)

    @reactive.Calc
    def total_session_hours_current():
        """Total session hours in current period"""
        df = filtered_timeseries()
        return df["sessionHours"].sum() if not df.empty else 0

    @reactive.Calc
    def total_session_hours_previous():
        """Total session hours in previous period"""
        start, end = comparison_period()
        df = timeseries[(timeseries["date"] >= start) & (timeseries["date"] <= end)].copy()
        return df["sessionHours"].sum() if not df.empty else 0

    @reactive.Calc
    def daily_active_users_current():
        """Users logging in at least once per day in current period (count)"""
        # Note: users table has lastLogin but not granular daily stats
        # Approximate: count distinct users in period
        return len(filtered_users())

    @reactive.Calc
    def weekly_active_users_current():
        """Users logging in at least once per week in current period"""
        # Approximate: distinct users in filtered dataset
        return len(filtered_users())

    @reactive.Calc
    def any_login_users_current():
        """Users logging in at least once in current period"""
        return len(filtered_users())

    @reactive.Calc
    def not_logged_in_current():
        """Users not logged in during current period"""
        start, end = current_period()
        tenancy_val = input.tenancy()
        env_val = input.environment()
        comp_val = input.component()
        
        all_users = users.copy()
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
        """Average session length (hours) in current period"""
        df = filtered_timeseries()
        if df.empty or len(filtered_users()) == 0:
            return 0.0
        total_hours = df["sessionHours"].sum()
        num_users = len(filtered_users())
        return total_hours / num_users if num_users > 0 else 0.0

    @reactive.Calc
    def sessions_per_user_current():
        """Average sessions per user in current period (estimate from data)"""
        # Estimate: if we have session hours, divide by typical session length (8.5 hours per day assumption)
        # This is a proxy metric since detailed session data isn't available
        df = filtered_timeseries()
        num_users = len(filtered_users())
        num_days = len(df) if not df.empty else 1
        if num_users == 0 or num_days == 0:
            return 0.0
        avg_active_users_per_day = df["activeUsers"].mean() if "activeUsers" in df.columns else 0
        return avg_active_users_per_day if avg_active_users_per_day > 0 else 0.0

    @output
    @render.text
    def overview_active_users():
        # Active users = distinct users with lastLogin in current period (with filters)
        return f"{len(filtered_users()):,}"

    @output
    @render.text
    def overview_total_users_change():
        current = len(users)
        prev = len(users)  # Total users is static, so no change
        change = 0.0
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
        return render_plotly(fig)

    @output
    @render.ui
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
        return render_plotly(fig)

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
    def lic_connect_assigned():
        tenancy_val = input.tenancy()
        comp_val = input.component()
        lic_df = licences.copy()
        if tenancy_val != "All Tenancies":
            lic_df = lic_df[lic_df["tenancy"] == tenancy_val]
        if comp_val != "All Components":
            lic_df = lic_df[lic_df["component"] == comp_val]
        
        connect_assigned = lic_df.loc[
            lic_df["component"] == "Connect", "licencesUsed"
        ].sum()
        return f"{int(connect_assigned):,} of {TOTAL_CONNECT_LICENCES:,}"

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
        connect_active_prev, _ = _licence_active_users_for_period(
            prev_start, prev_end
        )
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
        lic_df = licences.copy()
        if tenancy_val != "All Tenancies":
            lic_df = lic_df[lic_df["tenancy"] == tenancy_val]
        if comp_val != "All Components":
            lic_df = lic_df[lic_df["component"] == comp_val]
        
        workbench_assigned = lic_df.loc[
            lic_df["component"] == "Workbench", "licencesUsed"
        ].sum()
        return f"{int(workbench_assigned):,} of {TOTAL_WORKBENCH_LICENCES:,}"

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
        _, workbench_active_prev = _licence_active_users_for_period(
            prev_start, prev_end
        )
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
        # Rename columns to title case for better display
        final.columns = ["Tenancy", "Component", "Assigned Licences", "Active Licences"]
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
        dormant = TOTAL_USERS - len(filtered_users())
        return f"{dormant:,}"

    @output
    @render.text
    def users_dormant_change():
        dormant_current = TOTAL_USERS - len(filtered_users())
        dormant_prev = TOTAL_USERS - len(filtered_users_prev_period())
        
        if dormant_prev > 0:
            change = (dormant_current - dormant_prev) / dormant_prev * 100
        else:
            change = 0.0
        arrow = "▲" if change >= 0 else "▼"
        return f"{arrow} {change:.1f}% vs previous period"

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
    def users_daily_change():
        df_current = filtered_timeseries()
        if df_current.empty:
            return ""
        latest_current = df_current.sort_values("date").iloc[-1]
        daily_current = latest_current["powerUsers"]
        
        prev_start, prev_end = comparison_period()
        df_prev = timeseries[
            (timeseries["date"] >= prev_start) & (timeseries["date"] <= prev_end)
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
        df_prev = timeseries[
            (timeseries["date"] >= prev_start) & (timeseries["date"] <= prev_end)
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
            fig = px.pie(title="No data for selected period")
            return render_plotly(fig)

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
        return render_plotly(fig)

    @output
    @render.text
    def users_avg_session_length():
        hours = avg_session_length_current()
        minutes = hours * 60
        return f"{minutes:.0f} minutes"

    @output
    @render.text
    def users_sessions_per_user():
        sessions = sessions_per_user_current()
        return f"{sessions:.1f}"

    @output
    @render.data_frame
    def users_table():
        df = filtered_users_by_pid().copy()
        if df.empty:
            # Return an empty frame with the correct columns so the table still renders
            return pd.DataFrame(
                columns=["User ID", "Tenancy", "Component", "Environment", "Last login", "Login count"]
            )

        df = df.sort_values("lastLogin", ascending=False)
        out = df[["userId", "tenancy", "component", "environment", "lastLogin", "loginCount"]].copy()
        out.columns = ["User ID", "Tenancy", "Component", "Environment", "Last login", "Login count"]
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
