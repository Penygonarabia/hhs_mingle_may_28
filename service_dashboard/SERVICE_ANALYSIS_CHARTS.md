# Service Analysis - New Dashboard: Chart Reference Guide

## Overview

The **Service Analysis - New** dashboard (Board ID: 63) is powered by KS Dashboard Ninja and uses **`dbmodel.jobcards.analysis`** as its primary data model — a PostgreSQL SQL view that aggregates data from multiple tables. All charts query this view or run custom SQL directly against `project_task`.

---

## Table Relationships & Data Model

```
project_task  (core job card table — machine_repair_management)
│
├── product_lines              (job card product lines)
│   └── product_product        (product catalogue)
│       └── ir_property        (standard price / cost)
│
├── res_users_work_center_location_rel  (user ↔ work center mapping)
│   └── res_users              (technicians, coordinators)
│       └── res_groups_users_rel  (user ↔ group membership)
│           └── ir_model_data  (resolve role/group XML IDs)
│
├── work_center_group          (region grouping)
├── work_center_location       (work center / city)
├── service_warranty           (warranty type)
└── user_work_center_group_rel (user ↔ work center group)
```

---

## Core SQL View: `dbmodel.jobcards.analysis`

This view (defined in `models/dbmodel_jobcards_analysis.py`) joins all the tables above and exposes the following key fields to KS Dashboard charts:

| Field | Type | Source Table | Description |
|---|---|---|---|
| `task_id` | Many2one | `project_task` | Job card reference |
| `task_name` | Char | `project_task.name` | Job card number |
| `user_id` | Many2one | `res_users` | Assigned coordinator |
| `user_role` | Char | `res_groups_users_rel` + `ir_model_data` | User role label |
| `technician_id` | Many2one | `res_users` | Assigned technician |
| `work_center_group_id` | Many2one | `project_task` | Region |
| `work_center_id` | Many2one | `project_task` | Work center / city |
| `service_warranty_id` | Many2one | `project_task` | Warranty type |
| `job_card_state` | Char | `project_task` | State label (New, Closed, etc.) |
| `job_card_status` | Char | `project_task.job_card_state` | Alias for state |
| `action_status` | Char | `project_task` | Action status |
| `service_created_datetime` | Datetime | `project_task` | Created date |
| `total_revenue` | Float | `product_lines` | Total job revenue |
| `labour_revenue` | Float | `product_lines` | Labour revenue |
| `parts_revenue` | Float | `product_lines` | Spare parts revenue |
| `warranty_spareparts_revenue` | Float | `ir_property` | Warranty parts cost |
| `rtat_hours` | Float | `project_task` | RTAT (float hours) |
| `onhold_hours_min` | Float | `project_task.onhold_hours_min` | On-hold duration (hours) |
| `cstneedquote_hours_min` | Float | `project_task.cstneedquote_hours_min` | Quote-to-parts duration (hours) |
| `is_my_user_group` | Boolean | `user_work_center_group_rel` | Filter: current user's group |
| `is_user_work_location` | Boolean | `res_users_work_center_location_rel` | Filter: current user's location |

---

## Charts in Service Analysis - New

### KPI Cards

---

#### 1. Total / Closed Job Cards
| Property | Value |
|---|---|
| **Type** | KPI |
| **Tables** | `project_task` |
| **SQL** | `SELECT count(pt.control_card_no) FROM project_task pt WHERE service_created_datetime BETWEEN %(ks_start_datetime)s AND %(ks_end_datetime)s` |
| **Purpose** | Counts total job cards created within the selected date range |

---

#### 2. Total Service Revenue
| Property | Value |
|---|---|
| **Type** | KPI |
| **Tables** | `project_task` |
| **SQL** | `SELECT sum(grand_total) FROM project_task WHERE service_created_datetime BETWEEN %(ks_start_datetime)s AND %(ks_end_datetime)s` |
| **Purpose** | Sum of grand totals (labour + parts) for all job cards |

---

#### 3. Spare Parts Revenue
| Property | Value |
|---|---|
| **Type** | KPI |
| **Tables** | `project_task` |
| **SQL** | `SELECT sum(pt.parts_grand_total_amount) FROM project_task pt WHERE service_created_datetime BETWEEN %(ks_start_datetime)s AND %(ks_end_datetime)s` |
| **Purpose** | Total spare parts revenue in the period |

---

#### 4. AVG RTAT
| Property | Value |
|---|---|
| **Type** | KPI |
| **Tables** | `project_task` |
| **SQL** | `SELECT avg(pt.rtat_hours) FROM project_task pt WHERE pt.active = true AND pt.job_card_state = 'Closed' AND pt.service_created_datetime BETWEEN %(ks_start_date)s AND %(ks_end_date)s` |
| **Purpose** | Average Return-to-Available-Time (hours) for closed job cards |
| **Note** | Formatted as float `HH.MM` for display |

---

