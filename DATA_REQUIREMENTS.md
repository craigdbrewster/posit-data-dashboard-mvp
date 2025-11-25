# Posit Platform Analytics - Data Requirements

## Overview
This document outlines the data requirements for the Posit Platform Analytics Dashboard. All data should be provided via API endpoints or database queries that can be filtered by date range, tenancy, environment, and component.

---

## 1. User Data

### Entity: `users`
Core user activity and status information.

**Required Fields:**
- `userId` (string) - Unique user identifier
- `tenancy` (string) - User's tenancy (e.g., "Nebula", "Phoenix", "Atlas", "Zenith", "Spectrum")
- `component` (string) - Component being used ("Workbench" or "Connect")
- `environment` (string) - Environment type ("Live" or "Pre-production")
- `lastLogin` (date/string ISO 8601) - Date of most recent login
- `loginCount` (integer) - Total number of logins (all time)
- `loginsLast60Days` (integer) - Number of logins in the last 60 days
- `status` (string) - User status: "active", "inactive", or "dormant"

**Status Definitions:**
- **Active**: Logged in within last 7 days
- **Inactive**: Logged in between 8-60 days ago
- **Dormant**: No login in 60+ days

**Filtering Requirements:**
- Filter by tenancy (single or all)
- Filter by environment (single or all)
- Filter by component (single or all)
- Filter by date range (based on lastLogin)
- Filter by status

**Expected Volume:** ~8,000 records

---

## 2. Tenancy Metrics

### Entity: `tenancy_metrics`
Aggregated performance metrics per tenancy.

**Required Fields:**
- `tenancy` (string) - Tenancy identifier
- `activeUsers` (integer) - Count of active users (logged in last 7 days)
- `totalLogins` (integer) - Total login count across all users
- `workbenchUsers` (integer) - Count of users using Workbench
- `connectUsers` (integer) - Count of users using Connect
- `growth` (decimal) - Growth rate percentage (compared to previous period)

**Filtering Requirements:**
- Filter by tenancy (single or all)
- Date range for calculating active users and growth

**Expected Volume:** 5 tenancy records

---

## 3. License Usage

### Entity: `licence_usage`
License allocation and usage by tenancy and component.

**Required Fields:**
- `tenancy` (string) - Tenancy identifier
- `component` (string) - "Connect" or "Workbench"
- `licencesUsed` (integer) - Number of licenses currently in use

**Additional Constants:**
- `TOTAL_CONNECT_LICENCES` (integer) - Total Connect licenses available (e.g., 10,000)
- `TOTAL_WORKBENCH_LICENCES` (integer) - Total Workbench licenses available (e.g., 1,000)

**Filtering Requirements:**
- Filter by tenancy (single or all)
- Filter by component (single or all)

**Expected Volume:** ~10 records (5 tenancies × 2 components)

---

## 4. Time Series Data

### Entity: `time_series_data`
Daily engagement metrics for trend analysis.

**Required Fields:**
- `date` (date/string ISO 8601) - The date for this data point
- `activeUsers` (integer) - Count of active users on this date
- `logins` (integer) - Total number of logins on this date
- `newUsers` (integer) - Count of new user registrations on this date
- `powerUsers` (integer) - Users with daily activity (40-60 logins in 60 days)
- `regularUsers` (integer) - Users with weekly activity (8-40 logins in 60 days)
- `lightUsers` (integer) - Users with occasional activity (1-8 logins in 60 days)
- `dormantUsers` (integer) - Users with no activity (0 logins in 60 days)

**Filtering Requirements:**
- Filter by date range (typically last 30, 60, or 90 days)
- Filter by tenancy
- Filter by component
- Filter by environment

**Expected Volume:** 90+ daily records (expandable based on date range)

---

## 5. Component Usage

### Entity: `component_usage`
Usage distribution across different development tools.

**Required Fields:**
- `name` (string) - Tool name (e.g., "RStudio Pro", "Jupyter", "Positron", "VS Code", "Published Apps")
- `users` (integer) - Number of users using this tool
- `percentage` (integer) - Percentage of total users (calculated or provided)

**Filtering Requirements:**
- Filter by tenancy
- Filter by date range

