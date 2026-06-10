/** @odoo-module **/
import { useService, useBus } from "@web/core/utils/hooks";
import { WebClient } from "@web/webclient/webclient";
import { patch } from "@web/core/utils/patch";
import { useRef, useState, onMounted } from "@odoo/owl";
import { SidebarBottom } from "./SidebarBottom";

patch(WebClient.prototype, {
    setup() {
        super.setup();
        this.root = useRef("root");
        this.rpc = useService('rpc');
        this.companyService = useService("company");
        this.menuService = useService("menu");
        this.currentCompany = this.companyService.currentCompany;
        this.navState = useState({ menuId: new URLSearchParams(window.location.hash.substring(1)).get('menu_id') });
        useBus(this.env.bus, 'ACTION_MANAGER:UI-UPDATED', () => {
            this.navState.menuId = new URLSearchParams(window.location.hash.substring(1)).get('menu_id');
        });
        this.fetch_menu_data();

        onMounted(() => {
        this.onPageLoad();
    });
    },
    toggleSidebar(ev){
        $(ev.currentTarget).toggleClass('visible');
        $('.nav-wrapper-bits').toggleClass('toggle-show');
    },
    onPageLoad() {
    //console.log("Custom page load logic triggered.");
    //alert("page loaded");
    //this.toggleSidebar();
    // Place any additional initialization logic here
    },
    toggle1arrow(hv){
       // $(hv.currentTarget).toggleClass('visible');
        $('.nav-ico').toggleClass('oi oi-chevron-right oi oi-chevron-left');
    },
    toggle1check(ev, ds){
       // $(ev.currentTarget).toggleClass('visible');
        var caschk = ev.currentTarget;
        var dds="child_menu_"+ds;
        //$(ev.currentTarget).nav()
       // $('.nav-ico').toggleClass('oi oi-chevron-right oi oi-chevron-left');
       //console.log(ev.currentTarget);
       //$('.nav-ico'+ds).toggleClass('oi oi-chevron-right oi oi-chevron-down');
       //$('.child_menu_'+ds).removeClass('show');
       //$('.nav-ico'+ds).toggleClass('fa fa-plus fa fa-minus');
      // $('.nav-ico'+ds).toggleClass('fa fa-plus fa fa-minus');
     //  console.log($(ev.currentTarget).parent());

    },
    fetch_menu_data(){
      var menu_data = this.menuService.getApps()
      var self = this;
      var rec_ids = []
      menu_data.map(app => rec_ids.push(app.id))
      this.rpc('/get/menu_data',{'menu_ids':rec_ids,
      }).then(function(rec) {
        console.log(rec); 
          $.each(menu_data, function( key, menu ) {
            var target_elem = '.primary-nav a.main_link[data-menu='+ menu.id+']'
            var elem = $(self.root.el).find(target_elem)

            elem.find('.app_icon').empty()
            var pr_record = rec[menu.id][0]
            menu.id = pr_record.id
            menu.use_icon = pr_record.use_icon
            menu.icon_class_name = pr_record.icon_class_name
            menu.icon_img = pr_record.icon_img

            if (pr_record.use_icon) {
                if (pr_record.icon_class_name) {
                    var icon_image = "<span class='ri "+pr_record.icon_class_name+"'/>"
                } else if (pr_record.icon_img) {
                    var icon_image = "<img class='img img-fluid' src='/web/image/ir.ui.menu/"+pr_record.id+"/icon_img' />"
                } else if (pr_record.web_icon != false) {
                    var icon_data = pr_record.web_icon.split('/icon.')
                    if (icon_data[1] == 'svg'){
                        var web_svg_icon = pr_record.web_icon.replace(',', '/')
                        var icon_image = "<img class='img img-fluid' src='"+web_svg_icon+"' />"
                    } else {
                        var icon_image = "<img class='img img-fluid' src='data:image/"+icon_data[1]+";base64,"+pr_record.web_icon_data+"' />"
                    }
                } else{
                    var icon_image = "<img class='img img-fluid' src='/clarity_backend_theme_bits/static/img/logo.png' />"
                    }
                elem.find('.app_icon').append($(icon_image))
            } else {
                if (pr_record.icon_img) {
                    var icon_image = "<img class='img img-fluid' src='/web/image/ir.ui.menu/"+pr_record.id+"/icon_img' />"
                } else if (pr_record.web_icon != false){
                    var icon_data = pr_record.web_icon.split('/icon.')
                    if (icon_data[1] == 'svg'){
                        var web_svg_icon = pr_record.web_icon.replace(',', '/')
                        var icon_image = "<img class='img img-fluid' src='"+web_svg_icon+"' />"
                    } else {
                        var icon_image = "<img class='img img-fluid' src='data:image/"+icon_data[1]+";base64,"+pr_record.web_icon_data+"' />"
                    }
                } else{
                    var icon_image = "<img class='img img-fluid' src='/clarity_backend_theme_bits/static/img/logo.png' />"
                }
                elem.find('.app_icon').append($(icon_image))
            }
          });
      })
    },
    BackMenuToggle(ev){  
        $(ev.currentTarget).parent().removeClass('show');
    },
    get currentMenuId() {
        return this.navState.menuId;
    },
    hasActiveDescendant(menuId) {
        const currentId = parseInt(this.currentMenuId);
        if (!currentId) return false;
        const check = (id) => {
            if (id === currentId) return true;
            const menu = this.menuService.getMenu(id);
            return (menu?.children || []).some(c => check(c));
        };
        const menu = this.menuService.getMenu(parseInt(menuId));
        return (menu?.children || []).some(c => check(c));
    },
    getBreadcrumbPath() {
        const currentId = parseInt(this.currentMenuId);
        if (!currentId) return [];
        const allMenus = this.menuService.getAll();
        const parentMap = new Map();
        for (const menu of allMenus) {
            for (const childId of (menu.children || [])) {
                parentMap.set(childId, menu.id);
            }
        }
        const path = [];
        let id = currentId;
        while (id && id !== 'root') {
            const menu = this.menuService.getMenu(id);
            if (!menu || menu.id === 'root') break;
            path.unshift({ id: menu.id, name: menu.name });
            id = parentMap.get(id);
        }
        return path;
    },
});
patch(WebClient, {
    components: { ...WebClient.components, SidebarBottom },
});

