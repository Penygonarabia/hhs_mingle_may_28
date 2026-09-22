/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { t, addLabels } from "@pbi_dashboards/js/pbi_i18n";

addLabels({
  "Dashboard Configurations": "إعدادات لوحات المعلومات",
  "★ Complete Master Sync & Gap Repair": "★ المزامنة الكاملة للبيانات الرئيسية وإصلاح الفجوات",
  "Verify Links, Gaps and Data Alignments": "التحقق من الروابط والفجوات ومطابقة البيانات",
  "Run Complete Master Sync": "تشغيل المزامنة الكاملة",
  "Running Sync…": "جاري تنفيذ المزامنة…",
  "Run Verification": "تشغيل التحقق",
  "Verifying…": "جاري التحقق…",
  "Sync & Repair": "مزامنة وإصلاح",
  "Server capabilities": "إمكانيات الخادم",
  "Expand all": "توسيع الكل",
  "Collapse all": "طي الكل",
  "Expand": "توسيع",
  "Collapse": "طي",
  "packages": "حزم",
  "Run": "تشغيل",
  "Running…": "جاري التشغيل…",
  "Read only": "قراءة فقط",
  "Changes data": "يعدّل البيانات",
  "no rows": "لا توجد صفوف",
  "Failed": "فشل",
  "Not installed": "غير مثبت",
  "Executing SQL script…": "جاري تنفيذ البرنامج النصي SQL…",
  "Executing repair pipeline…": "جاري تنفيذ إجراءات الإصلاح…",
  "Running verification check…": "جاري تشغيل فحص التحقق…",
  "Completed": "اكتمل",
  "Cancel": "إلغاء",
  "Cancelled": "تم الإلغاء",
  "Cancelling…": "جاري الإلغاء…",
  "Operation cancelled": "تم إلغاء العملية",
  "Script finished successfully": "تم تنفيذ البرنامج النصي بنجاح",
  "Script execution failed": "فشل تنفيذ البرنامج النصي",
  "Analyzing CSV file…": "جاري تحليل ملف CSV…",
  "Applying bidata migration…": "جاري تطبيق ترحيل البيانات…",
  "Checking system capabilities…": "جاري فحص إمكانيات النظام…",
  "Installing Python package…": "جاري تثبيت حزمة Python…",
  "Create the bidata table and v_bidata_live": "إنشاء جدول bidata والعرض v_bidata_live",
  "Create table & view": "إنشاء الجدول والعرض",
  "Move bidata to another server": "نقل bidata إلى خادم آخر",
  "transfer tool": "أداة نقل",
  "Probe only (changes nothing)": "فحص فقط (بدون أي تغيير)",
  "Probing this server…": "جاري فحص الخادم…",
  "Bringing this server up…": "جاري تهيئة الخادم…",
  "Bring-up finished": "اكتملت التهيئة",
  "Bring-up failed": "فشلت التهيئة",
  "Copy": "نسخ",
  "Copied": "تم النسخ",
  "tools": "أدوات",
  "Database Master Taxonomy & Data Pipeline Sync": "تصنيف البيانات الرئيسية ومزامنة مسار البيانات",
  "Expand section": "توسيع القسم",
  "Collapse section": "طي القسم",
  "Restarting…": "جاري إعادة التشغيل…",
  "Purging cache & restarting container…": "جاري مسح الذاكرة المؤقتة وإعادة تشغيل الحاوية…",
  "Restart initiated. Reconnecting to server…": "تم بدء إعادة التشغيل. جاري إعادة الاتصال بالخادم…",
  "Server online! Reloading page…": "الخادم متصل الآن! جاري إعادة تحميل الصفحة…",
  // The four steps this page is now, and the third-party report above them.
  "Third-Party Odoo Apps the Boards Read": "تطبيقات أودو الخارجية التي تقرأ منها اللوحات",
  "Master-data modules released separately from this suite. Probed against the live schema, not the Apps list.": "وحدات البيانات الرئيسية الصادرة بشكل منفصل عن هذه الحزمة. يتم فحصها مقابل مخطط قاعدة البيانات الفعلي، لا قائمة التطبيقات.",
  "apps": "تطبيقات",
  "missing": "غير مثبت",
  "All present": "كل المتطلبات متوفرة",
  "Not on this server": "غير موجود على هذا الخادم",
  "Older version": "إصدار أقدم",
  "Present": "متوفر",
  "What this costs:": "ما الذي يترتب على ذلك:",
  "Absent from this database:": "غير موجود في قاعدة البيانات:",
  "Also absent, and it only costs a caption:": "غير موجود أيضاً، وتكلفته مجرد تسمية:",
  "Install ANY ONE of these from Apps:": "ثبّت أيّاً من هذه من قائمة التطبيقات:",
  "Module:": "الموديول:",
  "installed": "مثبت",
  "not on disk": "غير موجود على الخادم",
  "Installed, but older than the boards expect.": "مثبت، لكنه أقدم مما تتوقعه اللوحات.",
  "Upgrade the module rather than installing it again — the table or column named above was added after this version.": "قم بترقية الموديول بدلاً من إعادة تثبيته — فالجدول أو العمود المذكور أعلاه أُضيف بعد هذا الإصدار.",
  "No module owns this any more.": "لم يعد أي موديول مسؤولاً عن هذا.",
  "Do not look for it in Apps — Step 3 below creates the table, restores the column and rebuilds the view.": "لا تبحث عنه في التطبيقات — الخطوة 3 أدناه تنشئ الجدول وتستعيد العمود وتعيد بناء العرض.",
  "Checking…": "جاري الفحص…",
  "Check again": "إعادة الفحص",
  "Checking companion Odoo apps…": "جاري فحص تطبيقات أودو المرافقة…",
  "Requirements up to date": "تم تحديث حالة المتطلبات",
  "Check failed": "فشل الفحص",
  "Apply": "تطبيق",
  "tool": "أداة",
  "Apply Installs: Purge Assets & Restart Odoo": "تطبيق التثبيتات: تفريغ الأصول وإعادة تشغيل أودو",
  "A package installed above is inert until Odoo restarts. This is that restart.": "الحزمة المثبتة أعلاه لا تعمل حتى تتم إعادة تشغيل أودو. هذه هي إعادة التشغيل.",
  "Purge web assets cache and restart the container": "تفريغ ذاكرة الأصول وإعادة تشغيل الحاوية",
  "Interrupts the server": "يقطع الخدمة مؤقتاً",
  "Purge cache & restart Odoo": "تفريغ الذاكرة وإعادة تشغيل أودو",
  "Purge assets only": "تفريغ الأصول فقط",
  "Purging…": "جاري التفريغ…",
  "Step 1 · Bidata table and v_bidata_live": "الخطوة 1 · جدول bidata والعرض v_bidata_live",
  "Create the Table and the Live View": "إنشاء الجدول والعرض الحي",
  "Builds bidata with dbprod’s full shape and v_bidata_live over it. Safe to run twice.": "ينشئ جدول bidata بالبنية الكاملة والعرض v_bidata_live فوقه. آمن للتشغيل أكثر من مرة.",
  "Case-insensitive unit gate for v_bidata_live": "بوابة الوحدات غير الحساسة لحالة الأحرف في v_bidata_live",
  "Apply unit-gate fix": "تطبيق إصلاح بوابة الوحدات",
  "Step 2 · Bidata data import": "الخطوة 2 · استيراد بيانات bidata",
  "Export Here, Import There": "التصدير هنا والاستيراد هناك",
  "Move 2024, 2025 and 2026 across, then check what the feed is missing.": "انقل بيانات 2024 و2025 و2026، ثم تحقق مما ينقص التغذية.",
  "No years to export from this server.": "لا توجد سنوات للتصدير من هذا الخادم.",
  "That is what an empty or absent bidata table looks like — run Step 1 here, and do the exporting on the server that already carries the feed.": "هكذا يبدو جدول bidata الفارغ أو غير الموجود — شغّل الخطوة 1 هنا، وقم بالتصدير من الخادم الذي يحمل التغذية بالفعل.",
  "Check bidata feed gaps": "فحص فجوات تغذية bidata",
  "Check feed gaps": "فحص فجوات التغذية",
  "Step 3 · Master setup": "الخطوة 3 · إعداد البيانات الرئيسية",
  "Master Taxonomy, Sub-Group Link and Snapshot Rebuild": "تصنيف البيانات الرئيسية ورابط المجموعة الفرعية وإعادة بناء اللقطات",
  "Align all ten master dimensions across Target, This Year and Last Year, then rebuild and verify.": "مواءمة الأبعاد الرئيسية العشرة عبر المستهدف وهذا العام والعام الماضي، ثم إعادة البناء والتحقق.",
  "Rebuild the fact and budget views": "إعادة بناء عروض الحقائق والموازنة",
  "Rebuild the views": "إعادة بناء العروض",
  "Restore Product Sub-Group link (product_family)": "استعادة رابط المجموعة الفرعية للمنتج (product_family)",
  "Run Repair": "تشغيل الإصلاح",
  "Dismiss": "إغلاق",
  "View Rebuild Pipeline Results": "نتائج مسار إعادة بناء العروض",
});

