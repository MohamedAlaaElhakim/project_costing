# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class KpiLabor(models.Model):
    _name = "kpi.labor"
    _description = "KPI Labor Line"
    _order = "id desc"

    # =================
    # Relations
    # =================
    project_id = fields.Many2one(
        "kpi.project",
        string="Project",
        required=True,
        ondelete="cascade",
        index=True,  # تحسين أداء البحث والربط
    )

    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        required=True,
        ondelete="restrict",
    )
    # =================
    # Currency & Amounts
    # =================
    currency_id = fields.Many2one(
        "res.currency",
        related="project_id.currency_id",
        store=True,
        readonly=True,
    )

    hours = fields.Float(string="Hours", default=0.0, tracking=True)
    hour_cost = fields.Monetary(
        string="Hour Cost",
        currency_field="currency_id",
        compute="_compute_hour_cost",
        store=True,
        readonly=False,  # عشان يقدر يعدلها لو عايز
    )

    subtotal = fields.Monetary(
        string="Subtotal",
        currency_field="currency_id",
        compute="_compute_subtotal",
        store=True,
    )

    # =================
    # Computed Fields
    # =================
    days = fields.Float(string="Days", compute="_compute_days", store=True)

    overtime_hours = fields.Float(string="Overtime Hours", compute="_compute_overtime", store=True)
    is_overtime = fields.Boolean(string="Is Overtime?", compute="_compute_overtime", store=True)

    planned_days = fields.Integer(string="Planned Days", compute="_compute_planned", store=True)
    planned_hours = fields.Float(string="Planned Hours", compute="_compute_planned", store=True)

    utilization_percent = fields.Float(string="Utilization %", compute="_compute_utilization", store=True)
    is_over_allocated = fields.Boolean(string="Over Allocated?", compute="_compute_utilization", store=True)

    cost_share_percent = fields.Float(string="Cost Share (%)", compute="_compute_cost_share", store=True)

    # =================
    # SQL Constraints (أسرع من Python Constraints)
    # =================
    _sql_constraints = [
        ('hours_positive', 'CHECK (hours >= 0)', 'Hours cannot be negative!'),
        ('cost_positive', 'CHECK (hour_cost >= 0)', 'Hour Cost cannot be negative!'),
    ]

    # =================
    # Compute Methods
    # =================
    @api.depends("hours", "hour_cost")
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.hours * rec.hour_cost

    @api.depends("hours")
    def _compute_days(self):
        # يفضل وضع 8.0 في متغير أو System Parameter
        HOURS_PER_DAY = 8.0
        for rec in self:
            rec.days = rec.hours / HOURS_PER_DAY if rec.hours else 0.0

    @api.depends("hours")
    def _compute_overtime(self):
        HOURS_PER_DAY = 8.0
        for rec in self:
            rec.is_overtime = rec.hours > HOURS_PER_DAY
            rec.overtime_hours = rec.hours - HOURS_PER_DAY if rec.hours > HOURS_PER_DAY else 0.0

    @api.depends("project_id.start_date", "project_id.end_date")
    def _compute_planned(self):
        for rec in self:
            planned_days = 0
            if rec.project_id.start_date and rec.project_id.end_date:
                if rec.project_id.end_date >= rec.project_id.start_date:
                    planned_days = (rec.project_id.end_date - rec.project_id.start_date).days + 1
                else:
                    planned_days = 0  # حالة التاريخ غير صحيح

            rec.planned_days = planned_days
            rec.planned_hours = planned_days * 8.0 if planned_days else 0.0

    @api.depends("hours", "planned_hours")
    def _compute_utilization(self):
        for rec in self:
            if rec.planned_hours > 0:
                rec.utilization_percent = (rec.hours / rec.planned_hours * 100)
                rec.is_over_allocated = rec.hours > rec.planned_hours
            else:
                rec.utilization_percent = 0.0
                rec.is_over_allocated = False

    @api.depends("subtotal", "project_id.total_cost")
    def _compute_cost_share(self):
        for rec in self:
            total = rec.project_id.total_cost
            rec.cost_share_percent = (rec.subtotal / total * 100) if total else 0.0

    @api.depends("employee_id")
    def _compute_hour_cost(self):
        """جلب تكلفة الساعة من عقد الموظف أوتوماتيك"""
        for rec in self:
            if rec.employee_id and rec.employee_id.contract_ids:
                active_contract = rec.employee_id.contract_ids.filtered(
                    lambda c: c.state in ['open', 'done']
                )[:1]

                if active_contract and active_contract.wage:
                    # نحسب سعر الساعة (الراتب الشهري / 160 ساعة متوسط)
                    rec.hour_cost = active_contract.wage / 160.0
                else:
                    rec.hour_cost = 50.0  # قيمة افتراضية
            else:
                rec.hour_cost = 50.0  # قيمة افتراضية

    # =================
    # Display Name (مهم جداً للـ UX)
    # =================
    def name_get(self):
        res = []
        for rec in self:
            name = rec.employee_id.name if rec.employee_id else _("Unassigned Labor")
            if rec.project_id:
                name = f"{name} ({rec.project_id.code})"
            res.append((rec.id, name))
        return res

    # =================
    # Security & Locking (حرج جداً)
    # =================
    def _is_record_locked(self):
        self.ensure_one()
        return self.project_id and self.project_id.state in ('done', 'cancelled')

    def write(self, vals):
        if not self.env.su:
            for rec in self:
                if rec._is_record_locked():
                    raise ValidationError(_("Cannot modify labor lines on a locked project (Done/Cancelled)."))
        return super().write(vals)

    def unlink(self):
        if not self.env.su:
            for rec in self:
                if rec._is_record_locked():
                    raise ValidationError(_("Cannot delete labor lines on a locked project."))
        return super().unlink()