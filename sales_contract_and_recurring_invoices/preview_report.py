import os
import re
import datetime
import webbrowser

# Paths relative to this script
module_dir = os.path.dirname(os.path.abspath(__file__))
xml_path = os.path.join(module_dir, 'report/report_contract_document.xml')
output_path = os.path.join(module_dir, 'report_preview.html')

# Read XML content
with open(xml_path, 'r', encoding='utf-8') as f:
    xml_content = f.read()

# Let's replace image relative paths with absolute file:// paths so they render correctly in the browser using a single-pass regex sub
xml_content = re.sub(r'/?sales_contract_and_recurring_invoices/static/src/img/', os.path.join(module_dir, 'static/src/img/'), xml_content)

# Helper function to remove QWeb template tags but keep internal HTML
def clean_qweb(html):
    # Remove Odoo envelope tags
    html = re.sub(r'<t\s+[^>]*t-call="[^"]*"[^>]*>', '', html)
    html = re.sub(r'<t\s+[^>]*t-foreach="[^"]*"[^>]*>', '', html)
    html = re.sub(r'<t\s+[^>]*t-as="[^"]*"[^>]*>', '', html)
    # Replace <t t-esc="..." /> or <t t-raw="..." /> with mock values
    html = re.sub(r'<t\s+t-esc="datetime[^"]*"\s*/>', datetime.datetime.today().strftime('%d-%m-%Y'), html)
    html = re.sub(r'<t\s+t-esc="o\.name"\s*/>', 'REF-2026-001', html)
    html = re.sub(r'<t\s+t-esc="o\.customer_name"\s*/>', 'HH Shaker Modern Trading Co. Ltd.', html)
    html = re.sub(r'<t\s+t-esc="o\.contact_persons[^"]*"\s*/>', 'John Doe', html)
    html = re.sub(r'<t\s+t-esc="o\.contact_persons_mobile[^"]*"\s*/>', '+966 50 123 4567', html)
    html = re.sub(r'<t\s+t-esc="o\.additional_info[^"]*"\s*/>', 'Special request for weekend maintenance service.', html)
    html = re.sub(r'<t\s+t-raw="0"\s*/>', '', html)
    html = re.sub(r'</t>', '', html)
    # Remove odoo attributes
    html = re.sub(r't-att-style="[^"]*"', '', html)
    html = re.sub(r't-att-src="[^"]*"', '', html)
    return html

# 1. Parse First Page Elements
first_page_header_match = re.search(r'(<div class="header"\s+style="border-bottom:1px solid #002060;.*?</div>\s*</div>)', xml_content, re.DOTALL)
first_page_header = first_page_header_match.group(1) if first_page_header_match else ""

first_page_body_match = re.search(r'(<div class="page contract-page">.*?</div>\s*</div>\s*</div>)', xml_content, re.DOTALL)
first_page_body = first_page_body_match.group(1) if first_page_body_match else ""

first_page_footer_match = re.search(r'(<div class="footer"\s+style="margin:0; padding:0; border-top: 1px solid #002060;.*?</div\s*>\s*</div>)', xml_content, re.DOTALL)
first_page_footer = first_page_footer_match.group(1) if first_page_footer_match else ""

# 2. Parse Subsequent Page Elements
subsequent_header_match = re.search(r'(<div class="header"\s+t-att-style="report_header_style".*?</div>\s*</div>\s*</div>)', xml_content, re.DOTALL)
subsequent_header = subsequent_header_match.group(1) if subsequent_header_match else ""

subsequent_footer_match = re.search(r'(<div class="footer"\s+style="padding:5px 0; border-top: 1px solid #002060;.*?</div\s*>\s*</div>)', xml_content, re.DOTALL)
subsequent_footer = subsequent_footer_match.group(1) if subsequent_footer_match else ""

