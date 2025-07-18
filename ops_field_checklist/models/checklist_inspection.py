from odoo import models, fields
from odoo import api
from odoo.exceptions import ValidationError

from datetime import date


class ChecklistInspection(models.Model):
    _name = 'checklist.inspection'
    _description = 'Checklist Inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.constrains('inspection_activity_ids')
    def _validate_activities(self):
        for inspection in self:
            if inspection.template_id:
                invalid_activities = inspection.inspection_activity_ids.filtered(
                    lambda a: a.activity_id.template_id != inspection.template_id
                )
                if invalid_activities:
                    raise ValidationError(
                        f"Activity {invalid_activities[0].activity_id.name} doesn't belong to template {inspection.template_id.name}"
                    )

    name = fields.Char(string='Reference',
                                readonly=True)
    template_id = fields.Many2one('checklist.template', string='Area Inspected', required=True)
    officer_id = fields.Many2one('res.users',
                                 string='Completed By',
                                 required=True,
                                 )
    start_date = fields.Date(string='Inspection Date', default=fields.Date.context_today)
    date_completed = fields.Date(string='Date Completed')
    state = fields.Selection([
        ('new', 'New'),
        ('missed', 'Missed'),
        ('completed', 'Completed'),
        ('reviewed', 'Reviewed'),
    ], string='Status', default='new')

    ppe_observed_staff_name = fields.Char(string='Name of Staff Observed')
    ppe_activity_type = fields.Char(string='Type of Activity')
    ppe_location = fields.Char(string='Location of Inspection')
    template_checklist_type = fields.Selection(related='template_id.checklist_type')
    inspection_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')
    ], string='Inspection Type', default='daily', required=True)

    inspection_activity_ids = fields.One2many(
        'checklist.inspection.activity',
        'inspection_id',
        string='Inspected Activities',
        domain="[('inspection_id.template_id', '=', template_id)]"
    )

    due_date = fields.Date(string="Due Date", tracking=True)
    inspection_count = fields.Integer(
        compute='_compute_dashboard_stats',
        string='Number of Inspections',
        help="Total number of inspections for this template."
    )
    job_request_count = fields.Integer(
        compute='_compute_dashboard_stats',
        string='Job Requests',
        help="Total number of job requests raised from this inspection."
    )
    color = fields.Integer("Color Index", default=1)


    #
    # @api.model
    # def create(self, vals):
    #     if vals.get('name', 'New') == 'New':
    #         vals['name'] = self.env['ir.sequence'].next_by_code('checklist.inspection') or 'New'
    #     return super(ChecklistInspection, self).create(vals)

    @api.model
    def write(self, vals):
        if 'officer_id' in vals and vals.get('officer_id'):
            officer = self.env['res.users'].browse(vals['officer_id'])
            self.message_subscribe(partner_ids=[officer.partner_id.id])
            message_body = f"You have been assigned a new inspection: <b>{self.name}</b>."
            self.message_post(body=message_body, partner_ids=[officer.partner_id.id])
        return super(ChecklistInspection, self).write(vals)

    def notify_officer(self):
        for inspection in self:
            message_body = f"You have been assigned a new inspection: <b>{inspection.name}</b>."
            inspection.message_post(body=message_body, partner_ids=[inspection.officer_id.partner_id.id])

    @api.model
    def create(self, vals):
        """
        Overrides the create method to validate data submitted by an API.
        """
        if vals.get('state') == 'completed':
            template_id = vals.get('template_id')
            answer_data = vals.get('answer_ids', [])

            if not template_id:
                raise ValidationError("An inspection template must be provided.")
            template = self.env['checklist.template'].browse(template_id)
            self._validate_inspection_answers(template, answer_data)
        vals['name'] = self.env['ir.sequence'].next_by_code('checklist.inspection') or 'New'
        record = super(ChecklistInspection, self).create(vals)
        if vals.get('officer_id'):
            officer = self.env['res.users'].browse(vals['officer_id'])
            record.message_subscribe(partner_ids=[officer.partner_id.id])
            message_body = f"You have been assigned a new inspection to inspect {record.template_id.name}. due on {record.due_date}. Please complete it as soon as possible."
            record.message_post(body=message_body, partner_ids=[officer.partner_id.id])
        return record


    def _validate_inspection_answers(self, template, answer_data):
        """
        A helper method containing the core validation logic.
        This can be reused by both create() and write() methods.
        """
        if not answer_data:
            raise ValidationError("Inspection must contain answers.")
        submitted_answers_vals = [vals for cmd, record_id, vals in answer_data]
        expected_questions = template.mapped('activity_ids.question_ids')
        submitted_question_ids = {vals.get('question_id') for vals in submitted_answers_vals}

        if not submitted_question_ids.issubset(set(expected_questions.ids)):
            raise ValidationError("One or more answers refer to questions not found in the selected template.")
        if len(expected_questions) != len(submitted_question_ids):
            raise ValidationError("Not all questions for this template have been answered.")
        question_types = {q.id: q.answer_type for q in expected_questions}

        for answer in submitted_answers_vals:
            question_id = answer.get('question_id')
            question_type = question_types.get(question_id)

            if question_type == 'value' and not answer.get('answer_value'):
                raise ValidationError(f"A value is required for one of the questions, but was not provided.")

            if question_type == 'code' and not answer.get('answer_code_id'):
                raise ValidationError(f"A code must be selected for one of the questions, but was not provided.")

        return True

    def action_complete_inspection(self):
        """
        Button-triggered method for UI interaction.
        It now reuses the same validation logic.
        """
        self.ensure_one()
        answer_data_for_validation = [
            (0, 0, {'question_id': ans.question_id.id,
                    'answer_code_id': ans.answer_code_id.id,
                    'answer_value': ans.answer_value})
            for ans in self.answer_ids
        ]
        self._validate_inspection_answers(self.template_id, answer_data_for_validation)
        self.write({'state': 'done'})

    def action_confirm_review(self):
        """
        check if all activities with job request raised are confirmed, or cancelled.
        """
        self.ensure_one()
        activities_with_job_requests = self.inspection_activity_ids.filtered(
            lambda a: a.job_request_raised
        )
        if not all(
                activity.job_request_state in ['confirmed', 'cancelled'] for activity in activities_with_job_requests):
            raise ValidationError("All activities with job requests must be confirmed or cancelled before review.")
        self.write({'state': 'reviewed'})

    @api.model
    def _process_missed_inspections(self):
        missed_inspections = self.search([
            ('state', '=', 'new'),
            ('due_date', '<', date.today())
        ])
        for inspection in missed_inspections:
            inspection.write({'state': 'missed'})
            message_body = f"The inspection <b>{inspection.name}</b> was missed and is now overdue."
            inspection.message_post(body=message_body, partner_ids=[inspection.officer_id.partner_id.id])

    @api.depends('inspection_activity_ids')
    def _compute_dashboard_stats(self):
        inspection = self.env['checklist.inspection']
        for template in self:
            template.inspection_count = inspection.search_count(
                [('template_id', '=', template.id)]
            )
            template.job_request_count = self.env['checklist.inspection.activity'].search_count([
                ('inspection_id.template_id', '=', template.id),
                ('job_request_state', 'in', ['raised', 'confirmed'])
            ])

    def action_view_inspections(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Inspections for {self.name}',
            'res_model': 'checklist.inspection',
            'view_mode': 'kanban,tree,form',
            'domain': [('template_id', '=', self.id)],
            'context': {'default_template_id': self.id}
        }



    # @api.model
    # def default_get(self, fields_list):
    #     result = super().default_get(fields_list)
    #     if not result.get('name'):
    #         result['name'] = self.env['ir.sequence'].next_by_code('checklist.inspection') or 'New'
    #     return  result


