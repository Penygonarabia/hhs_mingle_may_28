from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date

class dealerAssignment(models.Model):
    _name = 'dsales.assignment'
    _description = 'ASSIGN SALESMAN'
    _rec_name = 'name'
    _order = 'active desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # -------------------------
    # Fields
    # -------------------------
    name = fields.Char(string="Name", compute="_compute_name", store=True)

    dealer_id = fields.Many2one(
        'res.partner', string='Dealer', domain=[('dealersalesman_required', '=', True)], required=True, tracking=True
    )
    dealer_showroom_id = fields.Many2one('dsales.showroom', string='Dealer Showroom', required=True)
    sale_dealer_id = fields.Many2one('res.users', string='Salesman', required=True)

    available_sale_dealer_ids = fields.Many2many(
        'res.users',
        compute="_compute_available_sale_dealer_ids",
        string="Available Dealers"
    )

    category_id = fields.Many2one(
        'product.category',
        string="Category",
        domain="[('parent_id','=',False),('name', '!=', 'All')]",
        required=True
    )

    from_date = fields.Date(string="From Date", required=True)
    to_date = fields.Date(string="To Date")

    shift1_from = fields.Selection(selection="_get_time_selection", string="Shift 1 From")
    shift1_to = fields.Selection(selection="_get_time_selection", string="Shift 1 To")
    shift2_from = fields.Selection(selection="_get_time_selection", string="Shift 2 From")
    shift2_to = fields.Selection(selection="_get_time_selection", string="Shift 2 To")

    active = fields.Boolean(default=True)
    dealer_conflict = fields.Boolean(compute="_compute_conflict")

    user_id = fields.Many2one(
        'res.users',
        string='Mobile User'
    )

    # -------------------------
    # Compute methods
    # -------------------------
    @api.depends("sale_dealer_id")
    def _compute_name(self):
        for rec in self:
            rec.name = rec.sale_dealer_id.name if rec.sale_dealer_id else ''

    @api.depends('sale_dealer_id')
    def _compute_available_sale_dealer_ids(self):
        group = self.env.ref('dealer.group_dealer_user', raise_if_not_found=False)
        dealers = self.env['res.users'].search([('groups_id', 'in', group.id)]) if group else self.env['res.users'].search([])
        for rec in self:
            rec.available_sale_dealer_ids = dealers

    @api.depends('sale_dealer_id', 'from_date', 'to_date')
    def _compute_conflict(self):
        for rec in self:
            rec.dealer_conflict = False
            if rec.sale_dealer_id and rec.from_date and rec.to_date:
                domain = [
                    ('sale_dealer_id', '=', rec.sale_dealer_id.id),
                    ('from_date', '<=', rec.to_date),
                    ('to_date', '>=', rec.from_date),
                    ('active', '=', True),
                ]
                if rec.id:
                    domain.append(('id', '!=', rec.id))
                overlapping = self.search(domain)
                if overlapping:
                    rec.dealer_conflict = True

    @api.model
    def _get_time_selection(self):
        times = []
        for hour in range(0, 24):
            for minute in (0, 30):
                time_str = f"{hour:02}:{minute:02}"
                times.append((time_str, time_str))
        return times

    # -------------------------
    # Constraints
    # -------------------------
    @api.constrains('from_date')
    def _check_from_date_future(self):
        today = date.today()
        for rec in self:
            if rec.from_date and rec.from_date < today:
                raise ValidationError("From Date must be today or a future date.")

    @api.constrains('from_date', 'to_date')
    def _check_date_range(self):
        for rec in self:
            if rec.from_date and rec.to_date and rec.from_date > rec.to_date:
                raise ValidationError("From Date must be earlier than To Date.")

    @api.constrains('shift1_from', 'shift1_to', 'shift2_from', 'shift2_to')
    def _check_shift_order(self):
        def to_minutes(t):
            if t:
                h, m = map(int, t.split(':'))
                return h * 60 + m
            return None

        for rec in self:
            s1f, s1t = to_minutes(rec.shift1_from), to_minutes(rec.shift1_to)
            s2f, s2t = to_minutes(rec.shift2_from), to_minutes(rec.shift2_to)

            if s1f is None or s1t is None:
                raise ValidationError("Shift 1 'From' and 'To' are required.")
            if s1t <= s1f:
                raise ValidationError("Shift 1 'To' must be after 'From'.")
            if s2f and s2t:
                if s2t <= s2f:
                    raise ValidationError("Shift 2 'To' must be after 'From'.")
                if s2f < s1t:
                    raise ValidationError("Shift 2 must start after Shift 1 ends.")
            elif s2t and not s2f:
                raise ValidationError("Shift 2 'From' is required if 'To' is provided.")

    # -------------------------
    # Helper methods
    # -------------------------
    def _deactivate_previous_assignments(self):
        """Ensure one dealer per showroom and one showroom per dealer"""
        for rec in self:
            if not rec.active:
                continue

            # Deactivate other active assignments of the same dealer
            dealer_others = self.search([
                ('sale_dealer_id', '=', rec.sale_dealer_id.id),
                ('id', '!=', rec.id),
                ('active', '=', True),
            ])
            if dealer_others:
                dealer_others.write({'active': False})

            # Deactivate other active assignments of the same showroom
            showroom_others = self.search([
                ('dealer_showroom_id', '=', rec.dealer_showroom_id.id),
                ('id', '!=', rec.id),
                ('active', '=', True),
            ])
            if showroom_others:
                showroom_others.write({'active': False})



    def _update_showroom_dealer_info(self):
        for rec in self:
            if rec.dealer_showroom_id:
                rec.dealer_showroom_id.write({
                    'sale_dealer_id': rec.sale_dealer_id.id,
                    'from_date': rec.from_date,
                    'to_date': rec.to_date,
                    'shift1_from': rec.shift1_from,
                    'shift1_to': rec.shift1_to,
                    'shift2_from': rec.shift2_from,
                    'shift2_to': rec.shift2_to,
                    'user_id': rec.sale_dealer_id.id,
                })

    def _update_user_current_assignment(self):
        for rec in self:
            if rec.active and rec.sale_dealer_id:
                rec.sale_dealer_id.write({
                    'dealer_id': rec.dealer_id.id,
                    'dealer_showroom_id': rec.dealer_showroom_id.id,
                })

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        rec._deactivate_previous_assignments()
        rec._update_showroom_dealer_info()
        rec._update_user_current_assignment()
        return rec

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            rec._deactivate_previous_assignments()
            rec._update_showroom_dealer_info()
            rec._update_user_current_assignment()
        return res
