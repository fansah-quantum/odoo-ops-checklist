from odoo import models, fields
from odoo import api


class ChecklistTemplate(models.Model):
    _name = 'checklist.template'
    _description = 'Checklist Template'

    name = fields.Char(string='Checklist Area Name', required=True)
    checklist_type = fields.Selection([
        ('standard', 'Standard'),
        ('ppe', 'PPE'),
    ], string='Checklist Type', required=True, default='standard')
    activity_ids = fields.One2many('checklist.activity', 'template_id', string='Activities')
    color = fields.Integer(string='Color Index', default=0, help="Color index for the checklist template.")
    inspection_count = fields.Integer(compute='_compute_inspection_count', store=False)
    job_request_count = fields.Integer(compute='_compute_job_request_count', store=False)


    equipment_ids = fields.One2many(
        'checklist.equipment',
        'template_id',
        string='Equipment',
        help="Equipment associated with this checklist template."
    )

    @api.depends('activity_ids')
    def _compute_inspection_count(self):
        for template in self:
            template.inspection_count = self.env['checklist.inspection'].search_count([
                ('template_id', '=', template.id)
            ])

    @api.depends('activity_ids')
    def _compute_job_request_count(self):
        for template in self:
            template.job_request_count = self.env['checklist.inspection.activity'].search_count([
                ('template_id', '=', template.id),
                ('job_request_raised', '=', True)
            ])

    # class ChecklistCategory(models.Model):
    #     """'will rather replace the checklist template with a category that can be used for both standard and PPE
    #     checklists."""
    #
    #     _inherit = 'maintenance.category'
    #
    #     checklist_type = fields.Selection(
    #         ('standard', 'Standard'),
    #         ('ppe', 'PPE'),
    #         string='Checklist Type',
    #         default='standard',
    #         help="Type of checklist associated with this category."
    #     )
    #
    #     activity_ids = fields.Many2many(
    #         'maintenance.equipment',
    #         string='Equipment',
    #         help="Equipment associated with this category for checklist purposes."
    #     )

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


class ChecklistEquipment(models.Model):
    _name = 'checklist.equipment'
    _description = 'Checklist Equipment For Checklist Template'

    name = fields.Char(string='Equipment Name', required=True)
    reference = fields.Char(string='Equipment Reference', compute='_compute_reference',)
    template_id = fields.Many2one('checklist.template',
                                  string='Checklist Template',
                                  ondelete='cascade',
                                  help="Checklist template this equipment is associated with."
                                  )

    @api.depends('name')
    def _compute_reference(self):
        """Compute the equipment reference based on the equipment name."""
        for record in self:
            if record.name:
                record.reference = f"{record.name[:3].upper()}-{str(record.id).zfill(4)}"
            else:
                record.reference = ''

    @api.model
    def create(self, vals):
        """Override create method to ensure unique equipment names within the same template."""
        if 'name' in vals and 'template_id' in vals:
            existing = self.search([
                ('name', '=', vals['name']),
                ('template_id', '=', vals['template_id'])
            ])
            if existing:
                raise ValueError("Equipment name must be unique within the same checklist template.")
        record =  super(ChecklistEquipment, self).create(vals)
        record.reference  = f"{record.name[:3].upper()}-{str(record.id).zfill(4)}"
        return record

    def write(self, vals):
        """Override write method to ensure unique equipment names within the same template."""
        if 'name' in vals:
            for record in self:
                existing = self.search([
                    ('name', '=', vals['name']),
                    ('template_id', '=', record.template_id.id),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValueError("Equipment name must be unique within the same checklist template.")
        result = super(ChecklistEquipment, self).write(vals)
        if 'name' in vals:
            for record in self:
                record.reference = f"{record.name[:3].upper()}-{str(record.id).zfill(4)}"
        return result
