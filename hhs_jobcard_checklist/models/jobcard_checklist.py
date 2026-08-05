from odoo import models, fields, api


# =============================================================
# Job Card Checklist Response Line
# - Stores the technician's answer for each checklist item
# =============================================================
class JobCardChecklistLine(models.Model):
    _name = 'jobcard.checklist.line'
    _description = 'Job Card Checklist Response Line'
    _order = 'sequence'

    task_id = fields.Many2one(
        'project.task', string='Job Card',
        ondelete='cascade', required=True, index=True,
    )
    template_line_id = fields.Many2one(
        'post.service.checklist.line',
        string='Template Line', ondelete='set null',
    )
    sequence = fields.Integer(string='Sort Order', default=10)
    section_group = fields.Char(string='Section / Group')
    check_item = fields.Char(string='Check Item')
    field_type = fields.Selection([
        ('yes_no', 'Yes / No'),
        ('multiple', 'Multiple Options'),
        ('condition', 'Good / Partial / Damaged'),
        ('numeric', 'Numeric'),
        ('text', 'Text'),
        ('calculated', 'Calculated'),
    ], string='Type', default='yes_no')

    # Response fields (Unified single column)
    jobcard_option_ids = fields.One2many('jobcard.checklist.option', 'jobcard_line_id')
    answer_selection_id = fields.Many2one(
        'jobcard.checklist.option', 
        string='Answer',
        domain="[('jobcard_line_id', '=', id)]"
    )
    answer_text = fields.Char(string='Text / Notes')
    answer_numeric = fields.Float(string='Numeric Value')
    remark = fields.Char(string='Remark')

    answer_display = fields.Char(string='Answer', compute='_compute_answer_display', inverse='_inverse_answer_display', readonly=False)
    option_labels_data = fields.Char(string='Option Labels Data', compute='_compute_option_labels_data')

    '''Code Added on June 01 2026 by Vijaya Bhaskar because some of the state to be disabled'''
    job_card_state_code = fields.Char(
        related='task_id.job_card_state_code',
        string='Job Card State Code',
        store=False,
    )
    
    '''Code Added on August 05 2026 client asked mandatory for some post checklist items'''
    mandatory_checklist = fields.Boolean(string = 'Mandatory Checklist', related= "template_line_id.mandatory_checklist")
    
    
    def _compute_answer_display(self):
        for line in self:
            line.answer_display = ''

    def _inverse_answer_display(self):
        pass

    @api.depends('jobcard_option_ids', 'jobcard_option_ids.name')
    def _compute_option_labels_data(self):
        """Pass option IDs and names as a simple string for JS to parse."""
        for line in self:
            options = []
            for opt in line.jobcard_option_ids:
                options.append(f"{opt.id}:{opt.name}")
            line.option_labels_data = "|".join(options)

    @api.onchange('answer_numeric')
    def _onchange_answer_numeric(self):
        """Update calculated fields (e.g. Δt) when numeric values change."""
        for line in self:
            if line.field_type == 'numeric':
                line.task_id._update_calculated_fields()

class JobCardChecklistOption(models.Model):
    _name = 'jobcard.checklist.option'
    _description = 'Job Card Checklist Option'
    _order = 'sequence'

    jobcard_line_id = fields.Many2one('jobcard.checklist.line', ondelete='cascade', required=True)
    sequence = fields.Integer(string='Order', default=10)
    name = fields.Char(string='Option', required=True)

# =============================================================
# Job Card Checklist Photo Line
# - Stores the before/after photo uploads
# =============================================================
class JobCardChecklistPhoto(models.Model):
    _name = 'jobcard.checklist.photo'
    _description = 'Job Card Checklist Photo'
    _order = 'section, sequence'

    task_id = fields.Many2one(
        'project.task', string='Job Card',
        ondelete='cascade', required=True, index=True,
    )
    template_photo_id = fields.Many2one(
        'post.service.checklist.photo',
        string='Template Photo', ondelete='set null',
    )
    sequence = fields.Integer(string='Sort Order', default=1)
    section = fields.Char(string='Section', default='before', required=True)
    # section = fields.Selection([
    #     ('before', 'Before'),
    #     ('after', 'After'),
    # ], string='Section', default='before', required=True,deprecated =False)
    caption = fields.Char(string='Caption')
    photo = fields.Binary(string='Photo', attachment=True)
    photo_filename = fields.Char(string='Filename')
    
    '''Code Added on June 01 2026 by Vijaya Bhaskar because some of the state to be disabled'''
    job_card_state_code = fields.Char(
        related='task_id.job_card_state_code',
        string='Job Card State Code',
        store=False,
    )
    
    '''Code Added on August 05 2026 client asked mandatory for some post checklist items'''
    
    mandatory_photo = fields.Boolean(string = 'Mandatory Photo', related = "template_photo_id.mandatory_photo")


