/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import {KsListViewPreview} from '@ks_dashboard_ninja/widgets/ks_list_view/ks_list_view';
import {Ksdashboardgraph} from '@ks_dashboard_ninja/components/ks_dashboard_graphs/ks_dashboard_graphs'
import { localization } from "@web/core/l10n/localization";
import {formatDate,formatDateTime} from "@web/core/l10n/dates";
import { formatFloat,formatInteger } from "@web/views/fields/formatters";
import {parseDateTime,parseDate,} from "@web/core/l10n/dates";
import { session } from "@web/session";
import { convert_data_to_utc } from '@ks_dashboard_ninja/js/ks_global_functions'


patch(KsListViewPreview.prototype,{
    setup(){
        super.setup()
    },

       value(){
            var rec = this.props.record.data;
            if (rec.ks_dashboard_item_type === 'ks_list_view') {
                if(rec.ks_data_calculation_type === "custom"){
                     return super.value();
                } else {
                   this.calculation_type = rec.ks_data_calculation_type
                   return super.value();
                }
            }
        },
         onChartCanvasClick(ev){
            ev.stopPropagation();
    },
});
patch(Ksdashboardgraph.prototype,{
    setup(){
        super.setup()
    },

       prepare_list(){
            var self = this;
            super.prepare_list();
            this.layout = this.item.ks_list_view_layout;

       },

        _ksSortAscOrder(e) {
            if($(e.currentTarget).hasClass("ks_dn_asc") || ($(e.target).parent().parent().hasClass("ks_dn_asc"))){
                var self = this;
                var ks_value_offfset = $(e.currentTarget.parentElement.parentElement.parentElement.parentElement.parentElement).find('.ks_pager').find('.ks_counter').find('.ks_value').text();
                var offset = 0;
                var initial_count = 0;
                if (ks_value_offfset)
                {
                    initial_count = parseInt(ks_value_offfset.split('-')[0])
                    offset = parseInt(ks_value_offfset.split('-')[1])
                }

                var item_id = e.currentTarget.dataset.itemId;
                var field = e.currentTarget.dataset.fields;
                var context = {}
                var user_id = session.uid;
                var context = self.env.getContext();
                context.user_id = user_id;
                context.offset = offset;
                context.initial_count = initial_count;

                var store = e.currentTarget.dataset.store;
                context.field = field;
                context.sort_order = "ASC"
                var ks_domain

                ks_domain = self.env.ksGetParamsForItemFetch(parseInt(item_id));
                if (store) {
                    self._rpc("/web/dataset/call_kw/ks_dashboard_ninja.item/ks_get_list_data_orderby_extend",{
                        model: 'ks_dashboard_ninja.item',
                        method: 'ks_get_list_data_orderby_extend',
                        args: [
                            [parseInt(item_id)], ks_domain
                        ],
                        kwargs:{context: context}
                    }).then(function(result) {
                        if (result) {
                            result = convert_data_to_utc(JSON.stringify(result))
                            self.item.ks_list_view_data = result;
                            self.prepare_list()
                            }
                    }.bind(this));


                    $($(this.ks_list_view.el).find(".ks_sort_up[data-fields=" + field + "]")).removeClass('ks_plus')
                    $($(this.ks_list_view.el).find(".ks_sort_down[data-fields=" + field + "]")).addClass('ks_plus')
                    $($(this.ks_list_view.el).find(".list_header[data-fields=" + field + "]")).removeClass('ks_dn_asc')
                    $($(this.ks_list_view.el).find(".list_header[data-fields=" + field + "]")).addClass('ks_dn_desc')
                }

            }else{
                var self = this;
                var ks_value_offfset = $(e.currentTarget.parentElement.parentElement.parentElement.parentElement.parentElement).find('.ks_pager').find('.ks_counter').find('.ks_value').text();
                var offset = 0;
                var initial_count = 0;
                if (ks_value_offfset)
                {
                    initial_count = parseInt(ks_value_offfset.split('-')[0])
                    offset = parseInt(ks_value_offfset.split('-')[1])
                }
                var item_id = e.currentTarget.dataset.itemId;
                var field = e.currentTarget.dataset.fields;
                var context = self.env.getContext()
                var user_id = session.uid;
                context.user_id = user_id;
                context.offset = offset;
                context.initial_count = initial_count;
                var store = e.currentTarget.dataset.store;
                context.field = field;
                context.sort_order = "DESC";
                var ks_domain
                ks_domain = self.env.ksGetParamsForItemFetch(parseInt(item_id));
                if (store) {
                    self._rpc("/web/dataset/call_kw/ks_dashboard_ninja.item/ks_get_list_data_orderby_extend",{
                        model: 'ks_dashboard_ninja.item',
                        method: 'ks_get_list_data_orderby_extend',
                        args: [
                            [parseInt(item_id)], ks_domain
                        ],
                        kwargs:{context : context}
                    }).then(function(result) {
                        if (result){
                            result = convert_data_to_utc(JSON.stringify(result))
                            self.item.ks_list_view_data = result;
                            self.prepare_list()
                        }
                    }.bind(this));
                    $($(this.ks_list_view.el).find(".ks_sort_down[data-fields=" + field + "]")).removeClass('ks_plus')
                    $($(this.ks_list_view.el).find(".ks_sort_up[data-fields=" + field + "]")).addClass('ks_plus')
                    $($(this.ks_list_view.el).find(".list_header[data-fields=" + field + "]")).addClass('ks_dn_asc')
                    $($(this.ks_list_view.el).find(".list_header[data-fields=" + field + "]")).removeClass('ks_dn_desc')
                }
            }
        }


});

