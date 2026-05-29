from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    back_office_user = fields.Boolean('Back Office User')
    mobile_user = fields.Boolean('Mobile User')
    kanban_color = fields.Char(
        string='Stage Color',
        help="Hex color code (e.g., #FF0000 for red)",
        default='#FFFFFF'
    )
    code = fields.Char(string="Code", required=True, index=True)
    whatsapp_bool = fields.Boolean(string="Whatsapp", default=False)
    whatsapp_en_template = fields.Text(string="Whatsapp English")
    whatsapp_ar_template = fields.Text(string="Whatsapp Arabic")
    back_office_user_code = fields.Char(string="Back Office")
    mobile_user_code = fields.Char(string="Mobile User")
    parts_user_code = fields.Char(string="Parts User")
    dynamic_job_state_code = fields.Char(
        string="Allowed Scheduling Status Code",
    )
    internal_technician_status_hide = fields.Char(string="Regular - Internal Status Hide",
                                                  help="When the Technician select other than unit pull out so hide the internal technician status hide")
    other_status_hide = fields.Char(string="Internal - Regular Status Hide",
                                    help="when the technician select unit pull out so hide the other than Internal technician")
    scheduling_status_bool = fields.Boolean(string="Scheduling Status", default=False)
    
    '''Code Added on May 07 2026 by Vijaya Bhaskar client asked for the if the technician reached if same technician in other job card then state was updated '''
    status_copied_bool = fields.Boolean(string = "Mobile Status Copied Y/N",default = False, help = "When technician changes one job card then the other job card  in the same date will be updated the other job card also")
    
    
    @api.constrains('code')
    def _check_code_constraint(self):
        for rec in self:
            code_search = self.env['project.task.type'].search([('code', '=', rec.code), ('id', '!=', rec.id)], limit=1)
            if code_search:
                raise ValidationError("Please enter the code as an unique one")