#### 5. Labor Revenue
| Property | Value |
|---|---|
| **Type** | KPI |
| **Tables** | `project_task` |
| **SQL** | `SELECT sum(pt.service_grand_total_amount) FROM project_task pt WHERE service_created_datetime BETWEEN %(ks_start_datetime)s AND %(ks_end_datetime)s` |
| **Purpose** | Sum of service (labour) revenue |

---

#### 6. Spare Parts Warranty
| Property | Value |
|---|---|
| **Type** | KPI |
| **Tables** | `project_task`, `product_lines`, `ir_property` |
| **SQL** | `SELECT coalesce(sum(ip.value_float), 0) FROM project_task pt LEFT JOIN product_lines pl ON pl.project_task_id = pt.id LEFT JOIN ir_property ip ON cast(split_part(ip.res_id, ',', 2) AS integer) = pl.product_id WHERE pt.service_warranty_id IN ('1','2','6') AND ip.type = 'float' AND ip.name = 'standard_price' AND pt.service_created_datetime BETWEEN %(ks_start_date)s AND %(ks_end_date)s` |
| **Purpose** | Total standard cost of spare parts used under warranty |
| **Key Link** | `product_lines.product_id` → `ir_property.res_id` (format: `'product.product,<id>'`) |

---

### Bar Charts

---

#### 7. Job Status Wise - Count (by action_status)
| Property | Value |
|---|---|
| **Type** | Bar Chart |
| **Model** | `dbmodel.jobcards.analysis` |
| **Aggregation** | COUNT |
| **Group By** | `action_status` |
| **Tables** | `project_task` (via view) |
| **Purpose** | Number of job cards per action status |

---

#### 8. Warranty Sts & Region - Jobs Count
| Property | Value |
|---|---|
| **Type** | Bar Chart |
| **Model** | `dbmodel.jobcards.analysis` |
| **Aggregation** | COUNT |
| **Group By** | `service_warranty_id` |
| **Tables** | `project_task`, `service_warranty` (via view) |
| **Purpose** | Job count grouped by warranty type |

---

#### 9. Region Wise - Jobs Count
| Property | Value |
|---|---|
| **Type** | Bar Chart |
| **Model** | `dbmodel.jobcards.analysis` |
| **Aggregation** | COUNT |
| **Group By** | `work_center_group_id` |
| **Tables** | `project_task`, `work_center_group` (via view) |
| **Purpose** | Number of job cards per region (work center group) |

---

#### 10. Region Wise - RTAT (Avg)
| Property | Value |
|---|---|
| **Type** | Bar Chart |
| **Model** | `dbmodel.jobcards.analysis` |
| **Aggregation** | AVERAGE |
| **Group By** | `work_center_group_id` |
| **Measure** | `rtat_hours` |
| **Tables** | `project_task`, `work_center_group` (via view) |
| **Purpose** | Average RTAT per region — uses `isFormatChart` to display as `days, hh:mm` |

---

#### 11. Job Status Wise - Count (by job_card_status)
| Property | Value |
|---|---|
| **Type** | Bar Chart |
| **Model** | `dbmodel.jobcards.analysis` |
| **Aggregation** | COUNT |
| **Group By** | `job_card_status` |
| **Tables** | `project_task` (via view) |
| **Purpose** | Job card count per state (New, Scheduled, Closed, etc.) |

---

#### 12. Month wise - Jobs Count
| Property | Value |
|---|---|
| **Type** | Bar Chart |
| **Model** | `dbmodel.jobcards.analysis` |
| **Aggregation** | COUNT |
| **Group By** | `service_created_datetime` (month interval) |
| **Tables** | `project_task` (via view) |
| **Purpose** | Monthly trend of job card creation |

---

#### 13. Job Cards - Status analysis on weekly basis
| Property | Value |
|---|---|
| **Type** | Bar Chart |
| **Calculation** | Custom SQL |
| **Tables** | `project_task` |
| **SQL** | Groups job cards by week number within the month, counting `not_closed`, `closed`, and `cancelled` |
| **Purpose** | Weekly breakdown of open vs closed vs cancelled jobs |

```sql
SELECT
    'Week-' || (FLOOR((EXTRACT(DAY FROM service_created_datetime) - 1) / 7) + 1) AS week_no,
    sum(CASE WHEN job_card_state IN ('Cancelled','Closed') THEN 0 ELSE 1 END) AS not_closed,
    sum(CASE WHEN job_card_state = 'Closed'     THEN 1 ELSE 0 END) AS closed,
    sum(CASE WHEN job_card_state = 'Cancelled'  THEN 1 ELSE 0 END) AS cancelled
FROM project_task
WHERE service_created_datetime >= %(ks_start_date)s
  AND service_created_datetime <= %(ks_end_date)s
  AND work_center_group_id = '<region_id>'
  AND active = true
GROUP BY week_no
ORDER BY week_no
```

---

#### 14. Job Cards - Not Closed Status analysis on weekly basis
| Property | Value |
|---|---|
| **Type** | Bar Chart |
| **Calculation** | Custom SQL |
| **Tables** | `project_task` |
| **Purpose** | Same weekly grouping but focused on open (not-closed) jobs per status |

---

