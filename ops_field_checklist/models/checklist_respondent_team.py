from odoo import models, fields


class ChecklistRespondentTeam(models.Model):
    _inherit = 'maintenance.team'

    is_checklist_team = fields.Boolean(
        string="Checklist Inspection Team",
        help="Check this box if this team handles job requests from field inspections."
    )
