# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    crm_commercial_terms_header_notes = fields.Html(
        string="Terms & Conditions Header Notes",
        help="Formatted terms & conditions header notes to appear in Quotation PDF.",
    )
    crm_commercial_terms_footer_notes = fields.Html(
        string="Terms & Conditions Footer Notes",
        help="Formatted terms & conditions footer notes to appear in Quotation PDF.",
    )
    crm_commercial_quotation_intro_paragraph = fields.Html(
        string="Quotation Intro Paragraph (PDF)",
        help="Formatted introduction paragraph to appear in Quotation PDF.",
    )

    crm_commercial_inactivity_reminder_weeks = fields.Integer(
        string="Pipeline Inactivity Reminder Threshold (Weeks)",
        default=1,
        help="Number of weeks without lead status update before sending a weekly reminder to the salesman.",
    )
    crm_commercial_inactivity_lock_weeks = fields.Integer(
        string="Salesman Inactivity Lockout Threshold N (Weeks)",
        default=2,
        help="Number of weeks without any pipeline status update before locking the salesman account until reporting manager unlocks it.",
    )
    crm_commercial_order_expiry_alert_weeks = fields.Integer(
        string="Customer Order Expiry Alert Horizon X (Weeks)",
        default=2,
        help="Number of weeks before order expiry date to alert the salesman.",
    )
    # show_crm_commerical_product_category = fields.Selection(
    #     [
    #         ("yes", "Yes"),
    #         ("no", "No"),
    #     ],
    #     string="Show Product Category",
    #     default="no",
    #     config_parameter="crm_commercial.show_crm_commerical_product_category",
    # )
    show_crm_commerical_product_category = fields.Boolean(
        string="Show Product Category",
        # default=False,
        config_parameter="crm_commercial.show_crm_commerical_product_category",
    )

    crm_product_category_id = fields.Many2one(
        "product.category",
        string="Product Categories",
        domain=[
            # ("use_for_crm_commercial", "=", True),
            ("parent_id", "=", False),
        ],
        config_parameter="crm_commercial.crm_product_category_id",
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICP = self.env["ir.config_parameter"].sudo()

        res.update(
            crm_commercial_terms_header_notes=ICP.get_param(
                "crm_commercial.terms_header_notes", default=""
            ),
            crm_commercial_terms_footer_notes=ICP.get_param(
                "crm_commercial.terms_footer_notes", default=""
            ),
            crm_commercial_quotation_intro_paragraph=ICP.get_param(
                "crm_commercial.quotation_intro_paragraph", default=""
            ),
            crm_commercial_inactivity_reminder_weeks=int(
                ICP.get_param("crm_commercial.inactivity_reminder_weeks", default="1")
            ),
            crm_commercial_inactivity_lock_weeks=int(
                ICP.get_param("crm_commercial.inactivity_lock_weeks", default="2")
            ),
            crm_commercial_order_expiry_alert_weeks=int(
                ICP.get_param("crm_commercial.order_expiry_alert_weeks", default="2")
            ),
            show_crm_commerical_product_category=ICP.get_param(
                "crm_commercial.show_crm_commerical_product_category"
            ),
        ),

        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param(
            "crm_commercial.terms_header_notes",
            self.crm_commercial_terms_header_notes or "",
        )
        ICP.set_param(
            "crm_commercial.terms_footer_notes",
            self.crm_commercial_terms_footer_notes or "",
        )
        ICP.set_param(
            "crm_commercial.quotation_intro_paragraph",
            self.crm_commercial_quotation_intro_paragraph or "",
        )
        ICP.set_param(
            "crm_commercial.inactivity_reminder_weeks",
            str(self.crm_commercial_inactivity_reminder_weeks or 1),
        )
        ICP.set_param(
            "crm_commercial.inactivity_lock_weeks",
            str(self.crm_commercial_inactivity_lock_weeks or 2),
        )
        ICP.set_param(
            "crm_commercial.order_expiry_alert_weeks",
            str(self.crm_commercial_order_expiry_alert_weeks or 2),
        )
        ICP.set_param(
            "crm_commercial.show_crm_commerical_product_category",
            self.show_crm_commerical_product_category,
        )
