from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request


class WebPortal(CustomerPortal):
    
    def _prepare_home_portal_values(self, counters):
        res = super(WebPortal,self)._prepare_home_portal_values(counters)
        # res['loan_count'] = request.env['hr.employee.loan.ps'].search_count([])    
        return res
