from odoo import models, fields, api
from odoo.exceptions import UserError


# ========================================================
# Post Service Checklist Template (Header)
# - One record per Product Category + Service Unit Type
# ========================================================
class PostServiceChecklistTemplate(models.Model):
    _name = 'post.service.checklist.template'
    _description = 'Post Service Checklist Template'
    _order = 'category_id, service_unit_type_id'
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Name', compute='_compute_display_name', store=True,
    )
    category_id = fields.Many2one(
        'product.category',
        string='Product Category',
        required=True,
        domain="[('parent_id', '=', False)]",
        help='Top-level product category (e.g., Midea)',
    )
    service_unit_type_id = fields.Many2one(
        'product.product',
        string='Service Unit Type',
        required=True,
        domain="[('detailed_type', '=', 'service')]",
        help='Service product (e.g., Split, Package, VRF)',        
    )
    product_subgroup = fields.Char(string='Product Subgroup')
    active = fields.Boolean(default=True)

    # --- Checklist Lines ---
    line_ids = fields.One2many(
        'post.service.checklist.line', 'template_id',
        string='Checklist Items',
    )
    # --- Photo Captions ---
    photo_ids = fields.One2many(
        'post.service.checklist.photo', 'template_id',
        string='Photo Captions',
    )

    _sql_constraints = [
        ('unique_category_service_unit',
         'UNIQUE(category_id, service_unit_type_id)',
         'A checklist template already exists for this Product Category and Service Unit Type!'),
    ]

    @api.depends('category_id', 'service_unit_type_id')
    def _compute_display_name(self):
        for rec in self:
            parts = []
            if rec.category_id:
                parts.append(rec.category_id.name)
            if rec.service_unit_type_id:
                parts.append(rec.service_unit_type_id.name)
            rec.display_name = ' / '.join(parts) if parts else 'New'

    def action_copy_checklist(self):
        """Open wizard to copy checklist to another product group."""
        self.ensure_one()
        return {
            'name': 'Copy Checklist To',
            'type': 'ir.actions.act_window',
            'res_model': 'post.service.checklist.copy.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_source_template_id': self.id,
                'default_category_id': self.category_id.id,
            },
        }


# ========================================================
# Checklist Line (each check item in the template)
# ========================================================
class PostServiceChecklistLine(models.Model):
    _name = 'post.service.checklist.line'
    _description = 'Post Service Checklist Line'
    _order = 'section, sequence'

    template_id = fields.Many2one(
        'post.service.checklist.template',
        ondelete='cascade', required=True,
    )
    sequence = fields.Integer(string='SL No', default=10)
    name = fields.Char(string='Check Item', required=True)
    section = fields.Char(
        string='Section / Group',
        help='Group name (e.g., General, Indoor Unit, Outdoor Unit, Package Unit)',
    )
    field_type = fields.Selection([
        ('yes_no', 'Yes / No'),
        ('multiple', 'Multiple Options'),
        ('numeric', 'Numeric'),
        ('text', 'Text'),
        ('date', 'Date'),
        ('calculated', 'Calculated'),
    ], string='Type', default='yes_no', required=True)
    remark = fields.Char(
        string='Remark',
        help='Additional info (e.g., Manual Entry, Calculate formula)',
    )
    active = fields.Boolean(default=True)

    # --- Multiple Options (linked to options master) ---
    option_ids = fields.One2many(
        'post.service.checklist.option', 'line_id',
        string='Options',
    )
    
    '''Code Added on August 05 2026 by Vijaya bhaskar client asked mandatory in the jobcard checklist'''

    mandatory_checklist = fields.Boolean(string = "Mandatory", default = False)
    

    def action_setup_options(self):
        """Open the options master for this checklist item."""
        self.ensure_one()
        if self.field_type != 'multiple':
            raise UserError('Options setup is only available for "Multiple Options" type items.')
        return {
            'name': f'Options: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'post.service.checklist.option',
            'view_mode': 'tree',
            'target': 'new',
            'domain': [('line_id', '=', self.id)],
            'context': {
                'default_line_id': self.id,
            },
        }


# ========================================================
# Multiple Options Master
# - For "Multiple" type items, stores the list of options
# ========================================================
class PostServiceChecklistOption(models.Model):
    _name = 'post.service.checklist.option'
    _description = 'Post Service Checklist Option'
    _order = 'sequence'

    line_id = fields.Many2one(
        'post.service.checklist.line',
        ondelete='cascade', required=True,
        string='Checklist Item',
    )
    sequence = fields.Integer(string='Order', default=10)
    name = fields.Char(string='Option', required=True)
    is_default = fields.Boolean(string='Default', default=False)


# ========================================================
# Photo Caption Template
# - Section/Group, Caption, Sort Order
# ========================================================
class PostServiceChecklistPhoto(models.Model):
    _name = 'post.service.checklist.photo'
    _description = 'Post Service Checklist Photo'
    _order = 'section, sequence'

    template_id = fields.Many2one(
        'post.service.checklist.template',
        ondelete='cascade', required=True,
    )
    sequence = fields.Integer(string='Sort Order', default=10)
    section = fields.Char(
        string='Section / Group',
        help='Group name (e.g., Indoor Unit, Outdoor Unit)',
    )
    caption = fields.Char(
        string='Caption',
        help='Description of what this photo shows (e.g., Air Filter, Evaporator Coil)',
    )

    '''Code Added on August 05 2026 by Vijaya bhaskar client asked mandatory in the jobcard checklist'''
    mandatory_photo = fields.Boolean(string = "Mandatory", default = False)


# ========================================================
# Copy Wizard
# - Copy checklist from one product group to another
# ========================================================
class PostServiceChecklistCopyWizard(models.TransientModel):
    _name = 'post.service.checklist.copy.wizard'
    _description = 'Copy Checklist Wizard'

    source_template_id = fields.Many2one(
        'post.service.checklist.template',
        string='Source Template', readonly=True,
    )
    category_id = fields.Many2one(
        'product.category',
        string='Product Category', readonly=True,
    )
    target_service_unit_type_id = fields.Many2one(
        'product.product',
        string='Target Service Unit Type',
        required=True,
        domain="[('detailed_type', '=', 'service')]",
        help='Select the service unit type to copy this checklist to.',
    )

    def action_copy(self):
        """Copy all checklist lines + photos from source to target product group."""
        self.ensure_one()
        source = self.source_template_id

        # Check if target already exists
        existing = self.env['post.service.checklist.template'].search([
            ('category_id', '=', self.category_id.id),
            ('service_unit_type_id', '=', self.target_service_unit_type_id.id),
        ], limit=1)

        if existing:
            raise UserError(
                f'A checklist template already exists for '
                f'{self.category_id.name} / {self.target_service_unit_type_id.name}. '
                f'Please delete it first or edit it directly.'
            )

        # Create new template
        new_template = self.env['post.service.checklist.template'].create({
            'category_id': self.category_id.id,
            'service_unit_type_id': self.target_service_unit_type_id.id,
            'product_subgroup': source.product_subgroup,
        })

        # Copy checklist lines
        for line in source.line_ids:
            new_line = line.copy({
                'template_id': new_template.id,
            })
            # Copy options for multiple type
            for option in line.option_ids:
                option.copy({
                    'line_id': new_line.id,
                })

        # Copy photo captions
        for photo in source.photo_ids:
            photo.copy({
                'template_id': new_template.id,
            })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'post.service.checklist.template',
            'res_id': new_template.id,
            'view_mode': 'form',
            'target': 'current',
        }
