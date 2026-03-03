from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KpiPurchaseWizard(models.TransientModel):
    _name = "kpi.purchase.wizard"
    _description = "Create Purchase Orders for Equipment"

    # حقل عشان نربط الـ Wizard بالمشروع
    project_id = fields.Many2one("kpi.project", string="Project", required=True)

    # سطور المعدات اللي هتختار منها (One2many لـ transient model)
    line_ids = fields.One2many("kpi.purchase.wizard.line", "wizard_id", string="Equipment Lines")



    def action_create_purchase_orders(self):
        """إنشاء أوامر الشراء للمعدات المختارة"""
        self.ensure_one()

        # 1. تصفية المعدات اللي المستخدم اختارها
        selected_lines = self.line_ids.filtered(lambda x: x.select)

        if not selected_lines:
            raise UserError(_("Please select at least one equipment to purchase."))

        purchase_orders = []

        for line in selected_lines:
            # إنشاء Purchase Order
            po = self.env['purchase.order'].create({
                'partner_id': line.vendor_id.id,
                'origin': f"KPI Project: {self.project_id.code}",
                'project_id': self.project_id.project_id.id if self.project_id.project_id else False,
                'order_line': [(0, 0, {
                    'product_id': line.equipment_id.product_id.id if line.equipment_id.product_id else False,
                    'name': line.equipment_id.name,
                    'product_qty': 1,
                    'product_uom': line.equipment_id.product_id.uom_po_id.id if line.equipment_id.product_id else False,
                    'price_unit': line.estimated_cost,
                    'date_planned': fields.Datetime.now(),
                })],
            })

            purchase_orders.append(po.id)

            # تسجيل في Chatter بتاع المشروع
            self.project_id.message_post(
                body=_("Purchase Order %s created for equipment: %s") % (po.name, line.equipment_id.name),
                message_type="notification"
            )

        # 3. إظهار رسالة نجاح وفتح الـ Purchase Orders
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Orders'),
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', purchase_orders)],
            'target': 'current',
        }


    def action_cancel(self):
        """إغلاق الـ Wizard من غير تنفيذ"""
        return {'type': 'ir.actions.act_window_close'}
