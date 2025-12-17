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
        ui.tags.script(
            """
            function makeSortable(table) {
                if (table.dataset.sortableAttached === "true") return;
                const getCellValue = (row, idx) => {
                    const txt = row.children[idx].innerText.trim();
                    const num = parseFloat(txt.replace(/,/g, ''));
                    if (!Number.isNaN(num) && /^-?\\d+[\\d,\\.]*$/.test(txt)) {
                        return num;
                    }
                    const time = Date.parse(txt);
                    if (!Number.isNaN(time)) {
                        return time;
                    }
                    return txt.toLowerCase();
                };
                const comparer = (idx, asc) => (a, b) => {
                    const v1 = getCellValue(asc ? a : b, idx);
                    const v2 = getCellValue(asc ? b : a, idx);
                    if (v1 === v2) return 0;
                    return v1 > v2 ? 1 : -1;
                };
                table.querySelectorAll('th').forEach((th, idx) => {
                    th.style.cursor = 'pointer';
                    th.addEventListener('click', () => {
                        // reset indicators
                        table.querySelectorAll('th').forEach(header => {
                            header.classList.remove('sort-asc', 'sort-desc');
                        });
                        const tbody = table.tBodies[0];
                        const asc = th.asc = !th.asc;
                        th.classList.add(asc ? 'sort-asc' : 'sort-desc');
                        Array.from(tbody.querySelectorAll('tr'))
                            .sort(comparer(idx, asc))
                            .forEach(tr => tbody.appendChild(tr));
                    });
                });
                table.dataset.sortableAttached = "true";
            }
            function attachSortables() {
                document.querySelectorAll('table.sortable').forEach(makeSortable);
            }
            document.addEventListener('DOMContentLoaded', attachSortables);
            document.addEventListener('shiny:domupdate', attachSortables);
            const observer = new MutationObserver(attachSortables);
            observer.observe(document.body, { childList: true, subtree: true });
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
            .govuk-width-container {
                max-width: 1020px;
                margin: 0 auto;
                padding: 0 16px;
            }
            .govuk-skip-link {
                position: absolute;
                top: -40px;
                left: 0;
                padding: 8px 16px;
                background: #fd0;
                color: #0b0c0c;
                font-weight: 700;
                text-decoration: none;
                z-index: 100;
            }
            .govuk-skip-link:focus {
                top: 0;
                outline: 3px solid transparent;
                box-shadow: 0 0 0 3px #0b0c0c;
            }
            .govuk-service-header {
                background: #0b0c0c;
                color: #fff;
            }
            .govuk-service-header__content {
                display: flex;
                align-items: center;
                min-height: 52px;
                gap: 12px;
                color: inherit;
            }
            .govuk-crown {
                display: inline-flex;
                align-items: center;
            }
            .govuk-crown img {
                height: 32px;
                width: auto;
                display: block;
            }
            .govuk-service-header__link {
                color: #fff;
                font-weight: 700;
                font-size: 20px;
                text-decoration: none;
            }
            .govuk-service-header__link:focus {
                outline: 3px solid #fd0;
                outline-offset: 2px;
                color: #0b0c0c;
                background: #fd0;
            }
            .zenith-app {
                padding: 8px 16px 40px;
                max-width: 1020px;
                margin: 0 auto;
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
            table.sortable th.sort-asc::after {
                content: " ▲";
                font-size: 12px;
                opacity: 1;
            }
            table.sortable th.sort-desc::after {
                content: " ▼";
                font-size: 12px;
                opacity: 1;
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
            .govuk-phase-banner {
                padding: 8px 0 12px;
                border-bottom: 1px solid #b1b4b6;
            }
            .govuk-phase-banner__content {
                margin: 0;
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 16px;
            }
            .govuk-phase-banner__content__tag {
                margin: 0;
            }
            .govuk-phase-banner__text {
                color: var(--ink);
            }
            .govuk-tag {
                display: inline-block;
                background: #1d70b8;
                color: #fff;
                font-weight: 700;
                padding: 2px 8px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                font-size: 14px;
            }
            .govuk-link {
                color: #1d70b8;
                text-decoration: underline;
            }
            .govuk-link:focus {
                outline: 3px solid #fd0;
                outline-offset: 2px;
                background: #fd0;
                color: #0b0c0c;
            }
            .table-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-end;
                gap: 10px;
                margin-bottom: 4px;
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
    ui.tags.a("Skip to main content", href="#main-content", class_="govuk-skip-link"),
    ui.tags.header(
        {"class": "govuk-service-header", "role": "banner"},
        ui.tags.div(
            {"class": "govuk-width-container"},
            ui.tags.div(
                    {"class": "govuk-service-header__content"},
                    ui.tags.span(
                        {"class": "govuk-crown", "aria-hidden": "true"},
                        ui.tags.img(
                            src="data:image/png;base64,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",
                        alt="",
                        width="40",
                        height="32",
                        loading="lazy",
                    ),
                ),
                ui.tags.a(
                    "Posit Platform Analytics",
                    href="#",
                    class_="govuk-service-header__link",
                    aria_label="Posit Platform Analytics home",
                ),
            ),
        ),
    ),
    ui.tags.main(
        {"class": "zenith-app", "role": "main", "id": "main-content"},
        ui.tags.div(
            {"class": "govuk-phase-banner", "data-module": "govuk-phase-banner", "role": "status", "aria-label": "Beta notice"},
            ui.tags.p(
                {"class": "govuk-phase-banner__content"},
                ui.tags.strong("Beta", class_="govuk-tag govuk-phase-banner__content__tag"),
                ui.tags.span(
                    {"class": "govuk-phase-banner__text"},
                    "This is a new service - your ",
                    ui.tags.a(
                        "feedback",
                        href="https://forms.office.com/e/hVV9jZpfhp",
                        target="_blank",
                        rel="noreferrer noopener",
                        class_="govuk-link",
                    ),
                    " will help us improve it.",
                ),
            ),
        ),
        ui.tags.div(
            {"class": "hero-bar"},
            ui.tags.header(
                {"class": "zenith-hero"},
                ui.tags.h1("Posit Platform Analytics"),
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
                            ),
                        ),
                    ),
                    ui.tags.div(
                        {"class": "app-card-grid", "style": "margin-top:10px;"},
                        metric_card(
                            "Total users to date",
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
                            ui.output_text("users_inactive_change"),
                        ),
                    ),
                    ui.tags.div(
                        {"class": "app-panel-grid", "style": "margin-top:10px"},
                        panel_card("Total and active users over time", ui.output_ui("users_trend")),
                    ),
                    ui.tags.div(
                        {"class": "app-panel-grid", "style": "margin-top:10px"},
                        panel_card("Avg logins per week", ui.output_ui("users_logins_pie")),
                    ),
                    ui.tags.div(
                        {"class": "app-panel-grid", "style": "margin-top:10px"},
                        panel_card("Logins over time", ui.output_ui("users_frequency")),
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
                        ),
                    ),
                    ui.tags.div(
                        {"class": "app-panel-grid", "style": "margin-bottom:12px; grid-template-columns: 1fr;"},
                        panel_card("Total users", ui.output_ui("tenancy_licence_bars")),
                        panel_card("Active users", ui.output_ui("tenancy_active_bars")),
                    ),
                    ui.tags.div(
                        {"class": "app-panel-grid", "style": "margin-bottom:12px; grid-template-columns: 1fr;"},
                        panel_card("Total logins", ui.output_ui("tenancy_logins_bars")),
                    ),
                    ui.tags.div(
                        {"class": "app-table-wrapper", "style": "margin-top:10px;"},
                        ui.tags.div(
                            {"class": "table-header", "style": "margin-bottom:6px;"},
                            ui.tags.div({"class": "app-panel__title", "style": "margin:0;"}, "Connect"),
                            ui.download_button("download_tenancies_connect", "Download CSV", class_="btn btn-primary"),
                        ),
                        ui.output_ui("tenancies_table_connect"),
                        ui.tags.hr(),
                        ui.tags.div(
                            {"class": "table-header", "style": "margin:6px 0;"},
                            ui.tags.div({"class": "app-panel__title", "style": "margin:0;"}, "Workbench"),
                            ui.download_button("download_tenancies_workbench", "Download CSV", class_="btn btn-primary"),
                        ),
                        ui.output_ui("tenancies_table_workbench"),
                        
                    ),
                ),
            ),
        ),
    ),
)
