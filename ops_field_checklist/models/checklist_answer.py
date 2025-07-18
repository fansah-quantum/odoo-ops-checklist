from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class ChecklistAnswer(models.Model):
    _name = 'checklist.answer'
    _description = 'Checklist Answer'

    @api.constrains('question_id', 'inspection_activity_id')
    def _check_question_activity(self):
        for record in self:
            if record.question_id.activity_id != record.inspection_activity_id.activity_id:
                raise ValidationError(
                    "Selected question doesn't belong to this activity's checklist!"
                )

    @api.constrains('question_id', 'answer_code_id', 'answer_value')
    def _validate_answer_matches_question(self):
        for record in self:
            question = record.question_id
            if question.answer_type == 'code':
                if not record.answer_code_id:
                    raise ValidationError(
                        "This question requires a coded answer! "
                        "Please select from the available codes."
                    )
                if record.answer_value:
                    raise ValidationError(
                        "This question only accepts coded answers! "
                        "Please remove the text value."
                    )
                if record.answer_code_id not in question.possible_code_ids:
                    raise ValidationError(
                        "Selected answer code is not valid for this question!"
                    )

            elif question.answer_type == 'value':
                if not record.answer_value:
                    raise ValidationError(
                        "This question requires a text value answer!"
                    )
                if record.answer_code_id:
                    raise ValidationError(
                        "This question only accepts text answers! "
                        "Please remove the selected code."
                    )

    inspection_activity_id = fields.Many2one(
        'checklist.inspection.activity',
        string='Inspection Activity',
        ondelete='cascade'
    )
    question_id = fields.Many2one(
        'checklist.question',
        string='Question',
        required=True,
        domain="[('activity_id', '=', parent.activity_id)]"
    )

    answer_code_id = fields.Many2one('checklist.answer.code', string='Answer Code')
    answer_value = fields.Char(string='Recorded Value')
    question_type = fields.Selection(related='question_id.answer_type')






    def action_confirm_job_request(self):
        """ Confirm the job request for this answer. """
        self.ensure_one()
        if not self.job_request_raised:
            raise UserError("Job request has not been raised yet.")
        self.job_request_status = 'confirmed'

    def action_cancel_job_request(self):
        """ Cancel the job request for this answer. """
        self.ensure_one()
        if not self.job_request_raised:
            raise UserError("Job request has not been raised yet.")
        self.job_request_status = 'cancelled'
