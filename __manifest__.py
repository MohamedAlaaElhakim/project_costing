{
    "name": "KPI Management System",
    "version": "1.0",
    "category": "Project",
    "sequence": 10,
    "summary": "KPI Projects, Labor & Equipment Tracking",
    "description": """
KPI Management System
====================

- Projects with budgets, selling price, profit, margins
- Labor Lines with hours, cost, utilization
- Equipment Lines with days, cost, utilization
- Security: Users see only their projects, Managers full access
- Workflow: Draft → Submitted → Approved → Done
""",
    "author": "KPI Dev",
    "website": "https://github.com/your-username/project_costing",
    "license": "AGPL-3",
    "depends": [
        "base",
        "mail",
        "project",
        "hr",
        "maintenance",
        "purchase",
        "hr_contract",
    ],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "security/kpi_security.xml",

        # 2️⃣ Data (Sequences, Defaults)
        "data/kpi_project_sequence.xml",

        # 3️⃣ Views (الترتيب هنا مرن)
        "reports/kpi_project_report.xml",
        "wizard/kpi_purchase_wizard.xml",
        "views/kpi_labor_views.xml",
        "views/kpi_equipment_views.xml",
        "views/kpi_project_views.xml",
        "views/project_inherit.xml",
        "views/kpi_menus.xml",

    ],
    "demo": [
        "demo/demo_data.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "images": ["static/description/banner.png"],  # ✅ صورة للموديول في Apps Store
}