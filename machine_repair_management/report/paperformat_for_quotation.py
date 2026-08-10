from odoo import api, models


class ReportServiceSaleOrderDynamic(models.AbstractModel):
    _name = 'report.machine_repair_management.report_ssorder_dynamic'
    _description = 'Service Sale Order Dynamic Quotation Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['service.sale.order'].browse(docids)
        rec = docs[0] if docs else None

        if rec and rec.job_task_id:
            # HHS branch — template reads fields directly off doc, no extra values needed
            return {
                'doc_ids': docids,
                'doc_model': 'service.sale.order',
                'docs': docs,
            }
        else:
            # AMC branch — delegate to the existing AMC values builder
            amc_report = self.env['report.machine_repair_management.report_saleorder_amcquotation']
            return amc_report._get_report_values(docids, data)
        
        
class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        report = self._get_report(report_ref)
        if report.report_name == 'machine_repair_management.report_ssorder_dynamic' and res_ids:
            record = self.env['service.sale.order'].browse(res_ids[0])
            if record.job_task_id:
                report.paperformat_id = self.env.ref(
                    'machine_repair_management.paperformat_service_saleorder_hhs'
                )
            else:
                report.paperformat_id = self.env.ref(
                    'machine_repair_management.paperformat_amc_quotation_hhs'
                )
        return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)       

