import io

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request


class DatabaseStudioController(http.Controller):

    @http.route("/database_studio/export_xlsx", type="http", auth="user", methods=["POST"], csrf=True)
    def export_xlsx(self, query=None, **kwargs):
        import xlsxwriter

        Analyser = request.env["database.studio.analyser"]
        try:
            Analyser._check_access()
        except AccessError as e:
            return request.make_response(str(e), status=403)

        query = (query or "").strip()
        if not query:
            return request.not_found()

        cr = request.env.cr
        try:
            cr.execute(query)
        except Exception as e:
            cr.rollback()
            return request.make_response(str(e), status=400)

        description = cr.description
        if not description:
            return request.not_found()

        columns = [d[0] for d in description]
        max_rows = Analyser._EXPORT_MAX_ROWS
        rows = cr.fetchmany(max_rows + 1)
        truncated = len(rows) > max_rows
        if truncated:
            rows = rows[:max_rows]

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Result")
        header_fmt = workbook.add_format({"bold": True, "bg_color": "#EFEFEF"})
        for col_idx, col in enumerate(columns):
            sheet.write(0, col_idx, col, header_fmt)
        for row_idx, row in enumerate(rows, start=1):
            for col_idx, val in enumerate(row):
                val = Analyser._fmt(val)
                if val is None:
                    sheet.write_blank(row_idx, col_idx, None)
                else:
                    sheet.write(row_idx, col_idx, val)
        if truncated:
            note = workbook.add_worksheet("Info")
            note.write(0, 0, "Result set exceeded %s rows; only the first %s were exported." % (max_rows, max_rows))
        workbook.close()
        output.seek(0)

        return request.make_response(
            output.read(),
            headers=[
                ("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                ("Content-Disposition", 'attachment; filename="query_result.xlsx"'),
            ],
        )