// THE PAGE IS FOUR STEPS AND NOTHING ELSE.
//
// It used to carry seven sections -- snapshot freshness, upgrade blockers, an
// asset purge, a bring-up, a dated pile of maintenance scripts -- and standing
// up a new server meant finding the four that mattered among them and guessing
// their order. Run out of order they do not error; they leave a board of
// confident zeroes, which is why each wrong order produced a different failure
// that looked like a dashboard bug.
//
// What is left is: what this box is missing (Python packages AND the companion
// Odoo modules the boards read master data from), then the bidata shape, then
// the bidata rows, then the masters. The routes behind the removed sections are
// untouched on the server side -- they came off the page, they were not
// deleted, and a section can come back by adding markup and nothing else.
export class PbiDashboardConfigPage extends Component {
  static template = "pbi_dashboard_configurations.config_page";
  static props = ["*"];

  setup() {
    this.rpc = useService("rpc");
    this.t = t;
    this._progressTimers = {};
    this._abortControllers = {};
    this.state = useState({
      loading: true,
      error: "",
      collapsedCapabilities: true,
      bringUpSteps: null,
      bringUpRunning: "",
      // The four steps open, the two that are conditional closed. Someone
      // landing here is standing one up, so the work should be visible without
      // a click; the restart is only wanted after an install, and the packages
      // list is short and rarely the problem.
      collapsedWorkflowGroups: {
        requirements: false,
        restart: true,
        bidataschema: false,
        bidataimport: false,
        masters: false,
      },
      // Companion Odoo modules: which the boards read, which this database
      // has, and what each absence costs. Read-only -- installing an Odoo
      // module belongs to Apps, which knows how to run its hooks and
      // migrations.
      requirements: [],
      reqBusy: false,
      // Moving bidata between servers. `bidataDiagnosis` doubles as the gate on
      // the Apply button: it only appears once a file has been read and
      // reported on, so nothing is written before someone has seen the numbers.
      bidataYears: [],
      bidataPick: {},
      bidataBusy: false,
      bidataMessage: "",
      bidataDiagnosis: null,
      // Optional packages. Read on setup and re-readable, because the answer
      // changes when someone installs one on the host.
      capabilities: [],
      capsBusy: false,
      copied: "",
      installing: "",
      installMessage: {},
      installOutput: {},
      running: null,
      result: null,
      results: {},
      // Real-time progress percentage (%) and status indicator for running buttons
      progress: {},
      purgingAssets: false,
      purgeAssetsMessage: "",
      purgingAndRestarting: false,
    });

    onMounted(() => {
      // Capabilities resolves `loading`, and does it in a finally, so a route
      // that 500s still opens the page with the rest of the steps on it. The
      // other two are independent: a server with no bidata table has no years
      // to offer and must still be able to read the requirements report.
      this.loadCapabilities();
      this.loadRequirements();
      this.loadBidataYears();
    });
    onWillUnmount(() => {
      this._stopAllProgress();
    });
  }