# =============================================================
# Inherit project.task (Job Card) to add checklist tabs
# =============================================================
class ProjectTask(models.Model):
    _inherit = 'project.task'

    checklist_line_ids = fields.One2many(
        'jobcard.checklist.line', 'task_id',
        string='Post Service Checklist',
    )
    checklist_photo_ids = fields.One2many(
        'jobcard.checklist.photo', 'task_id',
        string='Post Service Photos',
    )
    checklist_loaded = fields.Boolean(
        string='Checklist Loaded', default=False,
        help='Whether the checklist has been loaded from template',
    )

    @api.onchange('brand', 'product_category_id', 'service_products_code_id')
    def _onchange_load_checklist(self):
        """Auto-load checklist when Service Unit Type is set."""
        for task in self:
            if not task.service_products_code_id:
                continue
            task._load_checklist_from_template()

    def action_load_checklist(self):
        """Manual reload button – same logic."""
        for task in self:
            if not task.service_products_code_id:
                continue
            task._load_checklist_from_template()
        return True

    def _load_checklist_from_template(self):
        """Core logic: find matching template and load items + photos."""
        self.ensure_one()

        domain = [('service_unit_type_id', '=', self.service_products_code_id.id)]
        category = False
        if self.product_category_id:
            category = self.product_category_id
        elif self.brand:
            category = self.env['product.category'].search([
                ('name', '=ilike', self.brand.strip()),
            ], limit=1)

        if category:
            domain.append(('category_id', '=', category.id))

        template = self.env['post.service.checklist.template'].search(domain, limit=1)

        if not template:
            # Clear if no matching template
            self.checklist_line_ids = [(5, 0, 0)]
            self.checklist_photo_ids = [(5, 0, 0)]
            self.checklist_loaded = False
            return

        # Clear existing lines
        self.checklist_line_ids = [(5, 0, 0)]
        self.checklist_photo_ids = [(5, 0, 0)]

        # Load checklist items with dynamic options
        checklist_vals = []
        for line in template.line_ids.sorted(key=lambda l: l.sequence):
            option_vals = []
            if line.field_type == 'yes_no':
                option_vals.extend([
                    (0, 0, {'name': 'Yes', 'sequence': 1}),
                    (0, 0, {'name': 'No', 'sequence': 2})
                ])
            elif line.field_type == 'condition':
                option_vals.extend([
                    (0, 0, {'name': 'Good', 'sequence': 1}),
                    (0, 0, {'name': 'Partial', 'sequence': 2}),
                    (0, 0, {'name': 'Bad', 'sequence': 3})
                ])
            elif line.field_type == 'multiple':
                for seq, opt in enumerate(line.option_ids.sorted(key=lambda o: o.sequence)):
                    option_vals.append((0, 0, {'name': opt.name, 'sequence': seq}))
                    
            checklist_vals.append((0, 0, {
                'template_line_id': line.id,
                'sequence': line.sequence,
                'section_group': line.section,
                'check_item': line.name,
                'field_type': line.field_type,
                'jobcard_option_ids': option_vals,
            }))

        # Load photo captions
        photo_vals = []
        for photo in template.photo_ids.sorted(key=lambda p: (p.section, p.sequence)):
            photo_vals.append((0, 0, {
                'template_photo_id': photo.id,
                'sequence': photo.sequence,
                'section': photo.section,
                'caption': photo.caption,
             }))

        self.checklist_line_ids = checklist_vals
        self.checklist_photo_ids = photo_vals
        self.checklist_loaded = True

    def _update_calculated_fields(self):
        """Logic to compute Δt = Return Air Temp - Supply Air Temp."""
        supply_temp = 0.0
        return_temp = 0.0
        calc_line = self.env['jobcard.checklist.line']

        for line in self.checklist_line_ids:
            name = (line.check_item or '').lower()
            if 'supply air temperature' in name:
                supply_temp = line.answer_numeric
            elif 'return air temperature' in name:
                return_temp = line.answer_numeric
            elif line.field_type == 'calculated' or 'temperature difference' in name:
                calc_line = line

        if calc_line:
            calc_line.answer_numeric = return_temp - supply_temp

