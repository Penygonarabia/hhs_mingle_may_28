from odoo import api,fields,models,_
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, time
import base64
import io

class JobCardReport(models.TransientModel):
    
    _name = "job.card.report"
    
    
    job_card_ids = fields.Many2many('project.task',string="Job Card")

    product_category_ids = fields.Many2many('product.category', string="Product Category")

    from_date = fields.Date(string='From Date', required=True,
                            default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    to_date = fields.Date(string='To Date', required=True, default=lambda self: fields.Date.to_string(
        (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    
    region_id = fields.Many2one('res.region', string="Region")
    
    work_center_group_id = fields.Many2one('work.center.group',string = "Region")
    
    # status = fields.Selection([('new','New'),('scheduled','Scheduled'),('parts_required','Parts Required'),
    #                                    ('completed','Completed'), ('cancelled','Cancelled'), ('closed','Closed')],string="Status")
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,required=True)

    logo = fields.Binary("Company Logo")
    
    
    job_state_ids = fields.Many2many(
        'project.task.type',
        string="Job Status",
        domain=lambda self: self._get_job_state_domain(),
        tracking=True,
        store=True,
    )
    '''Code Added on June 10 2026 by Vijaya Bhaskar'''
    action_status = fields.Selection([('closed','Closed'),('cancelled','Cancelled'),('not_closed','Not Closed')],string = "Action Status")
    
    
    @api.model
    def _get_job_state_domain(self):
        domain = []
        project = self.env['project.project'].search([('name','=','HHS')],limit = 1)
        if project.exists():
            domain.append(('project_ids', '=', project.id))
    
        return domain

    
    @api.constrains('from_date', 'to_date')
    def _check_from_date(self):
        if self.filtered(lambda c: c.to_date and c.from_date > c.to_date):
            raise ValidationError(_('From date Date must be less than Period To Date.'))
    
    #
    # @api.onchange('from_date')
    # def _onchange_from_date(self):
    #     for rec in self:
    #         if rec.from_date:
    #             rec.to_date = rec.from_date
    #
    #
    def print_job_card_report_xlsx(self):
        company = self.company_id
        logo = base64.b64decode(company.logo) if company.logo else False
        datas = {
            'model': 'job.card.report',
            'form_data': self.read()[0],
            'logo': logo,
            
        }
        return self.env.ref('machine_repair_management.action_job_card_report_xlsx').report_action(self, data=datas)
    
    
    def print_pdf_report(self):
        
        domain = []
       
        # domain.append('id', 'in',
        #            self.job_card_ids.ids if self.job_card_ids else self.env['project.task'].search([]).ids)

        if self.from_date :
            domain.append(('service_created_datetime', '<=', self.to_date))

        if self.to_date:
            domain.append(('service_created_datetime', '>=', self.from_date))

        if self.job_card_ids:
            domain.append(('id', 'in', self.job_card_ids.ids))
        if self.product_category_ids:
            domain.append(('product_category_id', 'in', self.product_category_ids.ids))
            
        if self.work_center_group_ids:
            domain.append(('work_center_id.work_center_group_id','in', self.work_center_group_ids.ids))   
         
            
        job_card_search = self.env['project.task'].search((domain))
      
        # if self.job_card_ids:
        #     job_card_search = job_card_search.sorted(key=lambda c: c.name.lower())
        #
        # if self.product_category_ids:
        #     job_card_search = job_card_search.sorted(key=lambda c: c.product_category_id.name.lower())
        #

        
        job_lst = []
        for job in job_card_search:
            
            vals ={
                
                'name':job.name,
                'location':job.location_id.name,
                'partner_id':job.partner_id.name,
                'address': job.address,
                'service_created_date':job.service_created_datetime.strftime("%d-%m-%Y"),
                'product_category':job.product_category_id.name,
                'problem':job.service_request_id.problem,
                'user_id': self.env.user.name,
                'client_comments':job.client_comments,
                
                }
            job_lst.append(vals)
                
            
        datas = {
            'model': 'job.card.report',
            'jobs':job_lst,
            'form_data': self.read()[0],
        }
        return self.env.ref('machine_repair_management.print_job_card_preformatted_document').report_action(self, data=datas)
    
   