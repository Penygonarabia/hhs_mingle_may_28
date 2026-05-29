from odoo import http
from odoo.http import request
from odoo.addons.web.controllers import main

import logging
_logger = logging.getLogger(__name__)

class OrgChart(http.Controller):
    
    @http.route('/orgchart/get_user_group', type="json", auth='user')                
    def get_user_group(self, user_id):
        if user_id:
            data = []
            is_hr_manager = request.env.user.has_group('hr.group_hr_manager')
            is_hr_user = request.env.user.has_group('hr.group_hr_user')
            data.append({
                'is_hr_user': is_hr_user,
                'is_hr_manager': is_hr_manager,
            })
            return data
        else:
            return False
    
    @http.route('/orgchart/getdata', type="json", auth="user")
    def get_orgchart_data(self, company_id):
        data = {}        
        company_env = request.env['res.company']
        employee_env = request.env['hr.employee']        
        company =  company_env.sudo().search([('id', '=', int(company_id))])                
        if company:
            data['id'] = -(company.id)
            data['name'] = company.name
            data['title'] = company.country_id.name if company.country_id.name else ''
            data['children'] = []
            data['_name'] = company._name
            
            employees = employee_env.search([('parent_id', '!=', False),('company_id', '=', company.id),('state','=','draft')])
            #employees = employee_env.search([('parent_id', '=', False),('company_id', '=', company.id)])
            for employee in employees:
                reportees = self.get_reportees(employee, company)
                data['children'].append(reportees)
                    
        return {'data': data}
        
    def get_reportees(self, employee, company):
        children = []
        employee_env = request.env['hr.employee']        
        data = {
            'id': employee.id, 
            'name': employee.name, 
            'title':  employee.job_id.name,
            '_name': employee._name,
        }
        direct_reportees = employee_env.search([('parent_id', '=', employee.id),('company_id', '=', company.id)])
        for reportee in direct_reportees:
            direct_reportee = employee_env.search([('parent_id', '=', reportee.id),('company_id', '=', company.id)])
            if not direct_reportee:
                child_data = {
                    'id': reportee.id,
                    'name': reportee.name,
                    'title': reportee.job_id.name,
                    '_name': reportee._name,
     			}
                children.append(child_data)
            else:
                reportees = self.get_reportees(reportee, company)
                children.append(reportees)
        if direct_reportees:
            data['children'] = children
        return data
    
    @http.route('/orgchart/update', type='json', auth="user")
    def update_org_chart(self, source_id, target_id):
        if source_id and target_id:
            source = request.env['hr.employee'].search([('id','=',int(source_id))], limit=1)
            target = request.env['hr.employee'].search([('id','=',int(target_id))], limit=1)
            if source and target:
                source.sudo().write({
                    'parent_id' : target.id,
                })
                return True
            else:
                return False
        else:
            return False
