from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class TechnicianPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'jobcard_count' in counters:
            # Show all job cards for admin, assigned ones for technicians
            if request.env.user.has_group('base.group_system'):
                values['jobcard_count'] = request.env['jobcard'].search_count([])
            else:
                values['jobcard_count'] = request.env['jobcard'].search_count([
                    ('technician_id', '=', request.env.user.id)
                ])
        return values


class JobCardPortal(http.Controller):

    def _get_jobcard_domain(self):
        """Returns domain based on user permissions"""
        if request.env.user.has_group('base.group_system'):
            return []  # Admin sees all
        return [('technician_id', '=', request.env.user.id)]

    @http.route(['/my/jobcards', '/my/jobcards/page/<int:page>'],
                type='http', auth="user", website=True)
    def portal_technician_jobcards(self, page=1, sortby=None, view_type='list', **kw):
        """
        Unified view handler for both list and kanban views
        """
        print("Controller invoked")
        JobCard = request.env['jobcard']
        domain = self._get_jobcard_domain()

        # Sorting options
        sortings = {
            'date': 'service_created_datetime desc',
            'name': 'name',
            'customer': 'partner_id',
        }
        order = sortings.get(sortby, 'service_created_datetime desc')

        # Get job cards
        jobcards = JobCard.search(domain, order=order)

        # Pager for list view only
        pager = None
        if view_type == 'list':
            pager = request.website.pager(
                url='/my/jobcards',
                total=len(jobcards),
                page=page,
                step=20
            )
            jobcards = jobcards[pager['offset']:pager['offset'] + pager['step']]

        values = {
            'jobcards': jobcards,
            'pager': pager,
            'default_url': '/my/jobcards',
            'sortby': sortby,
            'view_type': view_type,
            'page': page,
        }

        template = "machine_repair_management.portal_technician_jobcards_kanban" \
            if view_type == 'kanban' else "machine_repair_management.portal_technician_jobcards"

        return request.render(template, values)

    @http.route('/my/jobcard/<int:jobcard_id>', type='http', auth="user", website=True)
    def portal_technician_jobcard_detail(self, jobcard_id, **kw):
        jobcard = request.env['jobcard'].browse(jobcard_id)
        # Check access rights
        if not request.env.user.has_group('base.group_system') and \
                jobcard.technician_id != request.env.user:
            return request.redirect('/my/home')

        return request.render("machine_repair_management.portal_technician_jobcard_page", {
            'jobcard': jobcard,
        })