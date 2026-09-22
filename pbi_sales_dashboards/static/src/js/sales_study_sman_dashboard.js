/** @odoo-module **/

import { registry } from "@web/core/registry";
import { t, addLabels } from "@pbi_dashboards/js/pbi_i18n";
import { PbiSalesStudyDashboard } from "./sales_study_dashboard";

// The ten-level "Sales Data Study" — the same matrix as its six-level sibling,
// on the salesman chain: Sales Type Group > Partner Classification > Region >
// City > Salesman > Customer > Main Category > Sub Category > Product Group >
// Product Sub-Group, from the v_pbi_sales_sman_fact snapshot
// (controllers/sales_study_sman_main.py).
//
// Everything visible is inherited. This file is only the configuration that
// differs: a different route, a different subtitle, and two filters the bidata
// board has no equivalent of — the Regular/Manager sub-category switch, and the
// developer-mode product scope. Deliberately so: the two boards carry the SAME
// menu name in two different containers, so a user reading them as one thing is
// right, and one component is what keeps that true.
addLabels({
  "Qty and Value by month across all eleven levels": "الكمية والقيمة شهريًا عبر المستويات الأحد عشر",
  "the budget is not captured per salesman": "الميزانية غير مسجلة لكل مندوب مبيعات",
  "the budget is not captured per product sub-group": "الميزانية غير مسجلة لكل مجموعة فرعية للمنتجات",
  "Sales Type Group": "مجموعة نوع البيع",
  "Partner Classification": "تصنيف العميل",
  "Region": "المنطقة",
  "City": "المدينة",
  "Salesman": "مندوب المبيعات",
  "Main Category": "الفئة الرئيسية",
  "Sub Category": "الفئة الفرعية",
  "Sub-Category Mode": "وضع الفئة الفرعية",
  "Regular": "عادي",
  "Manager": "مدير",
  "Product Scope": "نطاق المنتجات",
  "AC product groups": "مجموعات مكيفات",
  "All MDA lines": "كل بنود MDA",
  "Unassigned": "غير محدد",
  "Part No": "رقم القطعة",
  "Type a part number and press Enter": "اكتب رقم القطعة ثم اضغط Enter",
  "the budget is not captured per part": "الميزانية غير مسجلة لكل قطعة",
  "No sales for this part number in this period.": "لا توجد مبيعات لرقم القطعة هذا في هذه الفترة.",
  "Showing sales only": "عرض المبيعات فقط",
  "Part": "القطعة",
  "values": "قيم",
  "Outside product scope": "خارج نطاق المنتجات",
  "This part is outside the product scope": "هذه القطعة خارج نطاق المنتجات",
  "a part lookup ignores it, so these figures are not comparable with the unfiltered board.":
    "بحث القطعة يتجاهله، لذا هذه الأرقام غير قابلة للمقارنة مع اللوحة غير المفلترة.",
});

export class PbiSalesStudySmanDashboard extends PbiSalesStudyDashboard {
  get route() { return '/pbi_dashboards/sales_study_sman/data'; }
  get sourceName() { return 'v_pbi_sales_sman_fact'; }
  get subtitleText() { return t('Qty and Value by month across all eleven levels'); }
  get menuPath() { return t('Sales Dashboards'); }
  get csvName() { return 'sales_data_study_10_levels'; }

  // No Franchise control: the snapshot is MDA-only, so there is nothing for one
  // to choose between — same reasoning as the salesman chart boards. No
  // Customer Group either; that taxonomy is a bidata join and does not exist on
  // this source.
  get showFranchise() { return false; }
  get showCustomerGroup() { return false; }
  get showSubMode() { return false; }
  get showProductScope() { return this.isDebugMode; }

  // This board's source HAS a target: v_pbi_sales_budget_live, through the
  // same BUDGET_TEMP the three salesman chart boards read (see
  // controllers/sales_study_sman_main.py). So it offers the Sales / Budget /
  // Sales & Budget control the bidata board cannot.
  //
  // The target is not captured at every level. Salesman and Product Sub-Group
  // carry none at all — the budget was never captured per salesman or per
  // sub-group, and the view has no column to read one from — and a level can
  // go blank for ONE YEAR when that year's file was captured at another grain
  // (2026's Customer codes are channels). Those rows draw a dash and the
  // reason rather than an allocated figure: in a matrix people export to
  // Excel, a derived number and a captured one must not look alike.
  get showBudget() { return true; }

  // THE PART NO BOX. Only this board can offer it: v_pbi_sales_sman_fact —
  // the same snapshot "Sales Dashboard - VQ" and "Sales Dashboard With
  // Salesman" read, through the same view and the same in_scope rules — carries
  // part_no on every sales row, beside all ten level columns.
  //
  // It is a filter and not an eleventh level. Typing a part narrows the entire
  // board to it: the four product-side levels then hold exactly one value each,
  // which is the "which product group is this part in" answer, and the six
  // sale-side levels show every customer, city and salesman that bought it —
  // which is the answer worth having and the one a single resolved tuple could
  // not give.
  get showPartFilter() { return true; }

  // `scope` is the PRODUCT scope on this route and `periodScope` the
  // year/ytd/mtd one — two different things that happen to share a word. The
  // six-level route has only the period one and calls it `scope`, which is why
  // the mapping lives here rather than in the shared fetch.
  extraParams() {
    return {
      // Chooses the l7/l8 pair on BOTH halves: the actuals' temp table and the
      // budget temp each alias the chosen pair, so sales and target are always
      // compared in one taxonomy.
      subCategoryMode: this.state.subMode,
      scope: this.state.productScope,
      periodScope: this.state.periodScope,
    };
  }
}

registry.category("actions").add("pbi_sales_dashboards.sales_study_sman_dashboard", PbiSalesStudySmanDashboard);
