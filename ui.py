from shiny import ui

import data


def metric_card(title, value, change=None, aria_label=None):
    """Lightweight stat card used across tabs."""
    parts = [
        ui.tags.div({"class": "app-card__label"}, title),
        ui.tags.div({"class": "app-card__value"}, value),
    ]
    if change is not None:
        parts.append(ui.tags.div({"class": "app-card__change"}, change))
    return ui.tags.div(
        {"class": "app-card", "role": "group", "aria-label": aria_label or title},
        *parts,
    )


def panel_card(title, body):
    """Panel wrapper matching the React mock styling."""
    return ui.tags.div(
        {"class": "app-panel"},
        ui.tags.h2({"class": "app-panel__title"}, title),
        body,
    )


app_ui = ui.page_fluid(
    ui.tags.head(
        ui.tags.title("Posit Platform Analytics"),
        ui.tags.script("document.documentElement.setAttribute('lang','en');"),
        ui.tags.script(
            """
            document.addEventListener('DOMContentLoaded', function() {
                const stripAria = () => {
                    document.querySelectorAll('table[aria-multiselectable]').forEach((tbl) => {
                        tbl.removeAttribute('aria-multiselectable');
                    });
                };
                stripAria();
                document.addEventListener('shiny:domupdate', stripAria);
                const observer = new MutationObserver(stripAria);
                observer.observe(document.body, { childList: true, subtree: true, attributes: true });
            });
            """
        ),
        ui.tags.style(
            """
            :root {
                --ink: #0f172a;
                --muted: #475467;
                --border: #d0d5dd;
                --surface: #ffffff;
                --panel: #f5f7fb;
                --accent: #2563eb;
            }
            body {
                background: var(--panel);
                color: var(--ink);
                font-family: "Inter", "Segoe UI", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
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
                color: var(--muted);
            }
            .app-filter-bar {
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 8px;
                padding: 16px 18px;
                margin: 20px 0;
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
                gap: 12px 18px;
            }
            .app-filter-bar label.form-label {
                font-weight: 700;
                font-size: 16px;
                margin-bottom: 6px;
            }
            .app-filter-bar .form-select,
            .app-filter-bar input[type="text"],
            .app-filter-bar input[type="date"] {
                border: 1px solid var(--border);
                border-radius: 4px;
                min-height: 44px;
                font-size: 16px;
            }
            .app-tabs .nav-tabs {
                border: none;
                gap: 8px;
                margin-bottom: 0;
            }
            .app-tabs .nav-tabs .nav-link {
                border: 1px solid var(--border);
                border-bottom: 0;
                background: #e7e8e8;
                color: var(--ink);
                border-radius: 6px 6px 0 0;
                font-weight: 600;
                padding: 10px 14px;
            }
            .app-tabs .nav-tabs .nav-link.active {
                background: var(--surface);
                border-color: var(--border);
                border-bottom: 0;
            }
            .app-tabs .tab-content {
                border: 1px solid var(--border);
                background: var(--surface);
                padding: 18px;
                border-radius: 0 8px 8px 8px;
            }
            .app-card-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 14px;
                margin-bottom: 16px;
            }
            .app-card {
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 8px;
                padding: 14px 16px;
                box-shadow: 0 1px 0 rgba(0,0,0,0.03);
            }
            .app-card__label {
                font-size: 15px;
                color: var(--muted);
                margin-bottom: 4px;
            }
            .app-card__value {
                font-size: 32px;
                font-weight: 700;
                line-height: 1.1;
            }
            .app-card__change {
                color: var(--muted);
                font-size: 14px;
                margin-top: 2px;
            }
            .app-panel-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
                gap: 14px;
            }
            .app-panel {
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 8px;
                padding: 12px 14px 10px;
                box-shadow: 0 2px 0 rgba(0,0,0,0.03);
            }
            .app-panel__title {
                font-weight: 700;
                margin: 0 0 6px;
                font-size: 18px;
            }
            .app-table-wrapper {
                margin-top: 14px;
                border: 1px solid var(--border);
                border-radius: 8px;
                overflow: hidden;
                background: var(--surface);
                padding: 8px;
            }
            table {
                width: 100%;
            }
            .shiny-data-grid table {
                font-size: 14px;
            }
            .app-table-wrapper table {
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
            .app-muted {
                color: var(--muted);
                font-size: 15px;
            }
            .app-progress {
                background: #efefef;
                border-radius: 999px;
                height: 10px;
                overflow: hidden;
                width: 100%;
            }
            .app-progress__bar {
                height: 100%;
                border-radius: 999px;
            }
            .app-pill {
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
            .app-pill__label {
                display: flex;
                align-items: center;
                gap: 8px;
                font-weight: 600;
            }
            .app-pill__icon {
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
            .app-pill__metrics {
                display: flex;
                flex-direction: column;
                align-items: flex-end;
                gap: 2px;
            }
            .app-pill__value-lg {
                font-size: 24px;
                font-weight: 700;
                line-height: 1.1;
            }
            .app-pill__sub {
                color: var(--muted);
                font-size: 14px;
            }
            .app-pill__change {
                color: #0b7a0b;
                font-weight: 600;
                font-size: 14px;
            }
            .app-dist-row {
                display: grid;
                grid-template-columns: 1fr auto;
                align-items: center;
                gap: 16px;
                margin-bottom: 6px;
            }
            .app-dist-label {
                font-weight: 600;
            }
            .app-dist-val {
                color: var(--muted);
                font-weight: 600;
            }
            /* Force DataTables to fill wrappers */
            .app-table-wrapper .dataTables_wrapper,
            .app-table-wrapper .dataTables_scroll,
            .app-table-wrapper .dataTables_scrollHead,
            .app-table-wrapper .dataTables_scrollBody,
            .app-table-wrapper table.dataTable {
                width: 100% !important;
            }
            .app-table-wrapper table.dataTable {
                margin: 0 !important;
            }
            .users-top-row {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 14px;
                align-items: stretch;
            }
            .users-metric-stack {
                display: grid;
                grid-template-rows: repeat(3, 1fr);
                gap: 10px;
                height: 100%;
            }
            .users-metric-stack .app-card {
                height: 100%;
            }
            .usage-frequency-panel {
                display: flex;
                flex-direction: column;
                height: 100%;
            }
            .usage-frequency-list {
                flex: 1;
                display: flex;
                flex-direction: column;
                gap: 14px;
            }
            .full-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 14px;
            }
            .full-table th,
            .full-table td {
                border: 1px solid #d0d0d0;
                padding: 8px 10px;
            }
            .full-table th {
                background: #f3f2f1;
                font-weight: 700;
                text-align: left;
            }
            .hero-bar {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 16px;
            }
            .shared-tab-panel {
                border: 1px solid var(--border);
                background: var(--surface);
                padding: 18px;
                border-radius: 0 0 8px 8px;
                margin-top: -1px;
                box-shadow: 0 1px 0 rgba(0,0,0,0.03);
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            .licence-filter-row {
                display: grid;
                grid-template-columns: 1fr;
                gap: 12px;
                align-items: stretch;
            }
            .licence-filter-row > * {
                height: 100%;
            }
            .licence-card {
                height: 100%;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }
            .filter-card {
                height: 100%;
                border: 1px solid var(--border);
                border-radius: 8px;
                background: var(--surface);
                padding: 12px 14px;
                display: flex;
                align-items: center;
            }
            .filter-card .app-filter-bar {
                border: none;
                padding: 0;
                margin: 0;
                width: 100%;
                align-content: center;
            }
            .download-bar {
                display: flex;
                align-items: flex-end;
                gap: 10px;
                justify-content: space-between;
            }
            .download-bar .form-group {
                flex: 1;
                margin-bottom: 0;
            }
            .beta-banner {
                background: #ffd24d;
                border: 1px solid #e0b500;
                border-radius: 8px;
                padding: 12px 14px;
                margin-bottom: 12px;
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .beta-banner__title {
                font-weight: 700;
                margin: 0;
            }
            .beta-banner__text {
                margin: 0;
                color: var(--muted);
            }
            .beta-banner__action {
                margin-left: auto;
            }
            /* Keep Plotly charts contained within panels */
            .app-panel .plotly-graph-div {
                width: 100% !important;
                max-width: 100%;
                overflow: hidden;
            }
            .app-panel .plot-container {
                width: 100% !important;
                max-width: 100%;
                overflow: hidden;
            }
            .app-panel {
                overflow: hidden;
            }
            .app-tabs .tab-content {
                display: block;
                padding: 0;
                border: none;
                min-height: 0;
            }
            """
        ),
    ),
    ui.tags.main(
        {"class": "zenith-app", "role": "main"},
        ui.tags.div(
            {"class": "beta-banner", "role": "status", "aria-label": "Beta notice"},
            ui.tags.div(
                ui.tags.p("Beta", class_="beta-banner__title"),
                ui.tags.p(
                    "This is a beta version of the data dashboard. Please let us know if you have any comments or suggestions",
                    class_="beta-banner__text",
                ),
            ),
            ui.tags.a(
                "Feedback",
                href="#",
                class_="btn btn-primary beta-banner__action",
                role="button",
            ),
        ),
        ui.tags.div(
            {"class": "hero-bar"},
            ui.tags.header(
                {"class": "zenith-hero"},
                ui.tags.h1("Posit Usage Data Dashboard"),
                ui.tags.p(
                    "Enabling more people to use Posit, Python and R more often.",
                    class_="app-muted",
                ),
            ),
        ),
        ui.tags.div(
            {"class": "app-tabs"},
            ui.navset_tab(
                ui.nav_panel(
                    "Connect",
                    value="connect",
                ),
                ui.nav_panel(
                    "Workbench",
                    value="workbench",
                ),
                ui.nav_panel(
                    "Tenancies",
                    ui.tags.div(),  # content rendered via panel_conditional below
                    value="tenancies",
                ),
                id="main_tabs",
            ),
            ui.panel_conditional(
                "input.main_tabs == 'connect' || input.main_tabs == 'workbench'",
                    ui.tags.div(
                        {"class": "shared-tab-panel"},
                    ui.tags.div(
                        {"class": "licence-filter-row"},
                        ui.tags.div(
                            {"class": "filter-card"},
                            ui.tags.div(
                                {"class": "app-filter-bar"},
                                ui.input_date_range(
                                    "dates",
                                    "Date range",
                                    start=data.default_start,
                                    end=data.default_end,
                                    min=data.min_date.date(),
                                    max=data.max_date.date(),
                                    width="100%",
                                ),
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
                            ),
                        ),
                    ),
                    ui.tags.div(
                        {"class": "app-card-grid", "style": "margin-top:10px;"},
                        metric_card(
                            "Total users",
                            ui.output_text("users_total"),
                            ui.output_text("overview_total_users_change"),
                        ),
                        metric_card(
                            "New users",
                            ui.output_text("overview_new_users"),
                            ui.output_text("overview_new_users_change"),
                        ),
                        metric_card(
                            "Active users",
                            ui.output_text("users_active"),
                            ui.output_text("users_active_change"),
                        ),
                        metric_card(
                            "Inactive users",
                            ui.output_text("users_inactive"),
                        ),
                    ),
                    ui.tags.div(
                        {"class": "app-panel-grid", "style": "margin-top:10px"},
                        panel_card("Avg logins per week", ui.output_ui("users_logins_pie")),
                    ),
                    ui.tags.div(
                        {"class": "app-panel-grid", "style": "margin-top:10px"},
                        panel_card("Total and active users per week", ui.output_ui("users_trend")),
                    ),
                    ui.tags.div(
                        {"class": "app-panel-grid", "style": "margin-top:10px"},
                        panel_card("Logins per week", ui.output_ui("users_frequency")),
                    ),
                    ui.tags.div(
                        {"class": "app-table-wrapper"},
                        ui.tags.div(
                            {"class": "download-bar", "style": "margin:0 0 8px 0;"},
                            ui.input_text("pid_search", "Search by PID", placeholder="Enter a PID"),
                            ui.download_button("download_users", "Download CSV", class_="btn btn-primary"),
                        ),
                        ui.output_ui("users_table"),
                    ),
                ),
            ),
            ui.panel_conditional(
                "input.main_tabs == 'tenancies'",
                ui.tags.div(
                    {"class": "shared-tab-panel"},
                    ui.tags.div(
                        {"class": "filter-card"},
                        ui.tags.div(
                            {"class": "app-filter-bar"},
                            ui.input_date_range(
                                "tenancy_dates",
                                "Date range",
                                start=data.default_start,
                                end=data.default_end,
                                min=data.min_date.date(),
                                max=data.max_date.date(),
                                width="100%",
                            ),
                            ui.input_select(
                                "tenancy_environment",
                                "Environment",
                                choices=data.environment_choices(),
                                selected="All Environments",
                                width="100%",
                            ),
                        ),
                    ),
                    ui.tags.div(
                        {"class": "app-panel-grid", "style": "margin-bottom:12px; grid-template-columns: 1fr;"},
                        panel_card("Total users", ui.output_ui("tenancy_licence_bars")),
                        panel_card("Active users (current range)", ui.output_ui("tenancy_active_bars")),
                    ),
                    ui.tags.div(
                        {"class": "app-panel-grid", "style": "margin-bottom:12px; grid-template-columns: 1fr;"},
                        panel_card("Logins (current range)", ui.output_ui("tenancy_logins_bars")),
                    ),
                    ui.tags.div(
                        {"class": "app-table-wrapper", "style": "margin-top:10px;"},
                        ui.tags.div(
                            {"style": "text-align:right; margin-bottom:6px;"},
                            ui.download_button("download_tenancies", "Download CSV", class_="btn btn-primary"),
                        ),
                        ui.output_ui("tenancies_table_all"),
                    ),
                ),
            ),
        ),
    ),
)