# Sample body layout for subsequent page preview
subsequent_body = """
<div class="page">
    <table class="contract-table table-with-rows" style="width:100%; border-collapse:collapse; font-size:12pt; margin-top: 10px;">
        <tbody>
            <tr class="para">
                <td>Customer Name</td>
                <td colspan="2" style="width:50%; text-align:center; border-right: 1px solid #000 !important; border-left: 1px solid #000 !important;">
                    <strong>HH Shaker Modern Trading Co. Ltd.</strong>
                </td>
                <td dir="rtl" style="width:25%; text-align:right;">الاسم</td>
            </tr>
            <tr class="para" style="height:80px;">
                <td>Signature</td>
                <td colspan="2" style="border-right: 1px solid #000 !important; border-left: 1px solid #000 !important;"></td>
                <td dir="rtl" style="text-align:right;">التوقيع</td>
            </tr>
            <tr class="para">
                <td>Date</td>
                <td colspan="2" style="border-right: 1px solid #000 !important; border-left: 1px solid #000 !important;"></td>
                <td dir="rtl" style="text-align:right;">التاريخ</td>
            </tr>
        </tbody>
    </table>
    <br/>
    <table class="contract-table table-with-rows" style="width:100%; border-collapse:collapse; font-size:12pt; margin-top: 20px;">
        <tr class="para">
            <td style="width:50%; vertical-align:top; padding:10px;">
                <span style="font-weight:bold; color:#002060;">Annex A – Scope of Preventive Maintenance</span>
                <ul style="margin-top:8px; margin-bottom:8px; padding-left:20px;">
                    <li>As Mentioned in Quotation</li>
                    <li>Clean condenser coils and air filters.</li>
                    <li>Inspect and clean evaporator coils (if required).</li>
                    <li>Check fan motors, pulleys, and belts.</li>
                </ul>
            </td>
            <td dir="rtl" style="width:50%; vertical-align:top; padding:10px; text-align:right;">
                <span style="font-weight:bold; color:#002060;">الملحق أ - نطاق الصيانة الوقائية</span>
                <ul style="margin-top:8px; margin-bottom:8px; padding-right:20px; list-style-position: inside;">
                    <li>كما هو مذكور في العرض</li>
                    <li>تنظيف ملفات المكثف وفلاتر الهواء.</li>
                    <li>فحص وتنظيف ملفات المبخر (عند الحاجة).</li>
                </ul>
            </td>
        </tr>
    </table>
</div>
"""

# Let's clean all sections of QWeb logic
first_page_header = clean_qweb(first_page_header)
first_page_body = clean_qweb(first_page_body)
first_page_footer = clean_qweb(first_page_footer)
subsequent_header = clean_qweb(subsequent_header)
subsequent_footer = clean_qweb(subsequent_footer)
subsequent_body = clean_qweb(subsequent_body)

# Let's construct a complete html document with Bootstrap v4 styling and clean spacing
html_document = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Report Preview</title>
    <!-- Include Bootstrap 4 CDN to match Odoo's QWeb report styling grid -->
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <style>
        body {{
            background-color: #f0f2f5;
            padding: 30px;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }}
        .page-container {{
            background: #ffffff;
            width: 21cm;
            min-height: 29.7cm;
            padding: 2cm;
            margin: 0 auto 50px auto;
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
            border-radius: 8px;
            position: relative;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        .preview-label {{
            text-align: center;
            font-weight: bold;
            color: #4a5568;
            margin-bottom: 10px;
            font-size: 1.2rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }}
        .header {{
            margin-bottom: 20px;
        }}
        .footer {{
            margin-top: auto;
            padding-top: 15px;
        }}
        .contract-table {{
            background-color: #ffffff;
            position: relative;
            z-index: 2;
        }}
        .contract-table td {{
            border: 1px solid #000;
            padding: 8px;
        }}
    </style>
</head>
<body>

    <div class="preview-label">Page 1 Preview (First Page Layout)</div>
    <div class="page-container">
        <!-- FIRST PAGE HEADER -->
        {first_page_header}
        
        <!-- FIRST PAGE BODY -->
        <div style="margin-top: 40px; flex-grow: 1;">
            {first_page_body}
        </div>
        
        <!-- FIRST PAGE FOOTER -->
        {first_page_footer}
    </div>

    <div class="preview-label">Page 2 Preview (Subsequent Pages Layout)</div>
    <div class="page-container" style="position: relative;">
        <!-- Middle Vertical Line -->
        <div style="position: absolute; left: 50%; top: 2cm; bottom: 2cm; border-left: 1px solid #002060; z-index: 1;"></div>
        <!-- SUBSEQUENT PAGES HEADER -->
        {subsequent_header}
        
        <!-- SUBSEQUENT PAGES BODY -->
        <div style="margin-top: 10px; flex-grow: 1; position: relative; z-index: 2;">
            {subsequent_body}
        </div>
        
        <!-- SUBSEQUENT PAGES FOOTER -->
        {subsequent_footer}
    </div>

</body>
</html>
'''

# Write output file
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html_document)

print(f"Preview HTML generated successfully: {output_path}")
