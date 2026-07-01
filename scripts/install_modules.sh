#!/bin/bash
# ============================================================
# install_modules.sh  
# Copies custom Odoo modules into Docker container
# (bypassing iCloud sync deadlock) and installs via HTTP API
# ============================================================

CONTAINER="cloud-web-1"
CLOUD_DIR="/Users/saravanan/Library/Mobile Documents/com~apple~CloudDocs/Saravanan/Cielo_Digital/Odoo/Applications/cloud"
DEST_DIR="/opt/extra-addons"
BASE_URL="http://localhost:8069"
DB="dbcloud"
ADMIN_USER="admin"
ADMIN_PASS="admin"
SESSION_FILE="/tmp/odoo_install_session.txt"

ALL_MODULES=(
  "ks_dashboard_ninja" "ks_dn_advance" "ks_dashboard_admin_restrict"
  "dashboard_rights" "dashboard_rights_ninja_bridge"
  "om_hr_payroll" "om_hr_payroll_account"
  "hr_contract_types" "hr_contract_allowances" "hr_attendances_overtime"
  "hr_loan_advance" "hr_gratuity" "hr_end_service_benefits"
  "hr_custody" "hr_exit_process" "hr_saudi" "hr_employee_updation"
  "hr_transaction" "hr_leave_balance_report" "leave_encash_hr"
  "leave_sandwich_rule" "ag_employee_self_service" "sh_hr_promotion"
  "employee_documents_expiry" "tw_gosi" "iqama_management" "hrms_salary_al_dt"
  "report_xlsx" "base_account_budget" "base_accounting_kit"
  "accounting_pdf_reports" "accounting_excel_reports" "dynamic_accounts_report"
  "query_deluxe" "sh_accounting_reports" "account_analytic_parent"
  "account_analytic_tag" "analytic_account_policy" "analytic_base_department"
  "purchase_stock_analytic" "sale_stock_analytic" "stock_analytic"
  "advance_login_form" "wk_debrand_odoo" "easy_language_selector"
  "required_label_star" "odoo_caption_changes" "remove_odoo_enterprise"
  "hide_dashboard_buttons" "hide_menu_user" "hide_partner_form"
  "beta_dashboards" "contract_dashboards" "loyalty_dashboard"
  "promoter_dashboards" "service_dashboards_ct" "service_dashboards_ot"
  "base_territory" "partner_type_hhs" "hhs_company_logo_image"
  "hhs_contract_payment_terms" "hhs_amc_pricing" "hhs_amc_quotation"
  "amc_quotation" "hhs_loyalty_management" "hhs_loyalty_res_partner"
  "hhs_loyalty_invoice_processor" "hhs_pm_service" "pm_service_checklist"
  "hhs_post_service_checklist" "machine_repair_management" "dealer"
  "promoter" "hyperbill_payments" "payment_bank_two"
  "sales_contract_and_recurring_invoices" "service_sale_approval"
  "service_sale_approvals" "service_sale_order_revision"
  "bb_stock_quant_report" "dev_inventory_ageing_report"
  "setu_inventory_count_management" "stock_quant"
  "stock_valuation_by_location_warehouse_app" "sync_inventory_adjustment"
  "ak_material_request" "warehouse_restrictions_app" "selling_cost_price_restrict"
  "custom_moves_report" "employee_details_report" "employee_document_renewal_report"
  "employee_payroll_report" "employee_salary_report" "employee_advance_report"
  "employee_loan_report" "payroll_report" "payroll_employee_report"
  "payroll_payment" "payroll_payment_advice" "payment_advice_payroll"
  "payroll_transaction_batch" "payroll_transactions_report"
  "termination_details_report" "daily_attendance_report"
  "bi_hr_attendance_leave_report" "leave_arrival_employee"
  "auto_database_backup" "user_audit" "user_geolocation" "user_password_strength"
  "birthday_wish" "dh_visitor_managment" "partner_whatsapp"
  "whatapps_chat_bot" "whatsapp_sale_order_notify" "organization_chart"
  "registration_form" "registration_form_bar" "registration_form_new"
  "project_api" "project_dom_gantt_view" "project_task_readonly_control"
  "project_team_assignment" "dom_gantt_view" "dom_gantt_resource_wo_event"
  "entitlement" "geomarking_attendance_mobile_app_knk" "yc_code_scanner_mobile"
  "website_menu_restriction" "disable_service_worker"
  "pos_restrict" "odoo_ecommerce_pwa"
)

echo "============================================"
echo "Step 1: Ensure /opt/extra-addons exists"
echo "============================================"
docker exec -u root "$CONTAINER" mkdir -p "$DEST_DIR"
docker exec -u root "$CONTAINER" chown odoo:odoo "$DEST_DIR"
echo "Done."

