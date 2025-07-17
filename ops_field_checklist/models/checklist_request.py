from odoo import models, fields


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    inspection_activity_id = fields.Many2one('checklist.inspection.activity', string='Originating Inspection Activity')
    equipment_name = fields.Char(
        related='inspection_activity_id.equipment_name',
        string='Equipment Name',
        readonly=True,
        store=True,
        help="Name of the equipment associated with this maintenance request."
    )
    equipment_id = fields.Many2one(
        'checklist.equipment',
        string='Equipment',
        help="Equipment associated with this maintenance request.",
        domain="[('template_id', '=', inspection_activity_id.template_id)]"
    )