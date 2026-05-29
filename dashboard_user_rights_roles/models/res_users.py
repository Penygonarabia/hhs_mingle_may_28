from odoo import api,fields,models,_

class Resusers(models.Model):
    
    _inherit = "res.users"
    
    
    '''Code Added on April 18 2026 by Vijaya Bhaskar for Dashboard'''
    
    work_center_group_ids = fields.Many2many('work.center.group','user_work_center_group_rel',
                                             'user_id',
                                             'work_center_group_id',
                                             string = "Work Center Group")
    
    '''Code Added on April 18 2026 by Vijaya Bhaskar for Dashboard'''
    # user_role_selection = fields.Selection([('call_center','Call Center'),('parts_user','Parts'),('co_ordinator','Co-Ordinator'),('manager','Manager'),('supervisor','Supervisor')],string = "User Selection",
    #                                             help = "User Rights For Dashboard Purpose")
    #

    '''Code Added on April 18 2026 by Vijaya Bhaskar for Dashboard'''
    dashboard_type_selection = fields.Selection([('individual','Individual'),('manager','Manager')],string = "User Roles")
    
    
    
    
    '''code Added on April 24 2026 by Vijaya Bhaskar'''
    user_rights_roles_ids = fields.Many2many('dashboard.user.rights',
                                         'user_dashboard_rights_rel',
                                         'user_id',
                                         'dashboard_rights_id',
                                         string = "User Selection"
                                         
                                         )