echo ""
echo "============================================"
echo "Step 2: Copy modules into container"
echo "============================================"
COPIED=0; SKIPPED=0; FAILED=0
for module in "${ALL_MODULES[@]}"; do
  SRC="$CLOUD_DIR/$module"
  if [ -d "$SRC" ]; then
    printf "  Copying %-45s" "$module..."
    if docker cp "$SRC" "$CONTAINER:$DEST_DIR/$module" 2>/dev/null; then
      echo " OK"
      COPIED=$((COPIED+1))
    else
      echo " FAILED"
      FAILED=$((FAILED+1))
    fi
  else
    SKIPPED=$((SKIPPED+1))
  fi
done
echo ""
echo "  Summary: Copied=$COPIED, Skipped=$SKIPPED, Failed=$FAILED"

echo ""
echo "============================================"
echo "Step 3: Update addons_path in odoo.conf"
echo "============================================"
docker exec -u root "$CONTAINER" sh -c "
  if grep -q '/opt/extra-addons' /etc/odoo/odoo.conf; then
    echo 'Already present'
  else
    sed -i 's|addons_path = /mnt/extra-addons,|addons_path = /opt/extra-addons,/mnt/extra-addons,|' /etc/odoo/odoo.conf
    echo 'Updated addons_path:'
  fi
  grep addons_path /etc/odoo/odoo.conf
"

echo ""
echo "============================================"
echo "Step 4: Restart Odoo"
echo "============================================"
docker restart "$CONTAINER"
printf "Waiting for Odoo to start"
for i in $(seq 1 40); do
  sleep 2
  STATUS=$(curl -s "$BASE_URL/web/health" 2>/dev/null)
  if echo "$STATUS" | grep -q '"status":"pass"'; then
    echo " Ready!"
    break
  fi
  printf "."
done
echo ""

echo ""
echo "============================================"
echo "Step 5: Login"
echo "============================================"
rm -f "$SESSION_FILE"
LOGINRESP=$(curl -s -c "$SESSION_FILE" -X POST "$BASE_URL/web/session/authenticate" \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"db\":\"$DB\",\"login\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"}}")
LOGIN_UID=$(echo "$LOGINRESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('result',{}).get('uid','ERROR'))")
echo "Login UID: $LOGIN_UID"
if [ "$LOGIN_UID" = "ERROR" ] || [ -z "$LOGIN_UID" ]; then
  echo "ERROR: Login failed!"
  exit 1
fi

echo ""
echo "============================================"
echo "Step 6: Update module list"
echo "============================================"
curl -s -b "$SESSION_FILE" -c "$SESSION_FILE" -X POST "$BASE_URL/web/dataset/call_kw" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"model":"ir.module.module","method":"update_list","args":[],"kwargs":{}}}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('Module list result:', d.get('result','ERROR'))"
sleep 2

echo ""
echo "============================================"
echo "Step 7: Install modules"
echo "============================================"

do_login() {
  rm -f "$SESSION_FILE"
  curl -s -c "$SESSION_FILE" -X POST "$BASE_URL/web/session/authenticate" \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"db\":\"$DB\",\"login\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"}}" > /dev/null
}

install_module() {
  local name="$1"
  local RESULT=$(curl -s -b "$SESSION_FILE" -c "$SESSION_FILE" -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"model\":\"ir.module.module\",\"method\":\"search_read\",\"args\":[[[[\"name\",\"=\",\"$name\"]]]],\"kwargs\":{\"fields\":[\"id\",\"state\"]}}}")
  local ID=$(echo "$RESULT" | python3 -c "import sys,json; r=json.load(sys.stdin).get('result',[]); print(r[0]['id'] if r else '')" 2>/dev/null)
  local STATE=$(echo "$RESULT" | python3 -c "import sys,json; r=json.load(sys.stdin).get('result',[]); print(r[0]['state'] if r else 'not_found')" 2>/dev/null)

  if [ -z "$ID" ]; then
    printf "  %-45s Not found\n" "[$name]"
    return
  fi
  if [ "$STATE" = "installed" ]; then
    printf "  %-45s Already installed\n" "[$name]"
    return
  fi

  printf "  %-45s Installing... " "[$name]"
  local INSTALL=$(curl -s -b "$SESSION_FILE" -c "$SESSION_FILE" -X POST "$BASE_URL/web/dataset/call_kw" \
    -H "Content-Type: application/json" \
    --max-time 180 \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"model\":\"ir.module.module\",\"method\":\"button_immediate_install\",\"args\":[[$ID]],\"kwargs\":{}}}")
  
  if echo "$INSTALL" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(1 if d.get('error') else 0)" 2>/dev/null; then
    echo "OK"
    sleep 3
    do_login
  else
    ERR=$(echo "$INSTALL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(str(d.get('error',{}).get('data',{}).get('message','?'))[:100])" 2>/dev/null)
    echo "FAILED: $ERR"
  fi
}

for module in "${ALL_MODULES[@]}"; do
  install_module "$module"
done

echo ""
echo "============================================"
echo "DONE! Installed module count:"
PGPASSWORD=odoo docker exec cloud-db-1 psql -U odoo -d "$DB" -c \
  "SELECT COUNT(*) as total_installed FROM ir_module_module WHERE state='installed';"
echo "============================================"
