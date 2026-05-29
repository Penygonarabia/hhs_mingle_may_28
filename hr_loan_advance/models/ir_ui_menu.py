from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    # @api.model
    # def search(self, args, offset=0, limit=None, order=None, count=False):
    #     # TODO : remove this try catch if you didnt face any issues
    #     employee_obj = self.env['hr.employee']
    #     uid = self.env.uid
    #     is_direct_manager = False
    #     is_coach = False
    #     # employee = user.employee_ids and user.employee_ids[0]
    #     direct_manager_ids = employee_obj.search([('parent_id.user_id', '=', uid)])
    #     if len(direct_manager_ids):
    #         is_direct_manager = True
    #     try: #Hide a menu based on the value in company master
    #         hr_mgr_loan_menu = self.env.ref('hr_loan_advance.menu_open_hr_employee_loan_ps_hrm')
    #         d_mgr_loan_menu = self.env.ref('hr_loan_advance.menu_open_hr_employee_loan_ps_direct')
    #         group_user = self.user_has_groups('hr.group_user')
    #         group_hr_manager = self.user_has_groups('hr.group_hr_manager')
    #         if uid != 1:
    #             args = args + [('id', 'not in', [d_mgr_loan_menu.id])]
    #         if group_user and not group_hr_manager:
    #             args = args + [('id', 'not in', [hr_mgr_loan_menu.id])]
    #         # if group_hr_manager :
    #         if not is_direct_manager:
    #             args = args + [('id', 'not in', [d_mgr_loan_menu.id])]
    #
    #     except UserError as e:
    #         _logger.info('ERROR ON LOADING MENUS. ' + str(e))
    #         pass
    #     return super(IrUiMenu, self).search(args, offset=0, limit=None, order=order, count=False)
