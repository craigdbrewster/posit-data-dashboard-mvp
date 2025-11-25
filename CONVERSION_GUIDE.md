# React to Python Shiny Conversion Guide

## Overview
This guide will help you convert the Posit Platform Analytics dashboard from React/TypeScript to Python Shiny.

## Step-by-Step Instructions

### Step 1: Export the Current Codebase
1. In Lovable, click the **Dev Mode** toggle (top left)
2. Review all the component files to understand the logic
3. Take note of the calculations in each tab component

### Step 2: Set Up Python Shiny Environment
```bash
# Install Python Shiny
pip install shiny pandas plotly

# Create your project directory
mkdir posit-analytics-dashboard
cd posit-analytics-dashboard
```

### Step 3: Use the Provided CSV Files
The following CSV files are included in this package:
- `data/users.csv` - User activity data
- `data/tenancies.csv` - Tenancy metrics
- `data/licences.csv` - Licence usage by tenancy and component
- `data/timeseries.csv` - Daily time series data

### Step 4: Key Components to Convert

#### A. Overview Tab
**Metrics to calculate:**
- Total users: 10,500 (static)
- Active users: Count of users in date range
- New users: 50 (static for MVP)
- Total session hours: activeUsers × 8.5

**Charts:**
1. Line chart: Active users + Session hours per week
2. Bar chart: Active users + Session hours by tenancy (top 5)

**Period comparison:**
- Calculate previous period of same length
- Show percentage change for active users, new users, session hours

#### B. Licences Tab
**Metrics to calculate:**
- Assigned Connect: Sum of Connect licences used (total: 10,000)
- Active Connect: Count of Connect users in date range
- Assigned Workbench: Sum of Workbench licences used (total: 5,000)
- Active Workbench: Count of Workbench users in date range

**Period comparison:**
- Compare active licences with previous period

**Table:**
- Columns: Tenancy, Component, Assigned licences, Active licences
- Sortable by all columns
- Show totals for Connect and Workbench

#### C. Users Tab
**Metrics to calculate:**
- Daily users: Users with avg days between logins ≤ 1.5
- Weekly users: Users with avg days between logins ≤ 7 and > 1.5
- Active users in period: Total users with logins in date range
- Dormant users: 10,500 - active users

**Session metrics (mock values for MVP):**
- Average session length: 45 minutes (+7.1% vs previous)
- Average sessions per user: 8.5 (+9.0% vs previous)

**Charts:**
- Distribution bars showing daily/weekly/other/dormant percentages

**Table:**
- Columns: User ID, Tenancy, Component, Environment, Last login, Login count
- Show first 100 rows
- Sortable by all columns

#### D. Tenancies Tab
**Table:**
- Columns: Tenancy, Total users, Active users, Assigned Connect, Active Connect, Assigned Workbench, Active Workbench
- Sortable by all columns

### Step 5: Filter Implementation
Filters apply across all tabs:
- **Tenancy**: Dropdown with "All Tenancies" + individual tenancies
- **Environment**: Dropdown with "All Environments", "Production", "Development", "Staging"
- **Component**: Dropdown with "All Components", "Connect", "Workbench"
- **Date Range**: Start date and end date pickers (default: last 30 days)

### Step 6: Key Calculations

#### Period Comparison
```python
# Calculate comparison period
day_diff = (end_date - start_date).days
comp_start = start_date - timedelta(days=day_diff + 1)
comp_end = start_date - timedelta(days=1)

# Calculate percentage change
change = ((current - previous) / previous * 100) if previous > 0 else 0
```

#### Weekly Aggregation
```python
# Group time series by week
weekly_data = timeseries_df.resample('W', on='date').agg({
    'activeUsers': 'mean',
    'logins': 'sum'
})
```

#### User Categorization
```python
# Daily users: average ≤ 1.5 days between logins
avg_days = date_range_days / user['loginCount']
if avg_days <= 1.5:
    category = 'daily'
elif avg_days <= 7:
    category = 'weekly'
else:
    category = 'occasional'
```

### Step 7: Python Shiny Structure
Your `app.py` should have this structure:

```python
from shiny import App, ui, render, reactive
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

# Load data
users_df = pd.read_csv('data/users.csv')
tenancies_df = pd.read_csv('data/tenancies.csv')
licences_df = pd.read_csv('data/licences.csv')
timeseries_df = pd.read_csv('data/timeseries.csv')

# UI layout
app_ui = ui.page_fluid(
    # Header
    # Filters
    # Tabs (Overview, Licences, Users, Tenancies)
)

# Server logic
def server(input, output, session):
    # Reactive filtering
    # Tab rendering
    # Chart creation
    pass

app = App(app_ui, server)
```

### Step 8: Styling for GDS Compliance
- Use semantic HTML elements
- Ensure proper heading hierarchy (h1, h2, h3)
- Add ARIA labels for accessibility
- Use high-contrast colors
- Make all interactive elements keyboard accessible
- Add descriptive alt text for charts

### Step 9: Testing Checklist
- [ ] All filters work correctly
- [ ] Period comparisons calculate accurately
- [ ] Tables sort properly
- [ ] Charts render with correct data
- [ ] Date range picker functions
- [ ] Responsive layout works on mobile
- [ ] Keyboard navigation works
- [ ] Screen reader compatibility

### Step 10: Resources
- [Shiny for Python Documentation](https://shiny.posit.co/py/)
- [Plotly Python Documentation](https://plotly.com/python/)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [GDS Design System](https://design-system.service.gov.uk/)
- [WCAG Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

## Data Dictionary

### users.csv
- `userId`: Unique user identifier
- `tenancy`: Tenancy name
- `component`: "Connect" or "Workbench"
- `environment`: "Production", "Development", or "Staging"
- `lastLogin`: ISO date string of last login
- `loginCount`: Number of logins in the period
- `status`: "active" or "inactive"

### tenancies.csv
- `tenancy`: Tenancy name
- `activeUsers`: Number of active users
- `totalLogins`: Total login count
- `workbenchUsers`: Users on Workbench
- `connectUsers`: Users on Connect
- `growth`: Growth percentage

### licences.csv
- `tenancy`: Tenancy name
- `component`: "Connect" or "Workbench"
- `licencesUsed`: Number of licences assigned

### timeseries.csv
- `date`: ISO date string
- `activeUsers`: Number of active users on that day
- `logins`: Number of logins on that day
- `newUsers`: Number of new users on that day
- `powerUsers`: Number of power users
- `regularUsers`: Number of regular users
- `lightUsers`: Number of light users
- `dormantUsers`: Number of dormant users

## Constants
- `TOTAL_USERS = 10500`
- `TOTAL_CONNECT_LICENCES = 10000`
- `TOTAL_WORKBENCH_LICENCES = 5000`
- `NEW_USERS = 50` (static for MVP)

## Notes
- All percentages should display to 1 decimal place
- Charts should use the color scheme from the design system
- Tables should show clear totals/summaries where applicable
- Period comparisons should show up/down arrows and color coding
