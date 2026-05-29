# -*- coding: utf-8 -*-
from odoo import models, fields, tools

class VIDBProductTask(models.Model):
    _name = 'db.product.task'
    _description = 'VI Product Task'
    _auto = False  # View-backed model

    Work_Location_ID = fields.Integer()
    Work_Location = fields.Char()
    Technician_ID = fields.Integer()    
    Technician = fields.Char()
    Job_Status = fields.Char()
    Warranty_Status = fields.Char()
    CIC_Ref_No = fields.Char()
    Parts_Warranty_Cost = fields.Float()
    Service_Charge = fields.Float()
    Parts_Charge = fields.Float()
    Job_Created_Datetime = fields.Date()

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
            SELECT 
                pt.work_center_id AS Work_Location_ID,
                (reg.name::json)->>'en_US' AS Work_Location,
                pt.technician_id AS Technician_ID,
                par.name AS Technician,
                pt.job_card_state AS Job_Status,
                CASE WHEN pt.warranty = true THEN 'Under Warranty' ELSE 'Not Under Warranty' END AS Warranty_Status,
                pt.control_card_no AS CIC_Ref_No,
                pt.service_warranty_amount AS Parts_Warranty_Cost,
                pt.service_grand_total_amount AS Service_Charge,
                pt.parts_total_amount AS Parts_Charge,
                pt.service_created_datetime AS Job_Created_Datetime
            FROM 
                project_task AS pt
            LEFT OUTER JOIN res_region AS reg ON reg.id = pt.work_center_id
            LEFT OUTER JOIN res_users usr ON usr.id = pt.technician_id
            LEFT OUTER JOIN res_partner par ON par.id = usr.partner_id
            );
        """)

