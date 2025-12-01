from shiny import ui

import data


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
        ui.tags.h2({"class": "gds-panel__title govuk-heading-m"}, title),
        body,
    )


app_ui = ui.page_fluid(
    ui.tags.head(
        ui.tags.title("Posit Platform Analytics"),
        ui.tags.link(
            rel="stylesheet",
            href="https://unpkg.com/govuk-frontend@4.7.0/dist/govuk/all.css",
        ),
        ui.tags.script(src="https://unpkg.com/govuk-frontend@4.7.0/dist/govuk/all.js"),
        ui.tags.script("window.GOVUKFrontend && window.GOVUKFrontend.initAll();"),
        ui.tags.script("document.documentElement.setAttribute('lang','en');"),
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
            .gds-table-wrapper table {
                width: 100% !important;
            }
            .dataTables_wrapper .dataTable {
                width: 100% !important;
            }
            .dataTables_wrapper .dataTables_scrollHeadInner,
            .dataTables_wrapper .dataTables_scrollHeadInner table,
            .dataTables_wrapper .dataTables_scrollBody table {
                width: 100% !important;
            }
            .default-chevron {
                font-size: 12px;
                margin-left: 4px;
                color: #505a5f;
            }
            table.dataTable thead th.sorting_desc .default-chevron,
            table.dataTable thead th.sorting_asc .default-chevron {
                display: none;
            }
            /* Default sort hint only when DataTables header is in unsorted state */
            .dataTable thead th.sorting:first-child::after {
                content: "▲";
                font-size: 12px;
                margin-left: 4px;
                color: #505a5f;
            }
            .gds-secondary {
                color: var(--gds-muted);
                font-size: 15px;
            }
            .gds-progress {
                background: #efefef;
                border-radius: 999px;
                height: 10px;
                overflow: hidden;
                width: 100%;
            }
            .gds-progress__bar {
                height: 100%;
                border-radius: 999px;
            }
            .gds-pill {
                background: #f3f2f1;
                border-radius: 8px;
                padding: 12px 14px;
                display: flex;
                align-items: flex-start;
                justify-content: space-between;
                gap: 12px;
                margin-bottom: 10px;
                border: 1px solid #dcdcdc;
            }
            .gds-pill__label {
                display: flex;
                align-items: center;
                gap: 8px;
                font-weight: 600;
            }
            .gds-pill__icon {
                width: 24px;
                height: 24px;
                border-radius: 12px;
                background: #d8e8f4;
                color: #1d70b8;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                font-size: 14px;
            }
            .gds-pill__metrics {
                display: flex;
                flex-direction: column;
                align-items: flex-end;
                gap: 2px;
            }
            .gds-pill__value-lg {
                font-size: 24px;
                font-weight: 700;
                line-height: 1.1;
            }
            .gds-pill__sub {
                color: var(--gds-muted);
                font-size: 14px;
            }
            .gds-pill__change {
                color: #0b7a0b;
                font-weight: 600;
                font-size: 14px;
            }
            .gds-dist-row {
                display: grid;
                grid-template-columns: 1fr auto;
                align-items: center;
                gap: 10px;
                margin-bottom: 10px;
            }
            .gds-dist-label {
                font-weight: 600;
            }
            .gds-dist-val {
                color: var(--gds-muted);
            }
            """
        ),
    ),
    ui.tags.main(
        {"class": "govuk-width-container zenith-app", "role": "main"},
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
                choices=data.tenancy_choices(),
                selected="All Tenancies",
                width="100%",
            ),
            ui.input_select(
                "environment",
                "Environment",
                choices=data.environment_choices(),
                selected="All Environments",
                width="100%",
            ),
            ui.input_select(
                "component",
                "Component",
                choices=data.component_choices(),
                selected="All Components",
                width="100%",
            ),
            ui.input_date_range(
                "dates",
                "Date range",
                start=data.default_start,
                end=data.default_end,
                min=data.min_date.date(),
                max=data.max_date.date(),
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
                            f"{data.TOTAL_USERS:,}",
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
                            "Session engagement metrics",
                            ui.output_ui("users_session_metrics"),
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
