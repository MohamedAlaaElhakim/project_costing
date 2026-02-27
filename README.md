# 📊 KPI Management System

> Custom Odoo 17 module for tracking project costs, labor, equipment, and profitability with a full approval workflow.

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Odoo](https://img.shields.io/badge/Odoo_17-714B67?style=for-the-badge&logo=odoo&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/License-AGPL_3-blue?style=for-the-badge)

-----

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Module Structure](#module-structure)
- [Models](#models)
- [Workflow](#workflow)
- [Security](#security)
- [Installation](#installation)
- [Dependencies](#dependencies)
- [Demo Data](#demo-data)
- [Author](#author)

-----

## 🧩 Overview

The **KPI Management System** is a fully custom Odoo 17 module designed to help companies track and analyze the financial performance of their projects. It covers labor costs, equipment usage, budget control, profit margins, and integrates with Odoo’s native Purchase and Project modules.

-----

## ✨ Features

### 📁 Project Management

- Create KPI projects with budget, selling price, and date range
- Auto-generated reference codes using Odoo sequences (e.g. `KPI/2025/0001`)
- Link KPI projects to native Odoo projects
- Full **chatter** support (messages, activities, followers)
- **Kanban, Tree, Graph, and Pivot** views

### 👷 Labor Tracking

|Field         |Description                                              |
|--------------|---------------------------------------------------------|
|Employee      |Linked to `hr.employee`                                  |
|Hours         |Actual hours worked                                      |
|Hour Cost     |Auto-fetched from employee’s active contract (wage ÷ 160)|
|Subtotal      |Hours × Hour Cost                                        |
|Overtime Hours|Hours exceeding 8h/day                                   |
|Utilization % |Actual hours ÷ Planned hours × 100                       |
|Cost Share %  |Labor subtotal ÷ Total project cost × 100                |

### 🏗️ Equipment Tracking

|Field        |Description                                  |
|-------------|---------------------------------------------|
|Equipment    |Linked to `maintenance.equipment`            |
|Quantity     |Number of units                              |
|Days         |Actual days used                             |
|Day Cost     |Cost per day                                 |
|Subtotal     |Days × Day Cost × Quantity                   |
|Utilization %|Actual days ÷ Planned days × 100             |
|Cost Share % |Equipment subtotal ÷ Total project cost × 100|

### 💰 Financial KPIs (Auto-Computed)

|KPI                 |Formula                       |
|--------------------|------------------------------|
|Total Labor Cost    |Sum of all labor subtotals    |
|Total Equipment Cost|Sum of all equipment subtotals|
|Total Cost          |Labor + Equipment             |
|Profit              |Selling Price − Total Cost    |
|Profit Margin %     |Profit ÷ Selling Price × 100  |
|Remaining Budget    |Budget − Total Cost           |
|Over Budget         |True if Total Cost > Budget   |

### 🛒 Purchase Order Wizard

- Open wizard directly from the project form
- Select which equipment lines to convert to POs
- Assign vendor and estimated cost per line
- Auto-creates Purchase Orders and logs a message in the project chatter

### 📄 QWeb PDF Report

- Professional PDF report per project
- Includes: project info, financial summary, labor details, equipment details

-----

## 📁 Module Structure

```
project_costing/
├── models/
│   ├── kpi_project.py        # Main project model — workflow, KPIs, security
│   ├── kpi_labor.py          # Labor lines — cost, overtime, utilization
│   └── kpi_equipment.py      # Equipment lines — cost, utilization
│
├── wizard/
│   ├── kpi_purchase_wizard.py       # Wizard to create Purchase Orders
│   └── kpi_purchase_wizard_line.py  # Wizard line model
│
├── views/
│   ├── kpi_project_views.xml    # Tree, Form, Kanban, Graph, Pivot, Search
│   ├── kpi_labor_views.xml      # Labor standalone views
│   ├── kpi_equipment_views.xml  # Equipment standalone views
│   ├── project_inherit.xml      # Smart button on native project form
│   └── kpi_menus.xml            # Menu structure
│
├── reports/
│   └── kpi_project_report.xml   # QWeb PDF report template + action
│
├── security/
│   ├── groups.xml               # KPI User & KPI Manager groups
│   ├── kpi_security.xml         # Record rules (users see own projects only)
│   └── ir.model.access.csv      # Model access rights
│
├── data/
│   └── kpi_project_sequence.xml # Auto reference sequence
│
├── demo/
│   └── demo_data.xml            # Demo projects in all workflow states
│
└── __manifest__.py
```

-----

## 🗂️ Models

### `kpi.project`

Main model that holds all project data.

**Key fields:**

```python
name          # Project name (required)
code          # Auto-generated reference (e.g. KPI/2025/0001)
client_id     # res.partner — the client
budget        # Monetary — project budget
selling_price # Monetary — agreed selling price
start_date    # Project start date
end_date      # Project end date
project_id    # Link to native project.project
state         # Workflow state
labor_ids     # One2many → kpi.labor
equipment_ids # One2many → kpi.equipment

# Computed
total_labor_cost     # Sum of labor subtotals
total_equipment_cost # Sum of equipment subtotals
total_cost           # Labor + Equipment
profit               # selling_price - total_cost
profit_margin        # profit / selling_price * 100
remaining_budget     # budget - total_cost
is_over_budget       # True if total_cost > budget
```

### `kpi.labor`

Labor lines linked to a project.

**Key fields:**

```python
project_id         # Many2one → kpi.project
employee_id        # Many2one → hr.employee
hours              # Float — actual hours worked
hour_cost          # Auto-computed from contract wage ÷ 160
subtotal           # hours × hour_cost
days               # hours ÷ 8
overtime_hours     # hours - 8 if hours > 8
planned_hours      # project_days × 8
utilization_percent # hours / planned_hours * 100
cost_share_percent  # subtotal / total_cost * 100
```

### `kpi.equipment`

Equipment lines linked to a project.

**Key fields:**

```python
project_id          # Many2one → kpi.project
equipment_id        # Many2one → maintenance.equipment
quantity            # Float — number of units
days                # Float — days used
day_cost            # Monetary — cost per day
subtotal            # days × day_cost × quantity
planned_days        # project end_date - start_date
utilization_percent # days / planned_days * 100
cost_share_percent  # subtotal / total_cost * 100
```

-----

## 🔄 Workflow

```
Draft ──► Submitted ──► Approved ──► Done
  │           │              │
  └───────────┴──────────────┴──► Cancelled
                                      │
                              (Manager only) ▼
                                    Draft
```

|Transition            |Button      |Condition                                     |
|----------------------|------------|----------------------------------------------|
|Draft → Submitted     |Submit      |Must have at least 1 labor or equipment line  |
|Submitted → Approved  |Approve     |Auto-creates a task in the linked Odoo project|
|Approved → Done       |Mark as Done|Selling Price must be set                     |
|Any → Cancelled       |Cancel      |Available from Draft, Submitted, Approved     |
|Done/Cancelled → Draft|Reopen      |**Managers only**                             |

-----

## 🔐 Security

### Groups

|Group          |Permissions                                 |
|---------------|--------------------------------------------|
|**KPI User**   |Read, Write, Create — own projects only     |
|**KPI Manager**|Full access — all projects + delete + reopen|

### Record Rules

- **Users** can only see projects they created
- **Managers** can see all projects

### Locking

- Projects in `Done` or `Cancelled` state are **locked**
- Regular users cannot edit or delete locked projects
- Only system fields (computed fields, chatter) can be updated on locked records
- Managers can reopen locked projects

-----

## ⚙️ Installation

**1. Copy the module to your Odoo addons path:**

```bash
git clone https://github.com/MohamedAlaaElhakim/project_costing.git /path/to/odoo/addons/project_costing
```

**2. Update addons list:**

- Enable **Developer Mode** → Settings → Activate the developer mode
- Go to **Apps → Update Apps List**

**3. Install the module:**

- Search for **KPI Management System**
- Click **Install**

-----

## 📦 Dependencies

The following Odoo apps must be installed before this module:

|Module       |Purpose                        |
|-------------|-------------------------------|
|`project`    |Native project linking         |
|`hr`         |Employee management            |
|`hr_contract`|Auto-fetch employee hourly rate|
|`maintenance`|Equipment tracking             |
|`purchase`   |Purchase order creation        |
|`mail`       |Chatter, activities, followers |

-----

## 🎭 Demo Data

The module includes demo data with 4 projects covering all workflow states:

|Project                        |State    |Client               |
|-------------------------------|---------|---------------------|
|Office Tower - New Cairo       |Draft    |Nile Construction Co.|
|Warehouse Complex - 6th October|Submitted|Delta Tech Solutions |
|Road Infrastructure - Ring Road|Approved |Cairo Infra Group    |
|Residential Complex - Maadi    |Done     |Nile Construction Co.|


> **Note:** Demo data only loads if your Odoo database was created with **“Load demonstration data”** enabled.

-----

## 👤 Author

**Mohamed Alaa Elhakim**
Odoo Developer | Python | ERP Solutions

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=flat-square&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/mohamedalaaelhakim)
[![Gmail](https://img.shields.io/badge/Gmail-D14836?style=flat-square&logo=gmail&logoColor=white)](mailto:mohamed.alaa918214@gmail.com)
[![WhatsApp](https://img.shields.io/badge/WhatsApp-25D366?style=flat-square&logo=whatsapp&logoColor=white)](https://wa.me/201019272209)