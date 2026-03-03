from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KpiEquipment(models.Model):
    _name = "kpi.equipment"
    _description = "KPI Equipment"

    project_id = fields.Many2one(
        "kpi.project",
        string="Project",
        required=True,
        ondelete="cascade",
    )

    equipment_id = fields.Many2one("maintenance.equipment", string="Equipment")

    # Currency related from project
    currency_id = fields.Many2one(
        "res.currency",
        related="project_id.currency_id",
        store=True,
        readonly=True,
    )

    days = fields.Float(string="Days", default=0.0)

    day_cost = fields.Monetary(
        string="Day Cost",
        currency_field="currency_id",
        default=0.0,
    )

    subtotal = fields.Monetary(
        string="Subtotal",
        currency_field="currency_id",
        compute="_compute_subtotal",
        store=True,
    )

    hours = fields.Float(string="Hours", compute="_compute_hours", store=True)

    hour_cost = fields.Monetary(
        string="Hour Cost",
        currency_field="currency_id",
        compute="_compute_hour_cost",
        store=True,
    )



    planned_days = fields.Integer(
        string="Planned Days",
        compute="_compute_planned_days",
        store=True,
    )

    utilization_percent = fields.Float(
        string="Utilization %",
        compute="_compute_utilization",
        store=True,
    )

    is_over_allocated = fields.Boolean(
        string="Over Allocated?",
        compute="_compute_utilization",
        store=True,
    )

    cost_share_percent = fields.Float(
        string="Cost Share (%)",
        compute="_compute_cost_share",
        store=True,
    )
    quantity = fields.Float(string="Quantity", default=1.0)

    # ---------------- Compute Methods ----------------
    @api.depends("days", "day_cost", "quantity")
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.days * rec.day_cost * rec.quantity

    @api.depends("days")
    def _compute_hours(self):
        for rec in self:
            rec.hours = rec.days * 8.0 if rec.days else 0.0

    @api.depends("day_cost")
    def _compute_hour_cost(self):
        for rec in self:
            rec.hour_cost = rec.day_cost / 8.0 if rec.day_cost else 0.0


    @api.depends("project_id.start_date", "project_id.end_date")
    def _compute_planned_days(self):
        for rec in self:
            planned_days = 0
            if (
                rec.project_id.start_date
                and rec.project_id.end_date
                and rec.project_id.end_date >= rec.project_id.start_date
            ):
                planned_days = (rec.project_id.end_date - rec.project_id.start_date).days + 1
            rec.planned_days = planned_days

    @api.depends("days", "planned_days")
    def _compute_utilization(self):
        for rec in self:
            rec.utilization_percent = (rec.days / rec.planned_days * 100) if rec.planned_days else 0.0
            rec.is_over_allocated = bool(rec.planned_days) and rec.days > rec.planned_days

    @api.depends("subtotal", "project_id.total_cost")
    def _compute_cost_share(self):
        for rec in self:
            total = rec.project_id.total_cost
            rec.cost_share_percent = (rec.subtotal / total * 100) if total else 0.0

    # ---------------- Constraints ----------------
    @api.constrains("days", "day_cost", "quantity")
    def _check_equipment_values(self):
        for rec in self:
            if rec.days < 0:
                raise ValidationError(_("Days cannot be negative."))
            if rec.day_cost < 0:
                raise ValidationError(_("Day Cost cannot be negative."))
            if rec.quantity <= 0:
                raise ValidationError(_("Quantity must be greater than zero."))