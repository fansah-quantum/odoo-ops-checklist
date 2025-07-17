from odoo import models, fields


class ChecklistAnswerCode(models.Model):
    _name = 'checklist.answer.code'
    _description = 'Checklist Answer Code'

    name = fields.Char(string='Code', required=True)
    description = fields.Char(string='Description', required=True)
