# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SupportTeam(models.Model):
    _name = 'machine.support.team'
    _rec_name = 'leader_id'
    _description = 'Support Team'

    name = fields.Char(
        string='Name',
        required=True, ondelete="cascade"
    )
    team_ids = fields.Many2many(
        'res.users',
        string='Team Members', ondelete="cascade"
    )
    is_team = fields.Boolean(
        'Is Default Team?',
        help='Tick this box to set this team as default support team when request come from website',
    )
    leader_id = fields.Many2one(
        'res.users',
        string='Leader',
        required=True, ondelete="cascade"
    )
    service_type_id = fields.Many2one('service.nature', string='Service Type', ondelete="cascade")
    work_center_id = fields.Many2one('work.center.location', string="Work Center", required=True)
    location_id = fields.Many2one('hr.work.location', string="Location")
    support_team_line_ids = fields.One2many('machine.support.team.line', 'support_team_id', string="Team Members")

    # team_member_names = fields.Text(string="Team Member Names", readonly=True)
    # team_member_ids = fields.Many2many(
    #     'res.users',
    #     'machine_support_team_member_rel',  # <-- custom relation table name
    #     'support_team_id', 'user_id',
    #     string="Selected Members",
    #     readonly=True,
    #     store=True
    # )
    #
    # @api.onchange('team_ids')
    # def _onchange_team_ids(self):
    #     self.team_member_ids = self.team_ids

    team_member_ids = fields.Many2many(
        'res.users',
        'machine_support_team_member_rel',  # custom table
        'support_team_id', 'user_id',
        string="Selected Members",
        compute='_compute_team_member_ids',
        store=True
    )

    project_ids = fields.Many2many(
        'project.project',
        string='Project',
        compute="_compute_res_user_allowed_project",
        store=True
    )

    @api.depends("leader_id")
    def _compute_res_user_allowed_project(self):
        for rec in self:
            if rec.leader_id and rec.leader_id.project_ids:
                rec.project_ids = rec.leader_id.project_ids
            else:
                rec.project_ids = False

    @api.depends('team_ids')
    def _compute_team_member_ids(self):
        for rec in self:
            rec.team_member_ids = rec.team_ids

    @api.constrains('support_team_line_ids')
    def _check_team_members(self):
        for rec in self:
            if not rec.support_team_line_ids:
                raise ValidationError("Please enter at-least one member to the team")
            if not any(line.is_default_team_member for line in rec.support_team_line_ids):
                raise ValidationError("Please tick at-least one default member in the team")

    @api.onchange('leader_id')
    def _onchange_leader_id(self):
        for rec in self:
            if rec.leader_id:
                val_lst = []
                vals = {
                    'support_team_user_id': rec.leader_id.id,
                    'is_default_team_member': True,

                }
                val_lst.append((0, 0, vals))
                rec.support_team_line_ids = val_lst

    @api.model
    @api.returns('self', lambda value: value.id if value else False)
    def _get_default_team_id(self, user_id=None):
        if not user_id:
            user_id = self.env.uid
        team_id = None
        if 'default_team_id' in self.env.context:
            team_id = self.browse(self.env.context.get('default_team_id'))
        if not team_id or not team_id.exists():
            team_id = self.sudo().search(
                ['|', ('leader_id', '=', user_id), ('team_ids', '=', user_id)],
                limit=1)
        #         if not team_id:
        #             default_team_id = self.env.ref('website_helpdesk_support_ticket.team_support_department', raise_if_not_found=False)
        #             if default_team_id and (self.env.context.get('default_type') != 'lead' or default_team_id.use_leads):
        #                 team_id = default_team_id
        return team_id

    @api.constrains('leader_id', 'service_type_id', 'location_id')
    def _validity_check_constrains(self):
        for rec in self:
            team_search = self.env['machine.support.team'].search([
                ('leader_id', '=', rec.leader_id.id),
                ('service_type_id', '=', rec.service_type_id.id),
                ('location_id', '=', rec.location_id.id),
                ('id', '!=', rec.id)
            ])

            if len(team_search) > 1:
                raise ValidationError('Already team leader,location, service type is there. please Change another team')


class MachineSupportTeamLine(models.Model):
    _name = "machine.support.team.line"

    support_team_id = fields.Many2one('machine.support.team', string="Support Team")
    support_team_user_id = fields.Many2one('res.users', string="Team Users")
    is_default_team_member = fields.Boolean(string=" Default Team Member ", default=False)

    @api.constrains('support_team_id', 'support_team_user_id')
    def _check_team_member_user(self):
        for rec in self:
            team_search = self.env['machine.support.team.line'].search(
                [('support_team_id', '=', rec.support_team_id.id),

                 ('support_team_user_id', '=', rec.support_team_user_id.id), ('id', '!=', rec.id)])

            if team_search:
                raise ValidationError(
                    "Same team member is not repeated in a single team.Please select different team member")

            if rec.is_default_team_member:
                default_team_member_search = self.env['machine.support.team.line'].search([
                    ('support_team_id', '=', rec.support_team_id.id),
                    ('is_default_team_member', '=', True),
                    ('id', '!=', rec.id)])

                if default_team_member_search:
                    raise ValidationError("Only one Default Member to be set in each team")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: