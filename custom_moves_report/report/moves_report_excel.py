from odoo import fields, models, api, _
import xlsxwriter
import io
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class CustomMovesReportExcel(models.AbstractModel):
    _name = 'report.custom_moves_report.report_custom_moves_xlsx'
    _inherit = 'report.report_xlsx.abstract'    
    _description = 'Custom Moves Report Xlsx'

    def generate_xlsx_report(self, workbook, data, wizard):
        
        header_merge_format = workbook.add_format({'bold':True, 'align':'center', 'valign':'vcenter', \
                                            'font_size':10, 'bg_color':'#D3D3D3', 'border':1})
        header_data_format = workbook.add_format({'align':'center', 'valign':'vcenter', \
                                                   'font_size':10, 'border':1})
        product_header_format = workbook.add_format({'valign':'vcenter', 'font_size':11, 'border':1,'bold':True,})
        sheet = workbook.add_worksheet("Movement Report in "+ wizard.location_id.name_get()[0][1])
        sheet.set_row(0, 25)

        sheet.merge_range(5, 0, 5, 1, 'Company', header_merge_format)
        sheet.write(5, 2, 'Warehouse', header_merge_format)
        sheet.write(5, 3, 'Start Date', header_merge_format)
        sheet.write(5, 4, 'End Date', header_merge_format)
        sheet.merge_range(6, 0, 6, 1, wizard.company_id.name, header_data_format)
        sheet.write(6, 2, wizard.warehouse_ids.name, header_data_format)
        sheet.write(6, 3, str(wizard.start_date), header_data_format)
        sheet.write(6, 4, str(wizard.end_date), header_data_format)

        if wizard.to_collapse == True:
            sheet.merge_range(0, 0, 2, 9, "Movement Report in "+ wizard.location_id.name_get()[0][1] , header_merge_format)
            sheet.write(8, 0, 'S.No', header_merge_format)
            sheet.set_column(0, 0, 10)
            sheet.write(8, 1, 'Product', header_merge_format)
            sheet.set_column(1, 1, 27)
            sheet.write(8, 2, 'Opening Balance', header_merge_format)
            sheet.set_column(2, 2, 16)
            sheet.write(8, 3, 'Opening Value', header_merge_format)
            sheet.set_column(3, 3, 16)
            sheet.write(8, 4, 'Total In Qty', header_merge_format)
            sheet.set_column(4, 4, 16)
            sheet.write(8, 5, 'In Value', header_merge_format)
            sheet.write(8, 6, 'Total Out Qty', header_merge_format)
            sheet.set_column(6, 6, 12)
            sheet.write(8, 7, 'Out Value', header_merge_format)
            sheet.write(8, 8, 'Balance Qty', header_merge_format)
            sheet.set_column(8, 8, 12)
            sheet.write(8, 9, 'End Value', header_merge_format)
            row = 9
            no = 1
            all_qty = 0
            total_all_qty = 0
            total_all_value = 0
            qty_lst = []
            val_lst = []
            all_lst = []
            unit_value = 0
            stock_quant = self.env['stock.quant'].search([('product_id', '=', wizard.product_ids.ids),('location_id', '=', wizard.location_id.id),('company_id', '=', wizard.company_id.id)],order = "product_id ASC")
            for stock in stock_quant:
                if stock.product_id:
                    col = 0
                    sheet.write(row, col, no, header_data_format)
                    col += 1
                    sheet.write(row, col, "["+str(stock.product_id.default_code)+ "]  "+stock.product_id.name, header_data_format)
                    '''Beginning stock Product search before the start date '''
                    all_moves = self.env['stock.move.line'].search([('product_id', '=', stock.product_id.id),('state', '=', 'done'),('company_id', '=', wizard.company_id.id),('date', '<', wizard.start_date),('location_dest_id', '=', wizard.location_id.id)])
                    beg_qty = 0
                    beg_val = 0
                    valu = 0
                    stock_valuation = self.env['stock.valuation.layer'].search([('product_id', '=', stock.product_id.id)])
                    for sto in stock_valuation:
                        valu = sto.unit_cost
                    unit_value = valu

                    for sto in all_moves:
                        qty=0
                        val=0
                        if sto.location_dest_id == wizard.location_id:
                            qty = sto.quantity
                            val = qty * unit_value
                            beg_qty += qty
                            beg_val += val
                    total_all_qty += beg_qty
                    total_all_value += beg_val

                    beg_in_qty = 0
                    beg_in_val = 0
                    stock_begin_out = self.env['stock.move.line'].search([('product_id', '=', stock.product_id.id),('state', '=', 'done'),('company_id', '=', wizard.company_id.id),('date', '<', wizard.start_date),('location_id', '=', wizard.location_id.id)])
                    for stock_out in stock_begin_out:
                        qty_beg = 0
                        val_beg = 0
                        if stock_out.location_id == wizard.location_id:
                            qty_beg = stock_out.quantity
                            val_beg = qty_beg * unit_value
                            beg_in_qty += qty_beg
                            beg_in_val += val_beg
                    total_all_qty -= beg_in_qty
                    total_all_value -= beg_in_val
                    qty_lst.append(total_all_qty)
                    val_lst.append(total_all_value)

                    col = 2
                    sheet.write(row, col, ('{:,.2f}'.format(total_all_qty)) or 0.0, header_data_format)
                    col += 1
                    sheet.write(row, col,('{:,.2f}'.format(total_all_value))   or 0.0, header_data_format)

                    ''' stock Product entered in to warehouse '''
                    stock_in = self.env['stock.move.line'].search([('product_id', '=', stock.product_id.id),('company_id', '=', wizard.company_id.id),('date', '>=', wizard.start_date),('date', '<=', wizard.end_date),('state', '=', 'done'),('location_dest_id', '=', wizard.location_id.id)])
                    total_qty = 0
                    total_val = 0
                    for prod in stock_in:
                        qty = 0
                        val = 0
                        if prod.location_dest_id == wizard.location_id:
                            qty = prod.quantity
                            val = qty * unit_value
                            total_qty += qty
                            total_val += val

                    qty_lst.append(total_qty)
                    val_lst.append(total_val)
                    total_all_qty += total_qty
                    total_all_value += total_val
                    col = 4
                    sheet.write(row, col, ('{:,.2f}'.format(total_qty)) or 0.0, header_data_format)
                    col += 1
                    sheet.write(row, col, ('{:,.2f}'.format(total_val)) or 0.0, header_data_format)

                    ''' stock Product Out from the warehouse '''
                    stock_out = self.env['stock.move.line'].search([('product_id', '=', stock.product_id.id),('company_id', '=', wizard.company_id.id),('date', '>=', wizard.start_date),('date', '<=', wizard.end_date),('state', '=', 'done'),('location_id', '=', wizard.location_id.id)])
                    tot_qty = 0
                    tot_val = 0
                    for sto in stock_out:
                        qty1 = 0
                        value1 = 0
                        if sto.location_id == wizard.location_id:
                            qty1 = sto.quantity
                            value1 = qty1 * unit_value
                            tot_qty += qty1
                            tot_val += value1
                    qty_lst.append(tot_qty)
                    val_lst.append(tot_val)
                    total_all_qty -= tot_qty
                    total_all_value -= tot_val
                    col = 6
                    sheet.write(row, col, ('{:,.2f}'.format(tot_qty)) or 0.0, header_data_format)
                    col += 1
                    sheet.write(row, col, ('{:,.2f}'.format(tot_val)) or 0.0, header_data_format)
                    qty_lst.append(total_all_qty)
                    val_lst.append(total_all_value)
                    col = 8
                    sheet.write(row, col,('{:,.2f}'.format(total_all_qty)) or 0.0, header_data_format)
                    col += 1
                    sheet.write(row, col, ('{:,.2f}'.format(total_all_value)) or 0.0, header_data_format)
                    total_all_qty = 0
                    total_all_value = 0
                    row += 1
                    no += 1
              
            ''' All quantity and all values goes into list and split the list and add the numbers into form the list  '''
            row += 1
            n = 4
            x = [qty_lst[i:i + n] for i in range(0, len(qty_lst), n)]
            y = [val_lst[j:j+n] for j in range(0, len(val_lst),n)]
            if x:
                col = 1
                sheet.merge_range(row, 0, row, col, 'Total' , header_merge_format)
                col += 1
                f_list = []
                for r in range(len(x[0])):
                    value = 0
                    for v in range(0,len(x)):
                        value += x[v][r]
                    f_list.append(value)
                for total_line in f_list:
                    sheet.write(row, col, ('{:,.2f}'.format(total_line)) or 0.0, header_data_format)
                    col += 2
            if y:
                col = 3
                f_list = []
                for r in range(len(y[0])):
                    value = 0
                    for v in range(0,len(y)):
                        value += y[v][r]
                    f_list.append(value)
                for total_line in f_list:
                    sheet.write(row, col, ('{:,.2f}'.format(total_line)) or 0.0, header_data_format)
                    col += 2

        elif wizard.to_collapse==False:
            sheet.merge_range(0, 0, 2, 11, "Movement Report in "+ wizard.location_id.name_get()[0][1] , header_merge_format)
            sheet.write(8, 0, 'S.No', header_merge_format)
            sheet.set_column(0, 0, 10)
            sheet.write(8, 1, 'Product', header_merge_format)
            sheet.set_column(1, 1, 27)
            sheet.write(8, 2, 'Date', header_merge_format)
            sheet.set_column(2, 2, 18)
            sheet.write(8, 3, 'Reference', header_merge_format)
            sheet.set_column(3,3,20)
            sheet.write(8, 4, 'From', header_merge_format)
            sheet.set_column(4, 4, 20)
            sheet.write(8, 5, 'To', header_merge_format)
            sheet.set_column(5, 5, 20)
            sheet.write(8, 6, 'In Qty', header_merge_format)
            sheet.write(8, 7, 'In value', header_merge_format)
            sheet.write(8, 8, 'Out Qty', header_merge_format)
            sheet.write(8, 9, 'Out Value',header_merge_format)
            sheet.write(8, 10, 'Balance Qty',header_merge_format)
            sheet.set_column(10, 10, 12)
            sheet.write(8, 11, 'Balance Value', header_merge_format)
            sheet.set_column(11, 11, 12)
            row = 9
            no = 1
            unit_value = 0
            stock_quant = self.env['stock.quant'].search([('product_id','=',wizard.product_ids.ids),('location_id','=',wizard.location_id.id),('company_id','=',wizard.company_id.id)], order = "product_id ASC")
            for stock in stock_quant:
                if stock.product_id:
                    col = 0
                    sheet.write(row, col, no, header_data_format)
                    col += 1
                    sheet.write(row, col, "["+str(stock.product_id.default_code)+ "]  "+stock.product_id.name,header_data_format)
                    stock_movement = self.env['stock.move.line'].search([('product_id', '=', stock.product_id.id),('state', '=', 'done'),('company_id', '=', wizard.company_id.id),('date', '<', wizard.start_date),('location_dest_id', '=', wizard.location_id.id)])
                    all_qty = 0
                    all_val =  0
                    beg_qty = 0
                    beg_val = 0
                    valu = 0
                    stock_valuation=self.env['stock.valuation.layer'].search([('product_id', '=', stock.product_id.id)])
                    for sto in stock_valuation:
                        valu = sto.unit_cost
                    unit_value=valu
                    for sto in stock_movement:
                        qty = 0
                        val = 0
                        if sto.location_dest_id == wizard.location_id:
                            qty = sto.quantity
                            val = qty * unit_value
                            beg_qty += qty
                            beg_val += val
                    all_qty += beg_qty
                    all_val += beg_val

                    beg_in_qty = 0
                    beg_in_val = 0
                    stock_begin_out = self.env['stock.move.line'].search([('product_id', '=', stock.product_id.id),('state', '=', 'done'),('company_id', '=', wizard.company_id.id),('date', '<', wizard.start_date),('location_id', '=', wizard.location_id.id)])
                    for stock_out in stock_begin_out:
                        qty_beg = 0
                        val_beg = 0
                        if stock_out.location_id == wizard.location_id:
                            qty_beg = stock_out.quantity
                            val_beg = qty_beg * unit_value
                            beg_in_qty += qty_beg
                            beg_in_val += val_beg
                    all_qty -= beg_in_qty
                    all_val -= beg_in_val
                    col = 10
                    sheet.write(row, col, ('{:,.2f}'.format(all_qty)) or 0.0, header_data_format)
                    col += 1
                    sheet.write(row, col, ('{:,.2f}'.format(all_val)) or 0.0, header_data_format)
                    row += 1

                    all_moves = self.env['stock.move.line'].search(['|', ('location_id', '=', wizard.location_id.id),('location_dest_id', '=', wizard.location_id.id),('product_id', '=', stock.product_id.id),('company_id', '=', wizard.company_id.id),('state', '=', 'done'),('date', '>=', wizard.start_date),('date', '<=', wizard.end_date)], order='date')
                    for moves in all_moves:
                        col = 2
                        sheet.write(row, col, str(moves.date), header_data_format)
                        col += 1
                        sheet.write(row, col, moves.reference or ' ', header_data_format)
                        sheet.set_column(3, 3, 25)
                        col += 1
                        sheet.write(row, col, moves.location_id.name_get()[0][1] or ' ', header_data_format)
                        sheet.set_column(4, 4, 30)
                        col += 1
                        sheet.write(row, col, moves.location_dest_id.name_get()[0][1] or ' ', header_data_format)
                        sheet.set_column(5, 5, 30)
                        col += 1

                        value = 0
                        qty = 0
                        if moves.location_dest_id == wizard.location_id and moves.location_dest_id != moves.location_id:
                            qty = moves.quantity
                            sheet.write(row, col, ('{:,.2f}'.format(qty)) or '0.0', header_data_format)
                            col += 1
                            value = qty * unit_value
                            sheet.write(row, col, ('{:,.2f}'.format(value)) or '0.0', header_data_format)
                        all_qty += qty
                        all_val += value

                        quty = 0
                        val = 0
                        if moves.location_id == wizard.location_id:
                            col = 8
                            quty = moves.quantity
                            sheet.write(row, col, ('{:,.2f}'.format(quty)) or '0.0', header_data_format)
                            col += 1
                            val = quty * unit_value
                            sheet.write(row, col, ('{:,.2f}'.format(val)) or '0.0', header_data_format )
                        all_qty -= quty
                        all_val -= val
                        col = 10
                        sheet.write(row, col, ('{:,.2f}'.format(all_qty)) or '0.0', header_data_format)
                        col += 1
                        sheet.write(row, col, ('{:,.2f}'.format(all_val)) or '0.0', header_data_format)
                        row += 1
                    col = 9
                    sheet.merge_range(row, 0, row, col, 'Total', header_merge_format)
                    col += 1
                    sheet.write(row, col, ('{:,.2f}'.format(all_qty)) or '0.0', header_merge_format )
                    col += 1
                    sheet.write(row, col, ('{:,.2f}'.format(all_val)) or '0.0', header_merge_format)
                    row += 1
                    no += 1
                   
            
          
            
            
            
            
            
            
        
        
        
        