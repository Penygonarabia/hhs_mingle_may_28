# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from datetime import timedelta

class CrmCommercialCron(models.Model):
    _name = 'crm.commercial.cron'
    _description = 'CRM Commercial Cron Automation'

    @api.model
    def cron_weekly_salesman_reminder(self):
        """Weekly cron job:
        (a) Remind salesman if there are open pipeline leads with no status updates.
        (b) Lock salesman account if no updates in the last N weeks until manager unlocks it.
        (c) Alert salesman of customer orders expiring in the next X weeks.
        """
        today = fields.Date.context_today(self)
        ICP = self.env['ir.config_parameter'].sudo()

        reminder_weeks = int(ICP.get_param('crm_commercial.inactivity_reminder_weeks', '1'))
        lock_weeks = int(ICP.get_param('crm_commercial.inactivity_lock_weeks', '2'))
        expiry_alert_weeks = int(ICP.get_param('crm_commercial.order_expiry_alert_weeks', '2'))

        reminder_limit_dt = fields.Datetime.now() - timedelta(weeks=reminder_weeks)
        lock_limit_dt = fields.Datetime.now() - timedelta(weeks=lock_weeks)
        expiry_limit_date = today + timedelta(weeks=expiry_alert_weeks)

        base_url = ICP.get_param('web.base.url', '')
        default_from = self.env.company.email or self.env.user.email or 'notifications@hh-shaker.com.sa'

        # Include all active CRM Commercial salesmen
        salesmen = self.env['res.users'].search([
            ('is_crm_commercial_user', '=', True),
            ('active', '=', True)
        ])

        for salesman in salesmen:
            salesman_email = salesman.email or (salesman.partner_id and salesman.partner_id.email)

            # (a) Open pipeline leads assigned to this salesman
            open_leads = self.env['crm.commercial.lead'].search([
                ('assigned_id', '=', salesman.id),
                ('state', 'in', ('draft', 'approved'))
            ], order='write_date asc')

            # Leads with no status update in the last reminder_weeks
            stale_leads = open_leads.filtered(lambda l: l.write_date < reminder_limit_dt)

            # (b) Inactivity lockout check: no updates on open leads for N weeks
            is_newly_locked = False
            if open_leads and all(l.write_date < lock_limit_dt for l in open_leads):
                salesman.write({
                    'active': False,
                    'is_locked_by_cron': True,
                    'locked_date': fields.Datetime.now(),
                    'lock_reason': _('No pipeline status update recorded for %s weeks.') % lock_weeks,
                })
                is_newly_locked = True

                # Notify salesman's reporting manager by email (Bilingual & Mobile Responsive)
                manager = salesman.reporting_manager_id
                manager_email = manager.email or (manager.partner_id and manager.partner_id.email) if manager else False
                if manager_email:
                    mgr_subject = f"Commercial CRM Alert: Salesman {salesman.name} Locked Due to Inactivity / تنبيه قفل حساب المندوب"
                    user_url = f"{base_url}/web#id={salesman.id}&model=res.users&view_type=form"

                    lead_rows_html = ""
                    for lead in open_leads:
                        lead_url = f"{base_url}/web#id={lead.id}&model=crm.commercial.lead&view_type=form"
                        st_en = dict(lead._fields['state'].selection).get(lead.state, lead.state)
                        st_ar = {'draft': 'مسودة', 'approved': 'معتمد', 'cancel': 'ملغي'}.get(lead.state, st_en)
                        lead_rows_html += f"""
                            <tr>
                                <td style="border: 1px solid #dee2e6; padding: 10px 8px; font-weight: bold;"><a href="{lead_url}" style="color: #0d6efd; text-decoration: none;">{lead.lead_no}</a></td>
                                <td style="border: 1px solid #dee2e6; padding: 10px 8px;">{lead.name}</td>
                                <td style="border: 1px solid #dee2e6; padding: 10px 8px;">{lead.customer_type_id.name or ''}</td>
                                <td style="border: 1px solid #dee2e6; padding: 10px 8px;"><span style="background-color: #e9ecef; padding: 3px 8px; border-radius: 4px; font-size: 12px;">{st_en} / {st_ar}</span></td>
                                <td style="border: 1px solid #dee2e6; padding: 10px 8px; white-space: nowrap;">{lead.write_date.strftime('%Y-%m-%d %H:%M')}</td>
                            </tr>
                        """

                    mgr_body = f"""<!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8"/>
                        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
                    </head>
                    <body style="margin: 0; padding: 15px 10px; background-color: #f4f6f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #212529;">
                        <div style="max-width: 650px; width: 100%; margin: 0 auto; background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                            <div style="background-color: #dc3545; color: #ffffff; padding: 16px 20px;">
                                <h2 style="margin: 0; font-size: 18px; line-height: 1.3;">⚠️ Salesman Account Locked Due to Inactivity</h2>
                                <div style="font-size: 14px; margin-top: 4px; opacity: 0.95;" dir="rtl">تنبيه: تم قفل حساب المندوب بسبب عدم النشاط</div>
                            </div>
                            <div style="padding: 20px;">
                                <p style="margin: 0 0 12px 0; font-size: 15px;">Dear <b>{manager.name}</b> / مرحباً <b>{manager.name}</b>,</p>
                                <p style="margin: 0 0 15px 0; font-size: 14px; line-height: 1.5;">
                                    Salesman <b>{salesman.name}</b> has been locked because no pipeline status updates were recorded for <b>{lock_weeks} weeks</b>.
                                    <br/>
                                    <span dir="rtl" style="display: block; color: #495057; margin-top: 4px;">
                                        تم قفل حساب المندوب <b>{salesman.name}</b> تلقائياً لعدم تسجيل أي تحديثات على الفرص البيعية لمدة <b>{lock_weeks} أسابيع</b>.
                                    </span>
                                </p>
                                
                                <div style="background-color: #fff3cd; color: #664d03; border: 1px solid #ffe69c; border-radius: 6px; padding: 12px 15px; margin-bottom: 20px; font-size: 13px;">
                                    <b>Inactive Leads ({len(open_leads)}) / الفرص البيعية المعلقة:</b>
                                </div>

                                <div style="overflow-x: auto; -webkit-overflow-scrolling: touch; margin-bottom: 20px;">
                                    <table style="width: 100%; min-width: 500px; border-collapse: collapse; font-size: 13px;">
                                        <thead>
                                            <tr style="background-color: #f8f9fa; text-align: left;">
                                                <th style="border: 1px solid #dee2e6; padding: 8px;">Lead No<br/><span style="font-weight:normal; font-size:11px;">رقم الفرصة</span></th>
                                                <th style="border: 1px solid #dee2e6; padding: 8px;">Project / Name<br/><span style="font-weight:normal; font-size:11px;">اسم المشروع</span></th>
                                                <th style="border: 1px solid #dee2e6; padding: 8px;">Customer Type<br/><span style="font-weight:normal; font-size:11px;">نوع العميل</span></th>
                                                <th style="border: 1px solid #dee2e6; padding: 8px;">Status<br/><span style="font-weight:normal; font-size:11px;">الحالة</span></th>
                                                <th style="border: 1px solid #dee2e6; padding: 8px;">Last Updated<br/><span style="font-weight:normal; font-size:11px;">آخر تحديث</span></th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {lead_rows_html}
                                        </tbody>
                                    </table>
                                </div>

                                <div style="margin-top: 25px; padding-top: 15px; border-top: 1px solid #dee2e6; text-align: center;">
                                    <p style="font-size: 14px; margin-bottom: 12px; color: #495057;">
                                        <b>Action Required / الإجراء المطلوب:</b> Review the pipeline and unlock the account if approved.
                                    </p>
                                    <a href="{user_url}" style="display: inline-block; min-height: 44px; line-height: 22px; padding: 12px 24px; background-color: #198754; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 15px; text-align: center; box-sizing: border-box;">
                                        Review &amp; Unlock User Account<br/>
                                        <span style="font-size: 13px; font-weight: normal;" dir="rtl">مراجعة وإلغاء قفل حساب المستخدم</span>
                                    </a>
                                </div>

                                <p style="color: #6c757d; font-size: 12px; margin-top: 25px; border-top: 1px solid #f0f0f0; padding-top: 10px; text-align: center;">
                                    Commercial CRM System Automated Notification &bull; نظام إدارة علاقات العملاء التجارية
                                </p>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                    self.env['mail.mail'].sudo().create({
                        'subject': mgr_subject,
                        'body_html': mgr_body,
                        'email_to': manager_email,
                        'email_from': default_from,
                    }).send()

            # (c) Expiring Customer Orders (Projects) in next X weeks
            expiring_orders = self.env['crm.commercial.sale.order'].search([
                ('assigned_id', '=', salesman.id),
                ('state', 'in', ('confirmed', 'partially_delivered')),
                ('expiry_date', '>=', today),
                ('expiry_date', '<=', expiry_limit_date)
            ], order='expiry_date asc')

            # Send Email Digest to Salesman if there is any action required
            if (stale_leads or expiring_orders or is_newly_locked) and salesman_email:
                subject = _("Commercial CRM Weekly Action Digest / الملخص الأسبوعي للفرص وانتهاء الطلبات")
                status_dict_en = dict(self.env['crm.commercial.sale.order']._fields['state'].selection)
                status_dict_ar = {
                    'confirmed': 'مؤكد',
                    'partially_delivered': 'تم التوصيل جزئياً',
                    'delivered': 'تم التوصيل',
                    'cancelled': 'ملغي',
                    'draft': 'مسودة',
                }

                stale_leads_html = ""
                if stale_leads:
                    for lead in stale_leads:
                        lead_url = f"{base_url}/web#id={lead.id}&model=crm.commercial.lead&view_type=form"
                        st_en = dict(lead._fields['state'].selection).get(lead.state, lead.state)
                        st_ar = {'draft': 'مسودة', 'approved': 'معتمد', 'cancel': 'ملغي'}.get(lead.state, st_en)
                        stale_leads_html += f"""
                            <tr>
                                <td style="border: 1px solid #dee2e6; padding: 10px 8px; font-weight: bold;"><a href="{lead_url}" style="color: #0d6efd; text-decoration: none;">{lead.lead_no}</a></td>
                                <td style="border: 1px solid #dee2e6; padding: 10px 8px;">{lead.name}</td>
                                <td style="border: 1px solid #dee2e6; padding: 10px 8px;">{lead.customer_type_id.name or ''}</td>
                                <td style="border: 1px solid #dee2e6; padding: 10px 8px;"><span style="background-color: #e9ecef; padding: 3px 8px; border-radius: 4px; font-size: 12px;">{st_en} / {st_ar}</span></td>
                                <td style="border: 1px solid #dee2e6; padding: 10px 8px; white-space: nowrap;">{lead.write_date.strftime('%Y-%m-%d %H:%M')}</td>
                            </tr>
                        """

                expiring_orders_html = ""
                if expiring_orders:
                    for order in expiring_orders:
                        order_url = f"{base_url}/web#id={order.id}&model=crm.commercial.sale.order&view_type=form"
                        days_left = (order.expiry_date - today).days
                        st_en = status_dict_en.get(order.state, order.state)
                        st_ar = status_dict_ar.get(order.state, st_en)
                        expiring_orders_html += f"""
                            <tr>
                                <td style="border: 1px solid #dee2e6; padding: 10px 8px; font-weight: bold;"><a href="{order_url}" style="color: #0d6efd; text-decoration: none;">{order.name}</a></td>
                                <td style="border: 1px solid #dee2e6; padding: 10px 8px;">{order.project_name or ''}</td>
                                <td style="border: 1px solid #dee2e6; padding: 10px 8px;">{order.partner_id.name or ''}</td>
                                <td style="border: 1px solid #dee2e6; padding: 10px 8px; color: #dc3545; font-weight: bold; white-space: nowrap;">{order.expiry_date}</td>
                                <td style="border: 1px solid #dee2e6; padding: 10px 8px; font-weight: bold;">{days_left} d / {days_left} يوم</td>
                                <td style="border: 1px solid #dee2e6; padding: 10px 8px;"><span style="background-color: #e9ecef; padding: 3px 8px; border-radius: 4px; font-size: 12px;">{st_en} / {st_ar}</span></td>
                            </tr>
                        """

                lock_warning_block = ""
                if is_newly_locked:
                    lock_warning_block = f"""
                    <div style="background-color: #f8d7da; color: #842029; border: 1px solid #f5c2c7; padding: 14px; border-radius: 6px; margin-bottom: 20px; font-size: 14px; line-height: 1.4;">
                        <strong>⚠️ Notice / تنبيه:</strong> Your account has been temporarily locked due to no pipeline updates for {lock_weeks} weeks. Your manager has been notified to review and unlock your account.
                        <div style="margin-top: 6px;" dir="rtl">
                            تم قفل حسابك مؤقتاً لعدم تسجيل أي تحديثات على الفرص لمدة {lock_weeks} أسابيع. تم إشعار مديرك المباشر للمراجعة والتنشيط.
                        </div>
                    </div>
                    """

                stale_section_html = ""
                if stale_leads:
                    stale_section_html = f"""
                    <div style="margin-bottom: 25px;">
                        <h3 style="color: #dc3545; margin: 0 0 6px 0; font-size: 16px; border-bottom: 2px solid #dc3545; padding-bottom: 6px;">
                            1. Pipeline Leads Requiring Update ({len(stale_leads)})
                        </h3>
                        <div style="font-size: 14px; color: #dc3545; margin-bottom: 8px;" dir="rtl">
                            ١. الفرص البيعية التي تتطلب تحديث الحالة ({len(stale_leads)})
                        </div>
                        <p style="font-size: 13px; color: #495057; margin: 0 0 10px 0; line-height: 1.4;">
                            The following open leads have had no status updates in the last <b>{reminder_weeks} week(s)</b>. Please update their progress:
                            <span style="display:block; margin-top: 3px;" dir="rtl">الفرص التالية لم يتم تحديث حالتها منذ <b>{reminder_weeks} أسابيع</b>. يرجى تحديث الإجراءات وسير العمل:</span>
                        </p>
                        <div style="overflow-x: auto; -webkit-overflow-scrolling: touch;">
                            <table style="width: 100%; min-width: 500px; border-collapse: collapse; font-size: 13px;">
                                <thead>
                                    <tr style="background-color: #f8f9fa; text-align: left;">
                                        <th style="border: 1px solid #dee2e6; padding: 8px;">Lead No<br/><span style="font-weight:normal; font-size:11px;">رقم الفرصة</span></th>
                                        <th style="border: 1px solid #dee2e6; padding: 8px;">Project / Name<br/><span style="font-weight:normal; font-size:11px;">اسم المشروع</span></th>
                                        <th style="border: 1px solid #dee2e6; padding: 8px;">Customer Type<br/><span style="font-weight:normal; font-size:11px;">نوع العميل</span></th>
                                        <th style="border: 1px solid #dee2e6; padding: 8px;">Status<br/><span style="font-weight:normal; font-size:11px;">الحالة</span></th>
                                        <th style="border: 1px solid #dee2e6; padding: 8px;">Last Updated<br/><span style="font-weight:normal; font-size:11px;">آخر تحديث</span></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {stale_leads_html}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    """

                expiring_section_html = ""
                if expiring_orders:
                    expiring_section_html = f"""
                    <div style="margin-bottom: 20px;">
                        <h3 style="color: #fd7e14; margin: 0 0 6px 0; font-size: 16px; border-bottom: 2px solid #fd7e14; padding-bottom: 6px;">
                            2. Customer Orders Expiring in Next {expiry_alert_weeks} Weeks ({len(expiring_orders)})
                        </h3>
                        <div style="font-size: 14px; color: #fd7e14; margin-bottom: 8px;" dir="rtl">
                            ٢. أوامر البيع (المشاريع) المنتهية صلاحيتها خلال {expiry_alert_weeks} أسابيع ({len(expiring_orders)})
                        </div>
                        <p style="font-size: 13px; color: #495057; margin: 0 0 10px 0; line-height: 1.4;">
                            <b>Action Required:</b> Coordinate delivery schedules, process an expiry date extension via the <i>"Extend Expiry Date"</i> button on the order, or request inventory release:
                            <span style="display:block; margin-top: 3px;" dir="rtl">
                                <b>الإجراء المطلوب:</b> يرجى التنسيق لجدولة التسليم، أو طلب تمديد تاريخ الصلاحية من خلال زر <i>"تمديد تاريخ الانتهاء"</i> في أمر البيع، أو طلب فك حجز البضاعة.
                            </span>
                        </p>
                        <div style="overflow-x: auto; -webkit-overflow-scrolling: touch;">
                            <table style="width: 100%; min-width: 550px; border-collapse: collapse; font-size: 13px;">
                                <thead>
                                    <tr style="background-color: #f8f9fa; text-align: left;">
                                        <th style="border: 1px solid #dee2e6; padding: 8px;">Order No<br/><span style="font-weight:normal; font-size:11px;">رقم الطلب</span></th>
                                        <th style="border: 1px solid #dee2e6; padding: 8px;">Project Name<br/><span style="font-weight:normal; font-size:11px;">اسم المشروع</span></th>
                                        <th style="border: 1px solid #dee2e6; padding: 8px;">Customer<br/><span style="font-weight:normal; font-size:11px;">العميل</span></th>
                                        <th style="border: 1px solid #dee2e6; padding: 8px;">Expiry Date<br/><span style="font-weight:normal; font-size:11px;">تاريخ الانتهاء</span></th>
                                        <th style="border: 1px solid #dee2e6; padding: 8px;">Days Left<br/><span style="font-weight:normal; font-size:11px;">المتبقي</span></th>
                                        <th style="border: 1px solid #dee2e6; padding: 8px;">Status<br/><span style="font-weight:normal; font-size:11px;">الحالة</span></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {expiring_orders_html}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    """

                body = f"""<!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8"/>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
                </head>
                <body style="margin: 0; padding: 15px 10px; background-color: #f4f6f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #212529;">
                    <div style="max-width: 680px; width: 100%; margin: 0 auto; background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                        <div style="background-color: #0d6efd; color: #ffffff; padding: 16px 20px;">
                            <h2 style="margin: 0; font-size: 18px; line-height: 1.3;">Weekly Commercial CRM Action Digest</h2>
                            <div style="font-size: 14px; margin-top: 4px; opacity: 0.95;" dir="rtl">الملخص الأسبوعي للفرص وانتهاء الطلبات - إدارة علاقات العملاء التجارية</div>
                        </div>
                        <div style="padding: 20px;">
                            <p style="margin: 0 0 15px 0; font-size: 15px;">Hello <b>{salesman.name}</b> / مرحباً <b>{salesman.name}</b>,</p>

                            {lock_warning_block}
                            {stale_section_html}
                            {expiring_section_html}

                            <p style="color: #6c757d; font-size: 12px; margin-top: 25px; border-top: 1px solid #dee2e6; padding-top: 10px; text-align: center;">
                                This is an automated notification from the Commercial CRM System. Please do not reply directly to this email.<br/>
                                <span dir="rtl">هذا إشعار آلي من نظام إدارة علاقات العملاء التجارية. يرجى عدم الرد المباشر على هذه الرسالة.</span>
                            </p>
                        </div>
                    </div>
                </body>
                </html>
                """

                self.env['mail.mail'].sudo().create({
                    'subject': subject,
                    'body_html': body,
                    'email_to': salesman_email,
                    'email_from': default_from,
                }).send()
