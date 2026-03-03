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
        """نسخة معالجة لخطأ AttributeError في المعدات"""
        self.ensure_one()

        selected_lines = self.line_ids.filtered(lambda x: x.select)
        if not selected_lines:
            raise UserError(_("Please select at least one equipment to purchase."))

        purchase_orders = []

        for line in selected_lines:
            product = False
            if line.equipment_id:
                product = getattr(line.equipment_id, 'product_id', False)

            if not product:
                raise UserError(_(
                    "المعدة '%s' غير مرتبطة بمنتج (Product).\n"
                    "تأكد من إضافة حقل product_id لموديل maintenance.equipment أولاً."
                ) % line.equipment_id.name)

            po_vals = {
                'partner_id': line.vendor_id.id,
                'origin': f"Project: {self.project_id.name}",
                'order_line': [(0, 0, {
                    'product_id': product.id,
                    'name': product.display_name or line.equipment_id.name,
                    'product_qty': 1.0,
                    'product_uom': product.uom_po_id.id or product.uom_id.id,
                    'price_unit': line.estimated_cost or 0.0,
                    'date_planned': fields.Datetime.now(),
                })],
            }

            po = self.env['purchase.order'].create(po_vals)
            po.order_line._compute_tax_id()
            purchase_orders.append(po.id)

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