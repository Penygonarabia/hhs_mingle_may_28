/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { KsHeader } from "@ks_dashboard_ninja/components/Header/Header";
import { _t } from "@web/core/l10n/translation";
import { ModalDialog } from '@ks_dn_advance/js/play_modal';

patch(KsHeader.prototype,{
    setup(){
        super.setup();
        let dropdowns_to_add = [
            {name: "Dashboard TV", svg: "dashboard_tv", func:() => this.startTvDashboard(), class : '', modes: ["manager", "user", "custom_date"],},
            {name: "Email", svg: "email_svg", func:() => this.ks_send_mail(), class : '', modes: ["manager","user", "custom_date"],},
            {name: "Print Dashboard", svg: "print_dashboard", func:() => this.ks_dash_print(), class : '', modes: ["manager","user", "custom_date"],},
        ]
        let last_dropdown = this.dropdowns.find( (dropdown) => dropdown.name === 'More')
        last_dropdown.dropdown_items.push(...dropdowns_to_add)
    },

        ks_dash_print(id){
            var self = this;
            var ks_dashboard_name = self.ks_dashboard_data.name
            setTimeout(function () {
            window.scrollTo(0, 0);
            html2canvas(document.querySelector('.ks_dashboard_item_content'), {useCORS: true, allowTaint: false}).then(function(canvas){
            window.jsPDF = window.jspdf.jsPDF;
            var pdf = new jsPDF("p", "mm", "a4");
            var ks_img = canvas.toDataURL("image/jpeg", 0.90);
            var ks_props= pdf.getImageProperties(ks_img);
            var KspageHeight = 300;
            var KspageWidth = pdf.internal.pageSize.getWidth();
            var ksheight = (ks_props.height * KspageWidth) / ks_props.width;
            var ksheightLeft = ksheight;
            var position = 0;

            pdf.addImage(ks_img,'JPEG', 0, 0, KspageWidth, ksheight, 'FAST');
            ksheightLeft -= KspageHeight;
            while (ksheightLeft >= 0) {
                position = ksheightLeft - ksheight;
                pdf.addPage();
                pdf.addImage(ks_img, 'JPEG', 0, position,  KspageWidth, ksheight, 'FAST');
                ksheightLeft -= KspageHeight;
            };
            pdf.save(ks_dashboard_name + '.pdf');
        })
        },500);
        },

        ks_send_mail(ev) {
            var self = this;
            var ks_dashboard_name = self.ks_dashboard_data.name
            setTimeout(function () {
            $('.fa-envelope').addClass('d-none')
            $('.fa-spinner').removeClass('d-none');


            window.scrollTo(0, 0);
            html2canvas(document.querySelector('.ks_dashboard_item_content'), {useCORS: true, allowTaint: false}).then(function(canvas){
            window.jsPDF = window.jspdf.jsPDF;
            var pdf = new jsPDF("p", "mm", "a4");
            var ks_img = canvas.toDataURL("image/jpeg", 0.90);
            var ks_props= pdf.getImageProperties(ks_img);
            var KspageHeight = 300;
            var KspageWidth = pdf.internal.pageSize.getWidth();
            var ksheight = (ks_props.height * KspageWidth) / ks_props.width;
            var ksheightLeft = ksheight;
            var position = 0;

            pdf.addImage(ks_img,'JPEG', 0, 0, KspageWidth, ksheight, 'FAST');
            ksheightLeft -= KspageHeight;
            while (ksheightLeft >= 0) {
                position = ksheightLeft - ksheight;
                pdf.addPage();
                pdf.addImage(ks_img, 'JPEG', 0, position,  KspageWidth, ksheight, 'FAST');
                ksheightLeft -= KspageHeight;
            };
//            pdf.save(ks_dashboard_name + '.pdf');
            const file = pdf.output()
            const base64String = btoa(file)

//            localStorage.setItem(ks_dashboard_name + '.pdf',file);

            $.when(base64String).then(function(){
                self._rpc("/web/dataset/call_kw/ks_dashboard_ninja.board/ks_dashboard_send_mail",{
                    model: 'ks_dashboard_ninja.board',
                    method: 'ks_dashboard_send_mail',
                    args: [
                        [parseInt(self.ks_dashboard_id)],base64String

                    ],

                    kwargs:{}
                }).then(function(res){
                    $('.fa-envelope').removeClass('d-none')
                    $('.fa-spinner').addClass('d-none');
                    if (res['ks_is_send']){
                        var msg = res['ks_massage']
                            self.notification.add(_t(msg),{
                                title:_t("Success"),
                                type: 'info',
                            });

                    }else{
                        var msg = res['ks_massage']
                        self.notification.add(_t(msg),{
                                title:_t("Fail"),
                                type: 'warning',
                            });

                    }
                });
             })
        })
        },500);

        },

        startTvDashboard(e){
            if(this.checkItemsPresence())   return;
            var self = this;
            this.dialogService.add(ModalDialog,{
                items : Object.values(self.ks_dashboard_data.ks_item_data),
                dashboard_data : self.ks_dashboard_data,
                ksdatefilter:'none',
                pre_defined_filter : {},
                custom_filter:{},
                close: () => {},
                getDomainParams: this.env.ksGetParamsForItemFetch,
                getDashboardContext: this.env.getContext,

            });
        },


});

