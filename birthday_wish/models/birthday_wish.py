from odoo import api, fields, models, _
from datetime import date,time,datetime
import base64
import os
import logging

_logger = logging.getLogger(__name__)
class BirthdayWish(models.Model):
    
    _inherit = "hr.employee"
    
    
    # @api.model
    # def _birthday_wish_cron_job(self):
    #     """Send birthday wishes to employees with embedded image"""
    #     try:
    #         # Find employees with birthdays today (active only)
    #         today = fields.Date.today()
    #         employees = self.search([
    #             ('birthday', '!=', False),
    #             ('active', '=', True),
    #             ('work_email', '!=', False)
    #         ])
    #
    #         # Get the image file
    #         module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    #         image_path = os.path.join(module_path, 'static', 'src', 'img', 'Birthday_4.jpg')
    #
    #         if not os.path.exists(image_path):
    #             raise FileNotFoundError(f"Birthday image not found at {image_path}")
    #
    #         # Read and encode image
    #         with open(image_path, "rb") as img_file:
    #             encoded_image = base64.b64encode(img_file.read()).decode('utf-8')
    #
    #         # Get email template
    #         template = self.env.ref('birthday_wish.employee_birthday_wish_mail', raise_if_not_found=False)
    #         if not template:
    #             raise ValueError("Email template not found")
    #
    #         # Process each employee
    #         for emp in employees:
    #             if emp.birthday.month == today.month and emp.birthday.day == today.day:
    #                 # Create attachment
    #                 attachment = self.env['ir.attachment'].create({
    #                     'name': f"birthday_wish_{emp.name}.jpg",
    #                     'type': 'binary',
    #                     'datas': encoded_image,
    #                     'mimetype': 'image/jpeg',
    #                     'res_model': 'mail.template',
    #                     'res_id': template.id
    #                 })
    #
    #                 # Send email with both context and attachment
    #                 template.with_context({
    #                     'birthday_image': encoded_image,
    #                     'employee_name': emp.name
    #                 }).send_mail(
    #                     emp.id,
    #                     force_send=True,
    #                     email_values={'attachment_ids': [(4, attachment.id)]}
    #                 )
    #
    #                 _logger.info(f"Birthday email sent to {emp.name} ({emp.work_email})")
    #
    #     except Exception as e:
    #         _logger.error(f"Failed to send birthday wishes: {str(e)}", exc_info=True)
    #

    @api.model
    def _birthday_wish_cron_job(self):
        
        module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        image_path = os.path.join(module_path, 'static', 'src', 'img', 'Birthday_4.jpg')        
        image_data = None
        
        with open(image_path, 'rb') as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
       
        # <img src="data:image/jpeg;base64,{image_data}" alt="Happy Birthday" 
        #                 style="max-width: 300px; border-radius: 8px;"/>    
        
        '''https://email2go.io/projects'''  
        img_tag = f'<img src="https://cloud1.email2go.io/7b4436d7d402f3a6b9a11d6ca58c4057/e6e56925c04bcc464195e5abc1b33c51291c9d6960728b737050cfdbb8a2ce5a.jpg" style="max-width: 300px; border-radius: 8px;"/>'
        employee_search = self.env['hr.employee'].search([
            ('birthday', '!=', False),
            ('state', '=', 'draft'),
            ('work_email', '!=', False)
        ])
        today = fields.Date.today()

        for employee in employee_search:
            if employee.birthday.strftime("%d-%m") == today.strftime("%d-%m"):
                subject = f"Happy Birthday - {employee.name}"
                body_html = f"""
                <p><b style="color:#0000FF;font-size:20px">Happy Birthday Dear {employee.name}</b>,</p>
                <p style="color:#0000FF;font-size:20px">
                    Your dedication to creating a positive work environment is truly appreciated...
                </p>
                <div style="text-align: center; margin: 20px 0;">
                   {img_tag}
                </div>
                 <b style="color:#0000FF;font-size:20px">Best Regards</b><br>
                <b style="color:#0000FF;font-size:20px">Human Resource Dept</b><br>
                <b style="color:#0000FF;font-size:20px">HH-Shaker</b>
                """
              
                mail = self.env['mail.mail'].sudo().create({
                        'subject': subject,
                        'email_to': employee.work_email,
                        'email_from': self.env.user.email,
                        'body_html': body_html,
                   
                       
                    })
               
                mail.send()
               
    # @api.model
    # def _birthday_wish_cron_job(self):
    #
    #     employee_search = self.env['hr.employee'].search([
    #         ('birthday','!=', False),('state','=','draft'),('work_email', '!=', False)
    #         ])
    #     today = fields.Date.today()
    #
    #     image_path = os.path.join(os.path.dirname(__file__), 'static/src/img/Birthday_4.jpg')
    #     # image_path = '/birthday_wish/static/src/img/Birthday_4.jpg'
    #     with open(image_path, 'rb') as image_file:
    #         image_data = base64.b64encode(image_file.read()).decode('utf-8')
    #
    #     for employee in employee_search:
    #         if employee.birthday.strftime("%d-%m") == today.strftime("%d-%m"):
    #             subject = f"Happy Birthday - {employee.name}"
    #             body_html = f"""
    #             <p><b style="color:#0000FF">Happy Birthday Dear <t t-out="object.name"></t></b>,</p>
    #                  <p style="color:#0000FF">
    #                 Your dedication to creating a positive work environment is truly appreciated...
    #                 </p>
    #                 <div style="text-align: center; margin: 20px 0;">
    #                     <img src="cid:birthday_image" 
    #                          alt="Happy Birthday" 
    #                          style="max-width: 100%; border-radius: 8px;"/>
    #                     </div>
    #
    #                 <b style="color:#0000FF">Best Regards</b><br>
    #                 <b style="color:#0000FF">Human Resource Dept</b><br>
    #                  <b style="color:#0000FF">HH-Shaker</b>    
    #                 """
    #             self.env['mail.mail'].create({
    #
    #                 'subject':subject,
    #                 'email_to':employee.work_email,
    #                 'email_from':self.env.user.email,
    #                 'body_html':body_html,
    #                  'attachment_ids': [(0, 0, {
    #                     'name': 'Birthday_4.jpg',
    #                     'datas': image_data,
    #                     'type': 'binary',
    #                     'res_id': 0,
    #                     'mimetype': 'image/jpeg',
    #                     'cid': 'birthday_image'
    #                 })]
    #
    #                 }).send() 
    #
    #             # self.env.ref('birthday_wish.employee_birthday_wish_mail').send_mail(employee.id,force_send = True)
    #             return {
    #                 'effect':
    #                  {
    #                     'fadeout' : 'slow',
    #                      'message' :  'Your Mail is send Successfully',
    #                      'type' : 'rainbow_man',
    #
    #                     }
    #
    #                 }
    #


            
            
        