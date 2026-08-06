from odoo import fields, models


class PbiDashboardNote(models.Model):
    _name = 'pbi.dashboard.note'
    _description = 'PBI Sales Dashboard — imported narrative note override'

    key = fields.Char(required=True, help="Section this note belongs to: trend, region, franchise, "
                                           "customerType, product or salesman.")
    year = fields.Char(required=True, help="Matches the dashboard's Period filter value.")
    franchise = fields.Char(required=True, help="Matches the dashboard's Franchise filter value.")
    customer_type = fields.Char(required=True, default='all', help="Matches the dashboard's Customer Type filter value.")
    region = fields.Char(required=True, default='all', help="Matches the dashboard's Region filter value.")
    text = fields.Text(required=True)

    _sql_constraints = [
        ('pbi_dashboard_note_unique', 'unique(key, year, franchise, customer_type, region)',
         'Only one note override per section, period and filter combination.'),
    ]
