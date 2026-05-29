from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError

class AttendanceRequest(models.Model):
    _name = "attendance.request"
    _description = "Attendance Request"

    name = fields.Char(readonly=True)
    request_type = fields.Selection(
        [
            ("check_in", "Check In"),
            ("check_out", "Check Out"),
            ("both", "Both"),
        ],
        required=True,
    )
    check_in_datetime = fields.Datetime()
    check_out_datetime = fields.Datetime()
    reason = fields.Char(required=True)
    attendance_id = fields.Many2one("hr.attendance")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("approve", "Approve"),
            ("reject", "Reject"),
            ("cancel", "Cancel"),
        ],
        default="draft",
    )
    employee_id = fields.Many2one("hr.employee", required=True)
    is_current_user_manager = fields.Boolean(
        compute="_compute_is_current_user_manager"
    )
    approve_reject_datetime = fields.Datetime()
    cancelled_datetime = fields.Datetime()
    reject_reason = fields.Char()

    im_manager_approval = fields.Boolean()

    def _compute_is_current_user_manager(self):
        if (
            self.env.user.employee_id
            and self.employee_id.parent_id.id == self.env.user.employee_id.id
        ):
            self.is_current_user_manager = True
        else:
            self.is_current_user_manager = False

    def approve_request(self):
        if not self.im_manager_approval:
            pass
        if self.request_type == "check_in":
            self.attendance_id.check_in = self.check_in_datetime
        elif self.request_type == "check_out":
            self.attendance_id.check_out = self.check_out_datetime
        else:
            attendance = (
                self.env["hr.attendance"]
                .sudo()
                .create(
                    {
                        "check_in": self.check_in_datetime,
                        "check_out": self.check_out_datetime,
                        "employee_id": self.employee_id.id,
                        "manual": True,
                    }
                )
            )
            self.attendance_id = attendance.id
        self.state = "approve"
        self.approve_reject_datetime = fields.Datetime.now()

        title = "Attendance Request Approval: {}".format(self.name)
        body = "{} has approved your {} attendance request.".format(
            self.employee_id.parent_id.name, self.name
        )
        self.employee_id.send_email_notification(
            self.employee_id.empl_id, title, body
        )

    def reject_request(self):
        if not self.reject_reason:
            raise UserError("Please add a reason for request rejection.")
        self.state = "reject"
        self.approve_reject_datetime = fields.Datetime.now()

        title = "Attendance Request Rejection: {}".format(self.name)
        body = "{} has rejected your {} attendance request.".format(
            self.employee_id.parent_id.name, self.name
        )
        self.employee_id.send_email_notification(
            self.employee_id.empl_id, title, body
        )

    def cancel_request(self):
        self.state = "cancel"
        self.cancelled_datetime = fields.Datetime.now()

        title = "Attendance Request Cancellation: {}".format(self.name)
        body = "{} has cancelled {} attendance request.".format(
            self.employee_id.name, self.name
        )
        if self.employee_id.parent_id:
            self.employee_id.send_email_notification(
                self.employee_id.parent_id.empl_id, title, body
            )

    @api.model_create_multi
    def create(self, vals_list):
        res = super(AttendanceRequest, self).create(vals_list)
        for att_request in res:
            att_request.name = self.env["ir.sequence"].next_by_code(
                "attendance.request"
            )
            title = "New Attendance Request: {}".format(att_request.name)
            body = "{} has applied for attendance request.".format(
                att_request.employee_id.name
            )
            if att_request.employee_id.parent_id:
                att_request.employee_id.send_email_notification(
                    att_request.employee_id.parent_id.empl_id, title, body
                )
        return res
