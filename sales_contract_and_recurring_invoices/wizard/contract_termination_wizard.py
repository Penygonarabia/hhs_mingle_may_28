from odoo import api,fields,models, _
from odoo.exceptions import ValidationError

class ContractTerminationWizard(models.TransientModel):
    
    _name = "contract.termination.wizard"
    
    _description = "Contract Termination Wizard"
    
    
    contract_id = fields.Many2one('subscription.contracts',string = "Contract")
    
    termination_reason = fields.Text('Reason for Termination')
    
    
    def action_confirm_wizard(self):
        
        self.ensure_one()
        
        
        self.contract_id.write({
            
            'state':'terminate',
            'termination_date' : fields.Date.today(),
            'termination_reason': self.termination_reason
            
            })
        
        body_html =  f"""
            
             <p style="color:#0000FF;font-size:20px">Dear </p>
             <p style="color:#0000FF;font-size:20px">
                Please note that Contract No.{self.contract_id.name} is terminated
             </p>
             <p>
             Contract Details are:
             </p>
              <table style="border-collapse:collapse;width:100%;" border="1" cellpadding="6" cellspacing="0">
                    <tr>
                        <th style="border:1px solid #000;background:#e6e6e6;">Description</th>
                        <th style="border:1px solid #000;background:#e6e6e6;">Value</th>
                    </tr>
                
                    <tr>
                        <td style="border:1px solid #000;">Contract No.</td>
                        <td style="border:1px solid #000;">{self.contract_id.name or ''}</td>
                    </tr>
                
                    <tr>
                        <td style="border:1px solid #000;">Start Date</td>
                        <td style="border:1px solid #000;">{self.contract_id.date_start.strftime('%d-%m-%Y') if self.contract_id.date_start else ''}</td>
                    </tr>
                
                    <tr>
                        <td style="border:1px solid #000;">End Date</td>
                        <td style="border:1px solid #000;">{self.contract_id.date_end.strftime('%d-%m-%Y') if self.contract_id.date_end else ''}</td>
                    </tr>
                
                    <tr>
                        <td style="border:1px solid #000;">Project Name</td>
                        <td style="border:1px solid #000;">{self.contract_id.reference or ''}</td>
                    </tr>
                
                    <tr>
                        <td style="border:1px solid #000;">Contract Period</td>
                        <td style="border:1px solid #000;">{self.contract_id.recurring_period or ''}</td>
                    </tr>
                
                    <tr>
                        <td style="border:1px solid #000;">Contract Interval</td>
                        <td style="border:1px solid #000;">{self.contract_id.recurring_period_interval or ''}</td>
                    </tr>
                
                    <tr>
                        <td style="border:1px solid #000;">Termination Reason</td>
                        <td style="border:1px solid #000;">{self.termination_reason or ''}</td>
                    </tr>
                
                    <tr>
                        <td style="border:1px solid #000;">Termination Date</td>
                        <td style="border:1px solid #000;">{fields.Date.today().strftime('%d-%m-%Y')}</td>
                    </tr>
                </table>
                         
             <br/><br/>
             
            <b style="color:#0000FF;font-size:20px">Best Regards</b><br/>
            <b style="color:#0000FF;font-size:20px">Maintenance Dept</b><br/>
            <b style="color:#0000FF;font-size:20px">HH-Shaker</b>
        
        
        
        """
        
        self.env['mail.mail'].create({
            
            'email_from': self.env.user.email,
            'email_to' : self.contract_id.amc_quotation_id.email_from or '',
            'subject' : f"Contract Termination - {self.contract_id.name}",
            'body_html': body_html,
            
            }).send()
        
                
        return {"type": "ir.actions.act_window_close"}