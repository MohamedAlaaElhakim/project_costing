# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class KpiProject(models.Model):
    _name = "kpi.project"
    _description = "KPI Project"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    # =================
    # Constants
    # =================
    SEQUENCE_CODE = "kpi.project"
    LOCKED_STATES = ("done", "cancelled")
    MANAGER_GROUP_XMLID = "project_costing.group_kpi_manager"

    # =================
    # Basic Fields
    # =================
    name = fields.Char(string="Project Name", required=True, tracking=True)
    code = fields.Char(
        string="Reference",
        default="New",
        tracking=True,
        readonly=True,
        copy=False,
        index=True,  # تحسين سرعة البحث
    )

    client_id = fields.Many2one("res.partner", string="Client", tracking=True)

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    budget = fields.Monetary(string="Budget", currency_field="currency_id", tracking=True)
    selling_price = fields.Monetary(string="Selling Price", currency_field="currency_id", tracking=True)

    start_date = fields.Date(string="Start Date", tracking=True)
    end_date = fields.Date(string="End Date", tracking=True)

    project_id = fields.Many2one("project.project", string="Linked Odoo Project")

    # Relations
    labor_ids = fields.One2many("kpi.labor", "project_id", string="Labor Lines")
    equipment_ids = fields.One2many("kpi.equipment", "project_id", string="Equipment Lines")

    # =================
    # Workflow
    # =================
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        string="Status",
        required=True,
        tracking=True,
        copy=False,  # عدم نسخ الحالة عند التكرار
    )

    # =================
    # Computed Totals
    # =================
    total_labor_cost = fields.Monetary(
        string="Total Labor Cost",
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
    )
    total_equipment_cost = fields.Monetary(
        string="Total Equipment Cost",
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
    )
    total_cost = fields.Monetary(
        string="Total Cost",
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
    )

    # =================
    # KPI Computed
    # =================
    profit = fields.Monetary(
        string="Profit",
        currency_field="currency_id",
        compute="_compute_profit",
        store=True,
    )
    profit_margin = fields.Float(
        string="Profit Margin (%)",
        compute="_compute_profit",
        store=True,
    )

    remaining_budget = fields.Monetary(
        string="Remaining Budget",
        currency_field="currency_id",
        compute="_compute_budget",
        store=True,
    )
    is_over_budget = fields.Boolean(
        string="Is Over Budget",
        compute="_compute_budget",
        store=True,
    )

    labor_lines_count = fields.Integer(compute="_compute_counts", store=False)
    equipment_lines_count = fields.Integer(compute="_compute_counts", store=False)

    # =================
    # Compute Methods
    # =================
    @api.depends("labor_ids.subtotal", "equipment_ids.subtotal")
    def _compute_totals(self):
        for rec in self:
            # استخدام sum مباشرة على القائمة mapped
            rec.total_labor_cost = sum(rec.labor_ids.mapped("subtotal"))
            rec.total_equipment_cost = sum(rec.equipment_ids.mapped("subtotal"))
            rec.total_cost = rec.total_labor_cost + rec.total_equipment_cost

    @api.depends("selling_price", "total_cost")
    def _compute_profit(self):
        for rec in self:
            rec.profit = rec.selling_price - rec.total_cost
            rec.profit_margin = (rec.profit / rec.selling_price * 100) if rec.selling_price else 0.0

    @api.depends("budget", "total_cost")
    def _compute_budget(self):
        for rec in self:
            rec.remaining_budget = rec.budget - rec.total_cost
            rec.is_over_budget = bool(rec.budget) and rec.total_cost > rec.budget

    @api.depends("labor_ids", "equipment_ids")
    def _compute_counts(self):
        for rec in self:
            rec.labor_lines_count = len(rec.labor_ids)
            rec.equipment_lines_count = len(rec.equipment_ids)

    # =================
    # Workflow Actions
    # =================
    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft projects can be submitted."))
            if not rec.labor_ids and not rec.equipment_ids:
                raise UserError(_("Add at least one Labor or Equipment line before submitting."))
            rec.state = "submitted"

    def action_approve(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError(_("Only submitted projects can be approved."))

            if rec.project_id:
                self.env['project.task'].create({
                    'name': f"Task for {rec.name}",
                    'project_id': rec.project_id.id,
                    'description': f"Auto-created from KPI Project {rec.code}",
                    'user_ids': [(4, self.env.uid)],
                })

            rec.state = "approved"

    def action_done(self):
        for rec in self:
            if rec.state != "approved":
                raise UserError(_("Only approved projects can be marked as done."))
            if not rec.selling_price:
                raise UserError(_("Set Selling Price before marking as Done."))
            rec.state = "done"

    def action_cancel(self):
        for rec in self:
            if rec.state not in ("draft", "submitted", "approved"):
                raise UserError(_("Only draft, submitted, or approved projects can be cancelled."))
            rec.state = "cancelled"

    def action_reset_to_draft(self):
        # التحقق من الصلاحيات قبل التغيير
        if not self._is_kpi_manager():
            raise UserError(_("Only Managers can reset a project to Draft."))

        for rec in self:
            if rec.state not in self.LOCKED_STATES:
                raise UserError(_("Only locked projects (Done/Cancelled) can be reset."))

        # التغيير المباشر للحالة
        self.write({"state": "draft"})
        self.message_post(body=_("Project has been reset to Draft by %s.") % self.env.user.name)

    def action_open_purchase_wizard(self):
        """فتح Wizard إنشاء أوامر الشراء"""
        self.ensure_one()

        line_vals = []
        for equipment in self.equipment_ids:
            # ✅ نجيب المورد بأمان
            vendor = False
            if equipment.equipment_id:
                if hasattr(equipment.equipment_id, 'vendor_id') and equipment.equipment_id.vendor_id:
                    vendor = equipment.equipment_id.vendor_id
                elif hasattr(equipment.equipment_id, 'product_id') and equipment.equipment_id.product_id:
                    if equipment.equipment_id.product_id.seller_ids:
                        vendor = equipment.equipment_id.product_id.seller_ids[0].partner_id

            # ✅ نجيب المنتج بأمان
            product = False
            if equipment.equipment_id and hasattr(equipment.equipment_id, 'product_id'):
                product = equipment.equipment_id.product_id

            # ✅ نمرر الحقول للـ Wizard (اللي إحنا أضفناها للتو)
            line_vals.append((0, 0, {
                'equipment_id': equipment.equipment_id.id if equipment.equipment_id else False,
                'vendor_id': vendor.id if vendor else False,
                'estimated_cost': equipment.subtotal,
            }))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Purchase Orders'),
            'res_model': 'kpi.purchase.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.id,
                'default_line_ids': line_vals,
            },
        }

    @api.onchange("budget", "total_cost")
    def _onchange_budget_warning(self):
        if self.budget and self.total_cost and self.budget < self.total_cost:
            return {
                "warning": {
                    "title": _("Warning"),
                    "message": _("Budget is less than Total Cost. Please review."),
                }
            }

    # =========================
    # Create / Write / Unlink
    # =========================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code", "New") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code(self.SEQUENCE_CODE) or "New"
        return super().create(vals_list)

    def name_get(self):
        res = []
        for rec in self:
            display = f"{rec.code} - {rec.name}" if rec.code and rec.code != "New" else rec.name
            res.append((rec.id, display))
        return res

    def copy(self, default=None):
        default = dict(default or {})
        # عند النسخ، نبدأ بحالة جديدة وكود جديد وتواريخ واضحة
        default.update({
            "state": "draft",
            "code": "New",
            "start_date": False,
            "end_date": False,
        })
        return super().copy(default)

    def _is_kpi_manager(self):
        try:
            return self.env.user.has_group('project_costing.group_kpi_manager')
        except Exception:
            return False

    def write(self, vals):
        # السماح بالكتابة في وضع التثبيت أو بواسطة Super User
        if self.env.context.get("install_mode") or self.env.su:
            return super().write(vals)

        # الحقول المسموح بتحديثها حتى في الحالة المقفولة
        system_fields = {
            "total_labor_cost", "total_equipment_cost", "total_cost",
            "profit", "profit_margin",
            "remaining_budget", "is_over_budget",
            "labor_lines_count", "equipment_lines_count",
            "message_follower_ids", "message_ids", "activity_ids",
            "activity_state", "activity_user_id", "activity_type_id",
            "activity_date_deadline", "activity_summary", "activity_note",
            "state",  # مسموح بتغيير الحالة عبر الأزرار
        }

        for project in self:
            if project.state in self.LOCKED_STATES and not project._is_kpi_manager():
                blocked = set(vals.keys()) - system_fields
                if blocked:
                    raise ValidationError(_("المشروع مقفول. التعديل بعد الإغلاق مسموح للمدير فقط."))

        return super().write(vals)

    def unlink(self):
        if self.env.context.get("install_mode") or self.env.su:
            return super().unlink()

        for project in self:
            if project.state in self.LOCKED_STATES:
                raise ValidationError(_("لا يمكن حذف مشروع بعد الإغلاق (Done/Cancelled)."))

        return super().unlink()

    # =================
    # Constraints
    # =================
    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(_("End Date must be after Start Date."))

    @api.constrains("budget", "selling_price")
    def _check_non_negative_amounts(self):
        for rec in self:
            if rec.budget < 0:
                raise ValidationError(_("Budget cannot be negative."))
            if rec.selling_price < 0:
                raise ValidationError(_("Selling Price cannot be negative."))

    @api.constrains("state", "selling_price")
    def _check_done_requires_price(self):
        for rec in self:
            if rec.state == "done" and not rec.selling_price:
                raise ValidationError(_("You must set Selling Price before marking the project as Done."))

    @api.constrains("selling_price", "total_cost")
    def _check_price_not_less_than_cost(self):

        pass

    @api.onchange("selling_price", "total_cost")
    def _onchange_price_vs_cost_warning(self):
        # ✅ FIX: warning بدل constraint — مش بيمنع الحفظ
        if self.selling_price and self.total_cost and self.selling_price < self.total_cost:
            return {
                "warning": {
                    "title": _("Warning"),
                    "message": _("Selling Price is less than Total Cost. This project will result in a loss."),
                }
            }
