from odoo import models, fields


class ChecklistQuestion(models.Model):
    _name = 'checklist.question'
    _description = 'Checklist Question'
    _order = 'sequence'

    sequence = fields.Integer(default=10)
    activity_id = fields.Many2one('checklist.activity', string='Activity', ondelete='cascade')
    name = fields.Char(string='Question/Prompt', required=True)

    answer_type = fields.Selection([
        ('code', 'Select a Code'),
        ('value', 'Record a Value')
    ], required=True, default='code')
    possible_code_ids = fields.Many2many('checklist.answer.code', string='Possible Codes')

