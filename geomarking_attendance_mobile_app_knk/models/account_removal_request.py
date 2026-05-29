from odoo import fields, models, api


class AccountRemovalRequest(models.Model):
    _name = "account.removal.request"
    _description = "Account Removal Request"

    name = fields.Char(default="New", readonly=True, required=True)
    employee_id = fields.Many2one("hr.employee", required=True)
    empl_id = fields.Char()
    reason_id = fields.Many2one("removal.request.reason", required=True)
    request_approval_date = fields.Datetime()
    request_submission_date = fields.Datetime()
    request_reject_date = fields.Datetime()
    state = fields.Selection(
        [("draft", "Draft"), ("approve", "Approved"), ("reject", "Rejected")],
        default="draft",
    )
    description = fields.Char()
    note = fields.Char()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["name"] = (
                self.env["ir.sequence"].next_by_code("account.removal.request")
                or "New"
            )

        return super(AccountRemovalRequest, self).create(vals_list)

    def approve_request(self):
        self.employee_id.empl_id = False
        self.request_approval_date = fields.Datetime.now()
        self.state = "approve"

    def reject_request(self):
        self.employee_id.empl_id = False
        self.request_reject_date = fields.Datetime.now()
        self.state = "reject"
