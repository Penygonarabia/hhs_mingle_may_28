from odoo import models, fields, api


class PMService(models.Model):
    _name = "pm.service"
    _description = "PM Service"
    _order = "sort_order_header, id desc"

    # Header: Service Unit Type
    # Based on query: select product_product.id, product_product.default_code, name
    #   from product_template, product_product
    #   where product_template.id = product_product.product_tmpl_id
    #   and detailed_type = 'service'
    service_unit_type_id = fields.Many2one(
        "product.product",
        string="Service Unit Type",
        required=True,
        domain="[('detailed_type', '=', 'service')]",
    )

    service_unit_sub_type_id = fields.Selection([
        ('indoor', 'Indoor'),
        ('outdoor', 'Outdoor')
    ], string="Unit Sub Type")

    service_type_id = fields.Selection([
        ('major', 'Major'),
        ('minor', 'Minor'),
        ('both', 'Major/Minor'),
    ], string="Service Type")

        # Arabic fields (separate)
    service_unit_sub_type_ar = fields.Selection([
        ('indoor', 'داخلي'),
        ('outdoor', 'خارجي')
    ], string="نوع الوحدة")

    service_type_ar = fields.Selection([
        ('major', 'رئيسي'),
        ('minor', 'ثانوي'),
        ('both', 'ثانوي/رئيسي')
    ], string="نوع الخدمة")
    print_always_default=fields.Boolean(string="Print Always",default=True)


    # _sql_constraints = [
    #     ('service_unit_unique', 'unique(service_unit_type_id)', 'A PM Service configuration already exists for this Service Unit Type!')
    # ]

    line_ids = fields.One2many("pm.service.line", "pm_service_id", string="Parameters")
    sort_order_header = fields.Integer(
        string="Sort",
    )
    # line_ids = fields.One2many(
    #     'pm.service.line',
    #     'pm_service_id'
    # )

    @api.onchange("service_unit_type_id")
    def _onchange_set_sort_order_header(self):
        if not self.sort_order_header:
            records = self.search([])

            max_sort = max(
                records.mapped("sort_order_header"),
                default=0
            )

            self.sort_order_header = max_sort + 1



class PMServiceLine(models.Model):
    _name = "pm.service.line"
    _description = "PM Service Parameter Line"
    _order = "sort_order, id"

    pm_service_id = fields.Many2one(
        "pm.service", string="PM Service", required=True, ondelete="cascade"
    )

    service_type = fields.Selection(
        [
            ("major", "Major"),
            ("minor", "Minor"),
            ("both", "Major/Minor"),
        ],
        related='pm_service_id.service_type_id',
        string="Service Type",
        required=True,
    )
    service_type_ar = fields.Selection(
        [
            ("رئيسي", "رئيسي"),
            ("ثانوي", "ثانوي"),
            ("both", "ثانوي/رئيسي"),
        ],
        related='pm_service_id.service_type_ar',
        string="Service Type Arabic",
    )

    parameter = fields.Selection(
        [
            ("services", "Services"),
            ("physical_inspection", "Physical Inspection"),
            ("visual_inspection", "Visual Inspection"),
            ("parameter_measurement", "Parameter Measurement"),
        ],
        string="Parameters",
        required=True,
    )
    parameter_ar = fields.Selection(
        [
            ("الخدمات", "الخدمات"),
            ("الفحص الفيزيائى", "الفحص الفيزيائى"),
            ("الفحص البصري", "الفحص البصري"),
            ("قياسات المعايير", "قياسات المعايير"),
        ],
        string="Parameters Arabic",
    )

    description = fields.Text(string="Description")
    description_ara = fields.Text(string="Description Arabic")
    sort_order = fields.Integer(string="Sort", default=1)
    active = fields.Boolean(string="Active", default=True)

    sno = fields.Integer(string="Sort Order", default=0)

    parameter_sortorder = fields.Integer(string="Parameter Sortorder", default=1)
    parameter_sortorder_ar = fields.Integer(string="Parameter Sortorder", default=1)


    @api.onchange("pm_service_id")
    def _onchange_set_sno(self):
        """Auto set sno immediately when adding a line"""
        if not self.sno and self.pm_service_id:
            # include unsaved lines as well
            lines = self.pm_service_id.line_ids.filtered(lambda l: l != self)
            max_sno = max(lines.mapped("sno"), default=0)
            self.sno = max_sno + 1

    @api.onchange("pm_service_id")
    def _onchange_set_parameter_sortorder(self):
        """Auto set sno immediately when adding a line"""
        if not self.sno and self.pm_service_id:
            # include unsaved lines as well
            lines = self.pm_service_id.line_ids.filtered(lambda l: l != self)
            max_sno = max(lines.mapped("parameter_sortorder"), default=0)
            self.parameter_sortorder = max_sno + 1
