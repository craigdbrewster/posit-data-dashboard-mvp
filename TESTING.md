# Testing Guidance

- **Run app locally**: `shiny run --reload app.py` (or `python3 app.py`) from the repo root.
- **Quick sanity checks**:
  - Pick a single day and set both date inputs to that day. Verify:
    - Total = cumulative unique users up to that day.
    - New = users whose first login is that day.
    - Active = unique users with a login that day.
    - Inactive = Total – Active.
  - Switch tenancy/environment filters; all cards/charts/tables should change and remain internally consistent.
  - Toggle between Connect and Workbench and repeat the single-day check.
- **CSV spot checks**:
  - Download the Users CSV, pick a PID, and confirm last login and total logins match the JSON for the selected range.
  - Download the Tenancies CSV and ensure per-tenancy totals sum to the Total for the selected component.
- **Known data quirks**: `data.py` enforces a single tenancy/product per user (latest login wins), so counts should never double-count users across tenancies.
