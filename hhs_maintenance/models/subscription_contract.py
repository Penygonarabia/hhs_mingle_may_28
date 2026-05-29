from odoo import api, fields, models, _
from odoo.tools import date_utils
from odoo.tools.safe_eval import datetime
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, time, date
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)

class SubscriptionContracts(models.Model):
    """ Model for subscription contracts """
    _inherit = 'subscription.contracts'

    contract_reference_id=fields.Many2one('maintenance.equipment', string="Contract Reference")