  // ---------------------------------------------------- progress tracking
  startProgress(key, initialLabel = t("Running…"), durationEstimateMs = 5000) {
    this._stopProgress(key);
    this.state.progress = {
      ...this.state.progress,
      [key]: { pct: 8, label: initialLabel, status: "running" }
    };
    const startTime = Date.now();
    this._progressTimers[key] = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const cur = this.state.progress[key];
      if (!cur || cur.status !== "running") {
        this._stopProgress(key);
        return;
      }
      let targetPct;
      const ratio = elapsed / Math.max(durationEstimateMs, 1000);
      if (ratio < 0.3) {
        targetPct = 8 + (ratio / 0.3) * 35;
      } else if (ratio < 0.7) {
        targetPct = 43 + ((ratio - 0.3) / 0.4) * 35;
      } else {
        targetPct = 78 + (1 - Math.exp(-(ratio - 0.7) * 2.5)) * 18;
      }
      const rounded = Math.min(96, Math.max(cur.pct, Math.round(targetPct)));
      this.state.progress = {
        ...this.state.progress,
        [key]: { ...cur, pct: rounded }
      };
    }, 150);
  }

  finishProgress(key, success = true, finalLabel = null) {
    this._stopProgress(key);
    const label = finalLabel || (success ? t("Completed") : t("Failed"));
    this.state.progress = {
      ...this.state.progress,
      [key]: { pct: 100, label, status: success ? "done" : "error" }
    };
    setTimeout(() => {
      if (this.state.progress[key] && this.state.progress[key].status !== "running") {
        const next = { ...this.state.progress };
        delete next[key];
        this.state.progress = next;
      }
    }, 3500);
  }

  _stopProgress(key) {
    if (this._progressTimers && this._progressTimers[key]) {
      clearInterval(this._progressTimers[key]);
      delete this._progressTimers[key];
    }
  }

  _stopAllProgress() {
    if (this._progressTimers) {
      for (const k of Object.keys(this._progressTimers)) {
        clearInterval(this._progressTimers[k]);
      }
      this._progressTimers = {};
    }
  }

  getProgress(key) {
    return this.state.progress && this.state.progress[key];
  }

  async cancelAction(key) {
    if (!key) return;

    // 1. Abort fetch if there is an active AbortController
    if (this._abortControllers && this._abortControllers[key]) {
      try {
        this._abortControllers[key].abort();
      } catch (e) {}
      delete this._abortControllers[key];
    }

    // 2. Stop progress timer and mark cancelled
    this._stopProgress(key);
    this.finishProgress(key, false, t("Cancelled"));

    // 3. Reset component state corresponding to key
    if (this.state.running === key || !this.state.progress[key] || this.state.progress[key].status === "running") {
      this.state.running = null;
    }
    if (key === "bidata_import") {
      this.state.bidataBusy = false;
      this.state.bidataMessage = t("Cancelled.");
    }
    if (key === "caps_check") {
      this.state.capsBusy = false;
    }
    if (key === "reqs_check") {
      this.state.reqBusy = false;
    }
    if (typeof key === "string" && key.startsWith("cap_")) {
      this.state.installing = "";
      const capKey = key.replace("cap_", "");
      this.state.installMessage = { ...this.state.installMessage, [capKey]: t("Cancelled.") };
    }

    // 4. Send background query cancel to PostgreSQL
    try {
      await this.rpc("/pbi_dashboards/config/cancel_query", {});
    } catch (e) {}
  }

  // Capabilities collapse / expand
  toggleCapabilities() {
    this.state.collapsedCapabilities = !this.isCapabilitiesCollapsed();
  }

  expandCapabilities() {
    this.state.collapsedCapabilities = false;
  }

  collapseCapabilities() {
    this.state.collapsedCapabilities = true;
  }

  isCapabilitiesCollapsed() {
    return this.state.collapsedCapabilities !== false;
  }

  // Workflow Groups collapse / expand
  toggleWorkflowGroup(groupKey) {
    const current = this.isWorkflowGroupCollapsed(groupKey);
    this.state.collapsedWorkflowGroups = {
      ...this.state.collapsedWorkflowGroups,
      [groupKey]: !current,
    };
  }

  isWorkflowGroupCollapsed(groupKey) {
    if (this.state.collapsedWorkflowGroups[groupKey] === undefined) {
      return true;
    }
    return !!this.state.collapsedWorkflowGroups[groupKey];
  }

  // Copy a command to the clipboard.
  //
  // navigator.clipboard is undefined on an insecure origin, and this server is
  // reached over plain http on a .local hostname, so it is absent exactly where
  // it is needed. Falling back to selecting the text is not a consolation
  // prize: the command ends up on screen, selected, one keystroke from copied,
  // which is what someone about to paste it into a terminal actually needs.
  async copyCommand(key) {
    const el = document.getElementById("cmd-" + key);
    if (!el) return;
    const text = el.textContent.trim();
    await this.copyText(text, key);
  }

  async copyText(text, key) {
    if (!text) return;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        this.state.copied = key;
        setTimeout(() => { if (this.state.copied === key) this.state.copied = ""; }, 2000);
        return;
      }
    } catch {
      // fallback to selecting / execCommand
    }
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try {
      document.execCommand("copy");
      this.state.copied = key;
      setTimeout(() => { if (this.state.copied === key) this.state.copied = ""; }, 2000);
    } catch (e) {
      console.warn("Copy failed:", e);
    }
    document.body.removeChild(ta);
  }

  // ------------------------------------------------- from-scratch bring-up
  async runBringUp(dryRun) {
    if (this.state.bringUpRunning) return;
    if (!dryRun) {
      const ok = window.confirm(
        "Bring this server up to the expected schema\n\n" +
        "This creates missing tables and columns, repopulates the Product " +
        "Sub-Group link, and DROPs and rebuilds the fact and budget views " +
        "from module code. The rebuild repopulates the view, so it can take " +
        "a while on a database with a full ERP feed.\n\n" +
        "Every step diagnoses first and is safe to run twice. Run it?"
      );
      if (!ok) return;
    }
    this.state.bringUpRunning = dryRun ? "dry" : "run";
    this.state.bringUpSteps = null;
    this.startProgress("bring_up",
      dryRun ? t("Probing this server…") : t("Bringing this server up…"),
      dryRun ? 4000 : 90000);
    try {
      const res = await this.rpc("/pbi_dashboards/config/bring_up", { dry_run: !!dryRun });
      if (res.error) {
        this.state.bringUpSteps = [{
          key: "error", name: t("Failed"), state: "error",
          detail: res.error === "forbidden"
            ? t("You do not have access to this page.") : res.error,
        }];
        this.finishProgress("bring_up", false, t("Bring-up failed"));
      } else {
        this.state.bringUpSteps = res.steps || [];
        const bad = this.state.bringUpSteps.some(s => s.state === "error");
        this.finishProgress("bring_up", !bad,
          bad ? t("Bring-up failed") : t("Bring-up finished"));
      }
    } catch (e) {
      this.state.bringUpSteps = [{
        key: "error", name: t("Failed"), state: "error",
        detail: (e && e.message) || String(e),
      }];
      this.finishProgress("bring_up", false, t("Bring-up failed"));
    } finally {
      this.state.bringUpRunning = "";
    }
  }

  // ---------------------------------------------------- post-upgrade cache reset & restart
  async purgeWebAssets() {
    if (this.state.purgingAssets) return;
    this.state.purgingAssets = true;
    this.state.purgeAssetsMessage = t("Purging compiled web assets cache…");
    this.startProgress("purge_assets", t("Purging web assets cache…"), 2500);
    try {
      const res = await this.rpc("/pbi_dashboards/config/purge_web_assets", {});
      if (res.error) {
        this.state.purgeAssetsMessage = res.error;
        this.finishProgress("purge_assets", false, res.error);
      } else {
        const msg = res.message || t("Assets cache purged successfully.");
        this.state.purgeAssetsMessage = msg;
        this.finishProgress("purge_assets", true, msg);
      }
    } catch (e) {
      this.state.purgeAssetsMessage = t("Failed to purge web assets.");
      this.finishProgress("purge_assets", false, t("Failed to purge web assets."));
    } finally {
      this.state.purgingAssets = false;
    }
  }

  async purgeAndRestart() {
    if (this.state.purgingAndRestarting) return;
    const ok = window.confirm(
      `Purge Assets Cache & Restart Server\n\n` +
      `This will:\n` +
      `1. Delete compiled web.assets_* bundles from PostgreSQL\n` +
      `2. Restart the Odoo web container (cloud-web-1)\n\n` +
      `The page will automatically reconnect and reload.\n\n` +
      `Proceed with cache reset and restart?`
    );
    if (!ok) return;

    this.state.purgingAndRestarting = true;
    this.startProgress("purge_and_restart", t("Purging cache & restarting container…"), 14000);

    try {
      await this.rpc("/pbi_dashboards/config/purge_and_restart", {});
    } catch {
      // Network disconnect is expected
    }
    this._reconnectOdooLoop("purge_and_restart");
  }

  _reconnectOdooLoop(progressKey) {
    let attempts = 0;
    const maxAttempts = 50; // ~75 seconds
    setTimeout(() => {
      const interval = setInterval(async () => {
        attempts++;
        try {
          const resp = await fetch("/web/login", {
            method: "GET",
            cache: "no-store",
            credentials: "same-origin",
          });
          if (resp && (resp.ok || resp.status === 200 || resp.status === 302 || resp.status === 303)) {
            clearInterval(interval);
            this.finishProgress(progressKey, true, t("Server online! Reloading page…"));
            this.state.purgingAndRestarting = false;
            setTimeout(() => {
              window.location.reload();
            }, 800);
          }
        } catch {
          // Container is still rebooting
          if (attempts >= maxAttempts) {
            clearInterval(interval);
            this.finishProgress(progressKey, false, t("Reconnection timed out. Please refresh page manually."));
            this.state.purgingAndRestarting = false;
          }
        }
      }, 1400);
    }, 1800);
  }

  // Install the package for ONE capability. The button only exists on a card
  // whose state is 'missing', and the server re-checks that anyway -- a stale
  // page must not be able to reinstall something already in use.
  async installCapability(key) {
    if (this.state.installing) return;
    this.state.installing = key;
    this.state.installMessage = { ...this.state.installMessage, [key]: t("Running pip — this can take a minute.") };
    this.state.installOutput = { ...this.state.installOutput, [key]: "" };
    this.startProgress("cap_" + key, t("Installing Python package…"), 25000);
    try {
      const res = await this.rpc("/pbi_dashboards/config/install_capability", { key });
      if (this.state.progress["cap_" + key] && this.state.progress["cap_" + key].label === t("Cancelled")) {
        return;
      }
      const msg = res.error || res.message || "";
      this.state.installMessage = { ...this.state.installMessage, [key]: msg };
      if (res.output && res.output.length) {
        this.state.installOutput = { ...this.state.installOutput, [key]: res.output.join("\n") };
      }
      this.finishProgress("cap_" + key, !res.error, res.error ? t("Install failed") : t("Installation complete"));
      // Re-read either way: on success the card should move to "Restart
      // needed", and on failure it should still show what is actually true.
      await this.loadCapabilities();
    } catch {
      if (this.state.progress["cap_" + key] && this.state.progress["cap_" + key].label === t("Cancelled")) {
        return;
      }
      this.state.installMessage = { ...this.state.installMessage, [key]: t("The install request failed.") };
      this.finishProgress("cap_" + key, false, t("The install request failed."));
    } finally {
      this.state.installing = "";
    }
  }

  // This one also resolves `loading`, and does it in a finally. The whole page
  // is gated on that flag, so a route that 500s must still open the page --
  // three of the four steps do not need this answer, and a blank screen is the
  // worst possible response to "the capabilities check failed".
  async loadCapabilities(explicit) {
    if (explicit) {
      this.state.capsBusy = true;
      this.startProgress("caps_check", t("Checking system capabilities…"), 2000);
    }
    try {
      const res = await this.rpc("/pbi_dashboards/config/capabilities", {});
      if (this.state.progress["caps_check"] && this.state.progress["caps_check"].label === t("Cancelled")) {
        return;
      }
      if (res.error === "forbidden") {
        this.state.error = t("You do not have access to this page.");
        this.state.capabilities = [];
        return;
      }
      this.state.error = "";
      if (!res.error) this.state.capabilities = res.capabilities || [];
      if (explicit) this.finishProgress("caps_check", true, t("Capabilities up to date"));
    } catch {
      if (this.state.progress["caps_check"] && this.state.progress["caps_check"].label === t("Cancelled")) {
        return;
      }
      this.state.capabilities = [];
      if (explicit) this.finishProgress("caps_check", false, t("Check failed"));
    } finally {
      this.state.capsBusy = false;
      this.state.loading = false;
    }
  }

  // ------------------------------------------- companion Odoo modules
  // Read-only, always. Nothing on this page installs an Odoo module: that runs
  // the module's own hooks, data files and migrations against this database,
  // and Apps is what knows how to do that.
  async loadRequirements(explicit) {
    if (explicit) {
      this.state.reqBusy = true;
      this.startProgress("reqs_check", t("Checking companion Odoo apps…"), 2000);
    }
    try {
      const res = await this.rpc("/pbi_dashboards/config/requirements", {});
      if (this.state.progress["reqs_check"] && this.state.progress["reqs_check"].label === t("Cancelled")) {
        return;
      }
      if (!res.error) this.state.requirements = res.requirements || [];
      if (explicit) this.finishProgress("reqs_check", true, t("Requirements up to date"));
    } catch {
      if (this.state.progress["reqs_check"] && this.state.progress["reqs_check"].label === t("Cancelled")) {
        return;
      }
      this.state.requirements = [];
      if (explicit) this.finishProgress("reqs_check", false, t("Check failed"));
    } finally {
      this.state.reqBusy = false;
    }
  }

  // How many companion apps this database does not have. Drives the chip on
  // the collapsed group header, so the count is readable without expanding --
  // which is the whole point of putting it there.
  missingRequirements() {
    return this.state.requirements.filter(r => r.state === "missing").length;
  }

  // ------------------------------------------------------------ bidata
  async loadBidataYears() {
    try {
      const res = await this.rpc("/pbi_dashboards/config/bidata_years", {});
      if (!res.error) this.state.bidataYears = res.years || [];
      if (res.message) this.state.bidataMessage = res.message;
    } catch {
      this.state.bidataYears = [];
    }
  }

  pickYear(year, on) {
    this.state.bidataPick = { ...this.state.bidataPick, [year]: on };
  }

  exportBidata() {
    const years = Object.keys(this.state.bidataPick).filter(y => this.state.bidataPick[y]);
    if (!years.length) {
      this.state.bidataMessage = t("Pick at least one year to export.");
      return;
    }
    // A plain navigation, not fetch: the response is a download and the browser
    // handles it better than a blob round-trip for a file this size.
    window.location = "/pbi_dashboards/config/export_bidata?years=" + years.join(",");
    this.state.bidataMessage = t("Exporting ") + years.join(", ") + "…";
  }

  async importBidata(apply) {
    const input = document.getElementById("bidata-file");
    const file = input && input.files && input.files[0];
    if (!file) {
      this.state.bidataMessage = t("Choose a CSV file first.");
      return;
    }
    this.state.bidataBusy = true;
    this.state.bidataMessage = apply ? t("Applying…") : t("Reading the file…");
    const estDuration = apply ? 20000 : 8000;
    const pLabel = apply ? t("Applying bidata migration…") : t("Analyzing CSV file…");
    this.startProgress("bidata_import", pLabel, estDuration);
    const controller = new AbortController();
    this._abortControllers["bidata_import"] = controller;
    try {
      const body = new FormData();
      body.append("csv_file", file);
      if (apply) body.append("apply", "1");
      const res = await fetch("/pbi_dashboards/config/import_bidata", { method: "POST", body, signal: controller.signal });
      const out = await res.json();
      if (this.state.progress["bidata_import"] && this.state.progress["bidata_import"].label === t("Cancelled")) {
        return;
      }
      if (out.error) {
        this.state.bidataMessage = out.error;
        // A refusal still carries its numbers, and they are what explain it.
        this.state.bidataDiagnosis = out.diagnosis || null;
        this.finishProgress("bidata_import", false, t("Import error"));
        return;
      }
      const d = out.diagnosis;
      this.state.bidataDiagnosis = d;
      this.state.bidataMessage = out.applied
        ? t("Imported: ") + d.inserted + t(" new, ") + d.updated + t(" updated (years ") +
          (d.years_in_file || []).join(", ") + ")."
        : d.rows_in_file + t(" rows in the file for years ") + (d.years_in_file || []).join(", ") +
          " — " + d.new_rows + t(" new, ") + d.already_present + t(" already here, of which ") +
          d.overlapping_but_different + t(" differ. Nothing written yet.");
      this.finishProgress("bidata_import", true, out.applied ? t("Import applied") : t("Analysis complete"));
    } catch (err) {
      if (err.name === "AbortError" || (this.state.progress["bidata_import"] && this.state.progress["bidata_import"].label === t("Cancelled"))) {
        this.state.bidataMessage = t("Cancelled.");
        this.finishProgress("bidata_import", false, t("Cancelled"));
      } else {
        this.state.bidataMessage = t("The upload failed.");
        this.finishProgress("bidata_import", false, t("The upload failed."));
      }
    } finally {
      delete this._abortControllers["bidata_import"];
      this.state.bidataBusy = false;
    }
  }

  async runScript(script) {
    // A script that writes deserves a deliberate second action. The read-only
    // one does not: making someone confirm a diagnosis trains them to click
    // through the dialog that matters.
    if (script.writes) {
      const ok = window.confirm(
        `${script.name}\n\n` +
        `This changes data in the database.\n\n` +
        `It diagnoses first, guards every write and is safe to run twice, ` +
        `but it is not a preview. Run it?`
      );
      if (!ok) return;
    }
    this.state.running = script.key;
    const isHeavy = script.file.includes("rebuild") || script.file.includes("scope") || script.file.includes("sync") || script.file.includes("pipeline") || script.file.includes("diagnose");
    const estDuration = isHeavy ? 25000 : 8000;
    this.startProgress(script.key, t("Executing SQL script…"), estDuration);
    try {
      const res = await this.rpc("/pbi_dashboards/config/run_script", { key: script.key });
      if (this.state.progress[script.key] && this.state.progress[script.key].label === t("Cancelled")) {
        return;
      }
      if (res.error) {
        const errObj = {
          key: script.key, name: script.name,
          failed: { message: res.error === "forbidden"
            ? t("You do not have access to this page.")
            : (res.message || res.error || t("That script is not known.")) },
          blocks: [], narration: [],
        };
        this.state.results = { ...this.state.results, [script.key]: errObj };
        this.state.result = errObj;
        this.finishProgress(script.key, false, t("Script execution failed"));
        return;
      }
      this.state.results = { ...this.state.results, [script.key]: res };
      this.state.result = res;
      if (res.failed) {
        this.finishProgress(script.key, false, t("Script execution failed"));
      } else {
        this.finishProgress(script.key, true, t("Script finished successfully"));
      }
    } catch (e) {
      if (this.state.progress[script.key] && this.state.progress[script.key].label === t("Cancelled")) {
        return;
      }
      const failObj = {
        key: script.key, name: script.name,
        failed: { message: t("The script could not be run.") },
        blocks: [], narration: [],
      };
      this.state.results = { ...this.state.results, [script.key]: failObj };
      this.state.result = failObj;
      this.finishProgress(script.key, false, t("The script could not be run."));
    } finally {
      this.state.running = null;
    }
  }

  getResult(key) {
    if (this.state.results && this.state.results[key]) {
      return this.state.results[key];
    }
    if (this.state.result && this.state.result.key === key) {
      return this.state.result;
    }
    return null;
  }

  clearResult(key) {
    if (this.state.results && this.state.results[key]) {
      const next = { ...this.state.results };
      delete next[key];
      this.state.results = next;
    }
    if (this.state.result && this.state.result.key === key) {
      this.state.result = null;
    }
  }

}

registry.category("actions").add("pbi_dashboard_configurations.config_page",
                                PbiDashboardConfigPage);
