from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64
import qrcode
from io import BytesIO
from num2words import num2words


def generate_qr_code(value):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=20,
        border=4,
    )
    qr.add_data(value)
    qr.make(fit=True)
    img = qr.make_image()
    stream = BytesIO()
    img.save(stream, format="PNG")
    qr_img = base64.b64encode(stream.getvalue())
    return qr_img

class AccountMove(models.Model):
    
    _inherit = "account.move"
    
    
    '''Code Added on May 22 2026 by Vijaya Bhaskar'''
    customer_code = fields.Char(string = "Customer Code")
    
    warehouse_id = fields.Many2one('stock.warehouse',string = "Warehouse")
    
    work_center_id = fields.Many2one('work.center.location', string = "Work center")
    
    work_center_group_id = fields.Many2one('work.center.group', string = "Work Center  Group")
    
    '''Code Added on May 26 2026 by Vijaya Bhaskar '''
    
    sales_person_user_id = fields.Many2one('res.users', string  = "SalesPerson")
    
    
    qr_image = fields.Binary(string="QR Code", compute="_generate_qr_code")

    invoice_no = fields.Char("Invoice No")

    inv_pvs_xmlhas = fields.Char(string="Invoice Previous XML Has")
    inv_xmlhas = fields.Char(string="Invoice XMl Has")
    inv_qrcode_has = fields.Char(string="Invoice QR Code Has")
    
    '''code Added on Jun 02 2026 by Vijaya Bhaskar'''
    invoice_txt = fields.Text(string = "Invoice Text")
    
    '''Code Added on June 25 2026 by Vijaya Bhaskar'''
    partner_name = fields.Char(string = "Company Name")
    
    '''Code Added on July 28 2026 by Vijaya Bhaskar''' 
    street = fields.Char(string = "Street")
    
    street2 = fields.Char(string = "Street2")
    
    customer_city_id = fields.Many2one('res.city', string = "Customer City")
    
    district_id  = fields.Many2one('res.state.district',string = "District")
    
    state_id = fields.Many2one('res.country.state', string = "State")
    
    country_id = fields.Many2one('res.country', string = "Country")
    
    zip = fields.Char(string = "Zip")
    
    customer_name = fields.Char('Customer')
    

    def _generate_qr_code(self):
        for record in self:
            qr_value = (
                f"Previous XML Hash: {record.inv_pvs_xmlhas or ''}\n"
                f"XML Hash: {record.inv_xmlhas or ''}\n"
                f"QR Code Hash: {record.inv_qrcode_has or ''}"
            )

            qr_img = generate_qr_code(record.inv_qrcode_has)
            record.qr_image = qr_img

        return True

    