#### 15. Employee Performance Analysis - Actual Hours
| Property | Value |
|---|---|
| **Type** | Bar Chart |
| **Model** | `dbmodel.jobcards.analysis` |
| **Aggregation** | SUM |
| **Group By** | `work_center_group_id` |
| **Tables** | `project_task`, `work_center_group` (via view) |
| **Purpose** | Total actual hours worked per region — uses `isFormatChart` for `days, hh:mm` labels |

---

### Pie Charts

---

#### 16. Warranty Status - Jobs (%)
| Property | Value |
|---|---|
| **Type** | Pie Chart |
| **Model** | `dbmodel.jobcards.analysis` |
| **Aggregation** | COUNT |
| **Group By** | `service_warranty_id` |
| **Purpose** | Percentage distribution of jobs by warranty type |

---

#### 17. Region Wise - Jobs (%)
| Property | Value |
|---|---|
| **Type** | Pie Chart |
| **Model** | `dbmodel.jobcards.analysis` |
| **Aggregation** | COUNT |
| **Group By** | `work_center_group_id` |
| **Purpose** | Percentage distribution of jobs across regions |

---

#### 18. Region Wise - RTAT (Avg %)
| Property | Value |
|---|---|
| **Type** | Pie Chart |
| **Model** | `dbmodel.jobcards.analysis` |
| **Aggregation** | AVERAGE |
| **Group By** | `work_center_group_id` |
| **Measure** | `rtat_hours` |
| **Purpose** | Proportional RTAT distribution across regions |

---

## Table Join Reference

```sql
-- Core pattern used by most charts via dbmodel.jobcards.analysis view

project_task pt
  -- Revenue from product lines
  LEFT JOIN product_lines pl          ON pl.project_task_id = pt.id
  LEFT JOIN product_product pp        ON pp.id = pl.product_id
  -- Standard price (warranty cost)
  LEFT JOIN ir_property ip            ON ip.res_id = 'product.product,' || pp.id
                                     AND ip.name = 'standard_price'
                                     AND ip.type = 'float'
  -- User / technician assignment
  LEFT JOIN res_users_work_center_location_rel ruwcll
                                      ON pt.work_center_id = ruwcll.work_center_location_id
  LEFT JOIN res_users ru              ON ru.id = ruwcll.res_users_id
  -- Role determination
  LEFT JOIN res_groups_users_rel rel  ON rel.uid = ru.id
  LEFT JOIN ir_model_data imd         ON imd.res_id = rel.gid
                                     AND imd.module = 'machine_repair_management'
  -- User scoping (current user filters)
  LEFT JOIN user_work_center_group_rel uwcgr
                                      ON uwcgr.res_users_id = <current_uid>
                                     AND uwcgr.work_center_group_id = pt.work_center_group_id
```

---

## How to Build a New Chart

### Step 1 — Choose the Chart Type
| Goal | KS Dashboard Type |
|---|---|
| Single value (count/sum/avg) | `ks_kpi` |
| Bar comparison by category | `ks_bar_chart` |
| Percentage distribution | `ks_pie_chart` |
| Trend over time | `ks_bar_chart` with date groupby |

### Step 2 — Choose the Data Source
| Use Case | Model / Table |
|---|---|
| Standard groupby/measure from job cards | `dbmodel.jobcards.analysis` |
| Complex multi-column or weekly breakdown | Custom SQL on `project_task` |

### Step 3 — Select Group By Field
| Grouping | Field |
|---|---|
| By region | `work_center_group_id` |
| By warranty type | `service_warranty_id` |
| By job status | `job_card_status` or `action_status` |
| By month/week | `service_created_datetime` |
| By user/technician | `user_id` or `technician_id` |

### Step 4 — Select Measure Field
| Metric | Field |
|---|---|
| Job card count | (COUNT, no field needed) |
| Total revenue | `total_revenue` |
| Labour revenue | `labour_revenue` |
| Parts revenue | `parts_revenue` |
| RTAT hours | `rtat_hours` |
| On-hold duration | `onhold_hours_min` |
| Quote-to-parts duration | `cstneedquote_hours_min` |

### Step 5 — Enable `days, hh:mm` Label Format
To display data values as `N days, hh:mm` instead of decimal numbers, add the chart name to the `isFormatChart` array in:

```
ks_dashboard_ninja/static/src/js/charts_render_global_functions.js
```

```javascript
const isFormatChart = [
  "Employee Performance Analysis - Actual Hours",
  "Region Wise - RTAT (Avg)",
  "Waiting period from quotation to parts ready state",
  "Waiting period from On hold to parts ready state",
  // Add your new chart name here
  "Your New Chart Name"
].includes(item.name);
```

---

## Key Filters Applied Automatically

| Filter | Field | Purpose |
|---|---|---|
| Date range | `service_created_datetime` | All charts respect the dashboard date filter |
| Active records | `active = true` | Excludes archived job cards |
| User's work location | `is_user_work_location` | Scopes data to current user's locations |
| User's group | `is_my_user_group` | Scopes data to current user's work center group |
