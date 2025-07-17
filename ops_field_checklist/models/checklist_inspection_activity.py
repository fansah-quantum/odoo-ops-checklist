from odoo import models, fields
from odoo import api
from odoo.exceptions import UserError


class ChecklistInspectionActivity(models.Model):
    """
    Represents an activity performed during an inspection (LINE).
    This model holds the job request, comments, and the answers for its questions.
    """
    _name = 'checklist.inspection.activity'
    _description = 'Checklist Inspection Activity'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    inspection_id = fields.Many2one('checklist.inspection', string='Inspection', ondelete='cascade')
    activity_id = fields.Many2one('checklist.activity', string='Activity', required=True)
    answer_ids = fields.One2many('checklist.answer', 'inspection_activity_id', string='Answers')
    job_request_raised = fields.Boolean(string='Raise Job Request', default=False)
    comment = fields.Text(string='Activity Comments')
    equipment_id = fields.Many2one(
        related='activity_id.equipment_id',
        string='Equipment',
        help="Equipment associated with this activity. "
             "This is used to track the equipment being inspected or maintained.",
        domain="[('template_id', '=', activity_id.template_id)]"
    )


    equipment_name = fields.Char(related='activity_id.equipment_name', string='Equipment Name', readonly=True)
    template_id = fields.Many2one(
        'checklist.template',
        compute='_compute_template_id',
        store=True,
        precompute=True,
        readonly=True
    )

    attachment_ids = fields.Many2many(
        'ir.attachment',
        string="Attached Documents",
        help="Attach all relevant documents, photos, or reports for this activity."
    )

    job_request_state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string="Job Request Status", default='draft')

    maintenance_request_id = fields.Many2one('maintenance.request', string='Job Request', readonly=True)
    display_name = fields.Char(compute='_compute_display_name', store=True)
    supervisor_comment = fields.Text(
        string='Supervisor\'s Comment',
        help="Comment from the supervisor after reviewing the activity."
        )
    respondent_team_id = fields.Many2one(
        'maintenance.team',
        string='Respondent Team',
        domain="[('is_checklist_team', '=', True)]",
        help="Team responsible for responding to the job request raised from this activity."
    )

    job_status = fields.Selection([
        ('completed', 'Completed'),
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
    ], string='Job State', default='pending', help="Current state of the job request."
    )
    checklist_job_request_id = fields.Many2one(
        'checklist.job.request',
        string='Checklist Job Request',
        help="Link to the job request created for this activity."
    )

    respondent_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Respondent User",
        help="User responsible for handling this job request.",
        tracking=True,
    )






    @api.depends('activity_id.name', 'inspection_id.name')
    def _compute_display_name(self):
        for record in self:
            activity = record.activity_id.name or 'Activity'
            inspection = record.inspection_id.name or 'Inspection'
            record.display_name = f"{activity} - {inspection}"


    @api.depends('inspection_id.template_id', 'activity_id.template_id')
    def _compute_template_id(self):
        for record in self:
            record.template_id = record.inspection_id.template_id or record.activity_id.template_id


    def action_view_activity_details(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Activity Details',
            'res_model': 'checklist.inspection.activity',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('ops_field_checklist.checklist_inspection_activity_form_view').id,
            'target': 'current',
            'context': {'form_view_initial_mode': 'readonly'},
        }

    def action_back_to_inspection(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'checklist.inspection',
            'res_id': self.inspection_id.id,
            'views': [(False, 'form')],
            'target': 'main',
        }

    def action_confirm_job_request(self):
        """ Confirm the job request for this activity. """
        self.ensure_one()
        if not self.job_request_raised:
            raise UserError("Job request has not been raised yet.")
        self.job_request_state = 'confirmed'

        for activity in self:
            if not activity.checklist_job_request_id:
                # Create a job request if it doesn't exist
                checklist_job_request = self.env['checklist.job.request'].create({
                    'name': f"Job Request for {activity.activity_id.name}",
                    'inspection_activity_id': activity.id,
                    'equipment_id': activity.equipment_id.id or False,
                    'respondent_team_id': activity.respondent_team_id.id or False,
                    'owner_user_id': self.env.user.id,
                    "respondent_user_id": activity.respondent_user_id.id or False,
                })
                activity.checklist_job_request_id = checklist_job_request.id

            else:
                activity.checklist_job_request_id.write({
                    'equipment_id': activity.equipment_id.id or False,
                    'respondent_team_id': activity.respondent_team_id.id or False,
                })
            # send notification to the respondent user and the owner user
            self.send_notification()

            # if not activity.maintenance_request_id:
            #     # Create a maintenance request if it doesn't exist
            #     maintenance_request = self.env['maintenance.request'].create({
            #         'name': f"Job Request for {activity.activity_id.name}",
            #         'inspection_activity_id': activity.id,
            #         'description': activity.comment or '',
            #         'maintenance_team_id': activity.respondent_team_id.id or False,
            #         'equipment_name': activity.activity_id.equipment_name,
            #     })
            #     activity.maintenance_request_id = maintenance_request.id
            # else:
            #     activity.maintenance_request_id.write({
            #         'description': activity.comment or '',
            #     })

    def action_cancel_job_request(self):
        """ Cancel the job request for this activity. """
        self.ensure_one()
        if not self.job_request_raised:
            raise UserError("Job request has not been raised yet.")
        self.job_request_state = 'cancelled'



    # @api.model
    # def default_get(self, fields_list):
    #     res = super().default_get(fields_list)
    #     if 'inspection_id' in res and 'template_id' not in res:
    #         inspection = self.env['checklist.inspection'].browse(res['inspection_id'])
    #         res['template_id'] = inspection.template_id.id
    #     return res

    def send_notification(self):
        """
        Send a notification to the respondent team and owner user.
        This method can be called after creating or confirming a job request.
        """
        for activity in self:
            if activity.respondent_team_id:
                # Notify the respondent team
                activity.respondent_team_id.message_post(
                    body=f"New job request created for activity: {activity.display_name}",
                    subtype_xmlid='mail.mt_comment'
                )
            if not activity.respondent_team_id:
                activity.message_post(
                    body=f"Job request on activity: {activity.display_name} has been created. Kindly attend to it.",
                    partner_ids=[self.env.user.partner_id.id],
                    subtype_xmlid='mail.mt_comment'
                )
            if activity.respondent_user_id:
                activity.message_post(
                    body=f"Job request on activity: {activity.display_name} has been created. Kindly attend to it.",
                    partner_ids=[activity.respondent_user_id.partner_id.id],
                    subtype_xmlid='mail.mt_comment'
                )
            if activity.inspection_id.officer_id:
                self.message_post(
                    body=f"Job request on activity: {activity.display_name} has been confirmed.",
                    partner_ids=[activity.inspection_id.officer_id.partner_id.id],
                    subtype_xmlid='mail.mt_comment'
                )



