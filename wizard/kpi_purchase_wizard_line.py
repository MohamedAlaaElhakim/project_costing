from odoo import api, fields, models, _


class KpiPurchaseWizardLine(models.TransientModel):
    _name = "kpi.purchase.wizard.line"
    _description = "Purchase Wizard Equipment Line"

    wizard_id = fields.Many2one("kpi.purchase.wizard", string="Wizard", ondelete="cascade")

    equipment_id = fields.Many2one("maintenance.equipment", string="Equipment", required=True)
    vendor_id = fields.Many2one("res.partner", string="Vendor", required=True)
    estimated_cost = fields.Monetary(string="Estimated Cost", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", string="Currency", default=lambda self: self.env.company.currency_id)
    select = fields.Boolean(string="Select", default=True)