from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ServiceSaleOrder(models.Model):
    _inherit = 'service.sale.order'


    pm_checklist_ids = fields.One2many(
        'pm.service.checklist.line',
        'service_order_id',
        string='PM Service Check List'
    )

    # @api.onchange('service_sale_order_line_ids')
    # def _onchange_order_line_populate_checklist(self):
    #     for order in self:
    #
    #         if not order.service_sale_order_line_ids:
    #             continue
    #
    #         # Step 1: Get selected product IDs
    #         extracted_types = order.service_sale_order_line_ids.mapped('product_id').ids
    #         if not extracted_types:
    #             continue
    #
    #         # Step 2: Fetch pm.service records
    #         masters = self.env['pm.service'].search([
    #             ('service_unit_type_id', 'in', extracted_types)
    #         ])
    #
    #         from collections import defaultdict
    #         existing_counts = defaultdict(int)
    #
    #         # Step 3: Track existing checklist lines
    #         for line in order.pm_checklist_ids:
    #             key = (
    #                 line.service_unit_type_id.id,
    #                 line.unit_sub_type_id,
    #                 line.service_type_id
    #             )
    #             existing_counts[key] += 1
    #
    #         # Step 4: Add only missing records
    #         new_line_commands = []
    #
    #         for master in masters:
    #             key = (
    #                 master.service_unit_type_id.id,
    #                 master.service_unit_sub_type_id,
    #                 master.service_type_id
    #             )
    #
    #             if existing_counts[key] > 0:
    #                 existing_counts[key] -= 1
    #             else:
    #                 new_line_commands.append((0, 0, {
    #                     'service_unit_type_id': master.service_unit_type_id.id,
    #                     'unit_sub_type_id': master.service_unit_sub_type_id,
    #                     'service_type_id': master.service_type_id,
    #                     'is_selected': True,
    #                 }))
    #
    #         # ✅ IMPORTANT: Append instead of replace
    #         if new_line_commands:
    #             order.pm_checklist_ids = new_line_commands

    @api.onchange('service_sale_order_line_ids')
    def _onchange_order_line_populate_checklist(self):
        for order in self:

            extracted_types = order.service_sale_order_line_ids.mapped('product_id').ids

            # If no products, clear checklist
            if not extracted_types:
                order.pm_checklist_ids = [(5, 0, 0)]
                continue

            # Fetch PM services
            masters = self.env['pm.service'].search(['|',
                ('service_unit_type_id', 'in', extracted_types),
                 ('print_always_default','=',True)
            ])
            # masters = self.env['pm.service'].search(
            #     [('service_unit_type_id', 'in', extracted_types)],
            #     order='sort_order_header asc'
            # )

            from collections import defaultdict

            # Existing checklist counts
            existing_counts = defaultdict(int)

            for line in order.pm_checklist_ids:

                p_id = line.service_unit_type_id.id

                if (
                        not isinstance(p_id, int)
                        and hasattr(line.service_unit_type_id, '_origin')
                        and line.service_unit_type_id._origin
                ):
                    p_id = line.service_unit_type_id._origin.id

                key = (
                    p_id,
                    line.unit_sub_type_id,
                    line.service_type_id
                )

                existing_counts[key] += 1

            # Valid master keys
            valid_keys = set()

            for master in masters:
                valid_keys.add((
                    master.service_unit_type_id.id,
                    master.service_unit_sub_type_id,
                    master.service_type_id
                ))

            commands = []

            # Remove unwanted checklist lines
            for line in order.pm_checklist_ids:

                p_id = line.service_unit_type_id.id
                print("line.service_unit_type_id.id",line.service_unit_type_id.id)

                if (
                        not isinstance(p_id, int)
                        and hasattr(line.service_unit_type_id, '_origin')
                        and line.service_unit_type_id._origin
                ):
                    p_id = line.service_unit_type_id._origin.id

                line_key = (
                    p_id,
                    line.unit_sub_type_id,
                    line.service_type_id
                )

                if line_key not in valid_keys:
                    commands.append((2, line.id))
                    print("origin_id",line.service_unit_type_id._origin.id)

            # Add missing checklist lines
            for master in masters:

                key = (
                    master.service_unit_type_id.id,
                    master.service_unit_sub_type_id,
                    master.service_type_id
                )

                if existing_counts[key] > 0:
                    existing_counts[key] -= 1

                else:

                    has_print_always = master.print_always_default

                    commands.append((0, 0, {
                        'service_unit_type_id': master.service_unit_type_id.id,
                        'unit_sub_type_id': master.service_unit_sub_type_id,
                        'service_type_id': master.service_type_id,

                        # untick if print_always_default=True
                        'is_selected': False if has_print_always else True,

                        'print_always_default': has_print_always,

                        # move bottom
                        'sort_order': 999 if has_print_always else 1,
                    }))
            # for master in masters:
            #
            #     key = (
            #         master.service_unit_type_id.id,
            #         master.service_unit_sub_type_id,
            #         master.service_type_id
            #     )
            #
            #     if existing_counts[key] > 0:
            #         existing_counts[key] -= 1
            #     else:
            #         commands.append((0, 0, {
            #             'service_unit_type_id': master.service_unit_type_id.id,
            #             'unit_sub_type_id': master.service_unit_sub_type_id,
            #             'service_type_id': master.service_type_id,
            #             # 'sort_order_header': master.sort_order_header,
            #             'is_selected': True,
            #         }))



            if commands:
                order.pm_checklist_ids = commands
                print("pm_checklist_ids", order.pm_checklist_ids)

    # @api.onchange('service_sale_order_line_ids')
    # def _onchange_order_line_populate_checklist(self):
    #     for order in self:
    #         # Extract Service Unit Types from order lines
    #         # The PM Service master 'service_unit_type_id' maps to the 'product_id' on the order line.
    #         if hasattr(order, 'service_sale_order_line_ids'):
    #             extracted_types = order.service_sale_order_line_ids.mapped('product_id').ids
    #
    #             if not extracted_types:
    #                 continue
    #             # Search pm.service based on extracted types
    #             masters = self.env['pm.service'].search([
    #                 ('service_unit_type_id', 'in', extracted_types)
    #             ])
    #
    #             from collections import defaultdict
    #             # Maintain existing combinations count to prevent blind resets while allowing intended duplicates
    #             existing_counts = defaultdict(int)
    #             for line in order.pm_checklist_ids:
    #                 # Robust extraction of the integer ID for Many2one in onchange
    #                 p_id = line.service_unit_type_id.id
    #                 if not isinstance(p_id, int) and hasattr(line.service_unit_type_id, '_origin') and line.service_unit_type_id._origin:
    #                     p_id = line.service_unit_type_id._origin.id
    #
    #                 key = (
    #                     p_id,
    #                     line.unit_sub_type_id,
    #                     line.service_type_id
    #                 )
    #                 existing_counts[key] += 1
    #
    #             # Batch generate commands to add missing checklist records
    #             new_line_commands = []
    #             for master in masters:
    #                 key = (
    #                     master.service_unit_type_id.id,
    #                     master.service_unit_sub_type_id,
    #                     master.service_type_id
    #                 )
    #                 if existing_counts[key] > 0:
    #                     existing_counts[key] -= 1
    #                 else:
    #                     new_line_commands.append((0, 0, {
    #                         'service_unit_type_id': master.service_unit_type_id.id,
    #                         'unit_sub_type_id': master.service_unit_sub_type_id,
    #                         'service_type_id': master.service_type_id,
    #                         'is_selected': True,
    #                     }))
    #
    #             if new_line_commands:
    #                 order.pm_checklist_ids = new_line_commands

    @api.model_create_multi
    def create(self, vals_list):
        records = super(ServiceSaleOrder, self).create(vals_list)
        for record in records:
            record._validate_pm_checklist()
        return records

    def write(self, vals):
        res = super(ServiceSaleOrder, self).write(vals)
        if 'pm_checklist_ids' in vals:
            for record in self:
                record._validate_pm_checklist()
        return res

    def action_confirm(self):
        # We assume there could be an action_confirm hook defined by other modules if any
        if hasattr(super(ServiceSaleOrder, self), 'action_confirm'):
            res = super(ServiceSaleOrder, self).action_confirm()
        else:
            res = True

        for record in self:
            record._validate_pm_checklist()
        return res

    def _validate_pm_checklist(self):
        for record in self:
            if record.pm_checklist_ids:
                if not any(l.is_selected for l in record.pm_checklist_ids):
                    raise ValidationError("At least one PM Service must be selected.")