**Expected Volume:** 5+ tool records

---

## 6. Application Data

### Entity: `applications`
Posit Connect application metadata and usage metrics.

**Required Fields:**
- `appId` (string) - Unique application identifier
- `appName` (string) - Display name of the application
- `tenancy` (string) - Tenancy that owns the application
- `createdDate` (date/string ISO 8601) - When the app was first created/deployed
- `lastAccessed` (date/string ISO 8601) - Most recent access date
- `totalUsers` (integer) - Total number of unique users who have accessed this app
- `totalAccessTime` (integer) - Total usage time in minutes
- `accessCount` (integer) - Total number of times the app has been accessed
- `type` (string) - Application type: "Dashboard", "API", "Report", "Model", or "Notebook"

**Filtering Requirements:**
- Filter by tenancy (single or all)
- Filter by type
- Filter by date range (for createdDate and lastAccessed)
- Sorting by: totalUsers, totalAccessTime, accessCount

**Expected Volume:** ~250 application records

---

## 7. Calculated Metrics

The following metrics need to be calculated from the base data:

### Overview Tab
- Total users (count)
- Active users in date range (count)
- Total logins (sum)
- Growth rate (percentage change from previous period)

### Users Tab (Engagement)
- User segment distribution (power/regular/light/dormant)
- Average session length (calculated from usage patterns)
- App deployments in period (count)
- Login success rate (percentage)

### Applications Tab
- Total apps (count)
- Apps created in period (count where createdDate in range)
- Apps accessed in period (count where lastAccessed in range)
- Total usage time in hours (sum of totalAccessTime / 60)
- Top 10 apps by users (sorted by totalUsers, limit 10)
- Top 10 apps by usage time (sorted by totalAccessTime, limit 10)

---

## 8. Filtering & Date Range Requirements

All data endpoints should support the following filter parameters:

**Global Filters:**
- `tenancy` (string) - Single tenancy or "All Tenancies"
- `environment` (string) - "Live", "Pre-production", or "All Environments"
- `component` (string) - "Workbench", "Connect", or "All Components"
- `startDate` (date ISO 8601) - Start of date range
- `endDate` (date ISO 8601) - End of date range

**Default Date Range:** Last 30 days

---

## 9. API Endpoint Recommendations

Suggested REST API structure:

```
GET /api/users
  ?tenancy={tenancy}
  &environment={environment}
  &component={component}
  &startDate={date}
  &endDate={date}
  &status={status}
  &limit={number}

GET /api/tenancy-metrics
  ?tenancy={tenancy}
  &startDate={date}
  &endDate={date}

GET /api/licence-usage
  ?tenancy={tenancy}
  &component={component}

GET /api/time-series
  ?startDate={date}
  &endDate={date}
  &tenancy={tenancy}
  &component={component}
  &environment={environment}

GET /api/component-usage
  ?tenancy={tenancy}
  &startDate={date}
  &endDate={date}

GET /api/applications
  ?tenancy={tenancy}
  &type={type}
  &startDate={date}
  &endDate={date}
  &sortBy={field}
  &limit={number}
```

---

## 10. Performance Considerations

- **Pagination**: User activity table displays first 50 records; implement pagination for full dataset
- **Caching**: Time series and aggregated metrics should be cached/pre-calculated where possible
- **Aggregation**: Daily aggregations should be pre-computed rather than calculated on-demand
- **Indexes**: Ensure indexes on: userId, tenancy, lastLogin, createdDate, lastAccessed

---

## 11. Data Refresh Requirements

- **Real-time data**: Not required
- **Recommended refresh frequency**: 
  - User activity data: Daily (overnight batch)
  - License usage: Hourly
  - Application metrics: Every 4 hours
  - Time series aggregations: Daily

---

## 12. Mock Data Location

Current mock data implementation can be found in:
- `src/lib/mockData.ts` - Mock data generation
- `src/lib/filterUtils.ts` - Filtering logic to be applied to real data

These files demonstrate the expected data structure and filtering behavior that should be replicated with real data sources.

---

## Questions or Clarifications

Please contact the development team if you need:
- Additional fields or metrics
- Different filtering capabilities
- Alternative data aggregation methods
- Performance optimization guidance
