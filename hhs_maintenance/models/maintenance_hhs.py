# from odoo import fields, models, api
#
#
# class MaintenanceEquipment(models.Model):
#     _inherit = "maintenance.equipment"
#
#     maintenance_equipment_bool = fields.Boolean(string="Maintenance Equipment Tab Show",
#                                                 compute="_compute_maintenance_equipment_bool")
#     brand_id = fields.Many2one('brand', string='Brand')
#     model_id = fields.Many2one('equipment.model.code', string='Model')
#
#     @api.onchange('brand_id')
#     def _onchange_brand_id(self):
#         if self.brand_id:
#             return {'domain': {'model_id': [('brand_id', '=', self.brand_id.id)]}}
#         else:
#             return {'domain': {'model_id': []}}
#
#     @api.depends('equipment_assign_to')
#     def _compute_maintenance_equipment_bool(self):
#         self.maintenance_equipment_bool = False
#         equipment = self.env['ir.config_parameter'].sudo().get_param(
#             'hhs_maintenance.maintenance_equipment_show')
#
#         if equipment == 'True':
#             self.maintenance_equipment_bool=True
#
#         # if self.maintenance_equipment_bool=='True':
#         #     self.equipment_assign_to='other'
#         #     print("-----------------------=---------------------------",self.equipment_assign_to)
#
#
#
#
# class MaintenanceMixin(models.AbstractModel):
#     _inherit = 'maintenance.mixin'
#
#     technician_user_id = fields.Many2one('res.users', string='Default Technician', tracking=True)
#
#


