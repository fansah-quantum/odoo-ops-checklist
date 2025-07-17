from odoo import models, fields, api


class ChecklistJobRequest(models.Model):
    _name = "checklist.job.request"
    _description = "Checklist Job Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Job Request Name",
        required=True,
        tracking=True,
    )
    inspection_activity_id = fields.Many2one(
        comodel_name="checklist.inspection.activity",
        string="Inspection Activity",
        required=True,
        tracking=True,
    )
    equipment_name = fields.Char(
        related="inspection_activity_id.equipment_name",
        string="Equipment Name",
        readonly=True,
        store=True,
        help="Name of the equipment associated with this job request.",
    )

    equipment_id = fields.Many2one(
        comodel_name="checklist.equipment",
        string="Equipment",
        help="Equipment associated with this job request.",
        # domain="[('template_id', '=', inspection_activity_id.template_id)]",
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        tracking=True,
    )
    request_date = fields.Datetime(
        string="Request Date",
        default=fields.Datetime.now,
        tracking=True,
    )
    respondent_team_id = fields.Many2one(
        comodel_name="res.partner",
        string="Respondent Team",
        help="Team responsible for handling this job request.",
        tracking=True,
    )
    respondent_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Respondent User",
        help="User responsible for handling this job request.",
        tracking=True,
    )
    archive = fields.Boolean(default=False, help="Set archive to true to hide the checklist job request without deleting it.")
    color = fields.Integer("Color Index", default=0)
    kanban_state = fields.Selection(
        [('normal', 'In Progress'), ('blocked', 'Blocked'), ('done', 'Ready for next stage')],
        string='Kanban State', required=True, default='normal', tracking=True)
    inspected_area = fields.Char(
        string="Inspected Area",
        help="Area of the equipment that was inspected during this job request.",
        tracking=True,
        compute ="_compute_inspected_area",
        store=True,
    )
    owner_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Resquested By",
        help="User who created this job request.",
        tracking=True,
    )

    job_request_reference = fields.Char(
        string="Job Request Reference",
    )


    @api.model
    def create(self, vals):
        if not vals.get('job_request_reference'):
            vals['job_request_reference'] = self.env['ir.sequence'].next_by_code('checklist.job.request')
        return super(ChecklistJobRequest, self).create(vals)






    @api.depends('inspection_activity_id')
    def _compute_inspected_area(self):
        for record in self:
            if record.inspection_activity_id:
                record.inspected_area = record.inspection_activity_id.template_id.name
            else:
                record.inspected_area = False

    def _track_subtype(self, init_values):
        self.ensure_one()
        if "state" in init_values and init_values["state"] != self.state:
            if self.state == "completed":
                self.write({
                    "kanban_state": "done",
                })
                inspection_activity = self.env['checklist.inspection.activity'].browse(self.inspection_activity_id.id)
                inspection_activity.job_status = 'completed'
                return self.env.ref('mail.mt_note')
            return  super(ChecklistJobRequest, self)._track_subtype(init_values)







