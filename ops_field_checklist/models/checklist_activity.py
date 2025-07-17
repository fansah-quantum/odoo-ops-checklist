from odoo import models, fields
from odoo import api


class ChecklistActivity(models.Model):
    _name = 'checklist.activity'
    _description = 'Checklist Activity'
    _order = 'sequence'

    sequence = fields.Integer(default=10)
    template_id = fields.Many2one('checklist.template', string='Template', ondelete='cascade')
    name = fields.Char(string='Activity Name', required=True)
    equipment_name = fields.Char(string='Equipment Name')
    equipment_reference = fields.Char(string='Equipment Reference', compute='_compute_equipment_reference', store=True)
    question_ids = fields.One2many('checklist.question', 'activity_id', string='Questions')

    equipment_id = fields.Many2one(
        "checklist.equipment",
        string="Equipment",
        help="Equipment associated with this activity. "
             "This is used to track the equipment being inspected or maintained.",
        domain="[('template_id', '=', template_id)]"
    )

    @api.depends('equipment_name')
    def _compute_equipment_reference(self):
        """Compute the equipment reference based on the equipment name."""
        for record in self:
            if record.equipment_name:
                record.equipment_reference = f"{record.equipment_name[:3].upper()}-{str(record.id).zfill(4)}"
            else:
                record.equipment_reference = ''








